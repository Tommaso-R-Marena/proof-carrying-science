"""Fail if any predecessor tracked file/mode is rewritten by the V2 stack."""
import json
from pathlib import Path
import subprocess

BASE = "7be674df70eb3108c9dbd8b0b97f42a728bde000"
ROOT = Path(__file__).resolve().parents[2]


def check():
    changes = subprocess.check_output(["git", "diff", "--name-status", BASE, "--"],
                                      cwd=ROOT, text=True).splitlines()
    failures = [line for line in changes if not line.startswith("A\t")]
    if failures:
        raise RuntimeError("Predecessor source/mode changed: " + repr(failures))
    return {"format": "pcs-authority-v2-predecessor-preservation-v1", "base": BASE,
            "all_predecessor_tracked_files_and_modes_unchanged": True,
            "new_files": len(changes), "production_authority": False}


if __name__ == "__main__":
    print(json.dumps(check(), indent=2))
