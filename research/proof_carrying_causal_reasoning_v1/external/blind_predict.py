"""Offline prediction process. Its only input file consists of projected public tasks."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from fractions import Fraction
from pathlib import Path

from ..kernel.dag import CausalDAG
from ..kernel.scm import BinarySCM
from . import finite_replay as replay


def _opposites(first, second):
    # Restricted lexical negation; no learned concept or benchmark ID lookup.
    def positives(s):
        return {
            s.replace(token, replacement, 1)
            for token, replacement in (
                ("not ", ""),
                ("don't ", ""),
                ("do not ", ""),
                ("no ", ""),
                ("non-", ""),
            )
            if re.search(r"\b" + re.escape(token), s)
        }

    return first in positives(second) or second in positives(first)


def _marginal(text):
    if set(text) != {"background", "given_info", "question"} or any(
        type(x) is not str for x in text.values()
    ):
        return None
    q = re.fullmatch(
        r"Is ([^?]+) (more|less) likely than ([^?]+) overall\?", text["question"]
    )
    g = re.fullmatch(
        r"The overall probability of [^.]+ is (\d{1,3})%\. "
        r"For ([^,]+), the probability of ([^.]+) is (\d{1,3})%\. "
        r"For ([^,]+), the probability of ([^.]+) is (\d{1,3})%\.",
        text["given_info"],
    )
    if not q or not g or q[1] != g[3] or q[1] != g[6]:
        return None
    if not _opposites(q[1], q[3]) or not _opposites(g[2], g[5]):
        return None
    rates = [int(g[4]), int(g[7])]
    if any(n > 100 for n in (*rates, int(g[1]))):
        return None
    # Every mixture of these binary strata lies strictly on the same side
    # of 1/2, including uncertainty from percent rounding.
    if min(rates) > 50:
        return "yes" if q[2] == "more" else "no"
    if max(rates) < 50:
        return "no" if q[2] == "more" else "yes"
    return None


def _mechanism(row):
    probs = [Fraction(s) for s in row["p1"]]

    def p1(world):
        index = 0
        for parent in row["parents"]:
            index = (index << 1) | world[parent]
        return probs[index]

    return p1


def predict(protocol, claim_id, public):
    if protocol not in ("A", "B"):
        raise ValueError("unknown protocol")
    if public is None:
        return {"prediction": None, "reason": "missing_or_unsupported_input"}
    if protocol == "A":
        prediction = _marginal(public)
        return {
            "prediction": prediction,
            "reason": "binary_strata_marginal" if prediction else "unsupported_text",
        }
    replay.check_problem(public)
    nodes = public["nodes"]
    graph = CausalDAG.from_parents({row["name"]: row["parents"] for row in nodes})
    scm = BinarySCM(graph, {row["name"]: _mechanism(row) for row in nodes})
    p0, p1 = [
        scm.interventional_expectation(public["outcome"], {public["treatment"]: v})
        for v in (0, 1)
    ]
    cert = replay.certificate(claim_id, public, p0, p1)
    if not replay.verify(claim_id, public, replay.canonical(cert)):
        raise ValueError("certificate replay failed")
    return {"prediction": cert["prediction"], "certificate": cert}


def freeze(public_path, output_path):
    batch = json.loads(public_path.read_bytes())
    protocol = batch["protocol"]
    rows = [
        dict(id=row["id"], **predict(protocol, row["id"], row["task"]))
        for row in batch["rows"]
    ]
    data = (
        replay.canonical(
            {"protocol": protocol, "public_sha256": replay.digest(batch), "rows": rows}
        )
        + b"\n"
    )
    with output_path.open("xb") as stream:
        stream.write(data)
    return hashlib.sha256(data).hexdigest()


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("public", type=Path)
    ap.add_argument("predictions", type=Path)
    args = ap.parse_args()
    print(freeze(args.public, args.predictions))
