"""Adversarial rejection tests for the independent checker."""

from __future__ import annotations

import json

import pytest

from pcs_epistemic.checker import CheckerError, verify_certificate
from pcs_epistemic.lattice import EvidenceClass, le, meet


def _assures(level: str, evidence_class: str, accepted: bool = True) -> bytes:
    cert = {
        "format": "pcs-epistemic-certificate-v1",
        "kind": "assures",
        "level": level,
        "claim": {
            "id": "c",
            "required_class": level,
            "required_evidence": ["e"],
        },
        "evidence": [{"id": "e", "class": evidence_class, "accepted": accepted}],
    }
    return json.dumps(cert).encode()


@pytest.mark.parametrize(
    "evidence_class",
    ["computational", "empirical", "provenance"],
)
def test_rejects_illicit_promotion_to_formal(evidence_class: str):
    receipt = verify_certificate(_assures("formal", evidence_class))
    assert receipt["accepted"] is False


def test_rejects_rejected_formal_evidence():
    receipt = verify_certificate(_assures("formal", "formal", accepted=False))
    assert receipt["accepted"] is False


def test_rejects_unknown_format():
    with pytest.raises(CheckerError):
        verify_certificate(b'{"format":"nope","kind":"assures"}')


def test_rejects_unknown_kind():
    with pytest.raises(CheckerError):
        verify_certificate(
            b'{"format":"pcs-epistemic-certificate-v1","kind":"forge_authority"}'
        )


def test_rejects_oversize_payload():
    with pytest.raises(CheckerError):
        verify_certificate(b"{" + b"x" * (2 * 1024 * 1024) + b"}")


def test_rejects_invalid_json():
    with pytest.raises(CheckerError):
        verify_certificate(b"{not-json")


def test_single_byte_mutations_do_not_false_accept(tmp_path):
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    raw = (root / "examples" / "pk_dialectic" / "dialectic_certificate.json").read_bytes()
    assert verify_certificate(raw)["accepted"] is True
    # Mutate many positions; none may yield accepted=true with altered meaning
    # without also being invalid JSON / schema. Count strict failures.
    rejections = 0
    false_accepts = 0
    for i in range(0, len(raw), max(1, len(raw) // 64)):
        mutant = bytearray(raw)
        mutant[i] ^= 0x20
        try:
            receipt = verify_certificate(bytes(mutant))
            if receipt.get("accepted"):
                # Only acceptable if bytes somehow still parse to same semantic
                # expectations; track as false accept if expected cores changed.
                detail = receipt.get("detail", {})
                if detail.get("agreement_core") != ["mass_conserved", "cmax_bound"]:
                    false_accepts += 1
            else:
                rejections += 1
        except (CheckerError, ValueError, KeyError, TypeError):
            rejections += 1
    assert false_accepts == 0
    assert rejections > 0


def test_lattice_exhaustive_non_promotion_matrix():
    classes = list(EvidenceClass)
    for src in classes:
        for dst in classes:
            if src == EvidenceClass.COMPUTATIONAL and dst == EvidenceClass.FORMAL:
                assert le(src, dst) is False
            if src == EvidenceClass.PROVENANCE and dst != EvidenceClass.PROVENANCE:
                assert le(src, dst) is False
            if src == EvidenceClass.EMPIRICAL and dst == EvidenceClass.FORMAL:
                assert le(src, dst) is False


def test_meet_collapse_is_not_silent_promotion():
    assert meet(EvidenceClass.FORMAL, EvidenceClass.EMPIRICAL) == EvidenceClass.PROVENANCE
    assert le(EvidenceClass.PROVENANCE, EvidenceClass.FORMAL) is False
