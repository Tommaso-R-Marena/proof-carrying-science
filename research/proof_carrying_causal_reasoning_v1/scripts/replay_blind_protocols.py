"""Replay the external evaluation and both frozen prediction files, offline."""

import argparse
import gzip
import hashlib
import json
import subprocess
import sys
import tempfile
import time
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
EVIDENCE = Path(__file__).resolve().parents[1] / "qualification" / "blind_protocols"
MODULE = "research.proof_carrying_causal_reasoning_v1.external"
ARCHIVE_SHA256 = "9fdae052b1ebe4ee6a19fdfb3e1eb88a381c7345df394cea524bcce97e2349b3"


def run(module, *args):
    return subprocess.check_output(
        [sys.executable, "-m", MODULE + "." + module, *args], cwd=ROOT
    )


def replay(archive):
    if hashlib.sha256(archive.read_bytes()).hexdigest() != ARCHIVE_SHA256:
        raise ValueError("reviewed CLadder release bytes required")
    with tempfile.TemporaryDirectory() as location:
        directory = Path(location)
        with zipfile.ZipFile(archive) as z:
            for name in ("cladder-v1-q-balanced.json", "cladder-v1-meta-models.json"):
                (directory / name).write_bytes(z.read(name))
        for protocol in ("A", "B"):
            started = time.monotonic()
            public = directory / (protocol + ".public")
            rows = directory / (protocol + ".rows")
            run("blind_eval", "prepare", protocol, directory, public)
            digest = run("blind_predict", public, rows).decode().strip()
            if rows.read_bytes() != gzip.decompress(
                (EVIDENCE / (protocol + ".rows.json.gz")).read_bytes()
            ):
                raise ValueError(
                    "prediction or certificate bytes differ from frozen rows"
                )
            report = json.loads(
                run("blind_eval", "score", directory, public, rows, digest)
            )
            if report != json.loads(
                (EVIDENCE / (protocol + ".report.json")).read_bytes()
            ):
                raise ValueError("scoring report differs")
            print(
                protocol,
                json.dumps(report["overall"]),
                "replay_seconds",
                round(time.monotonic() - started, 3),
            )
            if protocol == "B":
                print(
                    run("finite_replay", public, rows, report["public_sha256"], digest)
                    .decode()
                    .strip()
                )
        oracle_dir = directory / "C"
        run("cladder_certified_solver", "--data-dir", directory, "--out", oracle_dir)
        oracle = json.loads((oracle_dir / "cladder_certified_eval.json").read_bytes())
        if (
            oracle["protocol"] != "C"
            or (oracle["n_correct"], oracle["n"]) != (10112, 10112)
            or oracle["information_sources"]
            != json.loads((EVIDENCE / "C.sources.json").read_bytes())
        ):
            raise ValueError("historical generator regression differs")
        print(
            "C",
            oracle["n_correct"],
            "/",
            oracle["n"],
            json.dumps(oracle["information_sources"], sort_keys=True),
        )


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("archive", type=Path)
    replay(ap.parse_args().archive)
