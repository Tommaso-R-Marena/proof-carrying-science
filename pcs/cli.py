from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path

from .kernel import build_certificate, verify_certificate, AssuranceError
from .hashing import sha256_file
from .impact import impact_from_artifacts
from .report import write_html
from .signing import generate_keypair, sign_certificate, verify_signature, SignatureError
from .bundle import create_reproducible_bundle, BundleSafetyError
from .bundle_verify import verify_bundle, BundleVerificationError
from .diffing import diff_certificates
from .scaffold import init_project, ScaffoldError
from .doctor import doctor
from .attest import attest, AttestationError
from .policy import load_policy, evaluate_policy_file, PolicyError
from .package import build_package_manifest, PackageError
from .environment import write_environment, diff_environment_files
from .intake import freeze_intake_file, PilotIntakeError
from .normalized_wire import write_normalized_decision, write_normalized_set, validate_normalized_wire, verify_normalized_against_certificate, NormalizationError
from .jsonio import StrictJSONError


def cmd_certify(args):
    try:
        out = Path(args.output).resolve()
        if out.exists() and any(out.iterdir()):
            raise AssuranceError(
                f"certification output directory must be empty to prevent stale evidence contamination: {out}"
            )
        cert = build_certificate(args.manifest, out)
    except (AssuranceError, OSError, json.JSONDecodeError) as e:
        print(f"REJECT: {type(e).__name__}: {e}", file=sys.stderr)
        return 2
    print(f"WROTE {Path(args.output) / 'certificate.json'}")
    print(f"SEMANTIC_HASH {cert.get('semantic_hash')}")
    for c in cert["claims"]:
        print(f"{c['id']}: {c['assessment']['status']}")
    return 0


def cmd_verify(args):
    try:
        result = verify_certificate(args.certificate)
    except (AssuranceError, OSError, json.JSONDecodeError) as e:
        print(f"REJECT: {type(e).__name__}: {e}", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["valid"] else 1


def cmd_inspect(args):
    cert = json.loads(Path(args.certificate).read_text(encoding="utf-8"))
    print(f"Subject: {cert.get('subject')}")
    print(f"Semantic: {cert.get('semantic_hash')}")
    print(f"Integrity: {cert.get('integrity_hash')}")
    print("Claims:")
    for c in cert.get("claims", []):
        a = c.get("assessment", {})
        assumptions = ",".join(c.get("assumptions", [])) or "none"
        print(f"  {c.get('id')}: {a.get('status')} | assumptions={assumptions} | {c.get('statement')}")
    return 0


def cmd_hash(args):
    print(sha256_file(args.file))
    return 0


def cmd_impact(args):
    cert = json.loads(Path(args.certificate).read_text(encoding="utf-8"))
    result = impact_from_artifacts(cert, set(args.artifact))
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


def cmd_report(args):
    cert = json.loads(Path(args.certificate).read_text(encoding="utf-8"))
    out = write_html(cert, args.output)
    print(f"WROTE {out}")
    return 0


def cmd_gate(args):
    cert = json.loads(Path(args.certificate).read_text(encoding="utf-8"))
    statuses = {c.get("id"): c.get("assessment", {}).get("status") for c in cert.get("claims", [])}
    acceptable = set(args.accept or ["COMPUTATIONALLY_SUPPORTED", "FORMALLY_VERIFIED_UNDER_ASSUMPTIONS", "EMPIRICALLY_VALIDATED_WITHIN_SCOPE", "MIXED_SUPPORT_UNDER_ASSUMPTIONS"])
    required = args.claim or sorted(statuses)
    failures = {cid: statuses.get(cid, "MISSING") for cid in required if statuses.get(cid) not in acceptable}
    print(json.dumps({"pass": not failures, "required": required, "acceptable_statuses": sorted(acceptable), "failures": failures}, indent=2, sort_keys=True))
    return 0 if not failures else 1


def cmd_keygen(args):
    try:
        result = generate_keypair(args.private_key, args.public_key, overwrite=args.force)
    except (OSError, SignatureError) as e:
        print(f"ERROR: {type(e).__name__}: {e}", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


def cmd_sign(args):
    try:
        integrity = verify_certificate(args.certificate)
        if not integrity["valid"]:
            print(json.dumps(integrity, indent=2, sort_keys=True), file=sys.stderr)
            print("REJECT: refusing to sign an invalid certificate", file=sys.stderr)
            return 2
        record = sign_certificate(args.certificate, args.private_key, args.output)
    except (OSError, json.JSONDecodeError, SignatureError, AssuranceError) as e:
        print(f"ERROR: {type(e).__name__}: {e}", file=sys.stderr)
        return 2
    print(json.dumps({"wrote": str(args.output), "public_key_fingerprint": record["public_key_fingerprint"]}, indent=2, sort_keys=True))
    return 0


def cmd_verify_signature(args):
    try:
        integrity = verify_certificate(args.certificate)
        sig = verify_signature(args.certificate, args.signature, args.public_key)
        result = {"valid": bool(integrity["valid"] and sig["valid"]), "certificate_integrity": integrity, "signature": sig}
    except (OSError, json.JSONDecodeError, SignatureError, AssuranceError) as e:
        print(f"ERROR: {type(e).__name__}: {e}", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["valid"] else 1


def cmd_bundle(args):
    try:
        integrity = verify_certificate(args.certificate)
        if not integrity["valid"]:
            print(json.dumps(integrity, indent=2, sort_keys=True), file=sys.stderr)
            print("REJECT: refusing to bundle an invalid certificate", file=sys.stderr)
            return 2
        package_root = Path(args.certificate).resolve().parent
        normalized_dir = package_root / "normalized"
        if not normalized_dir.exists():
            write_normalized_set(args.certificate, normalized_dir)
        build_package_manifest(package_root)
        result = create_reproducible_bundle(args.certificate, args.output)
    except (OSError, json.JSONDecodeError, AssuranceError, PackageError, BundleSafetyError) as e:
        print(f"ERROR: {type(e).__name__}: {e}", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


def cmd_verify_bundle(args):
    try:
        result = verify_bundle(
            args.bundle,
            public_key=args.public_key,
            require_signature=args.require_signature,
            expected_signer_fingerprint=args.expected_signer_fingerprint,
            policy=args.policy,
        )
    except (OSError, json.JSONDecodeError, AssuranceError, SignatureError, BundleVerificationError, PolicyError) as e:
        print(f"ERROR: {type(e).__name__}: {e}", file=sys.stderr)
        return 2

    receipt_path = getattr(args, "receipt", None)
    if receipt_path:
        receipt = dict(result)
        out = Path(receipt_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        result = dict(result)
        result["receipt_written"] = str(out.resolve())

    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["valid"] else 1


def cmd_diff(args):
    try:
        result = diff_certificates(args.left, args.right)
    except (OSError, json.JSONDecodeError) as e:
        print(f"ERROR: {type(e).__name__}: {e}", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


def cmd_init(args):
    try:
        result = init_project(args.destination, template=args.template, subject=args.subject, force=args.force)
    except (OSError, ScaffoldError) as e:
        print(f"ERROR: {type(e).__name__}: {e}", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


def cmd_doctor(args):
    result = doctor()
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["healthy"] else 1


def cmd_attest(args):
    try:
        result = attest(
            args.manifest,
            args.output,
            private_key=args.private_key,
            public_key=args.public_key,
            bundle_path=args.bundle,
            intake_lock=args.intake_lock,
        )
    except (OSError, json.JSONDecodeError, AssuranceError, SignatureError, AttestationError) as e:
        print(f"ERROR: {type(e).__name__}: {e}", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


def cmd_freeze_intake(args):
    try:
        result = freeze_intake_file(args.input, args.output, overwrite=args.force)
    except (OSError, json.JSONDecodeError, PilotIntakeError) as e:
        print(f"ERROR: {type(e).__name__}: {e}", file=sys.stderr)
        return 2
    print(json.dumps({
        "wrote": str(Path(args.output).resolve()),
        "pilot_id": result["intake"]["pilot_id"],
        "intake_semantic_hash": result["intake_semantic_hash"],
        "frozen_at": result["frozen_at"],
    }, indent=2, sort_keys=True))
    return 0




def cmd_verify_normalized(args):
    try:
        from .jsonio import strict_json_load
        wire = strict_json_load(args.input)
        result = (
            verify_normalized_against_certificate(wire, args.certificate)
            if args.certificate
            else validate_normalized_wire(wire)
        )
    except (OSError, json.JSONDecodeError, StrictJSONError, NormalizationError) as e:
        print(f"ERROR: {type(e).__name__}: {e}", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["valid"] else 1


def cmd_normalize_decision(args):
    try:
        result = write_normalized_decision(
            args.certificate,
            args.claim,
            args.output,
        )
    except (OSError, json.JSONDecodeError, AssuranceError, NormalizationError) as e:
        print(f"ERROR: {type(e).__name__}: {e}", file=sys.stderr)
        return 2
    print(json.dumps({
        "wrote": str(Path(args.output).resolve()),
        "wire_format": result["wire_format"],
        "claim_id": result["claim"]["id"],
        "decision": result["decision"],
        "wire_semantic_hash": result["wire_semantic_hash"],
        "certificate_semantic_hash": result["source"]["certificate_semantic_hash"],
    }, indent=2, sort_keys=True))
    return 0

def cmd_snapshot_env(args):
    try:
        result = write_environment(args.output)
    except OSError as e:
        print(f"ERROR: {type(e).__name__}: {e}", file=sys.stderr)
        return 2
    print(json.dumps({"wrote": str(args.output), "semantic_hash": result["semantic_hash"], "packages": len(result["packages"])}, indent=2, sort_keys=True))
    return 0


def cmd_env_diff(args):
    try:
        result = diff_environment_files(args.left, args.right)
    except (OSError, json.JSONDecodeError, ValueError) as e:
        print(f"ERROR: {type(e).__name__}: {e}", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


def build_parser():
    p = argparse.ArgumentParser(prog="pcs", description="Proof-Carrying Science reference CLI")
    sub = p.add_subparsers(required=True)

    c = sub.add_parser("certify", help="run manifest checks and emit self-contained evidence package")
    c.add_argument("manifest")
    c.add_argument("-o", "--output", required=True)
    c.set_defaults(func=cmd_certify)

    v = sub.add_parser("verify", help="independently verify an evidence certificate/package")
    v.add_argument("certificate")
    v.set_defaults(func=cmd_verify)

    i = sub.add_parser("inspect", help="human-readable certificate summary")
    i.add_argument("certificate")
    i.set_defaults(func=cmd_inspect)

    h = sub.add_parser("hash", help="SHA-256 an artifact")
    h.add_argument("file")
    h.set_defaults(func=cmd_hash)

    im = sub.add_parser("impact", help="show claims/evidence invalidated if an artifact changes")
    im.add_argument("certificate")
    im.add_argument("--artifact", action="append", required=True, help="changed artifact id; repeatable")
    im.set_defaults(func=cmd_impact)

    r = sub.add_parser("report", help="render a human-readable HTML assurance report")
    r.add_argument("certificate")
    r.add_argument("-o", "--output", required=True)
    r.set_defaults(func=cmd_report)

    g = sub.add_parser("gate", help="CI gate: fail unless required claims have acceptable status")
    g.add_argument("certificate")
    g.add_argument("--claim", action="append", help="required claim id; default is all claims")
    g.add_argument("--accept", action="append", help="acceptable status; repeatable")
    g.set_defaults(func=cmd_gate)

    kg = sub.add_parser("keygen", help="generate an Ed25519 certificate-signing keypair")
    kg.add_argument("--private-key", required=True)
    kg.add_argument("--public-key", required=True)
    kg.add_argument("--force", action="store_true", help="explicitly replace existing key files")
    kg.set_defaults(func=cmd_keygen)

    s = sub.add_parser("sign", help="sign a valid certificate without modifying it")
    s.add_argument("certificate")
    s.add_argument("--private-key", required=True)
    s.add_argument("-o", "--output", required=True)
    s.set_defaults(func=cmd_sign)

    vs = sub.add_parser("verify-signature", help="verify certificate integrity and an Ed25519 signature record")
    vs.add_argument("certificate")
    vs.add_argument("--signature", required=True)
    vs.add_argument("--public-key", required=True)
    vs.set_defaults(func=cmd_verify_signature)

    b = sub.add_parser("bundle", help="create a deterministic ZIP of a valid evidence package")
    b.add_argument("certificate")
    b.add_argument("-o", "--output", required=True)
    b.set_defaults(func=cmd_bundle)

    vb = sub.add_parser("verify-bundle", help="safely unpack and independently verify a PCS evidence ZIP")
    vb.add_argument("bundle")
    vb.add_argument("--public-key", help="Ed25519 public key for signature verification")
    vb.add_argument("--require-signature", action="store_true", help="reject unsigned bundles")
    vb.add_argument("--expected-signer-fingerprint", help="pin the accepted Ed25519 public-key SHA-256 fingerprint")
    vb.add_argument("--policy", help="external reviewer acceptance-policy JSON")
    vb.add_argument("--receipt", help="write a JSON verification receipt for this exact bundle/policy invocation")
    vb.set_defaults(func=cmd_verify_bundle)

    d = sub.add_parser("diff", help="compare the scientific content of two certificates")
    d.add_argument("left")
    d.add_argument("right")
    d.set_defaults(func=cmd_diff)

    ini = sub.add_parser("init", help="create a bounded starter PCS project")
    ini.add_argument("destination")
    ini.add_argument("--template", default="pkpd", choices=["pkpd"])
    ini.add_argument("--subject")
    ini.add_argument("--force", action="store_true")
    ini.set_defaults(func=cmd_init)

    doc = sub.add_parser("doctor", help="check the local PCS runtime and reference adapter")
    doc.set_defaults(func=cmd_doctor)

    att = sub.add_parser("attest", help="certify, replay-verify, report, optionally sign, and bundle a manifest")
    att.add_argument("manifest")
    att.add_argument("-o", "--output", required=True, help="evidence output directory")
    att.add_argument("--private-key")
    att.add_argument("--public-key")
    att.add_argument("--bundle", help="output ZIP path; defaults to <output>.zip")
    att.add_argument("--intake-lock", help="frozen pilot intake lock; claim/assumption IDs must exactly match the certificate")
    att.set_defaults(func=cmd_attest)

    fi = sub.add_parser("freeze-intake", help="freeze a pre-result pilot claim/assumption inventory by semantic hash")
    fi.add_argument("input", help="pilot intake JSON")
    fi.add_argument("-o", "--output", required=True, help="write the timestamped intake lock JSON")
    fi.add_argument("--force", action="store_true", help="explicitly replace an existing intake lock")
    fi.set_defaults(func=cmd_freeze_intake)

    nd = sub.add_parser("normalize-decision", help="verify a certificate and export one claim-scoped normalized decision wire state")
    nd.add_argument("certificate")
    nd.add_argument("--claim", required=True, help="claim id to normalize")
    nd.add_argument("-o", "--output", required=True, help="write pcs-normalized-decision-v1 JSON")
    nd.set_defaults(func=cmd_normalize_decision)

    vn = sub.add_parser("verify-normalized", help="independently recompute a normalized decision wire state's invariants")
    vn.add_argument("input")
    vn.add_argument("--certificate", help="also require exact reproduction from this independently replay-verified source certificate")
    vn.set_defaults(func=cmd_verify_normalized)

    se = sub.add_parser("snapshot-env", help="write a deterministic, secrets-free runtime provenance snapshot")
    se.add_argument("-o", "--output", required=True)
    se.set_defaults(func=cmd_snapshot_env)

    ed = sub.add_parser("env-diff", help="compare two PCS runtime provenance snapshots")
    ed.add_argument("left")
    ed.add_argument("right")
    ed.set_defaults(func=cmd_env_diff)

    return p


def main():
    args = build_parser().parse_args()
    raise SystemExit(args.func(args))


if __name__ == "__main__":
    main()
