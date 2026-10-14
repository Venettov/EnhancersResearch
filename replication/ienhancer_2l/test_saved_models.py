"""Check published model artifacts against saved held-out predictions."""
import csv
import json
from pathlib import Path
import tempfile
import unittest
import numpy as np
from common import HERE, ROOT, load_benchmark, sha256
from features import pseknc
from prepare_data import prepare
from predict_svm import predict_records, validate_models
from train_svm import portable_scores

CHECKPOINT = HERE / 'checkpoints/2026-10-13-svm-training'


class SavedModelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with tempfile.TemporaryDirectory() as temp:
            prepare(ROOT, Path(temp))
            cls.rows = {r['record_id']:r for r in load_benchmark(Path(temp))}

    def test_every_artifact_retains_its_run_hash(self):
        audit = json.loads((CHECKPOINT / 'training_audit.json').read_text())
        self.assertEqual(audit['status'], 'complete')
        for name, expected in audit['artifact_sha256'].items():
            self.assertEqual(sha256(CHECKPOINT / name), expected, name)

    def test_fold_models_exclude_held_out_records_and_replay_scores(self):
        validate_models(CHECKPOINT / 'models')
        for layer, weight in [('layer1',0.1),('layer2',0.4)]:
            with (CHECKPOINT / f'{layer}_held_out_predictions.csv').open(newline='') as stream:
                predictions = list(csv.DictReader(stream))
            self.assertEqual(len({r['record_id'] for r in predictions}), len(predictions))
            for fold in range(5):
                selected = [r for r in predictions if int(r['outer_fold']) == fold]
                path = CHECKPOINT / 'models' / f'{layer}_outer_{fold}.npz'
                with np.load(path, allow_pickle=False) as model:
                    self.assertFalse(set(model['support_record_ids']) & {r['record_id'] for r in selected})
                # Rebuild independent rows directly from the original FASTAs.
                samples = selected[:2] + selected[-2:]
                X = np.asarray([pseknc(self.rows[r['record_id']]['sequence'], weight=weight) for r in samples])
                scores = portable_scores(path, X)
                np.testing.assert_allclose(scores, [float(r['decision_score']) for r in samples], atol=1e-7, rtol=0)
                np.testing.assert_array_equal((scores > 0).astype(int), [int(r['predicted_label']) for r in samples])

    def test_cascade_uses_layer_two_only_after_positive_layer_one(self):
        records = [(r['record_id'],r['sequence']) for r in list(self.rows.values())[::50]]
        result = predict_records(records, CHECKPOINT / 'models')
        self.assertEqual(len(result),len(records))
        self.assertTrue(any(r['predicted_class']=='non-enhancer' for r in result))
        self.assertTrue(any(r['predicted_class']!='non-enhancer' for r in result))
        for r in result:
            self.assertEqual(r['strength_decision_score']=='',r['enhancer_decision_score'] <= 0)
        with self.assertRaisesRegex(ValueError,'exactly 200'):
            predict_records([('invalid','ACGT')], CHECKPOINT / 'models')


if __name__ == '__main__':
    unittest.main()
