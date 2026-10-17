"""Small independent fixtures for scientific eligibility and leakage checks."""
import hashlib
import unittest
from audit_readiness import coordinate,exact_hits,legacy_index,qc,rc,windows

class ReadinessTests(unittest.TestCase):
    def row(self,sequence='A'*200):
        return {'seq':sequence,'seq_hg38':sequence,'coordinate_hg38':'chr1:101-300','coord':'chr1:101-300','vista_id':'hs_test'}
    def test_coordinate_conversion_matches_bed(self):
        self.assertEqual(coordinate('chr1:101-300'),('chr1',100,300))
        self.assertIsNone(qc(self.row(),{'hs_test':{('chr1',100,300)}}))
    def test_zero_based_string_rejected(self):
        with self.assertRaises(ValueError):coordinate('chr1:0-200')
    def test_short_fragment_not_padded(self):
        with self.assertRaises(ValueError):windows(199)
    def test_terminal_tile_is_covered_once(self):
        self.assertEqual(windows(200),[0]);self.assertEqual(windows(251),[0,50,51]);self.assertEqual(windows(300),[0,50,100])
    def test_non_stride_exact_match_is_found(self):
        s='ACGT'*50
        r={'sequence':s,'sequence_sha256':hashlib.sha256(s.encode()).hexdigest(),'file':'legacy','row_1_based':'1'}
        self.assertEqual(exact_hits('G'*17+s+'C'*13,legacy_index([r])),['legacy:1'])
    def test_reverse_complement_and_multiple_sources_retained(self):
        s='A'*199+'C';rows=[{'sequence':s,'sequence_sha256':hashlib.sha256(s.encode()).hexdigest(),'file':'legacy','row_1_based':str(i)} for i in (1,2)]
        self.assertEqual(exact_hits('G'*7+rc(s),legacy_index(rows)),['legacy:1','legacy:2'])
    def test_near_match_is_not_claimed_as_exact(self):
        s='A'*200;row={'sequence':s,'sequence_sha256':hashlib.sha256(s.encode()).hexdigest(),'file':'legacy','row_1_based':'1'}
        self.assertEqual(exact_hits('A'*199+'C',legacy_index([row])),[])
    def test_invalid_legacy_hash_stops_audit(self):
        with self.assertRaises(ValueError):legacy_index([{'sequence':'A'*200,'sequence_sha256':'bad'}])
    def test_reference_reverse_orientation_allowed(self):
        row=self.row('A'*199+'C');row['seq']=rc(row['seq_hg38']);self.assertIsNone(qc(row,{'hs_test':{('chr1',100,300)}}))
    def test_mutation_ambiguity_and_coordinate_mismatch_rejected(self):
        row=self.row();row['seq']='A'*199+'C';self.assertEqual(qc(row,{}),'tested_reference_sequence_mismatch')
        row=self.row('N'+'A'*199);self.assertEqual(qc(row,{}),'ambiguous_or_missing_sequence')
        row=self.row();self.assertEqual(qc(row,{'hs_test':{('chr1',101,301)}}),'coordinate_bed_mismatch')

if __name__=='__main__':unittest.main()
