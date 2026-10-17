"""Feature fidelity, leakage traps and model-runtime checks for the repaired code."""
import io
import json
import pickle
import unittest
import numpy as np
from sklearn.base import BaseEstimator, ClassifierMixin
from sklearn.dummy import DummyClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.neural_network import MLPClassifier
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from common import HERE
from evaluation import make_splits, positive_probability, predict_stack, select_candidate
from feature_matrix import load_matrix, VARIANTS
from ilearn_features import load_reference, recover, independent, METHODS


class MemoryClassifier(ClassifierMixin,BaseEstimator):
    """A deliberately overfitting classifier that exposes in-sample meta features."""
    def __init__(self,unseen=0.25):
        self.unseen=unseen
    def fit(self,x,y):
        self.seen_=set(x[:,0]);self.classes_=np.array([0,1]);return self
    def predict_proba(self,x):
        p=np.array([0.99 if row[0] in self.seen_ else self.unseen for row in x])
        return np.column_stack([1-p,p])


class IlearnTests(unittest.TestCase):
    def test_properties_match_original_safe_data(self):
        class DataOnly(pickle.Unpickler):
            def find_class(self,*args):
                raise ValueError('Classes prohibited')
        _,p=load_reference()
        d=DataOnly(io.BytesIO((HERE/'vendor/iLearn/data/didnaPhyche.data').read_bytes())).load()
        self.assertEqual(len(p['defaults']['PCPseDNC']),38)
        self.assertEqual(len(p['defaults']['DCC']),6)
        for name,values in p['values'].items():
            self.assertEqual(values,[float(x) for x in d[name]])

    def test_independent_formulas_and_dummy_label_invariance(self):
        rng=np.random.default_rng(42)
        sequences=['AAAACCGTT','ACGT'*50,''.join(rng.choice(list('ACGT'),200))]
        a,names=recover([[str(i),s,'0','training'] for i,s in enumerate(sequences)])
        b,_=recover([[str(i),s,'1','training'] for i,s in enumerate(sequences)])
        p=load_reference()[1]
        for name in METHODS:
            np.testing.assert_array_equal(a[name],b[name])
            self.assertEqual(len(names[name]),a[name].shape[1])
            for i,s in enumerate(sequences):
                np.testing.assert_allclose(a[name][i],independent(s,name,p),rtol=1e-12,atol=1e-12)

    def test_kmer_overlaps_and_denominator(self):
        a,_=recover([['test','AAAACGTA','0','training']])
        self.assertEqual(a['Kmer2'].shape,(1,16))
        self.assertEqual(a['Kmer3'].shape,(1,64))
        self.assertEqual(a['Kmer2'][0,0],3/7)
        self.assertEqual(a['Kmer3'][0,0],2/6)

    def test_invalid_descriptor_input_rejected(self):
        for sequence in ['ACGT','ACGTNNNN','acgtacgt']:
            with self.assertRaises(ValueError):
                recover([['test',sequence,'0','training']])

    def test_saved_variants_align_all_rows(self):
        for variant,(_,_,width) in VARIANTS.items():
            x,y,g,ids,names,rows=load_matrix(variant)
            self.assertEqual(x.shape,(2968,width))
            self.assertEqual(len(set(g)),2451)
            self.assertEqual(len(set(ids)),2968)
            self.assertEqual(sum(y),1484)


class EvaluationTests(unittest.TestCase):
    def setUp(self):
        self.g=np.repeat(np.arange(24),4)
        self.y=np.repeat(np.arange(24)%2,4)
        self.ids=np.array([f'train:{i}' for i in range(96)])
        rng=np.random.default_rng(2)
        self.x=np.column_stack([np.arange(96),rng.normal(size=(96,3))])
        self.new=np.column_stack([np.arange(200,208),rng.normal(size=(8,3))])
        self.ng=np.repeat([100,101],4);self.nid=np.array([f'new:{i}' for i in range(8)])
        self.splits=make_splits(self.y,self.g,3,19)

    def call(self,candidates=None,y=None,**kwargs):
        if candidates is None:
            candidates={'memory':[MemoryClassifier()]}
        return predict_stack(self.x,self.y if y is None else y,self.g,self.ids,self.new,self.ng,self.nid,
                             candidates,DummyClassifier(strategy='prior'),crossfit_splits=self.splits,seed=19,**kwargs)

    def test_oof_features_are_never_in_sample(self):
        model=MemoryClassifier()
        r=self.call({'memory':[model]})
        np.testing.assert_array_equal(r['oof_features'],np.full((96,1),0.25))
        self.assertFalse(hasattr(model,'seen_'))
        for event in r['audit']:
            if event['kind']=='fit':
                self.assertFalse(set(event['train_ids'])&set(event['predict_ids']))
                self.assertFalse(set(event['train_groups'])&set(event['predict_groups']))

    def test_all_candidate_folds_scored_and_tie_stable(self):
        audit=[]
        select_candidate(self.x,self.y,self.g,self.ids,[MemoryClassifier(.2),MemoryClassifier(.3)],
                         seed=19,n_splits=3,audit=audit,stage='test',splits=self.splits)
        record=audit[-1]
        self.assertEqual(np.asarray(record['fold_scores']).shape,(2,3))
        self.assertEqual(record['selected'],0)
        self.assertEqual(sum(e['kind']=='fit' for e in audit),6)

    def test_nested_tuning_excludes_oof_groups(self):
        r=self.call({'memory':[MemoryClassifier(.2),MemoryClassifier(.8)]})
        for fold,(_,valid) in enumerate(self.splits):
            excluded=set(self.ids[valid])
            events=[e for e in r['audit'] if e['stage'].startswith(f'memory/oof{fold}/tune')]
            self.assertTrue(events)
            for e in events:
                consulted=set(e.get('train_ids',e.get('training_ids',[])))|set(e.get('predict_ids',[]))
                self.assertFalse(consulted&excluded)

    def test_oof_predictions_unchanged_when_its_labels_change(self):
        candidates={'linear':[make_pipeline(StandardScaler(),LogisticRegression(C=c,random_state=1)) for c in [.1,1]]}
        a=self.call(candidates)
        changed=self.y.copy();valid=self.splits[0][1];changed[valid]=1-changed[valid]
        b=self.call(candidates,y=changed)
        np.testing.assert_array_equal(a['oof_features'][valid],b['oof_features'][valid])

    def test_rejects_group_overlap_and_invalid_crossfit(self):
        self.ng[0]=self.g[0]
        with self.assertRaises(ValueError):self.call()
        self.ng[0]=100
        self.splits=[self.splits[0]]*3
        with self.assertRaises(ValueError):self.call()

    def test_positive_probability_uses_class_order(self):
        class Reversed:
            classes_=np.array([1,0])
            def predict_proba(self,x):return np.tile([.8,.2],(len(x),1))
        np.testing.assert_array_equal(positive_probability(Reversed(),self.new),np.full(8,.8))

    def test_nonconverged_models_stop_strict_evaluation(self):
        with self.assertRaisesRegex(ValueError,'Nonconverged'):
            self.call({'MLP':[MLPClassifier(hidden_layer_sizes=(20,),max_iter=1,random_state=1)]})

    def test_deterministic_repeated_predictions(self):
        a=self.call();b=self.call()
        np.testing.assert_array_equal(a['probability'],b['probability'])
        self.assertEqual(a['audit'],b['audit'])


if __name__=='__main__':unittest.main()
