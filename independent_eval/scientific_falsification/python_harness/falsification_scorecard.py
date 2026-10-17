"""Lattice-aligned falsification scorecard (inspection aid, non-authority).

Maps Workstream B campaign results into the same inspection_class vocabulary
used by the Assurance Card / reviewer workbench. Never issues ACCEPT/PASS.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .canonical_seal import seal_artifact
from .paths import RESULTS

SCORECARD_DISCLAIMER = (
    "Inspection aid only. computational PASS without empirical adequacy remains "
    "scientific_adequacy_open. This scorecard does not issue ACCEPT/PASS and "
    "does not certify science, clinical validity, or external-lab completion."
)


def build_scorecard(summary: dict[str, Any]) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []

    inad = summary.get("inadequacy") or {}
    rows.append(
        {
            "id": "SF-INADEQUACY",
            "surface": "inadequacy",
            "inspection_class": "scientific_adequacy_open",
            "evidence": {
                "example_count": inad.get("example_count"),
                "computational_pass_count": inad.get("computational_pass_count"),
                "empirical_adequacy_established_count": inad.get(
                    "empirical_adequacy_established_count"
                ),
            },
            "rationale": (
                "Examples are designed so computational support can hold while "
                "empirical adequacy remains unestablished."
            ),
        }
    )

    ext = summary.get("external_validity") or {}
    rows.append(
        {
            "id": "SF-EXTERNAL-VALIDITY",
            "surface": "external_validity",
            "inspection_class": (
                "scientific_adequacy_open"
                if not ext.get("empirical_adequacy_established")
                else "unknown_or_ambiguous"
            ),
            "evidence": {
                "completeness_score": ext.get("completeness_score"),
                "empirical_adequacy_established": ext.get(
                    "empirical_adequacy_established"
                ),
                "results_status": ext.get("results_status"),
            },
            "rationale": "Blank/protocol scoring never invents collected study results.",
        }
    )

    meta = summary.get("metamorphic") or {}
    meta_ok = (
        meta.get("cases_ok") == meta.get("case_count")
        and meta.get("case_count")
        and meta.get("oracles_all_passed_count") == meta.get("case_count")
    )
    rows.append(
        {
            "id": "SF-METAMORPHIC",
            "surface": "metamorphic",
            "inspection_class": (
                "computationally_supported" if meta_ok else "rejected_or_failed"
            ),
            "evidence": {
                "case_count": meta.get("case_count"),
                "cases_ok": meta.get("cases_ok"),
                "oracles_all_passed_count": meta.get("oracles_all_passed_count"),
            },
            "rationale": (
                "Metamorphic oracles are computational/transform checks, not "
                "empirical adequacy."
            ),
        }
    )

    casebook = summary.get("casebook_fixtures") or {}
    rows.append(
        {
            "id": "SF-CASEBOOK",
            "surface": "casebook_fixtures",
            "inspection_class": (
                "computationally_supported"
                if casebook.get("positives_ok") == casebook.get("case_count")
                and casebook.get("case_count")
                else "unknown_or_ambiguous"
            ),
            "evidence": casebook,
            "rationale": "Fixture certify/verify controls; not scientific truth.",
        }
    )

    aristotle = summary.get("aristotle_candidates") or {}
    rows.append(
        {
            "id": "SF-ARISTOTLE-CANDIDATES",
            "surface": "aristotle_candidates",
            "inspection_class": "scientific_adequacy_open",
            "evidence": {
                "candidate_count": aristotle.get("candidate_count"),
                "status": aristotle.get("status"),
                "empirical_adequacy_established_any": aristotle.get(
                    "empirical_adequacy_established_any"
                ),
            },
            "rationale": "Formalization candidates are proposals only.",
        }
    )

    counts: dict[str, int] = {}
    for row in rows:
        cls = row["inspection_class"]
        counts[cls] = counts.get(cls, 0) + 1

    payload = {
        "format": "pcs-independent-falsification-scorecard-v1",
        "issues_accept": False,
        "inspection_is_not_authority": True,
        "disclaimer": SCORECARD_DISCLAIMER,
        "rows": rows,
        "class_counts": counts,
        "non_claims": [
            "no clinical validity",
            "no external lab completion",
            "no merge recommendation",
            "computational PASS is not empirical adequacy",
        ],
    }
    return seal_artifact(payload)


def write_scorecard(
    summary: dict[str, Any] | None = None,
    path: Path | None = None,
) -> dict[str, Any]:
    RESULTS.mkdir(parents=True, exist_ok=True)
    if summary is None:
        summary_path = RESULTS / "SUMMARY.json"
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
    card = build_scorecard(summary)
    out = path or (RESULTS / "falsification_scorecard.json")
    out.write_text(json.dumps(card, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return card
