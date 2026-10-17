"""Independent normalization oracles and guards for the fixed representation change."""
import itertools
import unittest
from unittest.mock import patch
import numpy as np
from normalization_features import paper_word_frequencies, load_matrix
from compare_normalization import check_feature_change, probability_diagnostics


class NormalizationTests(unittest.TestCase):
    def setUp(self):
        self.words=[''.join(w) for w in itertools.product('ACGT',repeat=3)]
        self.sequences=['ACGT','AAAAA','ACGT'*50]
        self.names=np.array(['shared:first']+['Kmer3:'+w for w in self.words]+['shared:last'])
        rows=[]
        for s in self.sequences:
            windows=[s[i:i+3] for i in range(len(s)-2)]
            rows.append([7]+[windows.count(w)/len(windows) for w in self.words]+[9])
        self.a=np.array(rows,dtype=float);self.b=self.a.copy()
        self.b[:,1:-1]=paper_word_frequencies(self.sequences,self.words)

    def test_hand_count_and_variable_length_denominator(self):
        self.assertEqual(self.b[0,1+self.words.index('ACG')],.25)
        self.assertEqual(self.b[0,1+self.words.index('CGT')],.25)
        self.assertEqual(self.b[1,1+self.words.index('AAA')],.6)
        np.testing.assert_allclose(self.b[:,1:-1].sum(axis=1),[.5,.6,.99],rtol=0,atol=1e-15)
        self.assertEqual(check_feature_change(self.a,self.b,self.names,self.names,self.sequences)['common_columns_exactly_equal'],2)

    def test_wrong_denominator_and_changed_shared_column_rejected(self):
        with self.assertRaises(AssertionError):check_feature_change(self.a,self.a,self.names,self.names,self.sequences)
        self.b[0,-1]+=1
        with self.assertRaises(AssertionError):check_feature_change(self.a,self.b,self.names,self.names,self.sequences)

    def test_invalid_sequences_and_column_identities_rejected(self):
        for seq in ['AC','ANN','acg','']:
            with self.assertRaises(ValueError):paper_word_frequencies([seq],self.words)
        with self.assertRaises(ValueError):paper_word_frequencies(['ACGT'],self.words[:-1]+[self.words[0]])
        names=self.names.copy();names[1],names[2]=names[2],names[1]
        with self.assertRaises(AssertionError):check_feature_change(self.a,self.b,self.names,names,self.sequences)

    def test_word_order_is_explicit(self):
        reverse=paper_word_frequencies(self.sequences,self.words[::-1])
        np.testing.assert_array_equal(reverse[:,::-1],self.b[:,1:-1])

    def test_unapproved_variant_fails_before_loading(self):
        with patch('normalization_features.load_ilearn_matrix') as source:
            with self.assertRaises(ValueError):load_matrix('notebook_k2_full')
            source.assert_not_called()

    def test_probability_diagnostics_distinguish_scores_and_labels(self):
        a=np.array([.2,.49,.9]);b=np.array([.2+1e-14,.51,.8])
        d=probability_diagnostics(a,b)
        self.assertEqual(d['unequal_probabilities'],3)
        self.assertEqual(d['probabilities_differing_over_1e_12'],2)
        self.assertEqual(d['changed_labels_at_0_5'],1)


if __name__=='__main__':unittest.main()
