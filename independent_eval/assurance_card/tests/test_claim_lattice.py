from __future__ import annotations

from python_harness.claim_lattice import (
    INSPECTION_CLASSES,
    classify_claim,
    summarize_classes,
)


def test_inspection_classes_match_product_lattice():
    assert INSPECTION_CLASSES == (
        "cryptographic_validity",
        "computationally_supported",
        "scientific_adequacy_open",
        "rejected_or_failed",
        "unknown_or_ambiguous",
    )


def test_classify_computationally_supported():
    assert (
        classify_claim(reported_status="COMPUTATIONALLY_SUPPORTED", kind="computational")
        == "computationally_supported"
    )


def test_classify_cryptographic_validity():
    assert (
        classify_claim(reported_status="SIGNATURE_OK", kind="integrity")
        == "cryptographic_validity"
    )
    assert (
        classify_claim(reported_status="CRYPTOGRAPHIC_VALID", kind="cryptographic")
        == "cryptographic_validity"
    )


def test_classify_scientific_adequacy_open():
    assert classify_claim(reported_status="OPEN", kind="scientific") == "scientific_adequacy_open"
    # Computational labels do not establish scientific adequacy.
    assert (
        classify_claim(reported_status="COMPUTATIONALLY_SUPPORTED", kind="scientific")
        == "scientific_adequacy_open"
    )


def test_classify_rejected_or_failed():
    assert classify_claim(reported_status="REJECTED", kind="computational") == "rejected_or_failed"
    assert (
        classify_claim(reported_status="HASH_MISMATCH", kind="computational")
        == "rejected_or_failed"
    )


def test_classify_unknown_or_ambiguous():
    assert classify_claim(reported_status="UNREPORTED", kind="computational") == "unknown_or_ambiguous"
    assert classify_claim(reported_status=None, kind=None) == "unknown_or_ambiguous"


def test_summarize_classes_counts():
    summary = summarize_classes(
        ["computationally_supported", "scientific_adequacy_open", "computationally_supported"]
    )
    assert summary["computationally_supported"] == 2
    assert summary["scientific_adequacy_open"] == 1
    assert summary["rejected_or_failed"] == 0
    assert set(summary) == set(INSPECTION_CLASSES)
