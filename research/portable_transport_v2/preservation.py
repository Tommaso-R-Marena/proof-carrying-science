"""Refuse any change to the frozen, qualified V2 predecessor tree."""
import json
from pathlib import Path
import subprocess

BASE = "1e41f82f5511d368b7d7309d3fa5c68a1903203e"
ROOT = Path(__file__).resolve().parents[2]


def check():
    def tree(ref):
        raw = subprocess.check_output(["git", "ls-tree", "-rz", "-r", ref], cwd=ROOT)
        return {entry.split(b"\t", 1)[1]: entry.split(b"\t", 1)[0]
                for entry in raw.split(b"\x00") if entry}
    old, new = tree(BASE), tree("HEAD")
    bad = [name.decode() for name, value in old.items() if new.get(name) != value]
    dirty = subprocess.check_output(["git", "diff", "--name-only", "HEAD"], cwd=ROOT, text=True)
    if bad or dirty.strip():
        raise RuntimeError("Predecessor or working source changed: " + repr((bad, dirty)))
    return {"base": BASE, "head": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
            "predecessor_files_and_modes_preserved": len(old), "new_files": len(new) - len(old),
            "passed": True, "production_authority": False}


if __name__ == "__main__":
    print(json.dumps(check(), indent=2))
