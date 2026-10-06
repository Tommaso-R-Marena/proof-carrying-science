from __future__ import annotations
import json
import tempfile
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from pcs.kernel import build_certificate, verify_certificate, AssuranceError, semantic_hash
from pcs.hashing import sha256_file, sha256_json
from pcs.signing import generate_keypair, sign_certificate, verify_signature
from pcs.attest import attest
from pcs.bundle_verify import verify_bundle
from pcs.package import build_package_manifest
from pcs.scaffold import init_project

MANIFEST = ROOT / "examples/biopharma_demo/manifest.json"
PKPD_MANIFEST = ROOT / "examples/pkpd_one_compartment/manifest.json"


def rehash(cert: dict) -> None:
    cert["integrity_hash"] = ""
    cert["integrity_hash"] = sha256_json(cert)


def packaged_artifact_path(package_dir: Path, cert: dict, artifact_id: str) -> Path:
    """Resolve a tampering target from the actual digest-addressed certificate.

    The producer no longer packages artifacts using their source filenames.
    A missing, escaped or ambiguous packaged path is a campaign error, never
    evidence that the verifier safely rejected a forged artifact.
    """
    matches = [artifact for artifact in cert["artifacts"] if artifact.get("id") == artifact_id]
    if len(matches) != 1:
        raise ValueError(f"expected exactly one packaged artifact {artifact_id!r}")
    root = package_dir.resolve()
    relative = matches[0].get("path")
    if not isinstance(relative, str) or not relative or Path(relative).is_absolute():
        raise ValueError(f"invalid packaged path for {artifact_id!r}")
    target = (root / relative).resolve()
    if not target.is_relative_to(root) or not target.is_file():
        raise ValueError(f"missing or escaped packaged artifact {artifact_id!r}")
    return target


def campaign() -> dict:
    results=[]

    def run(name, fn):
        try:
            rejected, detail = fn()
            results.append({"attack":name,"rejected":bool(rejected),"detail":detail})
        except Exception as e:
            results.append({"attack":name,"rejected":False,"detail":f"campaign error {type(e).__name__}: {e}"})

    def artifact_tamper():
        with tempfile.TemporaryDirectory() as d:
            cert=build_certificate(MANIFEST,d)
            p=packaged_artifact_path(Path(d),cert,"train")
            p.write_text(p.read_text()+"X,0\n")
            r=verify_certificate(Path(d)/"certificate.json")
            return (not r["valid"], r["errors"])
    run("artifact_tamper_without_rehash", artifact_tamper)

    def cert_hash_tamper():
        with tempfile.TemporaryDirectory() as d:
            build_certificate(MANIFEST,d)
            cp=Path(d)/"certificate.json"; c=json.loads(cp.read_text()); c["subject"]="forged"; cp.write_text(json.dumps(c))
            r=verify_certificate(cp); return (not r["valid"],r["errors"])
    run("certificate_content_tamper_without_rehash",cert_hash_tamper)

    def forged_pass():
        with tempfile.TemporaryDirectory() as d:
            build_certificate(MANIFEST,d)
            cp=Path(d)/"certificate.json"; c=json.loads(cp.read_text())
            tp=packaged_artifact_path(Path(d),c,"test")
            tp.write_text("subject_id,concentration_mg_L\nS001,9.8\n")
            for a in c["artifacts"]:
                if a["id"]=="test": a["sha256"]=sha256_file(tp)
            rehash(c); cp.write_text(json.dumps(c,indent=2,sort_keys=True))
            r=verify_certificate(cp); return (not r["valid"],r["errors"])
    run("forged_PASS_after_data_change_with_rehash",forged_pass)

    def evidence_detail_forge():
        with tempfile.TemporaryDirectory() as d:
            build_certificate(MANIFEST,d)
            cp=Path(d)/"certificate.json"; c=json.loads(cp.read_text())
            c["evidence"][0]["details"]["left_unique"]=999999
            rehash(c); cp.write_text(json.dumps(c,indent=2,sort_keys=True))
            r=verify_certificate(cp); return (not r["valid"],r["errors"])
    run("evidence_details_forged_with_rehash",evidence_detail_forge)

    def assessment_forge():
        with tempfile.TemporaryDirectory() as d:
            build_certificate(MANIFEST,d)
            cp=Path(d)/"certificate.json"; c=json.loads(cp.read_text())
            c["claims"][0]["assessment"]={"status":"FORMALLY_VERIFIED_UNDER_ASSUMPTIONS","reason":"forged"}
            rehash(c); cp.write_text(json.dumps(c,indent=2,sort_keys=True))
            r=verify_certificate(cp); return (not r["valid"],r["errors"])
    run("claim_assessment_forged_with_rehash",assessment_forge)

    def workflow_forge():
        with tempfile.TemporaryDirectory() as d:
            build_certificate(MANIFEST,d)
            cp=Path(d)/"certificate.json"; c=json.loads(cp.read_text())
            c["workflow_summary"]["node_count"]=500
            rehash(c); cp.write_text(json.dumps(c,indent=2,sort_keys=True))
            r=verify_certificate(cp); return (not r["valid"],r["errors"])
    run("workflow_summary_forged_with_rehash",workflow_forge)

    def build_path_escape():
        with tempfile.TemporaryDirectory() as d:
            p=Path(d); outside=p.parent/"pcs-secret.txt"; outside.write_text("secret")
            m={"subject":"x","assumptions":[],"claims":[],"artifacts":[{"id":"a","path":"../pcs-secret.txt","role":"input"}],"checks":[],"workflow":{"nodes":[]}}
            mp=p/"manifest.json"; mp.write_text(json.dumps(m))
            try:
                build_certificate(mp,p/"out")
            except AssuranceError as e:
                outside.unlink(missing_ok=True)
                return True,str(e)
            outside.unlink(missing_ok=True)
            return False,"path escape accepted"
    run("manifest_path_traversal",build_path_escape)

    def semantic_misbinding():
        with tempfile.TemporaryDirectory() as d:
            p=Path(d); m=json.loads(MANIFEST.read_text())
            for name in ("train.csv","test.csv","model_spec.txt"):
                (p/name).write_bytes((MANIFEST.parent/name).read_bytes())
            m["claims"][0]["required_evidence"]=["E3"]
            m["checks"][2]["claim_ids"].append("C1")
            mp=p/"manifest.json"; mp.write_text(json.dumps(m))
            try:
                build_certificate(mp,p/"out")
            except AssuranceError as e:
                return True,str(e)
            return False,"unrelated evidence supported typed claim"
    run("semantic_evidence_misbinding",semantic_misbinding)

    def pkpd_tamper(field, delta, row=1):
        with tempfile.TemporaryDirectory() as d:
            build_certificate(PKPD_MANIFEST, d)
            cp=Path(d)/"certificate.json"; c=json.loads(cp.read_text())
            pp=packaged_artifact_path(Path(d),c,"pk_predictions")
            lines=pp.read_text().splitlines(); cells=lines[row].split(",")
            idx = 1 if field=="concentration" else 2
            cells[idx]=str(float(cells[idx])+delta); lines[row]=",".join(cells)
            pp.write_text("\n".join(lines)+"\n")
            for a in c["artifacts"]:
                if a["id"]=="pk_predictions": a["sha256"]=sha256_file(pp)
            rehash(c); cp.write_text(json.dumps(c,indent=2,sort_keys=True))
            r=verify_certificate(cp); return (not r["valid"],r["errors"])
    run("pkpd_prediction_tamper_with_rehash", lambda: pkpd_tamper("concentration",0.25,1))
    run("pkpd_effect_tamper_with_rehash", lambda: pkpd_tamper("effect",5.0,2))

    def semantic_hash_forge():
        with tempfile.TemporaryDirectory() as d:
            build_certificate(PKPD_MANIFEST,d)
            cp=Path(d)/"certificate.json"; c=json.loads(cp.read_text())
            c["semantic_hash"]="0"*64; rehash(c); cp.write_text(json.dumps(c,indent=2,sort_keys=True))
            r=verify_certificate(cp); return (not r["valid"],r["errors"])
    run("semantic_hash_forged_with_integrity_rehash",semantic_hash_forge)

    def signature_replay_after_certificate_rewrite():
        with tempfile.TemporaryDirectory() as d:
            p=Path(d); build_certificate(PKPD_MANIFEST,p/"evidence")
            cp=p/"evidence/certificate.json"; priv,pub,sig=p/"private.pem",p/"public.pem",p/"sig.json"
            generate_keypair(priv,pub); sign_certificate(cp,priv,sig)
            c=json.loads(cp.read_text()); c["subject"]="rewritten-subject"; c["semantic_hash"]=""; c["integrity_hash"]=""
            c["semantic_hash"]=semantic_hash(c); c["integrity_hash"]=sha256_json(c)
            cp.write_text(json.dumps(c,indent=2,sort_keys=True))
            r=verify_signature(cp,sig,pub); return (not r["valid"],r["errors"])
    run("signature_replay_after_certificate_rewrite",signature_replay_after_certificate_rewrite)

    def package_report_tamper():
        with tempfile.TemporaryDirectory() as d:
            p=Path(d); project=p/"project"; init_project(project)
            priv,pub=p/"priv.pem",p/"pub.pem"; generate_keypair(priv,pub)
            attest(project/"manifest.json",p/"evidence",private_key=priv,public_key=pub)
            evidence=p/"evidence"; (evidence/"report.html").write_text("<html>forged human report</html>")
            z=p/"tampered.zip"
            with zipfile.ZipFile(z,"w",compression=zipfile.ZIP_DEFLATED) as zf:
                for f in sorted(x for x in evidence.rglob("*") if x.is_file()):
                    zf.write(f,f.relative_to(evidence).as_posix())
            r=verify_bundle(z,public_key=pub,require_signature=True)
            return (not r["valid"],r["errors"])
    run("package_report_tamper",package_report_tamper)

    def package_manifest_rewrite_without_resign():
        with tempfile.TemporaryDirectory() as d:
            p=Path(d); project=p/"project"; init_project(project)
            priv,pub=p/"priv.pem",p/"pub.pem"; generate_keypair(priv,pub)
            attest(project/"manifest.json",p/"evidence",private_key=priv,public_key=pub)
            evidence=p/"evidence"; report=evidence/"report.html"; report.write_text(report.read_text()+"<!-- forged -->")
            build_package_manifest(evidence)
            z=p/"forged.zip"
            with zipfile.ZipFile(z,"w",compression=zipfile.ZIP_DEFLATED) as zf:
                for f in sorted(x for x in evidence.rglob("*") if x.is_file()):
                    zf.write(f,f.relative_to(evidence).as_posix())
            r=verify_bundle(z,public_key=pub,require_signature=True)
            return (not r["valid"],r["errors"])
    run("package_manifest_rewrite_without_resign",package_manifest_rewrite_without_resign)

    def signer_substitution_against_pin():
        with tempfile.TemporaryDirectory() as d:
            p=Path(d); project=p/"project"; init_project(project)
            honest_priv,honest_pub=p/"honest-priv.pem",p/"honest-pub.pem"; honest=generate_keypair(honest_priv,honest_pub)
            attacker_priv,attacker_pub=p/"attacker-priv.pem",p/"attacker-pub.pem"; generate_keypair(attacker_priv,attacker_pub)
            a=attest(project/"manifest.json",p/"evidence",private_key=attacker_priv,public_key=attacker_pub)
            r=verify_bundle(a["bundle"]["bundle"],public_key=attacker_pub,require_signature=True,expected_signer_fingerprint=honest["fingerprint"])
            return (not r["valid"],r["errors"])
    run("signer_substitution_against_pinned_identity",signer_substitution_against_pin)

    def external_policy_rejects_producer_success():
        with tempfile.TemporaryDirectory() as d:
            p=Path(d); project=p/"project"; init_project(project)
            priv,pub=p/"priv.pem",p/"pub.pem"; keys=generate_keypair(priv,pub)
            a=attest(project/"manifest.json",p/"evidence",private_key=priv,public_key=pub)
            policy=p/"reviewer-policy.json"
            policy.write_text(json.dumps({"policy_version":"pcs-acceptance-policy-v1","require_signature":True,"expected_signer_fingerprint":keys["fingerprint"],"required_claims":{"C_PKPD_REPLAY":["FORMALLY_VERIFIED_UNDER_ASSUMPTIONS"]}}))
            r=verify_bundle(a["bundle"]["bundle"],public_key=pub,require_signature=True,policy=policy)
            return (not r["valid"],r["errors"])
    run("external_reviewer_policy_rejects_producer_supported_claim",external_policy_rejects_producer_success)


    def private_key_leak_bundle():
        from pcs.bundle import create_reproducible_bundle, BundleSafetyError
        with tempfile.TemporaryDirectory() as d:
            p=Path(d); project=p/"project"; init_project(project)
            priv,pub=p/"priv.pem",p/"pub.pem"; generate_keypair(priv,pub)
            attest(project/"manifest.json",p/"evidence",private_key=priv,public_key=pub)
            evidence=p/"evidence"
            (evidence/"accidental-private.pem").write_bytes(priv.read_bytes())
            try:
                create_reproducible_bundle(evidence/"certificate.json",p/"unsafe.zip")
            except BundleSafetyError as e:
                return True,str(e)
            return False,"private key material was included in an evidence bundle"
    run("private_key_material_accidentally_staged_for_bundle",private_key_leak_bundle)

    def delayed_private_key_marker():
        from pcs.bundle import create_reproducible_bundle, BundleSafetyError
        with tempfile.TemporaryDirectory() as d:
            p=Path(d); evidence=p/"evidence"; evidence.mkdir()
            (evidence/"certificate.json").write_text("{}")
            (evidence/"late-key.bin").write_bytes(
                b"x"*16384 + b"-----BEGIN PRIVATE KEY-----\nforbidden"
            )
            try:
                create_reproducible_bundle(evidence/"certificate.json",p/"unsafe.zip")
            except BundleSafetyError as e:
                return ("private-key material" in str(e), str(e))
            return False,"private key marker beyond historical prefix scan was accepted"
    run("private_key_marker_beyond_prefix_scan",delayed_private_key_marker)


    def stale_output_contamination():
        with tempfile.TemporaryDirectory() as d:
            p=Path(d); project=p/"project"; init_project(project)
            evidence=p/"evidence"; evidence.mkdir()
            (evidence/"stale-signature.json").write_text("stale")
            try:
                attest(project/"manifest.json",evidence)
            except Exception as e:
                return ("stale evidence contamination" in str(e), str(e))
            return False,"non-empty attestation output directory was accepted"
    run("stale_attestation_output_contamination",stale_output_contamination)

    def duplicate_zip_members():
        from pcs.bundle_verify import BundleVerificationError
        import warnings
        with tempfile.TemporaryDirectory() as d:
            z=Path(d)/"duplicate.zip"
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", UserWarning)
                with zipfile.ZipFile(z,"w",compression=zipfile.ZIP_DEFLATED) as zf:
                    zf.writestr("certificate.json","{}")
                    zf.writestr("certificate.json","{}")
            try:
                verify_bundle(z)
            except BundleVerificationError as e:
                return ("duplicate" in str(e), str(e))
            return False,"duplicate ZIP member names were accepted"
    run("duplicate_zip_member_ambiguity",duplicate_zip_members)

    def zip_file_parent_collision():
        from pcs.bundle_verify import BundleVerificationError
        with tempfile.TemporaryDirectory() as d:
            z=Path(d)/"collision.zip"
            with zipfile.ZipFile(z,"w",compression=zipfile.ZIP_DEFLATED) as zf:
                zf.writestr("certificate.json","{}")
                zf.writestr("artifacts","regular-file")
                zf.writestr("artifacts/data.csv","x")
            try:
                verify_bundle(z)
            except BundleVerificationError as e:
                return ("namespace collision" in str(e), str(e))
            return False,"file-as-parent ZIP namespace collision was accepted"
    run("zip_file_parent_namespace_collision",zip_file_parent_collision)

    def casefold_zip_collision():
        from pcs.bundle_verify import BundleVerificationError
        with tempfile.TemporaryDirectory() as d:
            z=Path(d)/"casefold.zip"
            with zipfile.ZipFile(z,"w",compression=zipfile.ZIP_DEFLATED) as zf:
                zf.writestr("certificate.json","{}")
                zf.writestr("Artifacts/data.csv","a")
                zf.writestr("artifacts/data.csv","b")
            try:
                verify_bundle(z)
            except BundleVerificationError as e:
                return ("cross-platform ZIP name collision" in str(e), str(e))
            return False,"case-folding ZIP namespace collision was accepted"
    run("zip_casefold_namespace_collision",casefold_zip_collision)

    def windows_reserved_zip_name():
        from pcs.bundle_verify import BundleVerificationError
        with tempfile.TemporaryDirectory() as d:
            z=Path(d)/"reserved.zip"
            with zipfile.ZipFile(z,"w",compression=zipfile.ZIP_DEFLATED) as zf:
                zf.writestr("certificate.json","{}")
                zf.writestr("artifacts/CON.txt","x")
            try:
                verify_bundle(z)
            except BundleVerificationError as e:
                return ("Windows-reserved" in str(e), str(e))
            return False,"Windows-reserved ZIP filename was accepted"
    run("zip_windows_reserved_filename",windows_reserved_zip_name)

    def duplicate_json_key_certificate():
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"certificate.json"
            p.write_text('{"spec_version":"pcs-0.5","subject":"first","subject":"second"}')
            r=verify_certificate(p)
            return (
                (not r["valid"]) and any("duplicate JSON object key" in e for e in r["errors"]),
                r["errors"],
            )
    run("duplicate_json_key_parser_differential",duplicate_json_key_certificate)

    def posthoc_intake_claim_rewrite():
        from pcs.intake import freeze_intake, assert_lock_matches_certificate, PilotIntakeError
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)
            intake=json.loads((PKPD_MANIFEST.parent/"pilot_intake.json").read_text())
            lock=freeze_intake(intake)
            cert=build_certificate(PKPD_MANIFEST,p/"evidence")
            cert["claims"][0]["statement"]="weakened post-hoc claim"
            try:
                assert_lock_matches_certificate(lock,cert)
            except PilotIntakeError as e:
                return ("claim statement changed" in str(e),str(e))
            return False,"post-hoc claim rewrite with same ID was accepted"
    run("posthoc_claim_rewrite_after_intake_freeze",posthoc_intake_claim_rewrite)

    total=len(results); rejected=sum(x["rejected"] for x in results)
    return {"campaign":"pcs-v0.5-foundational-attacks","attacks":total,"rejected":rejected,"false_accepts":total-rejected,"results":results}


if __name__=="__main__":
    r=campaign(); print(json.dumps(r,indent=2,sort_keys=True))
    raise SystemExit(0 if r["false_accepts"]==0 else 1)
