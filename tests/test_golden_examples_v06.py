from __future__ import annotations

from scripts.run_golden_examples_v06 import build_golden_examples


def test_three_golden_examples_are_valid_and_preserve_positive_negative_semantics(tmp_path):
    report = build_golden_examples(tmp_path / "run")
    cases = {case["name"]: case for case in report["cases"]}
    assert set(cases) == {"pkpd-supported", "pkpd-falsified", "environment-bound"}
    assert cases["pkpd-supported"]["valid"] is True
    assert cases["pkpd-supported"]["claims"]["C_PKPD_REPLAY"] == "COMPUTATIONALLY_SUPPORTED"
    assert cases["pkpd-falsified"]["valid"] is True
    assert cases["pkpd-falsified"]["claims"]["C_PKPD_REPLAY"] == "FALSIFIED_OR_CHECK_FAILED"
    assert cases["environment-bound"]["valid"] is True


def test_golden_examples_are_byte_deterministic(tmp_path):
    first = build_golden_examples(tmp_path / "first")
    second = build_golden_examples(tmp_path / "second")
    hashes1 = {c["name"]: c["bundle_sha256"] for c in first["cases"]}
    hashes2 = {c["name"]: c["bundle_sha256"] for c in second["cases"]}
    assert hashes1 == hashes2
