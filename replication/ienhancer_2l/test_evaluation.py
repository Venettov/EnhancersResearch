"""Leakage-boundary, reference-integrity, and reproducible splitting checks."""
import copy
import random
import unittest
from common import digest, reverse_complement
from evaluation import (CLASSES, group_records, nested_assignments, sequence_distance,
                        validate_assignments, validate_receipts)


def row(rid, sequence, start, label='strong', chrom=1):
    return {'record_id': rid, 'sequence': sequence, 'sequence_sha256': digest(sequence),
            'header': f'CHR{chrom}_{start}_{start+200}', 'class_label': label}


def receipts(rows):
    # Synthetic fixtures test validation and grouping logic, not hg19 biology.
    return [{'record_id': r['record_id'], 'header': r['header'], 'assembly': 'hg19',
             'start_convention': 'zero-based, end-exclusive', 'sequence_sha256': digest(r['sequence']),
             'reference_sha256': digest(r['sequence']), 'match': 'forward'} for r in rows]


class EvaluationTests(unittest.TestCase):
    def test_exact_reverse_complement_and_transitive_sequence_groups(self):
        a = 'A' * 200
        b = 'C' * 40 + 'A' * 160
        c = 'C' * 80 + 'A' * 120
        records = [row('a', a, 0), row('b', b, 5000), row('c', c, 10000), row('rc', reverse_complement(c), 15000)]
        groups, edges = group_records(records, receipts(records), max_locus_gap=0)
        self.assertEqual(len(set(groups.values())), 1)
        self.assertFalse(any(e['left'] == 'a' and e['right'] == 'c' for e in edges))
        self.assertTrue(any(e['edit_distance'] == 0 for e in edges))

    def test_edit_threshold_and_shifted_sequence(self):
        self.assertEqual(sequence_distance('A'*200, 'A'*160+'C'*40), 40)
        self.assertEqual(sequence_distance('A'*200, 'A'*159+'C'*41), 41)
        rng = random.Random(13)
        original = ''.join(rng.choices('ACGT', k=200))
        shifted = original[1:] + 'A'
        self.assertGreater(sum(a != b for a, b in zip(original, shifted)), 100)
        self.assertLessEqual(sequence_distance(original, shifted), 2)

    def test_genomic_gap_boundary_and_chromosome(self):
        records = [row('a', 'A'*200, 0), row('b', 'C'*200, 1200),
                   row('c', 'AC'*100, 2401), row('d', 'AG'*100, 1200, chrom=2)]
        groups, edges = group_records(records, receipts(records))
        self.assertEqual(groups['a'], groups['b'])  # gap is exactly 1000
        self.assertNotEqual(groups['b'], groups['c'])  # gap 1001
        self.assertNotEqual(groups['b'], groups['d'])
        self.assertEqual([e['gap_bp'] for e in edges if e['reason'] == 'genomic_proximity'], [1000])

    def test_missing_mismatched_and_unverified_receipts_fail(self):
        records = [row('a', 'A'*200, 0)]
        with self.assertRaises(ValueError):
            validate_receipts(records, [])
        for key, value in [('assembly', 'hg18'), ('match', 'mismatch'), ('reference_sha256', 'wrong'), ('header', 'CHR1_1_201')]:
            bad = receipts(records)
            bad[0][key] = value
            with self.assertRaises(ValueError):
                group_records(records, bad)

    def test_nested_folds_are_stable_and_exclude_outer_test_rows(self):
        rng = random.Random(7)
        records = [row(str(i), ''.join(rng.choices('ACGT', k=200)), i*5000, CLASSES[i % 3]) for i in range(90)]
        groups, _ = group_records(records, receipts(records))
        # Keep a deliberately mixed-class group together.
        groups['0'] = groups['1']
        assignments = nested_assignments(records, groups)
        shuffled = records.copy()
        rng.shuffle(shuffled)
        regrouped, _ = group_records(shuffled, receipts(shuffled))
        regrouped['0'] = regrouped['1']
        self.assertEqual(groups, regrouped)
        repeated = nested_assignments(shuffled, regrouped)
        self.assertEqual(sorted(assignments, key=lambda r:r['record_id']), sorted(repeated, key=lambda r:r['record_id']))
        for r in assignments:
            self.assertEqual(r[f'inner_fold_outer_{r["outer_fold"]}'], -1)
        by_id = {r['record_id']:r for r in assignments}
        self.assertEqual(by_id['0']['outer_fold'], by_id['1']['outer_fold'])
        tampered = copy.deepcopy(assignments)
        tampered[0]['outer_fold'] = (tampered[0]['outer_fold'] + 1) % 5
        with self.assertRaises(ValueError):
            validate_assignments(tampered)
        tampered = copy.deepcopy(assignments)
        tampered[0][f'inner_fold_outer_{tampered[0]["outer_fold"]}'] = 0
        with self.assertRaisesRegex(ValueError, 'Outer test'):
            validate_assignments(tampered)
        tampered = copy.deepcopy(assignments)
        tampered[0]['outer_fold'] = -1
        with self.assertRaisesRegex(ValueError, 'Invalid outer'):
            validate_assignments(tampered)


if __name__ == '__main__':
    unittest.main()
