"""Reproducible image-level evaluation; never overwrites historical results by default."""
import argparse
import csv
import json
from pathlib import Path
import detector


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--data', type=Path, default=detector.ROOT / 'data')
    parser.add_argument('--output', type=Path, default=detector.ROOT / 'results_current')
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    rows = []
    extensions = {'.jpg', '.jpeg', '.png', '.webp', '.bmp', '.avif'}
    for folder, positive in [('person', True), ('no_person', False)]:
        images = sorted(p for p in (args.data / folder).glob('*') if p.suffix.lower() in extensions)
        for image in images:
            dets, ms, _ = detector.detect(image, conf_floor=0.001)
            valid = [d for d in dets if detector.is_valid(d, conf=0.001)]
            r = {'confidence': max((d['confidence'] for d in valid), default=0.0), 'ms': ms}
            rows.append({'path': str(image), 'label_person': positive,
                         'best_confidence': r['confidence'], 'ms': r['ms']})
    if not rows:
        raise SystemExit(f'No supported images in {args.data}/person or no_person')
    positives = sum(r['label_person'] for r in rows)
    negatives = len(rows) - positives
    with (args.output / 'predictions.csv').open('w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    metrics = []
    for threshold in sorted(set([round(i / 100, 2) for i in range(20, 95, 5)] + [detector.CONF_THRESHOLD])):
        tp = sum(r['label_person'] and r['best_confidence'] >= threshold for r in rows)
        fp = sum(not r['label_person'] and r['best_confidence'] >= threshold for r in rows)
        fn = sum(r['label_person'] and r['best_confidence'] < threshold for r in rows)
        tn = len(rows) - tp - fp - fn
        precision = (tp / (tp + fp) if tp + fp else 0) if negatives else None
        recall = tp / (tp + fn) if tp + fn else None
        metrics.append(dict(threshold=threshold, TP=tp, FP=fp, FN=fn, TN=tn,
                            precision=precision, recall=recall,
                            F1=(2*precision*recall/(precision+recall) if precision+recall else 0)
                            if precision is not None and recall is not None else None,
                            negative_image_false_positive_rate=fp/(fp+tn) if negatives else None))
    report = {'model': detector.MODEL_NAME, 'images': len(rows), 'imgsz': detector.IMG_SIZE,
              'note': 'Image-level metrics; independence from historical checkpoint training is not proven.',
              'person_images': sum(r['label_person'] for r in rows),
              'negative_images': sum(not r['label_person'] for r in rows),
              'settings': {k: getattr(detector, k) for k in ['CONF_THRESHOLD', 'MIN_BOX_AREA', 'MIN_BOX_HEIGHT', 'MAX_ASPECT', 'USE_TTA', 'ENHANCE_DARK', 'ZOOM_OUT_PASS']},
              'mean_ms_including_first_inference': sum(r['ms'] for r in rows)/len(rows), 'thresholds': metrics}
    (args.output / 'report.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    for key in ('precision', 'recall', 'F1'):
        plt.plot([m['threshold'] for m in metrics], [m[key] for m in metrics], label=key)
    plt.xlabel('Confidence threshold')
    plt.ylabel('Image-level score')
    plt.ylim(0, 1.02)
    plt.legend()
    plt.tight_layout()
    plt.savefig(args.output / 'threshold_sweep.png')
    plt.close()
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
