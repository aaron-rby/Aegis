"""Install only the reviewed hardware-monitor files into the user-named project."""
from datetime import datetime
import hashlib
from pathlib import Path
import shutil
import sys

SOURCE = Path(__file__).resolve().parent
TARGET = Path(r"C:\Users\aaron\Downloads\AI-Intrusion-Detection-main\AI-Intrusion-Detection-main").resolve()
FILES = ["START_HARDWARE.bat", "website/app.py", "website/serial_bridge.py",
         "website/hardware_launcher.py", "website/test_hardware_monitor.py", "website/test_live.py",
         "website/HARDWARE_MONITOR.md", "website/dist/app.js", "website/dist/live.js",
         "website/dist/live.css", "website/dist/index.html"]
if "--launcher-only" in sys.argv:
    FILES = ["START_HARDWARE.bat"]
if "--ui-entry-only" in sys.argv:
    FILES = ["website/dist/index.html"]
PRESERVE = [TARGET / "START_SERVER.bat", TARGET / "website/START_SENTINEL.bat"]
hashes = {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in PRESERVE if p.exists()}
backup = TARGET / "website" / "backups" / ("hardware-before-" + datetime.now().strftime("%Y%m%d-%H%M%S"))
for name in FILES:
    src, dst = SOURCE / name, (TARGET / name).resolve()
    if not dst.is_relative_to(TARGET) or not src.is_file():
        raise RuntimeError(f"Unsafe or missing update path: {name}")
    if dst.exists():
        saved = backup / name
        saved.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(dst, saved)
    dst.parent.mkdir(parents=True, exist_ok=True)
    temporary = dst.with_suffix(dst.suffix + ".hardware-update")
    shutil.copy2(src, temporary)
    if dst.suffix.lower() == ".bat":
        # cmd.exe needs CRLF, particularly while switching code pages for the title.
        temporary.write_bytes(temporary.read_bytes().replace(b"\r\n", b"\n").replace(b"\n", b"\r\n"))
    temporary.replace(dst)
for path, digest in hashes.items():
    if hashlib.sha256(path.read_bytes()).hexdigest() != digest:
        raise RuntimeError(f"Existing launcher changed unexpectedly: {path.name}")
print(f"Installed {len(FILES)} hardware-monitor files into {TARGET}")
print(f"Previous files backed up to {backup}")
print("Existing START_SERVER.bat and website/START_SENTINEL.bat are unchanged.")
