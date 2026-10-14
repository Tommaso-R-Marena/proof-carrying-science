"""Exact versioned build identities; historical evidence is never rewritten.

The v2 configuration appends only new, separately named proof libraries to the
unchanged protected v1 configuration. Kernel/authority imports, toolchains,
locks, source bindings and the full original controls are still required.
"""
import hashlib
from pathlib import Path

BASELINE_SHA256 = "3aaad652ac3f4bebe37ed04781f3f2edf14e86e91fb947170b808cc737369fd9"
EXTENDED_SHA256 = "1180fda60bf5784fb347abc25f17534ba436c6e3cbc76860aca6747789394e36"
EXTENSION_SHA256 = "89d76fea4ad52031a0be9b10204ef89eec75892b85c7912c02fe900aed49e43f"


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
