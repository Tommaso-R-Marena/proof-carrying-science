"""Path resolution helpers for Assurance Card inputs."""
from __future__ import annotations

from pathlib import Path

CERT_NAMES = (
    "certificate.json",
    "pcs-certificate.json",
    "manifest.json",
)
RECEIPT_NAMES = (
    "verification-receipt.json",
    "receipt.json",
    "verification_receipt.json",
)
LIMITATIONS_NAMES = ("LIMITATIONS.md", "limitations.md")


def resolve_evidence_root(path: str | Path) -> Path:
    """Resolve an evidence directory or a certificate file path to a root dir."""
    p = Path(path).expanduser().resolve()
    if p.is_file():
        return p.parent
    if p.is_dir():
        return p
    raise FileNotFoundError(f"evidence path not found: {p}")


def find_named_file(root: Path, names: tuple[str, ...]) -> Path | None:
    """Find the first matching filename under root (direct, then rglob)."""
    root = Path(root).resolve()
    if not root.is_dir():
        return None
    for name in names:
        candidate = root / name
        if candidate.is_file():
            return candidate
    for name in names:
        matches = sorted(root.rglob(name))
        if matches:
            return matches[0]
    return None


def find_certificate(evidence: str | Path) -> Path | None:
    """Locate a certificate under an evidence directory, or return a cert file path."""
    p = Path(evidence).expanduser().resolve()
    if p.is_file() and p.name in CERT_NAMES:
        return p
    if p.is_file() and p.suffix.lower() == ".json":
        # Explicit certificate path (even if name is atypical).
        return p
    if p.is_dir():
        return find_named_file(p, CERT_NAMES)
    return None


def find_receipt(root: Path) -> Path | None:
    return find_named_file(root, RECEIPT_NAMES)


def find_limitations(root: Path) -> Path | None:
    return find_named_file(root, LIMITATIONS_NAMES)


def package_root() -> Path:
    """Return independent_eval/assurance_card/."""
    return Path(__file__).resolve().parents[1]


def repo_root() -> Path | None:
    """Best-effort repo root (directory containing .git), else None."""
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / ".git").exists():
            return parent
    return None
