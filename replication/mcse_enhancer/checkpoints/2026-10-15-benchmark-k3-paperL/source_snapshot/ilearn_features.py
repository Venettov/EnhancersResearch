"""Pinned iLearn descriptor recovery; original functions, explicit metadata removal."""
import ast
from collections import Counter
import itertools
import json
import re
import sys
import numpy as np

from common import HERE, check_file

VENDOR = HERE / 'vendor/iLearn'
METHODS = ('DCC', 'PseKNC', 'SCPseDNC', 'PCPseDNC', 'Kmer2', 'Kmer3')
WIDTHS = (150, 66, 28, 18, 16, 64)


def load_reference():
    manifest = json.loads((HERE / 'ilearn_source_manifest.json').read_text())
    for name, item in manifest['files'].items():
        check_file(VENDOR / name, item['sha256'])
    properties_path = HERE / 'ilearn_properties.json'
    check_file(properties_path, manifest['derived_properties_sha256'])
    properties = json.loads(properties_path.read_text())
    modules = {}
    for name in ['ACC', 'Pse', 'Kmer']:
        tree = ast.parse((VENDOR / f'descnucleotide/{name}.py').read_text())
        # Only inspected function definitions and literal index constants. No CLI,
        # wildcard imports, filesystem operations, sys.path edits or pickle loads.
        allowed = [n for n in tree.body if isinstance(n, ast.FunctionDef)]
        if name != 'Kmer':
            allowed += [n for n in tree.body if isinstance(n, ast.Assign) and
                        all(isinstance(t, ast.Name) and t.id in ['myDiIndex', 'myTriIndex', 'baseSymbol'] for t in n.targets)]
        env = {'re': re, 'sys': sys, 'itertools': itertools, 'Counter': Counter}
        exec(compile(ast.Module(body=allowed, type_ignores=[]), f'pinned_iLearn_{name}', 'exec'), env)
        modules[name] = env
    return modules, properties


def recover(fastas):
    """fastas: [unique ID, sequence, dummy label, training tag]; labels not features."""
    if not fastas or len({r[0] for r in fastas})!=len(fastas):
        raise ValueError('Descriptor inputs need unique record IDs')
    if any(len(r[1])<7 or set(r[1])-set('ACGT') for r in fastas):
        raise ValueError('DCC lag 5 requires at least seven canonical DNA bases')
    modules, properties = load_reference()
    defaults, values = properties['defaults'], properties['values']
    raw = {
        'DCC': modules['ACC']['make_cc_vector'](fastas, defaults['DCC'], values, 5, 2),
        'PseKNC': modules['Pse']['make_PseKNC_vector'](fastas, defaults['PseKNC'], values, 2, 0.1, 3),
        'SCPseDNC': modules['Pse']['make_SCPseDNC_vector'](fastas, defaults['SCPseDNC'], values, 2, 0.1),
        'PCPseDNC': modules['Pse']['make_PseDNC_vector'](fastas, defaults['PCPseDNC'], values, 2, 0.1),
        'Kmer2': modules['Kmer']['Kmer'](fastas),
        'Kmer3': modules['Kmer']['Kmer'](fastas, k=3),
    }
    arrays, names = {}, {}
    for method, width in zip(METHODS, WIDTHS):
        encoded = raw[method]
        if encoded[0][:2] != ['#', 'label'] or [r[0] for r in encoded[1:]] != [r[0] for r in fastas]:
            raise ValueError('iLearn row identity or metadata format changed')
        arrays[method] = np.asarray([r[2:] for r in encoded[1:]], dtype=np.float64)
        names[method] = [f'{method}:{s}' for s in encoded[0][2:]]
        if arrays[method].shape != (len(fastas), width) or not np.isfinite(arrays[method]).all():
            raise ValueError(f'Invalid recovered {method} matrix')
    return arrays, names


def independent(sequence, method, properties):
    """Independent vectorized formulas for cross-checking the upstream loops."""
    words = lambda k: [''.join(x) for x in itertools.product('ACGT', repeat=k)]
    def freq(k):
        c = Counter(sequence[i:i+k] for i in range(len(sequence)-k+1))
        return np.array([c[w] / (len(sequence)-k+1) for w in words(k)])
    if method.startswith('Kmer'):
        return freq(int(method[-1]))
    indices = {w:i for i,w in enumerate(words(2))}
    ix = [indices[sequence[i:i+2]] for i in range(len(sequence)-1)]
    keys = properties['defaults'][method]
    p = np.asarray([properties['values'][k] for k in keys])[:, ix]
    if method == 'DCC':
        centered = p - p.mean(axis=1, keepdims=True)
        pairs = [pair for i in range(len(keys)) for j in range(i+1,len(keys)) for pair in [(i,j),(j,i)]]
        return np.array([np.mean(centered[i,:-lag]*centered[j,lag:]) for i,j in pairs for lag in range(1,6)])
    if method == 'SCPseDNC':
        theta = np.concatenate([np.mean(p[:,:-lag]*p[:,lag:],axis=1) for lag in [1,2]])
    else:
        theta = np.array([np.mean((p[:,:-lag]-p[:,lag:])**2) for lag in [1,2]])
    return np.concatenate([freq(3 if method=='PseKNC' else 2), 0.1*theta]) / (1+0.1*sum(theta))
