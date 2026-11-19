"""Mathlib-backed Lean compile oracle for autoformalization candidates.

Expects a Lake project with Mathlib already built (default:
`/tmp/forml4_compile/FormL4AF`). Research-only; not PCS authority.
"""
from __future__ import annotations

import re
import subprocess
import time
from pathlib import Path
from typing import Any

DEFAULT_PROJECT = Path("/tmp/forml4_compile/FormL4AF")


def extract_lean_code(text: str) -> str:
    text = text.strip()
    fence = re.search(r"```(?:lean4?|lean)?\s*([\s\S]*?)```", text, re.I)
    if fence:
        text = fence.group(1).strip()
    # Drop trailing natural-language after first blank line following theorem
    return text.strip()


def normalize_candidate(code: str) -> str:
    code = extract_lean_code(code)
    # Ensure import Mathlib
    if not re.search(r"(?m)^import\s+Mathlib\b", code):
        code = "import Mathlib\n\n" + code
    # Force sorry body for typecheck-only compile metric (PDA-style statement compile)
    if ":=" in code and not re.search(r":=\s*by\s+sorry\b", code):
        # replace proof body with sorry when a theorem/example is present
        code = re.sub(
            r"(theorem|example|lemma)\b([\s\S]*?):=\s*[\s\S]*$",
            r"\1\2:= by sorry",
            code,
            count=1,
        )
    if "theorem" in code or "example" in code or "lemma" in code:
        if ":=" not in code:
            code = code.rstrip() + " := by sorry"
    return code.strip() + "\n"


def compile_lean(
    code: str,
    *,
    project: Path = DEFAULT_PROJECT,
    timeout: float = 120.0,
) -> dict[str, Any]:
    project = Path(project)
    if not (project / "lakefile.lean").is_file() and not (project / "lakefile.toml").is_file():
        return {
            "ok": False,
            "compiled": False,
            "error": f"missing lake project at {project}",
            "normalized": None,
        }
    normalized = normalize_candidate(code)
    if not re.search(r"(?m)^\s*(theorem|lemma|example)\b", normalized):
        return {
            "ok": True,
            "compiled": False,
            "error": "no theorem/lemma/example declaration in candidate",
            "normalized": normalized,
        }
    stamp = f"Candidate_{int(time.time() * 1000)}_{abs(hash(normalized)) % 10_000_000}"
    # Write under FormL4AF/ so it can import Mathlib via the package
    target_dir = project / "FormL4AF"
    target_dir.mkdir(parents=True, exist_ok=True)
    path = target_dir / f"{stamp}.lean"
    try:
        path.write_text(normalized)
        proc = subprocess.run(
            ["lake", "env", "lean", str(path.relative_to(project))],
            cwd=project,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        ok = proc.returncode == 0
        err = (proc.stderr or "") + (proc.stdout or "")
        return {
            "ok": True,
            "compiled": ok,
            "returncode": proc.returncode,
            "error": None if ok else err[-4000:],
            "normalized": normalized,
            "path": str(path),
        }
    except subprocess.TimeoutExpired:
        return {
            "ok": False,
            "compiled": False,
            "error": "timeout",
            "normalized": normalized,
        }
    finally:
        try:
            path.unlink(missing_ok=True)
        except OSError:
            pass


__all__ = ["compile_lean", "normalize_candidate", "extract_lean_code", "DEFAULT_PROJECT"]
