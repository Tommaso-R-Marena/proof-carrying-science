"""Independent canonical ZIP (ZIP_STORED, sorted members, fixed DOS time).

Mirrors the PCS v0.6 contract documented in ``pcs.canonical_zip_v06`` without
importing that module, so this harness remains a black-box evaluator even when
PCS is unavailable.
"""

from __future__ import annotations

import io
import zipfile
from collections.abc import Mapping

FIXED_ZIP_TIME = (1980, 1, 1, 0, 0, 0)


def canonical_zip_bytes(members: Mapping[str, bytes]) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_STORED) as zf:
        for name in sorted(members):
            info = zipfile.ZipInfo(name, FIXED_ZIP_TIME)
            info.compress_type = zipfile.ZIP_STORED
            info.create_system = 3
            info.create_version = 20
            info.extract_version = 20
            info.flag_bits = 0
            info.external_attr = 0o100644 << 16
            info.internal_attr = 0
            info.extra = b""
            info.comment = b""
            zf.writestr(info, members[name], compress_type=zipfile.ZIP_STORED)
    return buf.getvalue()


def noncanonical_zip_bytes(members: Mapping[str, bytes], *, dos_time: tuple[int, ...] = (2024, 6, 15, 12, 0, 0)) -> bytes:
    """Build a ZIP with the same member bytes but a different DOS timestamp.

    Used to demonstrate that regenerated archives can differ from identical-archive
    replay even when semantic content matches.
    """
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_STORED) as zf:
        for name in sorted(members):
            info = zipfile.ZipInfo(name, dos_time)
            info.compress_type = zipfile.ZIP_STORED
            zf.writestr(info, members[name], compress_type=zipfile.ZIP_STORED)
    return buf.getvalue()


def read_zip_members(raw: bytes) -> dict[str, bytes]:
    out: dict[str, bytes] = {}
    with zipfile.ZipFile(io.BytesIO(raw), "r") as zf:
        for name in zf.namelist():
            out[name] = zf.read(name)
    return out
