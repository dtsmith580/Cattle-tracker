# tools/fix_imports.py
import re
from pathlib import Path

def find_project_root(start: Path) -> Path:
    cur = start.resolve()
    for _ in range(8):  # walk up a few levels
        if (cur / "manage.py").exists():
            return cur
        if cur.parent == cur:
            break
        cur = cur.parent
    # fallback: two levels up from this script
    return Path(__file__).resolve().parents[1]

ROOT = find_project_root(Path.cwd())

PY_FILES = [p for p in ROOT.rglob("*.py") if "migrations" not in p.parts]

PATTERNS = [
    (re.compile(r'from\s+(?:\.\.|cattle_tracker_app\.)?utils\.access_utils\s+import\s+'),
     'from cattle_tracker_app.utils.access import '),
    (re.compile(r'from\s+cattle_tracker_app\.access\s+import\s+'),
     'from cattle_tracker_app.utils.access import '),
    # optional normalization of relative imports:
    (re.compile(r'from\s+(?:\.\.)?utils\.access\s+import\s+'),
     'from cattle_tracker_app.utils.access import '),
]

changed = 0
for p in PY_FILES:
    text = p.read_text(encoding="utf-8")
    new = text
    for pat, repl in PATTERNS:
        new = pat.sub(repl, new)
    if new != text:
        p.write_text(new, encoding="utf-8")
        print("UPDATED:", p.relative_to(ROOT))
        changed += 1

print(f"Root: {ROOT}")
print(f"Files updated: {changed}")
