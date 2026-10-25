"""Audit generated dataset pairing and exact overlap; save machine-readable evidence."""
import hashlib
import json
from pathlib import Path
ROOT = Path(__file__).resolve().parent
if __name__ == '__main__':
    seen = {}
    result = {}
    overlaps = []
    for split, image_dir, label_dir in [
        ('test', ROOT/'camo_test/images', ROOT/'camo_test/labels'),
        ('val', ROOT/'train_data/val/images', ROOT/'train_data/val/labels'),
        ('train', ROOT/'train_data/train/images', ROOT/'train_data/train/labels')]:
        images = list(image_dir.glob('*'))
        missing = []
        invalid = []
        for image in images:
            label = label_dir/(image.stem+'.txt')
            if not label.exists():
                missing.append(image.name)
            else:
                for number, line in enumerate(label.read_text().splitlines(), 1):
                    try:
                        cls, x, y, w, h = map(float, line.split())
                        if cls != 0 or not all(0 <= v <= 1 for v in (x, y, w, h)) or min(w, h) <= 0:
                            invalid.append(f'{label.name}:{number}')
                    except ValueError:
                        invalid.append(f'{label.name}:{number}')
            digest = hashlib.sha256(image.read_bytes()).hexdigest()
            if digest in seen:
                overlaps.append([seen[digest], str(image)])
            seen[digest] = str(image)
        result[split] = {'images': len(images), 'missing_labels': missing, 'invalid_labels': invalid}
    result['exact_duplicate_pairs'] = overlaps
    regression_overlap = []
    for folder in ('person', 'no_person'):
        for image in (ROOT / 'data' / folder).glob('*'):
            if image.is_file():
                digest = hashlib.sha256(image.read_bytes()).hexdigest()
                if digest in seen:
                    regression_overlap.append([str(image), seen[digest]])
    result['regression_exact_overlap'] = regression_overlap
    result['prepared_evaluation_exact_overlap'] = [str(image)
        for folder in ('person', 'no_person')
        for image in (ROOT / 'data_prepared' / folder).glob('*')
        if image.is_file() and hashlib.sha256(image.read_bytes()).hexdigest() in seen]
    result['note'] = 'Exact byte duplicates only; scene and near-duplicate leakage requires source review.'
    (ROOT/'dataset_audit.json').write_text(json.dumps(result, indent=2))
    print(json.dumps({k:v for k,v in result.items() if k != 'exact_duplicate_pairs'}, indent=2))
    print('Exact duplicate pairs:', len(overlaps))
