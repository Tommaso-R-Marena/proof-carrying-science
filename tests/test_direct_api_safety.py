import json
import tempfile
from pathlib import Path

import pytest

from pcs.kernel import build_certificate
from pcs.package import build_package_manifest, sign_package_manifest, PackageError
from pcs.signing import generate_keypair, sign_certificate, SignatureError


ROOT = Path(__file__).resolve().parents[1]
PKPD = ROOT / "examples" / "pkpd_one_compartment" / "manifest.json"


def test_direct_sign_certificate_refuses_invalid_certificate():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        evidence = root / "evidence"
        build_certificate(PKPD, evidence)
        cert = evidence / "certificate.json"
        obj = json.loads(cert.read_text(encoding="utf-8"))
        obj["subject"] = "tampered-without-rehash"
        cert.write_text(json.dumps(obj), encoding="utf-8")
        private = root / "private.pem"
        public = root / "public.pem"
        generate_keypair(private, public)
        with pytest.raises(SignatureError, match="refusing to sign invalid certificate"):
            sign_certificate(cert, private, root / "signature.json")


def test_direct_sign_package_manifest_refuses_stale_manifest():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        evidence = root / "evidence"
        build_certificate(PKPD, evidence)
        build_package_manifest(evidence)
        private = root / "private.pem"
        public = root / "public.pem"
        generate_keypair(private, public)
        (evidence / "unexpected.txt").write_text("not bound by manifest", encoding="utf-8")
        with pytest.raises(PackageError, match="does not match staged files"):
            sign_package_manifest(
                evidence / "package_manifest.json",
                private,
                evidence / "package_signature.json",
            )
