"""Independently check saved recovery artifacts before any model consumes them."""
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np

from common import ROOT, check_file, read_csv, sha256, write_json
from features import GAP_FAMILIES, WIDTH, feature_names
from prepare import check_groups


def validate(prepared, features):
    prepared, features = Path(prepared), Path(features)
    data_audit = json.loads((prepared / 'data_audit.json').read_text())
    feature_audit = json.loads((features / 'features_audit.json').read_text())
    for name, expected in data_audit['input_sha256'].items():
        check_file(ROOT / name, expected)
    for name, expected in data_audit['output_sha256'].items():
        check_file(prepared / name, expected)
    for name, expected in feature_audit['inputs_sha256'].items():
        check_file(prepared / name, expected)
    for name, expected in feature_audit['outputs_sha256'].items():
        check_file(features / name, expected)
    rows = read_csv(prepared / 'train.csv')
    check_groups(rows)
    for row in rows:
        if hashlib.sha256(row['sequence'].encode('ascii')).hexdigest() != row['sequence_sha256']:
            raise ValueError('Sequence hash mismatch')
    with np.load(features / 'notebook_block_train.npz', allow_pickle=False) as saved:
        if set(saved.files) != {'X', 'record_ids', 'feature_names'}:
            raise ValueError('Unexpected arrays, possibly labels, in features')
        x = saved['X']
        if x.shape != (2968, WIDTH) or x.dtype != np.float64 or not np.isfinite(x).all():
            raise ValueError('Matrix shape, dtype or finiteness error')
        np.testing.assert_array_equal(saved['record_ids'], [r['record_id'] for r in rows])
        np.testing.assert_array_equal(saved['feature_names'], feature_names())
        # Recompute the seven simple values independently over every row.
        for i, row in enumerate(rows):
            s = row['sequence']
            a, c, g, t = [s.count(base) for base in 'ACGT']
            basic = [a + g - c - t, a + c - g - t, a + t - c - g,
                     (g + c) / len(s) * 100, (g - c) / (g + c),
                     (a - t) / (a + t), (a + t) / (g + c)]
            np.testing.assert_array_equal(x[i, :7], basic)
        # Every gapped window contributes exactly once to its family/gap block.
        offset = 7 + 84
        block_count = 0
        for left, right in GAP_FAMILIES:
            width = 4 ** (left + right)
            for gap in range(1, 6):
                block = x[:, offset:offset + width]
                if np.any(block < 0) or np.any(block != np.floor(block)):
                    raise ValueError('Gapped counts are not nonnegative integers')
                np.testing.assert_array_equal(block.sum(axis=1), np.full(len(rows), 201 - left - right - gap))
                offset += width
                block_count += 1
        if offset != WIDTH:
            raise ValueError('Unvalidated trailing columns')
        with np.load(features / 'basic_summaries_train.npz', allow_pickle=False) as basic:
            np.testing.assert_array_equal(basic['X'], x[:, :7])
            np.testing.assert_array_equal(basic['record_ids'], saved['record_ids'])
            np.testing.assert_array_equal(basic['feature_names'], saved['feature_names'][:7])
    return {'passed': True, 'rows_checked': len(rows), 'feature_columns': WIDTH,
            'all_basic_summaries_recomputed': True, 'gapped_count_blocks_checked_per_row': block_count,
            'saved_feature_row_ids_and_names_verified': True,
            'input_output_hashes_verified': True, 'saved_matrices_contain_no_labels': True,
            'audit_sha256': {'data_audit.json': sha256(prepared / 'data_audit.json'),
                             'features_audit.json': sha256(features / 'features_audit.json')}}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--prepared', type=Path, required=True)
    parser.add_argument('--features', type=Path, required=True)
    parser.add_argument('--report', type=Path, required=True)
    args = parser.parse_args()
    if args.report.exists():
        parser.error('Validation report already exists; choose a new path')
    result = validate(args.prepared, args.features)
    write_json(args.report, result)
    print(json.dumps(result, indent=2))
