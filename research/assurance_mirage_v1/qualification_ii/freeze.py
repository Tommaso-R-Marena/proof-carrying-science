"""Write new freeze inputs to an empty directory, or verify a published freeze."""

import argparse
import hashlib
import json
from pathlib import Path

from adjudicator import denied
from packets import packets


HERE = Path(__file__).resolve().parent
SOURCES = ("PROTOCOL.md", "packets.py", "adjudicator.py", "freeze.py")


def jsonl(rows):
    return "".join(json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n"
                   for row in rows).encode()


def products():
    raw = list(packets())
    return {
        "cases.jsonl": jsonl(raw),
        "answers.jsonl": jsonl({"id": row["id"], "denied": denied(row)} for row in raw),
    }


def frozen_files():
    files = products()
    data = {**files, **{name: (HERE / name).read_bytes() for name in SOURCES}}
    manifest = "".join(f"{hashlib.sha256(data[name]).hexdigest()}  {name}\n"
                       for name in sorted(data)).encode()
    return {**files, "freeze.sha256": manifest}


def verify(directory):
    for name, data in frozen_files().items():
        if (directory / name).read_bytes() != data:
            raise ValueError(f"freeze mismatch: {name}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write-new", type=Path)
    args = parser.parse_args()
    if args.write_new:
        args.write_new.mkdir(exist_ok=False)
        for name, data in frozen_files().items():
            (args.write_new / name).write_bytes(data)
    else:
        verify(HERE / "frozen")
