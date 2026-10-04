from __future__ import annotations

import json
import subprocess
import sys
import unicodedata
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

REQUIRED_GOVERNANCE_FILES = {
    "CONTRIBUTING.md",
    ".github/pull_request_template.md",
    "docs/REPOSITORY_INTEGRITY_POLICY.md",
    "docs/BRANCH_RECONCILIATION_2026-10-04.md",
}

REQUIRED_DIRECT_EXECUTABLES = {
    "scripts/verify_lean.sh",
    "scripts/verify_lean_real.sh",
}

REQUIRED_GITATTRIBUTES = {
    "*.sh text eol=lf",
}


def _git(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def _tracked_modes() -> dict[str, str]:
    proc = _git("ls-files", "--stage", "-z")
    if proc.returncode:
        raise RuntimeError(proc.stderr.strip() or "git ls-files failed")
    modes: dict[str, str] = {}
    for record in proc.stdout.split("\0"):
        if not record:
            continue
        meta, path = record.split("\t", 1)
        mode, _sha, stage = meta.split()
        if stage != "0":
            raise RuntimeError(f"unmerged index entry for {path} (stage {stage})")
        modes[path] = mode
    return modes


def _read_bytes(path: str) -> bytes:
    return (ROOT / path).read_bytes()


def audit_repository() -> dict:
    errors: list[str] = []
    warnings: list[str] = []

    try:
        modes = _tracked_modes()
    except Exception as exc:
        return {
            "format": "pcs-repository-integrity-v1",
            "pass": False,
            "errors": [f"cannot inspect tracked Git metadata: {exc}"],
            "warnings": [],
        }

    tracked = set(modes)

    for path in sorted(REQUIRED_GOVERNANCE_FILES):
        if path not in tracked:
            errors.append(f"required governance file is not tracked: {path}")

    attributes_path = ROOT / ".gitattributes"
    if ".gitattributes" not in tracked or not attributes_path.is_file():
        errors.append(".gitattributes must be tracked")
    else:
        lines = {
            line.strip()
            for line in attributes_path.read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        }
        for required in sorted(REQUIRED_GITATTRIBUTES):
            if required not in lines:
                errors.append(f".gitattributes is missing required rule: {required}")

    shell_paths = sorted(path for path in tracked if path.endswith(".sh"))
    for path in shell_paths:
        mode = modes[path]
        raw = _read_bytes(path)
        if mode != "100755":
            errors.append(
                f"tracked shell entrypoint must be executable (100755), got {mode}: {path}"
            )
        if not raw.startswith(b"#!"):
            errors.append(f"tracked .sh file must start with a shebang: {path}")
        if b"\r\n" in raw:
            errors.append(f"tracked shell file contains CRLF line endings: {path}")
        if raw and not raw.endswith(b"\n"):
            warnings.append(f"tracked shell file does not end with a newline: {path}")

    for path in sorted(REQUIRED_DIRECT_EXECUTABLES):
        if path not in tracked:
            errors.append(f"required direct executable is not tracked: {path}")
        elif modes[path] != "100755":
            errors.append(
                f"required direct executable lost its Git execute bit: {path} ({modes[path]})"
            )

    # Cross-platform repositories must not contain names that alias under Unicode
    # normalization or case-insensitive filesystems.
    normalized: dict[str, str] = {}
    for path in sorted(tracked):
        key = unicodedata.normalize("NFC", path).casefold()
        previous = normalized.get(key)
        if previous is not None and previous != path:
            errors.append(
                f"cross-platform path collision: {previous!r} and {path!r}"
            )
        else:
            normalized[key] = path

    root_toolchain = ROOT / "lean-toolchain"
    formal_toolchain = ROOT / "formal" / "lean-toolchain"
    if root_toolchain.is_file() and formal_toolchain.is_file():
        if root_toolchain.read_bytes() != formal_toolchain.read_bytes():
            errors.append(
                "root lean-toolchain and formal/lean-toolchain differ; "
                "toolchain pin changes must be deliberate and synchronized"
            )
    else:
        errors.append("both lean-toolchain and formal/lean-toolchain must exist")

    result = {
        "format": "pcs-repository-integrity-v1",
        "pass": not errors,
        "tracked_paths": len(tracked),
        "tracked_shell_files": shell_paths,
        "required_direct_executables": sorted(REQUIRED_DIRECT_EXECUTABLES),
        "errors": errors,
        "warnings": warnings,
    }
    return result


def main() -> int:
    result = audit_repository()
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
