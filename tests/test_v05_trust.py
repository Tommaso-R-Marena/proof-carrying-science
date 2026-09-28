from __future__ import annotations
import json
import tempfile
import zipfile
from pathlib import Path

from pcs.attest import attest
from pcs.bundle_verify import verify_bundle
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
