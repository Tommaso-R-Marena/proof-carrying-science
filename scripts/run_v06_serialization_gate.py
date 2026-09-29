from __future__ import annotations

import json
import platform
import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def run(name: str, command: list[str]) -> dict:
    proc = subprocess.run(
        command,
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    return {
        "name": name,
        "command": command,
        "exit_code": proc.returncode,
        "stdout": proc.stdout,
        "stderr": proc.stderr,
    }


def main() -> int:
    node = shutil.which("node")
    if node is None:
        print("FAIL: Node.js is required for the v0.6 serialization gate", file=sys.stderr)
        return 2

    steps = [
        run(
            "pytest_v06_serialization",
            [
                sys.executable,
                "-m",
                "pytest",
                "-q",
                "tests/test_canonical_json_v06.py",
                "tests/test_crypto_domains_v06.py",
                "tests/test_signing_v06.py",
                "tests/test_v06_crypto_schemas.py",
                "tests/test_certificate_v06.py",
                "tests/test_package_v06.py",
            ],
        ),
        run(
            "node_cross_language_vectors",
            [node, "scripts/check_jcs_cross_language.mjs"],
        ),
        run(
            "python_node_differential_stress",
            [
                sys.executable,
                "scripts/stress_jcs_against_node.py",
                "--numbers",
                "20000",
                "--objects",
                "500",
                "--seed",
                "20260929",
            ],
        ),
    ]

    result = {
        "format": "pcs-v06-serialization-gate-v1",
        "python": {
            "executable": sys.executable,
            "version": platform.python_version(),
            "implementation": platform.python_implementation(),
        },
        "node": subprocess.run(
            [node, "--version"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        ).stdout.strip(),
        "steps": steps,
        "pass": all(step["exit_code"] == 0 for step in steps),
        "interpretation": (
            "This gate is cross-language executable conformance evidence for the "
            "PCS v0.6 canonicalization/crypto payload boundary. It is not a formal "
            "proof of parser, SHA-256, Ed25519, or runtime correctness."
        ),
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
