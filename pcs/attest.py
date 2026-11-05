from __future__ import annotations

import shutil
import json
from pathlib import Path

from .bundle import create_reproducible_bundle
from .bundle_verify import verify_bundle
from .environment import snapshot_environment
from .kernel import build_certificate, verify_certificate
from .limitations import write_limitations
from .package import build_package_manifest, sign_package_manifest
from .report import write_html
from .signing import sign_certificate
from .intake import load_lock, assert_lock_matches_certificate, PilotIntakeError


class AttestationError(ValueError):
    pass


def attest(
    manifest: str | Path,
    output_dir: str | Path,
    *,
    private_key: str | Path | None = None,
    public_key: str | Path | None = None,
    bundle_path: str | Path | None = None,
    intake_lock: str | Path | None = None,
) -> dict[str, object]:
    if (private_key is None) != (public_key is None):
        raise AttestationError(
            "signed attestation requires both private_key and public_key so the delivered bundle can be immediately self-verified"
        )

    out = Path(output_dir).resolve()
    if out.exists():
        if not out.is_dir():
            raise AttestationError(f"attestation output is not a directory: {out}")
        if any(out.iterdir()):
            raise AttestationError(
                f"attestation output directory must be empty to prevent stale evidence contamination: {out}"
            )
    else:
        out.mkdir(parents=True, exist_ok=False)

    runtime = snapshot_environment()
    (out / "runtime.json").write_text(
        json.dumps(runtime, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    cert = build_certificate(manifest, out)
    cert_path = out / "certificate.json"
    verification = verify_certificate(cert_path)
    if not verification["valid"]:
        raise AttestationError(f"certificate failed independent replay: {verification['errors']}")
    report_path = write_html(cert, out / "report.html")
    limitations_path = write_limitations(cert, out / "LIMITATIONS.md")

    intake_lock_path = None
    if intake_lock is not None:
        try:
            lock = load_lock(intake_lock)
            assert_lock_matches_certificate(lock, cert)
        except PilotIntakeError as exc:
            raise AttestationError(str(exc)) from exc
        intake_lock_path = out / "pilot-intake-lock.json"
        intake_lock_path.write_text(
            json.dumps(lock, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

    # Fail closed if the runtime changed while checks/report generation were running.
    # This does not prove runtime correctness; it prevents an attestation from silently
    # spanning two different recorded execution environments.
    runtime_after = snapshot_environment()
    if runtime_after.get("semantic_hash") != runtime.get("semantic_hash"):
        raise AttestationError(
            "runtime environment changed during attestation; refusing to sign mixed-runtime evidence"
        )

    certificate_signature = None
    package_signature = None
    if private_key is not None:
        certificate_signature = sign_certificate(cert_path, private_key, out / "signature.json")
        shutil.copyfile(public_key, out / "signer-public.pem")

    package_manifest = build_package_manifest(out)
    if private_key is not None:
        package_signature = sign_package_manifest(out / "package_manifest.json", private_key, out / "package_signature.json")

    bundle_path = Path(bundle_path).resolve() if bundle_path is not None else out.with_suffix(".zip")
    bundle = create_reproducible_bundle(cert_path, bundle_path)

    # Verify the exact delivered archive from scratch after all report/signature/
    # manifest generation. This closes the gap between pre-bundle replay and the
    # bytes actually handed to a reviewer.
    expected_fingerprint = (package_signature or certificate_signature or {}).get("public_key_fingerprint")
    final_verification = verify_bundle(
        bundle_path,
        public_key=public_key,
        require_signature=bool(private_key is not None and public_key is not None),
        expected_signer_fingerprint=(expected_fingerprint if public_key is not None else None),
    )
    if not final_verification["valid"]:
        raise AttestationError(
            f"final delivered bundle failed independent verification: {final_verification['errors']}"
        )

    return {
        "certificate": str(cert_path),
        "semantic_hash": cert["semantic_hash"],
        "integrity_hash": cert["integrity_hash"],
        "claim_statuses": verification["claim_statuses"],
        "report": str(report_path),
        "limitations": str(limitations_path),
        "runtime": str(out / "runtime.json"),
        "runtime_semantic_hash": runtime["semantic_hash"],
        "pilot_intake_lock": str(intake_lock_path) if intake_lock_path is not None else None,
        "signed": certificate_signature is not None,
        "package_signed": package_signature is not None,
        "public_key_fingerprint": (package_signature or certificate_signature or {}).get("public_key_fingerprint"),
        "package_manifest": package_manifest,
        "bundle": bundle,
        "final_bundle_verification": final_verification,
    }
