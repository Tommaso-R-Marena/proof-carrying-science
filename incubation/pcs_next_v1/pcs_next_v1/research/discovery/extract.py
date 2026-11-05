"""Scientific dependency / obligation extraction (deterministic heuristics)."""

from __future__ import annotations

import re
from typing import Any

from ...translation.pog import ObligationNode, ProofObligationGraph
from ...core.statuses import AssuranceStatus

HYP = re.compile(r"(?i)\b(hypothesis|assume|assumption)\b[:\s]+(.+)")
CLAIM = re.compile(r"(?i)\b(we (show|prove|find|conclude)|therefore)\b[:\s]*(.+)")


def extract_from_markdown(text: str) -> ProofObligationGraph:
    g = ProofObligationGraph()
    assumptions = []
    for i, line in enumerate(text.splitlines()):
        m = HYP.search(line)
        if m:
            assumptions.append(m.group(2).strip())
        m = CLAIM.search(line)
        if m:
            oid = f"claim-{i}"
            g.add(
                ObligationNode(
                    id=oid,
                    claim=m.group(2).strip() if m.lastindex and m.lastindex >= 2 else m.group(0),
                    assumptions=list(assumptions),
                    method="deterministic_markdown_heuristic",
                    status=AssuranceStatus.OPEN,
                )
            )
    return g


def extract_report(text: str) -> dict[str, Any]:
    g = extract_from_markdown(text)
    return {
        "format": "pcs-next-discovery-extract-v1",
        "graph": g.to_dict() if g.nodes else {"format": "pcs-next-pog-v1", "nodes": {}, "edges": []},
        "note": "Extracted statements gain no authority merely by graph inclusion.",
    }
