import tempfile
from pathlib import Path

import pytest

import pcs.attest as attest_module
from pcs.attest import attest, AttestationError
from pcs.scaffold import init_project
from pcs.signing import generate_keypair


def test_signed_attestation_requires_public_key():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        project = root / "project"
        init_project(project)
        private_key = root / "private.pem"
        public_key = root / "public.pem"
        generate_keypair(private_key, public_key)
        with pytest.raises(AttestationError, match="requires both private_key and public_key"):
            attest(project / "manifest.json", root / "evidence", private_key=private_key)


def test_attestation_rejects_final_bundle_that_fails_post_bundle_verification(monkeypatch):
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        project = root / "project"
        init_project(project)
        private_key = root / "private.pem"
        public_key = root / "public.pem"
        generate_keypair(private_key, public_key)

        real_verify = attest_module.verify_bundle

        def fail_final_verify(*args, **kwargs):
            result = real_verify(*args, **kwargs)
            result["valid"] = False
            result["errors"] = ["injected final-delivery failure"]
            return result

        monkeypatch.setattr(attest_module, "verify_bundle", fail_final_verify)
        with pytest.raises(AttestationError, match="final delivered bundle failed"):
            attest(
                project / "manifest.json",
                root / "evidence",
                private_key=private_key,
                public_key=public_key,
            )
