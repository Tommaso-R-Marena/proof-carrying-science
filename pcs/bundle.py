from __future__ import annotations
import hashlib
import zipfile
from pathlib import Path

FIXED_TIME = (1980, 1, 1, 0, 0, 0)
MAX_BUNDLE_FILES = 1000
MAX_BUNDLE_TOTAL_UNCOMPRESSED = 100 * 1024 * 1024
MAX_BUNDLE_SINGLE_FILE = 50 * 1024 * 1024
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
    # Stream the whole staged file so a concatenated/embedded PEM key cannot evade
    # a prefix-only scan. Preserve overlap so markers split across chunks are found.
    overlap = max(len(marker) for marker in _PRIVATE_KEY_MARKERS) - 1
    tail = b""
    with path.open("rb") as fh:
        while True:
            chunk = fh.read(1024 * 1024)
            if not chunk:
                break
            data = tail + chunk
            if any(marker in data for marker in _PRIVATE_KEY_MARKERS):
                raise BundleSafetyError(
                    f"refusing to bundle apparent private-key material: {path.name}"
                )
            tail = data[-overlap:] if overlap else b""


def create_reproducible_bundle(certificate_path: str | Path, output_path: str | Path) -> dict[str, str | int]:
    certificate_path = Path(certificate_path).resolve()
    root = certificate_path.parent
    output_path = Path(output_path).resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    staged = list(root.rglob("*"))
    symlinks = [p.relative_to(root).as_posix() for p in staged if p.is_symlink()]
    if symlinks:
        raise BundleSafetyError(f"refusing to bundle staged symlinks: {symlinks}")
    files = [p for p in staged if p.is_file() and p.resolve() != output_path]
    files.sort(key=lambda p: p.relative_to(root).as_posix())
    if len(files) > MAX_BUNDLE_FILES:
        raise BundleSafetyError(
            f"refusing to create bundle with too many files: {len(files)} > {MAX_BUNDLE_FILES}"
        )
    total = 0
    for p in files:
        size = p.stat().st_size
        if size > MAX_BUNDLE_SINGLE_FILE:
            raise BundleSafetyError(
                f"refusing to bundle oversized file {p.name!r}: {size} > {MAX_BUNDLE_SINGLE_FILE}"
            )
        total += size
        if total > MAX_BUNDLE_TOTAL_UNCOMPRESSED:
            raise BundleSafetyError(
                f"refusing to create bundle larger than {MAX_BUNDLE_TOTAL_UNCOMPRESSED} uncompressed bytes"
            )
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
