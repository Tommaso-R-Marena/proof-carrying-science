from __future__ import annotations
from dataclasses import dataclass, field, asdict
from typing import Any, Literal

EvidenceOutcome = Literal["PASS", "FAIL", "UNVERIFIED"]
ClaimKind = Literal["formal", "computational", "empirical", "mixed"]


@dataclass(frozen=True)
class Assumption:
    id: str
    statement: str
    rationale: str = ""
    scope: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class Artifact:
    id: str
    path: str
    role: str
    sha256: str = ""
    media_type: str = "application/octet-stream"
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class Evidence:
    id: str
    kind: str
    claim_ids: list[str]
    outcome: EvidenceOutcome
    checker: str
    details: dict[str, Any] = field(default_factory=dict)
    artifact_ids: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class Claim:
    id: str
    statement: str
    kind: ClaimKind
    required_evidence: list[str] = field(default_factory=list)
    assumptions: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class WorkflowNode:
    id: str
    operation: str
    inputs: list[str] = field(default_factory=list)
    outputs: list[str] = field(default_factory=list)
    contract: dict[str, Any] = field(default_factory=dict)


def to_dict(x: Any) -> dict[str, Any]:
    return asdict(x)
