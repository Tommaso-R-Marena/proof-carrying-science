"""Canonical PCS v0.6 ZIP (``ZIP_STORED``) encoding.

This is the exact archive subset written by ``pcs.bundle_v06`` and decoded by the Lean
authority's verified decoder (``formal/PCS/V2/Zip.lean``: ``encodeZip`` / ``decodeZip``,
``decodeZip_sound``). An archive whose bytes equal ``canonical_zip_bytes_v06`` of its own
members is verified by the Lean authority directly from the raw archive bytes
(``pcs-lean-authority --zip``); any other archive (DEFLATE, foreign writers, extra fields,
other member order, ...) is handled by the legacy, explicitly less-assured path in which
Python materialises the members for the authority.
"""
from __future__ import annotations

import io
import zipfile
from collections.abc import Mapping

FIXED_ZIP_TIME_V06 = (1980, 1, 1, 0, 0, 0)


def canonical_zip_bytes_v06(members: Mapping[str, bytes]) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_STORED) as zf:
        for name in sorted(members):
            info = zipfile.ZipInfo(name, FIXED_ZIP_TIME_V06)
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


def is_canonical_zip_v06(raw: bytes, members: Mapping[str, bytes]) -> bool:
    try:
        return canonical_zip_bytes_v06(members) == raw
    except (ValueError, zipfile.LargeZipFile):
        return False
