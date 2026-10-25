"""Build the fine-tuning dataset in YOLO format -> train_data/

    python -I build_training_set.py

Sources (all single-class "person"; class id 0 = COCO's person id, so the pretrained
80-class head is kept):
  * raw/soldier_b, raw/soldier_a, raw/camouflage  (Roboflow, CC BY 4.0): train used for training, valid for validation; their TEST splits are copied to camo_test/ and never trained on.
  * COCO val2017 people (boxes from instances_val2017.json) + COCO images WITHOUT people
    (empty labels = background) so false alarms do not go up.
    Images already used in data/ (the regression test set) are excluded.
Excluded on purpose: raw/hidden (fire/smoke scenes, "Private" license).
"""
import json
import hashlib
import random
import shutil
import zipfile
from pathlib import Path

random.seed(7)
ROOT = Path(__file__).resolve().parent
OUT = ROOT / "train_data"
DL = ROOT.parent
N_COCO_PERSON, N_COCO_NEG = 10**6, 10**6  # use every COCO val image not already in data/
VAL_FRAC = 0.12

if OUT.exists() and any((OUT / "train/images").glob("*")):
    raise SystemExit(f"{OUT} already contains images; choose a new output directory before rebuilding.")
for split in ("train", "val"):
    (OUT / split / "images").mkdir(parents=True, exist_ok=True)
    (OUT / split / "labels").mkdir(parents=True, exist_ok=True)
for sub in ("images", "labels"):
    (ROOT / "camo_test" / sub).mkdir(parents=True, exist_ok=True)


def valid_person_lines(text):
    lines = []
    for line in text.splitlines():
        try:
            cls, x, y, w, h = map(float, line.split())
            if cls == 0 and all(0 <= v <= 1 for v in (x, y, w, h)) and min(w, h) > 0:
                lines.append(line)
        except ValueError:
            pass
    return lines


def copy_roboflow(name):
    n = 0
    for split, dest in (("train", "train"), ("valid", "val")):
        for img in (ROOT / "raw" / name / split / "images").glob("*"):
            lab = ROOT / "raw" / name / split / "labels" / (img.stem + ".txt")
            if not lab.exists():
                continue
            # keep only class 0 boxes (single-class datasets)
            lines = valid_person_lines(lab.read_text())
            if not lines:
                continue
            shutil.copy(img, OUT / dest / "images" / f"{name}_{img.name}")
            (OUT / dest / "labels" / f"{name}_{img.stem}.txt").write_text("\n".join(lines))
            n += 1
    for img in (ROOT / "raw" / name / "test" / "images").glob("*"):
        lab = ROOT / "raw" / name / "test" / "labels" / (img.stem + ".txt")
        if lab.exists():
            shutil.copy(img, ROOT / "camo_test" / "images" / f"{name}_{img.name}")
            shutil.copy(lab, ROOT / "camo_test" / "labels" / f"{name}_{img.stem}.txt")
    return n


counts = {n: copy_roboflow(n) for n in ("soldier_b", "soldier_a", "camouflage")}
print("Roboflow images into train/val:", counts)


# The historical run included hidden; new builds deliberately exclude it.

# ---------------------------------------------------------------- COCO
evaluation_roots = [ROOT / 'data', ROOT / 'data_prepared']
used = {p.name.removeprefix("coco_") for evaluation in evaluation_roots
        for sub in ("person", "no_person") for p in (evaluation / sub).glob("coco_*")}
coco = json.loads(zipfile.ZipFile(DL / "annotations_trainval2017.zip").read("annotations/instances_val2017.json"))
cats = {c["id"]: c["name"] for c in coco["categories"]}
imgs = {i["id"]: i for i in coco["images"]}
boxes, has_person = {}, set()
for a in coco["annotations"]:
    if cats[a["category_id"]] == "person":
        has_person.add(a["image_id"])
        if not a["iscrowd"]:
            boxes.setdefault(a["image_id"], []).append(a["bbox"])

cand_p = [i for i in boxes if imgs[i]["file_name"] not in used]
cand_n = [i for i in imgs if i not in has_person and imgs[i]["file_name"] not in used]
pick = [(i, True) for i in random.sample(cand_p, min(N_COCO_PERSON, len(cand_p)))]
pick += [(i, False) for i in random.sample(cand_n, min(N_COCO_NEG, len(cand_n)))]

val = zipfile.ZipFile(DL / "val2017.zip")
for i, positive in pick:
    info = imgs[i]
    split = "val" if random.random() < VAL_FRAC else "train"
    (OUT / split / "images" / f"coco_{info['file_name']}").write_bytes(val.read(f"val2017/{info['file_name']}"))
    lines = []
    if positive:
        W, H = info["width"], info["height"]
        for x, y, w, h in boxes[i]:
            if w < 4 or h < 4:
                continue
            lines.append(f"0 {(x + w / 2) / W:.6f} {(y + h / 2) / H:.6f} {w / W:.6f} {h / H:.6f}")
    (OUT / split / "labels" / f"coco_{Path(info['file_name']).stem}.txt").write_text("\n".join(lines))
print(f"COCO: {len(pick)} images ({sum(positive for _, positive in pick)} with people, {sum(not positive for _, positive in pick)} background)")

# --------------------------------------------------------------- yaml
names = [c["name"] for c in sorted(coco["categories"], key=lambda c: c["id"])]
# YOLO's 80-class order is the COCO category order with ids compressed; person must be index 0
coco80 = ["person"] + [n for n in names if n != "person"]
(OUT / "data.yaml").write_text(
    f"path: {OUT.resolve().as_posix()}\ntrain: train/images\nval: val/images\nnames:\n"
    + "".join(f"  {i}: {n}\n" for i, n in enumerate(coco80))
)
for s in ("train", "val"):
    print(s, len(list((OUT / s / "images").iterdir())), "images")
print("camo_test:", len(list((ROOT / "camo_test" / "images").iterdir())), "images (held out)")

# Keep exact duplicates out of separate splits, preferring held-out images.
seen = {hashlib.sha256(p.read_bytes()).hexdigest()
        for evaluation in evaluation_roots for folder in ("person", "no_person")
        for p in (evaluation / folder).glob("*") if p.is_file()}
removed = 0
for image_dir, label_dir in [(ROOT / "camo_test/images", ROOT / "camo_test/labels"),
                              (OUT / "val/images", OUT / "val/labels"),
                              (OUT / "train/images", OUT / "train/labels")]:
    for image in sorted(image_dir.glob("*")):
        digest = hashlib.sha256(image.read_bytes()).hexdigest()
        if digest in seen and image.is_relative_to(OUT):
            image.unlink()
            (label_dir / (image.stem + ".txt")).unlink(missing_ok=True)
            removed += 1
        seen.add(digest)
print("Removed exact duplicate train/val images:", removed)
