"""Exact versioned build identities; historical evidence is never rewritten.

The v2 configuration appends only new, separately named proof libraries to the
unchanged protected v1 configuration. Kernel/authority imports, toolchains,
locks, source bindings and the full original controls are still required.
"""
import hashlib
from pathlib import Path

BASELINE_SHA256 = "3aaad652ac3f4bebe37ed04781f3f2edf14e86e91fb947170b808cc737369fd9"
EXTENDED_SHA256 = "02b2b42963a7a12f29f07399cfcc018110f0ac8d7fe58beedd370ac3dacae4a6"
EXTENSION_SHA256 = "c4b7c076d75b0b1cb1895f7e9a2b28d5b4e865537dfa89b80f6851d157f94b0a"


def check_configuration(path: Path, expected: str) -> str:
    raw = path.read_bytes()
    actual = hashlib.sha256(raw).hexdigest()
    if actual == expected:
        return "exact_historical_configuration"
    if expected != BASELINE_SHA256 or actual != EXTENDED_SHA256:
        raise ValueError("Formal environment identity changed: lakefile.toml")
    baseline = Path(__file__).resolve().parents[1] / "research/formal-integration-phase-v1/baseline-lakefile.toml.txt"
    original = baseline.read_bytes()
    if hashlib.sha256(original).hexdigest() != BASELINE_SHA256 or not raw.startswith(original):
        raise ValueError("Historical build configuration was changed")
    if hashlib.sha256(raw[len(original):]).hexdigest() != EXTENSION_SHA256:
        raise ValueError("Unapproved appended formal libraries")
    return "exact_v2_extension_of_unchanged_historical_configuration"
