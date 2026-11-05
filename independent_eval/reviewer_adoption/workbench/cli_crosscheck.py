"""Observational CLI cross-check for workbench claim-strength inspection.

Runs black-box ``pcs verify <certificate>`` (or ``python -m pcs.cli verify``)
and compares the CLI outcome with ``inspect_evidence_dir`` results.

Authority: CLI / Lean path is authoritative. The workbench is inspection-only
and never mutates ``inspection_class`` based on this cross-check.
Never issues ACCEPT/PASS.
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Callable

from .inspect_evidence import EvidenceInspection, inspect_evidence_dir

CROSSCHECK_DISCLAIMER = (
    "CLI cross-check is observational only. "
    "cli_is_authority=true: the PCS CLI / Lean verification path is authority. "
    "The workbench inspection_class lattice is an inspection aid and is not mutated. "
    "workbench_issues_accept=false: this module never issues ACCEPT/PASS."
)

TAIL_CHARS = 4000
_CERT_NAMES = ("certificate.json", "pcs-certificate.json", "manifest.json")

# Demo / fixture formats that are not real attest packages.
_NON_ATTEST_FORMAT_MARKERS = (
    "fixture",
    "workbench",
    "synthetic",
    "demo",
)


@dataclass
class ClaimCrosscheck:
    claim_id: str
    inspection_class: str
    reported_status: str | None
    consistency: str  # agreement | disagreement | inconclusive
    reasons: list[str] = field(default_factory=list)


@dataclass
class CliCrosscheckResult:
    workbench_issues_accept: bool = False
    cli_is_authority: bool = True
    observational: bool = True
    disclaimer: str = CROSSCHECK_DISCLAIMER
    certificate_path: str | None = None
    cli_verify_attempted: bool = False
    cli_verify_ok: bool | None = None
    cli_returncode: int | None = None
    argv: list[str] | None = None
    stdout_tail: str = ""
    stderr_tail: str = ""
    cli_valid: bool | None = None
    cli_errors: list[str] = field(default_factory=list)
    overall_classification: str = "inconclusive"
    overall_reasons: list[str] = field(default_factory=list)
    claim_comparisons: list[ClaimCrosscheck] = field(default_factory=list)
    skipped: bool = False
    skip_reason: str | None = None

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["workbench_issues_accept"] = False
        d["cli_is_authority"] = True
        d["observational"] = True
        return d


def find_certificate(evidence_dir: str | Path) -> Path | None:
    """Locate certificate.json (or known aliases) under an evidence directory."""
    root = Path(evidence_dir).resolve()
    if not root.is_dir():
        return None
    for name in _CERT_NAMES:
        candidate = root / name
        if candidate.is_file():
            return candidate
    for name in _CERT_NAMES:
        matches = sorted(root.rglob(name))
        if matches:
            return matches[0]
    return None


def resolve_verify_argv(certificate: Path) -> list[str] | None:
    """Prefer ``pcs verify``; fall back to ``python -m pcs.cli verify``."""
    cert = str(Path(certificate).resolve())
    pcs_bin = shutil.which("pcs")
    if pcs_bin:
        return [pcs_bin, "verify", cert]
    # Module path available when running from repo with PYTHONPATH=.
    try:
        import pcs.cli  # noqa: F401
    except ImportError:
        return None
    return [sys.executable, "-m", "pcs.cli", "verify", cert]


def _tail(text: str, limit: int = TAIL_CHARS) -> str:
    if text is None:
        return ""
    if len(text) <= limit:
        return text
    return text[-limit:]


def _parse_cli_json(stdout: str) -> dict[str, Any] | None:
    text = (stdout or "").strip()
    if not text:
        return None
    # CLI prints a single JSON object; tolerate leading/trailing noise.
    start = text.find("{")
    end = text.rfind("}")
    if start < 0 or end <= start:
        return None
    try:
        data = json.loads(text[start : end + 1])
    except json.JSONDecodeError:
        return None
    return data if isinstance(data, dict) else None


def _looks_like_non_attest_package(certificate: Path, cli_errors: list[str]) -> bool:
    """Fixture / demo certificates are not real attest packages → inconclusive."""
    try:
        raw = json.loads(certificate.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        raw = {}
    fmt = str(raw.get("format") or "").lower()
    if any(m in fmt for m in _NON_ATTEST_FORMAT_MARKERS):
        return True
    # Schema failures listing required PCS fields strongly suggest non-attest input.
    blob = " ".join(cli_errors).lower()
    required_markers = (
        "spec_version",
        "checker_version",
        "json schema",
        "required property",
    )
    if sum(1 for m in required_markers if m in blob) >= 2:
        return True
    return False


def run_cli_verify(
    certificate: Path,
    *,
    runner: Callable[..., subprocess.CompletedProcess[str]] | None = None,
) -> tuple[list[str] | None, subprocess.CompletedProcess[str] | None, str | None]:
    """Execute black-box verify. Returns (argv, completed, skip_reason)."""
    argv = resolve_verify_argv(certificate)
    if argv is None:
        return None, None, "pcs CLI not available (neither `pcs` nor `pcs.cli` importable)"
    run = runner or subprocess.run
    completed = run(
        argv,
        capture_output=True,
        text=True,
        timeout=120,
    )
    return argv, completed, None


def _claim_consistency(
    *,
    claim_id: str,
    inspection_class: str,
    reported_status: str | None,
    cli_ok: bool | None,
    cli_attempted: bool,
    has_failure_warning: bool,
) -> ClaimCrosscheck:
    reasons: list[str] = []
    if not cli_attempted or cli_ok is None:
        return ClaimCrosscheck(
            claim_id=claim_id,
            inspection_class=inspection_class,
            reported_status=reported_status,
            consistency="inconclusive",
            reasons=["CLI verify was not completed; cannot compare."],
        )

    if cli_ok is False:
        # CLI is authority and reported failure: expect rejected_or_failed or a warning.
        if inspection_class == "rejected_or_failed":
            reasons.append(
                "CLI verify failed and inspection_class is rejected_or_failed — consistent."
            )
            return ClaimCrosscheck(
                claim_id=claim_id,
                inspection_class=inspection_class,
                reported_status=reported_status,
                consistency="agreement",
                reasons=reasons,
            )
        if has_failure_warning:
            reasons.append(
                "CLI verify failed; inspection_class is not rejected_or_failed, "
                "but workbench warnings acknowledge verification risk — soft agreement."
            )
            return ClaimCrosscheck(
                claim_id=claim_id,
                inspection_class=inspection_class,
                reported_status=reported_status,
                consistency="agreement",
                reasons=reasons,
            )
        if inspection_class in (
            "computationally_supported",
            "cryptographic_validity",
        ):
            reasons.append(
                "CLI verify failed (authority) but inspection_class="
                f"{inspection_class!r} suggests support without rejection — disagreement. "
                "inspection_class was not mutated."
            )
            return ClaimCrosscheck(
                claim_id=claim_id,
                inspection_class=inspection_class,
                reported_status=reported_status,
                consistency="disagreement",
                reasons=reasons,
            )
        reasons.append(
            f"CLI verify failed; inspection_class={inspection_class!r} is neither "
            "rejected_or_failed nor a clearly supported class — inconclusive."
        )
        return ClaimCrosscheck(
            claim_id=claim_id,
            inspection_class=inspection_class,
            reported_status=reported_status,
            consistency="inconclusive",
            reasons=reasons,
        )

    # CLI ok
    if inspection_class == "rejected_or_failed":
        reasons.append(
            "CLI verify succeeded but inspection_class is rejected_or_failed — disagreement. "
            "inspection_class was not mutated."
        )
        return ClaimCrosscheck(
            claim_id=claim_id,
            inspection_class=inspection_class,
            reported_status=reported_status,
            consistency="disagreement",
            reasons=reasons,
        )
    reasons.append(
        f"CLI verify succeeded; inspection_class={inspection_class!r} does not "
        "assert rejection — consistent with CLI success (observational)."
    )
    return ClaimCrosscheck(
        claim_id=claim_id,
        inspection_class=inspection_class,
        reported_status=reported_status,
        consistency="agreement",
        reasons=reasons,
    )


def _aggregate_overall(
    claim_comparisons: list[ClaimCrosscheck],
    *,
    cli_ok: bool | None,
    non_attest: bool,
    skip_reason: str | None,
) -> tuple[str, list[str]]:
    reasons: list[str] = []
    if skip_reason:
        return "inconclusive", [skip_reason]
    if non_attest:
        reasons.append(
            "Certificate appears to be a non-attest / fixture package; "
            "CLI outcome vs workbench lattice comparison is inconclusive "
            "(not a real attest verification subject)."
        )
        return "inconclusive", reasons
    if not claim_comparisons:
        reasons.append("No claims to compare.")
        return "inconclusive", reasons

    labels = {c.consistency for c in claim_comparisons}
    if "disagreement" in labels:
        reasons.append("At least one claim comparison is disagreement.")
        if cli_ok is False:
            reasons.append(
                "CLI (authority) failed while one or more inspection_class values "
                "did not reflect rejection or an explicit warning."
            )
        return "disagreement", reasons
    if labels == {"agreement"}:
        reasons.append("All claim comparisons agree with CLI outcome (observational).")
        return "agreement", reasons
    reasons.append("Mixed or incomplete claim comparisons → inconclusive.")
    return "inconclusive", reasons


def crosscheck_evidence_dir(
    evidence_dir: str | Path,
    *,
    inspection: EvidenceInspection | None = None,
    runner: Callable[..., subprocess.CompletedProcess[str]] | None = None,
) -> CliCrosscheckResult:
    """Run observational CLI cross-check against workbench inspection results."""
    root = Path(evidence_dir).resolve()
    result = CliCrosscheckResult()

    if inspection is None:
        try:
            inspection = inspect_evidence_dir(root)
        except FileNotFoundError as exc:
            result.overall_classification = "inconclusive"
            result.overall_reasons = [str(exc)]
            result.skipped = True
            result.skip_reason = str(exc)
            return result

    cert = find_certificate(root)
    if cert is None:
        result.overall_classification = "inconclusive"
        result.overall_reasons = ["No certificate.json found under evidence directory."]
        result.skipped = True
        result.skip_reason = result.overall_reasons[0]
        return result

    result.certificate_path = str(cert)

    try:
        argv, completed, skip_reason = run_cli_verify(cert, runner=runner)
    except subprocess.TimeoutExpired as exc:
        result.cli_verify_attempted = True
        result.cli_verify_ok = False
        result.argv = list(exc.cmd) if isinstance(exc.cmd, (list, tuple)) else [str(exc.cmd)]
        result.stdout_tail = _tail(exc.stdout or "")
        result.stderr_tail = _tail(exc.stderr or "")
        result.overall_classification = "inconclusive"
        result.overall_reasons = ["CLI verify timed out."]
        return result
    except OSError as exc:
        result.cli_verify_attempted = True
        result.cli_verify_ok = False
        result.overall_classification = "inconclusive"
        result.overall_reasons = [f"CLI verify OS error: {exc}"]
        result.skipped = True
        result.skip_reason = result.overall_reasons[0]
        return result

    if skip_reason or argv is None or completed is None:
        result.cli_verify_attempted = False
        result.skipped = True
        result.skip_reason = skip_reason or "pcs CLI unavailable"
        result.overall_classification = "inconclusive"
        result.overall_reasons = [result.skip_reason]
        return result

    result.cli_verify_attempted = True
    result.argv = argv
    result.cli_returncode = int(completed.returncode)
    result.stdout_tail = _tail(completed.stdout or "")
    result.stderr_tail = _tail(completed.stderr or "")

    parsed = _parse_cli_json(completed.stdout or "")
    if parsed is not None:
        result.cli_valid = bool(parsed.get("valid")) if "valid" in parsed else None
        errors = parsed.get("errors") or []
        if isinstance(errors, list):
            result.cli_errors = [str(e) for e in errors]
        elif errors:
            result.cli_errors = [str(errors)]

    # Authority outcome: prefer structured valid flag, else returncode.
    if result.cli_valid is not None:
        result.cli_verify_ok = result.cli_valid and completed.returncode == 0
    else:
        result.cli_verify_ok = completed.returncode == 0

    # Only count warnings that acknowledge CLI / verify failure — not the
    # generic "PCS authority remains external" disclaimer.
    has_failure_warning = any(
        (
            "cli verify" in w.lower()
            or "pcs verify" in w.lower()
            or "verification failed" in w.lower()
            or "verify failed" in w.lower()
            or "rejected_or_failed" in w.lower()
        )
        for w in (inspection.warnings or [])
    )

    for claim in inspection.claims:
        result.claim_comparisons.append(
            _claim_consistency(
                claim_id=claim.id,
                inspection_class=claim.inspection_class,
                reported_status=claim.reported_status,
                cli_ok=result.cli_verify_ok,
                cli_attempted=True,
                has_failure_warning=has_failure_warning,
            )
        )

    non_attest = False
    if result.cli_verify_ok is False:
        non_attest = _looks_like_non_attest_package(cert, result.cli_errors)

    overall, reasons = _aggregate_overall(
        result.claim_comparisons,
        cli_ok=result.cli_verify_ok,
        non_attest=non_attest,
        skip_reason=None,
    )
    result.overall_classification = overall
    result.overall_reasons = reasons
    result.overall_reasons.insert(
        0,
        f"CLI verify attempted argv={argv!r} returncode={completed.returncode} "
        f"cli_verify_ok={result.cli_verify_ok}.",
    )
    return result
