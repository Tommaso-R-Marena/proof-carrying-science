"""Offline replay of reviewer-signed promotions for bounded detector truth tables."""
from __future__ import annotations

import argparse
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey


HERE = Path(__file__).resolve().parent
GATE_SOURCE = HERE.parent / "formal" / "EvolvingSafetyGate.lean"
KERNEL_SOURCES = (GATE_SOURCE, HERE / "HardReview.lean", HERE / "ReceiptCheck.lean")
PREFIX = b"PCS-research/robust-review/ed25519/v1\0"
LIMIT = 131_072
HEX64 = re.compile(r"[0-9a-f]{64}")
NAME = re.compile(r"[a-z][a-z0-9-]{0,63}")
CHECKPOINT_FIELDS = {
    "schema", "challenge", "key_sha256", "review_sha256", "hard_sha256",
    "rule_sha256", "epoch", "generation", "champion_sha256", "last_receipt_sha256",
}


class Rejected(ValueError):
    """The supplied bytes or measured transition fail the review contract."""


def require(ok, reason):
    if not ok:
        raise Rejected(reason)


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
                      allow_nan=False).encode("ascii") + b"\n"


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def rule_digest():
    # Include transitive research source and both envelope and semantic receivers.
    sources = (*KERNEL_SOURCES, Path(__file__).resolve())
    return digest(canonical({path.name: digest(path.read_bytes()) for path in sources}))


def parse(raw):
    require(type(raw) is bytes and len(raw) <= LIMIT, "oversized or invalid artifact")
    try:
        doc = json.loads(raw)
        # Exact re-encoding rejects duplicate keys, whitespace and alternate spellings.
        require(canonical(doc) == raw, "noncanonical JSON")
    except (UnicodeError, ValueError, RecursionError) as exc:
        raise Rejected("invalid canonical JSON") from exc
    return doc


def fields(doc, names):
    require(type(doc) is dict and doc.keys() == names, "unexpected fields")


def uint(value, maximum):
    return type(value) is int and 0 <= value <= maximum


def hex_field(value, pattern=HEX64):
    return type(value) is str and pattern.fullmatch(value) is not None


def bounded_read(path):
    with Path(path).open("rb") as handle:
        raw = handle.read(LIMIT + 1)
    require(len(raw) <= LIMIT, "artifact exceeds byte bound")
    return raw


def read_cases(rows, ids):
    require(type(rows) is list and 1 <= len(rows) <= 512, "invalid case count")
    result = []
    for row in rows:
        fields(row, {"id", "packet", "flag"})
        name = row["id"]
        require(type(name) is str and NAME.fullmatch(name) and name not in ids,
                "invalid or duplicate case id")
        ids.add(name)
        require(uint(row["packet"], 7) and type(row["flag"]) is bool, "invalid labeled packet")
        result.append((row["packet"], row["flag"]))
    return result


def mask(raw, expected):
    require(digest(raw) == expected, "candidate source digest mismatch")
    doc = parse(raw)
    fields(doc, {"schema", "admission", "mask"})
    require(doc["schema"] == "pcs.detector-table/v1" and doc["admission"] == "jointChannel"
            and uint(doc["mask"], 255), "unsupported candidate")
    return doc["mask"]


def check_bindings(checkpoint, public_key, review_raw, envelope_raw, old_raw, new_raw):
    state = parse(checkpoint)
    fields(state, CHECKPOINT_FIELDS)
    require(state["schema"] == "pcs.review-checkpoint/v1" and hex_field(state["challenge"], NAME),
            "invalid checkpoint")
    require(all(hex_field(value) for key, value in state.items() if key.endswith("_sha256")),
            "malformed checkpoint digest")
    require(uint(state["epoch"], 2**63 - 1) and uint(state["generation"], 2**63 - 2),
            "invalid epoch or generation")
    require(len(public_key) == 32 and digest(public_key) == state["key_sha256"],
            "reviewer key mismatch")
    require(state["rule_sha256"] == rule_digest(), "rule source mismatch")
    require(digest(review_raw) == state["review_sha256"], "review digest mismatch")
    envelope = parse(envelope_raw)
    fields(envelope, {"edge", "ed25519"})
    edge = envelope["edge"]
    fields(edge, {"schema", "challenge", "epoch", "previous_checkpoint_sha256", "generation",
                  "parent_sha256", "candidate_sha256", "review_sha256", "rule_sha256"})
    require(hex_field(envelope["ed25519"], re.compile(r"[0-9a-f]{128}")), "malformed signature")
    try:
        Ed25519PublicKey.from_public_bytes(public_key).verify(
            bytes.fromhex(envelope["ed25519"]), PREFIX + canonical(edge))
    except InvalidSignature as exc:
        raise Rejected("invalid review signature") from exc
    require(edge["schema"] == "pcs.review-edge/v1" and edge["challenge"] == state["challenge"]
            and uint(edge["generation"], 2**63 - 1) and edge["generation"] == state["generation"] + 1
            and uint(edge["epoch"], 2**63 - 1) and edge["epoch"] == state["epoch"]
            and edge["previous_checkpoint_sha256"] == digest(checkpoint)
            and edge["parent_sha256"] == state["champion_sha256"]
            and edge["review_sha256"] == state["review_sha256"]
            and edge["rule_sha256"] == state["rule_sha256"]
            and hex_field(edge["candidate_sha256"]), "stale or mismatched edge")
    review = parse(review_raw)
    fields(review, {"schema", "challenge", "epoch", "hard", "measured"})
    require(review["schema"] == "pcs.review-cases/v1" and review["challenge"] == state["challenge"]
            and uint(review["epoch"], 2**63 - 1) and review["epoch"] == state["epoch"],
            "wrong evaluation context")
    require(digest(canonical(review["hard"])) == state["hard_sha256"], "hard contract mismatch")
    ids = set()
    hard = read_cases(review["hard"], ids)
    measured = read_cases(review["measured"], ids)
    old = mask(old_raw, edge["parent_sha256"])
    new = mask(new_raw, edge["candidate_sha256"])
    successor = {**state, "generation": edge["generation"], "champion_sha256": edge["candidate_sha256"],
                 "last_receipt_sha256": digest(envelope_raw)}
    return successor, old, new, hard, measured


def python_evaluation(old, new, hard, measured):
    # Direct lookup on all rows gives complete, receiver-computed predictions.
    def correct(table, rows):
        return [bool((table >> packet) & 1) == label for packet, label in rows]

    old_hard, new_hard = correct(old, hard), correct(new, hard)
    old_score, new_score = sum(correct(old, measured)), sum(correct(new, measured))
    witnessed = (old & 3) == 2 and (new & 3) == 2
    ok = witnessed and all(not a or b for a, b in zip(old_hard, new_hard)) and old_score < new_score
    return f"{str(ok).lower()} {old_score} {new_score} {sum(old_hard)} {sum(new_hard)}"


@contextmanager
def lean_kernel():
    lean = shutil.which("lean")
    require(lean is not None, "Lean 4.28.0 is required")
    with tempfile.TemporaryDirectory(prefix="pcs-robust-review-") as tmp:
        out = Path(tmp)
        env = {**os.environ, "LEAN_PATH": str(out)}

        def run(args):
            proc = subprocess.run([lean, *args], cwd=out, env=env, capture_output=True,
                                  text=True, check=False, timeout=90)
            require(proc.returncode == 0, "Lean replay failed: " + proc.stderr[-600:] + proc.stdout[-600:])
            return proc.stdout.strip()

        require("version 4.28.0," in run(["--version"]), "wrong Lean version")
        for source in KERNEL_SOURCES:
            shutil.copyfile(source, out / source.name)
            run(["-DwarningAsError=true", "-o", source.stem + ".olean", source.name])

        def replay(old, new, hard, measured):
            def codes(rows):
                return ",".join(str(2 * packet + int(label)) for packet, label in rows)
            return run(["--run", "ReceiptCheck.lean", str(old), str(new), codes(hard), codes(measured)])

        yield replay


def evaluate(inputs, kernel):
    state, old, new, hard, measured = check_bindings(*inputs)
    expected = python_evaluation(old, new, hard, measured)
    replayed = kernel(old, new, hard, measured)
    require(replayed == expected, "independent semantic replays disagree")
    require(replayed.startswith("true "), "semantic promotion rejected")
    return state


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for arg in ("checkpoint", "public_key", "review", "envelope", "incumbent", "candidate"):
        parser.add_argument(arg, type=Path)
    args = parser.parse_args()
    try:
        blobs = [bounded_read(getattr(args, key)) for key in vars(args)]
        with lean_kernel() as kernel:
            result = evaluate(blobs, kernel)
        sys.stdout.buffer.write(canonical(result))
    except (Rejected, OSError, subprocess.TimeoutExpired) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
