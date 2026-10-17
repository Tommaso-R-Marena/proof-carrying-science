"""Assurance Card builder CLI.

One command produces a reviewer-facing Assurance Card (JSON + static HTML):

  PYTHONPATH=independent_eval/assurance_card python3 -m python_harness.card \\
    --evidence PATH_OR_CERTIFICATE --out /tmp/pcs-assurance-card --format both
"""
from __future__ import annotations

import argparse
import json
import platform
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from .hashing import sha256_paths
from .html_render import LIMITATIONS_BANNER, render_assurance_card_html
from .inspect_lane import inspect_evidence
from .paths import find_certificate, package_root, repo_root, resolve_evidence_root
from .pcs_cli import run_pcs_verify

CARD_VERSION = "0.1.0"
_init = package_root() / "__init__.py"
if _init.is_file():
    for line in _init.read_text(encoding="utf-8").splitlines():
        if line.startswith("__version__"):
            CARD_VERSION = line.split("=", 1)[1].strip().strip("'\"")
            break

CARD_DISCLAIMER = (
    "This Assurance Card records a black-box pcs verify authority lane and a "
    "non-authority inspection lane. Computational PASS ≠ empirical adequacy. "
    "The card never certifies science, clinical validity, regulatory acceptance, "
    "external-lab completion, security proofs, or merge readiness. "
    "card_issues_accept=false; inspection_is_not_authority=true."
)

VALID_FORMATS = ("html", "json", "both")


def _git_head(cwd: Path | None) -> str | None:
    if cwd is None:
        return None
    try:
        proc = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if proc.returncode != 0:
        return None
    return (proc.stdout or "").strip() or None


def _cheap_tool_versions() -> dict[str, str | None]:
    versions: dict[str, str | None] = {
        "python": platform.python_version(),
        "platform": platform.platform(),
    }
    # Cheap pcs version probe — avoid heavy imports when possible.
    try:
        import pcs  # type: ignore

        versions["pcs"] = getattr(pcs, "__version__", None) or getattr(
            pcs, "VERSION", None
        )
        if versions["pcs"] is not None:
            versions["pcs"] = str(versions["pcs"])
    except Exception:
        versions["pcs"] = None
    return versions


def compare_lanes(
    *,
    authority: dict[str, Any],
    inspection: dict[str, Any],
) -> dict[str, Any]:
    """Observational consistency between authority ok and inspection classes.

    Never mutates inspection_class values.
    """
    reasons: list[str] = []
    if authority.get("skipped") or not authority.get("attempted"):
        return {
            "overall": "inconclusive",
            "reasons": [
                authority.get("skip_reason")
                or "Authority lane not completed; comparison inconclusive."
            ],
        }

    ok = authority.get("ok")
    classes = [c.get("inspection_class") for c in (inspection.get("claims") or [])]
    if ok is None:
        return {"overall": "inconclusive", "reasons": ["Authority ok is unknown."]}

    if ok is False:
        if any(c == "rejected_or_failed" for c in classes):
            reasons.append(
                "Authority verify failed and at least one claim is rejected_or_failed."
            )
            return {"overall": "agreement", "reasons": reasons}
        if any(c in ("computationally_supported", "cryptographic_validity") for c in classes):
            reasons.append(
                "Authority verify failed but inspection shows supported classes "
                "without rejection — disagreement (inspection not mutated)."
            )
            return {"overall": "disagreement", "reasons": reasons}
        reasons.append(
            "Authority verify failed; inspection classes are neither clearly "
            "rejected nor clearly supported — inconclusive."
        )
        return {"overall": "inconclusive", "reasons": reasons}

    # ok is True
    if any(c == "rejected_or_failed" for c in classes):
        reasons.append(
            "Authority verify succeeded but inspection has rejected_or_failed — "
            "disagreement (inspection not mutated)."
        )
        return {"overall": "disagreement", "reasons": reasons}
    reasons.append(
        "Authority verify succeeded; no inspection_class asserts rejection — "
        "agreement (observational)."
    )
    return {"overall": "agreement", "reasons": reasons}


def collect_provenance(
    *,
    inspected_paths: list[str],
) -> dict[str, Any]:
    root = repo_root()
    return {
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "git_head": _git_head(root),
        "repo_root": str(root) if root else None,
        "input_sha256": sha256_paths(inspected_paths),
        "python_version": platform.python_version(),
        "card_version": CARD_VERSION,
        "tool_versions": _cheap_tool_versions(),
        "efficiency": {
            "single_process": True,
            "network": False,
            "mathlib_rebuild": False,
            "lean_rebuild": False,
            "verify_only": True,
        },
    }


def build_assurance_card(
    evidence: str | Path,
    *,
    runner: Callable[..., subprocess.CompletedProcess[str]] | None = None,
    skip_verify: bool = False,
) -> dict[str, Any]:
    """Build the full Assurance Card dict for an evidence path."""
    root = resolve_evidence_root(evidence)
    inspection = inspect_evidence(evidence)
    cert = find_certificate(evidence) or find_certificate(root)

    if skip_verify or cert is None:
        from .pcs_cli import AuthorityLaneResult

        authority_obj = AuthorityLaneResult(
            certificate_path=str(cert) if cert else None,
            skipped=True,
            skip_reason=(
                "verify skipped by caller"
                if skip_verify
                else "no certificate found for authority lane"
            ),
        )
        authority = authority_obj.to_dict()
    else:
        authority = run_pcs_verify(cert, runner=runner).to_dict()

    inspected = list(inspection.get("source_paths") or [])
    if cert is not None and str(cert) not in inspected:
        inspected.append(str(cert))
    provenance = collect_provenance(inspected_paths=inspected)
    lane_consistency = compare_lanes(authority=authority, inspection=inspection)

    return {
        "format": "pcs-assurance-card-v1",
        "card_issues_accept": False,
        "inspection_is_not_authority": True,
        "disclaimer": CARD_DISCLAIMER,
        "limitations_banner": LIMITATIONS_BANNER,
        "authority": authority,
        "inspection": inspection,
        "provenance": provenance,
        "lane_consistency": lane_consistency,
        "non_claims": [
            "no clinical validity",
            "no external lab completion",
            "no security proof",
            "no merge recommendation",
            "computational PASS is not empirical adequacy",
        ],
    }


def _output_paths(out: str | Path, fmt: str) -> dict[str, Path]:
    """Resolve JSON/HTML output paths from an --out stem or explicit file."""
    out_path = Path(out)
    suffix = out_path.suffix.lower()
    paths: dict[str, Path] = {}
    if suffix == ".json":
        stem_html = out_path.with_suffix(".html")
        stem_json = out_path
    elif suffix in {".html", ".htm"}:
        stem_html = out_path
        stem_json = out_path.with_suffix(".json")
    else:
        stem_json = Path(str(out_path) + ".json")
        stem_html = Path(str(out_path) + ".html")
    if fmt in ("json", "both"):
        paths["json"] = stem_json
    if fmt in ("html", "both"):
        paths["html"] = stem_html
    return paths


def write_card(
    card: dict[str, Any],
    out: str | Path,
    *,
    fmt: str = "both",
) -> dict[str, Path]:
    """Write JSON and/or HTML Assurance Card artifacts."""
    if fmt not in VALID_FORMATS:
        raise ValueError(f"unsupported format {fmt!r}; expected one of {VALID_FORMATS}")

    targets = _output_paths(out, fmt)
    written: dict[str, Path] = {}
    if "json" in targets:
        json_path = targets["json"]
        json_path.parent.mkdir(parents=True, exist_ok=True)
        json_path.write_text(
            json.dumps(card, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        written["json"] = json_path
    if "html" in targets:
        html_path = targets["html"]
        html_path.parent.mkdir(parents=True, exist_ok=True)
        html_path.write_text(render_assurance_card_html(card), encoding="utf-8")
        written["html"] = html_path
    return written


def build_and_write(
    evidence: str | Path,
    out: str | Path,
    *,
    fmt: str = "both",
    runner: Callable[..., subprocess.CompletedProcess[str]] | None = None,
    skip_verify: bool = False,
) -> tuple[dict[str, Any], dict[str, Path]]:
    card = build_assurance_card(evidence, runner=runner, skip_verify=skip_verify)
    written = write_card(card, out, fmt=fmt)
    return card, written


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="python -m python_harness.card",
        description=(
            "Build an offline PCS Assurance Card (JSON + static HTML). "
            "Authority lane = black-box pcs verify; inspection lane is non-authority."
        ),
    )
    p.add_argument(
        "--evidence",
        required=True,
        help="Evidence directory or certificate.json path",
    )
    p.add_argument(
        "--out",
        required=True,
        help="Output path stem (writes .json / .html) or explicit file",
    )
    p.add_argument(
        "--format",
        choices=VALID_FORMATS,
        default="both",
        help="Output format (default: both)",
    )
    p.add_argument(
        "--skip-verify",
        action="store_true",
        help="Skip authority-lane pcs verify (inspection + provenance only)",
    )
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        card, written = build_and_write(
            args.evidence,
            args.out,
            fmt=args.format,
            skip_verify=bool(args.skip_verify),
        )
    except FileNotFoundError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    except Exception as exc:  # pragma: no cover - unexpected
        print(f"ERROR: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2

    for kind, path in written.items():
        print(f"WROTE_{kind.upper()} {path}")
    auth = card.get("authority") or {}
    print(
        f"AUTHORITY_OK {auth.get('ok')} RETURNCODE {auth.get('returncode')} "
        f"DURATION_S {auth.get('duration_seconds')}"
    )
    print(
        f"LANE_CONSISTENCY {(card.get('lane_consistency') or {}).get('overall')} "
        f"card_issues_accept=false inspection_is_not_authority=true"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
