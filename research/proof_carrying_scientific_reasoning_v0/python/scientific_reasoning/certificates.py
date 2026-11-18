from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Sequence

from .evaluator import Judgment
from .syntax import Authority, Context, Formula


@dataclass(frozen=True)
class Certificate:
    premises: tuple
    steps: tuple
    final_support: tuple
    final_authority: str
    conclusion: Formula

    def to_json(self) -> dict:
        return {
            "premises": [
                {"id": p.id, "formula": p.formula, "authority": p.authority.value}
                for p in self.premises
            ],
            "steps": list(self.steps),
            "final_support": list(self.final_support),
            "final_authority": self.final_authority,
            "conclusion": self.conclusion,
        }

    def dumps(self) -> str:
        return json.dumps(self.to_json(), sort_keys=True, separators=(",", ":"))


def build_certificate(Γ: Context, steps: Sequence[Judgment]) -> Certificate:
    if not steps:
        raise ValueError("empty derivation")
    last = steps[-1]
    return Certificate(
        premises=tuple(Γ.premises),
        steps=tuple(
            {
                "rule": j.rule,
                "support": list(j.support),
                "authority": j.authority.value,
                "formula": j.formula,
            }
            for j in steps
        ),
        final_support=tuple(last.support),
        final_authority=last.authority.value,
        conclusion=last.formula,
    )
