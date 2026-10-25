"""Local integration checks: real inference, upload parsing, camera faults and busy handling."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import cv2
import numpy as np
from fastapi.testclient import TestClient
import detector
import server

class ServiceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.old = server.CAPTURES
        server.CAPTURES = Path(cls.temp.name)
        cls.client_context = TestClient(server.app)
        cls.client = cls.client_context.__enter__()
        cls.jpeg = cv2.imencode('.jpg', np.zeros((240, 320, 3), dtype=np.uint8))[1].tobytes()

    @classmethod
    def tearDownClass(cls):
        cls.client_context.__exit__(None, None, None)
        server.CAPTURES = cls.old
        cls.temp.cleanup()

    def test_upload_and_unique_saves(self):
        for _ in range(2):
            r = self.client.post('/verify', content=self.jpeg, headers={'Content-Type': 'image/jpeg'})
            self.assertEqual(r.status_code, 200)
            self.assertFalse(r.json()['person'])
        self.assertGreaterEqual(len(list(server.CAPTURES.glob('*.jpg'))), 2)

    def test_multipart(self):
        r = self.client.post('/verify', files={'file': ('frame.jpg', self.jpeg, 'image/jpeg')})
        self.assertEqual(r.status_code, 200)

    def test_bad_uploads(self):
        for body in (b'', b'not an image'):
            self.assertEqual(self.client.post('/verify', content=body).status_code, 400)
        self.assertEqual(self.client.post('/verify', content=b'x'*(server.MAX_UPLOAD+1)).status_code, 413)

    def test_camera_unconfigured(self):
        with patch.object(server, 'CAMERA_URL', ''):
            self.assertEqual(self.client.post('/check').status_code, 503)

    def test_camera_success_and_failure(self):
        class Response:
            status_code = 200
            content = self.jpeg
            def raise_for_status(self):
                pass
        with patch.object(server, 'CAMERA_URL', 'http://camera/capture'), patch.object(server.requests, 'request', return_value=Response()):
            r = self.client.post('/check')
            self.assertEqual(r.status_code, 200)
            self.assertEqual(r.json()['frames'], server.CHECK_FRAMES)
        with patch.object(server, 'CAMERA_URL', 'http://camera/capture'):
            server.CHECK_LOCK.acquire()
            try:
                self.assertEqual(self.client.post('/check').status_code, 409)
            finally:
                server.CHECK_LOCK.release()

    def test_positive_real_image(self):
        image = detector.ROOT / 'data/person/coco_000000011699.jpg'
        self.assertTrue(detector.verify_person(image)['person'])

    def test_camera_failure_is_not_clear(self):
        import requests
        with patch.object(server, 'CAMERA_URL', 'http://camera/capture'), \
             patch.object(server.requests, 'request', side_effect=requests.Timeout('test timeout')), \
             patch.object(server.time, 'sleep'):
            self.assertEqual(self.client.post('/check').status_code, 502)
        self.assertFalse(server.CHECK_LOCK.locked())

if __name__ == '__main__':
    unittest.main()
