"""SQLite index for camera photos; JPEGs and existing ML artifacts stay on disk."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from contextlib import contextmanager
import json
from pathlib import Path
import re
import sqlite3

# The camera prints its session token as hexadecimal without leading zeroes.
CAMERA_ID = re.compile(r"^([0-9A-Fa-f]{12})-([0-9A-Fa-f]{1,8})-([1-9][0-9]*)-([1-5])$")


def camera_parts(identifier: str):
    """Only interpret IDs matching the observed camera format; keep all IDs intact."""
    match = CAMERA_ID.fullmatch(identifier)
    if not match:
        return None, None
    return "-".join(match.groups()[:3]), int(match.group(4))


class Store:
    def __init__(self, db_path: Path, captures: Path, predictions: Path):
        self.db_path = Path(db_path).resolve()
        self.captures = Path(captures).resolve()
        self.predictions = Path(predictions).resolve()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS photos (
                    id TEXT PRIMARY KEY,
                    burst_id TEXT,
                    photo_number INTEGER,
                    received_at TEXT NOT NULL,
                    file_path TEXT NOT NULL,
                    size INTEGER NOT NULL,
                    ml_state TEXT NOT NULL DEFAULT 'queued',
                    prediction TEXT,
                    error TEXT
                );
                CREATE INDEX IF NOT EXISTS photos_received ON photos(received_at DESC, id DESC);
                CREATE INDEX IF NOT EXISTS photos_burst ON photos(burst_id, photo_number);
                CREATE TABLE IF NOT EXISTS service_state (
                    name TEXT PRIMARY KEY, value TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS ml_jobs (
                    photo_id TEXT PRIMARY KEY REFERENCES photos(id),
                    state TEXT NOT NULL,
                    attempts INTEGER NOT NULL DEFAULT 0,
                    queued_at TEXT NOT NULL,
                    started_at TEXT,
                    finished_at TEXT,
                    worker_id TEXT,
                    error TEXT
                );
                CREATE INDEX IF NOT EXISTS ml_jobs_state ON ml_jobs(state,queued_at);
            """)
            migration = db.execute("SELECT value FROM service_state WHERE name='legacy_state_migrated'").fetchone()
            if not migration:
                db.execute("UPDATE photos SET ml_state='legacy_unprocessed' WHERE ml_state='queued' AND prediction IS NULL")
                db.execute("INSERT INTO service_state(name,value) VALUES ('legacy_state_migrated','1')")
            # Repair photos uploaded before variable-width camera session IDs were recognized.
            for row in db.execute("SELECT id FROM photos WHERE burst_id IS NULL").fetchall():
                burst_id, photo_number = camera_parts(row["id"])
                if burst_id is not None:
                    db.execute("UPDATE photos SET burst_id=?,photo_number=? WHERE id=?",
                               (burst_id, photo_number, row["id"]))

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.db_path, timeout=10)
        db.row_factory = sqlite3.Row
        try:
            db.execute("PRAGMA busy_timeout=10000")
            db.execute("PRAGMA journal_mode=WAL")
            yield db
            db.commit()
        except BaseException:
            db.rollback()
            raise
        finally:
            db.close()

    def add_photo(self, path: Path, received_at: str | None = None, legacy: bool = False,
                  record_upload: bool = True):
        path = Path(path).resolve()
        identifier = path.stem
        burst_id, photo_number = camera_parts(identifier)
        stat = path.stat()
        received_at = received_at or datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat()
        with self.connect() as db:
            inserted = db.execute("""INSERT OR IGNORE INTO photos
                (id,burst_id,photo_number,received_at,file_path,size,ml_state)
                VALUES (?,?,?,?,?,?,?)""",
                (identifier, burst_id, photo_number, received_at, str(path), stat.st_size,
                 "legacy_unprocessed" if legacy else "queued")).rowcount
            if not legacy and (inserted or db.execute(
                    "SELECT ml_state FROM photos WHERE id=?", (identifier,)).fetchone()[0] == "queued"):
                db.execute("""INSERT OR IGNORE INTO ml_jobs(photo_id,state,queued_at)
                    VALUES (?,'queued',?)""", (identifier, received_at))
            if not legacy and record_upload:
                db.execute("INSERT OR REPLACE INTO service_state(name,value) VALUES ('last_camera_upload',?)",
                           (json.dumps({"id": identifier, "received_at": received_at}),))

    def import_captures(self):
        count = 0
        for path in self.captures.glob("*.jpg"):
            if path.is_file():
                self.add_photo(path, legacy=True)
                count += 1
        return count

    def sync_predictions(self):
        """Import compatible result JSON from the current ML watcher, idempotently."""
        imported = 0
        for path in self.predictions.glob("*.json"):
            if path.name.endswith("-ml.json"):
                continue  # New worker commits its own DB result after atomic artifact writes.
            try:
                record = json.loads(path.read_text(encoding="utf-8"))
                identifier = Path(record["source"]).stem
                if not (self.captures / (identifier + ".jpg")).is_file():
                    continue
                classification = record.get("classification", "")
                state = ("error" if classification == "PROCESSING ERROR" else
                         "person_detected" if record.get("person") else "no_person_detected")
                if classification not in ("PROCESSING ERROR", "PERSON DETECTED", "NO PERSON DETECTED"):
                    continue
                annotated = Path(record.get("annotated_image") or "").name
                result = {
                    "classification": classification,
                    "person": bool(record.get("person", False)),
                    "confidence": float(record.get("confidence", 0) or 0),
                    "processed_at": record.get("processed_at"),
                    "annotated_image": annotated if annotated and (self.predictions / annotated).is_file() else None,
                    "count": record.get("count"),
                }
                with self.connect() as db:
                    cursor = db.execute("""UPDATE photos SET ml_state=?, prediction=?, error=?
                        WHERE id=? AND ml_state IN ('queued','processing','error','legacy_unprocessed')""",
                        (state, json.dumps(result), record.get("error"), identifier))
                    imported += cursor.rowcount
                    if cursor.rowcount:
                        db.execute("""UPDATE ml_jobs SET state=?, finished_at=?, error=?
                            WHERE photo_id=? AND state IN ('queued','processing','error')""",
                            (state, record.get("processed_at"), record.get("error"), identifier))
            except (OSError, ValueError, TypeError, KeyError, sqlite3.Error):
                continue
        return imported

    @staticmethod
    def as_photo(row):
        prediction = json.loads(row["prediction"]) if row["prediction"] else None
        return {
            "id": row["id"], "name": row["id"] + ".jpg",
            "burst_id": row["burst_id"], "photo_number": row["photo_number"],
            "received_at": row["received_at"], "size": row["size"],
            "ml_state": row["ml_state"], "prediction": prediction, "error": row["error"],
            "image_url": "/photos/" + row["id"] + ".jpg",
            "annotated_url": "/ml-images/" + prediction["annotated_image"] if prediction and prediction.get("annotated_image") else None,
        }

    def photos_page(self, page: int, per_page: int, person_filter: str = "all", burst_id: str | None = None):
        offset = (page - 1) * per_page
        states = {"person": ("person_detected",), "no_person": ("no_person_detected",),
                  "pending": ("queued", "processing", "legacy_unprocessed"), "error": ("error",)}
        conditions, parameters = [], []
        if person_filter != "all":
            selected = states[person_filter]
            conditions.append("ml_state IN (" + ",".join("?" for _ in selected) + ")")
            parameters.extend(selected)
        if burst_id is not None:
            conditions.append("burst_id=?")
            parameters.append(burst_id)
        where = " WHERE " + " AND ".join(conditions) if conditions else ""
        with self.connect() as db:
            total = db.execute("SELECT COUNT(*) FROM photos" + where, parameters).fetchone()[0]
            rows = db.execute("SELECT * FROM photos" + where + " ORDER BY received_at DESC,id DESC LIMIT ? OFFSET ?",
                              (*parameters, per_page, offset)).fetchall()
        return {"items": [self.as_photo(row) for row in rows], "page": page,
                "per_page": per_page, "total": total, "pages": (total + per_page - 1) // per_page}

    def photo(self, identifier: str):
        with self.connect() as db:
            row = db.execute("SELECT * FROM photos WHERE id=?", (identifier,)).fetchone()
        return self.as_photo(row) if row else None

    def bursts_page(self, page: int, per_page: int):
        with self.connect() as db:
            total = db.execute("SELECT COUNT(DISTINCT burst_id) FROM photos WHERE burst_id IS NOT NULL").fetchone()[0]
            rows = db.execute("""SELECT burst_id,COUNT(*) received,
                SUM(CASE WHEN ml_state IN ('person_detected','no_person_detected','error') THEN 1 ELSE 0 END) finished,
                SUM(CASE WHEN ml_state='error' THEN 1 ELSE 0 END) errors,
                GROUP_CONCAT(photo_number) photo_numbers,
                GROUP_CONCAT(CASE WHEN ml_state IN ('person_detected','no_person_detected','error') THEN photo_number END) finished_numbers,
                MIN(received_at) first_received,MAX(received_at) last_received
                FROM photos WHERE burst_id IS NOT NULL GROUP BY burst_id
                ORDER BY last_received DESC,burst_id DESC LIMIT ? OFFSET ?""",
                (per_page, (page - 1) * per_page)).fetchall()
        return {"items": [dict(row) for row in rows], "page": page,
                "per_page": per_page, "total": total, "pages": (total + per_page - 1) // per_page}

    def status(self, model: Path):
        with self.connect() as db:
            counts = {row[0]: row[1] for row in db.execute("SELECT ml_state,COUNT(*) FROM photos GROUP BY ml_state")}
            job_counts = {row[0]: row[1] for row in db.execute("SELECT state,COUNT(*) FROM ml_jobs GROUP BY state")}
            last = db.execute("SELECT value FROM service_state WHERE name='last_camera_upload'").fetchone()
            heartbeat = db.execute("SELECT value FROM service_state WHERE name='worker_heartbeat'").fetchone()
            worker_id = db.execute("SELECT value FROM service_state WHERE name='worker_id'").fetchone()
            worker_model = db.execute("SELECT value FROM service_state WHERE name='worker_model'").fetchone()
            total = db.execute("SELECT COUNT(*) FROM photos").fetchone()[0]
        # The old folder watcher has no heartbeat; never claim it is live based on files.
        heartbeat_at = heartbeat[0] if heartbeat else None
        live = False
        if heartbeat_at:
            try: live = (datetime.now(timezone.utc) - datetime.fromisoformat(heartbeat_at)).total_seconds() < 30
            except ValueError: pass
        return {"backend": {"alive": True}, "last_camera_upload": json.loads(last[0]) if last else None,
                "worker": {"running": live, "heartbeat_at": heartbeat_at,
                           "id": worker_id[0] if worker_id else None,
                           "model": worker_model[0] if worker_model else None},
                "jobs": {"queued": job_counts.get("queued", 0), "processing": job_counts.get("processing", 0),
                         "errors": job_counts.get("error", 0),
                         "legacy_unprocessed": counts.get("legacy_unprocessed", 0)},
                "photos_total": total, "configured_model": str(model)}

    def latest_alarm_event(self, max_age_seconds: int = 90):
        """Return one fresh person-detected burst from this worker, never legacy results."""
        cutoff = (datetime.now(timezone.utc) - timedelta(seconds=max_age_seconds)).isoformat()
        with self.connect() as db:
            row = db.execute("""SELECT COALESCE(p.burst_id,p.id) AS event_id
                FROM ml_jobs j JOIN photos p ON p.id=j.photo_id
                WHERE j.state='person_detected' AND p.ml_state='person_detected'
                  AND p.received_at>=? AND j.finished_at>=?
                ORDER BY j.finished_at DESC,j.photo_id DESC LIMIT 1""",
                (cutoff, cutoff)).fetchone()
        return row["event_id"] if row else None

    def recover_processing(self):
        """Only call after obtaining the exclusive worker lock."""
        with self.connect() as db:
            rows = db.execute("SELECT photo_id FROM ml_jobs WHERE state='processing'").fetchall()
            db.execute("UPDATE ml_jobs SET state='queued',started_at=NULL,worker_id=NULL WHERE state='processing'")
            db.execute("UPDATE photos SET ml_state='queued' WHERE id IN (SELECT photo_id FROM ml_jobs WHERE state='queued') AND ml_state='processing'")
        return len(rows)

    def claim_job(self, worker_id: str):
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("""SELECT p.id,p.file_path FROM ml_jobs j JOIN photos p ON p.id=j.photo_id
                WHERE j.state='queued' ORDER BY j.queued_at,j.photo_id LIMIT 1""").fetchone()
            if not row: return None
            now = datetime.now(timezone.utc).isoformat()
            db.execute("""UPDATE ml_jobs SET state='processing', attempts=attempts+1,
                started_at=?,worker_id=? WHERE photo_id=? AND state='queued'""", (now, worker_id, row["id"]))
            db.execute("UPDATE photos SET ml_state='processing',error=NULL WHERE id=?", (row["id"],))
            return dict(row)

    def finish_job(self, identifier: str, state: str, prediction: dict, error: str | None = None):
        if state not in ("person_detected", "no_person_detected", "error"):
            raise ValueError("Invalid final ML state")
        now = datetime.now(timezone.utc).isoformat()
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            changed = db.execute("""UPDATE ml_jobs SET state=?,finished_at=?,error=?
                WHERE photo_id=? AND state='processing'""", (state, now, error, identifier)).rowcount
            if changed != 1: raise RuntimeError(f"Job is no longer processing: {identifier}")
            db.execute("UPDATE photos SET ml_state=?,prediction=?,error=? WHERE id=?",
                       (state, json.dumps(prediction), error, identifier))

    def heartbeat(self, worker_id: str, model: Path):
        now = datetime.now(timezone.utc).isoformat()
        with self.connect() as db:
            db.execute("INSERT OR REPLACE INTO service_state(name,value) VALUES ('worker_heartbeat',?)", (now,))
            db.execute("INSERT OR REPLACE INTO service_state(name,value) VALUES ('worker_id',?)", (worker_id,))
            db.execute("INSERT OR REPLACE INTO service_state(name,value) VALUES ('worker_model',?)", (str(model),))

    def clear_heartbeat(self, worker_id: str):
        with self.connect() as db:
            row = db.execute("SELECT value FROM service_state WHERE name='worker_id'").fetchone()
            if row and row[0] == worker_id:
                db.execute("DELETE FROM service_state WHERE name IN ('worker_heartbeat','worker_id','worker_model')")
