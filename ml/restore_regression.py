"""Recover regression images by filename from existing archives; preserve historical labels."""
import csv
import io
import re
import zipfile
from pathlib import Path
ROOT = Path(__file__).resolve().parent
rows = list(csv.DictReader((ROOT / 'results/predictions.csv').open()))
missing = [r for r in rows if not (ROOT / Path(r['path'].replace('\\', '/'))).exists()]
with zipfile.ZipFile(ROOT.parent / 'val2017.zip') as coco:
    for r in list(missing):
        name = Path(r['path'].replace('\\', '/')).name
        if name.startswith('coco_'):
            dest = ROOT / Path(r['path'].replace('\\', '/'))
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(coco.read('val2017/' + name[5:]))
            missing.remove(r)
with zipfile.ZipFile(ROOT.parent / 'dataset-20261020T080309Z-1-002.zip') as outer:
    with zipfile.ZipFile(io.BytesIO(outer.read('dataset/ExDark.zip'))) as dark:
        lookup = {Path(n).name.lower(): n for n in dark.namelist() if not n.endswith('/')}
        for r in list(missing):
            dest = ROOT / Path(r['path'].replace('\\', '/'))
            name = dest.name.removeprefix('exdark_').lower()
            if name not in lookup:
                match = re.search(r'(2015_\d+\.[^.]+)$', name)
                if match:
                    name = match.group(1)
            if name in lookup:
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_bytes(dark.read(lookup[name]))
                missing.remove(r)
print('Regression files:', len(rows) - len(missing), '/', len(rows))
print('Unrecoverable:', [r['path'] for r in missing])
