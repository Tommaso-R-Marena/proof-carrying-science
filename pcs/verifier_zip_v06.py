from __future__ import annotations

import hashlib
import stat
import unicodedata
import zipfile
from pathlib import Path, PurePosixPath
from typing import Any

from .package_v06 import (
    MAX_PACKAGE_FILES_V06,
    MAX_PACKAGE_MEMBER_NAME_BYTES_V06,
    MAX_PACKAGE_SEGMENT_BYTES_V06,
    MAX_PACKAGE_SINGLE_FILE_V06,
    MAX_PACKAGE_TOTAL_BYTES_V06,
    V06PackageError,
    validate_package_namespace_v06,
)
from .verifier_io_v06 import (
    CONTROL_FILES_V06,
    V06VerifierIOError,
    load_public_key_v06,
)
from .verifier_v06 import verify_end_to_end_v06


MAX_ARCHIVE_ENTRIES_V06 = MAX_PACKAGE_FILES_V06 + 128
MAX_ARCHIVE_BYTES_V06 = 512 * 1024 * 1024
_ALLOWED_COMPRESSION_V06 = {zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED}
_WINDOWS_FORBIDDEN_V06 = set('<>:"|?*')
_WINDOWS_RESERVED_V06 = {
    "con", "prn", "aux", "nul",
    *(f"com{i}" for i in range(1, 10)),
    *(f"lpt{i}" for i in range(1, 10)),
}
_CONTROL_LIMITS_V06 = {
    "certificate_signature.json": 16 * 1024 * 1024,
    "package_manifest.json": 10 * 1024 * 1024,
    "package_signature.json": 16 * 1024 * 1024,
}
_PRIVATE_KEY_MARKERS_V06 = (
    b"-----BEGIN PRIVATE KEY-----",
    b"-----BEGIN ENCRYPTED PRIVATE KEY-----",
    b"-----BEGIN OPENSSH PRIVATE KEY-----",
    b"-----BEGIN RSA PRIVATE KEY-----",
    b"-----BEGIN EC PRIVATE KEY-----",
)


class V06BundleVerificationError(ValueError):
    pass


def _sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        while True:
            chunk = fh.read(1024 * 1024)
            if not chunk:
                return digest.hexdigest()
            digest.update(chunk)


def _validate_portable_archive_name(name: str, *, is_dir: bool) -> str:
    if not isinstance(name, str) or not name:
        raise V06BundleVerificationError("ZIP member name must be a non-empty string")
    if len(name.encode("utf-8")) > MAX_PACKAGE_MEMBER_NAME_BYTES_V06 + 1:
        raise V06BundleVerificationError(f"ZIP member name is too long: {name!r}")
    if "\\" in name:
        raise V06BundleVerificationError(f"ZIP member uses backslash: {name!r}")

    raw = name[:-1] if is_dir and name.endswith("/") else name
    path = PurePosixPath(raw)
    canonical = path.as_posix()
    expected = f"{canonical}/" if is_dir else canonical
    if (
        path.is_absolute()
        or canonical in ("", ".")
        or name != expected
        or any(part in ("", ".", "..") for part in path.parts)
    ):
        raise V06BundleVerificationError(f"unsafe or non-canonical ZIP member: {name!r}")

    for segment in path.parts:
        if len(segment.encode("utf-8")) > MAX_PACKAGE_SEGMENT_BYTES_V06:
            raise V06BundleVerificationError(
                f"ZIP member segment is too long: {segment!r}"
            )
        nfc = unicodedata.normalize("NFC", segment)
        if segment != nfc:
            raise V06BundleVerificationError(
                f"non-NFC ZIP member segment is not portable: {segment!r}"
            )
        if any(
            ord(ch) < 32 or ord(ch) == 127 or ch in _WINDOWS_FORBIDDEN_V06
            for ch in segment
        ):
            raise V06BundleVerificationError(
                f"ZIP member contains non-portable characters: {segment!r}"
            )
        if segment.endswith((" ", ".")):
            raise V06BundleVerificationError(
                f"ZIP member has non-portable trailing space/dot: {segment!r}"
            )
        stem = segment.split(".", 1)[0].rstrip(" .").casefold()
        if stem in _WINDOWS_RESERVED_V06:
            raise V06BundleVerificationError(
                f"ZIP member uses Windows-reserved filename: {segment!r}"
            )
    return canonical


def _portable_key(name: str) -> str:
    return "/".join(
        unicodedata.normalize("NFC", part).casefold()
        for part in PurePosixPath(name).parts
    )


def _validate_archive_namespace_v06(
    infos: list[zipfile.ZipInfo],
) -> dict[str, zipfile.ZipInfo]:
    if len(infos) > MAX_ARCHIVE_ENTRIES_V06:
        raise V06BundleVerificationError(
            f"v0.6 ZIP has too many entries: {len(infos)} > {MAX_ARCHIVE_ENTRIES_V06}"
        )

    kinds: dict[str, str] = {}
    portable: dict[str, str] = {}
    files: dict[str, zipfile.ZipInfo] = {}

    for info in infos:
        is_dir = info.is_dir()
        canonical = _validate_portable_archive_name(info.filename, is_dir=is_dir)

        key = _portable_key(canonical)
        other = portable.get(key)
        if other is not None and other != canonical:
            raise V06BundleVerificationError(
                f"cross-platform ZIP name collision: {other!r} vs {canonical!r}"
            )
        portable[key] = canonical

        if canonical in kinds:
            raise V06BundleVerificationError(
                f"duplicate or file/directory-colliding ZIP member: {info.filename!r}"
            )
        kinds[canonical] = "directory" if is_dir else "file"

        if is_dir:
            continue

        mode = (info.external_attr >> 16) & 0o170000
        if mode == stat.S_IFLNK:
            raise V06BundleVerificationError(
                f"symlink ZIP member is not allowed: {info.filename!r}"
            )
        if info.flag_bits & 0x1:
            raise V06BundleVerificationError(
                f"encrypted ZIP member is not allowed: {info.filename!r}"
            )
        if info.compress_type not in _ALLOWED_COMPRESSION_V06:
            raise V06BundleVerificationError(
                f"unsupported ZIP compression method for {info.filename!r}: "
                f"{info.compress_type}"
            )
        files[canonical] = info

    for canonical, kind in kinds.items():
        parts = PurePosixPath(canonical).parts
        for i in range(1, len(parts)):
            prefix = PurePosixPath(*parts[:i]).as_posix()
            if kinds.get(prefix) == "file":
                raise V06BundleVerificationError(
                    f"ZIP namespace collision: file {prefix!r} is parent of {canonical!r}"
                )

    required = {
        "certificate.json",
        "certificate_signature.json",
        "package_manifest.json",
        "package_signature.json",
    }
    missing = sorted(required - set(files))
    if missing:
        raise V06BundleVerificationError(
            f"v0.6 ZIP is missing required control files: {missing}"
        )

    signed_names = {
        name for name in files
        if name not in CONTROL_FILES_V06
    }
    if len(signed_names) > MAX_PACKAGE_FILES_V06:
        raise V06BundleVerificationError(
            f"v0.6 ZIP has too many signed package files: "
            f"{len(signed_names)} > {MAX_PACKAGE_FILES_V06}"
        )
    try:
        validate_package_namespace_v06({name: {} for name in signed_names})
    except V06PackageError as exc:
        raise V06BundleVerificationError(str(exc)) from exc

    return files


def _stream_member(
    zf: zipfile.ZipFile,
    info: zipfile.ZipInfo,
    *,
    max_bytes: int,
) -> bytes:
    if info.file_size > max_bytes:
        raise V06BundleVerificationError(
            f"ZIP member exceeds byte limit: {info.filename!r}: "
            f"{info.file_size} > {max_bytes}"
        )

    out = bytearray()
    try:
        with zf.open(info, "r") as fh:
            while True:
                chunk = fh.read(min(1024 * 1024, max_bytes + 1 - len(out)))
                if not chunk:
                    break
                out.extend(chunk)
                if len(out) > max_bytes:
                    raise V06BundleVerificationError(
                        f"ZIP member expands beyond byte limit: {info.filename!r}"
                    )
    except (zipfile.BadZipFile, RuntimeError, EOFError) as exc:
        raise V06BundleVerificationError(
            f"cannot safely read ZIP member {info.filename!r}: "
            f"{type(exc).__name__}: {exc}"
        ) from exc

    if len(out) != info.file_size:
        raise V06BundleVerificationError(
            f"ZIP member size metadata mismatch: {info.filename!r}: "
            f"declared={info.file_size} actual={len(out)}"
        )
    return bytes(out)


def load_package_zip_v06(bundle: str | Path) -> dict[str, Any]:
    """Read a v0.6 delivery ZIP without extracting it to the filesystem."""
    bundle_path = Path(bundle).resolve()
    if not bundle_path.is_file():
        raise V06BundleVerificationError(
            f"v0.6 bundle path is not a regular file: {bundle_path}"
        )
    if bundle_path.is_symlink():
        raise V06BundleVerificationError(
            f"refusing symlinked v0.6 bundle path: {bundle_path}"
        )
    archive_size = bundle_path.stat().st_size
    if archive_size > MAX_ARCHIVE_BYTES_V06:
        raise V06BundleVerificationError(
            f"v0.6 ZIP exceeds archive byte limit: "
            f"{archive_size} > {MAX_ARCHIVE_BYTES_V06}"
        )

    try:
        with zipfile.ZipFile(bundle_path, "r") as zf:
            files = _validate_archive_namespace_v06(zf.infolist())
            control: dict[str, bytes] = {}
            package_files: dict[str, bytes] = {}
            signed_total = 0

            for name, info in files.items():
                if name in CONTROL_FILES_V06:
                    raw = _stream_member(
                        zf,
                        info,
                        max_bytes=_CONTROL_LIMITS_V06[name],
                    )
                    control[name] = raw
                    continue

                raw = _stream_member(
                    zf,
                    info,
                    max_bytes=MAX_PACKAGE_SINGLE_FILE_V06,
                )
                signed_total += len(raw)
                if signed_total > MAX_PACKAGE_TOTAL_BYTES_V06:
                    raise V06BundleVerificationError(
                        "v0.6 ZIP exceeds total signed-package byte limit: "
                        f"{signed_total} > {MAX_PACKAGE_TOTAL_BYTES_V06}"
                    )
                if any(marker in raw for marker in _PRIVATE_KEY_MARKERS_V06):
                    raise V06BundleVerificationError(
                        f"refusing apparent private-key material in ZIP member: {name!r}"
                    )
                package_files[name] = raw

    except zipfile.BadZipFile as exc:
        raise V06BundleVerificationError(
            f"invalid v0.6 ZIP archive: {exc}"
        ) from exc
    except OSError as exc:
        raise V06BundleVerificationError(
            f"cannot read v0.6 ZIP archive: {type(exc).__name__}: {exc}"
        ) from exc

    return {
        "bundle_sha256": _sha256_path(bundle_path),
        "archive_bytes": archive_size,
        "certificate_bytes": package_files["certificate.json"],
        "certificate_signature_bytes": control["certificate_signature.json"],
        "package_manifest_bytes": control["package_manifest.json"],
        "package_signature_bytes": control["package_signature.json"],
        "package_files": package_files,
    }


def verify_package_zip_end_to_end_v06(
    bundle: str | Path,
    public_key_path: str | Path,
    *,
    expected_fingerprint: str | None = None,
) -> dict[str, Any]:
    loaded = load_package_zip_v06(bundle)
    public_key = load_public_key_v06(public_key_path)
    result = verify_end_to_end_v06(
        certificate_bytes=loaded["certificate_bytes"],
        certificate_signature_bytes=loaded["certificate_signature_bytes"],
        package_manifest_bytes=loaded["package_manifest_bytes"],
        package_signature_bytes=loaded["package_signature_bytes"],
        package_files=loaded["package_files"],
        public_key=public_key,
        expected_fingerprint=expected_fingerprint,
    )
    receipt = dict(result)
    receipt["bundle_sha256"] = loaded["bundle_sha256"]
    receipt["archive_bytes"] = loaded["archive_bytes"]
    receipt["archive_format"] = "zip"
    return receipt
