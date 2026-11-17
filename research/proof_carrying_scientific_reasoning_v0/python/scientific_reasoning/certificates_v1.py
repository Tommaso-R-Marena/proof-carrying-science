"""Emit schema-v1 certificates with explicit step citations."""
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Dict, List, Sequence, Union

from .syntax import Authority, Context, Formula


@dataclass
class StepV1:
    id: int
    rule: str
    extras: Dict[str, Any]

    def to_json(self) -> dict:
        d = {"id": self.id, "rule": self.rule, **self.extras}
        return d


@dataclass
class CertificateV1:
    premises: list
    steps: List[StepV1]
    conclusion_step: int

    def to_json(self) -> dict:
        return {
            "schema_version": 1,
            "premises": [
                {
                    "id": p.id,
                    "formula": _formula_list(p.formula),
                    "declared_authority": p.authority.value
                    if isinstance(p.authority, Authority)
                    else p.authority,
                }
                for p in self.premises
            ],
            "steps": [s.to_json() for s in self.steps],
            "conclusion_step": self.conclusion_step,
        }

    def dumps(self) -> str:
        return json.dumps(self.to_json(), sort_keys=True, separators=(",", ":"))


def _formula_list(φ: Formula) -> list:
    if φ[0] == "atom":
        return ["atom", φ[1]]
    if φ[0] == "not":
        return ["not", _formula_list(φ[1])]  # type: ignore[index]
    if φ[0] == "and":
        return ["and", _formula_list(φ[1]), _formula_list(φ[2])]  # type: ignore[index]
    raise ValueError(φ)


class Builder:
    def __init__(self, Γ: Context):
        self.Γ = Γ
        self.steps: List[StepV1] = []

    def hyp(self, premise_id: int) -> int:
        i = len(self.steps)
        self.steps.append(StepV1(i, "hyp", {"premise_id": premise_id}))
        return i

    def and_i(self, left: int, right: int) -> int:
        i = len(self.steps)
        self.steps.append(StepV1(i, "andI", {"left": left, "right": right}))
        return i

    def and_e1(self, src: int) -> int:
        i = len(self.steps)
        self.steps.append(StepV1(i, "andE1", {"from": src}))
        return i

    def and_e2(self, src: int) -> int:
        i = len(self.steps)
        self.steps.append(StepV1(i, "andE2", {"from": src}))
        return i

    def finish(self, conclusion_step: int | None = None) -> CertificateV1:
        cstep = len(self.steps) - 1 if conclusion_step is None else conclusion_step
        return CertificateV1(list(self.Γ.premises), list(self.steps), cstep)
