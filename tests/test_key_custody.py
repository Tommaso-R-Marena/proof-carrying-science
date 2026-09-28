import tempfile
from pathlib import Path

import pytest

from pcs.signing import generate_keypair, SignatureError


def test_keygen_refuses_overwrite_by_default():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        private = root / "private.pem"
        public = root / "public.pem"
        first = generate_keypair(private, public)
        private_before = private.read_bytes()
        public_before = public.read_bytes()
        with pytest.raises(SignatureError, match="refusing to overwrite"):
            generate_keypair(private, public)
        assert private.read_bytes() == private_before
        assert public.read_bytes() == public_before
        assert first["fingerprint"]


def test_keygen_allows_explicit_overwrite():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        private = root / "private.pem"
        public = root / "public.pem"
        first = generate_keypair(private, public)
        second = generate_keypair(private, public, overwrite=True)
        assert first["fingerprint"] != second["fingerprint"]


def test_keygen_rejects_same_private_and_public_path():
    with tempfile.TemporaryDirectory() as td:
        path = Path(td) / "same.pem"
        with pytest.raises(SignatureError, match="must be different"):
            generate_keypair(path, path)
