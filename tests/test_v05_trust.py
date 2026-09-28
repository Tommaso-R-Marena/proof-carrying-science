from __future__ import annotations
import json
import tempfile
import zipfile
from pathlib import Path
from types import SimpleNamespace

from pcs.attest import attest
from pcs.bundle_verify import verify_bundle
from pcs.cli import cmd_verify_bundle
from pcs.hashing import sha256_file
from pcs.scaffold import init_project
from pcs.signing import generate_keypair

def _signed_attestation(root: Path):
    project=root/"project"; init_project(project)
    priv,pub=root/"private.pem",root/"public.pem"; keys=generate_keypair(priv,pub)
    evidence=root/"evidence"; result=attest(project/"manifest.json",evidence,private_key=priv,public_key=pub)
    return project,priv,pub,keys,evidence,Path(result["bundle"]["bundle"])

def test_package_signature_binds_report_and_all_delivered_files():
    with tempfile.TemporaryDirectory() as td:
        root=Path(td); _,_,pub,_,evidence,bundle=_signed_attestation(root)
        ok=verify_bundle(bundle,public_key=pub,require_signature=True); assert ok["valid"],ok["errors"]
        (evidence/"report.html").write_text("<html>misleading report</html>")
        tampered=root/"tampered.zip"
        with zipfile.ZipFile(tampered,"w",compression=zipfile.ZIP_DEFLATED) as zf:
            for p in sorted(x for x in evidence.rglob("*") if x.is_file()): zf.write(p,p.relative_to(evidence).as_posix())
        bad=verify_bundle(tampered,public_key=pub,require_signature=True)
        assert not bad["valid"]; assert any("package hash mismatch: report.html" in e for e in bad["errors"])

def test_recomputed_package_manifest_cannot_forge_signature():
    with tempfile.TemporaryDirectory() as td:
        root=Path(td); _,_,pub,_,evidence,_=_signed_attestation(root)
        report=evidence/"report.html"; report.write_text(report.read_text()+"<!-- changed -->")
        from pcs.package import build_package_manifest
        build_package_manifest(evidence)
        forged=root/"forged.zip"
        with zipfile.ZipFile(forged,"w",compression=zipfile.ZIP_DEFLATED) as zf:
            for p in sorted(x for x in evidence.rglob("*") if x.is_file()): zf.write(p,p.relative_to(evidence).as_posix())
        result=verify_bundle(forged,public_key=pub,require_signature=True)
        assert not result["valid"]; assert any("package signature" in e for e in result["errors"])

def test_signer_fingerprint_can_be_pinned():
    with tempfile.TemporaryDirectory() as td:
        root=Path(td); _,_,pub,keys,_,bundle=_signed_attestation(root)
        assert verify_bundle(bundle,public_key=pub,require_signature=True,expected_signer_fingerprint=keys["fingerprint"])["valid"]
        bad=verify_bundle(bundle,public_key=pub,require_signature=True,expected_signer_fingerprint="0"*64)
        assert not bad["valid"]; assert any("pinned expected fingerprint" in e for e in bad["errors"])

def test_external_acceptance_policy_passes_reference_and_fails_unacceptable_status():
    with tempfile.TemporaryDirectory() as td:
        root=Path(td); _,_,pub,keys,_,bundle=_signed_attestation(root)
        policy=root/"policy.json"; policy.write_text(json.dumps({"policy_version":"pcs-acceptance-policy-v1","require_signature":True,"expected_signer_fingerprint":keys["fingerprint"],"required_claims":{"C_PKPD_CONTRACT":["COMPUTATIONALLY_SUPPORTED"],"C_PKPD_REPLAY":["COMPUTATIONALLY_SUPPORTED"]}}))
        ok=verify_bundle(bundle,public_key=pub,require_signature=True,policy=policy); assert ok["valid"],ok["errors"]
        failing=root/"failing.json"; failing.write_text(json.dumps({"policy_version":"pcs-acceptance-policy-v1","require_signature":True,"expected_signer_fingerprint":keys["fingerprint"],"required_claims":{"C_PKPD_REPLAY":["FORMALLY_VERIFIED_UNDER_ASSUMPTIONS"]}}))
        bad=verify_bundle(bundle,public_key=pub,require_signature=True,policy=failing)
        assert not bad["valid"]; assert bad["policy"] and not bad["policy"]["pass"]

def test_policy_is_external_not_part_of_signed_bundle():
    with tempfile.TemporaryDirectory() as td:
        root=Path(td); _,_,pub,_,_,bundle=_signed_attestation(root)
        with zipfile.ZipFile(bundle) as zf: names=set(zf.namelist())
        assert not any(n.startswith("policy") or "/policy" in n for n in names)
        assert verify_bundle(bundle,public_key=pub,require_signature=True)["valid"]


def test_bundle_refuses_accidental_private_key_material():
    from pcs.bundle import create_reproducible_bundle, BundleSafetyError
    with tempfile.TemporaryDirectory() as td:
        root=Path(td)
        _,priv,_,_,evidence,_=_signed_attestation(root)
        (evidence/"accidental-private.pem").write_bytes(priv.read_bytes())
        try:
            create_reproducible_bundle(evidence/"certificate.json",root/"unsafe.zip")
        except BundleSafetyError as exc:
            assert "private-key material" in str(exc)
        else:
            raise AssertionError("expected BundleSafetyError")
        assert not (root/"unsafe.zip").exists()


def test_verifier_separates_replay_integrity_authenticity_and_policy():
    with tempfile.TemporaryDirectory() as td:
        root=Path(td); _,_,pub,keys,_,bundle=_signed_attestation(root)

        without_key=verify_bundle(bundle)
        assert without_key["valid"]
        assert without_key["assurance_dimensions"]["scientific_replay"]=="PASS"
        assert without_key["assurance_dimensions"]["package_integrity"]=="PASS"
        assert without_key["assurance_dimensions"]["signer_authenticity"]=="PRESENT_NOT_VERIFIED"
        assert without_key["assurance_dimensions"]["reviewer_policy"]=="NOT_APPLIED"

        with_key=verify_bundle(
            bundle,
            public_key=pub,
            require_signature=True,
            expected_signer_fingerprint=keys["fingerprint"],
        )
        assert with_key["valid"]
        assert with_key["assurance_dimensions"]["signer_authenticity"]=="VERIFIED"


def test_verifier_rejects_duplicate_zip_members():
    import warnings
    from pcs.bundle_verify import BundleVerificationError
    with tempfile.TemporaryDirectory() as td:
        root=Path(td)
        z=root/"duplicate.zip"
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", UserWarning)
            with zipfile.ZipFile(z,"w",compression=zipfile.ZIP_DEFLATED) as zf:
                zf.writestr("certificate.json","{}")
                zf.writestr("certificate.json","{}")
        try:
            verify_bundle(z)
        except BundleVerificationError as exc:
            assert "duplicate" in str(exc)
        else:
            raise AssertionError("duplicate ZIP members should be rejected")


def test_verifier_rejects_file_as_parent_namespace_collision():
    from pcs.bundle_verify import BundleVerificationError
    with tempfile.TemporaryDirectory() as td:
        root=Path(td)
        z=root/"collision.zip"
        with zipfile.ZipFile(z,"w",compression=zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("certificate.json","{}")
            zf.writestr("artifacts","regular-file")
            zf.writestr("artifacts/data.csv","x")
        try:
            verify_bundle(z)
        except BundleVerificationError as exc:
            assert "namespace collision" in str(exc)
        else:
            raise AssertionError("file/parent namespace collision should be rejected")


def test_verifier_rejects_casefold_colliding_zip_members():
    from pcs.bundle_verify import BundleVerificationError
    with tempfile.TemporaryDirectory() as td:
        root=Path(td)
        z=root/"casefold.zip"
        with zipfile.ZipFile(z,"w",compression=zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("certificate.json","{}")
            zf.writestr("Artifacts/data.csv","a")
            zf.writestr("artifacts/data.csv","b")
        try:
            verify_bundle(z)
        except BundleVerificationError as exc:
            assert "cross-platform ZIP name collision" in str(exc)
        else:
            raise AssertionError("case-folding ZIP collision should be rejected")


def test_verifier_rejects_windows_reserved_zip_member():
    from pcs.bundle_verify import BundleVerificationError
    with tempfile.TemporaryDirectory() as td:
        root=Path(td)
        z=root/"reserved.zip"
        with zipfile.ZipFile(z,"w",compression=zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("certificate.json","{}")
            zf.writestr("artifacts/CON.txt","x")
        try:
            verify_bundle(z)
        except BundleVerificationError as exc:
            assert "Windows-reserved" in str(exc)
        else:
            raise AssertionError("Windows-reserved ZIP filename should be rejected")


def test_verification_receipt_binds_exact_bundle_and_policy():
    with tempfile.TemporaryDirectory() as td:
        root=Path(td)
        _,_,pub,keys,_,bundle=_signed_attestation(root)
        policy=root/"reviewer-policy.json"
        policy.write_text(json.dumps({
            "policy_version":"pcs-acceptance-policy-v1",
            "require_signature":True,
            "expected_signer_fingerprint":keys["fingerprint"],
            "required_claims":{
                "C_PKPD_CONTRACT":["COMPUTATIONALLY_SUPPORTED"],
                "C_PKPD_REPLAY":["COMPUTATIONALLY_SUPPORTED"]
            }
        },sort_keys=True))
        receipt=root/"verification-receipt.json"
        rc=cmd_verify_bundle(SimpleNamespace(
            bundle=str(bundle),
            public_key=str(pub),
            require_signature=True,
            expected_signer_fingerprint=keys["fingerprint"],
            policy=str(policy),
            receipt=str(receipt),
        ))
        assert rc==0
        record=json.loads(receipt.read_text(encoding="utf-8"))
        assert record["verification_receipt_format"]=="pcs-bundle-verification-v1"
        assert record["bundle_sha256"]==sha256_file(bundle)
        assert record["verification_inputs"]["policy_sha256"]==sha256_file(policy)
        assert record["assurance_dimensions"]["signer_authenticity"]=="VERIFIED"
        assert record["assurance_dimensions"]["reviewer_policy"]=="PASS"
        assert record["verified_at"]


def test_bundle_private_key_scan_covers_beyond_prefix():
    from pcs.bundle import create_reproducible_bundle, BundleSafetyError
    with tempfile.TemporaryDirectory() as td:
        root=Path(td)
        evidence=root/"evidence"
        evidence.mkdir()
        (evidence/"certificate.json").write_text("{}")
        (evidence/"late-key.bin").write_bytes(
            b"x"*16384 + b"-----BEGIN PRIVATE KEY-----\nforbidden"
        )
        try:
            create_reproducible_bundle(evidence/"certificate.json",root/"unsafe.zip")
        except BundleSafetyError as exc:
            assert "private-key material" in str(exc)
        else:
            raise AssertionError("private-key marker beyond old prefix should be rejected")


def test_bundle_creator_enforces_same_single_file_limit(monkeypatch):
    import pcs.bundle as bundle_module
    from pcs.bundle import create_reproducible_bundle, BundleSafetyError
    with tempfile.TemporaryDirectory() as td:
        root=Path(td)
        evidence=root/"evidence"
        evidence.mkdir()
        (evidence/"certificate.json").write_text("{}")
        (evidence/"large.bin").write_bytes(b"01234567890")
        monkeypatch.setattr(bundle_module,"MAX_BUNDLE_SINGLE_FILE",10)
        try:
            create_reproducible_bundle(evidence/"certificate.json",root/"too-large.zip")
        except BundleSafetyError as exc:
            assert "oversized file" in str(exc)
        else:
            raise AssertionError("producer should refuse files verifier would reject")
