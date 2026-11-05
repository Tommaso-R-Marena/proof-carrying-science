from __future__ import annotations
import json
import tempfile
import zipfile
from pathlib import Path

from pcs.attest import attest
from pcs.bundle_verify import verify_bundle, BundleVerificationError
from pcs.doctor import doctor
from pcs.scaffold import init_project, ScaffoldError
from pcs.signing import generate_keypair

def test_init_pkpd_project_is_immediately_attestable():
    with tempfile.TemporaryDirectory() as td:
        root=Path(td)/"pilot"; result=init_project(root,subject="pilot-subject"); assert result["template"]=="pkpd"
        out=Path(td)/"evidence"; att=attest(root/"manifest.json",out)
        assert all(v=="COMPUTATIONALLY_SUPPORTED" for v in att["claim_statuses"].values())
        assert Path(att["bundle"]["bundle"]).is_file()

def test_init_refuses_nonempty_destination_without_force():
    with tempfile.TemporaryDirectory() as td:
        root=Path(td)/"pilot"; root.mkdir(); (root/"existing.txt").write_text("keep")
        try: init_project(root)
        except ScaffoldError: pass
        else: raise AssertionError("expected ScaffoldError")
        assert (root/"existing.txt").read_text()=="keep"

def test_attest_signed_bundle_verifies_end_to_end():
    with tempfile.TemporaryDirectory() as td:
        root=Path(td); project=root/"project"; init_project(project)
        priv,pub=root/"private.pem",root/"public.pem"; generate_keypair(priv,pub)
        result=attest(project/"manifest.json",root/"evidence",private_key=priv,public_key=pub)
        verified=verify_bundle(result["bundle"]["bundle"],public_key=pub,require_signature=True)
        assert verified["valid"],verified["errors"]; assert verified["signature"]["valid"]

def test_verify_bundle_rejects_path_traversal_member():
    with tempfile.TemporaryDirectory() as td:
        z=Path(td)/"bad.zip"
        with zipfile.ZipFile(z,"w") as zf:
            zf.writestr("../escape.txt","bad"); zf.writestr("certificate.json",json.dumps({}))
        try: verify_bundle(z)
        except BundleVerificationError as e: assert "unsafe ZIP member" in str(e)
        else: raise AssertionError("expected BundleVerificationError")

def test_verify_bundle_requires_signature_when_requested():
    with tempfile.TemporaryDirectory() as td:
        root=Path(td); project=root/"project"; init_project(project)
        result=attest(project/"manifest.json",root/"evidence")
        verified=verify_bundle(result["bundle"]["bundle"],require_signature=True)
        assert not verified["valid"]
        assert any("required" in e and "signature" in e for e in verified["errors"])

def test_doctor_core_checks_healthy_without_requiring_lean():
    result=doctor(); assert result["healthy"]
    names={x["name"] for x in result["checks"]}
    assert {"python","cryptography","lean","lake","pkpd_reference_selfcheck"}.issubset(names)


def test_attest_refuses_nonempty_output_directory():
    from pcs.attest import AttestationError
    with tempfile.TemporaryDirectory() as td:
        root=Path(td); project=root/"project"; init_project(project)
        evidence=root/"evidence"; evidence.mkdir(); (evidence/"stale-signature.json").write_text("stale")
        try:
            attest(project/"manifest.json",evidence)
        except AttestationError as exc:
            assert "stale evidence contamination" in str(exc)
        else:
            raise AssertionError("expected AttestationError")
        assert (evidence/"stale-signature.json").read_text()=="stale"
