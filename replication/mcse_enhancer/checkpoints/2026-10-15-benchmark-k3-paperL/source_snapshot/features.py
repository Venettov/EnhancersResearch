"""Recover the pure-Python block in feature-notebook cell 15 (zero-based).

This is a notebook-compatible block, NOT the complete six-descriptor MCSE
input. The paper's NPCP description does not establish this 14,891-column
block. No labels, fitting, standardization, or statistical selection occur here.
"""
import ast
from collections import Counter
import itertools
import json
from pathlib import Path

from common import HERE, verify_snapshot

ALPHABET = 'ACGT'
GAP_FAMILIES = ((1, 1), (1, 2), (1, 3), (2, 1), (2, 2), (2, 3), (3, 1), (3, 2))
WIDTH = 14891
ORIGINAL_FUNCTIONS = (
    'kmers', 'pseudoKNC', 'zCurve', 'gcContent', 'cumulativeSkew', 'atgcRatio',
    'monoMonoKGap', 'monoDiKGap', 'monoTriKGap', 'diMonoKGap', 'diDiKGap',
    'diTriKGap', 'triMonoKGap', 'triDiKGap', 'generateFeatures',
)


def words(k):
    return [''.join(x) for x in itertools.product(ALPHABET, repeat=k)]


def validate_sequence(sequence):
    if not sequence or set(sequence) - set(ALPHABET):
        raise ValueError('Expected nonempty uppercase ACGT sequence')
    counts = Counter(sequence)
    if counts['G'] + counts['C'] == 0 or counts['A'] + counts['T'] == 0:
        raise ValueError('Original skew/ratio is undefined without both AT and GC')
    return counts


def basic_summaries(sequence):
    counts = validate_sequence(sequence)
    a, c, g, t = (counts[x] for x in ALPHABET)
    return [(a + g) - (c + t), (a + c) - (g + t), (a + t) - (c + g),
            (g + c) / (a + c + g + t) * 100.0,
            (g - c) / (g + c), (a - t) / (a + t), (a + t) / (g + c)]


def nonoverlap_words(sequence, max_k=3):
    # Preserve str.count semantics in the notebook, including repeated words.
    return [sequence.count(word) for k in range(1, max_k + 1) for word in words(k)]


def gap_counts(sequence, left, right, gap):
    """Same counts/order as the original nested loops, counting windows once."""
    width = left + gap + right
    counts = Counter(sequence[i:i + left] + sequence[i + left + gap:i + width]
                     for i in range(len(sequence) - width + 1))
    return [counts[word] for word in words(left + right)]


def notebook_block(sequence):
    values = basic_summaries(sequence) + nonoverlap_words(sequence)
    for left, right in GAP_FAMILIES:
        for gap in range(1, 6):
            values.extend(gap_counts(sequence, left, right, gap))
    if len(values) != WIDTH:
        raise ValueError('Unexpected feature width')
    return values


def feature_names():
    names = ['zcurve_x', 'zcurve_y', 'zcurve_z', 'gc_percent', 'gc_skew', 'at_skew', 'at_gc_ratio']
    names += [f'nonoverlap_{k}mer_{word}' for k in range(1, 4) for word in words(k)]
    names += [f'gap_left{left}_right{right}_g{gap}_{word}'
              for left, right in GAP_FAMILIES for gap in range(1, 6)
              for word in words(left + right)]
    return names


def author_reference(source=HERE / 'vendor/DNA-Enhancers'):
    """Load only inspected, hash-pinned pure functions, not notebook execution.

    Imports, file readers/writers, feature commands and model code are excluded.
    Used solely as an equivalence oracle; the optimized recovery lives above.
    """
    verify_snapshot(source)
    notebook = json.loads((Path(source) / 'Create_Feature_Descriptors.ipynb').read_text())
    tree = ast.parse(''.join(notebook['cells'][15]['source']))
    selected = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name in ORIGINAL_FUNCTIONS]
    if {n.name for n in selected} != set(ORIGINAL_FUNCTIONS):
        raise ValueError('Pinned reference function set differs')
    env = {'itertools': itertools, 'elements': ALPHABET}
    env.update({f'm{k}': list(itertools.product(ALPHABET, repeat=k)) for k in range(2, 6)})
    exec(compile(ast.Module(body=selected, type_ignores=[]), 'pinned_author_feature_functions', 'exec'), env)
    return env
