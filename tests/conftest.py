from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

# Automatically expose archived era directories so legacy tests resolve imports
archive_dir = ROOT / "src" / "archive"
if archive_dir.exists():
    for p in archive_dir.rglob("*"):
        if p.is_dir() and not p.name.startswith((".", "_")):
            sys.path.insert(0, str(p))
