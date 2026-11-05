from __future__ import annotations

import importlib.metadata
import json
import shutil
import sys
import tempfile
from pathlib import Path

from .adapters.pkpd import check_contract_file, check_output_file
from .scaffold import init_project


def doctor() -> dict[str, object]:
    checks: list[dict[str, object]] = []

    def add(name: str, ok: bool, detail: str) -> None:
        checks.append({"name": name, "ok": bool(ok), "detail": detail})

    add("python", sys.version_info >= (3, 11), sys.version.split()[0])
    try:
        version = importlib.metadata.version("cryptography")
        add("cryptography", True, version)
    except importlib.metadata.PackageNotFoundError:
        add("cryptography", False, "not installed")

    lean = shutil.which("lean")
    lake = shutil.which("lake")
    add("lean", bool(lean), lean or "not found (formal kernel cannot be locally rebuilt)")
    add("lake", bool(lake), lake or "not found (formal kernel cannot be locally rebuilt)")

    try:
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "starter"
            init_project(p)
            ok_contract, _ = check_contract_file(p / "model.json")
            ok_output, _ = check_output_file(p / "model.json", p / "predictions.csv")
            add("pkpd_reference_selfcheck", bool(ok_contract and ok_output), f"contract={ok_contract} replay={ok_output}")
    except Exception as exc:
        add("pkpd_reference_selfcheck", False, f"{type(exc).__name__}: {exc}")

    required_ok = all(c["ok"] for c in checks if c["name"] not in {"lean", "lake"})
    formal_toolchain_available = bool(lean and lake)
    return {
        "healthy": required_ok,
        "formal_toolchain_available": formal_toolchain_available,
        "checks": checks,
        "note": "Lean/Lake are reported separately: PCS can run the Python replay checker without them, but machine-checking the formal kernel requires both.",
    }
