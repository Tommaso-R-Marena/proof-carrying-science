"""Offline replay of two authored revisions, separate final measurement and archived failure."""
from __future__ import annotations

import argparse
import json

from . import receiver as r

DEV = "4f388e0cfdf3672b5446a3672e2587ad46c5b9aed1e6624174afc9a99ee63257"
FINAL = "b13b0b2c8597b114777cfdf405038e23c3c71a8fcf7ce58bdb46267f3204d787"
BASE = "330faf19134513cd026ee2d804bd7b64f1a05be27e17799ebd7dfcedd476e7e2"
CANDIDATE = "825b66fd0a022c58b23a60e5479f31cb63c898f8589b7c267148988f3e85d393"


def historical():
    old = r.PROJECT / "qualification/scope_pilot"
    attempt, prompts = [(old / name).read_bytes() for name in ("attempt.json", "prompts.json")]
    r.require(r.sha(attempt) == "ced61eb3011f66a3b313fec4361f73d5d70eba4654cc9f1a4e91f3c3c26820eb"
              and r.sha(prompts) == "532a525a394ddfbbf2a8944afd074c4e749768e1311a0a23074e2fe8f79dc437",
              "archived material changed")
    ledger = r.decode(attempt)
    candidate, = ledger["candidates"]
    part, = candidate["content"]["parts"]
    wire = part["text"].encode("utf-8")
    identifiers = list(r.decode(wire))
    requested = [i for i, _ in r.decode(prompts)]
    try:
        r.exact_ids(requested, identifiers)
    except r.Rejected as error:
        return {"accepted": False, "reason": str(error), "requested": len(requested),
                "received": len(identifiers), "response_sha256": r.sha(wire)}
    raise AssertionError("archive unexpectedly satisfies the identifier contract")


def record(wire, receipt):
    return {"response_utf8": wire.decode("utf-8"), "receipt": receipt}


def run():
    dev, final, base, new = [(r.HERE / (name + ".json")).read_bytes()
                             for name in ("development", "final", "baseline", "synonym")]
    r.require(r.sha(new) == CANDIDATE, "predeclared candidate")
    a = r.Submission(base, r.response(dev, DEV, "development", base))
    prior = r.replay(dev, DEV, BASE, [a])
    head = r.digest(prior)
    b = r.Submission(new, r.response(dev, DEV, "development", new, head, 1))
    promoted = r.advance(dev, DEV, BASE, [a], head, b)
    champion = r.digest(promoted)
    heldout = []
    for generation, revision, history, anchor in [(0, base, [a], head), (1, new, [a, b], champion)]:
        measured = r.measure_final(final, FINAL, dev, DEV, BASE, history, anchor)
        wire = r.response(final, FINAL, "final", revision, anchor, generation)
        r.require(r.sha(wire) == measured["response_sha256"], "final batch changed")
        heldout.append(record(wire, measured))
    return {"historical": historical(), "development": [record(a.response, prior), record(b.response, promoted)],
            "final": heldout}


if __name__ == "__main__":
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--check", action="store_true", help="compare all replayed receipt and response bytes")
    args = cli.parse_args()
    wire = (json.dumps(run(), sort_keys=True, indent=2) + "\n").encode("ascii")
    if args.check:
        r.require(wire == (r.HERE / "transcript.json").read_bytes(), "recorded transcript differs")
        print(f"verified full transcript {r.sha(wire)}")
    else:
        print(wire.decode("ascii"), end="")
