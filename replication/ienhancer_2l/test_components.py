"""Independent checks for component isolation and paired factorial contrasts."""
import json
from pathlib import Path
import tempfile
import unittest

import numpy as np
from sklearn.metrics.pairwise import euclidean_distances

from common import HERE
from features import components, combine
from compare_components import (ARMS, component_matrices, component_names,
                                contrasts_with_intervals, feature_geometry)
from compare_features import evaluate_svm
from test_training import toy_data
from train_svm import portable_scores, splits_for_outer


class ComponentTests(unittest.TestCase):
    def test_four_arms_against_hand_calculation(self):
        F = np.array([[.25,.75],[.6,.4]])
        theta = np.array([[2.,4.],[1.,3.]])
        X,Z = component_matrices(F,theta,.5)
        np.testing.assert_array_equal(Z,[4,3])
        np.testing.assert_array_equal(X['words'],F)
        np.testing.assert_allclose(X['rescaled_words'],[[.0625,.1875],[.2,.4/3]],atol=1e-16,rtol=0)
        np.testing.assert_array_equal(X['words_structure'],[[.25,.75,1,2],[.6,.4,.5,1.5]])
        np.testing.assert_allclose(X['full'],[[.0625,.1875,.25,.5],[.2,.4/3,1/6,.5]],atol=1e-16)
        np.testing.assert_array_equal(X['full'][:,:2],X['rescaled_words'])
        np.testing.assert_allclose(X['full']*Z[:,None],X['words_structure'],atol=1e-16,rtol=0)

    def test_raw_sequence_full_agrees_with_equation_and_zero_terms_collapse(self):
        parts = [components(s) for s in ('A'*200,'ACGT'*50,'A'*100+'G'*100)]
        F,theta = np.stack([p[0] for p in parts]),np.stack([p[1] for p in parts])
        for weight in (0,.1,.4):
            X,Z = component_matrices(F,theta,weight)
            np.testing.assert_array_equal(X['full'],np.stack([combine(*p,weight) for p in parts]))
            np.testing.assert_array_equal(X['full'][0,:4096],F[0])
            self.assertEqual(Z[0],1)
            if weight == 0:
                np.testing.assert_array_equal(X['rescaled_words'],F)
                np.testing.assert_array_equal(X['full'][:,4096:],0)
        for arm in ARMS:
            self.assertEqual(len(component_names(arm)), X[arm].shape[1])

    def test_no_cohort_dependence_and_reject_invalid_components(self):
        F,theta = np.array([[.2,.8],[.4,.6]]),np.array([[1,2],[3,4]])
        whole,Z = component_matrices(F,theta,.4)
        for i in range(2):
            single,z = component_matrices(F[i:i+1],theta[i:i+1],.4)
            for arm in ARMS:
                np.testing.assert_array_equal(whole[arm][i:i+1],single[arm])
        for a,b,w in [(F*2,theta,.4),(F,theta*-1,.4),(F,theta,-1),(F,theta,np.nan),
                      (F[:1],theta,.4),(F,theta*np.nan,.4)]:
            with self.assertRaises(ValueError):
                component_matrices(a,b,w)

    def test_contrast_direction_interaction_and_identical_arm_cancellation(self):
        data = toy_data(); y = data['y']
        protocol = json.loads((HERE/'component_protocol.json').read_text())
        perfect = (y,y.astype(float)); wrong = (1-y,(1-y).astype(float))
        predictions = {'words':wrong,'rescaled_words':perfect,'words_structure':wrong,'full':perfect}
        result = contrasts_with_intervals(data,predictions,{'resamples':30,'seed':42},protocol['contrasts'])
        self.assertEqual(result['accepted'],30)
        expected = {'rescaling_without_terms':1,'adding_terms_without_rescaling':0,
                    'adding_terms_with_rescaling':0,'rescaling_with_terms':1,
                    'combined_change':1,'interaction':0}
        for name,value in expected.items():
            for metric in result['contrasts'][name]['metrics'].values():
                self.assertEqual(metric['estimate'],value)
                self.assertEqual(metric['ci95'],[value,value])

    def test_geometry_against_direct_pair_distances(self):
        F,theta = np.array([[.2,.8],[.9,.1]]),np.array([[1.,2.],[2.,4.]])
        X,Z = component_matrices(F,theta,.5)
        g = feature_geometry(X,Z,{'pairs':11,'seed':42},split=2)
        for arm in ('full','words_structure'):
            d = (X[arm][0]-X[arm][1])**2
            self.assertAlmostEqual(g[arm]['structure_share_of_total_squared_distance'],d[2:].sum()/d.sum())
        self.assertEqual(g['Z_quantiles']['min'],Z.min())

    def test_component_model_exports_and_fixed_setting_isolation(self):
        data = toy_data()
        rng = np.random.default_rng(8)
        F = rng.dirichlet(np.ones(4),len(data['y']))
        theta = rng.uniform(0,2,(len(F),2))
        X,_ = component_matrices(F,theta,.4)
        protocol = json.loads((HERE/'training_protocol.json').read_text())
        choices = [{'C':2.,'gamma':.5}]*5
        with tempfile.TemporaryDirectory() as folder:
            for arm in ARMS:
                changed = {**data,'X':X[arm]}
                names = [f'component_{i}' for i in range(X[arm].shape[1])]
                pred,scores,folds = evaluate_svm(changed,euclidean_distances(X[arm],squared=True),names,
                                               arm,'layer1',protocol,Path(folder),1,'test',choices)
                for fold in range(5):
                    train,test,_ = splits_for_outer(data,fold)
                    path = Path(folder)/arm/'layer1'/f'outer_{fold}_model.npz'
                    with np.load(path,allow_pickle=False) as m:
                        self.assertLessEqual(set(m['support_record_ids']),set(data['ids'][train]))
                        self.assertEqual(float(m['C']),2.)
                        self.assertEqual(float(m['gamma']),.5)
                    np.testing.assert_allclose(portable_scores(path,X[arm][test]),scores[test],atol=1e-6)


if __name__ == '__main__':
    unittest.main()
