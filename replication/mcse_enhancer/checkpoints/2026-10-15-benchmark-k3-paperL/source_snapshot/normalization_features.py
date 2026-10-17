"""Literal Equation 7 denominator for the standalone 3-mer block only.

Other descriptors, word order, overlapping windows and row metadata are retained.
This is a normalization diagnostic, not a recovered published feature matrix.
"""
import itertools
import numpy as np
from feature_matrix import load_matrix as load_ilearn_matrix

VARIANT = 'k3_paperL_full'


def paper_word_frequencies(sequences, words):
    """Count overlapping triplets with integer base-4 codes; divide by full L."""
    canonical = [''.join(w) for w in itertools.product('ACGT', repeat=3)]
    if len(words) != 64 or set(words) != set(canonical):
        raise ValueError('Expected all 64 unique A/C/G/T triplets')
    order = [canonical.index(w) for w in words]
    values = []
    for sequence in sequences:
        if len(sequence) < 3 or set(sequence) - set('ACGT'):
            raise ValueError('Expected unambiguous DNA with at least three bases')
        codes = np.fromiter(('ACGT'.index(x) for x in sequence), dtype=np.int64)
        triplets = 16*codes[:-2] + 4*codes[1:-1] + codes[2:]
        counts = np.bincount(triplets, minlength=64)
        values.append(counts[order] / len(sequence))
    return np.asarray(values, dtype=np.float64)


def load_matrix(variant):
    if variant != VARIANT:
        raise ValueError('Normalization experiment requires k3_paperL_full')
    x,y,groups,ids,names,rows = load_ilearn_matrix('k3_full')
    mask = np.char.startswith(names, 'Kmer3:')
    if int(mask.sum()) != 64:
        raise ValueError('Missing standalone Kmer3 block')
    words = [n.split(':',1)[1] for n in names[mask]]
    x[:,mask] = paper_word_frequencies([r['sequence'] for r in rows], words)
    if x.shape != (2968,15217) or not np.isfinite(x).all():
        raise ValueError('Invalid normalization feature matrix')
    return x,y,groups,ids,names,rows
