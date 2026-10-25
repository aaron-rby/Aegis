"""Regression checks for empty and single-class evaluation datasets."""
import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import evaluate


class EvaluationTests(unittest.TestCase):
    def run_evaluation(self, negatives=False):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root/'data/person').mkdir(parents=True)
            (root/'data/person/frame.jpg').write_bytes(b'mocked image')
            if negatives:
                (root/'data/no_person').mkdir()
                (root/'data/no_person/empty.jpg').write_bytes(b'mocked image')
            def detect(image, **kwargs):
                boxes = [] if image.parent.name == 'no_person' else [
                    {'confidence': 0.9, 'area': 0.1, 'height': 0.5, 'aspect': 1.0}]
                return boxes, 1.0, None
            with patch('sys.argv', ['evaluate.py', '--data', str(root/'data'), '--output', str(root/'out')]), \
                 patch.object(evaluate.detector, 'detect', side_effect=detect), \
                 contextlib.redirect_stdout(io.StringIO()):
                evaluate.main()
            report = json.loads((root/'out/report.json').read_text())
            return next(m for m in report['thresholds'] if m['threshold'] == 0.5)

    def test_positive_only_does_not_claim_false_alarm_rate(self):
        row = self.run_evaluation()
        self.assertEqual(row['recall'], 1)
        self.assertIsNone(row['negative_image_false_positive_rate'])
        self.assertIsNone(row['precision'])

    def test_labeled_positive_and_negative_metrics(self):
        row = self.run_evaluation(negatives=True)
        self.assertEqual((row['TP'], row['TN'], row['FP'], row['FN']), (1, 1, 0, 0))
        self.assertEqual(row['F1'], 1)

    def test_empty_dataset_fails_clearly(self):
        with tempfile.TemporaryDirectory() as temp:
            with patch('sys.argv', ['evaluate.py', '--data', temp, '--output', str(Path(temp)/'out')]):
                with self.assertRaisesRegex(SystemExit, 'No supported images'):
                    evaluate.main()


if __name__ == '__main__':
    unittest.main()
