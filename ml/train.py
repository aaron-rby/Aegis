"""Train a new checkpoint, preserving the supplied historical model."""
import argparse
from pathlib import Path
from ultralytics import YOLO
import json
import yaml
ROOT = Path(__file__).resolve().parent
if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--epochs', type=int, default=30)
    p.add_argument('--device', default='cpu')
    p.add_argument('--batch', type=int, default=4)
    p.add_argument('--base', type=Path, default=ROOT / 'yolo11m.pt')
    p.add_argument('--data', type=Path, default=ROOT / 'train_data/data.yaml')
    p.add_argument('--name', default='person')
    p.add_argument('--check', action='store_true', help='Validate inputs without training')
    a = p.parse_args()
    if a.epochs < 1 or a.batch < 1 or not a.base.is_file():
        p.error('Epochs and batch must be positive and --base must be a local model file')
    config = yaml.safe_load(a.data.read_text())
    base = Path(config.get('path', a.data.parent))
    if not base.is_absolute():
        base = a.data.parent / base
    counts = {}
    for split in ('train', 'val'):
        images = base / config[split]
        files = [f for f in images.glob('*') if f.suffix.lower() in {'.jpg', '.jpeg', '.png', '.bmp'}]
        missing = [f.name for f in files if not (images.parent / 'labels' / (f.stem + '.txt')).is_file()]
        if not files or missing:
            p.error(f'Invalid {split} dataset: {len(files)} images, {len(missing)} missing labels')
        counts[split] = len(files)
    if a.check:
        print('CHECK ONLY: no training was run')
        print(json.dumps({'data': str(a.data), 'images': counts, 'model': str(a.base)}, indent=2))
        raise SystemExit(0)
    YOLO(str(a.base)).train(data=str(a.data),
        epochs=a.epochs, device=a.device, batch=a.batch, imgsz=640,
        project=str(ROOT / 'runs_repaired'), name=a.name, exist_ok=False, freeze=10)
