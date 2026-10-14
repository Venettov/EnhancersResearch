"""Rebuild the full benchmark's saved groups from original data, offline."""
import csv
import json
import tempfile
import unittest
from pathlib import Path
from common import HERE, ROOT, load_benchmark
from prepare_data import prepare
from evaluation import group_records, nested_assignments


class SavedCheckpointTests(unittest.TestCase):
    def test_full_benchmark_reproduces_saved_groups_and_folds(self):
        checkpoint = HERE / 'checkpoints/2026-10-13-groups-features'
        with tempfile.TemporaryDirectory() as temp:
            prepare(ROOT, Path(temp))
            rows = load_benchmark(Path(temp))
        receipts = json.loads((checkpoint / 'reference_receipts.json').read_text())
        policy = json.loads((HERE / 'evaluation_policy.json').read_text())
        groups, edges = group_records(rows, receipts, policy['max_locus_gap_bp'], policy['max_edit_distance'])
        actual = nested_assignments(rows, groups, policy['outer_folds'], policy['inner_folds'], policy['seed'])
        with (checkpoint / 'evaluation_assignments.csv').open(newline='') as stream:
            expected = list(csv.DictReader(stream))
        self.assertEqual([{key:str(value) for key,value in row.items()} for row in actual], expected)
        with (checkpoint / 'group_edges.csv').open(newline='') as stream:
            expected_edges = list(csv.DictReader(stream))
        self.assertEqual([{key:str(value) for key,value in row.items()} for row in edges], expected_edges)
        self.assertEqual(len(set(groups.values())), 2451)
        self.assertEqual(len(actual), 2968)
        self.assertFalse(any('ind.txt' in r['record_id'] for r in actual))


if __name__ == '__main__':
    unittest.main()
