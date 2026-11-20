"""Recompute all archived structured ATE certificates with variable elimination."""

import argparse
import gzip
import hashlib
import json
import tempfile
import zipfile
from pathlib import Path

from ..external import finite_replay
from ..external.blind_predict import _mechanism
from ..kernel.dag import CausalDAG
from ..kernel.elimination import exact_mass
from ..kernel.scm import BinarySCM
from ..scripts.replay_blind_protocols import ARCHIVE_SHA256, EVIDENCE, run


def recompute(public):
    old = json.loads(gzip.decompress((EVIDENCE / "B.rows.json.gz").read_bytes()))
    report = json.loads((EVIDENCE / "B.report.json").read_bytes())
    if (
        public["protocol"] != "B"
        or finite_replay.digest(public) != report["public_sha256"]
        or hashlib.sha256(finite_replay.canonical(old) + b"\n").hexdigest()
        != report["predictions_sha256"]
    ):
        raise ValueError("batch differs from archived evidence")
    verified = 0
    for issue, receipt in zip(public["rows"], old["rows"], strict=True):
        if issue["id"] != receipt["id"]:
            raise ValueError("claim ID mismatch")
        claim, claim_id = issue["task"], issue["id"]
        if claim is None:
            if receipt["prediction"] is not None or "certificate" in receipt:
                raise ValueError("certificate for unissued claim")
            continue
        finite_replay.check_problem(claim)
        rows = claim["nodes"]
        graph = CausalDAG.from_parents({n["name"]: n["parents"] for n in rows})
        scm = BinarySCM(graph, {n["name"]: _mechanism(n) for n in rows})
        p0, p1 = [
            exact_mass(scm, {claim["outcome"]: 1}, {claim["treatment"]: t}).probability
            for t in (0, 1)
        ]
        certificate = finite_replay.certificate(claim_id, claim, p0, p1)
        if (
            certificate != receipt["certificate"]
            or receipt["prediction"] != certificate["prediction"]
            or not finite_replay.verify(
                claim_id, claim, finite_replay.canonical(certificate)
            )
        ):
            raise ValueError(f"certificate replay differs on {claim_id}")
        verified += 1
    if verified != report["verified_certificates"]:
        raise ValueError("incomplete certificate replay")
    return verified


def replay(archive):
    if hashlib.sha256(archive.read_bytes()).hexdigest() != ARCHIVE_SHA256:
        raise ValueError("pinned CLadder archive required")
    with tempfile.TemporaryDirectory() as tmp:
        folder = Path(tmp)
        with zipfile.ZipFile(archive) as z:
            for n in ("cladder-v1-q-balanced.json", "cladder-v1-meta-models.json"):
                (folder / n).write_bytes(z.read(n))
        dest = folder / "public"
        run("blind_eval", "prepare", "B", folder, dest)
        print(
            recompute(json.loads(dest.read_bytes())),
            "certificates reproduced and independently verified",
        )


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("archive", type=Path)
    replay(p.parse_args().archive)
