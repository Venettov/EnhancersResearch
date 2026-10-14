"""Check split isolation, kernel equivalence, selection and model replay."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
import numpy as np
from sklearn.metrics.pairwise import euclidean_distances
from common import HERE
from train_svm import (assert_split, checked_fit, choose_candidate, export_model,
                       kernel_from_distances, metrics, portable_scores, search,
                       splits_for_outer, svc, summarize_oof, group_bootstrap)


def toy_data():
    rng = np.random.default_rng(2)
    y = np.tile([0, 1], 30)
    X = rng.normal(size=(60, 4)) + y[:, None] * 2
    outer = np.repeat(np.arange(5), 12)
    inner = {}
    for fold in range(5):
        selected = np.flatnonzero(outer != fold)
        values = np.full(60, -1)
        values[selected] = np.repeat(np.arange(3), 16)
        inner[fold] = values
    return {'X':X, 'y':y, 'groups':np.asarray([f'g{i}' for i in range(60)]),
            'ids':np.asarray([f'id{i}' for i in range(60)]), 'outer':outer, 'inner':inner}


class TrainingTests(unittest.TestCase):
    def setUp(self):
        self.data = toy_data()
        self.protocol = json.loads((HERE / 'training_protocol.json').read_text())
        self.protocol['C_exponents_base2'] = [-1, 1]
        self.protocol['gamma_exponents_base2'] = [-3, -1]

    def test_precomputed_rbf_and_numeric_export_match_direct_svc(self):
        data = self.data
        X, y = data['X'], data['y']
        train, test = np.arange(40), np.arange(40, 60)
        distances = euclidean_distances(X, squared=True)
        kernel = kernel_from_distances(distances, 0.5)
        cached = checked_fit(svc(self.protocol, 2, 0.5), kernel[np.ix_(train, train)], y[train])
        direct = checked_fit(svc(self.protocol, 2, 0.5, precomputed=False), X[train], y[train])
        np.testing.assert_allclose(cached.decision_function(kernel[np.ix_(test, train)]), direct.decision_function(X[test]), atol=1e-10, rtol=1e-10)
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'model.npz'
            export_model(path, cached, X[train], data['ids'][train], 2, 0.5, 'test', 'fixture')
            np.testing.assert_allclose(portable_scores(path, X[test]), direct.decision_function(X[test]), atol=1e-10, rtol=1e-10)
            np.testing.assert_array_equal((portable_scores(path, X[test]) > 0).astype(int), direct.predict(X[test]))
            with np.load(path, allow_pickle=False) as saved:
                self.assertEqual(len(saved['support_record_ids']), len(cached.support_))

    def test_outer_test_labels_cannot_change_inner_search(self):
        data = self.data
        _, test, splits = splits_for_outer(data, 0)
        distances = euclidean_distances(data['X'], squared=True)
        chosen, candidates = search(distances, data['y'], data['groups'], splits, self.protocol, workers=1)
        changed = data['y'].copy()
        changed[test] = 1 - changed[test]
        repeated, repeated_candidates = search(distances, changed, data['groups'], splits, self.protocol, workers=2)
        self.assertEqual(chosen, repeated)
        self.assertEqual(candidates, repeated_candidates)

    def test_splits_reject_group_crossing_and_outer_contamination(self):
        data = self.data
        changed = copy.deepcopy(data)
        changed['groups'][12] = changed['groups'][0]
        with self.assertRaisesRegex(ValueError, 'group crosses'):
            splits_for_outer(changed, 0)
        changed = copy.deepcopy(data)
        changed['inner'][0][0] = 0
        with self.assertRaisesRegex(ValueError, 'Outer test'):
            splits_for_outer(changed, 0)
        with self.assertRaises(ValueError):
            assert_split(np.arange(10), np.arange(5, 15), data['groups'], data['y'])

    def test_selection_ties_prefer_smaller_C_then_gamma(self):
        candidates = [{'C':c, 'gamma':g, 'mean_balanced_accuracy':0.75} for c,g in [(2,1),(1,2),(1,1)]]
        self.assertEqual(choose_candidate(candidates), candidates[-1])
        candidates[0]['mean_balanced_accuracy'] = 0.76
        self.assertEqual(choose_candidate(candidates), candidates[0])

    def test_metric_orientation_confusion_and_fold_ranking(self):
        y = np.asarray([0,0,1,1])
        predicted = np.asarray([0,1,0,1])
        scores = np.asarray([-2,1,-1,2])
        result = metrics(y, predicted, scores)
        self.assertEqual([result[k] for k in ['tn','fp','fn','tp']], [1,1,1,1])
        self.assertEqual(result['accuracy'], 0.5)
        self.assertEqual(result['mcc'], 0)
        self.assertEqual(result['roc_auc'], 0.75)
        self.assertEqual(metrics(y, predicted, -scores)['roc_auc'], 0.25)
        summary = summarize_oof(np.tile(y,5), np.tile(predicted,5), np.tile(scores,5), np.repeat(np.arange(5),4))
        self.assertNotIn('roc_auc', summary['pooled_threshold_metrics'])
        self.assertEqual(summary['macro_mean']['roc_auc'], 0.75)

    def test_group_bootstrap_is_deterministic_and_perfect_case_is_one(self):
        data = self.data
        self.protocol['bootstrap']['resamples'] = 20
        a = group_bootstrap(data, data['y'], data['y'].astype(float), self.protocol)
        b = group_bootstrap(data, data['y'], data['y'].astype(float), self.protocol)
        self.assertEqual(a, b)
        self.assertEqual(a['macro_mean_intervals']['accuracy'], [1, 1])
        self.assertEqual(a['macro_mean_intervals']['roc_auc'], [1, 1])


if __name__ == '__main__':
    unittest.main()
