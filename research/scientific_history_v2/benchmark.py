"""Execute the frozen cold-replay experiment with real Lean and signatures."""
from __future__ import annotations

import argparse
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import resource
import sqlite3
import time

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from research.authorization_history_v1 import history
from research.scientific_history_v1.receiver import POLICY, checker_identity
from research.scientific_history_v1.test_receiver import real_config, FIXTURES
from research.scientific_receiver_v1 import host
from . import audit


def run(out: Path) -> dict:
    manifest_path = Path(__file__).with_name("BENCHMARK_MANIFEST.json")
    manifest_bytes = manifest_path.read_bytes()
    manifest = json.loads(manifest_bytes)
    out.mkdir(parents=True, exist_ok=False)
    config = real_config()
    for path in (Path(__file__).resolve(), Path(audit.__file__).resolve(), manifest_path.resolve()):
        config = replace(config, pins=(*config.pins, host.Pin("source", str(path),
                                                             hashlib.sha256(path.read_bytes()).hexdigest())))
    authority, witness = Ed25519PrivateKey.generate(), Ed25519PrivateKey.generate()
    genesis = (FIXTURES / "zero-step.wire").read_bytes()
    candidate = (FIXTURES / "one-step.wire").read_bytes()
    root = history.Root(authority.public_key().public_bytes_raw(), witness.public_key().public_bytes_raw(),
                        POLICY, checker_identity(config), b"benchmark-genesis", genesis)
    store = history.History.create(out / "history.sqlite", root)
    anchors, wires = [history.initial(root)], []
    for index in range(32):
        raw = candidate if index % 2 == 0 else genesis
        payload = history.proposed_payload(root, anchors[-1], event_id=f"event-{index:02}".encode(),
                                           candidate=raw, certificate=b"")
        signed = history.Envelope(payload, authority.sign(payload.signing_bytes()),
                                  witness.sign(payload.signing_bytes())).encode()
        wires.append(signed)
        anchors.append(store.append(signed))
    (out / "root.json").write_bytes(root.encode())
    (out / "anchor.json").write_bytes(audit.canonical({
        "generation": anchors[-1].generation, "incumbent_hex": anchors[-1].incumbent.hex(),
        "tip_hex": anchors[-1].tip.hex(), "chain_digest_hex": anchors[-1].chain_digest.hex()}))
    (out / "material.json").write_bytes(audit.canonical({"envelope_hex": [w.hex() for w in wires]}))
    assert set(dict(config.environment)) == {"LEAN_PATH"}  # Never export credentials.
    (out / "operator-config.json").write_text(json.dumps({
        "command": config.command, "executable_sha256": config.executable_sha256,
        "pins": [vars(p) for p in config.pins], "cwd": config.cwd,
        "environment": dict(config.environment), "toolchain": config.toolchain,
        "timeout_seconds": config.timeout_seconds, "stdout_limit": config.stdout_limit,
        "stderr_limit": config.stderr_limit}, indent=2, sort_keys=True) + "\n")
    observations = []
    for count, expected in zip(manifest["cases"], manifest["expected_artifact_checks"]):
        started = time.monotonic()
        if count == 32:
            report = audit.audit_history(out / "history.sqlite", root, anchors[count], config)
        else:
            report = audit.audit_material(root, anchors[count], tuple(wires[:count]), config)
        elapsed = time.monotonic() - started
        assert len(report.artifacts) == expected and report.anchor == anchors[count]
        assert report.historically_authenticated_verification == "UNVERIFIED"
        result = report.as_dict()
        (out / f"cold-{count:02}.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
        observation = {"events": count, "artifacts_checked": len(report.artifacts),
                       "elapsed_seconds": elapsed,
                       "total_scientific_bytes": sum(len(x.raw) for x in report.artifacts),
                       "maximum_observed_child_peak_RSS_KiB": resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss,
                       "status": "EXECUTED_PASS"}
        observations.append(observation)
        print(json.dumps(observation), flush=True)
    started = time.monotonic()
    audit.authenticate_material(root, anchors[-1], tuple(wires), config)
    authentication_seconds = time.monotonic() - started
    bad_store = history.History.create(out / "invalid-old-history.sqlite", root)
    bad_anchor = history.initial(root)
    negative_wires = []
    for event_id, raw in ((b"bad-old", (FIXTURES / "wrong-environment.wire").read_bytes()),
                          (b"valid-current", candidate)):
        payload = history.proposed_payload(root, bad_anchor, event_id=event_id,
                                           candidate=raw, certificate=b"")
        signed = history.Envelope(payload, authority.sign(payload.signing_bytes()),
                                  witness.sign(payload.signing_bytes())).encode()
        negative_wires.append(signed)
        bad_anchor = bad_store.append(signed)
    before = audit.digest((out / "invalid-old-history.sqlite").read_bytes())
    try:
        audit.audit_history(out / "invalid-old-history.sqlite", root, bad_anchor, config)
        raise AssertionError("Invalid old scientific claim was accepted")
    except audit.AuditRejected as exc:
        negative = {"name": "invalid_old_science_valid_current", "status": "EXECUTED_PASS",
                    "observed": "rejected", "reason": str(exc),
                    "envelope_hex": [w.hex() for w in negative_wires],
                    "database_unchanged": audit.digest((out / "invalid-old-history.sqlite").read_bytes()) == before}
        assert negative["database_unchanged"]
    result = {"format": "pcs-full-history-cold-replay-experiment-v1",
              "manifest_sha256": hashlib.sha256(manifest_bytes).hexdigest(),
              "operator_config_identity": config.identity(),
              "operator_config_sha256": checker_identity(config).hex(),
              "root_sha256": audit.digest(root.encode()), "observations": observations,
              "authentication_only_replay_seconds": authentication_seconds,
              "negative_control": negative,
              "sqlite_version": sqlite3.sqlite_version,
              "incremental_authenticated_cache": "NOT_IMPLEMENTED",
              "no_positive_verifier_mocks": True,
              "historically_authenticated_verification": "UNVERIFIED",
              "scientific_acceptance": False, "production_authority": False,
              "memory_scope": "Linux RUSAGE_CHILDREN maximum child peak RSS observed so far, not simultaneous aggregate RSS",
              "performance_scope": "Single run at each size with no controlled machine isolation; no asymptotic or speedup claim",
              "pins_scope": "Partial fixture inventory; not full loader/dependency/root attestation"}
    (out / "benchmark.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    run(args.out)
