from __future__ import annotations

import shutil
from pathlib import Path

from .bundle import create_reproducible_bundle
from .kernel import build_certificate, verify_certificate
from .package import build_package_manifest, sign_package_manifest
from .report import write_html
from .signing import sign_certificate


class AttestationError(ValueError):
    pass


def attest(
    manifest: str | Path,
    output_dir: str | Path,
    *,
    private_key: str | Path | None = None,
    public_key: str | Path | None = None,
    bundle_path: str | Path | None = None,
) -> dict[str, object]:
    out = Path(output_dir).resolve()
    out.mkdir(parents=True, exist_ok=True)
    cert = build_certificate(manifest, out)
    cert_path = out / "certificate.json"
    verification = verify_certificate(cert_path)
    if not verification["valid"]:
        raise AttestationError(f"certificate failed independent replay: {verification['errors']}")
    report_path = write_html(cert, out / "report.html")

    certificate_signature = None
    package_signature = None
    if private_key is not None:
        certificate_signature = sign_certificate(cert_path, private_key, out / "signature.json")
        if public_key is not None:
            shutil.copyfile(public_key, out / "signer-public.pem")
    elif public_key is not None:
        raise AttestationError("public_key was provided without private_key")

    package_manifest = build_package_manifest(out)
    if private_key is not None:
        package_signature = sign_package_manifest(out / "package_manifest.json", private_key, out / "package_signature.json")

    bundle_path = Path(bundle_path).resolve() if bundle_path is not None else out.with_suffix(".zip")
    bundle = create_reproducible_bundle(cert_path, bundle_path)
    return {
        "certificate": str(cert_path),
        "semantic_hash": cert["semantic_hash"],
        "integrity_hash": cert["integrity_hash"],
        "claim_statuses": verification["claim_statuses"],
        "report": str(report_path),
        "signed": certificate_signature is not None,
        "package_signed": package_signature is not None,
        "public_key_fingerprint": (package_signature or certificate_signature or {}).get("public_key_fingerprint"),
        "package_manifest": package_manifest,
        "bundle": bundle,
    }
