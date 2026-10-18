"""Read-only consolidated identity gate; never regenerates its expected profile."""
import ast
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]
REPORTS = ROOT / "docs/integration/2026-10-18"


def check_profile():
    profile = json.loads((REPORTS / "SOURCE_PROFILE.json").read_text())
    tracked = set(subprocess.check_output(["git", "ls-files", "-z"], cwd=ROOT).decode().split("\0"))
    failures = []
    for path, expected in profile["files"].items():
        file = ROOT / path
        if path not in tracked or not file.is_file() or file.is_symlink():
            failures.append(f"missing, untracked, or symlink source: {path}")
            continue
        if hashlib.sha256(file.read_bytes()).hexdigest() != expected["sha256"]:
            failures.append(f"source identity differs: {path}")
        if file.suffix == ".py":
            try:
                ast.parse(file.read_bytes(), filename=path)
            except (SyntaxError, UnicodeError) as exc:
                failures.append(f"Python source does not parse: {path}: {exc}")
        if file.suffix == ".sh" and not file.stat().st_mode & 0o111:
            failures.append(f"shell script lacks executable mode: {path}")
    modules = {p.relative_to(ROOT).as_posix() for p in (ROOT / "formal/PCS/V2").glob("ProofGated*.lean")}
    if modules != set(profile["V7_modules"]):
        failures.append("V7 module discovery differs from the exact audited source profile")
    ledger = json.loads((REPORTS / "OPEN_PR_LEDGER.json").read_text())
    if len(ledger["pull_requests"]) != 32 or len({p["number"] for p in ledger["pull_requests"]}) != 32:
        failures.append("32-PR source ledger incomplete")
    return {"format": "pcs-consolidated-source-gate-v1", "passed": not failures,
            "files_checked": len(profile["files"]), "V7_modules": len(modules),
            "failures": failures, "production_authority": False}


if __name__ == "__main__":
    result = check_profile()
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if result["passed"] else 1)
