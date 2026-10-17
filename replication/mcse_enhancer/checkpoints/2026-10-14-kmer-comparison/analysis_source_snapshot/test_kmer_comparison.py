"""Guard the controlled feature contrast and the explicit run specification."""
import itertools
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import numpy as np
from compare_kmers import check_feature_change
from evaluate_repaired import run


class ControlledFeaturesTests(unittest.TestCase):
    def setUp(self):
        self.sequences=['ACGT'*50,'A'*200]
        self.names=[];self.arrays=[]
        for k in [2,3]:
            words=[''.join(w) for w in itertools.product('ACGT',repeat=k)]
            names=['shared:first']+[f'Kmer{k}:{w}' for w in words]+['shared:last']
            values=[]
            for seq in self.sequences:
                windows=[seq[i:i+k] for i in range(len(seq)-k+1)]
                values.append([7]+[windows.count(w)/len(windows) for w in words]+[9])
            self.names.append(names);self.arrays.append(np.array(values,dtype=float))

    def check(self):
        return check_feature_change(*self.arrays,*self.names,self.sequences)

    def test_common_features_and_independent_windows(self):
        self.assertEqual(self.check()['common_columns_exactly_equal'],2)

    def test_changed_common_feature_rejected(self):
        self.arrays[1][0,-1]+=1
        with self.assertRaises(AssertionError):self.check()

    def test_wrong_denominator_and_permuted_identity_rejected(self):
        self.arrays[1][:,1:-1]*=198/200
        with self.assertRaises(AssertionError):self.check()
        self.setUp();self.names[1][0]='wrong'
        with self.assertRaises(AssertionError):self.check()

    def test_variant_mismatch_fails_before_writing_output(self):
        with tempfile.TemporaryDirectory() as directory:
            spec=Path(directory)/'spec.json';spec.write_text(json.dumps({'feature_variant':'notebook_k2_full'}))
            out=Path(directory)/'output'
            with patch('evaluate_repaired.load_matrix',return_value=(None,)*6):
                with self.assertRaisesRegex(ValueError,'variant must match'):
                    run('k3_full','plan',out,spec)
            self.assertFalse(out.exists())


if __name__=='__main__':unittest.main()
