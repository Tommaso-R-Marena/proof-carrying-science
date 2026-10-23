import json, subprocess
from pathlib import Path

BASE = "b025ad4297252c0601b7b9c9a85859267a89c1fb"
ROOT = Path(__file__).resolve().parents[2]


def check():
    def tree(ref):
        raw = subprocess.check_output(["git", "ls-tree", "-rz", "-r", ref], cwd=ROOT)
        return {
            x.split(b"\t", 1)[1]: x.split(b"\t", 1)[0] for x in raw.split(b"\0") if x
        }

    old, new = tree(BASE), tree("HEAD")
    if any(new.get(p) != v for p, v in old.items()):
        raise ValueError("Predecessor source changed")
    if any(
        not (
            p.startswith(b"research/scientific_engines_v1/")
            or p == b".github/workflows/pcs-scientific-engines-v1.yml"
        )
        for p in new.keys() - old.keys()
    ):
        raise ValueError("Unrelated addition")
    return dict(
        passed=True,
        base=BASE,
        previous_files_preserved=len(old),
        new_files=len(new) - len(old),
        production_authority=False,
    )


if __name__ == "__main__":
    print(json.dumps(check(), indent=2))
