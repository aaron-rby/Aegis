"""Check active image decoding and checkpoint archive integrity without training."""
import json
import zipfile
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parent


def main():
    images = set()
    for folder in ('train_data/train/images', 'train_data/val/images', 'camo_test/images',
                   'camo_eval', 'data', 'captures'):
        images.update(p for p in (ROOT/folder).rglob('*')
                      if p.suffix.lower() in {'.jpg', '.jpeg', '.png', '.bmp', '.webp'})
    images.update(ROOT/name for name in ('test.jpg', 'test_cam.jpg'))
    failures = []
    for path in sorted(images):
        try:
            with Image.open(path) as image:
                image.load()
        except (OSError, ValueError) as exc:
            failures.append({'path': str(path.relative_to(ROOT)), 'error': str(exc)})
    checkpoints = {}
    for path in sorted(list(ROOT.glob('*.pt')) + list((ROOT/'models').glob('*.pt'))):
        try:
            with zipfile.ZipFile(path) as archive:
                corrupt = archive.testzip()
            checkpoints[str(path.relative_to(ROOT))] = 'ok' if corrupt is None else f'corrupt: {corrupt}'
        except (OSError, zipfile.BadZipFile) as exc:
            checkpoints[str(path.relative_to(ROOT))] = str(exc)
    report = {'images_checked': len(images), 'image_failures': failures, 'checkpoints': checkpoints}
    (ROOT/'asset_validation.json').write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))
    return bool(failures or any(value != 'ok' for value in checkpoints.values()))


if __name__ == '__main__':
    raise SystemExit(main())
