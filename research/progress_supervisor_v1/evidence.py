"""Source-bound capture publication shared by batch and process entry points."""
from __future__ import annotations

from pathlib import Path

from .certificate import encode, evaluate, sha
from .trace import certify_path
from .binding import source_inventory

SYNTHETIC_ORIGIN = "synthetic fixed-tool experiment; no participant data"
EXTERNAL_ORIGIN = "external proposal bytes; provenance/consent unverified; synthetic fixed tools"
ORIGINS = (SYNTHETIC_ORIGIN, EXTERNAL_ORIGIN)


def sources():
    return source_inventory()


def read(path, limit=2 * 1024 * 1024):
    with Path(path).open("rb") as stream:
        raw = stream.read(limit + 1)
    if len(raw) > limit:
        raise ValueError("input exceeds byte limit")
    return raw


def write(path, value):
    with Path(path).open("xb") as stream:
        stream.write(encode(value) + b"\n")


def publish(out, broker, samples, before, *, pre_sanitized, replayed, data_origin=SYNTHETIC_ORIGIN):
    """Publish only after actual native/SQL completion and fresh kernel checks.

    A duplicate request is an idempotent observation, not an additional edge in
    the path. Replay still compares every observation to its original receipt.
    """
    if data_origin not in ORIGINS:
        raise ValueError("unsupported proposal provenance annotation")
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
    proof_dir = Path(out) / "proofs"
    wire = broker._authority.certify(pairs, "workflow-wire", proof_dir=proof_dir)
    path_proof = certify_path(broker._authority, path, proof_dir=proof_dir)
    if sources() != before:
        raise ValueError("implementation changed during capture/replay")
    artifact = dict(
        format="pcs-progress-supervisor-capture-v1",
        data_origin=data_origin,
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
        proposal_data_eligibility="NOT_EVALUATED_DO_NOT_TRAIN_WITHOUT_REVIEW",
    )
    # Both are fresh outputs. They are inspectable evidence, not restart anchors.
    write(Path(out) / "capture.json", artifact)
    write(Path(out) / "result.json", result)
    return result
