from __future__ import annotations
import json
import tempfile
import time
from pathlib import Path

from pcs.bundle import create_reproducible_bundle
from pcs.diffing import diff_certificates
from pcs.hashing import sha256_file, sha256_json
from pcs.kernel import build_certificate, verify_certificate
from pcs.signing import generate_keypair, sign_certificate, verify_signature

ROOT=Path(__file__).resolve().parents[1]
MANIFEST=ROOT/"examples/pkpd_one_compartment/manifest.json"

def test_semantic_hash_stable_across_runs():
    with tempfile.TemporaryDirectory() as d:
        p=Path(d); c1=build_certificate(MANIFEST,p/"a"); time.sleep(0.01); c2=build_certificate(MANIFEST,p/"b")
        assert c1["generated_at"] != c2["generated_at"]
        assert c1["integrity_hash"] != c2["integrity_hash"]
        assert c1["semantic_hash"] == c2["semantic_hash"]
        assert verify_certificate(p/"a/certificate.json")["valid"]
        assert verify_certificate(p/"b/certificate.json")["valid"]

def test_semantic_hash_tamper_rejected_even_after_integrity_rehash():
    with tempfile.TemporaryDirectory() as d:
        p=Path(d); build_certificate(MANIFEST,p); cp=p/"certificate.json"; cert=json.loads(cp.read_text())
        cert["semantic_hash"]="0"*64; cert["integrity_hash"]=""; cert["integrity_hash"]=sha256_json(cert)
        cp.write_text(json.dumps(cert,indent=2,sort_keys=True))
        result=verify_certificate(cp)
        assert not result["valid"]; assert "certificate semantic hash mismatch" in result["errors"]

def test_ed25519_signature_valid_then_certificate_tamper_invalid():
    with tempfile.TemporaryDirectory() as d:
        p=Path(d); build_certificate(MANIFEST,p/"evidence"); cert=p/"evidence/certificate.json"
        priv,pub,sig=p/"private.pem",p/"public.pem",p/"signature.json"
        generate_keypair(priv,pub); sign_certificate(cert,priv,sig); assert verify_signature(cert,sig,pub)["valid"]
        c=json.loads(cert.read_text()); c["subject"]="tampered"; c["semantic_hash"]="deadbeef"*8; c["integrity_hash"]=""; c["integrity_hash"]=sha256_json(c)
        cert.write_text(json.dumps(c,indent=2,sort_keys=True)); assert not verify_signature(cert,sig,pub)["valid"]

def test_reproducible_bundle_is_byte_identical():
    with tempfile.TemporaryDirectory() as d:
        p=Path(d); build_certificate(MANIFEST,p/"evidence"); cert=p/"evidence/certificate.json"
        a=create_reproducible_bundle(cert,p/"a.zip"); b=create_reproducible_bundle(cert,p/"b.zip")
        assert a["sha256"]==b["sha256"]; assert sha256_file(p/"a.zip")==sha256_file(p/"b.zip")

def test_certificate_diff_detects_changed_artifact_and_status():
    with tempfile.TemporaryDirectory() as d:
        p=Path(d); src=p/"src"; src.mkdir()
        for name in ("manifest.json","pk_model.json","predictions.csv"):
            (src/name).write_bytes((MANIFEST.parent/name).read_bytes())
        build_certificate(MANIFEST,p/"left")
        lines=(src/"predictions.csv").read_text().splitlines(); cells=lines[1].split(","); cells[1]=str(float(cells[1])+1.0); lines[1]=",".join(cells)
        (src/"predictions.csv").write_text("\n".join(lines)+"\n"); build_certificate(src/"manifest.json",p/"right")
        diff=diff_certificates(p/"left/certificate.json",p/"right/certificate.json")
        assert not diff["same_semantic_hash"]
        assert diff["artifact_changes"]["pk_predictions"]["change"]=="modified"
        assert diff["claim_changes"]["C_PK_REPLAY"]["fields"]["status"]["right"]=="FALSIFIED_OR_CHECK_FAILED"
