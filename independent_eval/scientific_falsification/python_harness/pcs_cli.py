"""Black-box PCS CLI wrappers via subprocess only."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence


@dataclass(frozen=True)
class CliResult:
    argv: list[str]
    returncode: int
    stdout: str
    stderr: str
    duration_s: float

    @property
    def ok(self) -> bool:
        return self.returncode == 0

    def combined(self) -> str:
        return (self.stdout or "") + (self.stderr or "")


def resolve_pcs_argv() -> list[str]:
    """Prefer installed `pcs` console script; fall back to `python -m pcs.cli`."""
    pcs = shutil.which("pcs")
    if pcs:
        return [pcs]
    return [sys.executable, "-m", "pcs.cli"]


def run_pcs(
    args: Sequence[str],
    *,
    cwd: Path | None = None,
    timeout: float = 120.0,
    env: dict[str, str] | None = None,
) -> CliResult:
    import time

    argv = [*resolve_pcs_argv(), *args]
    merged = os.environ.copy()
    if env:
        merged.update(env)
    # Ensure local editable install is importable for python -m fallback.
    merged.setdefault("PYTHONPATH", str(Path(__file__).resolve().parents[2].parent))
    started = time.perf_counter()
    proc = subprocess.run(
        argv,
        cwd=str(cwd) if cwd else None,
        capture_output=True,
        text=True,
        timeout=timeout,
        env=merged,
        check=False,
    )
    return CliResult(
        argv=list(argv),
        returncode=proc.returncode,
        stdout=proc.stdout or "",
        stderr=proc.stderr or "",
        duration_s=time.perf_counter() - started,
    )


def certify(manifest: Path, output: Path, *, timeout: float = 120.0) -> CliResult:
    output.mkdir(parents=True, exist_ok=True)
    return run_pcs(["certify", str(manifest), "-o", str(output)], timeout=timeout)


def verify_certificate(certificate: Path, *, timeout: float = 120.0) -> CliResult:
    return run_pcs(["verify", str(certificate)], timeout=timeout)


def discover_v06(
    project: Path,
    *,
    output: Path | None = None,
    report: Path | None = None,
    subject: str | None = None,
    minimum_confidence: float | None = None,
    force: bool = True,
    timeout: float = 120.0,
) -> CliResult:
    args: list[str] = ["discover-v06", str(project)]
    if output is not None:
        args.extend(["-o", str(output)])
    if report is not None:
        args.extend(["--report", str(report)])
    if subject is not None:
        args.extend(["--subject", subject])
    if minimum_confidence is not None:
        args.extend(["--minimum-confidence", str(minimum_confidence)])
    if force:
        args.append("--force")
    return run_pcs(args, timeout=timeout)


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))
