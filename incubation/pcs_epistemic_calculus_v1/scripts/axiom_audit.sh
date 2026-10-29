#!/usr/bin/env bash
# Fail if lake build axiom inventory mentions unapproved axioms or sorry.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
if ! command -v lake >/dev/null 2>&1; then
  echo "lake not on PATH; skip axiom audit" >&2
  exit 0
fi
log="$(mktemp)"
trap 'rm -f "$log"' EXIT
lake build 2>&1 | tee "$log"
# Reject sorry / admit / native_decide as code tokens (ignore comments/docs).
python3 - <<'PY'
from pathlib import Path
import re, sys
root = Path(".")
pat = re.compile(r"(?<![\w.])(sorry|admit|native_decide)(?![\w.])")
bad = []
for path in list(root.glob("PcsEpistemic/**/*.lean")) + [root / "PcsEpistemic.lean"]:
    if not path.is_file():
        continue
    for i, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        code = line.split("--", 1)[0]
        if "/-!" in code:
            code = code.split("/-!", 1)[0]
        if pat.search(code):
            bad.append(f"{path}:{i}:{line}")
if bad:
    print("AXIOM AUDIT FAIL: forbidden proof escape in Lean sources", file=sys.stderr)
    print("\n".join(bad), file=sys.stderr)
    sys.exit(1)
PY
python3 - "$log" <<'PY'
import re, sys
approved = {"propext", "Classical.choice", "Quot.sound"}
text = open(sys.argv[1], encoding="utf-8", errors="replace").read()
found = False
for m in re.finditer(r"depends on axioms: \[([^\]]*)\]", text):
    found = True
    axioms = {a.strip() for a in m.group(1).split(",") if a.strip()}
    bad = axioms - approved
    if bad:
        print("AXIOM AUDIT FAIL: unapproved axioms:", sorted(bad), file=sys.stderr)
        print(m.group(0), file=sys.stderr)
        sys.exit(1)
if "depends on axioms:" in text and not found:
    # lines with empty or unusual formatting
    pass
print("AXIOM AUDIT OK")
PY
