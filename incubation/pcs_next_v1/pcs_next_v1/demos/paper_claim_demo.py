"""Extract proof obligations from public paper blurbs (fixture text, not paywalled PDFs)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ..core.canonical import canonicalize
from ..core.statuses import AssuranceStatus, ClaimClass, status_record
from ..research.discovery.extract import extract_report
from ..translation.formalize import formalize_text
from .provenance import FIX

BLURB = FIX / "paper_abstracts" / "pinheiro_bates_theoph_blurb.txt"


def run_demo(out_dir: str | Path) -> dict[str, Any]:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    text = BLURB.read_text(encoding="utf-8")
    graph = extract_report(text)
    formalizations = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        # try deterministic formalize on each sentence-like line
        formalizations.append(formalize_text(f"line-{len(formalizations)}", line))
    report = {
        "format": "pcs-next-journal-demo-report-v1",
        "demo_id": "paper-blurb-claim-extraction",
        "citations": [
            "Fixture paraphrases publicly known Theoph modeling context from Pinheiro & Bates (2000) teaching material.",
        ],
        "source_fixture": str(BLURB.relative_to(FIX.parent.parent)),
        "extraction": graph,
        "formalizations": formalizations,
        "aggregate_status": status_record(
            AssuranceStatus.COMPUTATIONALLY_TESTED,
            claim_class=ClaimClass.TECHNICAL_VERIFICATION,
            reason="Deterministic obligation extraction + formalize pipeline executed on fixture blurb",
            limitations=[
                "Fixture text is not a verbatim copyrighted abstract",
                "Extracted claims gain no scientific authority by graph inclusion",
            ],
        ),
        "external_lab_validation": status_record(
            AssuranceStatus.OPEN,
            claim_class=ClaimClass.SCIENTIFIC_CLAIM,
            reason="No journal author participation.",
        ),
    }
    (out / "paper_claim_report.json").write_bytes(canonicalize(report) + b"\n")
    return report
