#!/usr/bin/env python3
"""Build frozen evaluation groups and validated PseKNC reconstruction matrices."""
import argparse
from collections import Counter, defaultdict
import hashlib
import importlib.metadata
import json
from pathlib import Path
import platform
import subprocess
import numpy as np
from common import HERE, PREPARED, ROOT, load_benchmark, sha256, write_csv, write_json
from evaluation import group_records, nested_assignments, CLASSES
from features import components, combine, feature_names, property_table

VARIANTS = {
    'primary': ('overlapping', 'sample'),
    'disjoint': ('disjoint', 'sample'),
    'per_word_nonoverlap': ('per_word_nonoverlap', 'sample'),
    'published_rounded': ('overlapping', 'published_rounded'),
    'population': ('overlapping', 'population'),
}


def array_hash(array):
    return hashlib.sha256(np.ascontiguousarray(array, dtype='<f8').tobytes()).hexdigest()


def build(rows, receipts, output):
    output.mkdir(parents=True, exist_ok=True)
    policy_path = HERE / 'evaluation_policy.json'
    policy = json.loads(policy_path.read_text())
    table = json.loads((HERE / 'properties_s2.json').read_text())
    if sha256(ROOT / table['source']) != table['source_sha256']:
        raise ValueError('Supplement S2 differs from the transcribed source')
    groups, edges = group_records(rows, receipts, policy['max_locus_gap_bp'], policy['max_edit_distance'])
    assignments = nested_assignments(rows, groups, policy['outer_folds'], policy['inner_folds'], policy['seed'])
    write_csv(output / 'evaluation_assignments.csv', assignments)
    if edges:
        write_csv(output / 'group_edges.csv', edges)
    else:
        (output / 'group_edges.csv').write_text('left,right,reason,edit_distance,gap_bp\n')
    by_group = defaultdict(list)
    for row in rows:
        by_group[groups[row['record_id']]].append(row)
    group_summary = {'records': len(rows), 'groups': len(by_group),
                     'group_size_distribution': dict(sorted(Counter(map(len, by_group.values())).items())),
                     'largest_group': max(map(len, by_group.values())),
                     'mixed_class_groups': sum(len({r['class_label'] for r in members}) > 1 for members in by_group.values()),
                     'edges_by_reason': dict(Counter(e['reason'] for e in edges)),
                     'zero_distance_sequence_edges': sum(e['reason'] == 'sequence_similarity' and e['edit_distance'] == 0 for e in edges),
                     'reference_matches': dict(Counter(r['match'] for r in receipts)),
                     'outer_folds': [], 'inner_folds': {}}
    for fold in range(policy['outer_folds']):
        members = [r for r in assignments if r['outer_fold'] == fold]
        group_summary['outer_folds'].append({'fold': fold, 'records': len(members),
            'groups': len({r['group_id'] for r in members}), 'classes': dict(Counter(r['class_label'] for r in members))})
        group_summary['inner_folds'][str(fold)] = [dict(Counter(r['class_label'] for r in assignments
            if r[f'inner_fold_outer_{fold}'] == inner)) for inner in range(policy['inner_folds'])]
    # Validate every edge independently against the saved fold assignment.
    by_id = {a['record_id']: a for a in assignments}
    fold_keys = ['outer_fold'] + [f'inner_fold_outer_{i}' for i in range(policy['outer_folds'])]
    crossings = sum(any(by_id[e['left']][key] != by_id[e['right']][key] for key in fold_keys) for e in edges)
    if crossings:
        raise ValueError('Related records cross an evaluation boundary')
    group_summary['edges_crossing_any_outer_or_inner_boundary'] = crossings
    write_json(output / 'evaluation_audit.json', group_summary)
    print(f'Frozen {len(by_group)} groups for {len(rows)} records; boundary crossings: {crossings}', flush=True)

    ids = np.asarray([r['record_id'] for r in rows])
    enhancer = np.asarray([r['class_label'] != 'non-enhancer' for r in rows])
    first_labels = enhancer.astype(np.int64)
    second_labels = np.asarray([int(r['class_label'] == 'strong') for r in rows if r['class_label'] != 'non-enhancer'])
    names = np.asarray(feature_names())
    features = {}
    primary = None
    for variant, (counting, normalization) in VARIANTS.items():
        first = np.empty((len(rows), len(names)), dtype=np.float64)
        second_all = np.empty_like(first)
        for i, row in enumerate(rows):
            frequencies, theta = components(row['sequence'], counting=counting, normalization=normalization)
            first[i] = combine(frequencies, theta, 0.1)
            second_all[i] = combine(frequencies, theta, 0.4)
        second = second_all[enhancer]
        del second_all
        stats = {}
        for layer, matrix in [('layer1', first), ('layer2', second)]:
            if not np.isfinite(matrix).all() or (matrix < 0).any() or not np.allclose(matrix.sum(axis=1), 1, rtol=0, atol=1e-12):
                raise ValueError(f'Invalid feature matrix: {variant}/{layer}')
            stats[layer] = {'shape': list(matrix.shape), 'dtype': str(matrix.dtype),
                            'max_row_sum_error': float(abs(matrix.sum(axis=1) - 1).max()),
                            'array_sha256_le_float64': array_hash(matrix)}
        if primary is None:
            primary = (first.copy(), second.copy())
        for layer, matrix, baseline in [('layer1', first, primary[0]), ('layer2', second, primary[1])]:
            stats[layer]['max_absolute_difference_from_primary'] = float(abs(matrix - baseline).max())
            stats[layer]['rows_differing_from_primary_at_1e-12'] = int(np.count_nonzero(np.any(abs(matrix - baseline) > 1e-12, axis=1)))
        target = output / f'features_{variant}.npz'
        np.savez_compressed(target, X_layer1=first, y_layer1=first_labels, record_ids_layer1=ids,
                            X_layer2=second, y_layer2=second_labels, record_ids_layer2=ids[enhancer],
                            feature_names=names)
        with np.load(target, allow_pickle=False) as saved:
            if (not np.array_equal(saved['X_layer1'], first) or not np.array_equal(saved['X_layer2'], second)
                    or not np.array_equal(saved['record_ids_layer1'], ids)
                    or not np.array_equal(saved['record_ids_layer2'], ids[enhancer])
                    or not np.array_equal(saved['feature_names'], names)):
                raise ValueError('Matrix round-trip failed')
        features[variant] = {'counting': counting, 'normalization': normalization, 'file': target.name,
                             'file_sha256': sha256(target), **stats}
        print(f'Validated {variant}: layer I {first.shape}, layer II {second.shape}', flush=True)
    normalized = property_table('published_rounded')
    table_comparison = {mode: float(abs(property_table(mode) - normalized).max()) for mode in ('sample', 'population')}
    if table_comparison['sample'] > 0.005:
        raise ValueError('Recomputed normalization no longer agrees with rounded S2-2')
    report = {
        'status': 'Data preparation, grouping and explicitly specified feature reconstruction complete; no model trained.',
        'not_author_implementation': True, 'published_accuracy_reproduced': False,
        'parameters': {'k': 6, 'lambda': 9, 'layer1_weight': 0.1, 'layer2_weight': 0.4,
                       'dinucleotide_pairs': 'overlapping; L-j-1 pairs at lag j',
                       'feature_order': '4096 lexicographic A,C,G,T k-mers then theta_1..theta_9'},
        's2_max_difference_from_published_rounded': table_comparison,
        'evaluation': group_summary, 'features': features,
        'policy': policy, 'evaluation_policy_sha256': sha256(policy_path),
        'source_sha256': {p.name: sha256(p) for p in sorted(HERE.glob('*.py'))},
        'properties_s2_sha256': sha256(HERE / 'properties_s2.json'),
        'environment': {'python': platform.python_version(),
                        'numpy': importlib.metadata.version('numpy'), 'rapidfuzz': importlib.metadata.version('rapidfuzz')},
        'limitations': [
            'No author-produced feature vectors are available for an external numerical parity check.',
            'Overlapping k-mer counts are the project primary reconstruction, not a resolved claim about author code.',
            'Disjoint and per-word non-overlapping counts are preserved as sensitivity variants; none selected by accuracy.',
            'All variants follow equation 7 position-based dinucleotide pairing despite Figure 2 caption ambiguity.',
            'Two layers share the same evaluation groups; layer II includes only known benchmark enhancers.',
            'No SVM fitting, tuning, feature scaling, training on historical test data, or lentiMPRA transfer has occurred.'
        ]
    }
    write_json(output / 'features_audit.json', report)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--prepared', type=Path, default=PREPARED)
    parser.add_argument('--receipts', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    report = build(load_benchmark(args.prepared), json.loads(args.receipts.read_text()), args.output)
    report['benchmark_sha256'] = sha256(args.prepared / 'benchmark.csv')
    report['reference_receipts_sha256'] = sha256(args.receipts)
    report['git_head_at_run'] = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    report['note_about_git_head'] = 'Implementation was uncommitted during run; source_sha256 identifies the executed source bytes.'
    write_json(args.output / 'features_audit.json', report)


if __name__ == '__main__':
    main()
