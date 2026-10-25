"""Evaluate the configured YOLO model on manually labelled ESP32-CAM frames."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    root = Path(__file__).resolve().parents[1]
    parser.add_argument("--config", type=Path, default=root / "backend" / "config.local.json")
    parser.add_argument("--labels", type=Path, default=root / "ml" / "evaluation" / "esp32_camera_labels.json")
    parser.add_argument("--output", type=Path, default=root / "ml" / "evaluation" / "esp32_camera_report.json")
    args = parser.parse_args()
    config = json.loads(args.config.read_text(encoding="utf-8"))
    labels = json.loads(args.labels.read_text(encoding="utf-8"))["images"]
    capture_dir = Path(config["capture_dir"])
    if not capture_dir.is_absolute(): capture_dir = args.config.parent / capture_dir
    model = Path(config["model_path"])
    if not model.is_absolute(): model = args.config.parent / model
    capture_dir, model = capture_dir.resolve(), model.resolve()
    if not capture_dir.is_dir() or not model.is_file():
        parser.error("Configured capture directory or model is missing")
    os.environ["MODEL_NAME"] = str(model)
    os.environ["CONF_THRESHOLD"] = "0.35"
    os.environ["IMG_SIZE"] = "960"
    import detector
    detector.get_model()
    rows = []
    for entry in labels:
        image = capture_dir / (entry["id"] + ".jpg")
        if not image.is_file(): parser.error(f"Missing labelled image: {image}")
        result = detector.verify_person(image, conf=0.35)
        rows.append({**entry, "predicted_person": bool(result["person"]),
                     "confidence": result["confidence"], "inference_ms": result["ms"],
                     "boxes": result["boxes"]})
    counts = {"tp": 0, "tn": 0, "fp": 0, "fn": 0}
    for row in rows:
        key = ("tp" if row["person"] else "fp") if row["predicted_person"] else ("fn" if row["person"] else "tn")
        counts[key] += 1
    report = {"evaluated_at": datetime.now(timezone.utc).isoformat(), "model": str(model),
              "threshold": 0.35, "counts": counts, "images": rows,
              "mean_inference_ms": round(sum(row["inference_ms"] for row in rows) / len(rows), 1),
              "limitations": "Only 10 frames from two bursts in one indoor scene; camera points upward and person is partly cropped. No low-light or distance diversity. Do not generalize these metrics to deployment."}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({"counts": counts, "mean_inference_ms": report["mean_inference_ms"],
                      "report": str(args.output)}, indent=2))


if __name__ == "__main__": main()
