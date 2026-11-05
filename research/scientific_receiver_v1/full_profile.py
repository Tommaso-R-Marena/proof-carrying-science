"""Operator experiment: replay real receiving with all inventoried module pins.

The qualification SHA must come from the operator's trusted review channel.
Neither this bootstrap nor an ephemeral receipt establishes a protected root.
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
from pathlib import Path
import time

from .host import OperatorConfig, Pin, ReceiverService, replay_signed_receipt

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            h.update(chunk)
    return h.hexdigest()


def run(qualification: Path, expected_sha256: str, out: Path) -> dict:
    qpath = qualification / "qualification.json"
    if digest(qpath) != expected_sha256:
        raise ValueError("qualification differs from operator-pinned identity")
    q = json.loads(qpath.read_bytes())
    artifacts_path = qualification / "module-artifacts.json"
    if digest(artifacts_path) != q["module_artifacts_sha256"]:
        raise ValueError("module inventory differs from pinned qualification")
    manifest = json.loads(artifacts_path.read_bytes())
    if digest(qualification / "environment.json") != q["environment_sha256"]:
        raise ValueError("search environment differs from pinned qualification")
    environment = json.loads((qualification / "environment.json").read_bytes())
    command = tuple(q["command"])
    if len(command) != 3 or command[1] != "--run" or not Path(command[0]).is_absolute():
        raise ValueError("experiment requires the directly qualified Lean --run command")
    sources = {str((ROOT / name).resolve()): sha for name, sha in q["source_sha256"].items()}
    # Host and reference are trusted operator code, additionally pinned here.
    for name in ("host.py", "reference.py", "full_profile.py"):
        p = HERE / name
        sources[str(p.resolve())] = digest(p)
    if str(Path(command[2]).resolve()) not in sources:
        raise ValueError("Main source is absent from qualified inventory")
    dependencies = {entry["path"]: entry["sha256"] for entry in manifest["artifacts"]}
    if sources.keys() & dependencies.keys():
        raise ValueError("ambiguous pin classification")
    config = OperatorConfig(command, q["lean_sha256"],
                            tuple(Pin(kind, path, sha) for kind, inventory in
                                  (("source", sources), ("dependency", dependencies))
                                  for path, sha in sorted(inventory.items())),
                            q["cwd"], tuple(sorted(environment.items())), q["lean_version"],
                            timeout_seconds=60)
    out.mkdir(parents=True, exist_ok=False)
    service = ReceiverService(config)
    externally_retained_key = service.public_key_hex
    observations = []
    for fixture, expected in (("multi-step-nonsingleton", True), ("wrong-environment", False)):
        raw = (HERE / "fixtures" / (fixture + ".wire")).read_bytes()
        start = time.monotonic()
        envelope = service.verify_bytes(raw)
        elapsed = time.monotonic() - start
        receipt = envelope["receipt"]
        if (receipt["errors"] or receipt["accepted"] is not expected
                or not all(receipt["checks"].values())
                or not replay_signed_receipt(envelope, externally_retained_key)):
            raise RuntimeError("actual full-profile replay failed: " + repr(receipt["errors"]))
        encoded = json.dumps(envelope, sort_keys=True, separators=(",", ":")).encode() + b"\n"
        target = out / (fixture + ".receipt.json.gz")
        target.write_bytes(gzip.compress(encoded, mtime=0))
        observations.append({"fixture": fixture, "raw_sha256": hashlib.sha256(raw).hexdigest(),
                             "accepted": receipt["accepted"], "checks": receipt["checks"],
                             "wall_seconds": elapsed, "receipt_archive": target.name,
                             "archive_sha256": digest(target),
                             "receipt_uncompressed_sha256": hashlib.sha256(encoded).hexdigest()})
    report = {"format": "pcs-scientific-full-profile-experiment-v1",
              "qualification_sha256": expected_sha256, "source_pins": len(sources),
              "dependency_pins": len(dependencies), "declared_modules": manifest["modules"],
              "operator_config_sha256": envelope["receipt"]["operator_config_sha256"],
              "ephemeral_receipt_public_key": externally_retained_key, "observations": observations,
              "scientific_acceptance": False, "production_authority": False,
              "scope": "Actual receiving with complete inventoried Lean module artifacts and toolchain shared libraries pinned before/after. No OS-loaded mapping, compiler correspondence, transient-substitution exclusion, independent key identity or protected host root is established."}
    (out / "full-profile.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    return report


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--qualification", required=True, type=Path)
    p.add_argument("--qualification-sha256", required=True)
    p.add_argument("--out", required=True, type=Path)
    a = p.parse_args()
    print(json.dumps(run(a.qualification, a.qualification_sha256, a.out), indent=2))
