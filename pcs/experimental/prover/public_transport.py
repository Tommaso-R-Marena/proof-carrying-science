"""Bounded lossless proof results for the public runner's text log channel.

This codec does not grant proof authority. The receiver still requires exact
workflow provenance, immutable request binding and the independently checked
kernel receipt. Byte exhaustion carries no accepted proof.
"""
import base64
import gzip
import json

MARKER = "PCS_LEAN_RESULT_GZIP_V1:"
MAX_JSON_BYTES = 1_000_000
MAX_GZIP_BYTES = 48_000


def _bytes(value):
    return json.dumps(value, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _exhausted(response, reason):
    binding = {key: response[key] for key in (
        "format", "request_id", "source_sha256", "core_sha", "source_license",
        "automatic_training_authorization", "actions_sha256", "model_family"
    ) if key in response}
    return {**binding, "result": {"status": "resource_exhaustion", "reason": reason,
                                  "pcs_authority": False},
            "previous": None, "baseline": None}


def serialize_result(response,*,binding=None):
    """Emit exactly one line below 64 KiB; preserve eligible JSON losslessly."""
    raw = _bytes(response)
    if len(raw) > MAX_JSON_BYTES:
        raw = _bytes(_exhausted(binding or response, "public result exceeds 1 MB"))
    compressed = gzip.compress(raw, mtime=0)
    if len(compressed) > MAX_GZIP_BYTES:
        raw = _bytes(_exhausted(binding or response, "public compressed result exceeds 48 KB"))
        compressed = gzip.compress(raw, mtime=0)
    if len(raw) > MAX_JSON_BYTES or len(compressed) > MAX_GZIP_BYTES:
        raise ValueError("public binding metadata exceeds transport bounds")
    return MARKER + base64.b64encode(compressed).decode("ascii")
