"""Fail-closed checks for the planning audit, using no real assay outcomes."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from audit_readiness import audit


class PlanningAuditTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.models = {}
        artifacts = {}
        for layer in ('layer1', 'layer2'):
            path = self.root / f'{layer}.npz'
            path.write_bytes(f'opaque frozen artifact {layer}'.encode())
            sha = hashlib.sha256(path.read_bytes()).hexdigest()
            self.models[layer] = {'path': path.name, 'sha256': sha}
            artifacts[f'models/{layer}_final.npz'] = sha
        (self.root / 'training.json').write_text(json.dumps({'artifact_sha256': artifacts}))
        (self.root / 'source.txt').write_text('frozen reference export')
        self.protocol = {
            'protocol_id': 'ienhancer-2l-independent-vista-v1',
            'input_sha256': {'source.txt': hashlib.sha256((self.root / 'source.txt').read_bytes()).hexdigest()},
            'primary_model': {'training_audit': 'training.json', 'artifacts': self.models},
            'gates_before_external_scoring': ['source_integrity', 'frozen_primary_model', 'near_sequence_screen'],
            'prior_information': {'archived_vista_audit': 'old-audit.json', 'archived_vista_counts': {'fragments': 1847}},
        }

    def test_source_and_model_integrity_never_certify_a_cohort(self):
        result = audit(self.protocol, self.root)
        self.assertFalse(result['independence_verified'])
        self.assertFalse(result['scoring_allowed'])
        self.assertIsNone(result['final_fragments'])
        self.assertEqual(result['gates']['near_sequence_screen'], 'pending')
        self.assertIsNone(result['external_metrics'])
        self.assertEqual(result['external_predictions'], 0)

    def test_changed_source_is_rejected(self):
        (self.root / 'source.txt').write_text('refreshed data')
        with self.assertRaisesRegex(ValueError, 'changed pinned input'):
            audit(self.protocol, self.root)

    def test_changed_model_is_rejected(self):
        (self.root / 'layer1.npz').write_bytes(b'a replacement model')
        with self.assertRaisesRegex(ValueError, 'Historical model changed'):
            audit(self.protocol, self.root)

    def test_repinning_model_cannot_disagree_with_historical_audit(self):
        path = self.root / 'layer1.npz'
        path.write_bytes(b'a replacement model')
        self.models['layer1']['sha256'] = hashlib.sha256(path.read_bytes()).hexdigest()
        with self.assertRaisesRegex(ValueError, 'differs from historical training audit'):
            audit(self.protocol, self.root)


if __name__ == '__main__':
    unittest.main()
