"""Phase 2 receiver and API integration checks on an isolated temporary store."""
import json
from io import BytesIO
from pathlib import Path
import sys
import tempfile
import threading
import unittest
from unittest.mock import Mock
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from http.server import ThreadingHTTPServer
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from server import make_handler
from storage import Store, camera_parts


class BackendTest(unittest.TestCase):
    def test_alarm_route_authentication_without_socket(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            captures, predictions = root / "captures", root / "predictions"
            captures.mkdir()
            predictions.mkdir()
            store = Store(root / "app.sqlite3", captures, predictions)

            def request(secret, supplied):
                handler_type = make_handler(store, "camera-token", root / "model.pt", secret)
                handler = handler_type.__new__(handler_type)
                handler.path = "/api/alarm/latest"
                handler.headers = {"X-Alarm-Token": supplied}
                handler.wfile = BytesIO()
                handler.send_response = Mock()
                handler.send_header = Mock()
                handler.end_headers = Mock()
                handler.do_GET()
                return handler.send_response.call_args.args[0], handler.wfile.getvalue()

            self.assertEqual(request(None, "anything")[0], 503)
            self.assertEqual(request("alarm-secret-token", "wrong")[0], 401)
            self.assertEqual(request("alarm-secret-token", "alarm-secret-token"), (200, b""))

    def test_variable_width_camera_id_and_existing_photo_backfill(self):
        identifier = "582ABD7BB88C-9e5dca0-2-5"
        self.assertEqual(camera_parts(identifier), ("582ABD7BB88C-9e5dca0-2", 5))
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            captures, predictions = root / "captures", root / "predictions"
            captures.mkdir()
            predictions.mkdir()
            database = root / "app.sqlite3"
            store = Store(database, captures, predictions)
            with store.connect() as db:
                db.execute("""INSERT INTO photos
                    (id,burst_id,photo_number,received_at,file_path,size,ml_state)
                    VALUES (?,NULL,NULL,?,?,?,'queued')""",
                    (identifier, "2026-10-24T14:29:00+00:00", str(captures / (identifier + ".jpg")), 100))
            repaired = Store(database, captures, predictions)
            self.assertEqual(repaired.photo(identifier)["burst_id"], "582ABD7BB88C-9e5dca0-2")
            self.assertEqual(repaired.photo(identifier)["photo_number"], 5)
            self.assertEqual(repaired.bursts_page(1, 10)["items"][0]["received"], 1)

    def test_camera_contract_and_index(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            captures, predictions = root / "captures", root / "predictions"
            captures.mkdir()
            predictions.mkdir()
            model = root / "yolo11m.pt"
            model.write_bytes(b"test fixture")
            store = Store(root / "app.sqlite3", captures, predictions)
            server = ThreadingHTTPServer(("127.0.0.1", 0),
                                         make_handler(store, "token", model, "alarm-secret-token"))
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            base = f"http://127.0.0.1:{server.server_port}"
            image_stream = BytesIO()
            Image.new("RGB", (8, 8), "blue").save(image_stream, format="JPEG")
            jpeg = image_stream.getvalue()

            def get(path):
                with urlopen(base + path, timeout=3) as response:
                    return response.status, response.read()

            def get_alarm(token="alarm-secret-token"):
                request = Request(base + "/api/alarm/latest",
                                  headers={"X-Alarm-Token": token})
                try:
                    with urlopen(request, timeout=3) as response:
                        return response.status, response.read()
                except HTTPError as error:
                    error.close()
                    return error.code, b""

            def post(identifier, data=jpeg, token="token"):
                request = Request(base + "/upload?id=" + identifier, data=data,
                                  headers={"Content-Type": "image/jpeg", "X-Camera-Token": token})
                try:
                    with urlopen(request, timeout=3) as response: return response.status
                except HTTPError as error:
                    error.close()
                    return error.code

            try:
                names = [f"582ABD7BB88C-3cae8d1e-1-{i}" for i in range(1, 6)]
                for identifier in names: self.assertEqual(post(identifier), 201)
                self.assertEqual(get_alarm("wrong")[0], 401)
                self.assertEqual(get_alarm(), (200, b""))
                before_retry = json.loads(get("/api/status")[1])["last_camera_upload"]
                self.assertEqual(post(names[0]), 200)
                self.assertEqual(json.loads(get("/api/status")[1])["last_camera_upload"], before_retry)
                self.assertEqual(post(names[0], jpeg + b"\xff\xd9"), 409)
                self.assertEqual(post("bad", token="wrong"), 401)
                self.assertEqual(post("bad", data=b"not-a-jpeg"), 400)
                self.assertEqual(post("fake-jpeg", data=b"\xff\xd8garbage\xff\xd9"), 400)
                self.assertEqual(post("..%2Fescape"), 400)
                self.assertEqual(len(list(captures.glob("*.jpg"))), 5)
                self.assertFalse(list(captures.glob("*.part")))

                page = json.loads(get("/api/photos?page=2&per_page=2")[1])
                self.assertEqual((page["total"], page["page"], len(page["items"])), (5, 2, 2))
                self.assertEqual(page["items"][0]["burst_id"], "582ABD7BB88C-3cae8d1e-1")
                self.assertEqual(page["items"][0]["ml_state"], "queued")
                pending = json.loads(get("/api/photos?person=pending&burst_id=582ABD7BB88C-3cae8d1e-1")[1])
                self.assertEqual(pending["total"], 5)
                empty = json.loads(get("/api/photos?person=person")[1])
                self.assertEqual(empty["total"], 0)
                for invalid in ("/api/photos?person=unknown", "/api/photos?burst_id=..%2Fbad"):
                    try: get(invalid)
                    except HTTPError as error:
                        self.assertEqual(error.code, 400)
                        error.close()
                    else: self.fail(f"Expected validation error for {invalid}")
                burst = json.loads(get("/api/bursts")[1])
                self.assertEqual((burst["total"], burst["items"][0]["received"]), (1, 5))
                self.assertEqual(get("/photos/" + names[0] + ".jpg")[1], jpeg)
                self.assertEqual(json.loads(get("/api/photos/" + names[0])[1])["id"], names[0])
                index = get("/")[1]
                self.assertTrue(b"Aegis" in index or b"Sentinel AI" in index or b"Vigil" in index or b"Intruder camera gallery" in index)
                if b"Vigil" in index or b"Sentinel AI" in index:
                    import re
                    asset = re.search(rb'src="(/assets/[^"]+\.js)"', index)
                    self.assertIsNotNone(asset)
                    self.assertGreater(len(get(asset.group(1).decode())[1]), 1000)

                record = {"source": str(captures / (names[0] + ".jpg")),
                          "classification": "PERSON DETECTED", "person": True,
                          "confidence": 0.82, "processed_at": "2026-10-20T19:14:18+05:30",
                          "annotated_image": "annotated.jpg"}
                (predictions / "annotated.jpg").write_bytes(jpeg)
                (predictions / "result.json").write_text(json.dumps(record), encoding="utf-8")
                item = json.loads(get("/api/photos/" + names[0])[1])
                self.assertEqual(item["ml_state"], "person_detected")
                # Imported legacy watcher results do not sound the physical alarm.
                self.assertEqual(get_alarm(), (200, b""))
                job = store.claim_job("test-worker")
                self.assertEqual(job["id"], names[1])
                store.finish_job(names[1], "person_detected",
                                 {"classification": "PERSON DETECTED", "person": True,
                                  "confidence": 0.8})
                self.assertEqual(get_alarm(), (200, b"582ABD7BB88C-3cae8d1e-1"))
                self.assertEqual(get(item["annotated_url"])[1], jpeg)
                self.assertEqual(len(json.loads(get("/api/ml-results")[1])["results"]), 2)
                self.assertIn(b"No person detected is a model result", get("/ml/")[1])
                status = json.loads(get("/api/status")[1])
                self.assertTrue(status["backend"]["alive"])
                self.assertFalse(status["worker"]["running"])
                self.assertEqual(status["jobs"]["queued"], 3)
                self.assertEqual(camera_parts("device-session-1-1"), (None, None))
                with store.connect() as db:
                    db.execute("DELETE FROM photos WHERE id=?", (names[2],))
                incomplete = json.loads(get("/api/bursts")[1])["items"][0]
                self.assertEqual(incomplete["received"], 4)
                self.assertEqual(set(map(int, incomplete["photo_numbers"].split(","))), {1, 2, 4, 5})
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=3)


if __name__ == "__main__": unittest.main()
