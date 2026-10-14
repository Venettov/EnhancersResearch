"""Group related benchmark records and freeze nested folds before modeling."""
from collections import Counter, defaultdict
import numpy as np
from rapidfuzz.distance import Levenshtein
from common import coordinates, digest, reverse_complement

CLASSES = ('strong', 'weak', 'non-enhancer')


class UnionFind:
    def __init__(self, keys):
        self.parent = {key: key for key in keys}

    def find(self, key):
        while self.parent[key] != key:
            self.parent[key] = self.parent[self.parent[key]]
            key = self.parent[key]
        return key

    def join(self, left, right):
        left, right = sorted((self.find(left), self.find(right)))
        self.parent[right] = left


def validate_receipts(rows, receipts):
    by_id = {r['record_id']: r for r in receipts}
    if len(by_id) != len(receipts) or set(by_id) != {r['record_id'] for r in rows}:
        raise ValueError('Reference receipts must cover each benchmark record exactly once')
    for row in rows:
        receipt = by_id[row['record_id']]
        if (receipt['header'] != row['header'] or receipt['assembly'] != 'hg19' or
                receipt['start_convention'] != 'zero-based, end-exclusive' or
                receipt['sequence_sha256'] != digest(row['sequence'])):
            raise ValueError(f'Invalid reference receipt: {row["record_id"]}')
        expected = (row['sequence'] if receipt['match'] == 'forward' else
                    reverse_complement(row['sequence']) if receipt['match'] == 'reverse_complement' else None)
        if expected is None or receipt['reference_sha256'] != digest(expected):
            raise ValueError(f'Unverified reference sequence: {row["record_id"]}')


def sequence_distance(left, right, cutoff=40):
    """Minimum unit-cost global edit distance over both orientations.

    Above the cutoff, only cutoff+1 is returned. This is NOT CD-HIT identity.
    """
    return min(Levenshtein.distance(left, right, score_cutoff=cutoff),
               Levenshtein.distance(left, reverse_complement(right), score_cutoff=cutoff))


def group_records(rows, receipts, max_locus_gap=1000, max_edit_distance=40):
    validate_receipts(rows, receipts)
    if max_locus_gap < 0 or not 0 <= max_edit_distance < 200:
        raise ValueError('Invalid grouping thresholds')
    rows = sorted(rows, key=lambda r: r['record_id'])
    if len({r['record_id'] for r in rows}) != len(rows):
        raise ValueError('Duplicate record IDs')
    if any(len(r['sequence']) != 200 or set(r['sequence']) - set('ACGT') for r in rows):
        raise ValueError('Grouping requires 200 uppercase A/C/G/T bases')
    uf = UnionFind(r['record_id'] for r in rows)
    edges = []
    loci = defaultdict(list)
    for row in rows:
        chrom, start, end = coordinates(row['header'])
        loci[chrom].append((start, end, row['record_id']))
    for chrom in sorted(loci):
        ordered = sorted(loci[chrom])
        for i, (start, end, rid) in enumerate(ordered):
            for other_start, _, other_id in ordered[i+1:]:
                if other_start - end > max_locus_gap:
                    break
                gap = max(0, other_start - end)
                uf.join(rid, other_id)
                edges.append({'left': rid, 'right': other_id, 'reason': 'genomic_proximity',
                              'edit_distance': '', 'gap_bp': gap})
    # Compare every pair, including pairs already connected by coordinates;
    # this preserves an auditable complete list of qualifying sequence edges.
    sequences = [r['sequence'] for r in rows]
    complements = [reverse_complement(s) for s in sequences]
    for i, left in enumerate(rows):
        for j in range(i+1, len(rows)):
            direct = Levenshtein.distance(sequences[i], sequences[j], score_cutoff=max_edit_distance)
            reverse = Levenshtein.distance(sequences[i], complements[j], score_cutoff=max_edit_distance)
            distance = min(direct, reverse)
            if distance <= max_edit_distance:
                right = rows[j]
                uf.join(left['record_id'], right['record_id'])
                edges.append({'left': left['record_id'], 'right': right['record_id'],
                              'reason': 'sequence_similarity', 'edit_distance': distance, 'gap_bp': ''})
    members = defaultdict(list)
    for row in rows:
        members[uf.find(row['record_id'])].append(row['record_id'])
    groups = {}
    for ids in members.values():
        group_id = 'g_' + digest('\n'.join(sorted(ids)))[:20]
        groups.update({rid: group_id for rid in ids})
    return groups, edges


def assign_folds(rows, groups, n_folds, seed):
    """Deterministic greedy balancing of whole groups and three known classes."""
    if n_folds < 2:
        raise ValueError('At least two folds required')
    counts = defaultdict(lambda: np.zeros(len(CLASSES), dtype=int))
    for row in rows:
        counts[groups[row['record_id']]][CLASSES.index(row['class_label'])] += 1
    if len(counts) < n_folds:
        raise ValueError('Too few groups for requested fold count')
    totals = np.sum(list(counts.values()), axis=0)
    if np.any(totals == 0):
        raise ValueError('All three classes are required')
    target = totals / n_folds
    assigned = np.zeros((n_folds, len(CLASSES)), dtype=int)
    result = {}
    ordered = sorted(counts, key=lambda g: (-max(counts[g] / totals), -counts[g].sum(), digest(f'{seed}:{g}')))
    for group_id in ordered:
        candidates = []
        for fold in range(n_folds):
            trial = assigned.copy()
            trial[fold] += counts[group_id]
            score = np.sum(((trial - target) / target) ** 2)
            candidates.append((float(score), digest(f'{seed}:{group_id}:{fold}'), fold))
        fold = min(candidates)[2]
        result[group_id] = fold
        assigned[fold] += counts[group_id]
    if np.any(assigned == 0):
        raise ValueError('At least one fold lacks a class; revise fold design explicitly')
    return {row['record_id']: result[groups[row['record_id']]] for row in rows}


def nested_assignments(rows, groups, outer_folds=5, inner_folds=3, seed=42):
    outer = assign_folds(rows, groups, outer_folds, seed)
    inner = {}
    for held_out in range(outer_folds):
        train = [r for r in rows if outer[r['record_id']] != held_out]
        inner[held_out] = assign_folds(train, groups, inner_folds, seed + 1 + held_out)
    assignments = []
    for row in rows:
        rid = row['record_id']
        record = {key: row[key] for key in ('record_id', 'sequence_sha256', 'class_label')}
        record.update(group_id=groups[rid], outer_fold=outer[rid])
        record.update({f'inner_fold_outer_{fold}': inner[fold].get(rid, -1) for fold in range(outer_folds)})
        assignments.append(record)
    validate_assignments(assignments, outer_folds, inner_folds)
    return assignments


def validate_assignments(assignments, outer_folds=5, inner_folds=3):
    """Reject crossed groups, missing classes, and outer-test rows in inner folds."""
    if len({r['record_id'] for r in assignments}) != len(assignments):
        raise ValueError('Duplicate assignment')
    for key, nfolds in [('outer_fold', outer_folds)] + [(f'inner_fold_outer_{i}', inner_folds) for i in range(outer_folds)]:
        group_folds = defaultdict(set)
        classes = defaultdict(Counter)
        for row in assignments:
            fold = row[key]
            if key == 'outer_fold' and fold not in range(nfolds):
                raise ValueError('Invalid outer fold index')
            if key != 'outer_fold':
                held_out = int(key.rsplit('_', 1)[1])
                if (row['outer_fold'] == held_out) != (fold == -1):
                    raise ValueError('Outer test rows must be excluded from inner evaluation')
            group_folds[row['group_id']].add(fold)
            if fold != -1:
                if fold not in range(nfolds):
                    raise ValueError('Invalid fold index')
                classes[fold][row['class_label']] += 1
        if any(len(folds) != 1 for folds in group_folds.values()):
            raise ValueError('A related group crosses folds')
        if any(set(classes[i]) != set(CLASSES) for i in range(nfolds)):
            raise ValueError('A fold lacks a class')
