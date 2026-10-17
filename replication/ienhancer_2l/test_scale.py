"""Independent checks of train-only distance scaling and dimensionless tuning."""
import json
from pathlib import Path
import tempfile
import unittest
import numpy as np
from scipy.spatial.distance import pdist, squareform
from sklearn.metrics import balanced_accuracy_score
from common import HERE
from compare_scale import training_scale, choose_scaled, scale_search, evaluate_scale
from test_training import toy_data
from train_svm import checked_fit, portable_scores, splits_for_outer, svc


class ScaleTests(unittest.TestCase):
    def setUp(self):
        self.data = toy_data()
        self.solver = json.loads((HERE/'training_protocol.json').read_text())
        self.protocol = {'C_exponents_base2':[-1,1], 'alpha_exponents_base2':[-3,1]}

    def test_hand_median_excludes_diagonal_and_excluded_records(self):
        D = squareform(pdist(np.array([[0.],[2.],[5.],[100.]]),'sqeuclidean'))
        self.assertEqual(training_scale(D,np.arange(3)),9.)
        D[3,:] = D[:,3] = np.nan
        np.fill_diagonal(D,999.)
        self.assertEqual(training_scale(D,np.arange(3)),9.)

    def test_duplicate_records_are_included_but_degenerate_scale_rejected(self):
        D = squareform(pdist(np.array([[0.],[0.],[1.],[2.]]),'sqeuclidean'))
        # Six pair distances: 0,1,4,1,4,1. Median is 1, not 2.5.
        self.assertEqual(training_scale(D,np.arange(4)),1.)
        for bad in (np.zeros((4,4)),np.full((4,4),np.nan),-np.ones((4,4))):
            with self.assertRaises(ValueError):
                training_scale(bad,np.arange(4))
        for indices in ([0,0],[0],[-1,1],[0,4],[0.,1.]):
            with self.assertRaises(ValueError):
                training_scale(D,np.asarray(indices))

    def test_each_inner_search_matches_direct_rbf_fits(self):
        d = self.data
        _,_,splits = splits_for_outer(d,0)
        D = squareform(pdist(d['X'],'sqeuclidean'))
        best,grid,scales = scale_search(D,d['y'],d['groups'],splits,self.protocol,self.solver,2)
        for candidate in grid:
            expected=[]
            for i,(tr,va) in enumerate(splits):
                m=float(np.median(pdist(d['X'][tr],'sqeuclidean')))
                self.assertEqual(scales[i],m)
                direct=checked_fit(svc(self.solver,candidate['C'],candidate['alpha']/m,precomputed=False),d['X'][tr],d['y'][tr])
                expected.append(float(balanced_accuracy_score(d['y'][va],direct.predict(d['X'][va]))))
            self.assertEqual(candidate['fold_balanced_accuracy'],expected)
            self.assertEqual(candidate['mean_balanced_accuracy'],float(np.mean(expected)))
        self.assertEqual(best,sorted(grid,key=lambda x:(-x['mean_balanced_accuracy'],x['C'],x['alpha']))[0])

    def test_outer_features_and_labels_cannot_change_search(self):
        d=self.data
        _,test,splits=splits_for_outer(d,0)
        D=squareform(pdist(d['X'],'sqeuclidean'))
        a=scale_search(D,d['y'],d['groups'],splits,self.protocol,self.solver,1)
        changed=D.copy();changed[test,:]=np.nan;changed[:,test]=np.nan
        y=d['y'].copy();y[test]=1-y[test]
        b=scale_search(changed,y,d['groups'],splits,self.protocol,self.solver,2)
        self.assertEqual(a,b)

    def test_inner_validation_values_cannot_change_its_training_scale(self):
        d=self.data
        _,_,splits=splits_for_outer(d,0)
        D=squareform(pdist(d['X'],'sqeuclidean'))
        for tr,va in splits:
            m=training_scale(D,tr)
            changed=D.copy();changed[va,:]=np.nan;changed[:,va]=np.nan
            self.assertEqual(training_scale(changed,tr),m)

    def test_uniform_scale_cancels_in_kernel_search_and_predictions(self):
        d=self.data
        train,test,splits=splits_for_outer(d,0)
        D=squareform(pdist(d['X'],'sqeuclidean'))
        # A power of two makes the squared-distance rescaling exact in float64.
        scaled=squareform(pdist(d['X']*8,'sqeuclidean'))
        a=scale_search(D,d['y'],d['groups'],splits,self.protocol,self.solver,1)
        b=scale_search(scaled,d['y'],d['groups'],splits,self.protocol,self.solver,2)
        for first,second in zip(a[1],b[1]):
            for key in ('C','alpha','mean_balanced_accuracy','fold_balanced_accuracy','iterations'):
                self.assertEqual(first[key],second[key])
        self.assertEqual((a[0]['C'],a[0]['alpha']),(b[0]['C'],b[0]['alpha']))
        m=training_scale(D,train);ms=training_scale(scaled,train)
        self.assertEqual(ms,64*m)
        K=np.exp(-a[0]['alpha']*D/m);Ks=np.exp(-b[0]['alpha']*scaled/ms)
        np.testing.assert_array_equal(K,Ks)
        model=checked_fit(svc(self.solver,a[0]['C'],a[0]['alpha']/m),K[np.ix_(train,train)],d['y'][train])
        other=checked_fit(svc(self.solver,b[0]['C'],b[0]['alpha']/ms),Ks[np.ix_(train,train)],d['y'][train])
        np.testing.assert_array_equal(model.predict(K[np.ix_(test,train)]),other.predict(Ks[np.ix_(test,train)]))

    def test_ties_and_invalid_candidates(self):
        grid=[{'C':c,'alpha':a,'mean_balanced_accuracy':.75} for c,a in [(2,1),(1,2),(1,1)]]
        self.assertEqual(choose_scaled(grid),grid[-1])
        grid[0]['mean_balanced_accuracy']=.76
        self.assertEqual(choose_scaled(grid),grid[0])
        for invalid in ([],[{'mean_balanced_accuracy':np.nan}]):
            with self.assertRaises(ValueError): choose_scaled(invalid)

    def test_nested_exports_record_training_ids_scales_and_replay(self):
        d=self.data;D=squareform(pdist(d['X'],'sqeuclidean'))
        with tempfile.TemporaryDirectory() as tmp:
            pred,scores,folds=evaluate_scale(d,D,'words','layer1',self.protocol,self.solver,Path(tmp),2,'fixture',names=['a','b','c','d'])
            for f,record in enumerate(folds):
                tr,te,splits=splits_for_outer(d,f)
                target=Path(tmp)/'words/layer1'
                scales=json.loads((target/f'outer_{f}_scale.json').read_text())
                self.assertEqual(scales['outer_training_ids'],d['ids'][tr].tolist())
                self.assertEqual(scales['outer_median_squared_distance'],float(np.median(pdist(d['X'][tr],'sqeuclidean'))))
                for i,(inner,_) in enumerate(splits):
                    self.assertEqual(scales['inner'][i]['training_ids'],d['ids'][inner].tolist())
                    self.assertEqual(scales['inner'][i]['median_squared_distance'],float(np.median(pdist(d['X'][inner],'sqeuclidean'))))
                path=target/f'outer_{f}_model.npz'
                with np.load(path,allow_pickle=False) as model:
                    self.assertLessEqual(set(model['support_record_ids']),set(d['ids'][tr]))
                    self.assertEqual(float(model['gamma']),float(model['alpha'])/float(model['training_median_squared_distance']))
                    self.assertEqual(float(model['gamma']),record['outer_effective_gamma'])
                replay=portable_scores(path,d['X'][te])
                np.testing.assert_allclose(replay,scores[te],atol=1e-6)
                np.testing.assert_array_equal((replay>0).astype(int),pred[te])


if __name__=='__main__': unittest.main()
