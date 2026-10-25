"""Prepare a reproducible evaluation set from local COCO archives.

Existing training COCO images are excluded. ExDark candidates are exported for
manual review, never silently labeled person-free based on their folder name.
"""
import argparse
import hashlib
import io
import json
import random
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('archives', nargs='?', type=Path, default=ROOT.parent)
    parser.add_argument('--output', type=Path, default=ROOT / 'data_prepared')
    parser.add_argument('--include-exdark', action='store_true')
    args = parser.parse_args()
    if args.output.exists() and any(args.output.iterdir()):
        raise SystemExit('Output is populated; choose a new --output directory')
    rng = random.Random(42)
    with zipfile.ZipFile(args.archives / 'annotations_trainval2017.zip') as archive:
        annotations = json.loads(archive.read('annotations/instances_val2017.json'))
    images = {i['id']: i for i in annotations['images']}
    person_ids = {c['id'] for c in annotations['categories'] if c['name'] == 'person'}
    people = {a['image_id'] for a in annotations['annotations'] if a['category_id'] in person_ids}
    training_names, training_hashes = set(), set()
    for split in ('train', 'val'):
        for image in (ROOT / 'train_data' / split / 'images').glob('*'):
            training_names.add(image.name.removeprefix('coco_'))
            training_hashes.add(hashlib.sha256(image.read_bytes()).hexdigest())
    manifest = []
    with zipfile.ZipFile(args.archives / 'val2017.zip') as archive:
        for folder, positive in [('person', True), ('no_person', False)]:
            dest = args.output / folder
            dest.mkdir(parents=True, exist_ok=True)
            candidates = sorted(i for i in images if (i in people) == positive
                                and images[i]['file_name'] not in training_names)
            rng.shuffle(candidates)
            count = 0
            for image_id in candidates:
                filename = images[image_id]['file_name']
                data = archive.read('val2017/' + filename)
                if hashlib.sha256(data).hexdigest() in training_hashes:
                    continue
                target = dest / ('coco_' + filename)
                target.write_bytes(data)
                manifest.append({'path': str(target.relative_to(args.output)),
                                 'person': positive, 'source': 'COCO annotations'})
                count += 1
                if count == 60:
                    break
            if not count:
                raise SystemExit(f'No independent {folder} images available in supplied archives')
    if args.include_exdark:
        with zipfile.ZipFile(args.archives / 'dataset-20261020T080309Z-1-002.zip') as outer:
            with zipfile.ZipFile(io.BytesIO(outer.read('dataset/ExDark.zip'))) as dark:
                for category in ('People', 'Cat', 'Dog', 'Chair', 'Table', 'Bottle'):
                    candidates = sorted(n for n in dark.namelist()
                                        if n.startswith('ExDark/' + category + '/')
                                        and Path(n).suffix.lower() in {'.jpg', '.jpeg', '.png'})
                    for name in rng.sample(candidates, min(10, len(candidates))):
                        target = args.output / 'review' / category / Path(name).name
                        target.parent.mkdir(parents=True, exist_ok=True)
                        target.write_bytes(dark.read(name))
    (args.output / 'manifest.json').write_text(json.dumps({
        'images': manifest,
        'note': 'Exact training-image overlap excluded; independence from historical checkpoint is unknown. '
                'Review ExDark candidates before copying into a labeled evaluation folder.'
    }, indent=2), encoding='utf-8')
    print(f'Prepared {len(manifest)} COCO images in {args.output}')


if __name__ == '__main__':
    main()
