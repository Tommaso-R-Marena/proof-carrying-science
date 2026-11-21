"""Software and benchmark freezes for the ClaimCheck evaluation.

    python -m research.claimcheck_v1.benchmark.freeze write-software      # before held-out material exists
    python -m research.claimcheck_v1.benchmark.freeze write-benchmark     # after annotation, before any run
    python -m research.claimcheck_v1.benchmark.freeze check

``FREEZE.json`` pins every file that can influence a result (code, the Lean checker and its pin,
the protocol, the candidate pool).  ``BENCHMARK_FREEZE.json`` pins every held-out input (texts,
tables, manifests, gold labels, variants).  The held-out runners refuse to start unless both
freezes verify, and they copy both digests into their results.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
SOFTWARE_GLOBS = ("*.py", "formal/*.lean", "formal/*.sha256", "formal/real/*.lean", "formal/lakefile.toml", "formal/lean-toolchain",
                  "formal/lake-manifest.json", "benchmark/*.py", "benchmark/PROTOCOL.md", "benchmark/candidates.json")


def _digest(paths: list[Path], base: Path) -> dict:
    files = {p.relative_to(base).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(paths)}
    overall = hashlib.sha256(json.dumps(files, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    return {"files": files, "sha256": overall}


def software() -> dict:
    paths = [p for g in SOFTWARE_GLOBS for p in ROOT.glob(g) if p.is_file() and "__pycache__" not in p.parts]
    return _digest(paths, ROOT)


def benchmark() -> dict:
    paths = [p for p in (HERE / "heldout").rglob("*") if p.is_file()]
    return _digest(paths, HERE)


def check(require_benchmark: bool = True) -> dict:
    """Raise unless the working tree matches the committed freezes; return their digests."""
    frozen = json.loads((HERE / "FREEZE.json").read_text(encoding="utf-8"))
    now = software()
    if now["files"] != frozen["files"]:
        changed = sorted(k for k in set(now["files"]) | set(frozen["files"]) if now["files"].get(k) != frozen["files"].get(k))
        raise SystemExit("software differs from FREEZE.json: " + ", ".join(changed))
    out = {"software_freeze_sha256": frozen["sha256"]}
    if require_benchmark:
        bfrozen = json.loads((HERE / "BENCHMARK_FREEZE.json").read_text(encoding="utf-8"))
        bnow = benchmark()
        if bnow["files"] != bfrozen["files"]:
            changed = sorted(k for k in set(bnow["files"]) | set(bfrozen["files"]) if bnow["files"].get(k) != bfrozen["files"].get(k))
            raise SystemExit("held-out inputs differ from BENCHMARK_FREEZE.json: " + ", ".join(changed[:12]))
        out["benchmark_freeze_sha256"] = bfrozen["sha256"]
    return out


def main(argv=None) -> int:
    cmd = (argv or sys.argv[1:] or ["check"])[0]
    if cmd == "write-software":
        if (HERE / "heldout").exists() and any((HERE / "heldout").iterdir()):
            raise SystemExit("held-out material already exists; the software freeze must come first")
        data = software()
        (HERE / "FREEZE.json").write_text(json.dumps(data, indent=1, sort_keys=True), encoding="utf-8")
        print(data["sha256"], len(data["files"]), "files")
    elif cmd == "write-benchmark":
        check(require_benchmark=False)
        data = benchmark()
        (HERE / "BENCHMARK_FREEZE.json").write_text(json.dumps(data, indent=1, sort_keys=True), encoding="utf-8")
        print(data["sha256"], len(data["files"]), "files")
    elif cmd == "check":
        print(json.dumps(check(require_benchmark=(HERE / "BENCHMARK_FREEZE.json").exists())))
    else:
        raise SystemExit("usage: freeze [write-software|write-benchmark|check]")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
