"""Check that preparation preserves labels and rejects changed source inputs."""
import csv
import importlib.util
import json
import shutil
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).with_name('prepare_data.py')
spec = importlib.util.spec_from_file_location('prepare_data', SCRIPT)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class PreparationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / 'source'
        self.output = Path(self.temp.name) / 'output'
        for name in [*module.FILES, *module.REFERENCES, module.REVIEW, module.LABELS]:
            target = self.root / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(module.ROOT / name, target)

    def test_labels_overlap_and_repeatability(self):
        result = module.prepare(self.root, self.output)
        self.assertEqual(result['benchmark_classes'], {'strong': 742, 'weak': 742, 'non-enhancer': 1484})
        self.assertEqual(result['exact_training_overlaps'], 100)
        with (self.output / 'benchmark.csv').open() as stream:
            rows = list(csv.DictReader(stream))
        for row in rows:
            self.assertEqual(row['is_enhancer'], '0' if row['class_label'] == 'non-enhancer' else '1')
            self.assertEqual(row['is_strong'], {'strong': '1', 'weak': '0', 'non-enhancer': ''}[row['class_label']])
        with (self.output / 'legacy_test_diagnostic_only.csv').open() as stream:
            historical = list(csv.DictReader(stream))
        self.assertEqual(sum(row['exact_training_overlap'] == '1' for row in historical), 100)
        self.assertTrue(all(row['class_label'] == 'strong' for row in historical if row['exact_training_overlap'] == '1'))
        before = {p.name: p.read_bytes() for p in self.output.iterdir()}
        module.prepare(self.root, self.output)
        self.assertEqual(before, {p.name: p.read_bytes() for p in self.output.iterdir()})
        self.assertNotIn(str(self.root), json.dumps(result))

    def test_changed_original_stops_before_writing(self):
        file = self.root / 'enhancer.cv.txt'
        file.write_bytes(file.read_bytes() + b'\n')
        with self.assertRaisesRegex(ValueError, 'does not match reviewed bytes'):
            module.prepare(self.root, self.output)
        self.assertFalse(self.output.exists())

    def test_mismatched_crosswalk_stops_before_writing(self):
        path = self.root / module.LABELS
        with path.open(newline='') as stream:
            rows = list(csv.DictReader(stream, delimiter='\t'))
        rows[0]['sequence_sha256'] = '0' * 64
        with path.open('w', newline='') as stream:
            writer = csv.DictWriter(stream, fieldnames=rows[0].keys(), delimiter='\t')
            writer.writeheader(); writer.writerows(rows)
        with self.assertRaisesRegex(ValueError, 'crosswalk does not match'):
            module.prepare(self.root, self.output)
        self.assertFalse(self.output.exists())

    def test_multiline_fasta_keeps_sequence_identity(self):
        path = Path(self.temp.name) / 'wrapped.fasta'
        path.write_text('>sample 1\nacgt\nACGT\n\n>sample 2\nTT\nAA\n')
        self.assertEqual(module.fasta(path), [('sample 1', 'ACGTACGT'), ('sample 2', 'TTAA')])


if __name__ == '__main__':
    unittest.main()
