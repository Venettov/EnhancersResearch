"""Independent checks of block balance, nested isolation and portable prediction."""
import json
from pathlib import Path
import tempfile
import unittest
import numpy as np
from scipy.spatial.distance import pdist, squareform
from sklearn.metrics import balanced_accuracy_score
from common import HERE
from compare_blocks import fit_block_scales, normalized_distances, search_blocks, evaluate_blocks, block_scores
from compare_scale import training_scale
from test_training import toy_data
from train_svm import checked_fit, splits_for_outer, svc


def blocks(X,split=2):
    return [squareform(pdist(b,'sqeuclidean')) for b in (X[:,:split],X[:,split:])]


class BlockTests(unittest.TestCase):
    def setUp(self):
        self.data=toy_data();self.D=blocks(self.data['X'])
        self.protocol={'C_exponents_base2':[-1,1],'alpha_exponents_base2':[-3,1],
                       'new_arms':{'balanced_words_structure':'words_structure'},'block_boundary':2}
        self.solver=json.loads((HERE/'training_protocol.json').read_text())

    def test_hand_calculation_and_equal_total_distance(self):
        X=np.array([[0.,0.],[1.,10.],[3.,20.],[999.,-999.]])
        D=blocks(X,1);s=fit_block_scales(D,np.arange(3))
        np.testing.assert_allclose(s['block_mean_squared_distances'],[14/3,200],rtol=0,atol=1e-14)
        self.assertAlmostEqual(s['balanced_median_squared_distance'],19/14)
        np.testing.assert_allclose(s['balanced_distance_shares'],[.5,.5],atol=1e-15)
        for d,q in zip(D,s['block_mean_squared_distances']):
            self.assertAlmostEqual(d[:3,:3][np.triu_indices(3,1)].mean()/q,1)
        # This is aggregate balance, not equal influence on every pair.
        self.assertNotAlmostEqual(D[0][0,1]/s['block_mean_squared_distances'][0],D[1][0,1]/s['block_mean_squared_distances'][1])

    def test_pair_mean_matches_twice_total_sample_variance(self):
        train=np.arange(17);s=fit_block_scales(self.D,train)
        expected=[2*np.var(b[train],axis=0,ddof=1).sum() for b in (self.data['X'][:,:2],self.data['X'][:,2:])]
        np.testing.assert_allclose(s['block_mean_squared_distances'],expected,rtol=1e-15)

    def test_zeros_preserved_and_invalid_or_degenerate_scales_rejected(self):
        D=squareform(pdist(np.array([[0.],[0.],[1.],[2.]]),'sqeuclidean'))
        self.assertAlmostEqual(fit_block_scales([D],np.arange(4))['block_mean_squared_distances'][0],11/6)
        for invalid in ([D,np.zeros_like(D)],[D,np.full_like(D,np.nan)],[D,-np.ones_like(D)],[D,D[:3,:3]],[]):
            with self.assertRaises(ValueError): fit_block_scales(invalid,np.arange(4))
        for idx in ([0,0],[0],[-1,1],[0,4],[0.,1.]):
            with self.assertRaises(ValueError): fit_block_scales([D],np.asarray(idx))
        # A positive mean can coexist with a zero median: no silent fallback.
        D=squareform(pdist(np.array([[0.],[0.],[0.],[0.],[1.]]),'sqeuclidean'))
        with self.assertRaises(ValueError): fit_block_scales([D],np.arange(5))

    def test_inner_validation_and_outer_records_cannot_fit_scales(self):
        _,test,splits=splits_for_outer(self.data,0)
        for train,valid in splits:
            original=fit_block_scales(self.D,train)
            changed=[d.copy() for d in self.D]
            for d in changed:
                d[valid,:]=np.nan;d[:,valid]=np.nan;d[test,:]=np.nan;d[:,test]=np.nan
            self.assertEqual(fit_block_scales(changed,train),original)

    def test_direct_scaled_coordinate_rbf_matches_inner_search(self):
        d=self.data;_,_,splits=splits_for_outer(d,0)
        best,grid,scales=search_blocks(self.D,d['y'],d['groups'],splits,self.protocol,self.solver,2)
        for candidate in grid:
            expected=[]
            for i,(train,valid) in enumerate(splits):
                qs=[2*np.var(b[train],axis=0,ddof=1).sum() for b in (d['X'][:,:2],d['X'][:,2:])]
                scaled=d['X']/np.sqrt(np.repeat(qs,2))
                m=float(np.median(pdist(scaled[train],'sqeuclidean')))
                np.testing.assert_allclose(qs,scales[i]['block_mean_squared_distances'],rtol=1e-15)
                self.assertAlmostEqual(m,scales[i]['balanced_median_squared_distance'])
                model=checked_fit(svc(self.solver,candidate['C'],candidate['alpha']/m,precomputed=False),scaled[train],d['y'][train])
                expected.append(float(balanced_accuracy_score(d['y'][valid],model.predict(scaled[valid]))))
            self.assertEqual(candidate['fold_balanced_accuracy'],expected)
        self.assertEqual(best,sorted(grid,key=lambda c:(-c['mean_balanced_accuracy'],c['C'],c['alpha']))[0])

    def test_outer_labels_features_and_worker_count_cannot_change_search(self):
        d=self.data;_,test,splits=splits_for_outer(d,0)
        original=search_blocks(self.D,d['y'],d['groups'],splits,self.protocol,self.solver,1)
        changed=[m.copy() for m in self.D]
        for m in changed: m[test,:]=np.nan;m[:,test]=np.nan
        y=d['y'].copy();y[test]=1-y[test]
        self.assertEqual(original,search_blocks(changed,y,d['groups'],splits,self.protocol,self.solver,2))

    def test_independent_block_unit_changes_cancel(self):
        d=self.data;train,test,splits=splits_for_outer(d,0)
        changed=blocks(d['X']*np.array([8.,8.,.25,.25]))
        s=fit_block_scales(self.D,train);cs=fit_block_scales(changed,train)
        np.testing.assert_array_equal(normalized_distances(self.D,test,train,s),normalized_distances(changed,test,train,cs))
        a,ag,_=search_blocks(self.D,d['y'],d['groups'],splits,self.protocol,self.solver,1)
        b,bg,_=search_blocks(changed,d['y'],d['groups'],splits,self.protocol,self.solver,2)
        for ac,bc in zip(ag,bg):
            for key in ('C','alpha','mean_balanced_accuracy','fold_balanced_accuracy','iterations'): self.assertEqual(ac[key],bc[key])
        self.assertEqual((a['C'],a['alpha']),(b['C'],b['alpha']))

    def test_single_block_matches_previous_median_normalization(self):
        train,test,_=splits_for_outer(self.data,0)
        for D in self.D:
            scale=fit_block_scales([D],train)
            old=D[np.ix_(test,train)]/training_scale(D,train)
            new=normalized_distances([D],test,train,scale)
            np.testing.assert_allclose(old,new,atol=1e-14,rtol=1e-14)
            np.testing.assert_allclose(np.exp(-2*old),np.exp(-2*new),atol=1e-14,rtol=1e-14)

    def test_nested_export_replays_with_raw_features_and_fitted_blocks(self):
        d=self.data
        with tempfile.TemporaryDirectory() as temp:
            out=Path(temp);pred,score,folds=evaluate_blocks(d,self.D,'balanced_words_structure','layer1',self.protocol,self.solver,out,2,'fixture',['a','b','c','d'])
            for f,record in enumerate(folds):
                train,test,splits=splits_for_outer(d,f);path=out/'balanced_words_structure/layer1'/f'outer_{f}_model.npz'
                receipt=json.loads(path.with_name(f'outer_{f}_scales.json').read_text())
                self.assertEqual(receipt['outer']['training_ids'],d['ids'][train].tolist())
                for i,(tr,_) in enumerate(splits): self.assertEqual(receipt['inner'][i]['training_ids'],d['ids'][tr].tolist())
                with np.load(path,allow_pickle=False) as model:
                    self.assertLessEqual(set(model['support_record_ids']),set(d['ids'][train]))
                    q=model['block_mean_squared_distances'];m=float(model['balanced_median_squared_distance']);alpha=float(model['alpha'])
                    np.testing.assert_array_equal(model['block_gammas'],alpha/(m*q))
                    scaled=d['X']/np.sqrt(np.repeat(q,2))
                    direct=checked_fit(svc(self.solver,float(model['C']),alpha/m,precomputed=False),scaled[train],d['y'][train])
                    np.testing.assert_allclose(block_scores(path,d['X'][test]),direct.decision_function(scaled[test]),atol=1e-6)
                np.testing.assert_allclose(block_scores(path,d['X'][test]),score[test],atol=1e-6)
                np.testing.assert_array_equal((block_scores(path,d['X'][test])>0).astype(int),pred[test])


if __name__=='__main__': unittest.main()
