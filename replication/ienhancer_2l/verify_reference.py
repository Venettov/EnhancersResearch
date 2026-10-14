#!/usr/bin/env python3
"""Verify every benchmark header against UCSC hg19, with resumable local receipts.

Queries only reference intervals from this public benchmark. Original sequences
are never uploaded. No assembly is inferred solely from a header or a sample.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import json
import time
import urllib.request
from pathlib import Path

from common import PREPARED, coordinates, digest, load_benchmark, reverse_complement, write_json


def verify(row, cache):
    chrom, start, end = coordinates(row['header'])
    url = f'https://api.genome.ucsc.edu/getData/sequence?genome=hg19;chrom={chrom};start={start};end={end}'
    path = cache / f'{chrom}_{start}_{end}.json'
    if path.exists():
        saved = json.loads(path.read_text())
    else:
        for attempt in range(3):
            try:
                request = urllib.request.Request(url, headers={'User-Agent': 'EnhancersResearch-reproduction/1.0'})
                with urllib.request.urlopen(request, timeout=30) as response:
                    payload = json.load(response)
                saved = {'url': url, 'retrieved_utc': datetime.now(timezone.utc).isoformat(), 'response': payload}
                write_json(path, saved)
                break
            except (OSError, ValueError):
                if attempt == 2:
                    raise
                time.sleep(2 ** attempt)
    payload = saved['response']
    if saved['url'] != url or any(payload.get(k) != v for k, v in
                               [('genome', 'hg19'), ('chrom', chrom), ('start', start), ('end', end)]):
        raise ValueError(f'Reference response coordinates do not match {row["header"]}')
    sequence = payload['dna'].upper()
    if len(sequence) != 200:
        raise ValueError('Reference response length mismatch')
    match = ('forward' if sequence == row['sequence'] else
             'reverse_complement' if reverse_complement(sequence) == row['sequence'] else 'mismatch')
    return {'record_id': row['record_id'], 'header': row['header'], 'assembly': 'hg19',
            'start_convention': 'zero-based, end-exclusive', 'sequence_sha256': row['sequence_sha256'],
            'reference_sha256': digest(sequence), 'match': match,
            'url': url, 'retrieved_utc': saved['retrieved_utc']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--prepared', type=Path, default=PREPARED)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    cache = args.output / 'reference_cache'
    cache.mkdir(parents=True, exist_ok=True)
    rows = load_benchmark(args.prepared)
    receipts = []
    with ThreadPoolExecutor(max_workers=3) as pool:
        for i, result in enumerate(pool.map(lambda row: verify(row, cache), rows), 1):
            receipts.append(result)
            if i % 100 == 0:
                print(f'Reference checks: {i}/{len(rows)}', flush=True)
    write_json(args.output / 'reference_receipts.json', receipts)
    mismatches = [r for r in receipts if r['match'] == 'mismatch']
    print(f'Checked {len(rows)} hg19 intervals; mismatches: {len(mismatches)}')
    if mismatches:
        raise SystemExit('STOP: coordinate verification incomplete; inspect mismatch receipts')


if __name__ == '__main__':
    main()
