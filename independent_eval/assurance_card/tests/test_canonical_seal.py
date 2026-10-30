from __future__ import annotations

import json
from pathlib import Path

from python_harness.canonical import (
    CANONICALIZATION_ID,
    compute_card_integrity,
    seal_card,
    verify_card_integrity,
)
from python_harness.card import build_assurance_card


def test_seal_stable_under_fixed_timestamp(fixture_bundle: Path):
    stamp = "2026-10-17T21:00:00Z"
    a = build_assurance_card(
        fixture_bundle,
        skip_verify=True,
        generated_at_utc=stamp,
    )
    b = build_assurance_card(
        fixture_bundle,
        skip_verify=True,
        generated_at_utc=stamp,
    )
    assert a["card_integrity"]["digest_sha256"] == b["card_integrity"]["digest_sha256"]
    assert a["card_integrity"]["canonicalization"] == CANONICALIZATION_ID
    assert verify_card_integrity(a)["ok"] is True


def test_tamper_breaks_seal(fixture_bundle: Path):
    card = build_assurance_card(
        fixture_bundle,
        skip_verify=True,
        generated_at_utc="2026-10-17T21:00:00Z",
    )
    tampered = dict(card)
    tampered["disclaimer"] = "TAMPERED"
    # Keep old integrity block → recompute should mismatch.
    check = verify_card_integrity(tampered)
    assert check["checked"] is True
    assert check["ok"] is False


def test_reseal_after_change_updates_digest():
    base = {"format": "pcs-assurance-card-v1", "x": 1, "card_issues_accept": False}
    sealed = seal_card(base)
    first = sealed["card_integrity"]["digest_sha256"]
    sealed["x"] = 2
    resealed = seal_card(sealed)
    assert resealed["card_integrity"]["digest_sha256"] != first
    assert verify_card_integrity(resealed)["ok"] is True


def test_integrity_excludes_itself_from_payload():
    card = {"a": 1, "card_integrity": {"digest_sha256": "deadbeef"}}
    recomputed = compute_card_integrity(card)
    # Payload for seal must ignore prior integrity; digest of {"a":1} is stable.
    again = compute_card_integrity({"a": 1})
    assert recomputed["digest_sha256"] == again["digest_sha256"]
    assert json.dumps({"a": 1}, sort_keys=True)  # smoke
