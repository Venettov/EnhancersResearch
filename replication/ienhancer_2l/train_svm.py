#!/usr/bin/env python3
"""Train two RBF SVMs with the predeclared, frozen grouped evaluation.

Cached RBF kernels depend only on each pair of fixed feature vectors. No
scaler or other statistic is fitted on the whole benchmark. All SVM training
and hyperparameter selection use explicitly indexed training subsets.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
import csv
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
from pathlib import Path
import platform
import subprocess
import time
import warnings
import numpy as np
from sklearn.exceptions import ConvergenceWarning
from sklearn.metrics import (accuracy_score, average_precision_score, balanced_accuracy_score,
                             confusion_matrix, matthews_corrcoef, roc_auc_score)
from sklearn.metrics.pairwise import euclidean_distances, rbf_kernel
from sklearn.svm import SVC
from threadpoolctl import threadpool_limits
from common import HERE, PREPARED, ROOT, load_benchmark, sha256, write_csv, write_json
from evaluation import validate_assignments
from features import feature_names

FEATURE_CHECKPOINT = HERE / 'checkpoints/2026-10-13-groups-features'
DEFAULT_FEATURES = HERE / 'output/2026-10-13-groups-features/features_primary.npz'
PROTOCOL = HERE / 'training_protocol.json'


def array_hash(array):
    return hashlib.sha256(np.ascontiguousarray(array, dtype='<f8').tobytes()).hexdigest()


def load_inputs(features_path=DEFAULT_FEATURES, prepared=PREPARED):
    checkpoint = json.loads((FEATURE_CHECKPOINT / 'checkpoint.json').read_text())
    for name in ('evaluation_assignments.csv', 'features_audit.json'):
        if sha256(FEATURE_CHECKPOINT / name) != checkpoint['files_sha256'][name]:
            raise ValueError(f'Changed frozen checkpoint: {name}')
    with (FEATURE_CHECKPOINT / 'evaluation_assignments.csv').open(newline='') as stream:
        assignments = list(csv.DictReader(stream))
    for row in assignments:
        for key in ['outer_fold'] + [f'inner_fold_outer_{i}' for i in range(5)]:
            row[key] = int(row[key])
    validate_assignments(assignments)
    by_id = {r['record_id']: r for r in assignments}
    rows = load_benchmark(prepared)
    if set(by_id) != {r['record_id'] for r in rows}:
        raise ValueError('Fold table differs from the benchmark population')
    reference = json.loads((FEATURE_CHECKPOINT / 'features_audit.json').read_text())['features']['primary']
    layers = {}
    with np.load(features_path, allow_pickle=False) as archive:
        if list(archive['feature_names']) != feature_names():
            raise ValueError('Feature order mismatch')
        for layer in ('layer1', 'layer2'):
            selected = rows if layer == 'layer1' else [r for r in rows if r['class_label'] != 'non-enhancer']
            expected_ids = [r['record_id'] for r in selected]
            X, y, ids = archive[f'X_{layer}'], archive[f'y_{layer}'], archive[f'record_ids_{layer}']
            if list(ids) != expected_ids or len(set(ids)) != len(ids):
                raise ValueError('Matrix record order or identity mismatch')
            expected_y = [int(r['class_label'] != 'non-enhancer' if layer == 'layer1' else r['class_label'] == 'strong') for r in selected]
            if not np.array_equal(y, expected_y):
                raise ValueError('Matrix labels differ from reviewed original labels')
            if list(X.shape) != reference[layer]['shape'] or array_hash(X) != reference[layer]['array_sha256_le_float64']:
                raise ValueError('Feature matrix differs from the frozen primary reconstruction')
            for row in selected:
                a = by_id[row['record_id']]
                if a['sequence_sha256'] != row['sequence_sha256'] or a['class_label'] != row['class_label']:
                    raise ValueError('Fold/source label or sequence mismatch')
            layers[layer] = {'X': X, 'y': y.astype(int), 'ids': ids,
                             'groups': np.asarray([by_id[r]['group_id'] for r in ids]),
                             'outer': np.asarray([by_id[r]['outer_fold'] for r in ids]),
                             'inner': {i:np.asarray([by_id[r][f'inner_fold_outer_{i}'] for r in ids]) for i in range(5)}}
    return layers


def assert_split(train, test, groups, y):
    train, test = np.asarray(train), np.asarray(test)
    if (len(train) == 0 or len(test) == 0 or len(set(train)) != len(train) or
            len(set(test)) != len(test) or np.intersect1d(train, test).size):
        raise ValueError('Invalid or overlapping split indices')
    if set(groups[train]) & set(groups[test]):
        raise ValueError('Related group crosses training and validation')
    if set(y[train]) != {0, 1} or set(y[test]) != {0, 1}:
        raise ValueError('Both classes are required in training and validation')


def splits_for_outer(data, held_out):
    outer_train = np.flatnonzero(data['outer'] != held_out)
    outer_test = np.flatnonzero(data['outer'] == held_out)
    assert_split(outer_train, outer_test, data['groups'], data['y'])
    inner = data['inner'][held_out]
    if not np.array_equal(inner == -1, data['outer'] == held_out):
        raise ValueError('Outer test records enter inner tuning')
    splits = []
    for fold in range(3):
        train = np.flatnonzero((inner >= 0) & (inner != fold))
        test = np.flatnonzero(inner == fold)
        assert_split(train, test, data['groups'], data['y'])
        if set(train) | set(test) != set(outer_train):
            raise ValueError('Inner fold does not partition the outer training set')
        splits.append((train, test))
    return outer_train, outer_test, splits


def svc(protocol, C, gamma, precomputed=True):
    settings = protocol['svm']
    if settings['probability'] is not False:
        raise ValueError('This protocol does not permit probability calibration')
    # In pinned sklearn 1.9, omitting the deprecated probability argument
    # explicitly takes the non-probabilistic path. Verify that state below.
    return SVC(C=C, gamma=gamma, kernel='precomputed' if precomputed else 'rbf',
               tol=settings['tol'], shrinking=settings['shrinking'],
               class_weight=settings['class_weight'],
               max_iter=settings['max_iter'], cache_size=settings['cache_size_mb'], random_state=42)


def checked_fit(model, X, y):
    with warnings.catch_warnings():
        warnings.simplefilter('error', ConvergenceWarning)
        model.fit(X, y)
    if model.fit_status_ != 0 or not np.array_equal(model.classes_, [0, 1]) or model._effective_probability is not False:
        raise ValueError('SVM failed to converge or has an unexpected class order')
    return model


def kernel_from_distances(distances, gamma):
    if gamma <= 0 or not np.isfinite(gamma):
        raise ValueError('Gamma must be positive and finite')
    return np.exp(-gamma * distances)


def choose_candidate(candidates):
    if not candidates or not all(np.isfinite(c['mean_balanced_accuracy']) for c in candidates):
        raise ValueError('Empty or non-finite parameter search')
    return min(candidates, key=lambda c: (-c['mean_balanced_accuracy'], c['C'], c['gamma']))


def search(distances, y, groups, splits, protocol, workers=4):
    """Only the provided split rows are used; excluded labels are never read."""
    for train, test in splits:
        assert_split(train, test, groups, y)
    C_values = [2.0 ** e for e in protocol['C_exponents_base2']]
    gammas = [2.0 ** e for e in protocol['gamma_exponents_base2']]

    def evaluate_gamma(gamma):
        kernel = kernel_from_distances(distances, gamma)
        candidates = []
        for C in C_values:
            scores = []
            iterations = []
            for train, test in splits:
                model = checked_fit(svc(protocol, C, gamma), kernel[np.ix_(train, train)], y[train])
                scores.append(float(balanced_accuracy_score(y[test], model.predict(kernel[np.ix_(test, train)]))))
                iterations.append(int(model.n_iter_[0]))
            candidates.append({'C': C, 'gamma': gamma, 'mean_balanced_accuracy': float(np.mean(scores)),
                               'fold_balanced_accuracy': scores, 'iterations': iterations})
        return candidates

    with ThreadPoolExecutor(max_workers=workers) as pool:
        candidates = [c for result in pool.map(evaluate_gamma, gammas) for c in result]
    candidates.sort(key=lambda c: (c['C'], c['gamma']))
    return choose_candidate(candidates), candidates


def metrics(y, prediction, scores):
    if len(y) == 0 or not (len(y) == len(prediction) == len(scores)) or set(y) != {0, 1}:
        raise ValueError('Metrics require aligned predictions and both classes')
    if not np.isfinite(scores).all() or not set(prediction) <= {0, 1}:
        raise ValueError('Invalid predictions or decision scores')
    tn, fp, fn, tp = confusion_matrix(y, prediction, labels=[0, 1]).ravel()
    return {'n': len(y), 'tn': int(tn), 'fp': int(fp), 'fn': int(fn), 'tp': int(tp),
            'sensitivity': float(tp / (tp + fn)), 'specificity': float(tn / (tn + fp)),
            'accuracy': float(accuracy_score(y, prediction)),
            'balanced_accuracy': float(balanced_accuracy_score(y, prediction)),
            'mcc': float(matthews_corrcoef(y, prediction)),
            'roc_auc': float(roc_auc_score(y, scores)),
            'average_precision': float(average_precision_score(y, scores))}


METRIC_NAMES = ('sensitivity', 'specificity', 'accuracy', 'balanced_accuracy', 'mcc', 'roc_auc', 'average_precision')


def summarize_oof(y, prediction, scores, outer):
    per_fold = [metrics(y[outer == i], prediction[outer == i], scores[outer == i]) for i in range(5)]
    pooled = metrics(y, prediction, scores)
    # Scores originate from different fitted models. Do not rank them together.
    del pooled['roc_auc'], pooled['average_precision']
    macro = {name: float(np.mean([m[name] for m in per_fold])) for name in METRIC_NAMES}
    return {'per_fold': per_fold, 'macro_mean': macro, 'pooled_threshold_metrics': pooled}


def group_bootstrap(data, prediction, scores, protocol):
    """Conditional intervals; whole groups sampled with replacement per fold."""
    settings = protocol['bootstrap']
    rng = np.random.default_rng(settings['seed'])
    members = []
    for fold in range(5):
        ids = np.flatnonzero(data['outer'] == fold)
        members.append([ids[data['groups'][ids] == group] for group in sorted(set(data['groups'][ids]))])
    samples = []
    rejected = 0
    for _ in range(settings['resamples']):
        selected = [np.concatenate([groups[i] for i in rng.integers(0, len(groups), len(groups))]) for groups in members]
        if any(set(data['y'][idx]) != {0, 1} for idx in selected):
            rejected += 1
            continue
        per_fold = [metrics(data['y'][idx], prediction[idx], scores[idx]) for idx in selected]
        samples.append([np.mean([m[name] for m in per_fold]) for name in METRIC_NAMES])
    if len(samples) < settings['resamples'] * 0.95:
        raise ValueError('Too many bootstrap resamples lack both classes')
    bounds = np.percentile(samples, [2.5, 97.5], axis=0)
    return {'method': settings, 'accepted': len(samples), 'rejected': rejected,
            'macro_mean_intervals': {name: [float(bounds[0, i]), float(bounds[1, i])] for i, name in enumerate(METRIC_NAMES)},
            'limitation': 'Conditional on these fitted models, fixed feature choices and folds; does not include retraining or protocol-selection uncertainty.'}


def export_model(path, model, X, train_ids, C, gamma, layer, protocol_hash):
    """Portable numeric artifact: contains no pickle or executable objects."""
    supports = X[model.support_]
    np.savez_compressed(path, support_vectors=supports, dual_coef=model.dual_coef_[0],
                        intercept=model.intercept_[0], classes=model.classes_, C=np.asarray(C), gamma=np.asarray(gamma),
                        support_record_ids=train_ids[model.support_], layer=np.asarray(layer),
                        feature_variant=np.asarray('primary'), feature_names=np.asarray(feature_names()),
                        protocol_sha256=np.asarray(protocol_hash))


def portable_scores(path, X):
    with np.load(path, allow_pickle=False) as model:
        return rbf_kernel(X, model['support_vectors'], gamma=float(model['gamma'])) @ model['dual_coef'] + float(model['intercept'])


def on_boundary(best, protocol):
    return {name: best[name] in (2.0 ** min(protocol[f'{name}_exponents_base2']),
                               2.0 ** max(protocol[f'{name}_exponents_base2'])) for name in ('C', 'gamma')}


def run_layer(layer, data, protocol, output, workers, protocol_hash):
    X, y, ids = data['X'], data['y'], data['ids']
    with threadpool_limits(limits=4):
        distances = euclidean_distances(X, squared=True)
    np.maximum(distances, 0, out=distances)
    np.fill_diagonal(distances, 0)
    prediction = np.full(len(y), -1, dtype=int)
    scores = np.full(len(y), np.nan)
    seen = np.zeros(len(y), dtype=int)
    fold_reports = []
    start = time.monotonic()
    for fold in range(5):
        train, test, splits = splits_for_outer(data, fold)
        t0 = time.monotonic()
        settings_count = len(protocol['C_exponents_base2']) * len(protocol['gamma_exponents_base2'])
        print(f'{layer} outer {fold+1}/5: tuning {settings_count} settings within training groups', flush=True)
        best, candidates = search(distances, y, data['groups'], splits, protocol, workers)
        kernel = kernel_from_distances(distances, best['gamma'])
        model = checked_fit(svc(protocol, best['C'], best['gamma']), kernel[np.ix_(train, train)], y[train])
        test_kernel = kernel[np.ix_(test, train)]
        prediction[test] = model.predict(test_kernel)
        scores[test] = model.decision_function(test_kernel)
        seen[test] += 1
        # Save each fold model for independent replay of held-out predictions.
        model_path = output / 'models' / f'{layer}_outer_{fold}.npz'
        export_model(model_path, model, X[train], ids[train], best['C'], best['gamma'], layer, protocol_hash)
        replay = portable_scores(model_path, X[test])
        error = float(abs(replay - scores[test]).max())
        if error > 1e-7 or not np.array_equal((replay > 0).astype(int), prediction[test]):
            raise ValueError('Exported outer model failed decision-score/prediction replay')
        result = {'outer_fold': fold, 'train_n': len(train), 'test_n': len(test),
                  'train_groups': len(set(data['groups'][train])), 'test_groups': len(set(data['groups'][test])),
                  'best': best, 'grid_boundary': on_boundary(best, protocol),
                  'metrics': metrics(y[test], prediction[test], scores[test]),
                  'support_vectors': len(model.support_), 'iterations': int(model.n_iter_[0]),
                  'export_max_score_error': error, 'seconds': time.monotonic() - t0}
        fold_reports.append(result)
        write_json(output / f'{layer}_outer_{fold}_search.json', candidates)
        write_json(output / f'{layer}_outer_{fold}_result.json', result)
        print(f'{layer} outer {fold+1}/5 complete ({result["seconds"]:.1f}s); held-out predictions saved', flush=True)
    if not np.all(seen == 1) or not np.isfinite(scores).all():
        raise ValueError('Each benchmark row must receive exactly one held-out prediction')
    predictions = [{'record_id':str(ids[i]), 'group_id':str(data['groups'][i]), 'outer_fold':int(data['outer'][i]),
                    'true_label':int(y[i]), 'predicted_label':int(prediction[i]), 'decision_score':float(scores[i])} for i in range(len(y))]
    write_csv(output / f'{layer}_held_out_predictions.csv', predictions)
    summary = summarize_oof(y, prediction, scores, data['outer'])
    summary['bootstrap'] = group_bootstrap(data, prediction, scores, protocol)
    summary['outer_folds'] = fold_reports
    print(f'{layer}: nested evaluation complete; selecting full-data model settings separately', flush=True)
    final_splits = [(np.flatnonzero(data['outer'] != i), np.flatnonzero(data['outer'] == i)) for i in range(5)]
    best, candidates = search(distances, y, data['groups'], final_splits, protocol, workers)
    # Direct RBF fitting creates the final reusable classifier; CV uses the
    # mathematically equivalent cached kernel, validated in unit tests.
    final_model = checked_fit(svc(protocol, best['C'], best['gamma'], precomputed=False), X, y)
    model_path = output / 'models' / f'{layer}_final.npz'
    export_model(model_path, final_model, X, ids, best['C'], best['gamma'], layer, protocol_hash)
    # Compare model serialization, not in-sample accuracy.
    direct_scores = final_model.decision_function(X)
    restored = portable_scores(model_path, X)
    error = float(abs(direct_scores - restored).max())
    # Direct LIBSVM accumulates the dual expansion differently from NumPy.
    # Large opposing coefficients amplify floating-point roundoff. 1e-6 is
    # 1000x below the solver's 1e-3 tolerance; predictions must still agree
    # exactly for every benchmark record, with no threshold adjustment.
    if error > 1e-6 or not np.array_equal((restored > 0).astype(int), final_model.predict(X)):
        raise ValueError('Final portable model does not match the fitted SVM')
    summary['final_model'] = {'best': best, 'grid_boundary': on_boundary(best, protocol),
                              'fit_n':len(y), 'support_vectors':len(final_model.support_),
                              'iterations':int(final_model.n_iter_[0]), 'export_max_score_error':error,
                              'export_score_tolerance':1e-6, 'export_prediction_disagreements':0,
                              'minimum_absolute_direct_score':float(abs(direct_scores).min()),
                              'note':'Full-data fit for future inference; its selection score is not a held-out performance estimate.'}
    write_json(output / f'{layer}_final_search.json', candidates)
    summary['seconds'] = time.monotonic() - start
    write_json(output / f'{layer}_summary.json', summary)
    print(f'{layer}: final model saved; total {summary["seconds"]:.1f}s', flush=True)
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--features', type=Path, default=DEFAULT_FEATURES)
    parser.add_argument('--prepared', type=Path, default=PREPARED)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--workers', type=int, default=4)
    args = parser.parse_args()
    if not 1 <= args.workers <= 8:
        parser.error('Use between 1 and 8 workers')
    if args.output.exists() and any(args.output.iterdir()):
        parser.error('Output must be a new or empty directory to preserve previous results')
    protocol = json.loads(PROTOCOL.read_text())
    protocol_hash = sha256(PROTOCOL)
    layers = load_inputs(args.features, args.prepared)
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / 'models').mkdir()
    report = {'started_utc': datetime.now(timezone.utc).isoformat(), 'protocol': protocol,
              'protocol_sha256':protocol_hash, 'feature_archive_sha256':sha256(args.features),
              'assignments_sha256':sha256(FEATURE_CHECKPOINT / 'evaluation_assignments.csv'),
              'source_sha256':{p.name:sha256(p) for p in sorted(HERE.glob('*.py'))},
              'git_head_at_start':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
              'source_note':'Source hashes identify the executed implementation if uncommitted at run start.',
              'environment':{'python':platform.python_version(), **{name:importlib.metadata.version(name) for name in ('numpy','scipy','scikit-learn','threadpoolctl')}},
              'workers':args.workers, 'status':'running', 'layers':{}}
    write_json(args.output / 'training_audit.json', report)
    with threadpool_limits(limits=1):
        for layer, data in layers.items():
            report['layers'][layer] = run_layer(layer, data, protocol, args.output, args.workers, protocol_hash)
            write_json(args.output / 'training_audit.json', report)
    if sha256(PROTOCOL) != protocol_hash:
        raise ValueError('Training protocol changed during the run')
    settings_count = len(protocol['C_exponents_base2']) * len(protocol['gamma_exponents_base2'])
    report.update(status='complete', completed_utc=datetime.now(timezone.utc).isoformat(),
                  historical_accuracy_reproduced=False, lentiMPRA_evaluated=False,
                  fit_count=2*(5*(settings_count*3+1)+settings_count*5+1))
    report['artifact_sha256'] = {str(p.relative_to(args.output)):sha256(p) for p in sorted(args.output.rglob('*'))
                                if p.is_file() and p.name != 'training_audit.json'}
    write_json(args.output / 'training_audit.json', report)
    print('Both classifiers trained; nested predictions, searches, intervals and numeric models saved.', flush=True)


if __name__ == '__main__':
    main()
