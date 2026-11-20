"""Replay the recorded transfer study with the exact pre-study detector source."""
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
BASE = "5cd0fe136bef17b2b869e6df96697aae256c1fe6"
MODULE = "research/evolving_safety_gate_v1"


def replay():
    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp) / MODULE
        work = target / "qualification"
        work.mkdir(parents=True)
        for name in ("catalog.py", "features.py"):
            data = subprocess.check_output(["git", "show", f"{BASE}:{MODULE}/{name}"], cwd=HERE)
            (target / name).write_bytes(data)
        (work / "observation_transfer.py").write_bytes((HERE / "observation_transfer.py").read_bytes())
        output = subprocess.check_output([sys.executable, "-m",
            "research.evolving_safety_gate_v1.qualification.observation_transfer"], cwd=tmp)
    if output != (HERE / "transfer-results.json").read_bytes():
        raise ValueError("frozen detector output differs")
    print("Verified 16 matched cases against the frozen catalog.")


if __name__ == "__main__":
    replay()
