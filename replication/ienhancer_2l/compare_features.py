#!/usr/bin/env python3
"""Run locally declared baseline/feature comparisons on the frozen grouped folds.

No full-data model is selected or replaced. Alternate feature identities are
explicit in every artifact. The original training implementation is reused.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
import csv
from datetime import datetime, timezone
import html
import importlib.metadata
import json
from pathlib import Path
import platform
import shutil
import subprocess
import time

import numpy as np
from sklearn.metrics import balanced_accuracy_score
from sklearn.metrics.pairwise import euclidean_distances
from threadpoolctl import threadpool_limits

from common import HERE, PREPARED, ROOT, load_benchmark, sha256, write_csv, write_json
from features import feature_names, words
from train_svm import (FEATURE_CHECKPOINT, DEFAULT_FEATURES, array_hash, assert_split, checked_fit, choose_candidate,
                       kernel_from_distances, load_inputs, metrics, on_boundary,
                       portable_scores, splits_for_outer, summarize_oof, svc)

PROTOCOL = HERE / 'comparison_protocol.json'
REFERENCE = HERE / 'checkpoints/2026-10-13-svm-training'
BOOT_METRICS = ('accuracy', 'balanced_accuracy', 'roc_auc')
LABELS = {
    'primary': 'Primary PseKNC (saved reference)',
    'majority': 'Majority class (no sequence)',
    'gc_only': 'GC content only',
    'sixmer_only': 'Ordinary overlapping 6-mers',
    'disjoint': 'Disjoint 6-mer windows',
    'per_word_nonoverlap': 'Per-word non-overlapping counts',
    'published_rounded': 'Rounded published property table',
    'population': 'Population SD for property table',
}


def baseline_features(sequences, method):
    """Per-sequence features only; no cohort statistics or labels are used."""
    if any(len(s) != 200 or set(s) - set('ACGT') for s in sequences):
        raise ValueError('Baselines require 200 A/C/G/T bases')
    if method == 'gc_only':
        return np.asarray([[(s.count('G') + s.count('C')) / 200] for s in sequences]), ['GC_fraction']
    if method != 'sixmer_only':
        raise ValueError('Unknown baseline feature method')
    vocabulary = words(6)
    index = {word: i for i, word in enumerate(vocabulary)}
    X = np.zeros((len(sequences), len(vocabulary)), dtype=np.float64)
    for row, sequence in enumerate(sequences):
        for start in range(195):
            X[row, index[sequence[start:start+6]]] += 1
    return X / 195, [f'frequency:{word}' for word in vocabulary]


def validate_variant(archive, layer, data, expected):
    X = archive[f'X_{layer}']
    if (list(archive['feature_names']) != feature_names() or
            not np.array_equal(archive[f'record_ids_{layer}'], data['ids']) or
            not np.array_equal(archive[f'y_{layer}'], data['y'])):
        raise ValueError('Variant feature order, record identity or labels differ')
    if list(X.shape) != expected['shape'] or array_hash(X) != expected['array_sha256_le_float64']:
        raise ValueError('Variant matrix differs from frozen feature checkpoint')
    if not np.isfinite(X).all() or (X < 0).any() or not np.allclose(X.sum(axis=1), 1, atol=1e-12, rtol=0):
        raise ValueError('Invalid variant values')
    return X


def load_reference(data, layer):
    """Validate identity and replay *all* saved held-out reference scores."""
    with (REFERENCE / f'{layer}_held_out_predictions.csv').open(newline='') as stream:
        rows = list(csv.DictReader(stream))
    if [r['record_id'] for r in rows] != list(data['ids']):
        raise ValueError('Reference prediction rows differ from benchmark')
    for key, expected in [('true_label', data['y']), ('outer_fold', data['outer'])]:
        if not np.array_equal([int(r[key]) for r in rows], expected):
            raise ValueError('Reference label or fold differs')
    if [r['group_id'] for r in rows] != list(data['groups']):
        raise ValueError('Reference prediction groups differ')
    prediction = np.asarray([int(r['predicted_label']) for r in rows])
    scores = np.asarray([float(r['decision_score']) for r in rows])
    choices, errors = [], []
    for fold in range(5):
        train, test, _ = splits_for_outer(data, fold)
        path = REFERENCE / 'models' / f'{layer}_outer_{fold}.npz'
        with np.load(path, allow_pickle=False) as model:
            if not set(model['support_record_ids']) <= set(data['ids'][train]):
                raise ValueError('Reference model contains non-training support records')
        replay = portable_scores(path, data['X'][test])
        error = float(abs(replay - scores[test]).max())
        if error > 1e-6 or not np.array_equal((replay > 0).astype(int), prediction[test]):
            raise ValueError('Reference model replay failed')
        errors.append(error)
        choices.append(json.loads((REFERENCE / f'{layer}_outer_{fold}_result.json').read_text())['best'])
    return prediction, scores, choices, errors


def majority_oof(data):
    predicted = np.full(len(data['y']), -1, dtype=int)
    scores = np.full(len(data['y']), np.nan)
    folds = []
    for fold in range(5):
        train, test, _ = splits_for_outer(data, fold)
        fraction = float(data['y'][train].mean())
        label = int(fraction > 0.5)
        predicted[test], scores[test] = label, fraction
        folds.append({'outer_fold': fold, 'train_n': len(train), 'test_n': len(test),
                      'training_positive_fraction': fraction, 'predicted_class': label,
                      'metrics': metrics(data['y'][test], predicted[test], scores[test])})
    return predicted, scores, folds


def export_comparison(path, model, X, ids, best, method, layer, names, protocol_hash):
    np.savez_compressed(path, support_vectors=X[model.support_], dual_coef=model.dual_coef_[0],
                        intercept=model.intercept_[0], classes=model.classes_,
                        C=np.asarray(best['C']), gamma=np.asarray(best['gamma']),
                        support_record_ids=ids[model.support_], layer=np.asarray(layer),
                        feature_variant=np.asarray(method), feature_names=np.asarray(names),
                        protocol_sha256=np.asarray(protocol_hash))


def comparison_search(distances, y, groups, splits, protocol, workers=4):
    """Same fits/results as train_svm.search, scheduled per individual fit.

    GC-only large-C fits can be much slower than other candidates. Sharing
    fixed kernels and distributing individual folds prevents a single gamma
    worker from serializing the slow tail. No candidate is pruned or changed.
    """
    for train, test in splits:
        assert_split(train, test, groups, y)
    Cs = [2.0**e for e in protocol['C_exponents_base2']]
    gammas = [2.0**e for e in protocol['gamma_exponents_base2']]
    kernels = {gamma: kernel_from_distances(distances, gamma) for gamma in gammas}
    jobs = [(C, gamma, fold) for C in sorted(Cs, reverse=True)
            for gamma in sorted(gammas, reverse=True) for fold in range(len(splits))]

    def fit_one(job):
        C, gamma, fold = job
        train, test = splits[fold]
        kernel = kernels[gamma]
        model = checked_fit(svc(protocol, C, gamma), kernel[np.ix_(train, train)], y[train])
        score = float(balanced_accuracy_score(y[test], model.predict(kernel[np.ix_(test, train)])))
        return job, (score, int(model.n_iter_[0]))

    with ThreadPoolExecutor(max_workers=workers) as pool:
        results = dict(pool.map(fit_one, jobs))
    candidates = []
    for C in sorted(Cs):
        for gamma in sorted(gammas):
            scores, iterations = zip(*(results[(C, gamma, fold)] for fold in range(len(splits))))
            candidates.append({'C': C, 'gamma': gamma, 'mean_balanced_accuracy': float(np.mean(scores)),
                               'fold_balanced_accuracy': list(scores), 'iterations': list(iterations)})
    return choose_candidate(candidates), candidates


def evaluate_svm(data, distances, names, method, layer, svm_protocol, output,
                 workers, protocol_hash, fixed_choices=None):
    target = output / method / layer
    target.mkdir(parents=True)
    prediction = np.full(len(data['y']), -1, dtype=int)
    scores = np.full(len(data['y']), np.nan)
    seen = np.zeros(len(data['y']), dtype=int)
    folds = []
    for fold in range(5):
        train, test, splits = splits_for_outer(data, fold)
        if fixed_choices is None:
            best, candidates = comparison_search(distances, data['y'], data['groups'], splits, svm_protocol, workers)
            write_json(target / f'outer_{fold}_search.json', candidates)
        else:
            best = {key: fixed_choices[fold][key] for key in ('C', 'gamma')}
        kernel = kernel_from_distances(distances, best['gamma'])
        model = checked_fit(svc(svm_protocol, best['C'], best['gamma']),
                            kernel[np.ix_(train, train)], data['y'][train])
        scores[test] = model.decision_function(kernel[np.ix_(test, train)])
        prediction[test] = model.predict(kernel[np.ix_(test, train)])
        seen[test] += 1
        path = target / f'outer_{fold}_model.npz'
        export_comparison(path, model, data['X'][train], data['ids'][train], best,
                          method, layer, names, protocol_hash)
        replay = portable_scores(path, data['X'][test])
        error = float(abs(replay - scores[test]).max())
        if error > 1e-6 or not np.array_equal((replay > 0).astype(int), prediction[test]):
            raise ValueError('Comparison model export failed held-out replay')
        folds.append({'outer_fold': fold, 'best': best, 'grid_boundary': on_boundary(best, svm_protocol),
                      'selection': 'inner-fold tuning' if fixed_choices is None else 'saved primary parameters',
                      'train_n': len(train), 'test_n': len(test),
                      'train_groups': len(set(data['groups'][train])), 'test_groups': len(set(data['groups'][test])),
                      'metrics': metrics(data['y'][test], prediction[test], scores[test]),
                      'support_vectors': len(model.support_), 'iterations': int(model.n_iter_[0]),
                      'export_max_score_error': error, 'export_prediction_disagreements': 0})
        write_json(target / f'outer_{fold}_result.json', folds[-1])
        print(f'{method}/{layer}: outer fold {fold+1}/5 saved', flush=True)
    if not np.all(seen == 1) or not np.isfinite(scores).all() or (prediction < 0).any():
        raise ValueError('Invalid held-out prediction coverage')
    return prediction, scores, folds


def save_predictions(output, method, layer, data, prediction, scores):
    target = output / method / layer
    target.mkdir(parents=True, exist_ok=True)
    write_csv(target / 'held_out_predictions.csv', [
        {'record_id': str(data['ids'][i]), 'group_id': str(data['groups'][i]),
         'outer_fold': int(data['outer'][i]), 'true_label': int(data['y'][i]),
         'predicted_label': int(prediction[i]), 'decision_score': float(scores[i])}
        for i in range(len(prediction))])


def bootstrap_weights(data, resamples, seed):
    """Integer row multiplicities; all members of each sampled group co-move."""
    rng = np.random.default_rng(seed)
    parts = []
    for fold in range(5):
        idx = np.flatnonzero(data['outer'] == fold)
        _, inverse = np.unique(data['groups'][idx], return_inverse=True)
        parts.append((idx, inverse, np.zeros((resamples, len(idx)), dtype=np.int64)))
    # Match the reference procedure's resample-then-fold random draw order.
    for sample in range(resamples):
        for _, inverse, weights in parts:
            n = int(inverse.max()) + 1
            counts = np.bincount(rng.integers(0, n, n), minlength=n)
            weights[sample] = counts[inverse]
    return [(idx, weights) for idx, _, weights in parts]


def weighted_metrics_batch(y, prediction, scores, weights):
    """Accuracy, balanced accuracy and tie-aware AUC for each bootstrap draw.

    This vectorized calculation is tested against sklearn on explicitly
    repeated rows, including ties and zero weights; it fits no model.
    """
    positive = weights * (y == 1)
    negative = weights * (y == 0)
    P, N = positive.sum(axis=1), negative.sum(axis=1)
    if (P == 0).any() or (N == 0).any():
        raise ValueError('Bootstrap draw lacks both classes')
    accuracy = (weights * (prediction == y)).sum(axis=1) / (P + N)
    balanced = .5 * ((positive * (prediction == 1)).sum(axis=1) / P +
                     (negative * (prediction == 0)).sum(axis=1) / N)
    order = np.argsort(scores, kind='stable')
    starts = np.r_[0, 1 + np.flatnonzero(np.diff(scores[order]) != 0)]
    pos_ties = np.add.reduceat(positive[:, order], starts, axis=1)
    neg_ties = np.add.reduceat(negative[:, order], starts, axis=1)
    negatives_below = np.cumsum(neg_ties, axis=1) - neg_ties
    auc = (pos_ties * (negatives_below + .5 * neg_ties)).sum(axis=1) / (P * N)
    return np.column_stack((accuracy, balanced, auc))


def paired_intervals(data, predictions, settings):
    parts = bootstrap_weights(data, settings['resamples'], settings['seed'])
    valid = np.ones(settings['resamples'], dtype=bool)
    for idx, weights in parts:
        valid &= (weights[:, data['y'][idx] == 0].sum(axis=1) > 0)
        valid &= (weights[:, data['y'][idx] == 1].sum(axis=1) > 0)
    if valid.sum() < .95 * settings['resamples']:
        raise ValueError('Too many bootstrap draws lack both classes')
    samples = {}
    for method, (prediction, scores) in predictions.items():
        samples[method] = np.mean([
            weighted_metrics_batch(data['y'][idx], prediction[idx], scores[idx], weights[valid])
            for idx, weights in parts], axis=0)
    result = {}
    for method, sample in samples.items():
        bounds = np.percentile(sample, [2.5, 97.5], axis=0)
        differences = np.percentile(sample - samples['primary'], [2.5, 97.5], axis=0)
        result[method] = {
            'macro_intervals': {name: bounds[:, i].tolist() for i, name in enumerate(BOOT_METRICS)},
            'paired_difference_from_primary_intervals': {name: differences[:, i].tolist() for i, name in enumerate(BOOT_METRICS)}}
    return {'accepted': int(valid.sum()), 'rejected': int((~valid).sum()), 'methods': result}


def method_label(method):
    base = method.split('__')[0]
    suffix = ' — retuned' if method.endswith('__retuned') else ' — fixed primary parameters' if '__fixed' in method else ''
    return LABELS[base] + suffix


def render_report(report, output):
    sections = []
    flat = []
    for layer, results in report['layers'].items():
        rows = []
        for method, result in results['methods'].items():
            m = result['metrics']['macro_mean']
            ci = result['bootstrap']['paired_difference_from_primary_intervals']['accuracy']
            delta = result['difference_from_primary']['accuracy']
            boundary = result.get('boundary_folds', [])
            rows.append(f'<tr><th>{html.escape(method_label(method))}</th><td>{100*m["accuracy"]:.2f}%</td>'
                        f'<td>{100*m["balanced_accuracy"]:.2f}%</td><td>{m["roc_auc"]:.3f}</td><td>{m["mcc"]:.3f}</td>'
                        f'<td>{100*delta:+.2f} [{100*ci[0]:+.2f}, {100*ci[1]:+.2f}]</td>'
                        f'<td>{result["prediction_disagreements_with_primary"]}</td>'
                        f'<td>{len(boundary)}/5</td></tr>')
            flat.append({'layer': layer, 'method': method, **m,
                         'accuracy_delta_vs_primary': delta,
                         'accuracy_delta_ci_low': ci[0], 'accuracy_delta_ci_high': ci[1],
                         'prediction_disagreements': result['prediction_disagreements_with_primary'],
                         'boundary_folds': len(boundary)})
        title = 'Enhancer versus non-enhancer' if layer == 'layer1' else 'Strong versus weak (known enhancers only)'
        sections.append(f'<h2>{title}</h2><p>{results["n"]:,} held-out sequences · same five grouped outer folds</p>'
                        '<div class="scroll"><table><thead><tr><th>Representation / model</th><th>Accuracy</th>'
                        '<th>Balanced accuracy</th><th>ROC AUC</th><th>MCC</th><th>Accuracy difference, pp [95% interval]</th>'
                        '<th>Changed labels</th><th>Grid edge</th></tr></thead><tbody>' + ''.join(rows) + '</tbody></table></div>')
    write_csv(output / 'comparison_summary.csv', flat)
    document = '''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>iEnhancer-2L · Local comparison results</title><style>
body{margin:0;background:#f6f5ef;color:#183c45;font:16px/1.6 system-ui,sans-serif}main{max-width:1320px;margin:auto;padding:42px 28px}
h1{font-size:clamp(1.8rem,4vw,3rem);line-height:1.2}h2{margin-top:2.5rem}a{color:#006f6d}p{max-width:1000px}.badge{background:#e9d5a7;padding:6px 12px;border-radius:8px}
.scroll{overflow-x:auto}table{border-collapse:collapse;background:white;width:100%;font-size:14px}th,td{padding:12px;text-align:right;border-bottom:1px solid #dbe4e1}
th:first-child{text-align:left;min-width:260px}thead{background:#183c45;color:white}tbody tr:nth-child(2n){background:#edf3f1}td{white-space:nowrap}
li{margin:.6rem 0}code{overflow-wrap:anywhere}footer{margin-top:3rem;border-top:1px solid #ccd8d5;padding-top:1rem;font-size:14px}</style><main>
<span class="badge">Local research draft · not published</span><h1>What do simpler features and alternate interpretations change?</h1>
<p>The reference model combines six-letter DNA word counts with nine DNA-property correlation terms (PseKNC).
These comparisons test whether simpler information performs similarly, and how the unresolved feature definitions affect the two classification tasks.</p>
<p>All entries use the same benchmark records and grouped folds. The primary reference is the previously saved evaluation.
New SVM settings are chosen only inside each outer training set. No historical test records or new lentiMPRA measurements enter these fits.</p>'''
    document += ''.join(sections)
    document += '''<h2>How to read these results</h2><ul>
<li>GC content is the fraction of DNA letters that are G or C. The ordinary 6-mer baseline uses only frequencies of six-letter words.
Majority class ignores DNA and always predicts the more frequent training label (ties choose 0).</li>
<li>Retuned variants use the same predeclared parameter search as the primary model. Fixed-parameter variants refit using the primary model's settings for each fold.
These answer different questions. Removing the PseKNC terms also removes its sequence-dependent denominator, so the ordinary baseline is not a clean test of the nine terms alone.</li>
<li>Accuracy differences are comparator minus primary, in percentage points (pp). Each 95% interval uses identical whole-group bootstrap resamples for both models.
They are conditional, pointwise exploratory intervals, without retraining or correction for multiple comparisons. An interval crossing zero does not prove equivalence.</li>
<li>Changed labels count the held-out predictions that disagree with primary, even when aggregate accuracy is similar.
ROC AUC is averaged within folds; scores from different trained models are never ranked together.</li>
<li>Grid edge counts folds where C or gamma reaches a search endpoint. Such cases limit conclusions about achievable performance.
Feature scales differ, so identical numeric grids do not impose identical effective regularization.</li>
<li>These comparisons were specified after viewing the primary results. They neither establish the original author implementation nor validate transfer to lentiMPRA.
No winning variant is selected and no full-data deployment model is replaced.</li></ul>
<h2>Files and reproducibility</h2><p><a href="comparison_summary.csv">Download the summary table</a> ·
<a href="comparison_audit.json">Complete audit and fold-level results</a> · <a href="protocol_snapshot.json">Frozen local comparison protocol</a></p>
<p>Each method/layer directory contains its held-out predictions, outer-fold numeric models, parameter searches (where tuned), and fold results.
The audit records original input hashes, source snapshots, environment versions and every result artifact's SHA-256.</p>
<p>Method reference: <a href="https://scikit-learn.org/stable/auto_examples/model_selection/plot_nested_cross_validation_iris.html" target="_blank" rel="noopener noreferrer">scikit-learn: nested cross-validation</a>.</p>'''
    document += f'<footer>Completed {html.escape(report["completed_utc"])} · Protocol SHA-256 <code>{report["protocol_sha256"]}</code><br>Local files only; publication requires review and agreement.</footer></main></html>'
    (output / 'report.html').write_text(document)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--prepared', type=Path, default=PREPARED)
    parser.add_argument('--features-dir', type=Path, default=DEFAULT_FEATURES.parent)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--workers', type=int, default=4)
    args = parser.parse_args()
    if not 1 <= args.workers <= 8:
        parser.error('Use 1 to 8 workers')
    if args.output.exists() and any(args.output.iterdir()):
        parser.error('Output must be new or empty to preserve earlier results')
    protocol = json.loads(PROTOCOL.read_text())
    svm_path = HERE / 'training_protocol.json'
    svm_protocol = json.loads(svm_path.read_text())
    checkpoint = json.loads((REFERENCE / 'checkpoint.json').read_text())
    for name, expected in checkpoint['files_sha256'].items():
        if sha256(REFERENCE / name) != expected:
            raise ValueError(f'Changed reference checkpoint: {name}')
    layers = load_inputs(args.features_dir / 'features_primary.npz', args.prepared)
    source_rows = load_benchmark(args.prepared)
    sequences = {r['record_id']: r['sequence'] for r in source_rows}
    feature_audit = json.loads((FEATURE_CHECKPOINT / 'features_audit.json').read_text())['features']
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / 'source_snapshot').mkdir()
    for p in [*sorted(HERE.glob('*.py')), PROTOCOL, svm_path, HERE / 'properties_s2.json']:
        shutil.copy2(p, args.output / 'source_snapshot' / p.name)
    shutil.copy2(PROTOCOL, args.output / 'protocol_snapshot.json')
    protocol_hash = sha256(PROTOCOL)
    inputs = {str(p.relative_to(ROOT)): sha256(p) for p in [
        args.prepared / 'benchmark.csv', FEATURE_CHECKPOINT / 'evaluation_assignments.csv',
        FEATURE_CHECKPOINT / 'features_audit.json', REFERENCE / 'checkpoint.json', svm_path]}
    for variant in ['primary', *protocol['sensitivity_variants']]:
        p = args.features_dir / f'features_{variant}.npz'
        inputs[str(p.relative_to(ROOT))] = sha256(p)
    report = {'status': 'running', 'started_utc': datetime.now(timezone.utc).isoformat(),
              'protocol': protocol, 'protocol_sha256': protocol_hash, 'input_sha256': inputs,
              'git_head_at_start': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
              'git_status_at_start': subprocess.check_output(['git', 'status', '--short'], cwd=ROOT, text=True),
              'source_sha256': {p.name: sha256(p) for p in (args.output / 'source_snapshot').iterdir()},
              'environment': {'python': platform.python_version(), **{p: importlib.metadata.version(p)
                              for p in ('numpy', 'scipy', 'scikit-learn', 'threadpoolctl')}},
              'workers': args.workers, 'layers': {}, 'svm_fit_count': 0,
              'scheduling': 'Individual inner fits share fixed kernels; equivalent to original gamma-batched search, verified in tests.',
              'publication_status': 'Local only. No push authorized.'}
    write_json(args.output / 'comparison_audit.json', report)
    (args.output / 'environment-lock.txt').write_text(subprocess.check_output(
        [str(ROOT / '.venv/bin/python'), '-m', 'pip', 'freeze'], text=True))
    started = time.monotonic()
    print(f'Comparison protocol frozen before fits: {protocol_hash}', flush=True)
    with threadpool_limits(limits=1):
        for layer, data in layers.items():
            ref_pred, ref_scores, choices, replay_errors = load_reference(data, layer)
            predictions = {'primary': (ref_pred, ref_scores)}
            methods = {'primary': {'metrics': summarize_oof(data['y'], ref_pred, ref_scores, data['outer']),
                                   'reference_replay_max_errors': replay_errors,
                                   'boundary_folds': [i for i, best in enumerate(choices) if any(on_boundary(best, svm_protocol).values())]}}
            save_predictions(args.output, 'primary', layer, data, ref_pred, ref_scores)
            pred, scores, folds = majority_oof(data)
            predictions['majority'] = (pred, scores)
            methods['majority'] = {'metrics': summarize_oof(data['y'], pred, scores, data['outer']), 'folds': folds}
            save_predictions(args.output, 'majority', layer, data, pred, scores)
            for variant in ['gc_only', 'sixmer_only', *protocol['sensitivity_variants']]:
                if variant in ('gc_only', 'sixmer_only'):
                    X, names = baseline_features([sequences[i] for i in data['ids']], variant)
                    np.savez_compressed(args.output / f'{variant}_{layer}_features.npz', X=X,
                                        ids=data['ids'], y=data['y'], feature_names=np.asarray(names))
                    modes = [('retuned', None)]
                else:
                    with np.load(args.features_dir / f'features_{variant}.npz', allow_pickle=False) as archive:
                        X = validate_variant(archive, layer, data, feature_audit[variant][layer])
                    names = feature_names()
                    modes = [('retuned', None), ('fixed_primary_parameters', choices)]
                print(f'{variant}/{layer}: verified features {X.shape}', flush=True)
                with threadpool_limits(limits=4):
                    distances = euclidean_distances(X, squared=True)
                np.maximum(distances, 0, out=distances)
                np.fill_diagonal(distances, 0)
                for mode, fixed in modes:
                    method = variant if variant in ('gc_only', 'sixmer_only') else variant + '__' + mode
                    changed = {**data, 'X': X}
                    pred, scores, folds = evaluate_svm(changed, distances, names, method, layer, svm_protocol,
                                                       args.output, args.workers, protocol_hash, fixed)
                    predictions[method] = (pred, scores)
                    methods[method] = {'feature_shape': list(X.shape), 'feature_array_sha256': array_hash(X),
                                       'metrics': summarize_oof(data['y'], pred, scores, data['outer']), 'folds': folds,
                                       'boundary_folds': [f['outer_fold'] for f in folds if any(f['grid_boundary'].values())]}
                    save_predictions(args.output, method, layer, data, pred, scores)
                    grid_size = len(svm_protocol['C_exponents_base2']) * len(svm_protocol['gamma_exponents_base2'])
                    report['svm_fit_count'] += 5 if fixed is not None else 5 * (grid_size * 3 + 1)
                    write_json(args.output / method / layer / 'summary.json', methods[method])
                del distances
            print(f'{layer}: computing paired whole-group bootstrap intervals', flush=True)
            intervals = paired_intervals(data, predictions, protocol['paired_bootstrap'])
            for method, result in methods.items():
                result['bootstrap'] = intervals['methods'][method]
                result['difference_from_primary'] = {name: result['metrics']['macro_mean'][name] - methods['primary']['metrics']['macro_mean'][name]
                                                      for name in methods['primary']['metrics']['macro_mean']}
                result['prediction_disagreements_with_primary'] = int(np.count_nonzero(predictions[method][0] != ref_pred))
                write_json(args.output / method / layer / 'summary.json', result)
            report['layers'][layer] = {'n': len(data['y']), 'methods': methods,
                                       'bootstrap_accepted': intervals['accepted'], 'bootstrap_rejected': intervals['rejected']}
            write_json(args.output / 'comparison_audit.json', report)
    if sha256(PROTOCOL) != protocol_hash or any(sha256(ROOT / p) != h for p, h in inputs.items()):
        raise ValueError('Protocol or inputs changed during comparisons')
    if any(sha256(HERE / name) != h for name, h in report['source_sha256'].items()):
        raise ValueError('Source changed during comparisons')
    report.update(status='complete', completed_utc=datetime.now(timezone.utc).isoformat(),
                  seconds=time.monotonic()-started, outer_svm_models_saved=100,
                  majority_folds_evaluated=10, published_accuracy_reproduced=False,
                  lentiMPRA_evaluated=False, model_selected_for_deployment=False)
    render_report(report, args.output)
    report['artifact_sha256'] = {str(p.relative_to(args.output)): sha256(p)
                                for p in sorted(args.output.rglob('*')) if p.is_file() and p.name != 'comparison_audit.json'}
    write_json(args.output / 'comparison_audit.json', report)
    print(f'Complete: {report["svm_fit_count"]} SVM fits, local report {args.output / "report.html"}', flush=True)


if __name__ == '__main__':
    main()
