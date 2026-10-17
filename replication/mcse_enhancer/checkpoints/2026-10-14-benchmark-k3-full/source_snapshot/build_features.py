"""Build the recoverable notebook feature block for training rows only."""
import argparse
import json
import platform
from pathlib import Path
import time
import numpy as np

from common import HERE, check_file, read_csv, sha256, write_json
from features import WIDTH, author_reference, feature_names, notebook_block


def build(prepared, output):
    prepared, output = Path(prepared), Path(output)
    audit = json.loads((prepared / 'data_audit.json').read_text())
    check_file(prepared / 'train.csv', audit['output_sha256']['train.csv'])
    rows = read_csv(prepared / 'train.csv')
    reference = author_reference()['generateFeatures']
    started = time.monotonic()
    matrix = np.asarray([notebook_block(r['sequence']) for r in rows], dtype=np.float64)
    if matrix.shape != (2968, WIDTH) or not np.isfinite(matrix).all():
        raise ValueError('Unexpected dimensions or nonfinite features')
    # Deterministic boundary cases and GC extremes; chosen without outcomes.
    indices = sorted({0, 1, 741, 742, 1483, 1484, 2967,
                      int(np.argmin(matrix[:, 3])), int(np.argmax(matrix[:, 3]))})
    for i in indices:
        original = reference(5, 3, rows[i]['sequence'], 987654321)
        if original[-1] != 987654321 or len(original) != WIDTH + 1:
            raise ValueError('Author label position differs')
        np.testing.assert_array_equal(matrix[i], np.asarray(original[:-1], dtype=np.float64))
    output.mkdir(parents=True, exist_ok=False)
    names = feature_names()
    np.savez_compressed(output / 'notebook_block_train.npz', X=matrix,
                        record_ids=np.asarray([r['record_id'] for r in rows]),
                        feature_names=np.asarray(names))
    # Separate 7-column view for later paper/notebook comparison, not a new model.
    np.savez_compressed(output / 'basic_summaries_train.npz', X=matrix[:, :7],
                        record_ids=np.asarray([r['record_id'] for r in rows]),
                        feature_names=np.asarray(names[:7]))
    result = {
        'status': 'Partial feature recovery; complete MCSE feature matrix and model not reproduced',
        'rows': len(rows), 'columns': WIDTH, 'dtype': 'float64',
        'component_widths': {'basic_summaries': 7, 'nonoverlapping_1_to_3mer_counts': 84, 'gapped_counts': 14800},
        'labels_in_feature_matrix': False, 'test_features_generated': False,
        'models_trained': 0, 'standardization_or_selection_fitted': False,
        'author_cell_zero_based': 15, 'author_parameters': {'kGap': 5, 'kTuple': 3},
        'author_reference_rows_zero_based': indices,
        'author_reference_exact_equality': True,
        'all_values_finite': True, 'python': platform.python_version(), 'numpy': np.__version__,
        'elapsed_seconds': time.monotonic() - started,
        'inputs_sha256': {'train.csv': sha256(prepared / 'train.csv'), 'data_audit.json': sha256(prepared / 'data_audit.json')},
        'implementation_sha256': {p.name: sha256(p) for p in [HERE / 'common.py', HERE / 'features.py', HERE / 'build_features.py']},
        'outputs_sha256': {p.name: sha256(p) for p in output.iterdir() if p.is_file()},
        'unrecovered_descriptors': ['DCC', 'PseKNC', 'SCPseDNC', 'PCPseDNC', 'iLearn Kmer'],
        'interpretation': 'Agreement with this notebook function does not establish the actual features used for the publication. The paper describes a much smaller NPCP concatenation, and the notebook merge cells are incomplete.',
    }
    write_json(output / 'features_audit.json', result)
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--prepared', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = build(args.prepared, args.output)
    print(json.dumps({k: result[k] for k in ['status', 'rows', 'columns', 'author_reference_exact_equality', 'models_trained', 'elapsed_seconds']}, indent=2))
