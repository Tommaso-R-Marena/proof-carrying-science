"""Integrity checks for longitudinal / concentration tables."""

from __future__ import annotations

from collections import defaultdict
from typing import Any, Iterable

from ..core.statuses import AssuranceStatus, ClaimClass, status_record


def check_nonnegative_concentrations(
    values: Iterable[float],
    *,
    allow_zero: bool = False,
) -> dict[str, Any]:
    bad = []
    for i, v in enumerate(values):
        if v != v:  # NaN
            bad.append({"index": i, "value": v, "kind": "nan"})
        elif v < 0 or (not allow_zero and v == 0.0):
            bad.append({"index": i, "value": v, "kind": "nonpositive" if v == 0 else "negative"})
    if bad:
        return status_record(
            AssuranceStatus.REFUTED,
            claim_class=ClaimClass.TECHNICAL_VERIFICATION,
            reason=f"non-positive/NaN concentrations: {len(bad)}",
            evidence_ids=[f"row:{b['index']}" for b in bad[:5]],
            limitations=["Domain rule for this fragment; zeros may be valid in other assays."],
        )
    return status_record(
        AssuranceStatus.COMPUTATIONALLY_TESTED,
        claim_class=ClaimClass.TECHNICAL_VERIFICATION,
        reason="all concentrations finite and positive" if not allow_zero else "all concentrations finite and non-negative",
    )


def check_subject_time_integrity(
    rows: list[dict[str, Any]],
    *,
    id_key: str = "id",
    time_key: str = "time",
    min_delta: float = 1e-9,
    require_strictly_increasing: bool = True,
) -> dict[str, Any]:
    """Flag non-monotonic times, exact duplicates, and sub-min_delta jitter within subject.

    Tiny nonzero deltas (0 < |Δt| < min_delta) are treated as suspicious float/corruption
    artifacts rather than legitimate sampling grids.
    """
    by_id: dict[Any, list[float]] = defaultdict(list)
    for r in rows:
        by_id[r[id_key]].append(float(r[time_key]))

    findings: list[dict[str, Any]] = []
    for sid, times in by_id.items():
        for a, b in zip(times, times[1:]):
            d = b - a
            if d < 0:
                findings.append({"id": sid, "kind": "time_decrease", "t0": a, "t1": b})
            elif d == 0 and require_strictly_increasing:
                findings.append({"id": sid, "kind": "duplicate_time", "t": a})
            elif 0 < abs(d) < min_delta:
                findings.append({"id": sid, "kind": "sub_epsilon_jitter", "t0": a, "t1": b, "delta": d})
    if findings:
        return status_record(
            AssuranceStatus.REFUTED,
            claim_class=ClaimClass.TECHNICAL_VERIFICATION,
            reason=f"longitudinal time integrity failures: {len(findings)}",
            evidence_ids=[f"{f['kind']}@{f['id']}" for f in findings[:8]],
            assumptions=[f"min_delta={min_delta}", f"strictly_increasing={require_strictly_increasing}"],
            limitations=["Does not model legitimate replicate sampling at identical clock times."],
        )
    return status_record(
        AssuranceStatus.COMPUTATIONALLY_TESTED,
        claim_class=ClaimClass.TECHNICAL_VERIFICATION,
        reason="per-subject times monotonic without sub-epsilon jitter",
    )


def check_registered_group_params(
    observed_by_group: dict[str, dict[str, float]],
    registered_by_group: dict[str, dict[str, float]],
    *,
    rel_tol: float = 0.15,
) -> dict[str, Any]:
    """Detect semantic label swaps when fitted group parameters disagree with a registration.

    If labels are swapped, each group's fit will align with the *other* registered
    parameter set rather than its own.
    """
    if set(observed_by_group) != set(registered_by_group):
        return status_record(
            AssuranceStatus.UNSUPPORTED,
            claim_class=ClaimClass.TECHNICAL_VERIFICATION,
            reason="group key mismatch between observed and registered",
        )

    def rel_err(a: dict[str, float], b: dict[str, float]) -> float:
        keys = set(a) & set(b)
        if not keys:
            return float("inf")
        errs = []
        for k in keys:
            denom = max(abs(b[k]), 1e-12)
            errs.append(abs(a[k] - b[k]) / denom)
        return max(errs)

    own_ok = all(rel_err(observed_by_group[g], registered_by_group[g]) <= rel_tol for g in observed_by_group)
    if own_ok:
        return status_record(
            AssuranceStatus.COMPUTATIONALLY_TESTED,
            claim_class=ClaimClass.TECHNICAL_VERIFICATION,
            reason="fitted group parameters match registration",
        )

    # Cross-match: every observed group closer to a different registered group
    swapped = True
    for g, obs in observed_by_group.items():
        own = rel_err(obs, registered_by_group[g])
        others = [rel_err(obs, registered_by_group[h]) for h in registered_by_group if h != g]
        if not others or min(others) >= own:
            swapped = False
            break
    if swapped:
        return status_record(
            AssuranceStatus.REFUTED,
            claim_class=ClaimClass.TECHNICAL_VERIFICATION,
            reason="group labels appear swapped relative to registered parameters",
            assumptions=["Registration is authoritative for group semantics"],
            limitations=["Requires a prior registration of per-group parameters."],
        )
    return status_record(
        AssuranceStatus.CONDITIONAL,
        claim_class=ClaimClass.TECHNICAL_VERIFICATION,
        reason="group parameters disagree with registration but swap pattern inconclusive",
    )
