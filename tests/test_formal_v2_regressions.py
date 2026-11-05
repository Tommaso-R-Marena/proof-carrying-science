"""Regression tests for defects exposed while refining PCS v0.6/v2 into Lean.

See formal/PCS_FULL_FORMALIZATION_REPORT.md, section F (counterexamples found).
"""

from __future__ import annotations

import base64
import json
from pathlib import Path

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from pcs.byte_contract_v06 import (
    parse_certificate_bytes_v06,
    verify_package_file_map_v06,
    verify_signed_certificate_bytes_v06,
)
from pcs.canonical_json import (
    MAX_SAFE_INTEGER,
    canonicalize_jcs_bytes,
    parse_jcs_json,
)
from pcs.signing_v06 import V06SignatureError, decode_canonical_signature_b64
from pcs.verifier_v06 import verify_end_to_end_v06


ROOT = Path(__file__).resolve().parents[1]
GOLDEN = ROOT / "tests" / "v06_golden"
META = json.loads((GOLDEN / "metadata.json").read_text(encoding="utf-8"))
B64 = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/"


def _raw(rel: str) -> bytes:
    return (GOLDEN / rel).read_bytes()


def _public_key() -> Ed25519PublicKey:
    return Ed25519PublicKey.from_public_bytes(
        base64.b64decode(META["public_key_raw_base64"], validate=True)
    )


def _files() -> dict[str, bytes]:
    return {
        "certificate.json": _raw("certificate.json"),
        "artifacts/fixture.bin": _raw("artifacts/fixture.bin"),
        META["normalized_wire_path"]: _raw(META["normalized_wire_path"]),
        "normalized/index.json": _raw("normalized/index.json"),
    }


def _malleate_signature_record(raw: bytes) -> bytes:
    """Flip an unused low bit of the last base64 data symbol."""
    record = json.loads(raw)
    sig = record["signature"]
    assert sig.endswith("==")
    alt = B64[B64.index(sig[-3]) ^ 1]
    record["signature"] = sig[:-3] + alt + "=="
    assert base64.b64decode(record["signature"]) == base64.b64decode(sig)
    out = canonicalize_jcs_bytes(record)
    assert out != raw
    return out


def _e2e(**overrides):
    args = dict(
        certificate_bytes=_raw("certificate.json"),
        certificate_signature_bytes=_raw("certificate_signature.json"),
        package_manifest_bytes=_raw("package_manifest.json"),
        package_signature_bytes=_raw("package_signature.json"),
        package_files=_files(),
        public_key=_public_key(),
        expected_fingerprint=META["public_key_fingerprint"],
    )
    args.update(overrides)
    return verify_end_to_end_v06(**args)


# --- Counterexample 1: integers were parsed as binary64 floats -------------------


def test_safe_integers_parse_as_int_and_keep_canonical_bytes():
    value = parse_jcs_json('{"a":2,"b":-7,"c":9007199254740992}')
    assert value == {"a": 2, "b": -7, "c": MAX_SAFE_INTEGER}
    assert all(type(v) is int for v in value.values())
    assert canonicalize_jcs_bytes(value) == b'{"a":2,"b":-7,"c":9007199254740992}'


def test_unsafe_integer_keeps_binary64_interpretation_and_noncanonical_spelling_fails():
    value = parse_jcs_json("9007199254740993")
    assert isinstance(value, float)
    assert canonicalize_jcs_bytes(value) == b"9007199254740992"


def test_golden_certificate_integers_reach_replay_as_integers():
    certificate = parse_certificate_bytes_v06(_raw("certificate.json"))
    spec = certificate["evidence"][0]["check_spec"]
    coefficients = [entry["coefficient"] for entry in spec["reactants"] + spec["products"]]
    assert coefficients == [2, 1, 2]
    assert all(type(c) is int for c in coefficients)


def test_golden_package_is_accepted_end_to_end():
    result = _e2e()
    assert result["valid"], result["errors"]


# --- Counterexample 2: base64 signature spelling was malleable -------------------


def test_noncanonical_base64_signature_is_rejected_by_decoder():
    sig = json.loads(_raw("certificate_signature.json"))["signature"]
    assert decode_canonical_signature_b64(sig) == base64.b64decode(sig)
    alt = sig[:-3] + B64[B64.index(sig[-3]) ^ 1] + "=="
    try:
        decode_canonical_signature_b64(alt)
    except V06SignatureError:
        pass
    else:  # pragma: no cover - regression guard
        raise AssertionError("non-canonical base64 signature accepted")


def test_malleated_certificate_signature_record_is_rejected():
    mutated = _malleate_signature_record(_raw("certificate_signature.json"))
    result = verify_signed_certificate_bytes_v06(
        _raw("certificate.json"),
        mutated,
        _public_key(),
        expected_fingerprint=META["public_key_fingerprint"],
    )
    assert not result["valid"]
    assert any("non-canonical base64" in err for err in result["errors"])
    e2e = _e2e(certificate_signature_bytes=mutated)
    assert not e2e["valid"]
    assert e2e["failed_stage"] == "certificate_signature"


def test_malleated_package_signature_record_is_rejected():
    mutated = _malleate_signature_record(_raw("package_signature.json"))
    result = verify_package_file_map_v06(
        _raw("package_manifest.json"),
        _raw("certificate.json"),
        mutated,
        _files(),
        _public_key(),
        expected_fingerprint=META["public_key_fingerprint"],
    )
    assert not result["valid"]
    e2e = _e2e(package_signature_bytes=mutated)
    assert not e2e["valid"]
    assert e2e["failed_stage"] == "package_binding"


# --- Counterexample 3: Unicode decimal digits in molecular formulas ---------------


def _water_evidence(h_formula: str) -> dict:
    certificate = parse_certificate_bytes_v06(_raw("certificate.json"))
    evidence = json.loads(json.dumps(certificate["evidence"][0]))
    for key in ("check_spec", "predicate"):
        evidence[key]["reactants"][0]["formula"] = h_formula
    return evidence


def test_unicode_digit_formula_is_rejected_by_parser():
    from pcs.checks.chemistry import parse_formula

    assert dict(parse_formula("H2O")) == {"H": 2, "O": 1}
    try:
        parse_formula("H\u0662O")  # ARABIC-INDIC DIGIT TWO
    except ValueError:
        pass
    else:  # pragma: no cover - regression guard
        raise AssertionError("non-ASCII digit accepted in molecular formula")


def test_unicode_digit_formula_is_schema_valid_but_fails_replay():
    from pcs.replay_v06 import replay_evidence_item_v06
    from pcs.schema_validation import validate_v06_certificate_shape

    certificate = parse_certificate_bytes_v06(_raw("certificate.json"))
    certificate["evidence"][0] = _water_evidence("H\u0662")
    validate_v06_certificate_shape(certificate)  # reaches replay: schema does not stop it
    assert replay_evidence_item_v06(_water_evidence("H2"), {})["outcome"] == "PASS"
    assert replay_evidence_item_v06(_water_evidence("H\u0662"), {})["outcome"] == "FAIL"


# --- Counterexample 4: boolean reaction coefficients --------------------------------


def test_boolean_coefficient_is_not_one():
    from pcs.checks.chemistry import reaction_balanced

    reactants = [{"formula": "H2", "coefficient": 2}, {"formula": "O2", "coefficient": True}]
    products = [{"formula": "H2O", "coefficient": 2}]
    try:
        reaction_balanced(reactants, products)
    except ValueError:
        pass
    else:  # pragma: no cover - regression guard
        raise AssertionError("boolean coefficient accepted as an integer")
