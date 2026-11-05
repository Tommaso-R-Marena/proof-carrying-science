"""Read-only preservation of every PR166 predecessor blob and mode."""
import json
from pathlib import Path
import subprocess

BASE = "77250c708dbc5e74c2c4bc4745acc7ef217af87c"
ROOT = Path(__file__).resolve().parents[2]


def check():
    def tree(ref):
        raw = subprocess.check_output(["git", "ls-tree", "-rz", "-r", ref], cwd=ROOT)
        return {x.split(b"\t", 1)[1]: x.split(b"\t", 1)[0] for x in raw.split(b"\0") if x}
    old, new = tree(BASE), tree("HEAD")
    if any(new.get(name) != value for name, value in old.items()):
        raise ValueError("Predecessor file or mode changed")
    if subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT).strip():
        raise ValueError("Clean committed source required")
    return {"base": BASE, "head": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
            "predecessor_files_and_modes_preserved": len(old), "new_files": len(new)-len(old),
            "passed": True, "production_authority": False}


if __name__ == "__main__":
    print(json.dumps(check(), indent=2))
