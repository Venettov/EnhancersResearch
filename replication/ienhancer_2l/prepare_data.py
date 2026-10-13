#!/usr/bin/env python3
"""Prepare audited iEnhancer-2L inputs; no feature extraction or model training.

Run from any directory with Python 3.10+ (standard library only). The original
files stay unchanged. Outputs are derived from the reviewed sequence-label TSV.
"""
import argparse
import csv
import hashlib
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REVIEW = Path('reports/assets/2026-10-12_original_publications_review.json')
LABELS = Path('reports/assets/2026-10-12_original_publications_review_sequence_labels.tsv')
FILES = {'enhancer.cv.txt': 1484, 'non.cv.txt': 1484,
         'enhancer.ind.txt': 200, 'non.ind.txt': 200}
REFERENCES = ['bioinformatics_32_3_362.pdf',
              'bioinformatics_32_3_362_s1/Supp-S1.pdf',
              'bioinformatics_32_3_362_s1/Supp-S2.pdf']


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def fasta(path):
    records, header, sequence = [], None, []
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        if line.startswith('>'):
            if header is not None:
                records.append((header, ''.join(sequence).upper()))
            header, sequence = line[1:], []
        else:
            require(header is not None, f'{path.name}: sequence before FASTA header')
            sequence.append(line)
    if header is not None:
        records.append((header, ''.join(sequence).upper()))
    return records


def prepare(root, output):
    review = json.loads((root / REVIEW).read_text())
    hashes = {}
    for name in [*FILES, *REFERENCES]:
        payload = (root / name).read_bytes()
        hashes[name] = sha(payload)
        expected = review['inputs'][name]
        require(hashes[name] == expected['sha256'] and len(payload) == expected['bytes'],
                f'{name}: does not match reviewed bytes; restore the Git copy before proceeding')
    hashes[str(REVIEW)] = sha((root / REVIEW).read_bytes())
    hashes[str(LABELS)] = sha((root / LABELS).read_bytes())
    with (root / LABELS).open(newline='') as stream:
        labels = list(csv.DictReader(stream, delimiter='\t'))
    lookup = {(r['file'], int(r['row_1_based'])): r for r in labels}
    require(len(labels) == len(lookup) == 3368, 'Unexpected or duplicate crosswalk rows')
    benchmark, historical = [], []
    for name, expected_count in FILES.items():
        records = fasta(root / name)
        require(len(records) == expected_count, f'{name}: wrong record count')
        for row, (header, sequence) in enumerate(records, 1):
            require(len(sequence) == 200 and set(sequence) <= set('ACGT'),
                    f'{name}:{row}: expected 200 A/C/G/T bases')
            digest = sha(sequence.encode('ascii'))
            source = lookup[(name, row)]
            require(source['sequence_sha256'] == digest and source['header'] == header,
                    f'{name}:{row}: crosswalk does not match sequence/header')
            training = name.endswith('.cv.txt')
            label = source['S1_label' if training else 'S4_label'].replace('_', '-')
            require(label in {'strong', 'weak', 'non-enhancer'}, f'{name}:{row}: missing label')
            record = {'file': name, 'row_1_based': row, 'header': header,
                      'sequence': sequence, 'sequence_sha256': digest,
                      'class_label': label, 'is_enhancer': int(label != 'non-enhancer'),
                      'is_strong': '' if label == 'non-enhancer' else int(label == 'strong'),
                      'label_source': 'S1' if training else 'current iEnhancer-EL S4 via reviewed crosswalk',
                      'source_page': source['S1_page' if training else 'S4_page']}
            (benchmark if training else historical).append(record)
    require(Counter(r['class_label'] for r in benchmark) ==
            {'strong': 742, 'weak': 742, 'non-enhancer': 1484}, 'Incorrect benchmark labels')
    require(Counter(r['class_label'] for r in historical) ==
            {'strong': 100, 'weak': 100, 'non-enhancer': 200}, 'Incorrect historical-test labels')
    training_hashes = {r['sequence_sha256'] for r in benchmark}
    require(len(training_hashes) == 2968, 'Benchmark contains duplicate sequences')
    for record in historical:
        record['exact_training_overlap'] = int(record['sequence_sha256'] in training_hashes)
    overlaps = Counter(r['class_label'] for r in historical if r['exact_training_overlap'])
    require(overlaps == {'strong': 100}, 'Overlap differs from reviewed result')
    output.mkdir(parents=True, exist_ok=True)
    for filename, records in [('benchmark.csv', benchmark), ('legacy_test_diagnostic_only.csv', historical)]:
        with (output / filename).open('w', newline='') as stream:
            writer = csv.DictWriter(stream, fieldnames=records[0].keys(), lineterminator='\n')
            writer.writeheader()
            writer.writerows(records)
    audit = {'status': 'Data preparation only; no model trained or published accuracy reproduced.',
             'benchmark_rows': len(benchmark), 'benchmark_classes': dict(Counter(r['class_label'] for r in benchmark)),
             'legacy_test_rows': len(historical), 'exact_training_overlaps': sum(overlaps.values()),
             'overlap_classes': dict(overlaps), 'input_sha256': hashes,
             'output_sha256': {p.name: sha(p.read_bytes()) for p in sorted(output.glob('*.csv'))
                               if p.name in {'benchmark.csv', 'legacy_test_diagnostic_only.csv'}},
             'limits': ['The historical 400-record test is not independent.',
                        'Exact hash comparisons do not rule out near-duplicates, reverse complements, or overlapping loci.',
                        'Strong/weak labels are chromatin annotations, not reporter-activity measurements.']}
    (output / 'data_audit.json').write_text(json.dumps(audit, indent=2) + '\n')
    return audit


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT / 'replication/ienhancer_2l/output',
                        help='Directory for derived CSV files and audit; rerunning replaces these outputs.')
    args = parser.parse_args()
    try:
        result = prepare(ROOT, args.output)
    except (OSError, ValueError, KeyError) as error:
        parser.exit(1, f'STOP: {error}\n')
    print('PASS: 2,968 benchmark sequences: 742 strong, 742 weak, 1,484 non-enhancers.')
    print('Historical test: 400 records; 100 exact training overlaps (all strong).')
    print('Wrote benchmark.csv, legacy_test_diagnostic_only.csv, data_audit.json')
    print('No features calculated or model trained. Outputs:', args.output)
