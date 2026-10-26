"""Source-bound capture publication shared by batch and process entry points."""
from __future__ import annotations

from pathlib import Path

from .certificate import encode, evaluate, sha
from .trace import certify_path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
IMPLEMENTATION = (
    "Progress.lean", "Wire.lean", "Codec.lean", "Main.lean", "authority.py",
    "broker.py", "certificate.py", "example.py", "trace.py", "__main__.py",
    "evidence.py", "worker.py",
)


def sources():
    return {
        **{name: sha((HERE / name).read_bytes()) for name in IMPLEMENTATION},
        "formal/PCSActionShield.lean": sha((ROOT / "formal/PCSActionShield.lean").read_bytes()),
    }


def read(path, limit=2 * 1024 * 1024):
    with Path(path).open("rb") as stream:
        raw = stream.read(limit + 1)
    if len(raw) > limit:
        raise ValueError("input exceeds byte limit")
    return raw


def write(path, value):
    with Path(path).open("xb") as stream:
        stream.write(encode(value) + b"\n")


def publish(out, broker, samples, before, *, pre_sanitized, replayed):
    """Publish only after actual native/SQL completion and fresh kernel checks.

    A duplicate request is an idempotent observation, not an additional edge in
    the path. Replay still compares every observation to its original receipt.
    """
    final = broker.snapshot()
    if final["state"] != 4 or final["transitions"] > 4:
        raise ValueError("workflow failed its certified bound")
    records = {}
    for sample in samples:
        record = sample["record"]
        if "action" in record:
            generation = record["generation"]
            if generation in records and records[generation] != record:
                raise ValueError("conflicting observations of one committed transition")
            records[generation] = record
    path = [records[g] for g in sorted(records)]
    pairs = [(bytes.fromhex(r["request_hex"]), bytes.fromhex(r["reply_hex"])) for r in path]
    wire = broker._authority.certify(pairs, "workflow-wire")
    path_proof = certify_path(broker._authority, path)
    if sources() != before:
        raise ValueError("implementation changed during capture/replay")
    artifact = dict(
        format="pcs-progress-supervisor-capture-v1",
        data_origin="synthetic fixed-tool experiment; no participant data",
        sources=before, model_hex=broker.model_raw.hex(),
        certificate_hex=broker.cert_raw.hex(), pre_sanitized=pre_sanitized,
        samples=samples, final=final,
    )
    result = dict(
        format="pcs-progress-supervisor-result-v1",
        analysis=evaluate(broker.model_raw, broker.cert_raw),
        native_build=broker._authority.manifest, captured_wire_proof=wire,
        captured_path_proof=path_proof, final=final, replayed=replayed,
        pcs_authority=False, implementation_correspondence="TESTED_NOT_PROVED",
        deployment_safety="OPEN", empirical_model_safety="NOT_ESTABLISHED",
    )
    # Both are fresh outputs. They are inspectable evidence, not restart anchors.
    write(Path(out) / "capture.json", artifact)
    write(Path(out) / "result.json", result)
    return result
