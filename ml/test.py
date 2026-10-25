"""Static-image person demo. Opens a window only with --show."""
import argparse
import json
from pathlib import Path
import cv2
import detector


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('image', nargs='?', type=Path, default=detector.ROOT / 'test.jpg')
    parser.add_argument('--show', action='store_true')
    parser.add_argument('--output', type=Path, default=detector.ROOT / 'results_current/test_annotated.jpg')
    args = parser.parse_args()
    image = detector.load_image(args.image)
    result = detector.verify_person(image)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    annotated = detector.annotate(image, result)
    if not cv2.imwrite(str(args.output), annotated):
        raise OSError(f'Could not save {args.output}')
    print(json.dumps(result, indent=2))
    print('PERSON DETECTED' if result['person'] else 'NO QUALIFYING PERSON DETECTION')
    if args.show:
        cv2.imshow('Person verification', annotated)
        cv2.waitKey(0)
        cv2.destroyAllWindows()


if __name__ == '__main__':
    main()
