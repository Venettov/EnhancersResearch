#!/usr/bin/env python3
"""Separate structural coordinates and sequence-dependent PseKNC rescaling."""
import argparse
import csv
from datetime import datetime, timezone
import html
import importlib.metadata
import json
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import time

import numpy as np
from sklearn.metrics.pairwise import euclidean_distances
from threadpoolctl import threadpool_limits

from common import HERE, ROOT, PREPARED, load_benchmark, sha256, write_csv, write_json
from features import components, feature_names
from compare_features import (REFERENCE, BOOT_METRICS, baseline_features, bootstrap_weights,
                              evaluate_svm, save_predictions, weighted_metrics_batch)
from train_svm import (DEFAULT_FEATURES, FEATURE_CHECKPOINT, array_hash, choose_candidate,
                       load_inputs, on_boundary, portable_scores, splits_for_outer, summarize_oof)

PROTOCOL = HERE / 'component_protocol.json'
ARMS = ('words', 'rescaled_words', 'words_structure', 'full')
LABELS = {'words': 'Word frequencies (F)', 'rescaled_words': 'Rescaled words (F/Z)',
          'words_structure': 'Words + structural terms [F,T]', 'full': 'Full PseKNC [F,T]/Z'}


def component_matrices(F, theta, weight):
    """No labels or population statistics; keep Z identical in both scaled arms."""
    F, theta = np.asarray(F, dtype=float), np.asarray(theta, dtype=float)
    if (F.ndim != 2 or theta.ndim != 2 or len(F) != len(theta) or
            not np.isfinite(F).all() or not np.isfinite(theta).all() or
            (F < 0).any() or (theta < 0).any() or
            not np.allclose(F.sum(axis=1), 1, atol=1e-12, rtol=0) or
            not np.isfinite(weight) or weight < 0):
        raise ValueError('Expected aligned nonnegative components, normalized frequencies and finite weight')
    T = weight * theta
    Z = F.sum(axis=1) + weight * theta.sum(axis=1)
    both = np.concatenate((F, T), axis=1)
    return {'words': F, 'rescaled_words': F / Z[:, None],
            'words_structure': both, 'full': both / Z[:, None]}, Z


def component_names(arm):
    names = feature_names()
    if arm == 'words':
        return names[:4096]
    if arm == 'rescaled_words':
        return [n.replace('frequency:', 'frequency_over_Z:') for n in names[:4096]]
    if arm == 'words_structure':
        return names[:4096] + [n.replace('theta:', 'weighted_theta:') for n in names[4096:]]
    if arm == 'full':
        return names  # Matches the frozen primary checkpoint's naming convention.
    raise ValueError('Unknown arm')


def feature_geometry(matrices, Z, settings, split=4096):
    rng = np.random.default_rng(settings['seed'])
    n = len(Z)
    i = rng.integers(0, n, settings['pairs'])
    j = (i + rng.integers(1, n, settings['pairs'])) % n
    result = {'Z_quantiles': dict(zip(['min','p05','median','p95','max'],
                                     np.quantile(Z, [0,.05,.5,.95,1]).tolist())),
              'sampled_distinct_record_pairs': len(i), 'seed': settings['seed']}
    for arm in ('words_structure', 'full'):
        X = matrices[arm]
        # Bound memory independently of the number of sampled pairs.
        distances = []
        for start in range(0, len(i), 256):
            delta = X[i[start:start+256]] - X[j[start:start+256]]
            distances.append(np.column_stack(((delta[:, :split]**2).sum(axis=1),
                                               (delta[:, split:]**2).sum(axis=1))))
        d = np.concatenate(distances)
        total = d.sum(axis=1)
        valid = total > 0
        result[arm] = {'word_mean_squared_distance': float(d[:,0].mean()),
                       'structure_mean_squared_distance': float(d[:,1].mean()),
                       'structure_share_of_total_squared_distance': float(d[:,1].sum()/total.sum()) if total.sum() else None,
                       'median_pair_structure_share': float(np.median(d[valid,1]/total[valid])) if valid.any() else None}
    return result


def contrasts_with_intervals(data, predictions, settings, contrasts):
    """Paired linear contrasts of mean fold metrics, using common group draws."""
    parts = bootstrap_weights(data, settings['resamples'], settings['seed'])
    valid = np.ones(settings['resamples'], dtype=bool)
    for idx, w in parts:
        valid &= (w[:,data['y'][idx] == 0].sum(axis=1) > 0)
        valid &= (w[:,data['y'][idx] == 1].sum(axis=1) > 0)
    if valid.sum() < .95 * settings['resamples']:
        raise ValueError('Too many invalid bootstrap draws')
    samples, observed = {}, {}
    for arm, (pred, score) in predictions.items():
        samples[arm] = np.mean([weighted_metrics_batch(data['y'][idx], pred[idx], score[idx], w[valid])
                                for idx, w in parts], axis=0)
        mean = summarize_oof(data['y'], pred, score, data['outer'])['macro_mean']
        observed[arm] = np.asarray([mean[k] for k in BOOT_METRICS])
    rows = {}
    for name, weights in contrasts.items():
        estimate = sum(v * observed[k] for k, v in weights.items())
        bounds = np.percentile(sum(v * samples[k] for k, v in weights.items()), [2.5,97.5], axis=0)
        rows[name] = {'coefficients': weights, 'metrics': {
            k: {'estimate': float(estimate[c]), 'ci95': bounds[:,c].tolist()} for c,k in enumerate(BOOT_METRICS)}}
        if len(weights) == 2:
            a,b = weights
            rows[name]['prediction_disagreements'] = int(np.count_nonzero(predictions[a][0] != predictions[b][0]))
    return {'accepted': int(valid.sum()), 'rejected': int((~valid).sum()), 'contrasts': rows,
            'arm_intervals': {a: {k: np.percentile(s[:,c],[2.5,97.5]).tolist()
                                  for c,k in enumerate(BOOT_METRICS)} for a,s in samples.items()}}


def verify_manifest(directory, manifest, key):
    for name, expected in manifest[key].items():
        if sha256(directory/name) != expected:
            raise ValueError(f'Changed reference artifact: {directory/name}')


def reuse_arm(data, layer, arm, source, output, method, svm_protocol):
    """Validate identity, train membership and every held-out score before reuse."""
    primary = arm == 'full'
    csv_path = source/f'{layer}_held_out_predictions.csv' if primary else source/'sixmer_only'/layer/'held_out_predictions.csv'
    with csv_path.open(newline='') as stream:
        rows = list(csv.DictReader(stream))
    if [r['record_id'] for r in rows] != list(data['ids']) or [r['group_id'] for r in rows] != list(data['groups']):
        raise ValueError('Reused prediction identity mismatch')
    for key, expected in [('true_label', data['y']), ('outer_fold', data['outer'])]:
        if not np.array_equal([int(r[key]) for r in rows], expected):
            raise ValueError('Reused labels/folds mismatch')
    pred = np.asarray([int(r['predicted_label']) for r in rows])
    scores = np.asarray([float(r['decision_score']) for r in rows])
    target = output/method/layer
    target.mkdir(parents=True)
    folds, paths = [], [csv_path]
    for fold in range(5):
        train, test, _ = splits_for_outer(data, fold)
        path = source/'models'/f'{layer}_outer_{fold}.npz' if primary else source/'sixmer_only'/layer/f'outer_{fold}_model.npz'
        result_path = source/f'{layer}_outer_{fold}_result.json' if primary else source/'sixmer_only'/layer/f'outer_{fold}_result.json'
        result = json.loads(result_path.read_text())
        with np.load(path, allow_pickle=False) as model:
            ids = list(model['support_record_ids'])
            if not set(ids) <= set(data['ids'][train]):
                raise ValueError('Reused support records leave training set')
            index = {r:i for i,r in enumerate(data['ids'])}
            np.testing.assert_array_equal(model['support_vectors'], data['X'][[index[r] for r in ids]])
            if list(model['feature_names']) != component_names(arm):
                raise ValueError('Reused feature order mismatch')
        replay = portable_scores(path, data['X'][test])
        error = float(np.max(abs(replay-scores[test])))
        if error > 1e-6 or not np.array_equal((replay > 0).astype(int), pred[test]):
            raise ValueError('Reused model replay failed')
        shutil.copy2(path, target/f'outer_{fold}_model.npz')
        paths += [path, result_path]
        folds.append({'outer_fold': fold, 'best': result['best'],
                      'grid_boundary': on_boundary(result['best'], svm_protocol),
                      'reused_from': str(path.relative_to(ROOT)), 'source_model_sha256': sha256(path),
                      'export_max_score_error': error})
        write_json(target/f'outer_{fold}_result.json', folds[-1])
    return pred, scores, folds, paths


def render_report(audit, output):
    summaries, contrast_rows, sections = [], [], []
    for layer, content in audit['layers'].items():
        sections.append('<h2>' + ('Enhancer versus non-enhancer' if layer == 'layer1' else 'Strong versus weak · known enhancers only') + '</h2>')
        for mode in ('retuned','fixed'):
            rows = []
            for arm in ARMS:
                result = content['methods'][arm+'__'+mode]
                m = result['metrics']['macro_mean']
                summaries.append({'layer': layer, 'mode': mode, 'arm': arm, **m,
                                  'boundary_folds': len(result['boundary_folds'])})
                rows.append(f'<tr><th>{LABELS[arm]}</th><td>{100*m["accuracy"]:.2f}%</td><td>{100*m["balanced_accuracy"]:.2f}%</td>'
                            f'<td>{m["roc_auc"]:.4f}</td><td>{m["mcc"]:.3f}</td><td>{len(result["boundary_folds"])}/5</td></tr>')
            sections.append(f'<h3>{"Inner-fold retuning" if mode == "retuned" else "Shared primary settings (diagnostic)"}</h3><div class="scroll"><table>'
                            '<tr><th>Features</th><th>Accuracy</th><th>Balanced accuracy</th><th>ROC AUC</th><th>MCC</th><th>Grid edge</th></tr>' + ''.join(rows) + '</table></div>')
            rows = []
            for name,c in content['inference'][mode]['contrasts'].items():
                a,b = c['metrics']['accuracy'], c['metrics']['roc_auc']
                for metric, value in c['metrics'].items():
                    contrast_rows.append({'layer':layer,'mode':mode,'contrast':name,'metric':metric,
                                          'estimate':value['estimate'],'ci95_low':value['ci95'][0],'ci95_high':value['ci95'][1]})
                rows.append(f'<tr><th>{name.replace("_"," ")}</th><td>{100*a["estimate"]:+.2f} [{100*a["ci95"][0]:+.2f}, {100*a["ci95"][1]:+.2f}]</td>'
                            f'<td>{b["estimate"]:+.4f} [{b["ci95"][0]:+.4f}, {b["ci95"][1]:+.4f}]</td></tr>')
            sections.append('<div class="scroll"><table><tr><th>Paired contrast</th><th>Accuracy change, pp [95% interval]</th><th>AUC change [95% interval]</th></tr>' + ''.join(rows) + '</table></div>')
        g = content['geometry']
        sections.append(f'<p>Per-sequence Z: median {g["Z_quantiles"]["median"]:.3f}; range {g["Z_quantiles"]["min"]:.3f}–{g["Z_quantiles"]["max"]:.3f}. '
                        f'Structural coordinates contribute {100*g["words_structure"]["structure_share_of_total_squared_distance"]:.1f}% of total sampled squared distance before rescaling '
                        f'and {100*g["full"]["structure_share_of_total_squared_distance"]:.1f}% after rescaling. This describes SVM input geometry, not measured DNA shape.</p>')
    write_csv(output/'component_summary.csv', summaries)
    write_csv(output/'component_contrasts.csv', contrast_rows)
    document = '''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Structural terms and rescaling · local analysis</title>
<style>body{margin:0;background:#f6f5ef;color:#183c45;font:16px/1.6 system-ui,sans-serif}main{max-width:1200px;margin:auto;padding:40px 24px}h1{line-height:1.2;font-size:2.6rem}h2{margin-top:3rem}a{color:#006f6d}.badge{background:#e9d5a7;padding:6px 12px;border-radius:6px}.scroll{overflow:auto;margin:20px 0}table{border-collapse:collapse;width:100%;background:white;font-size:14px}th,td{text-align:right;padding:11px;border-bottom:1px solid #dbe4e1;white-space:nowrap}th:first-child{text-align:left}tr:first-child{background:#183c45;color:white}code{overflow-wrap:anywhere}li{margin:.6rem 0}</style><main>
<span class="badge">Local research draft · not published</span><h1>What changes when structural terms and rescaling are separated?</h1>
<p>Ordinary six-letter DNA word frequencies previously performed better than full PseKNC for strong versus weak enhancers. That comparison removed two components at once. This four-arm experiment separates their effects on the reconstructed SVM pipeline.</p>
<p><b>F</b> = 4,096 word frequencies; <b>T</b> = nine sequence-derived property summaries multiplied by the original weight; <b>Z</b> = sum(F) + w × sum(theta). Rescaled words retain structural information through Z even though the nine coordinates are absent. These summaries describe patterns in a fixed dinucleotide-property table, not directly measured three-dimensional structures.</p>
<p>The four arms are F, F/Z, [F,T], and [F,T]/Z. The same sequence-specific Z is used in both rescaled arms. Retuning assesses the complete feature-and-tuning procedure. Shared primary settings hold C and gamma fixed within each outer fold; they favor the primary representation and provide a sensitivity diagnostic.</p>
<p><a href="interpretation.html">Plain-language interpretation and next steps</a> · <a href="component_summary.csv">Summary CSV</a> · <a href="component_contrasts.csv">Paired contrasts CSV</a> · <a href="component_audit.json">Complete audit</a> · <a href="protocol_snapshot.json">Protocol</a> · <a href="validation.json">Validation</a></p>'''
    document += ''.join(sections)
    document += '''<h2>Interpretation limits</h2><ul><li>All estimates use the same five grouped outer folds. Positive differences favor the added component; combined change is full minus ordinary words. Interaction is full − rescaled words − words with terms + ordinary words, a difference of performance differences.</li>
<li>Intervals use 1,000 paired whole-group bootstrap draws. They condition on fitted models and folds, exclude retraining and protocol-selection uncertainty, and are not corrected for multiple comparisons. Crossing zero does not establish equivalence.</li>
<li>The follow-up was designed after observing the earlier results on this benchmark. It does not independently confirm an advantage or establish a biological mechanism. The same numeric hyperparameter grid has different effective coverage at different feature scales; edge selections remain visible.</li>
<li>Original author code and published performance have not been reproduced exactly. No contaminated historical-test records or new lentiMPRA measurements were used. No replacement model or full-data final model was selected.</li></ul>'''
    document += f'<p>{audit["new_svm_fits"]:,} new SVM fits; {audit["new_outer_models"]} new outer-fold models. Existing reference models were verified and reused. Protocol SHA-256: <code>{audit["protocol_sha256"]}</code>.</p></main></html>'
    (output/'report.html').write_text(document)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--workers', type=int, default=4)
    args = parser.parse_args()
    output = args.output.resolve()
    if not 1 <= args.workers <= 8 or (output.exists() and any(output.iterdir())):
        parser.error('Use 1–8 workers and a new or empty output directory')
    protocol = json.loads(PROTOCOL.read_text())
    svm_path = HERE/'training_protocol.json'
    svm = json.loads(svm_path.read_text())
    old = HERE/protocol['existing_baselines']
    verify_manifest(REFERENCE, json.loads((REFERENCE/'checkpoint.json').read_text()), 'files_sha256')
    old_audit = json.loads((old/'comparison_audit.json').read_text())
    if old_audit['status'] != 'complete':
        raise ValueError('Previous comparison incomplete')
    verify_manifest(old, old_audit, 'artifact_sha256')
    layers = load_inputs()
    sequence_by_id = {r['record_id']:r['sequence'] for r in load_benchmark()}
    output.mkdir(parents=True, exist_ok=True)
    snapshot = output/'source_snapshot'
    snapshot.mkdir()
    for p in [*sorted(HERE.glob('*.py')), PROTOCOL, svm_path, HERE/'properties_s2.json']:
        shutil.copy2(p, snapshot/p.name)
    shutil.copy2(PROTOCOL, output/'protocol_snapshot.json')
    input_paths = [PREPARED/'benchmark.csv', DEFAULT_FEATURES, FEATURE_CHECKPOINT/'evaluation_assignments.csv',
                   FEATURE_CHECKPOINT/'features_audit.json', REFERENCE/'checkpoint.json', svm_path,
                   old/'comparison_audit.json']
    # Pin every reused model, prediction, result, and baseline matrix before any fit.
    input_paths += [p for p in (REFERENCE/'models').glob('*outer*.npz')]
    input_paths += list(REFERENCE.glob('*held_out_predictions.csv')) + list(REFERENCE.glob('*outer_*_result.json'))
    input_paths += list((old/'sixmer_only').rglob('*')) + list(old.glob('sixmer_only_*_features.npz'))
    inputs = {str(p.relative_to(ROOT)):sha256(p) for p in input_paths if p.is_file()}
    audit = {'status':'running', 'started_utc':datetime.now(timezone.utc).isoformat(),
             'protocol':protocol,'protocol_sha256':sha256(PROTOCOL), 'input_sha256':inputs,
             'source_sha256':{p.name:sha256(p) for p in snapshot.iterdir()},
             'environment':{'python':platform.python_version(), **{p:importlib.metadata.version(p) for p in ('numpy','scipy','scikit-learn','threadpoolctl')}},
             'git_head_at_start':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
             'git_status_at_start':subprocess.check_output(['git','status','--short'],cwd=ROOT,text=True),
             'workers':args.workers, 'layers':{}, 'new_svm_fits':0,'new_outer_models':0,
             'publication_status':'Local only; no push authorized', 'full_data_model_fitted':False}
    (output/'environment-lock.txt').write_text(subprocess.check_output([sys.executable,'-m','pip','freeze'],text=True))
    write_json(output/'component_audit.json', audit)
    print(f'Protocol frozen before new fits: {audit["protocol_sha256"]}', flush=True)
    start = time.monotonic()
    with threadpool_limits(limits=1):
        for layer, data in layers.items():
            raw = [sequence_by_id[r] for r in data['ids']]
            parts = [components(s) for s in raw]
            F = np.stack([p[0] for p in parts]); theta = np.stack([p[1] for p in parts])
            matrices, Z = component_matrices(F, theta, protocol['weights'][layer])
            np.testing.assert_array_equal(matrices['full'], data['X'])
            np.testing.assert_array_equal(F, baseline_features(raw,'sixmer_only')[0])
            with np.load(old/f'sixmer_only_{layer}_features.npz', allow_pickle=False) as saved:
                np.testing.assert_array_equal(F, saved['X'])
                np.testing.assert_array_equal(data['ids'], saved['ids'])
                np.testing.assert_array_equal(data['y'], saved['y'])
            np.savez_compressed(output/f'{layer}_components.npz', F=F, theta=theta, Z=Z, ids=data['ids'], y=data['y'])
            methods, predictions = {}, {'retuned':{},'fixed':{}}
            choices = [json.loads((REFERENCE/f'{layer}_outer_{i}_result.json').read_text())['best'] for i in range(5)]
            for arm in ARMS:
                X = matrices[arm]; changed = {**data,'X':X}
                distances = None
                for mode in ('retuned','fixed'):
                    method = arm+'__'+mode
                    reuse = arm == 'full' or (arm == 'words' and mode == 'retuned')
                    if reuse:
                        pred,scores,folds,_ = reuse_arm(changed, layer, arm, REFERENCE if arm == 'full' else old,
                                                        output, method, svm)
                        print(f'{method}/{layer}: all saved predictions replayed', flush=True)
                    else:
                        if distances is None:
                            with threadpool_limits(limits=4):
                                distances = euclidean_distances(X, squared=True)
                            np.maximum(distances,0,out=distances); np.fill_diagonal(distances,0)
                        pred,scores,folds = evaluate_svm(changed, distances, component_names(arm), method, layer, svm,
                                                        output,args.workers,audit['protocol_sha256'], choices if mode == 'fixed' else None)
                        audit['new_svm_fits'] += 5 if mode == 'fixed' else 5*(48*3+1)
                        audit['new_outer_models'] += 5
                    save_predictions(output,method,layer,data,pred,scores)
                    predictions[mode][arm] = (pred,scores)
                    methods[method] = {'origin':'verified reuse' if reuse else 'new fits',
                                       'feature_shape':list(X.shape), 'feature_array_sha256':array_hash(X),
                                       'metrics':summarize_oof(data['y'],pred,scores,data['outer']), 'folds':folds,
                                       'boundary_folds':[f['outer_fold'] for f in folds if any(f['grid_boundary'].values())]}
                    write_json(output/method/layer/'summary.json',methods[method])
                del distances
            inference = {mode:contrasts_with_intervals(data,predictions[mode],protocol['paired_bootstrap'],protocol['contrasts'])
                         for mode in ('retuned','fixed')}
            audit['layers'][layer] = {'n':len(data['y']),'methods':methods,'inference':inference,
                                     'geometry':feature_geometry(matrices,Z,protocol['geometry'])}
            write_json(output/'component_audit.json',audit)
            print(f'{layer}: four-arm contrasts and geometry saved',flush=True)
    if audit['new_svm_fits'] != protocol['expected_new_svm_fits'] or audit['new_outer_models'] != protocol['expected_new_outer_models']:
        raise ValueError('Unexpected fit count')
    if any(sha256(ROOT/p) != h for p,h in inputs.items()) or any(sha256(HERE/p) != h for p,h in audit['source_sha256'].items()):
        raise ValueError('Source or input changed during run')
    audit.update(status='complete', completed_utc=datetime.now(timezone.utc).isoformat(), seconds=time.monotonic()-start)
    render_report(audit,output)
    audit['artifact_sha256'] = {str(p.relative_to(output)):sha256(p) for p in sorted(output.rglob('*'))
                                if p.is_file() and p.name != 'component_audit.json'}
    write_json(output/'component_audit.json',audit)
    print(f'Complete: {audit["new_svm_fits"]} fits in {audit["seconds"]:.1f}s; {output/"report.html"}',flush=True)


if __name__ == '__main__':
    main()
