"""Verify the pinned authors' files; export data and existing evaluation groups.

No upstream notebook is executed. Historical test labels are read only for QC.
"""
import argparse
import ast
from collections import Counter
import hashlib
import json
from pathlib import Path
import shutil

from common import (HERE, ROOT, check_file, read_csv, read_fasta, read_labels,
                    sha256, verify_snapshot, write_csv, write_json)


def notebook_syntax(source):
    results = {}
    for path in sorted(Path(source).glob('*.ipynb')):
        cells = json.loads(path.read_text())['cells']
        result = {'syntax_errors': [], 'omitted_magic_lines': [], 'saved_output_cells': 0}
        for i, cell in enumerate(cells):
            if cell['cell_type'] != 'code':
                continue
            result['saved_output_cells'] += bool(cell.get('outputs'))
            lines = ''.join(cell['source']).splitlines()
            # Ignore notebook timing/shell directives, preserving source line numbers.
            for j, line in enumerate(lines):
                if line.lstrip().startswith(('%', '!')):
                    result['omitted_magic_lines'].append({'cell': i, 'line': j + 1})
                    lines[j] = ''
            try:
                ast.parse('\n'.join(lines))
            except SyntaxError as error:
                result['syntax_errors'].append({'cell': i, 'line': error.lineno,
                                                'message': error.msg})
        results[path.name] = result
    return results


def check_groups(rows):
    """Prove outer/inner group isolation for the inherited assignments."""
    if set(int(r['outer_fold']) for r in rows) != set(range(5)):
        raise ValueError('Expected five outer folds')
    for outer in range(5):
        train = [r for r in rows if int(r['outer_fold']) != outer]
        test = [r for r in rows if int(r['outer_fold']) == outer]
        if {r['group_id'] for r in train} & {r['group_id'] for r in test}:
            raise ValueError('Outer group leakage')
        key = f'inner_fold_outer_{outer}'
        if any(int(r[key]) != -1 for r in test):
            raise ValueError('Outer test record has inner assignment')
        if set(int(r[key]) for r in train) != {0, 1, 2}:
            raise ValueError('Expected three inner folds')
        for inner in range(3):
            a = [r for r in train if int(r[key]) != inner]
            b = [r for r in train if int(r[key]) == inner]
            if {r['group_id'] for r in a} & {r['group_id'] for r in b}:
                raise ValueError('Inner group leakage')
            if any({int(r['label']) for r in part} != {0, 1} for part in [a, b, test]):
                raise ValueError('Split missing a binary class')


def prepare(source, output):
    source, output = Path(source), Path(output)
    manifest = verify_snapshot(source)
    # All crosswalks must retain the bytes accepted in the earlier checkpoint.
    inputs = manifest['local_inputs_sha256']
    for name, expected in inputs.items():
        check_file(ROOT / name, expected)
    legacy = ROOT / 'replication/ienhancer_2l/output/2026-10-13-preparation'
    benchmark = read_csv(legacy / 'benchmark.csv')
    historical = read_csv(legacy / 'legacy_test_diagnostic_only.csv')
    folds = read_csv(ROOT / 'replication/ienhancer_2l/checkpoints/2026-10-13-groups-features/evaluation_assignments.csv')
    by_id = {r['record_id']: r for r in folds}
    if len(by_id) != len(folds) or len(folds) != len(benchmark):
        raise ValueError('Evaluation crosswalk not one-to-one')
    train_seq = set()
    exported = {}
    for split, filename, original in [('train', 'train', benchmark), ('historical_test', 'ind', historical)]:
        records = read_fasta(source / f'Dataset/{filename}.txt')
        labels = read_labels(source / f'Dataset/{filename}_label.txt', len(records))
        if len(records) != len(original):
            raise ValueError('MCSE/legacy row count mismatch')
        rows = []
        for i, ((header, seq), label, legacy_row) in enumerate(zip(records, labels, original), 1):
            if seq != legacy_row['sequence'] or label != int(legacy_row['is_enhancer']):
                raise ValueError(f'MCSE/legacy sequence or label differs at {split}:{i}')
            if len(seq) != 200:
                raise ValueError('Expected 200-base sequences')
            record_id = legacy_row['file'] + ':' + legacy_row['row_1_based']
            digest = hashlib.sha256(seq.encode('ascii')).hexdigest()
            row = {'mcse_record_id': f'{split}:{i}', 'record_id': record_id,
                   'mcse_header': header, 'legacy_header': legacy_row['header'],
                   'sequence': seq, 'sequence_sha256': digest, 'label': label,
                   'legacy_class_label': legacy_row['class_label']}
            if split == 'train':
                train_seq.add(seq)
                fold = by_id[record_id]
                if digest != fold['sequence_sha256'] or row['legacy_class_label'] != fold['class_label']:
                    raise ValueError('Evaluation crosswalk identity mismatch')
                row.update({k: v for k, v in fold.items() if k == 'group_id' or 'fold' in k})
            else:
                row['exact_training_overlap'] = int(seq in train_seq)
                row['use'] = 'diagnostic_only_not_for_tuning_or_primary_evaluation'
            rows.append(row)
        exported[split] = rows
    check_groups(exported['train'])
    overlaps = [r for r in exported['historical_test'] if r['exact_training_overlap']]
    if len(overlaps) != 100 or Counter(r['legacy_class_label'] for r in overlaps) != {'strong': 100}:
        raise ValueError('Overlap findings differ from accepted provenance')
    # Finish validation before writing. Never overwrite an earlier run.
    output.mkdir(parents=True, exist_ok=False)
    vendor = HERE / 'vendor/DNA-Enhancers'
    for name in manifest['files']:
        destination = vendor / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        if destination.exists():
            check_file(destination, manifest['files'][name]['sha256'])
        else:
            shutil.copyfile(source / name, destination)
    write_csv(output / 'train.csv', exported['train'])
    write_csv(output / 'historical_test_diagnostic_only.csv', exported['historical_test'])
    audit = {
        'stage': 'data recovery and static code audit; no model trained',
        'source_commit': manifest['commit'], 'source_files_verified': len(manifest['files']),
        'train_rows': len(exported['train']), 'train_unique_sequences': len(train_seq),
        'train_labels': dict(Counter(r['label'] for r in exported['train'])),
        'historical_test_rows': len(exported['historical_test']),
        'historical_test_labels': dict(Counter(r['label'] for r in exported['historical_test'])),
        'exact_test_train_overlaps': len(overlaps),
        'overlap_legacy_classes': dict(Counter(r['legacy_class_label'] for r in overlaps)),
        'mcse_legacy_sequence_order_and_binary_labels_identical': True,
        'evaluation_groups': len({r['group_id'] for r in exported['train']}),
        'outer_folds': 5, 'inner_folds_per_outer_training_set': 3,
        'outer_and_inner_group_isolation_verified': True,
        'grouping_limit': 'Reduces specified similarity/locus leakage; not complete biological independence. Prior exploration of these folds makes future comparisons exploratory.',
        'notebooks': notebook_syntax(vendor),
        'input_sha256': inputs,
        'output_sha256': {p.name: sha256(p) for p in output.iterdir() if p.is_file()},
    }
    write_json(output / 'data_audit.json', audit)
    return audit


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=HERE / 'vendor/DNA-Enhancers')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    audit = prepare(args.source, args.output)
    print(json.dumps({k: v for k, v in audit.items() if k not in ['notebooks', 'input_sha256', 'output_sha256']}, indent=2))
