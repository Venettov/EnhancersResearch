"""Strict readers and hash checks for the MCSE recovery checkpoint."""
import csv
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def check_file(path, expected):
    if sha256(path) != expected:
        raise ValueError(f'Checksum mismatch: {path}')


def write_json(path, value):
    Path(path).write_text(json.dumps(value, indent=2, ensure_ascii=False) + '\n')


def read_csv(path):
    with Path(path).open(newline='') as handle:
        return list(csv.DictReader(handle))


def write_csv(path, rows):
    with Path(path).open('w', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator='\n')
        writer.writeheader()
        writer.writerows(rows)


def read_fasta(path):
    records = []
    header = None
    parts = []
    for line in Path(path).read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        if line.startswith('>'):
            if header is not None:
                records.append((header, ''.join(parts).upper()))
            header, parts = line[1:], []
        else:
            if header is None:
                raise ValueError('Sequence before FASTA header')
            parts.append(line)
    if header is not None:
        records.append((header, ''.join(parts).upper()))
    if not records or any(not s or set(s) - set('ACGT') for _, s in records):
        raise ValueError('Empty or non-ACGT sequence')
    return records


def read_labels(path, n):
    labels = [int(x.strip()) for x in Path(path).read_text().splitlines() if x.strip()]
    if len(labels) != n or set(labels) != {0, 1}:
        raise ValueError('Expected one binary label per record and both classes')
    return labels


def verify_snapshot(source):
    manifest = json.loads((HERE / 'source_manifest.json').read_text())
    for name, record in manifest['files'].items():
        check_file(Path(source) / name, record['sha256'])
    return manifest
