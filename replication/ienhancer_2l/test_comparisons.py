"""Independent checks for baseline counts, paired inference and model identity."""
import copy
import json
from pathlib import Path
import tempfile
import unittest

import numpy as np
from sklearn.metrics import accuracy_score, balanced_accuracy_score, roc_auc_score
from sklearn.metrics.pairwise import euclidean_distances

from common import HERE
from compare_features import (baseline_features, bootstrap_weights, evaluate_svm,
                               comparison_search,
                               majority_oof, paired_intervals, validate_variant,
                               weighted_metrics_batch)
from features import feature_names, words
from test_training import toy_data
from train_svm import array_hash, portable_scores, search, splits_for_outer


class ComparisonTests(unittest.TestCase):
    def test_flat_scheduling_matches_original_search_and_excludes_outer_labels(self):
        data = toy_data()
        protocol = json.loads((HERE/'training_protocol.json').read_text())
        protocol['C_exponents_base2']=[-1,1]
        protocol['gamma_exponents_base2']=[-3,-1]
        _,test,splits=splits_for_outer(data,0)
        distances=euclidean_distances(data['X'],squared=True)
        original=search(distances,data['y'],data['groups'],splits,protocol,workers=1)
        flat=comparison_search(distances,data['y'],data['groups'],splits,protocol,workers=4)
        self.assertEqual(original,flat)
        changed=data['y'].copy()
        changed[test]=1-changed[test]
        self.assertEqual(flat,comparison_search(distances,changed,data['groups'],splits,protocol,workers=2))

    def test_gc_and_sixmer_counts_against_hand_counts(self):
        sequences = ['A'*200, 'G'*200, 'ACGT'*50, 'A'*199+'C']
        gc, names = baseline_features(sequences, 'gc_only')
        np.testing.assert_array_equal(gc[:, 0], [0, 1, .5, .005])
        self.assertEqual(names, ['GC_fraction'])
        X, names = baseline_features(sequences, 'sixmer_only')
        index = {w:i for i,w in enumerate(words(6))}
        self.assertEqual(X.shape, (4,4096))
        self.assertEqual(X[0,index['AAAAAA']], 1)
        self.assertEqual(X[1,index['GGGGGG']], 1)
        for word, count in [('ACGTAC',49),('CGTACG',49),('GTACGT',49),('TACGTA',48)]:
            self.assertEqual(X[2,index[word]], count/195)
        self.assertEqual(X[3,index['AAAAAA']], 194/195)
        self.assertEqual(X[3,index['AAAAAC']], 1/195)
        np.testing.assert_allclose(X.sum(axis=1), 1, atol=1e-15)
        self.assertEqual(names, feature_names()[:4096])
        with self.assertRaises(ValueError):
            baseline_features(['ACGT'], 'gc_only')

    def test_variant_validation_rejects_labels_order_and_values(self):
        data = {'ids': np.asarray(['a','b']), 'y': np.asarray([0,1])}
        X = np.full((2,4105), 1/4105)
        archive = {'X_layer1': X, 'y_layer1':data['y'], 'record_ids_layer1':data['ids'],
                   'feature_names': np.asarray(feature_names())}
        expected = {'shape':list(X.shape), 'array_sha256_le_float64':array_hash(X)}
        np.testing.assert_array_equal(validate_variant(archive,'layer1',data,expected), X)
        for key, value in [('y_layer1',np.asarray([1,0])), ('record_ids_layer1',np.asarray(['b','a'])),
                           ('X_layer1',X+1e-5), ('feature_names',np.asarray(feature_names()[::-1]))]:
            with self.assertRaises(ValueError):
                validate_variant({**archive,key:value},'layer1',data,expected)

    def test_weighted_metrics_match_explicit_resampling_with_score_ties(self):
        rng = np.random.default_rng(92)
        y = np.tile([0,1],20)
        predictions = rng.integers(0,2,40)
        scores = rng.integers(-3,4,40).astype(float)
        weights = rng.integers(0,4,(30,40))
        actual = weighted_metrics_batch(y,predictions,scores,weights)
        expected = []
        for row in weights:
            idx = np.repeat(np.arange(len(y)),row)
            expected.append([accuracy_score(y[idx],predictions[idx]),
                             balanced_accuracy_score(y[idx],predictions[idx]),
                             roc_auc_score(y[idx],scores[idx])])
        np.testing.assert_allclose(actual,expected,atol=1e-14,rtol=0)
        constant = weighted_metrics_batch(y,predictions,np.zeros(len(y)),weights)
        np.testing.assert_array_equal(constant[:,2],.5)

    def test_bootstrap_keeps_whole_groups_and_same_predictions_have_zero_difference(self):
        data = toy_data()
        data['groups'][1] = data['groups'][0]
        parts = bootstrap_weights(data,40,42)
        np.testing.assert_array_equal(parts[0][1][:,0],parts[0][1][:,1])
        for (_,a),(_,b) in zip(parts,bootstrap_weights(data,40,42)):
            np.testing.assert_array_equal(a,b)
        scores = np.linspace(-1,1,len(data['y']))
        prediction = (scores>0).astype(int)
        results = paired_intervals(data, {'primary':(prediction,scores),'same':(prediction,scores)},
                                   {'resamples':40,'seed':42})
        self.assertEqual(results['accepted'],40)
        for bounds in results['methods']['same']['paired_difference_from_primary_intervals'].values():
            self.assertEqual(bounds,[0,0])

    def test_paired_difference_direction(self):
        data = toy_data()
        y = data['y']
        results = paired_intervals(data, {'primary':(1-y,(1-y).astype(float)), 'perfect':(y,y.astype(float))},
                                   {'resamples':20,'seed':42})
        for bounds in results['methods']['perfect']['paired_difference_from_primary_intervals'].values():
            self.assertEqual(bounds,[1,1])

    def test_majority_uses_training_labels_and_breaks_ties_toward_zero(self):
        data = toy_data()
        pred,scores,folds = majority_oof(data)
        np.testing.assert_array_equal(pred,0)
        np.testing.assert_array_equal(scores,.5)
        changed = copy.deepcopy(data)
        heldout = data['outer']==0
        changed['y'][np.flatnonzero(heldout)[:4]] = 1
        new_pred,new_scores,_ = majority_oof(changed)
        np.testing.assert_array_equal(pred[heldout],new_pred[heldout])
        np.testing.assert_array_equal(scores[heldout],new_scores[heldout])

    def test_comparison_exports_keep_feature_identity_and_replay(self):
        data = toy_data()
        protocol = json.loads((HERE/'training_protocol.json').read_text())
        protocol['C_exponents_base2']=[-1]
        protocol['gamma_exponents_base2']=[-3]
        choices=[{'C':.5,'gamma':.125} for _ in range(5)]
        distances=euclidean_distances(data['X'],squared=True)
        with tempfile.TemporaryDirectory() as directory:
            output=Path(directory)
            pred,scores,folds=evaluate_svm(data,distances,['a','b','c','d'],'toy_fixed','layer1',
                                          protocol,output,1,'test_hash',choices)
            tuned_pred,tuned_scores,_=evaluate_svm(data,distances,['a','b','c','d'],'toy_retuned','layer1',
                                                  protocol,output,1,'test_hash')
            np.testing.assert_array_equal(pred,tuned_pred)
            np.testing.assert_allclose(scores,tuned_scores,atol=1e-12)
            for fold in range(5):
                path=output/'toy_fixed/layer1'/f'outer_{fold}_model.npz'
                with np.load(path,allow_pickle=False) as model:
                    self.assertEqual(str(model['feature_variant']),'toy_fixed')
                    self.assertEqual(list(model['feature_names']),['a','b','c','d'])
                    self.assertFalse(set(model['support_record_ids']) & set(data['ids'][data['outer']==fold]))
                np.testing.assert_allclose(portable_scores(path,data['X'][data['outer']==fold]),
                                           scores[data['outer']==fold],atol=1e-10)


if __name__=='__main__':
    unittest.main()
