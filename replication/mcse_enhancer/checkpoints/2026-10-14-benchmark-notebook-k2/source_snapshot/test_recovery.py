"""Meaningful checks of sequence identity, grouping and author-code equivalence."""
import json
import random
import tempfile
import unittest
from pathlib import Path
import numpy as np

from common import HERE, read_fasta, read_labels, read_csv, verify_snapshot
from features import (GAP_FAMILIES, WIDTH, author_reference, basic_summaries,
                      feature_names, gap_counts, nonoverlap_words, notebook_block, words)
from prepare import check_groups, prepare


class FeatureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.reference = author_reference()

    def test_hand_calculated_summaries(self):
        self.assertEqual(basic_summaries('AAAACCGT'), [2, 4, 2, 37.5, -1 / 3, 3 / 5, 5 / 3])

    def test_nonoverlapping_semantics_preserved(self):
        values = nonoverlap_words('AAAACGT')
        self.assertEqual(values[4 + words(2).index('AA')], 2)
        self.assertEqual(values[20 + words(3).index('AAA')], 1)

    def test_gap_counts_hand_example(self):
        values = gap_counts('AACGT', 1, 1, 1)
        self.assertEqual(sum(values), 3)
        for w in ['AC', 'AG', 'CT']:
            self.assertEqual(values[words(2).index(w)], 1)

    def test_gap_windows_conserved_all_families(self):
        seq = 'ACGT' * 50
        for left, right in GAP_FAMILIES:
            for gap in range(1, 6):
                self.assertEqual(sum(gap_counts(seq, left, right, gap)), len(seq) - left - right - gap + 1)

    def test_author_equivalence_adversarial_and_random(self):
        rng = random.Random(20261014)
        sequences = ['AAAACGT', 'A' * 198 + 'GC', 'G' * 198 + 'AT', 'ACGT' * 50,
                     'AAAAAACCCCCCGGGGGGTTTTTT', ''.join(rng.choices('ACGT', k=200))]
        for seq in sequences:
            expected = self.reference['generateFeatures'](5, 3, seq, 173)
            self.assertEqual(expected[-1], 173)
            np.testing.assert_array_equal(notebook_block(seq), expected[:-1])

    def test_width_names_and_label_separation(self):
        names = feature_names()
        self.assertEqual(len(names), WIDTH)
        self.assertEqual(len(set(names)), WIDTH)
        a = self.reference['generateFeatures'](5, 3, 'ACGT' * 3, 0)
        b = self.reference['generateFeatures'](5, 3, 'ACGT' * 3, 1)
        self.assertEqual(a[:-1], b[:-1])
        self.assertNotEqual(a[-1], b[-1])

    def test_undefined_and_invalid_inputs_fail(self):
        for seq in ['', 'AAAA', 'GGGG', 'ACGN', 'acgt']:
            with self.assertRaises(ValueError):
                notebook_block(seq)


class DataTests(unittest.TestCase):
    def test_multiline_fasta_and_labels(self):
        with tempfile.TemporaryDirectory() as folder:
            p = Path(folder) / 'test'
            p.write_text('>repeated\nac\ngt\n>repeated\nTGCA\n')
            self.assertEqual(read_fasta(p), [('repeated', 'ACGT'), ('repeated', 'TGCA')])
            p.write_text('1\n0\n')
            self.assertEqual(read_labels(p, 2), [1, 0])
            with self.assertRaises(ValueError):
                read_labels(p, 3)

    def test_snapshot_tampering_rejected(self):
        import shutil
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / 'snapshot'
            shutil.copytree(HERE / 'vendor/DNA-Enhancers', source)
            (source / 'Dataset/train.txt').write_text('changed')
            with self.assertRaises(ValueError):
                verify_snapshot(source)
            with self.assertRaises(ValueError):
                prepare(source, Path(folder) / 'out')
            self.assertFalse((Path(folder) / 'out').exists())

    def test_full_preparation_and_group_leakage_guard(self):
        with tempfile.TemporaryDirectory() as folder:
            out = Path(folder) / 'prepared'
            audit = prepare(HERE / 'vendor/DNA-Enhancers', out)
            self.assertEqual(audit['train_rows'], 2968)
            self.assertEqual(audit['exact_test_train_overlaps'], 100)
            self.assertEqual(audit['evaluation_groups'], 2451)
            self.assertEqual(sum(len(x['syntax_errors']) for x in audit['notebooks'].values()), 8)
            rows = read_csv(out / 'train.csv')
            a = rows[0]
            b = next(r for r in rows if r['outer_fold'] != a['outer_fold'])
            b['group_id'] = a['group_id']
            with self.assertRaises(ValueError):
                check_groups(rows)


if __name__ == '__main__':
    unittest.main()
