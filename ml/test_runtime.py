"""Check camera failure paths without activating physical cameras."""
import contextlib
import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch
import cv2
import numpy as np
import requests
import test_camera
import webcam


class WebcamCleanupTests(unittest.TestCase):
    def test_inference_failure_releases_camera(self):
        camera = MagicMock()
        camera.read.return_value = (True, np.zeros((100, 100, 3), dtype=np.uint8))
        with patch.object(webcam.detector, 'get_model'), patch.object(webcam, 'open_camera', return_value=camera), \
             patch.object(webcam.detector, 'verify_person', side_effect=RuntimeError('inference failed')), \
             patch.object(webcam.cv2, 'destroyAllWindows') as close, contextlib.redirect_stdout(io.StringIO()):
            with self.assertRaisesRegex(RuntimeError, 'inference failed'):
                webcam.run()
        camera.release.assert_called_once()
        close.assert_called_once()

    def test_read_failure_is_reported_and_releases_camera(self):
        camera = MagicMock()
        camera.read.return_value = (False, None)
        with patch.object(webcam.detector, 'get_model'), patch.object(webcam, 'open_camera', return_value=camera), \
             patch.object(webcam.cv2, 'destroyAllWindows'), contextlib.redirect_stdout(io.StringIO()):
            with self.assertRaisesRegex(RuntimeError, 'stopped providing frames'):
                webcam.run()
        camera.release.assert_called_once()

    def test_quit_key_releases_camera(self):
        camera = MagicMock()
        image = np.zeros((100, 100, 3), dtype=np.uint8)
        camera.read.return_value = (True, image)
        with patch.object(webcam.detector, 'get_model'), patch.object(webcam, 'open_camera', return_value=camera), \
             patch.object(webcam.detector, 'verify_person', return_value={'person': False, 'ms': 1}), \
             patch.object(webcam.detector, 'annotate', return_value=image), patch.object(webcam.cv2, 'imshow'), \
             patch.object(webcam.cv2, 'waitKey', return_value=ord('q')), \
             patch.object(webcam.cv2, 'destroyAllWindows'), contextlib.redirect_stdout(io.StringIO()):
            webcam.run()
        camera.release.assert_called_once()


class CameraDiagnosticTests(unittest.TestCase):
    def invoke(self, response):
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp)/'capture.jpg'
            with patch('sys.argv', ['test_camera.py', '--output', str(output)]), \
                 patch.dict('os.environ', {'CAMERA_URL': 'http://camera/capture', 'CAMERA_TOKEN': ''}), \
                 patch.object(test_camera.requests, 'request', return_value=response), \
                 contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                result = test_camera.main()
            return result, output.read_bytes() if output.exists() else None

    def test_invalid_http_200_image_is_not_saved(self):
        response = MagicMock(headers={'content-type': 'image/jpeg'}, content=b'\xff\xd8invalid\xff\xd9')
        self.assertEqual(self.invoke(response), (1, None))

    def test_http_error_returns_failure(self):
        response = MagicMock()
        response.raise_for_status.side_effect = requests.HTTPError('401 unauthorized')
        self.assertEqual(self.invoke(response), (1, None))

    def test_valid_image_is_saved(self):
        data = cv2.imencode('.jpg', np.zeros((100, 100, 3), dtype=np.uint8))[1].tobytes()
        response = MagicMock(headers={'content-type': 'image/jpeg'}, content=data)
        self.assertEqual(self.invoke(response), (0, data))


if __name__ == '__main__':
    unittest.main()
