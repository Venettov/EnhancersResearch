"""Checks for the statistics reported from held-out benchmark predictions."""
import unittest
import numpy as np
from sklearn.metrics import accuracy_score, matthews_corrcoef, roc_auc_score
from summarize_benchmark import metrics, paired_bootstrap


class SummaryTests(unittest.TestCase):
    def test_rank_auc_matches_library_with_probability_ties(self):
        rng=np.random.default_rng(16)
        for n in [12,100,2968]:
            y=np.arange(n)%2;score=rng.choice([0.,.2,.5,.8,1.],n);pred=score>=.5
            result=metrics(y,score,pred)
            np.testing.assert_allclose([result['accuracy'],result['auroc'],result['mcc']],
                [accuracy_score(y,pred),roc_auc_score(y,score),matthews_corrcoef(y,pred)],rtol=0,atol=1e-14)

    def test_constant_scores_and_confusion_counts(self):
        y=np.array([0,0,1,1]);result=metrics(y,np.full(4,.5),np.ones(4))
        self.assertEqual([result[k] for k in ['tn','fp','fn','tp']],[0,2,0,2])
        self.assertEqual(result['auroc'],.5);self.assertEqual(result['mcc'],0.)

    def test_paired_bootstrap_identical_and_opposite_predictions(self):
        y=np.arange(60)%2;groups=np.repeat(np.arange(30),2);folds=np.repeat(np.arange(3),20)
        result=paired_bootstrap(y,y,1-y,groups,folds,100,16)
        self.assertEqual(result['mcse_accuracy_interval'],[1.,1.])
        self.assertEqual(result['mcse_minus_reference_accuracy_interval'],[1.,1.])
        self.assertEqual(paired_bootstrap(y,y,y,groups,folds,100,16)['mcse_minus_reference_accuracy_interval'],[0.,0.])

    def test_bootstrap_keeps_unequal_groups_whole_and_paired(self):
        groups=np.repeat(np.arange(8),[1,2,3,4,2,3,4,5]);folds=groups//4
        rng=np.random.default_rng(27);y=rng.integers(2,size=len(groups))
        a=rng.integers(2,size=len(groups));b=rng.integers(2,size=len(groups))
        actual=paired_bootstrap(y,a,b,groups,folds,200,33)
        # Slow row-level oracle explicitly repeats all members of sampled groups.
        rng=np.random.default_rng(33);accuracy=[];difference=[]
        for _ in range(200):
            members=[]
            for fold in [0,1]:
                unique=np.unique(groups[folds==fold])
                for group in rng.choice(unique,size=len(unique),replace=True):
                    members.extend(np.flatnonzero(groups==group))
            accuracy.append(float(np.mean(a[members]==y[members])))
            difference.append(float(np.mean(a[members]==y[members])-np.mean(b[members]==y[members])))
        np.testing.assert_allclose(actual['mcse_accuracy_interval'],np.quantile(accuracy,[.025,.975]),atol=1e-14,rtol=0)
        np.testing.assert_allclose(actual['mcse_minus_reference_accuracy_interval'],np.quantile(difference,[.025,.975]),atol=1e-14,rtol=0)


if __name__=='__main__':unittest.main()
