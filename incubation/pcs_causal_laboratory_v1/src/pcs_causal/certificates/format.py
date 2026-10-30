"""Narrow mathematical certificate language (not PCS production certificates).

Statistical estimates are intentionally excluded from mathematical certificates.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional


class CertificateKind(str, Enum):
    BACKDOOR_IDENTIFICATION = "backdoor_identification"
    FRONTDOOR_IDENTIFICATION = "frontdoor_identification"
    D_SEPARATION = "d_separation"
    NONIDENTIFIABILITY_WITNESS = "nonidentifiability_witness"
    EXPERIMENT_DISTINGUISHABILITY = "experiment_distinguishability"
    INTERVENTION_SEMANTICS = "intervention_semantics"


@dataclass
class CausalCertificate:
    version: str
    kind: CertificateKind
    claim: str
    assumptions: List[str]
    graph: Dict[str, Any]
    query: Dict[str, Any]
    payload: Dict[str, Any]
    producer_pass: Optional[bool] = None  # untrusted if present

    def to_dict(self) -> dict:
        return {
            "version": self.version,
            "kind": self.kind.value,
            "claim": self.claim,
            "assumptions": list(self.assumptions),
            "graph": self.graph,
            "query": self.query,
            "payload": self.payload,
            "producer_pass": self.producer_pass,
            "notice": (
                "producer_pass is untrusted; verifier must recompute. "
                "Mathematical acceptance ≠ scientific validation of assumptions."
            ),
        }

    def to_json(self, path: str | Path | None = None, indent: int = 2) -> str:
        text = json.dumps(self.to_dict(), indent=indent, sort_keys=True)
        if path is not None:
            Path(path).write_text(text)
        return text

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "CausalCertificate":
        return cls(
            version=str(data["version"]),
            kind=CertificateKind(data["kind"]),
            claim=str(data["claim"]),
            assumptions=list(data.get("assumptions", [])),
            graph=dict(data["graph"]),
            query=dict(data["query"]),
            payload=dict(data.get("payload", {})),
            producer_pass=data.get("producer_pass"),
        )

    @classmethod
    def from_json(cls, path: str | Path) -> "CausalCertificate":
        return cls.from_dict(json.loads(Path(path).read_text()))
