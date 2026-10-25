"""Restore missing source-dataset files from local archives; never overwrite existing files."""
import io
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent

def unpack(archive, dest):
    dest = dest.resolve()
    count = 0
    for item in archive.infolist():
        if item.is_dir():
            continue
        target = (dest / item.filename).resolve()
        if not target.is_relative_to(dest):
            raise ValueError('Unsafe archive path')
        if not target.exists():
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(archive.read(item))
            count += 1
    print(dest.name, 'restored', count)

if __name__ == '__main__':
    unpack(zipfile.ZipFile(ROOT.parent / 'Camouflage.v1i.yolov11.zip'), ROOT / 'raw/camouflage')
    with zipfile.ZipFile(ROOT.parent / 'dataset-20261020T080309Z-1-002.zip') as outer:
        for name, dest in [('dataset/soldier.v1i.yolov11.zip', 'soldier_a'),
                           ('dataset/soldier.v1i.yolov11 (1).zip', 'soldier_b')]:
            with zipfile.ZipFile(io.BytesIO(outer.read(name))) as inner:
                unpack(inner, ROOT / 'raw' / dest)
