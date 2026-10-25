"""Live person detection. Three positive frames out of five confirm the banner."""
import argparse
import sys
from collections import deque
import cv2
import detector

WINDOW, CONFIRM_FRAMES = 5, 3


def open_camera(index):
    backends = [cv2.CAP_DSHOW, cv2.CAP_ANY] if sys.platform == 'win32' else [cv2.CAP_ANY]
    for backend in backends:
        camera = cv2.VideoCapture(index, backend)
        if camera.isOpened():
            return camera
        camera.release()
    raise RuntimeError(f'Cannot open camera {index}. Close other camera apps or try index 1.')


def run(index=0):
    detector.get_model()
    camera = None
    try:
        camera = open_camera(index)
        print('Camera started. Press Q or Escape in the video window to stop.', flush=True)
        history = deque(maxlen=WINDOW)
        while True:
            ok, frame = camera.read()
            if not ok:
                raise RuntimeError('Camera stopped providing frames. Check its connection and permissions.')
            result = detector.verify_person(frame)
            history.append(result['person'])
            view = detector.annotate(frame, result)
            if sum(history) >= CONFIRM_FRAMES:
                cv2.rectangle(view, (0, 0), (view.shape[1]-1, view.shape[0]-1), (0, 140, 255), 3)
                cv2.putText(view, 'ALERT: HUMAN CONFIRMED', (10, max(25, view.shape[0]-45)),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 140, 255), 2)
            cv2.putText(view, f"{result['ms']:.0f} ms", (10, view.shape[0]-10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
            cv2.imshow('AI Intrusion Detection (q to quit)', view)
            key = cv2.waitKey(1) & 0xFF
            if key in (ord('q'), ord('Q'), 27):
                break
            if cv2.getWindowProperty('AI Intrusion Detection (q to quit)', cv2.WND_PROP_VISIBLE) < 1:
                break
    finally:
        if camera is not None:
            camera.release()
        cv2.destroyAllWindows()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('camera', nargs='?', type=int, default=0)
    args = parser.parse_args()
    if args.camera < 0:
        parser.error('Camera index must be nonnegative')
    try:
        run(args.camera)
    except KeyboardInterrupt:
        return 0
    except (RuntimeError, ValueError, OSError, cv2.error) as exc:
        print(f'Webcam error: {exc}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
