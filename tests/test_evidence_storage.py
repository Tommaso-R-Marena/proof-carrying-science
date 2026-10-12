import gzip
import hashlib
import json

import pytest

from pcs.experimental.prover.evidence_storage import archive, exists, logical_paths, raw_bytes, read, verify_archive


def test_archive_preserves_exact_raw_bytes_and_can_resume_without_rerun(tmp_path):
    folder, backup = tmp_path / "published", tmp_path / "original"
    folder.mkdir()
    path = folder / "result.json"
    original = b'{"status": "unknown", "unicode": "\\u2200", "trailing": true}\n'
    path.write_bytes(original)
    report = archive(folder, backup)
    assert not path.exists() and exists(path)
    assert raw_bytes(path) == original == (backup / path.name).read_bytes()
    assert read(path)["status"] == "unknown"
    assert logical_paths(folder) == [path]
    assert report["records"][0]["raw_sha256"] == hashlib.sha256(original).hexdigest()
    assert report["result_values_changed"] is False
    assert verify_archive(folder, report)["verified"] == 1
    (folder / "result.json.gz").write_bytes(b"corrupted")
    with pytest.raises(ValueError, match="archive"):
        verify_archive(folder, report)
    with pytest.raises(ValueError, match="new directory"):
        archive(folder, backup)


def test_archive_is_deterministic_and_receiver_read_is_bounded(tmp_path):
    payload = json.dumps({"repeat": "x" * 10000}).encode()
    archived = []
    for suffix in ("a", "b"):
        folder = tmp_path / suffix
        folder.mkdir()
        (folder / "same.json").write_bytes(payload)
        archive(folder, tmp_path / (suffix + "-original"))
        archived.append((folder / "same.json.gz").read_bytes())
    assert archived[0] == archived[1]
    assert gzip.decompress(archived[0]) == payload
    with pytest.raises(ValueError, match="bounded"):
        raw_bytes(tmp_path / "a/same.json", max_bytes=100)
