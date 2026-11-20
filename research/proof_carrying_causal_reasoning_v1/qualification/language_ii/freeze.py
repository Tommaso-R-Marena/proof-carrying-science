"""Offline predictor process: only the three-string public projection enters predict."""

import argparse
import hashlib
import json
from pathlib import Path

from ...external.finite_replay import canonical, digest
from ...external.typed_language import predict


def freeze(public, target):
    batch = json.loads(public.read_bytes())
    if batch["protocol"] != "A":
        raise ValueError("expected public text")
    rows = [{"id": r["id"], **predict(r["task"])} for r in batch["rows"]]
    raw = (
        canonical({"protocol": "A", "public_sha256": digest(batch), "rows": rows})
        + b"\n"
    )
    with target.open("xb") as stream:
        stream.write(raw)
    return hashlib.sha256(raw).hexdigest()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("public", type=Path)
    parser.add_argument("target", type=Path)
    args = parser.parse_args()
    print(freeze(args.public, args.target))
