"""Numerical checks using hand cases, an independent scalar oracle and S2."""
from itertools import product
import json
import math
import random
import unittest
from unittest.mock import patch
import numpy as np
from common import HERE, reverse_complement
from features import components, pseknc, property_table, words, feature_names


def scalar_oracle(sequence, k, lag, weight):
    """Direct scalar transcription of equations 6–9, without feature helpers."""
    raw = json.loads((HERE / 'properties_s2.json').read_text())['raw']
    normalized = []
    for column in zip(*raw):
        mean = sum(column) / 16
        sd = math.sqrt(sum((x - mean) ** 2 for x in column) / 15)
        normalized.append([(x - mean) / sd for x in column])
    di = [''.join(x) for x in product('ACGT', repeat=2)]
    vocabulary = [''.join(x) for x in product('ACGT', repeat=k)]
    counts = [sum(sequence[i:i+k] == word for i in range(len(sequence) - k + 1)) for word in vocabulary]
    frequencies = [n / sum(counts) for n in counts]
    theta = []
    for j in range(1, lag + 1):
        squared = []
        for i in range(len(sequence) - j - 1):
            a, b = di.index(sequence[i:i+2]), di.index(sequence[i+j:i+j+2])
            squared.append(sum((p[a] - p[b]) ** 2 for p in normalized) / 6)
        theta.append(sum(squared) / len(squared))
    z = sum(frequencies) + weight * sum(theta)
    return np.asarray([f / z for f in frequencies] + [weight * t / z for t in theta])


class FeatureTests(unittest.TestCase):
    def test_normalization_matches_the_published_table(self):
        sample = property_table('sample')
        np.testing.assert_allclose(sample.mean(axis=0), 0, atol=1e-13)
        np.testing.assert_allclose(sample.std(axis=0, ddof=1), 1, atol=1e-13)
        self.assertLess(abs(sample - property_table('published_rounded')).max(), 0.005)
        self.assertGreater(abs(property_table('population') - property_table('published_rounded')).max(), 0.08)

    def test_homopolymer_has_no_correlation_component(self):
        for weight in (0.1, 0.4):
            result = pseknc('A' * 200, weight=weight)
            expected = np.zeros(4105)
            expected[0] = 1
            np.testing.assert_array_equal(result, expected)

    def test_hand_computed_pairing_and_denominator(self):
        # AACA: AA, AC, CA. Substitute scalar properties 0,1,2 in all six
        # columns. Lag 1 mean square = 1; lag 2 = 4. At w=.5, Z=3.5.
        table = np.zeros((16, 6))
        table[1] = 1   # AC
        table[4] = 2   # CA
        with patch('features.property_table', return_value=table):
            result = pseknc('AACA', k=1, lag=2, weight=0.5)
        np.testing.assert_allclose(result, [3/14, 1/14, 0, 0, 1/7, 4/7], rtol=0, atol=1e-15)

    def test_independent_scalar_oracle(self):
        rng = random.Random(42)
        for sequence in ('ACGTTGCAAAACGTACCTAG', ''.join(rng.choices('ACGT', k=200))):
            for weight in (0.1, 0.4):
                np.testing.assert_allclose(pseknc(sequence, weight=weight), scalar_oracle(sequence, 6, 9, weight), rtol=1e-13, atol=1e-15)

    def test_counting_modes_are_distinct_and_explicit(self):
        expected = {'overlapping': {'AA': 2/3, 'AC': 1/6, 'CA': 1/6},
                    'disjoint': {'AA': 2/3, 'CA': 1/3},
                    'per_word_nonoverlap': {'AA': 3/5, 'AC': 1/5, 'CA': 1/5}}
        for mode, nonzero in expected.items():
            frequencies, _ = components('AAAACAA', k=2, lag=1, counting=mode)
            self.assertEqual({w: float(f) for w, f in zip(words(2), frequencies) if f}, nonzero)

    def test_reverse_complement_permutation_and_theta(self):
        sequence = 'ACGTTGCAAAACGTACCTAG'
        forward, theta = components(sequence, k=3, lag=5)
        reverse, reverse_theta = components(reverse_complement(sequence), k=3, lag=5)
        lookup = {word: i for i, word in enumerate(words(3))}
        np.testing.assert_array_equal(forward, reverse[[lookup[reverse_complement(w)] for w in words(3)]])
        np.testing.assert_allclose(theta, reverse_theta, rtol=1e-14, atol=1e-14)

    def test_dimensions_and_invalid_inputs(self):
        self.assertEqual(len(feature_names()), 4105)
        self.assertEqual(feature_names()[4095:], ['frequency:TTTTTT'] + [f'theta:{i}' for i in range(1, 10)])
        for sequence in ('', 'acgt', 'ACGN', 'AA'):
            with self.assertRaises(ValueError):
                pseknc(sequence)
        for kwargs in ({'weight': -1}, {'weight': float('nan')}, {'k': 0}, {'lag': 199}, {'counting': 'unknown'}, {'normalization': 'unknown'}):
            with self.assertRaises(ValueError):
                pseknc('ACGT' * 50, **kwargs)


if __name__ == '__main__':
    unittest.main()
