"""Exact finite formalization capability certificate for PGRA v1.

Capability is measured only on a frozen discrete corpus under an explicit
rulebook. Outcomes are exact enums; loss is an exact non-negative integer.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable, Literal, Mapping, Sequence

from pcs.experimental.prover.ir import digest, theorem
from pcs.experimental.prover.language import formalize, parse_lean

try:
    from .grammar_extensions import RULE_CATALOG, RULE_IDS, apply_extensions
except ImportError:  # flat sys.path research execution
    from grammar_extensions import RULE_CATALOG, RULE_IDS, apply_extensions

CaseOutcome = Literal[
    "certified_supported",
    "certified_abstain",
    "unsupported_fail",
    "wrong_ir",
    "roundtrip_fail",
]

OUTCOMES: tuple[CaseOutcome, ...] = (
    "certified_supported",
    "certified_abstain",
    "unsupported_fail",
    "wrong_ir",
    "roundtrip_fail",
)

# Re-export catalog for discoverability alongside capability API.
__all__ = [
    "RULE_CATALOG",
    "RULE_IDS",
    "CaseOutcome",
    "OUTCOMES",
    "CaseResult",
    "CorpusReport",
    "formalize_with_rules",
    "evaluate_case",
    "evaluate_corpus",
    "loss_from_report",
]


@dataclass(frozen=True)
class CaseResult:
    outcome: CaseOutcome
    item_id: str
    ir_digest: str | None = None
    lean: str | None = None
    roundtrip_ok: bool = False
    status: str | None = None
    reason: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class CorpusReport:
    outcomes: dict[str, CaseOutcome]
    results: dict[str, CaseResult]
    certified_supported: frozenset[str]
    certified_abstain: frozenset[str]
    certified: frozenset[str]
    failed_supported: frozenset[str]
    failed_abstain: frozenset[str]
    wrong: frozenset[str]
    loss: int
    rules: frozenset[str]


def formalize_with_rules(source: str, rules: frozenset[str]) -> dict[str, Any]:
    """Local formalizer: base grammar plus optional rule-gated extensions."""
    known = frozenset(RULE_IDS)
    if not rules <= known:
        unknown = sorted(rules - known)
        raise ValueError(f"unknown formalization rules: {unknown}")

    extended = apply_extensions(source, rules)
    if extended is not None:
        return extended
    return formalize(source)


def _roundtrip(ir: Mapping[str, Any], lean: str) -> bool:
    try:
        parsed = parse_lean(lean)
        return digest(parsed) == digest(ir) and theorem(parsed) == lean
    except ValueError:
        return False


def evaluate_case(rules: frozenset[str], item: Mapping[str, Any]) -> CaseResult:
    """Evaluate one corpus item under a rulebook.

    Item fields:
      - id: str
      - english: str
      - target: "supported" | "abstain"
      - expected_ir_digest: optional str (when target is supported)
      - expected_lean: optional str
      - required_rules: optional sequence of rule ids that must be enabled
        for a supported target to be considered in-scope for this rulebook
    """
    item_id = str(item["id"])
    english = str(item["english"])
    target = item["target"]
    if target not in {"supported", "abstain"}:
        raise ValueError(f"invalid target for {item_id}: {target!r}")

    required = frozenset(item.get("required_rules") or ())
    result = formalize_with_rules(english, rules)
    status = result.get("status")

    if target == "abstain":
        if status == "unsupported" and not result.get("candidates"):
            return CaseResult(
                outcome="certified_abstain",
                item_id=item_id,
                status=status,
                reason=result.get("reason"),
                roundtrip_ok=True,
                metadata={"rules": sorted(rules)},
            )
        # Spurious support or ambiguous parse on an abstain target is wrong.
        return CaseResult(
            outcome="wrong_ir",
            item_id=item_id,
            status=status,
            reason="abstain target produced non-abstention formalization",
            metadata={"rules": sorted(rules)},
        )

    # target == supported
    if required and not required <= rules:
        return CaseResult(
            outcome="unsupported_fail",
            item_id=item_id,
            status=status if isinstance(status, str) else None,
            reason="required extension rules not enabled",
            metadata={"required_rules": sorted(required), "rules": sorted(rules)},
        )

    if status not in {"supported", "ambiguous"} or not result.get("candidates"):
        return CaseResult(
            outcome="unsupported_fail",
            item_id=item_id,
            status=status if isinstance(status, str) else None,
            reason=result.get("reason"),
            metadata={"rules": sorted(rules)},
        )

    candidate = result["candidates"][0]
    ir = candidate["ir"]
    lean = candidate["lean"]
    ir_digest = digest(ir)
    expected_digest = item.get("expected_ir_digest")
    expected_lean = item.get("expected_lean")

    if expected_digest is not None and ir_digest != expected_digest:
        return CaseResult(
            outcome="wrong_ir",
            item_id=item_id,
            ir_digest=ir_digest,
            lean=lean,
            status=status,
            reason="IR digest mismatch vs frozen expectation",
            metadata={"expected_ir_digest": expected_digest, "rules": sorted(rules)},
        )
    if expected_lean is not None and lean != expected_lean:
        return CaseResult(
            outcome="wrong_ir",
            item_id=item_id,
            ir_digest=ir_digest,
            lean=lean,
            status=status,
            reason="Lean mismatch vs frozen expectation",
            metadata={"expected_lean": expected_lean, "rules": sorted(rules)},
        )

    roundtrip_ok = _roundtrip(ir, lean)
    if not roundtrip_ok:
        return CaseResult(
            outcome="roundtrip_fail",
            item_id=item_id,
            ir_digest=ir_digest,
            lean=lean,
            status=status,
            roundtrip_ok=False,
            reason="parse_lean(lean) did not recover IR",
            metadata={"rules": sorted(rules)},
        )

    return CaseResult(
        outcome="certified_supported",
        item_id=item_id,
        ir_digest=ir_digest,
        lean=lean,
        status=status,
        roundtrip_ok=True,
        metadata={"rules": sorted(rules)},
    )


def evaluate_corpus(
    rules: frozenset[str],
    corpus: Sequence[Mapping[str, Any]],
) -> CorpusReport:
    """Evaluate a full corpus; loss is an exact integer."""
    results: dict[str, CaseResult] = {}
    outcomes: dict[str, CaseOutcome] = {}
    for item in corpus:
        case = evaluate_case(rules, item)
        results[case.item_id] = case
        outcomes[case.item_id] = case.outcome

    certified_supported = frozenset(
        i for i, o in outcomes.items() if o == "certified_supported"
    )
    certified_abstain = frozenset(
        i for i, o in outcomes.items() if o == "certified_abstain"
    )
    certified = certified_supported | certified_abstain

    failed_supported = frozenset(
        str(item["id"])
        for item in corpus
        if item["target"] == "supported"
        and outcomes[str(item["id"])] != "certified_supported"
    )
    failed_abstain = frozenset(
        str(item["id"])
        for item in corpus
        if item["target"] == "abstain"
        and outcomes[str(item["id"])] != "certified_abstain"
    )
    wrong = frozenset(
        i for i, o in outcomes.items() if o in {"wrong_ir", "roundtrip_fail"}
    )
    # Loss counts each failed target once via the three buckets; wrong items that
    # are also failed targets are still counted once in failed_* plus once in
    # wrong only when they are wrong_ir/roundtrip_fail — matching the PGRA spec:
    # Loss = (#failed_supported_targets) + (#failed_abstain_targets) + (#wrong)
    loss = len(failed_supported) + len(failed_abstain) + len(wrong)
    return CorpusReport(
        outcomes=outcomes,
        results=results,
        certified_supported=certified_supported,
        certified_abstain=certified_abstain,
        certified=certified,
        failed_supported=failed_supported,
        failed_abstain=failed_abstain,
        wrong=wrong,
        loss=loss,
        rules=frozenset(rules),
    )


def loss_from_report(report: CorpusReport) -> int:
    return report.loss


def freeze_expectations(
    corpus: Iterable[Mapping[str, Any]],
    rules: frozenset[str] | None = None,
) -> list[dict[str, Any]]:
    """Fill expected_ir_digest / expected_lean for supported items under full rules."""
    active = rules if rules is not None else frozenset(RULE_IDS)
    frozen: list[dict[str, Any]] = []
    for raw in corpus:
        item = dict(raw)
        if item["target"] == "supported":
            required = frozenset(item.get("required_rules") or ())
            case_rules = active if not required else required
            # Use all catalog rules so multi-rule sentences still resolve.
            result = formalize_with_rules(str(item["english"]), active)
            if result.get("status") not in {"supported", "ambiguous"} or not result.get(
                "candidates"
            ):
                raise RuntimeError(
                    f"cannot freeze supported item {item['id']}: {result.get('reason')}"
                )
            cand = result["candidates"][0]
            item["expected_ir_digest"] = digest(cand["ir"])
            item["expected_lean"] = cand["lean"]
            item["freeze_rules"] = sorted(case_rules if required else active)
        frozen.append(item)
    return frozen
