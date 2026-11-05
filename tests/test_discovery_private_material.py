import hashlib

import pytest
from cryptography.hazmat.primitives import serialization

from pcs.discover_v06 import discover_project_v06
from pcs.signing import generate_keypair


@pytest.mark.parametrize("prefix_length", [70000, 1024 * 1024 - 13])
def test_valid_private_key_after_prefix_and_across_chunk_is_never_inventoried(tmp_path, prefix_length):
    project = tmp_path / "project"
    project.mkdir()
    private, public = tmp_path / "private.pem", tmp_path / "public.pem"
    generate_keypair(private, public)
    raw = b"x" * prefix_length + b"\n" + private.read_bytes()
    # This is an actual loadable private key, not just a marker-shaped string.
    key = serialization.load_pem_private_key(raw, password=None)
    assert key is not None
    (project / "archival-notes.txt").write_bytes(raw)
    result = discover_project_v06(project, subject="Private-material publication regression")
    assert not any(item["path"] == "archival-notes.txt" for item in result["inventory"])
    assert {"path": "archival-notes.txt", "reason": "key-material-excluded"} in result["skipped"]


def test_nonsecret_large_source_keeps_exact_streamed_digest(tmp_path):
    raw = b"reviewed source\n" * 10000
    (tmp_path / "large-source.txt").write_bytes(raw)
    result = discover_project_v06(tmp_path, subject="Large public source")
    item = next(item for item in result["inventory"] if item["path"] == "large-source.txt")
    assert item["sha256"] == hashlib.sha256(raw).hexdigest()
    assert item["size"] == len(raw)
