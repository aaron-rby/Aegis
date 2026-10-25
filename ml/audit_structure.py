"""Check every path in the supplied folder tree, without requiring invented data."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DIRECTORIES = '''__pycache__ camo_eval/no_person camo_eval/person camo_test/images
camo_test/labels captures data/no_person data/person data/screen_negatives models
raw/camouflage raw/hidden raw/soldier_a raw/soldier_b results results_base_camo
results_base_main results_ft_camo results_ft_main runs/detect train_data/train
train_data/val venv/Include venv/Lib venv/Scripts venv/share weights'''.split()
FILES = '''.gitignore build_dataset.py build_training_set.py client_test.py
collect_camera.py detector.py evaluate.py gettyimages-586890581.avif README.md
requirements.txt rs.err rs.log run_server.py server.py srv.err srv.log test_cam.jpg
test_camera.py test.jpg test.py train_all.err train_all.log train.err train.log
train.py webcam.py yolo11m.pt yolo11n.pt yolo11x.pt'''.split()


def main():
    checks = [{'path': path, 'kind': kind, 'present': (ROOT/path).is_dir() if kind == 'directory'
               else (ROOT/path).is_file()}
              for kind, paths in [('directory', DIRECTORIES), ('file', FILES)] for path in paths]
    missing = [item['path'] for item in checks if not item['present']]
    report = {'root': str(ROOT), 'expected_paths': len(checks), 'missing': missing,
              'checks': checks,
              'notes': ['Presence is separate from functional validation.',
                        'Empty stderr logs reflect real commands without errors.',
                        'train.log records a configuration check, not a fresh training run.',
                        'Empty negative/screen folders need real labeled examples.']}
    (ROOT/'structure_audit.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(f"Present: {len(checks)-len(missing)}/{len(checks)}; missing: {missing}")
    return bool(missing)


if __name__ == '__main__':
    raise SystemExit(main())
