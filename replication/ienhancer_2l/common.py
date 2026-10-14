"""Shared provenance and sequence utilities for the reconstruction."""
import csv
import hashlib
import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PREPARED = HERE / 'output/2026-10-13-preparation'


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def digest(text):
    return hashlib.sha256(text.encode('ascii')).hexdigest()


def reverse_complement(sequence):
    return sequence.translate(str.maketrans('ACGT', 'TGCA'))[::-1]


def coordinates(header):
    match = re.fullmatch(r'CHR([0-9]+|X|Y)_([0-9]+)_([0-9]+)', header)
    if not match:
        raise ValueError(f'Unrecognized coordinate header: {header}')
    chrom, start, end = match.groups()
    if int(start) < 0 or int(end) - int(start) != 200:
        raise ValueError(f'Expected a 200-base interval: {header}')
    return 'chr' + chrom, int(start), int(end)


def load_benchmark(folder=PREPARED):
    """Accept only the immutable, already audited benchmark export."""
    folder = Path(folder)
    checkpoint = json.loads((HERE / 'checkpoints/2026-10-13-data-preparation.json').read_text())
    path = folder / 'benchmark.csv'
    if sha256(path) != checkpoint['data_audit']['output_sha256']['benchmark.csv']:
        raise ValueError('Benchmark export differs from the preparation checkpoint')
    with path.open(newline='') as stream:
        rows = list(csv.DictReader(stream))
    for row in rows:
        row['record_id'] = row['file'] + ':' + row['row_1_based']
        if digest(row['sequence']) != row['sequence_sha256']:
            raise ValueError('Sequence hash mismatch')
    return rows


def write_json(path, value):
    Path(path).write_text(json.dumps(value, indent=2, ensure_ascii=False) + '\n')


def write_csv(path, rows):
    rows = list(rows)
    if not rows:
        raise ValueError('Cannot infer fields from empty rows')
    with Path(path).open('w', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=rows[0], lineterminator='\n')
        writer.writeheader()
        writer.writerows(rows)
