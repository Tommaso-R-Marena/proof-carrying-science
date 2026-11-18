"""Run proof-carrying causal reasoning checks on controls and (optional) live models."""

from __future__ import annotations

import hashlib
import json
import time
from dataclasses import asdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

from research.proof_carrying_causal_reasoning_v1.kernel.certificate import (
    CausalClaim,
    CertificateVerdict,
    check_claim,
    parse_model_claim,
)
from research.proof_carrying_causal_reasoning_v1.kernel.backdoor import verify_backdoor_set
from research.proof_carrying_causal_reasoning_v1.tasks.battery import ALL_TASKS, Task, load_tasks
from research.proof_carrying_causal_reasoning_v1.programs.pipeline import build_program_tasks


PACKAGE = Path(__file__).resolve().parent


def all_research_tasks() -> Tuple[Task, ...]:
    return tuple(list(ALL_TASKS) + list(build_program_tasks()))


def check_task_claim(task: Task, claim: CausalClaim) -> CertificateVerdict:
    """Task-aware checker, including observed-only non-identifiability (T06)."""
    if task.task_id == "T06":
        return _check_t06(task, claim)
    return check_claim(
        claim,
        task.graph,
        task.scm,
        true_identifiable=task.identifiable,
        minimal_sets=task.minimal_sets(),
        allowed_strategies=task.allowed_strategies,
    )


def _check_t06(task: Task, claim: CausalClaim) -> CertificateVerdict:
    """U is unobserved; identification from {X,Y} alone is impossible."""
    observed = {"X", "Y"}
    # Force true_identifiable=False for observed-only queries.
    if claim.asserts_identifiable:
        # Even {U} is disallowed because U is not observed in the task.
        if claim.adjustment_set & (task.graph.nodes - observed):
            # Reuse standard path but mark as invalid for unobserved adjustment.
            base = check_claim(
                claim,
                task.graph,
                task.scm,
                true_identifiable=True,  # graph-level would allow {U}
                minimal_sets=task.minimal_sets(),
            )
            # Override: unobserved variables cannot be used.
            payload = base.to_dict()
            payload["accepted"] = False
            payload["verdict"] = "invalid_claim"
            payload["reasons"] = [
                "adjustment set uses unobserved variable(s); not available in observational data"
            ] + list(base.reasons)
            payload["ground_truth"]["identifiable_from_observed_only"] = False
            return _revive(payload)
        # Empty or observed-only set: not identifiable
        return check_claim(
            claim,
            task.graph,
            task.scm,
            true_identifiable=False,
            minimal_sets=[],
        )
    return check_claim(
        claim,
        task.graph,
        task.scm,
        true_identifiable=False,
        minimal_sets=[],
    )


def _revive(payload: dict) -> CertificateVerdict:
    from research.proof_carrying_causal_reasoning_v1.kernel.certificate import CertificateVerdict
    from research.proof_carrying_causal_reasoning_v1.kernel.backdoor import ASSUMPTIONS

    body = {
        "claim": payload["claim"],
        "accepted": payload["accepted"],
        "verdict": payload["verdict"],
        "reasons": payload["reasons"],
        "backdoor": payload.get("backdoor"),
        "frontdoor": payload.get("frontdoor"),
        "intervention": payload.get("intervention"),
        "ground_truth": payload["ground_truth"],
        "assumptions": list(ASSUMPTIONS),
        "epistemic_ceiling": "identified_under_assumptions_only",
    }
    digest = hashlib.sha256(
        json.dumps(body, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    return CertificateVerdict(
        task_id=payload["claim"]["task_id"],
        accepted=payload["accepted"],
        verdict=payload["verdict"],
        reasons=tuple(payload["reasons"]),
        backdoor=payload.get("backdoor"),
        frontdoor=payload.get("frontdoor"),
        intervention=payload.get("intervention"),
        ground_truth=payload["ground_truth"],
        claim=payload["claim"],
        assumptions=ASSUMPTIONS,
        certificate_sha256=digest,
        epistemic_ceiling="identified_under_assumptions_only",
    )


def run_controls(tasks: Optional[Sequence[Task]] = None) -> Dict[str, Any]:
    tasks = list(tasks) if tasks is not None else list(all_research_tasks())
    rows: List[dict] = []
    for task in tasks:
        for i, claim in enumerate(task.control_claims):
            verdict = check_task_claim(task, claim)
            rows.append(
                {
                    "task_id": task.task_id,
                    "control_index": i,
                    "expected_accept_pattern": _expected_control(task, i, claim),
                    "verdict": verdict.to_dict(),
                }
            )
    # Validate authored controls match expectations.
    mismatches = [
        r
        for r in rows
        if r["expected_accept_pattern"] is not None
        and r["verdict"]["accepted"] != r["expected_accept_pattern"]
    ]
    return {
        "kind": "control_suite",
        "n_tasks": len(tasks),
        "n_controls": len(rows),
        "n_mismatches": len(mismatches),
        "rows": rows,
        "mismatches": mismatches,
        "ok": len(mismatches) == 0,
    }


def _expected_control(task: Task, index: int, claim: CausalClaim) -> Optional[bool]:
    """First control is the correct one; subsequent are negative probes."""
    if index == 0:
        return True
    return False


def run_oracle_sanity(tasks: Optional[Sequence[Task]] = None) -> Dict[str, Any]:
    """For every identifiable task, backdoor estimate equals interventional truth."""
    tasks = list(tasks) if tasks is not None else list(all_research_tasks())
    rows = []
    for task in tasks:
        if task.task_id == "T06":
            # Observational-only: skip equality under full-graph adjustment with U.
            mins = task.minimal_sets()
            rows.append(
                {
                    "task_id": task.task_id,
                    "note": "observed-only non-identifiable; full-graph minimal sets require U",
                    "full_graph_minimal_sets": [sorted(s) for s in mins],
                    "ok": True,
                }
            )
            continue
        ok = True
        details = []
        truth = task.scm.interventional_expectation(
            task.outcome, {task.treatment: 1}
        )
        for adj in task.minimal_sets():
            bd = verify_backdoor_set(task.graph, task.treatment, task.outcome, adj)
            est = task.scm.backdoor_estimate(task.treatment, task.outcome, 1, adj)
            match = bd.valid and est is not None and est == truth
            ok = ok and match
            details.append(
                {
                    "criterion": "backdoor",
                    "adjustment_set": sorted(adj),
                    "backdoor_valid": bd.valid,
                    "estimate": None if est is None else f"{est}",
                    "truth": f"{truth}",
                    "match": match,
                }
            )
        if "frontdoor" in task.allowed_strategies:
            from research.proof_carrying_causal_reasoning_v1.kernel.frontdoor import (
                find_frontdoor_sets,
            )

            for fd in find_frontdoor_sets(task.graph, task.treatment, task.outcome):
                est = task.scm.frontdoor_estimate(
                    task.treatment, task.outcome, 1, fd.mediators
                )
                match = fd.valid and est is not None and est == truth
                ok = ok and match
                details.append(
                    {
                        "criterion": "frontdoor",
                        "mediators": sorted(fd.mediators),
                        "frontdoor_valid": fd.valid,
                        "estimate": None if est is None else f"{est}",
                        "truth": f"{truth}",
                        "match": match,
                    }
                )
        # Also confirm association≠effect where notes claim it for T01/T08.
        analysis = task.scm.analyze_effect(task.treatment, task.outcome)
        rows.append(
            {
                "task_id": task.task_id,
                "ok": ok,
                "details": details,
                "ate": f"{task.scm.ate(task.treatment, task.outcome)}",
                "association": (
                    None
                    if analysis.observational_association is None
                    else f"{analysis.observational_association}"
                ),
                "notes": list(analysis.notes),
            }
        )
    return {
        "kind": "oracle_sanity",
        "ok": all(r["ok"] for r in rows),
        "rows": rows,
    }


def write_results(out_dir: Path, payload: dict) -> Path:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / "results.json"
    if path.exists():
        raise FileExistsError(f"refusing to overwrite {path}")
    text = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    path.write_text(text)
    (out_dir / "results.sha256").write_text(
        hashlib.sha256(text.encode()).hexdigest() + "\n"
    )
    return path


def evaluate_model_responses(
    tasks: Sequence[Task],
    responses: Mapping[str, str],
) -> Dict[str, Any]:
    """Score model raw text responses keyed by task_id."""
    rows = []
    accepted = 0
    for task in tasks:
        raw = responses.get(task.task_id, "")
        claim = parse_model_claim(task.task_id, raw)
        verdict = check_task_claim(task, claim)
        if verdict.accepted:
            accepted += 1
        rows.append(
            {
                "task_id": task.task_id,
                "raw": raw,
                "claim": claim.to_dict(),
                "verdict": verdict.to_dict(),
            }
        )
    return {
        "kind": "model_evaluation",
        "n_tasks": len(tasks),
        "n_accepted": accepted,
        "accuracy": accepted / len(tasks) if tasks else 0.0,
        "rows": rows,
    }

