"""Differential tests: production verifier vs. the Lean v0.6 checker (`acceptPCS`).

The Lean side (formal/tools/LeanVerifyDir.lean) verifies canonical bytes, hashes,
both Ed25519 signatures (Lean RFC 8032 implementation), the package namespace and
file map, Lean normalization of every claim and the normalized set.  It replays
`reaction_balance` evidence with the verified Lean executor (`PCS.V2.Chemistry`) and
reports recorded outcomes for every other check type, so this test cross-checks every
layer *except* the external (non-chemistry) replay and environment executors.

Skipped when `lake` is unavailable or the formal library has not been built
(`./scripts/verify_lean.sh`).
"""

from __future__ import annotations

import base64
import json
import shutil
import subprocess
from pathlib import Path

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from pcs.canonical_json import canonicalize_jcs_bytes
from pcs.verifier_io_v06 import CONTROL_FILES_V06
from pcs.verifier_v06 import verify_end_to_end_v06


ROOT = Path(__file__).resolve().parents[1]
FORMAL = ROOT / "formal"
GOLDEN = ROOT / "tests" / "v06_golden"
META = json.loads((GOLDEN / "metadata.json").read_text(encoding="utf-8"))
B64 = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/"
RFC8032_TEST1_PK = "d75a980182b10ab7d54bfed3c964073a0ee172f3daa62325af021a68f707511a"

pytestmark = pytest.mark.skipif(
    shutil.which("lake") is None
    or not (FORMAL / ".lake" / "build" / "lib" / "lean" / "PCS.olean").exists(),
    reason="Lean toolchain or built formal library unavailable",
)


def _copy_golden(dst: Path) -> Path:
    shutil.copytree(GOLDEN, dst)
    (dst / "metadata.json").unlink()
    return dst


def _python_verdict(pkg: Path, pk_b64: str) -> bool:
    files: dict[str, bytes] = {}
    for path in sorted(pkg.rglob("*")):
        if path.is_file():
            rel = path.relative_to(pkg).as_posix()
            if rel not in CONTROL_FILES_V06:
                files[rel] = path.read_bytes()
    try:
        public_key = Ed25519PublicKey.from_public_bytes(base64.b64decode(pk_b64))
        result = verify_end_to_end_v06(
            certificate_bytes=(pkg / "certificate.json").read_bytes(),
            certificate_signature_bytes=(pkg / "certificate_signature.json").read_bytes(),
            package_manifest_bytes=(pkg / "package_manifest.json").read_bytes(),
            package_signature_bytes=(pkg / "package_signature.json").read_bytes(),
            package_files=files,
            public_key=public_key,
        )
    except (OSError, ValueError, KeyError):
        return False
    return bool(result["valid"])


def _lean_verdict(pkg: Path, pk_b64: str) -> bool:
    out = subprocess.run(
        ["lake", "env", "lean", "--run", "tools/LeanVerifyDir.lean", str(pkg), pk_b64],
        cwd=FORMAL,
        capture_output=True,
        text=True,
        timeout=300,
        check=True,
    )
    verdict = out.stdout.strip()
    assert verdict in {"ACCEPT", "REJECT"}, out
    return verdict == "ACCEPT"


def _malleate(pkg: Path) -> None:
    path = pkg / "certificate_signature.json"
    record = json.loads(path.read_bytes())
    sig = record["signature"]
    record["signature"] = sig[:-3] + B64[B64.index(sig[-3]) ^ 1] + "=="
    path.write_bytes(canonicalize_jcs_bytes(record))


def _replace(pkg: Path, rel: str, old: bytes, new: bytes) -> None:
    path = pkg / rel
    raw = path.read_bytes()
    assert old in raw
    path.write_bytes(raw.replace(old, new, 1))


MUTATIONS = {
    "golden": lambda p: None,
    "noncanonical_base64_signature": _malleate,
    "manifest_trailing_newline": lambda p: (p / "package_manifest.json").write_bytes(
        (p / "package_manifest.json").read_bytes() + b"\n"
    ),
    "manifest_whitespace": lambda p: _replace(
        p, "package_manifest.json", b'{"canonical', b'{ "canonical'
    ),
    "extra_unsigned_member": lambda p: (p / "extra.txt").write_bytes(b"x"),
    "missing_signed_member": lambda p: (p / "artifacts" / "fixture.bin").unlink(),
    "artifact_substituted": lambda p: (p / "artifacts" / "fixture.bin").write_bytes(
        b"fixture artifacT\n"
    ),
    "case_alias_member": lambda p: (p / "Certificate.json").write_bytes(
        (p / "certificate.json").read_bytes()
    ),
    "wire_decision_tampered": lambda p: _replace(
        p,
        META["normalized_wire_path"],
        b'"decision":"COMPUTATIONALLY_SUPPORTED"',
        b'"decision":"OPEN"',
    ),
    "index_removed": lambda p: (p / "normalized" / "index.json").unlink(),
    "package_signature_is_certificate_signature": lambda p: shutil.copy(
        p / "certificate_signature.json", p / "package_signature.json"
    ),
    "certificate_statement_changed": lambda p: _replace(
        p, "certificate.json", b"atom-balanced", b"atom-balanced!"
    ),
    # Adversarial byte-level encodings (added with the archive/hash refinement).
    "certificate_duplicate_key": lambda p: _replace(
        p, "certificate.json", b'{"artifacts":[],', b'{"artifacts":[],"artifacts":[],'
    ),
    "certificate_integer_as_float": lambda p: _replace(
        p, "certificate.json", b'"coefficient":2', b'"coefficient":2.0'
    ),
    "manifest_uppercase_hex": lambda p: _replace(
        p, "package_manifest.json", b"0e9ac5af", b"0E9AC5AF"
    ),
    "index_uppercase_hex": lambda p: _replace(
        p, "normalized/index.json", b"0e9ac5af", b"0E9AC5AF"
    ),
    "wire_whitespace": lambda p: _replace(p, META["normalized_wire_path"], b'{"', b'{ "'),
    "artifact_truncated": lambda p: (p / "artifacts" / "fixture.bin").write_bytes(b""),
}


@pytest.mark.parametrize("name", sorted(MUTATIONS))
def test_lean_checker_agrees_with_production(tmp_path: Path, name: str) -> None:
    pkg = _copy_golden(tmp_path / "pkg")
    MUTATIONS[name](pkg)
    pk = META["public_key_raw_base64"]
    python_ok = _python_verdict(pkg, pk)
    lean_ok = _lean_verdict(pkg, pk)
    assert python_ok == lean_ok
    assert python_ok == (name == "golden")


def test_wrong_trust_anchor_rejected_by_both(tmp_path: Path) -> None:
    pkg = _copy_golden(tmp_path / "pkg")
    other = base64.b64encode(bytes.fromhex(RFC8032_TEST1_PK)).decode("ascii")
    assert _python_verdict(pkg, other) is False
    assert _lean_verdict(pkg, other) is False
