from __future__ import annotations
import hashlib
import zipfile
from pathlib import Path

FIXED_TIME = (1980, 1, 1, 0, 0, 0)
_PRIVATE_KEY_MARKERS = (
    b"-----BEGIN PRIVATE KEY-----",
    b"-----BEGIN ENCRYPTED PRIVATE KEY-----",
    b"-----BEGIN OPENSSH PRIVATE KEY-----",
    b"-----BEGIN RSA PRIVATE KEY-----",
    b"-----BEGIN EC PRIVATE KEY-----",
)


class BundleSafetyError(ValueError):
    pass


def _reject_private_key_material(path: Path) -> None:
    # Read only enough to identify standard PEM/OpenSSH key headers.
    prefix = path.read_bytes()[:8192]
    if any(marker in prefix for marker in _PRIVATE_KEY_MARKERS):
        raise BundleSafetyError(
            f"refusing to bundle apparent private-key material: {path.name}"
        )


def create_reproducible_bundle(certificate_path: str | Path, output_path: str | Path) -> dict[str, str | int]:
    certificate_path = Path(certificate_path).resolve()
    root = certificate_path.parent
    output_path = Path(output_path).resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    files = [p for p in root.rglob('*') if p.is_file() and p.resolve() != output_path]
    files.sort(key=lambda p: p.relative_to(root).as_posix())
    for p in files:
        _reject_private_key_material(p)
    # Use ZIP_STORED rather than DEFLATE. Compression heuristics can vary across
    # zlib/runtime versions; stored entries make archive bytes depend only on the
    # ordered file names, fixed metadata, and file bytes.
    with zipfile.ZipFile(output_path, "w", compression=zipfile.ZIP_STORED) as zf:
        for p in files:
            rel = p.relative_to(root).as_posix()
            info = zipfile.ZipInfo(rel, FIXED_TIME)
            info.compress_type = zipfile.ZIP_STORED
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            info.extra = b""
            info.comment = b""
            zf.writestr(info, p.read_bytes(), compress_type=zipfile.ZIP_STORED)
    h = hashlib.sha256(output_path.read_bytes()).hexdigest()
    return {"bundle": str(output_path), "sha256": h, "files": len(files), "archive_format": "zip-stored-v1"}
