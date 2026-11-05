"""One-command Profile A research demonstration with a real witness subprocess.

All generated fixture keys are controlled by this one administrator/host. This
is not Profile C, external laboratory validation or a production deployment.
"""
from __future__ import annotations

import argparse
from dataclasses import asdict
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from research.authorization_history_v1 import history
from research.scientific_history_v1.receiver import POLICY, checker_identity
from research.scientific_receiver_v1.host import OperatorConfig
from research.scientific_receiver_v1.host import ReceiverService
from research.scientific_history_v2.audit import audit_material
from research.scientific_witness_v1.client import WitnessClient
from research.scientific_witness_v1.protocol import decode_anchor
from .coordinator import ScientificAuthority, AuthorityRejected, recover

ROOT = Path(__file__).resolve().parents[2]
FIXTURES = ROOT / "research/scientific_receiver_v1/fixtures"


def write_secret(path, raw):
    descriptor = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    with os.fdopen(descriptor, "wb") as stream:
        stream.write(raw)


def sign_intent(root, anchor, first, second, candidate, event_id):
    payload = history.proposed_payload(root, anchor, event_id=event_id,
                                       candidate=candidate, certificate=b"")
    return history.Envelope(payload, first.sign(payload.signing_bytes()),
                            second.sign(payload.signing_bytes())).encode()


def start_server(out, config_path):
    ready = out / "ready.json"
    log = (out / "witness-server.log").open("ab")
    process = subprocess.Popen([sys.executable, "-m", "research.scientific_witness_v1.server",
        "serve", "--db", str(out / "witness.sqlite"), "--root", str(out / "root.json"),
        "--config", str(config_path), "--key", str(out / "witness.key"),
        "--port", "0", "--ready-file", str(ready)], cwd=ROOT,
        stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT,
        env={"PATH": os.defpath, "PYTHONHASHSEED": "0"})
    log.close()
    try:
        deadline = time.monotonic() + 90
        while not ready.is_file():
            if process.poll() is not None:
                raise RuntimeError("Witness startup failed; inspect retained server log")
            if time.monotonic() >= deadline:
                raise TimeoutError("Witness startup deadline exceeded")
            time.sleep(.05)
        return process, json.loads(ready.read_bytes())
    except BaseException:
        process.terminate(); process.wait(timeout=10)
        raise


def run(config_path, out):
    out = Path(out).resolve()
    out.mkdir(exist_ok=False)
    config_path = Path(config_path).resolve()
    config = OperatorConfig.load(config_path)
    first, second, witness_key = (Ed25519PrivateKey.generate() for _ in range(3))
    genesis = (FIXTURES / "zero-step.wire").read_bytes()
    root = history.Root(first.public_key().public_bytes_raw(), second.public_key().public_bytes_raw(),
                        POLICY, checker_identity(config), b"scientific-authority-v2-genesis", genesis)
    (out / "root.json").write_bytes(root.encode())
    write_secret(out / "witness.key", witness_key.private_bytes_raw())
    subprocess.run([sys.executable, "-m", "research.scientific_witness_v1.server", "init",
        "--db", str(out / "witness.sqlite"), "--root", str(out / "root.json"),
        "--config", str(config_path), "--key", str(out / "witness.key")], cwd=ROOT, check=True)
    local = out / "producer.sqlite"
    history.History.create(local, root)
    shutil.copyfile(local, out / "producer-genesis-backup.sqlite")
    process, ready = start_server(out, config_path)
    try:
        # Key comes from operator-created bootstrap, never from ready/export bytes.
        client = WitnessClient("http://127.0.0.1:" + str(ready["port"]), root,
                               config, witness_key.public_key().public_bytes_raw())
        authority = ScientificAuthority(local, root, history.initial(root), config, client)
        accepted = []
        for index, name in enumerate(("one-step", "multi-step-nonsingleton")):
            current = authority.current()
            raw = (FIXTURES / (name + ".wire")).read_bytes()
            intent = sign_intent(root, current.anchor, first, second, raw,
                                 ("demo-" + str(index)).encode())
            (out / ("intent-" + str(index) + ".wire")).write_bytes(intent)
            start = time.monotonic()
            result = authority.submit(intent)
            accepted.append({"fixture": name, "generation": result.anchor.generation,
                             "raw_sha256": result.artifact.raw_sha256,
                             "result": result.artifact.to_dict()["result"],
                             "wall_seconds": time.monotonic() - start})
        bad_raw = (FIXTURES / "wrong-total.wire").read_bytes()
        negative_service = ReceiverService(config)
        negative = negative_service.verify_bytes(bad_raw)
        assert (negative["receipt"]["accepted"] is False
                and negative["receipt"]["errors"] == []
                and all(negative["receipt"]["checks"].values())
                and negative["receipt"]["verifier_response"]["accepted"] is False)
        import gzip
        (out / "independent-false-total.receipt.json.gz").write_bytes(
            gzip.compress(json.dumps(negative, sort_keys=True).encode(), mtime=0))
        bad = sign_intent(root, authority.current().anchor, first, second,
                          bad_raw, b"false-science")
        before = local.read_bytes()
        try:
            authority.submit(bad)
            raise AssertionError("False science was admitted")
        except ValueError:
            pass
        assert local.read_bytes() == before
        export = client.export()
        (out / "witness-export.json").write_text(json.dumps(export, indent=2) + "\n")
        report = audit_material(root, decode_anchor(export["anchor"]),
                                tuple(bytes.fromhex(x) for x in export["envelopes"]), config)
        (out / "independent-history-audit.json").write_text(json.dumps(report.as_dict(), indent=2) + "\n")
        # Whole producer-store rollback while the live witness remains unchanged.
        shutil.copyfile(out / "producer-genesis-backup.sqlite", local)
        rollback_detected = False
        try:
            ScientificAuthority(local, root, history.initial(root), config, client)
        except AuthorityRejected:
            rollback_detected = True
        assert rollback_detected
        recovered = recover(local, root, config, client)
        reopened = ScientificAuthority(local, root, recovered.anchor, config, client)
        assert reopened.current().anchor.generation == 2
        result = {"format": "pcs-scientific-authority-v2-demo", "profile": "A:same-host-separate-processes",
                  "independently_administered_witness": False,
                  "witness_process_pid": process.pid, "coordinator_pid": os.getpid(),
                  "accepted": accepted, "false_scientific_candidate_rejected": True,
                  "whole_producer_store_rollback_detected": rollback_detected,
                  "recovery_materialized_witnessed_events": recovered.materialized_finalized_events,
                  "retrospective_history_math": report.retrospective_mathematical_validity,
                  "historical_occurrence": "Authenticated witness assertions; honest witness/key/storage continuity required",
                  "scientific_acceptance": False, "production_authority": False,
                  "empirical_validity": "UNVERIFIED", "operator_config_sha256": root.checker.hex()}
        (out / "demo.json").write_text(json.dumps(result, indent=2) + "\n")
        return result
    finally:
        process.terminate()
        try: process.wait(timeout=10)
        except subprocess.TimeoutExpired: process.kill(); process.wait()
        (out / "witness.key").unlink(missing_ok=True)  # Never publish fixture private keys.


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(run(args.config, args.out), indent=2))


if __name__ == "__main__":
    main()
