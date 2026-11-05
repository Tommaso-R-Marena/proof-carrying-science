"""Generate ≥150 deterministic adversarial signed-bundle cases and actually verify them."""

from __future__ import annotations

import base64
import hashlib
import json
import shutil
import zipfile
from pathlib import Path
from typing import Any, Callable

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from .paths import FIXTURES, RESULTS, resolve_lean_authority


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _demo_keys(directory: Path) -> tuple[Path, Path, str, Ed25519PrivateKey]:
    directory.mkdir(parents=True, exist_ok=True)
    seed = hashlib.sha256(b"pcs-independent-eval-adversarial-corpus-v1").digest()
    private = Ed25519PrivateKey.from_private_bytes(seed)
    public = private.public_key()
    priv = directory / "private.pem"
    pub = directory / "public.pem"
    priv.write_bytes(
        private.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        )
    )
    pub.write_bytes(
        public.public_bytes(
            serialization.Encoding.PEM,
            serialization.PublicFormat.SubjectPublicKeyInfo,
        )
    )
    from pcs.signing import public_key_fingerprint

    return priv, pub, public_key_fingerprint(public), private


def _build_positive_bundle(work: Path) -> dict[str, Any]:
    """Build one positive-control v0.6 ZIP via PCS attest-v06 on synthetic PK/PD."""
    from pcs.attest_v06 import attest_v06
    from pcs.discover_v06 import (
        confirm_manifest_draft_v06,
        discover_project_v06,
        write_discovery_outputs_v06,
    )
    from .paths import REPO_ROOT

    lab = work / "lab"
    lab.mkdir(parents=True, exist_ok=True)
    src = REPO_ROOT / "examples" / "pkpd_one_compartment"
    for name in ("pk_model.json", "predictions.csv", "pilot_intake.json"):
        shutil.copyfile(src / name, lab / name)
    discovered = discover_project_v06(lab)
    draft = lab / "draft.json"
    write_discovery_outputs_v06(
        discovered,
        manifest_output=draft,
        report_output=lab / "discovery.json",
        overwrite=True,
    )
    manifest = lab / "manifest.json"
    confirm_manifest_draft_v06(draft, manifest, project_root=lab, overwrite=True)
    priv, pub, fingerprint, _ = _demo_keys(work / "keys")
    authority = resolve_lean_authority()
    bundle = work / "positive.pcs.zip"
    result = attest_v06(
        manifest,
        bundle,
        priv,
        pub,
        expected_fingerprint=fingerprint,
        overwrite=True,
        lean_authority_path=authority,
    )
    return {
        "bundle": bundle,
        "public_key": pub,
        "private_key": priv,
        "fingerprint": fingerprint,
        "attestation": result,
        "private": Ed25519PrivateKey.from_private_bytes(
            hashlib.sha256(b"pcs-independent-eval-adversarial-corpus-v1").digest()
        ),
    }


def _rewrite_zip(src: Path, dst: Path, mutator: Callable[[str, bytes], tuple[str, bytes]]) -> None:
    with zipfile.ZipFile(src, "r") as zin, zipfile.ZipFile(dst, "w", compression=zipfile.ZIP_STORED) as zout:
        for info in zin.infolist():
            raw = zin.read(info.filename)
            name, data = mutator(info.filename, raw)
            out = zipfile.ZipInfo(name, (1980, 1, 1, 0, 0, 0))
            out.create_system = 3
            out.external_attr = 0o100644 << 16
            out.compress_type = zipfile.ZIP_STORED
            zout.writestr(out, data)


def _mutate_json_member(
    src: Path,
    dst: Path,
    member: str,
    mutator: Callable[[dict[str, Any]], dict[str, Any] | bytes],
) -> None:
    def _inner(name: str, raw: bytes) -> tuple[str, bytes]:
        if name != member:
            return name, raw
        obj = json.loads(raw.decode("utf-8"))
        updated = mutator(obj)
        if isinstance(updated, bytes):
            return name, updated
        return name, (json.dumps(updated, separators=(",", ":"), ensure_ascii=False) + "\n").encode("utf-8")

    _rewrite_zip(src, dst, _inner)


def _flip_signature_bit(src: Path, dst: Path, member: str, bit_index: int) -> None:
    def _mut(obj: dict[str, Any]) -> dict[str, Any]:
        sig_b64 = obj["signature"]
        raw = bytearray(base64.b64decode(sig_b64, validate=True))
        byte_i = (bit_index // 8) % len(raw)
        bit_i = bit_index % 8
        raw[byte_i] ^= 1 << bit_i
        obj = dict(obj)
        obj["signature"] = base64.b64encode(bytes(raw)).decode("ascii")
        return obj

    _mutate_json_member(src, dst, member, _mut)


def _truncate_signature(src: Path, dst: Path, member: str, keep_chars: int) -> None:
    def _mut(obj: dict[str, Any]) -> dict[str, Any]:
        obj = dict(obj)
        sig = obj.get("signature", "")
        obj["signature"] = sig[:keep_chars] if isinstance(sig, str) else ""
        return obj

    _mutate_json_member(src, dst, member, _mut)


def _swap_fingerprint_in_signature(src: Path, dst: Path, member: str, fake_fp: str) -> None:
    def _mut(obj: dict[str, Any]) -> dict[str, Any]:
        obj = dict(obj)
        obj["public_key_fingerprint"] = fake_fp
        return obj

    _mutate_json_member(src, dst, member, _mut)


def _rename_member(src: Path, dst: Path, old: str, new: str) -> None:
    def _mut(name: str, raw: bytes) -> tuple[str, bytes]:
        return (new if name == old else name), raw

    _rewrite_zip(src, dst, _mut)


def _duplicate_critical_conflict(src: Path, dst: Path, member: str, alt: bytes) -> None:
    with zipfile.ZipFile(src, "r") as zin, zipfile.ZipFile(dst, "w", compression=zipfile.ZIP_STORED) as zout:
        for info in zin.infolist():
            out = zipfile.ZipInfo(info.filename, (1980, 1, 1, 0, 0, 0))
            out.create_system = 3
            out.external_attr = 0o100644 << 16
            out.compress_type = zipfile.ZIP_STORED
            zout.writestr(out, zin.read(info.filename))
        dup = zipfile.ZipInfo(member, (1980, 1, 1, 0, 0, 0))
        dup.create_system = 3
        dup.external_attr = 0o100644 << 16
        dup.compress_type = zipfile.ZIP_STORED
        zout.writestr(dup, alt)


def _verify(bundle: Path, public_key: Path, fingerprint: str) -> dict[str, Any]:
    from pcs.lean_authority_v06 import V06LeanAuthorityError
    from pcs.verifier_zip_v06 import V06BundleVerificationError, verify_package_zip_end_to_end_v06

    authority = resolve_lean_authority()
    try:
        result = verify_package_zip_end_to_end_v06(
            bundle,
            public_key,
            expected_fingerprint=fingerprint,
            lean_authority_path=authority,
            require_canonical_archive=True,
        )
        return {
            "attempted": True,
            "valid": result.get("valid") is True,
            "authoritative": result.get("authoritative") is True,
            "failed_stage": result.get("failed_stage"),
            "errors": result.get("errors") or [],
            "exception": None,
        }
    except (V06BundleVerificationError, V06LeanAuthorityError, ValueError, OSError) as exc:
        return {
            "attempted": True,
            "valid": False,
            "authoritative": False,
            "failed_stage": "exception",
            "errors": [str(exc)],
            "exception": type(exc).__name__,
        }


def generate_corpus(output_dir: Path | None = None) -> dict[str, Any]:
    root = output_dir or (FIXTURES / "adversarial" / "corpus")
    if root.exists():
        shutil.rmtree(root)
    root.mkdir(parents=True, exist_ok=False)
    work = root / "_seed"
    positive = _build_positive_bundle(work)
    cases: list[dict[str, Any]] = []

    # Positive controls (10)
    for i in range(10):
        dst = root / f"positive_{i:03d}.pcs.zip"
        shutil.copyfile(positive["bundle"], dst)
        outcome = _verify(dst, positive["public_key"], positive["fingerprint"])
        cases.append(
            {
                "id": f"positive_{i:03d}",
                "class": "positive",
                "attack": "none",
                "expected_reject": False,
                "bundle_sha256": _sha256(dst.read_bytes()),
                "verification": outcome,
            }
        )

    # Payload / certificate / signature / archive attacks
    attack_builders: list[tuple[str, Callable[[Path], None]]] = []

    def add(name: str, builder: Callable[[Path], None]) -> None:
        attack_builders.append((name, builder))

    add(
        "payload_tamper",
        lambda dst: _rewrite_zip(
            positive["bundle"],
            dst,
            lambda n, r: (n, b"tampered," + r if n.endswith("/payload") else r),
        ),
    )
    add(
        "certificate_empty",
        lambda dst: _rewrite_zip(
            positive["bundle"],
            dst,
            lambda n, r: (n, b"{}" if n == "certificate.json" else r),
        ),
    )
    add(
        "certificate_empty_bytes",
        lambda dst: _rewrite_zip(
            positive["bundle"],
            dst,
            lambda n, r: (n, b"" if n == "certificate.json" else r),
        ),
    )
    add(
        "certificate_truncated",
        lambda dst: _rewrite_zip(
            positive["bundle"],
            dst,
            lambda n, r: (n, r[: max(1, len(r) // 3)] if n == "certificate.json" else r),
        ),
    )
    add(
        "package_manifest_zero",
        lambda dst: _rewrite_zip(
            positive["bundle"],
            dst,
            lambda n, r: (n, b"{}" if n == "package_manifest.json" else r),
        ),
    )
    add(
        "package_manifest_empty_bytes",
        lambda dst: _rewrite_zip(
            positive["bundle"],
            dst,
            lambda n, r: (n, b"" if n == "package_manifest.json" else r),
        ),
    )
    add(
        "package_signature_flip",
        lambda dst: _rewrite_zip(
            positive["bundle"],
            dst,
            lambda n, r: (n, bytes(b ^ 0xFF for b in r) if n == "package_signature.json" else r),
        ),
    )
    add(
        "certificate_signature_flip",
        lambda dst: _rewrite_zip(
            positive["bundle"],
            dst,
            lambda n, r: (
                n,
                bytes(b ^ 0x01 for b in r) if n == "certificate_signature.json" else r,
            ),
        ),
    )
    add(
        "package_signature_empty_bytes",
        lambda dst: _rewrite_zip(
            positive["bundle"],
            dst,
            lambda n, r: (n, b"" if n == "package_signature.json" else r),
        ),
    )
    add(
        "certificate_signature_empty_bytes",
        lambda dst: _rewrite_zip(
            positive["bundle"],
            dst,
            lambda n, r: (n, b"" if n == "certificate_signature.json" else r),
        ),
    )
    # Empty normalized index (closest in-archive analogue to an empty authority transcript input)
    add(
        "normalized_index_empty",
        lambda dst: _rewrite_zip(
            positive["bundle"],
            dst,
            lambda n, r: (n, b"" if n == "normalized/index.json" else r),
        ),
    )
    add(
        "normalized_index_empty_object",
        lambda dst: _rewrite_zip(
            positive["bundle"],
            dst,
            lambda n, r: (n, b"{}" if n == "normalized/index.json" else r),
        ),
    )

    def drop_member(member: str) -> Callable[[Path], None]:
        def _b(dst: Path) -> None:
            with zipfile.ZipFile(positive["bundle"], "r") as zin, zipfile.ZipFile(
                dst, "w", compression=zipfile.ZIP_STORED
            ) as zout:
                for info in zin.infolist():
                    if info.filename == member:
                        continue
                    out = zipfile.ZipInfo(info.filename, (1980, 1, 1, 0, 0, 0))
                    out.create_system = 3
                    out.external_attr = 0o100644 << 16
                    out.compress_type = zipfile.ZIP_STORED
                    zout.writestr(out, zin.read(info.filename))

        return _b

    for member in (
        "certificate.json",
        "certificate_signature.json",
        "package_manifest.json",
        "package_signature.json",
    ):
        add(f"missing_{member.replace('.', '_')}", drop_member(member))

    add(
        "path_traversal_member",
        lambda dst: _inject_member(positive["bundle"], dst, "../escape.txt", b"escaped"),
    )
    add(
        "absolute_member",
        lambda dst: _inject_member(positive["bundle"], dst, "/tmp/evil.bin", b"abs"),
    )
    add(
        "duplicate_payload_name",
        lambda dst: _duplicate_first_payload(positive["bundle"], dst),
    )
    add(
        "appended_garbage",
        lambda dst: dst.write_bytes(positive["bundle"].read_bytes() + b"GARBAGE"),
    )
    add(
        "truncated_zip",
        lambda dst: dst.write_bytes(positive["bundle"].read_bytes()[:64]),
    )
    add(
        "empty_file",
        lambda dst: dst.write_bytes(b""),
    )
    add(
        "not_a_zip",
        lambda dst: dst.write_bytes(b"PK\x03\x04not-really"),
    )

    # Truncated / bit-flipped signature fields (inside signature records)
    add(
        "signature_truncated_package",
        lambda dst: _truncate_signature(positive["bundle"], dst, "package_signature.json", 20),
    )
    add(
        "signature_truncated_certificate",
        lambda dst: _truncate_signature(positive["bundle"], dst, "certificate_signature.json", 20),
    )
    for idx in range(8):
        add(
            f"signature_bit_flip_package_{idx:02d}",
            lambda dst, i=idx: _flip_signature_bit(
                positive["bundle"], dst, "package_signature.json", i * 7 + 3
            ),
        )
    for idx in range(8):
        add(
            f"signature_bit_flip_certificate_{idx:02d}",
            lambda dst, i=idx: _flip_signature_bit(
                positive["bundle"], dst, "certificate_signature.json", i * 11 + 5
            ),
        )

    # Swapped public key fingerprint vs signer (record claims a different key)
    attacker_fp = hashlib.sha256(b"pcs-independent-eval-attacker-fingerprint-v1").hexdigest()
    add(
        "swapped_fingerprint_package_sig",
        lambda dst: _swap_fingerprint_in_signature(
            positive["bundle"], dst, "package_signature.json", attacker_fp
        ),
    )
    add(
        "swapped_fingerprint_certificate_sig",
        lambda dst: _swap_fingerprint_in_signature(
            positive["bundle"], dst, "certificate_signature.json", attacker_fp
        ),
    )

    # Member rename that breaks lock / inventory
    for old, new in (
        ("certificate.json", "certificate.json.bak"),
        ("package_manifest.json", "package_manifest.json.renamed"),
        ("package_signature.json", "sigs/package_signature.json"),
        ("certificate_signature.json", "certificate_signature.txt"),
        ("normalized/index.json", "normalized/index.json.moved"),
    ):
        safe = old.replace("/", "_").replace(".", "_")
        add(
            f"rename_breaks_lock_{safe}",
            lambda dst, o=old, n=new: _rename_member(positive["bundle"], dst, o, n),
        )

    # Duplicated critical member with conflicting bytes
    for member, alt in (
        ("certificate.json", b'{"spec_version":"evil"}\n'),
        ("package_manifest.json", b'{"package_format":"evil"}\n'),
        ("package_signature.json", b'{"signature":"AAAA"}\n'),
        ("certificate_signature.json", b'{"signature":"BBBB"}\n'),
        ("normalized/index.json", b"[]\n"),
    ):
        safe = member.replace("/", "_").replace(".", "_")
        add(
            f"duplicate_conflict_{safe}",
            lambda dst, m=member, a=alt: _duplicate_critical_conflict(positive["bundle"], dst, m, a),
        )

    # Wrong-key verification cases (still attempt verify)
    attacker = Ed25519PrivateKey.generate()
    attacker_pub = work / "attacker.pem"
    attacker_pub.write_bytes(
        attacker.public_key().public_bytes(
            serialization.Encoding.PEM,
            serialization.PublicFormat.SubjectPublicKeyInfo,
        )
    )

    # Expand mutations to reach ≥150 by parametric variants
    for idx in range(40):
        add(
            f"payload_byte_flip_{idx:02d}",
            lambda dst, i=idx: _rewrite_zip(
                positive["bundle"],
                dst,
                lambda n, r, j=i: (
                    n,
                    (r[:j] + bytes([(r[j] ^ 0x5A)]) + r[j + 1 :] if n.endswith("/payload") and len(r) > j else r),
                ),
            ),
        )
    for idx in range(20):
        add(
            f"manifest_byte_flip_{idx:02d}",
            lambda dst, i=idx: _rewrite_zip(
                positive["bundle"],
                dst,
                lambda n, r, j=i: (
                    n,
                    (
                        r[:j] + bytes([(r[j] ^ 0xA5)]) + r[j + 1 :]
                        if n == "package_manifest.json" and len(r) > j
                        else r
                    ),
                ),
            ),
        )
    for idx in range(10):
        add(
            f"certificate_byte_flip_{idx:02d}",
            lambda dst, i=idx: _rewrite_zip(
                positive["bundle"],
                dst,
                lambda n, r, j=i: (
                    n,
                    (
                        r[:j] + bytes([(r[j] ^ 0x3C)]) + r[j + 1 :]
                        if n == "certificate.json" and len(r) > j
                        else r
                    ),
                ),
            ),
        )
    for idx in range(15):
        add(
            f"extra_member_{idx:02d}",
            lambda dst, i=idx: _inject_member(
                positive["bundle"], dst, f"extra/noise_{i:02d}.txt", f"noise-{i}".encode()
            ),
        )

    for name, builder in attack_builders:
        dst = root / f"{name}.pcs.zip"
        try:
            builder(dst)
            constructed = True
            construct_error = None
        except Exception as exc:  # noqa: BLE001
            constructed = False
            construct_error = f"{type(exc).__name__}: {exc}"
            dst.write_bytes(b"")
        if name.startswith("positive"):
            continue
        # Wrong public key cases for a subset
        if name == "payload_tamper":
            outcome = _verify(dst, attacker_pub, positive["fingerprint"])
            cases.append(
                {
                    "id": "wrong_key_on_tampered",
                    "class": "negative",
                    "attack": "signature_substitution_wrong_key",
                    "expected_reject": True,
                    "bundle_sha256": _sha256(dst.read_bytes()) if dst.is_file() else None,
                    "constructed": True,
                    "verification": outcome,
                }
            )
        outcome = _verify(dst, positive["public_key"], positive["fingerprint"]) if constructed else {
            "attempted": False,
            "valid": False,
            "authoritative": False,
            "failed_stage": "not_constructed",
            "errors": [construct_error],
            "exception": None,
        }
        # If construction failed, still record — do not claim rejection from generator refusal alone
        # unless verification was attempted.
        cases.append(
            {
                "id": name,
                "class": "negative",
                "attack": name,
                "expected_reject": True,
                "bundle_sha256": _sha256(dst.read_bytes()) if dst.is_file() else None,
                "constructed": constructed,
                "construct_error": construct_error,
                "verification": outcome,
            }
        )

    # Wrong fingerprint pin on positive bundle
    outcome = _verify(positive["bundle"], positive["public_key"], "0" * 64)
    cases.append(
        {
            "id": "wrong_fingerprint_pin",
            "class": "negative",
            "attack": "fingerprint_mismatch",
            "expected_reject": True,
            "bundle_sha256": _sha256(positive["bundle"].read_bytes()),
            "constructed": True,
            "verification": outcome,
        }
    )

    # Honest bundle verified under wrong signer key (fingerprint pin matches honest key → mismatch)
    outcome = _verify(positive["bundle"], attacker_pub, positive["fingerprint"])
    cases.append(
        {
            "id": "wrong_signer_key_honest_fingerprint",
            "class": "negative",
            "attack": "signer_key_vs_fingerprint_swap",
            "expected_reject": True,
            "bundle_sha256": _sha256(positive["bundle"].read_bytes()),
            "constructed": True,
            "verification": outcome,
        }
    )

    rejected_ok = 0
    positive_ok = 0
    for case in cases:
        ver = case["verification"]
        if case["class"] == "positive":
            if ver.get("attempted") and ver.get("valid") is True:
                positive_ok += 1
            case["result"] = "pass" if ver.get("valid") is True else "FAIL_POSITIVE"
        else:
            rejected = ver.get("attempted") and ver.get("valid") is not True
            if rejected:
                rejected_ok += 1
            case["result"] = "pass" if rejected else ("FAIL_FALSE_ACCEPT" if ver.get("attempted") else "FAIL_NOT_ATTEMPTED")

    summary = {
        "format": "pcs-independent-adversarial-corpus-v1",
        "case_count": len(cases),
        "positive_controls": sum(1 for c in cases if c["class"] == "positive"),
        "negative_controls": sum(1 for c in cases if c["class"] == "negative"),
        "positive_accepted": positive_ok,
        "negatives_rejected_after_attempted_verify": rejected_ok,
        "false_accepts": [
            c["id"] for c in cases if c["class"] == "negative" and c.get("result") == "FAIL_FALSE_ACCEPT"
        ],
        "not_attempted": [
            c["id"] for c in cases if c["class"] == "negative" and c.get("result") == "FAIL_NOT_ATTEMPTED"
        ],
        "mutation_families": sorted({c["attack"].split("_")[0] for c in cases if c["class"] == "negative"}),
        "cases": cases,
    }
    RESULTS.mkdir(parents=True, exist_ok=True)
    (RESULTS / "adversarial_corpus.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (root / "SUMMARY.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return summary


def _inject_member(src: Path, dst: Path, name: str, data: bytes) -> None:
    with zipfile.ZipFile(src, "r") as zin, zipfile.ZipFile(dst, "w", compression=zipfile.ZIP_STORED) as zout:
        for info in zin.infolist():
            out = zipfile.ZipInfo(info.filename, (1980, 1, 1, 0, 0, 0))
            out.create_system = 3
            out.external_attr = 0o100644 << 16
            out.compress_type = zipfile.ZIP_STORED
            zout.writestr(out, zin.read(info.filename))
        bad = zipfile.ZipInfo(name, (1980, 1, 1, 0, 0, 0))
        bad.create_system = 3
        bad.external_attr = 0o100644 << 16
        bad.compress_type = zipfile.ZIP_STORED
        zout.writestr(bad, data)


def _duplicate_first_payload(src: Path, dst: Path) -> None:
    with zipfile.ZipFile(src, "r") as zin:
        names = zin.namelist()
        payload = next(n for n in names if n.endswith("/payload"))
        raw = zin.read(payload)
    with zipfile.ZipFile(src, "r") as zin, zipfile.ZipFile(dst, "w", compression=zipfile.ZIP_STORED) as zout:
        for info in zin.infolist():
            out = zipfile.ZipInfo(info.filename, (1980, 1, 1, 0, 0, 0))
            out.create_system = 3
            out.external_attr = 0o100644 << 16
            out.compress_type = zipfile.ZIP_STORED
            zout.writestr(out, zin.read(info.filename))
        dup = zipfile.ZipInfo(payload, (1980, 1, 1, 0, 0, 0))
        dup.create_system = 3
        dup.external_attr = 0o100644 << 16
        dup.compress_type = zipfile.ZIP_STORED
        zout.writestr(dup, raw + b"\n#dup\n")
