"""PGSI-style proof gate for formalization rulebooks (PGRA v1).

Python is a reference checker proved-by-tests. It never authorizes production
deployment. Digests use the PCS-PGRA-v1 prefix.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
from typing import Any, Mapping, Sequence

try:
    from .capability import CaseOutcome, CorpusReport, evaluate_corpus
except ImportError:  # flat sys.path research execution
    from capability import CaseOutcome, CorpusReport, evaluate_corpus

POLICY_VERSION = "pcs-pgra-v1/formalization-rulebook-gate"
DIGEST_PREFIX = b"PCS-PGRA-v1\0"

REQUIREMENTS = (
    "preserve_certified_outcomes",
    "expand_certified_capability",
    "strict_loss_decrease",
    "no_rule_removal",
)


def canonical(data: object) -> bytes:
    return json.dumps(
        data, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("ascii")


def digest(data: object) -> str:
    return hashlib.sha256(DIGEST_PREFIX + canonical(data)).hexdigest()


POLICY = {
    "version": POLICY_VERSION,
    "requirements": list(REQUIREMENTS),
    "pcs_scientific_authority": False,
    "automatic_deployment": False,
}
POLICY_HASH = digest(POLICY)


@dataclass(frozen=True)
class Decision:
    accepted: bool
    reason: str
    old_loss: int
    new_loss: int
    old_certified: tuple[str, ...]
    new_certified: tuple[str, ...]
    gained: tuple[str, ...]
    preserved: tuple[str, ...]
    old_rules: tuple[str, ...]
    new_rules: tuple[str, ...]
    pcs_scientific_authority: bool = False
    automatic_deployment: bool = False

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def _certified_map(report: CorpusReport) -> dict[str, CaseOutcome]:
    out: dict[str, CaseOutcome] = {}
    for item_id, outcome in report.outcomes.items():
        if outcome in {"certified_supported", "certified_abstain"}:
            out[item_id] = outcome
    return out


def accept(
    old_rules: frozenset[str],
    new_rules: frozenset[str],
    corpus: Sequence[Mapping[str, Any]],
) -> Decision:
    """Gate a monotonic rulebook proposal on a frozen corpus.

    Requires:
      (1) preserve: every id certified under old remains certified the same way
      (2) expand: at least one new certified capability not in old
      (3) strict_loss_decrease: loss(new) < loss(old)
      (4) no_rule_removal: old_rules ⊆ new_rules
    """
    old_report = evaluate_corpus(frozenset(old_rules), corpus)
    new_report = evaluate_corpus(frozenset(new_rules), corpus)
    old_cert = _certified_map(old_report)
    new_cert = _certified_map(new_report)

    old_rules_t = tuple(sorted(old_rules))
    new_rules_t = tuple(sorted(new_rules))
    old_certified_t = tuple(sorted(old_cert))
    new_certified_t = tuple(sorted(new_cert))

    if not old_rules <= new_rules:
        reason = "REJECT:rule_removal_forbidden"
    elif any(new_cert.get(i) != outcome for i, outcome in old_cert.items()):
        reason = "REJECT:certified_capability_regression"
    elif not (set(new_cert) - set(old_cert)):
        reason = "REJECT:no_new_certified_capability"
    elif not new_report.loss < old_report.loss:
        reason = "REJECT:loss_not_strictly_lower"
    else:
        reason = "ACCEPT:reference_only"

    gained = tuple(sorted(set(new_cert) - set(old_cert)))
    preserved = tuple(
        sorted(i for i, outcome in old_cert.items() if new_cert.get(i) == outcome)
    )
    return Decision(
        accepted=reason.startswith("ACCEPT"),
        reason=reason,
        old_loss=old_report.loss,
        new_loss=new_report.loss,
        old_certified=old_certified_t,
        new_certified=new_certified_t,
        gained=gained,
        preserved=preserved,
        old_rules=old_rules_t,
        new_rules=new_rules_t,
        pcs_scientific_authority=False,
        automatic_deployment=False,
    )


def check(old_rules: frozenset[str], new_rules: frozenset[str], corpus: Sequence[Mapping[str, Any]]) -> Decision:
    """Alias matching PGSI naming."""
    return accept(old_rules, new_rules, corpus)


def request(old_rules: frozenset[str], new_rules: frozenset[str]) -> dict[str, Any]:
    return {
        "policy_hash": POLICY_HASH,
        "old_rules": sorted(old_rules),
        "new_rules": sorted(new_rules),
        "pcs_scientific_authority": False,
        "automatic_deployment": False,
    }


__all__ = [
    "POLICY",
    "POLICY_HASH",
    "POLICY_VERSION",
    "REQUIREMENTS",
    "Decision",
    "accept",
    "check",
    "canonical",
    "digest",
    "request",
]
