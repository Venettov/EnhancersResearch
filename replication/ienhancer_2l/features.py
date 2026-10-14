"""Explicit PseKNC reconstruction of Liu et al., equations 6–9.

This is not author code. See README for unresolved counting/rounding choices.
Property normalization uses the fixed 16-dinucleotide table, never sample labels
or benchmark-wide statistics. No learned preprocessing is performed here.
"""
from functools import lru_cache
from itertools import product
import json
import numpy as np
from common import HERE

COUNTING = ('overlapping', 'disjoint', 'per_word_nonoverlap')
NORMALIZATIONS = ('population', 'sample', 'published_rounded')


@lru_cache(maxsize=None)
def words(k):
    if not isinstance(k, int) or not 1 <= k <= 8:
        raise ValueError('k must be an integer between 1 and 8')
    return tuple(map(''.join, product('ACGT', repeat=k)))


@lru_cache(maxsize=None)
def property_table(normalization='sample'):
    if normalization not in NORMALIZATIONS:
        raise ValueError('Unknown property normalization')
    data = json.loads((HERE / 'properties_s2.json').read_text())
    if tuple(data['dinucleotides']) != words(2):
        raise ValueError('Unexpected dinucleotide order')
    raw = np.asarray(data['raw'], dtype=np.float64)
    if normalization == 'published_rounded':
        normalized = np.asarray(data['published_normalized'], dtype=np.float64)
    else:
        normalized = (raw - raw.mean(axis=0)) / raw.std(
            axis=0, ddof=0 if normalization == 'population' else 1)
    normalized.setflags(write=False)
    return normalized


def components(sequence, k=6, lag=9, counting='overlapping', normalization='sample'):
    if not isinstance(sequence, str) or not sequence or set(sequence) - set('ACGT'):
        raise ValueError('Expected a nonempty, uppercase A/C/G/T sequence')
    vocabulary = words(k)
    if not isinstance(lag, int) or lag < 1 or lag > len(sequence) - 2 or len(sequence) < k:
        raise ValueError('Require 1 <= lag <= length - 2 and k <= length')
    if counting not in COUNTING:
        raise ValueError('Unknown k-mer counting convention')
    counts = np.zeros(len(vocabulary), dtype=np.float64)
    index = {word: i for i, word in enumerate(vocabulary)}
    if counting == 'per_word_nonoverlap':
        # Python str.count: non-overlap within each word; different words can
        # cover the same positions. This is not a disjoint tiling of the DNA.
        for word in set(sequence[i:i+k] for i in range(len(sequence) - k + 1)):
            counts[index[word]] = sequence.count(word)
    else:
        stride = 1 if counting == 'overlapping' else k
        for i in range(0, len(sequence) - k + 1, stride):
            counts[index[sequence[i:i+k]]] += 1
    frequencies = counts / counts.sum()
    di_index = {word: i for i, word in enumerate(words(2))}
    properties = property_table(normalization)[
        [di_index[sequence[i:i+2]] for i in range(len(sequence) - 1)]]
    # Eq. 7 has L-j-1 pairs. Dinucleotides therefore begin at each position,
    # even though the Figure 2 caption uses the phrase "non-overlapping".
    theta = np.asarray([np.mean((properties[:-j] - properties[j:]) ** 2)
                        for j in range(1, lag + 1)], dtype=np.float64)
    return frequencies, theta


def combine(frequencies, theta, weight):
    if not np.isfinite(weight) or weight < 0:
        raise ValueError('Weight must be finite and nonnegative')
    denominator = frequencies.sum() + weight * theta.sum()
    return np.concatenate((frequencies, weight * theta)) / denominator


def pseknc(sequence, k=6, lag=9, weight=0.1, counting='overlapping', normalization='sample'):
    return combine(*components(sequence, k, lag, counting, normalization), weight)


def feature_names(k=6, lag=9):
    return [f'frequency:{word}' for word in words(k)] + [f'theta:{j}' for j in range(1, lag + 1)]
