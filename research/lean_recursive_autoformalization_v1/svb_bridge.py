"""SVB-like scientific claim → PGRA formalization-obligation bridge.

Relation (non-superiority):
  * SVB is an independent diagnostic for what evidence establishes about a
    scientific conclusion (scope, abstention, false acceptance).
  * PCS/PGRA owns controlled-English formalization gates and proof-gated
    rulebook improvement on a frozen corpus.
  * This adapter only shows that a *few* scientific-claim strings can be
    rewritten into PGRA corpus items, or else recorded as explicit unsupported
    abstention. It does not import the SVB repository, does not claim SVB is a
    better formalization benchmark, and never confers PCS authority.

Expected sibling APIs (imported when present; local helpers otherwise):
  capability.formalize_with_rules(source, rules) -> dict
  capability.evaluate_corpus(rules, corpus) -> CorpusReport
      .loss: int
      .certified / .certified_supported / .certified_abstain: frozenset[str]
      .outcomes: dict[str, str]
  grammar_extensions.RULE_IDS / apply_extensions
  Corpus item schema:
      {id, english, target ∈ {supported,abstain}, required_rules?,
       expected_ir_digest?, expected_lean?, class?, split?}
"""
from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Mapping, Sequence

from pcs.experimental.prover.language import formalize as base_formalize

# ---------------------------------------------------------------------------
# Sibling imports with documented expected APIs + local fallbacks
# ---------------------------------------------------------------------------

_CAPABILITY_NOTE = (
    "Expected: research.lean_recursive_autoformalization_v1.capability "
    "exposing formalize_with_rules(source, rules) and evaluate_corpus(rules, corpus). "
    "Using self-contained helpers until that module imports cleanly."
)

try:
    from .grammar_extensions import RULE_IDS, apply_extensions  # type: ignore
except Exception:  # pragma: no cover - mid-flight sibling edits
    RULE_IDS = ()  # type: ignore
    apply_extensions = None  # type: ignore

try:
    from . import capability as _capability
except Exception:  # pragma: no cover
    _capability = None


def _formalize_with_rules(source: str, rules: frozenset[str]) -> dict[str, Any]:
    if _capability is not None and hasattr(_capability, "formalize_with_rules"):
        return _capability.formalize_with_rules(source, rules)
    # Local fallback mirroring capability.formalize_with_rules.
    if apply_extensions is not None and rules:
        known = frozenset(RULE_IDS)
        if not rules <= known:
            raise ValueError(f"unknown formalization rules: {sorted(rules - known)}")
        extended = apply_extensions(source, rules)
        if extended is not None:
            return extended
    return base_formalize(source)


def _evaluate_corpus(rules: frozenset[str], corpus: Sequence[Mapping[str, Any]]) -> Any:
    if _capability is not None and hasattr(_capability, "evaluate_corpus"):
        return _capability.evaluate_corpus(rules, corpus)
    # Minimal local scorer: supported iff formalize succeeds; abstain iff unsupported.
    outcomes: dict[str, str] = {}
    for item in corpus:
        item_id = str(item["id"])
        target = item["target"]
        result = _formalize_with_rules(str(item["english"]), rules)
        status = result.get("status")
        required = frozenset(item.get("required_rules") or ())
        if target == "abstain":
            outcomes[item_id] = (
                "certified_abstain"
                if status == "unsupported" and not result.get("candidates")
                else "wrong_ir"
            )
        elif required and not required <= rules:
            outcomes[item_id] = "unsupported_fail"
        elif status in {"supported", "ambiguous"} and result.get("candidates"):
            outcomes[item_id] = "certified_supported"
        else:
            outcomes[item_id] = "unsupported_fail"
    certified_supported = frozenset(
        i for i, o in outcomes.items() if o == "certified_supported"
    )
    certified_abstain = frozenset(
        i for i, o in outcomes.items() if o == "certified_abstain"
    )
    failed_supported = frozenset(
        str(it["id"])
        for it in corpus
        if it["target"] == "supported" and outcomes[str(it["id"])] != "certified_supported"
    )
    failed_abstain = frozenset(
        str(it["id"])
        for it in corpus
        if it["target"] == "abstain" and outcomes[str(it["id"])] != "certified_abstain"
    )
    wrong = frozenset(i for i, o in outcomes.items() if o in {"wrong_ir", "roundtrip_fail"})
    return _LocalReport(
        outcomes=outcomes,
        certified_supported=certified_supported,
        certified_abstain=certified_abstain,
        certified=certified_supported | certified_abstain,
        failed_supported=failed_supported,
        failed_abstain=failed_abstain,
        wrong=wrong,
        loss=len(failed_supported) + len(failed_abstain) + len(wrong),
        rules=frozenset(rules),
        note=_CAPABILITY_NOTE,
    )


@dataclass(frozen=True)
class _LocalReport:
    outcomes: dict[str, str]
    certified_supported: frozenset[str]
    certified_abstain: frozenset[str]
    certified: frozenset[str]
    failed_supported: frozenset[str]
    failed_abstain: frozenset[str]
    wrong: frozenset[str]
    loss: int
    rules: frozenset[str]
    note: str = ""


# ---------------------------------------------------------------------------
# Claim → obligation mapping
# ---------------------------------------------------------------------------

# Explicit rewrite table: SVB-like claim → controlled English obligation.
# Only finite, authored rewrites — not a general NL understanding claim.
_SUPPORTED_REWRITES: tuple[tuple[str, str, tuple[str, ...], str], ...] = (
    (
        r"(?i)under a finite\s+nat\s+model.*for every natural number\s+(\w+).*equality\s+\1\s*=\s*\1",
        "For all natural numbers {0}, {0} equals {0}.",
        (),
        "nat_identity_rewrite",
    ),
    (
        r"(?i)^for all natural numbers\s+(\w+),\s*\1\s+plus\s+0\s+equals\s+\1\.?$",
        "For all natural numbers {0}, {0} plus 0 equals {0}.",
        ("rule_plus_times_words",),
        "plus_zero_passthrough",
    ),
    (
        r"(?i)^for all natural numbers\s+(\w+),\s*\1\s+equals\s+\1\.?$",
        "For all natural numbers {0}, {0} equals {0}.",
        (),
        "nat_eq_passthrough",
    ),
    (
        r"(?i)^for all propositions\s+(\w+)\s+and\s+(\w+),\s*\1\s+exactly when\s+\2\.?$",
        "For all propositions {0} and {1}, {0} exactly when {1}.",
        ("rule_exactly_when",),
        "exactly_when_passthrough",
    ),
)

_ABSTAIN_PATTERNS: tuple[tuple[str, str], ...] = (
    (r"(?i)lean\s+verified|checked formal proof", "authority_or_proof_artifact_overclaim"),
    (r"(?i)nanomolar|micromolar|unit", "unit_or_physical_quantity_outside_pgra_grammar"),
    (r"(?i)iris|sepal|biological|empirical|assay|clinical", "empirical_or_biological_escalation"),
    (r"(?i)graph is connected|hausdorff|topology|real numbers", "unrestricted_math_outside_controlled_grammar"),
    (r"(?i)prove everything|beauty is truth", "non_mathematical_or_unrestricted_imperative"),
)


@dataclass(frozen=True)
class BridgeResult:
    claim_id: str
    claim: str
    status: str  # "mapped_supported" | "abstain"
    reason: str
    corpus_item: dict[str, Any] | None = None
    rewrite_rule: str | None = None
    pcs_authority: bool = False
    svb_superiority_claim: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def map_claim(claim: str, *, claim_id: str | None = None) -> BridgeResult:
    """Map one scientific-claim string to a PGRA corpus item or abstention."""
    if type(claim) is not str or not claim.strip():
        raise ValueError("claim must be a non-empty string")
    text = claim.strip()
    cid = claim_id or "claim"

    for pattern, template, required, rule_name in _SUPPORTED_REWRITES:
        match = re.search(pattern, text)
        if not match:
            continue
        english = template.format(*match.groups())
        item = {
            "id": f"svb_bridge_{cid}",
            "english": english,
            "target": "supported",
            "required_rules": list(required),
            "class": "svb_like_mapped",
            "split": "bridge",
            "source": "PCS authored SVB-like bridge (not SVB frozen tasks)",
            "license": "Apache-2.0",
        }
        return BridgeResult(
            claim_id=cid,
            claim=text,
            status="mapped_supported",
            reason="authored_rewrite_to_controlled_english",
            corpus_item=item,
            rewrite_rule=rule_name,
            metadata={"required_rules": list(required)},
        )

    for pattern, reason in _ABSTAIN_PATTERNS:
        if re.search(pattern, text):
            item = {
                "id": f"svb_bridge_{cid}",
                "english": text,
                "target": "abstain",
                "required_rules": [],
                "class": "svb_like_abstain",
                "split": "bridge",
                "source": "PCS authored SVB-like bridge (not SVB frozen tasks)",
                "license": "Apache-2.0",
            }
            return BridgeResult(
                claim_id=cid,
                claim=text,
                status="abstain",
                reason=reason,
                corpus_item=item,
                rewrite_rule=None,
            )

    # Default: fail closed — scientific claim outside authored bridge table.
    item = {
        "id": f"svb_bridge_{cid}",
        "english": text,
        "target": "abstain",
        "required_rules": [],
        "class": "svb_like_unsupported",
        "split": "bridge",
        "source": "PCS authored SVB-like bridge (not SVB frozen tasks)",
        "license": "Apache-2.0",
    }
    return BridgeResult(
        claim_id=cid,
        claim=text,
        status="abstain",
        reason="no_authored_rewrite_fail_closed",
        corpus_item=item,
    )


def map_claims(claims: Sequence[Mapping[str, Any]] | Sequence[str]) -> list[BridgeResult]:
    results: list[BridgeResult] = []
    for i, entry in enumerate(claims):
        if isinstance(entry, str):
            results.append(map_claim(entry, claim_id=f"anon_{i}"))
        else:
            results.append(
                map_claim(str(entry["claim"]), claim_id=str(entry.get("id", f"anon_{i}")))
            )
    return results


def score_autoformalization(
    claims: Sequence[Mapping[str, Any]] | Sequence[str],
    rules: frozenset[str] | None = None,
) -> dict[str, Any]:
    """Score mapped obligations under a rulebook; abstentions stay visible.

    This is a small capability probe for *autoformalization gating*, not an SVB
    system evaluation and not a claim that SVB is superior or inferior to PCS.
    """
    active = frozenset(rules or ())
    bridged = map_claims(claims)
    items = [b.corpus_item for b in bridged if b.corpus_item is not None]
    report = _evaluate_corpus(active, items)
    outcomes = getattr(report, "outcomes", {})
    return {
        "format": "pcs-pgra-svb-bridge-score-v1",
        "pcs_authority": False,
        "pcs_scientific_authority": False,
        "svb_superiority_claim": False,
        "automatic_deployment": False,
        "rules": sorted(active),
        "bridges": [b.as_dict() for b in bridged],
        "mapped_supported": sum(1 for b in bridged if b.status == "mapped_supported"),
        "abstentions": sum(1 for b in bridged if b.status == "abstain"),
        "capability_outcomes": dict(outcomes),
        "certified_count": len(getattr(report, "certified", ())),
        "loss": int(getattr(report, "loss", 0)),
        "capability_import": _capability is not None,
        "capability_note": None if _capability is not None else _CAPABILITY_NOTE,
        "scope": (
            "Bridge scores whether SVB-like claim strings become PGRA formalization "
            "obligations or explicit abstentions under a discrete rulebook. "
            "It does not evaluate SVB frozen tasks, biological validity, or PCS "
            "package authority."
        ),
    }


def load_fixture(path: Path | None = None) -> dict[str, Any]:
    fixture_path = Path(path) if path else Path(__file__).with_name("fixtures") / "svb_like_claims.json"
    return json.loads(fixture_path.read_text())


def score_fixture(rules: frozenset[str] | None = None, path: Path | None = None) -> dict[str, Any]:
    fixture = load_fixture(path)
    scored = score_autoformalization(fixture["claims"], rules=rules)
    scored["fixture_format"] = fixture.get("format")
    scored["fixture_note"] = fixture.get("note")
    return scored


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture", type=Path, default=None)
    parser.add_argument(
        "--rules",
        default="",
        help="Comma-separated rule ids (default: empty base-only)",
    )
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()
    rules = frozenset(r for r in args.rules.split(",") if r.strip())
    result = score_fixture(rules=rules, path=args.fixture)
    text = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text)
    print(text, end="")


if __name__ == "__main__":
    main()
