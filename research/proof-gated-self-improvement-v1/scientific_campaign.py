"""Frozen deterministic synthetic experiments; no recursive-intelligence claim.

Training sees only finite-gate feedback. Evaluation starting states are disjoint;
held-out input errors never select proposals or update the adaptive policy.
The modeled target remains known, synthetic and fixed, not external empirical data.
"""

from __future__ import annotations
from dataclasses import asdict
import argparse
import hashlib
import itertools
import json
from pathlib import Path
import random
import statistics
import subprocess
import tempfile
import time
from proof_gate import Model, check, wire_bytes, loss, target
from universal_relu import (
    Net,
    Term,
    single_neuron,
    universal_correctness_preserved,
    exact_interval_max_error,
    all_integer_equal,
    integer_cells,
)
from affine_certificates import certificate, verify
from pinned_authority import PinnedAuthority
from transactional_store import TransactionalStore
from promotion_v2 import canonical

HERE = Path(__file__).resolve().parent
TARGET = Net((Term(1, 2, 1),))
ARMS = ("weight", "bias", "joint", "activation", "restart")
SEED = 202610170117


def hash_data(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def heldout(m):
    return sum(
        abs(m.predict(x) - target(x)) for x in list(range(-40, -3)) + list(range(4, 41))
    )


def write(folder, name, obj):
    p = folder / name
    with p.open("x") as f:
        f.write(json.dumps(obj, sort_keys=True, indent=2) + "\n")
    return hashlib.sha256(p.read_bytes()).hexdigest()


def proposal(m, arm, rng, models):
    w, b, r = m.weight, m.bias, m.relu
    if arm == "weight":
        w += rng.choice((-1, 1))
    elif arm == "bias":
        b += rng.choice((-1, 1))
    elif arm == "joint":
        w += rng.choice((-1, 1))
        b += rng.choice((-1, 1))
    elif arm == "activation":
        r = not r
    else:
        return rng.choice(models)
    # Out-of-lattice proposals are explicit identities/rejections, not omitted.
    return Model(r, w, b) if -3 <= w <= 4 and -3 <= b <= 4 else m


def learn(models, starts, accepted):
    stats = [[1, 1] for _ in ARMS]
    proposed = 0
    for index in starts:
        rng = random.Random(SEED + index)
        current = models[index]
        for _ in range(24):
            if loss(current) == 0:
                break
            scores = [rng.betavariate(a, b) for a, b in stats]
            i = max(range(len(scores)), key=scores.__getitem__)
            candidate = proposal(current, ARMS[i], rng, models)
            ok = accepted[current, candidate]
            stats[i][0 if ok else 1] += 1
            proposed += 1
            if ok:
                current = candidate
    return {
        "beta_counts": stats,
        "training_proposals": proposed,
        "feedback": "Only original finite gate; no held-out scores/inputs",
        "policy_is_Lean_verified": False,
    }


def run_rollout(start, models, policy, weights, strategy, seed, budget=24):
    rng = random.Random(seed)
    current = start
    alpha = [list(v) for v in weights]
    events = []
    proposal_ns = verify_ns = 0
    for step in range(budget):
        if loss(current) == 0:
            break
        began = time.perf_counter_ns()
        if strategy == "local_coordinate":
            i = step % 3 if step % 3 < 2 else 3
        elif strategy == "random_model":
            i = 4
        elif strategy == "trained_online":
            i = max(range(5), key=lambda k: rng.betavariate(*alpha[k]))
        else:
            probabilities = (
                [a / (a + b) for a, b in alpha]
                if strategy in {"trained_frozen", "shuffled_credit"}
                else [1] * 5
            )
            i = rng.choices(range(5), weights=probabilities, k=1)[0]
        candidate = proposal(current, ARMS[i], rng, models)
        proposal_ns += time.perf_counter_ns() - began
        began = time.perf_counter_ns()
        ok = policy[current, candidate]
        verify_ns += time.perf_counter_ns() - began
        if strategy == "trained_online":
            alpha[i][0 if ok else 1] += 1
        events.append(
            {
                "old": wire_bytes(current).decode(),
                "candidate": wire_bytes(candidate).decode(),
                "arm": ARMS[i],
                "accepted": ok,
            }
        )
        if ok:
            current = candidate
    return {
        "proposed": len(events),
        "accepted": sum(e["accepted"] for e in events),
        "rejected": sum(not e["accepted"] for e in events),
        "final": asdict(current),
        "finite_loss_before": loss(start),
        "finite_loss_after": loss(current),
        "heldout_l1_before": heldout(start),
        "heldout_l1_after": heldout(current),
        "proposal_compute_ns": proposal_ns,
        "reference_policy_lookup_ns": verify_ns,
        "events": events,
        "more_than_one_accepted": sum(e["accepted"] for e in events) > 1,
    }


def run(bundle, output):
    output = Path(output).resolve()
    output.mkdir(mode=0o700, parents=False, exist_ok=False)
    models = [
        Model(r, w, b)
        for r, w, b in itertools.product((False, True), range(-3, 5), range(-3, 5))
    ]
    order = sorted(
        range(128),
        key=lambda i: hashlib.sha256(
            b"PGSI-START-SPLIT-v1" + wire_bytes(models[i])
        ).digest(),
    )
    train, test = order[:64], order[64:]
    sources = {
        str(p.relative_to(HERE)): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(HERE.glob("*.py"))
    }
    sources.update(
        {
            str(p.relative_to(HERE)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted((HERE / "authority").iterdir())
        }
    )
    protocol = {
        "format": "pgsi-prospective-synthetic-protocol-v1",
        "seed": SEED,
        "models": 128,
        "training_start_ids": train,
        "evaluation_start_ids": test,
        "evaluation_budget_per_rollout": 24,
        "policies": ["finite", "universal", "universal_window"],
        "strategies": [
            "local_coordinate",
            "random_model",
            "uniform_operators",
            "trained_frozen",
            "trained_online",
            "shuffled_credit",
        ],
        "heldout_inputs": list(range(-40, -3)) + list(range(4, 41)),
        "target": "relu(2*x+1)",
        "selection_uses_heldout_errors": False,
        "source_sha256": sources,
        "external_blind_validation": False,
        "universal_policies_know_the_entire_modeled_target": True,
        "heldout_scores_are_not_independent_scientific_evidence": True,
        "live_rollout_seeds": [SEED + 99999 + i for i in range(8)],
    }
    sources["ARISTOTLE_INTEGRATION_BOUNDARY.json"] = hashlib.sha256(
        (HERE / "ARISTOTLE_INTEGRATION_BOUNDARY.json").read_bytes()
    ).hexdigest()
    protocol_sha = write(
        output, "PROTOCOL.json", protocol
    )  # frozen BEFORE results/training
    authority = PinnedAuthority(Path(bundle))
    write(
        output,
        "NATIVE_AUTHORITY_MANIFEST.json",
        json.loads((Path(bundle) / "manifest.json").read_bytes()),
    )
    pairs = list(itertools.product(models, repeat=2))
    started = time.perf_counter()
    native = authority.transitions((wire_bytes(a), wire_bytes(b)) for a, b in pairs)
    native_seconds = time.perf_counter() - started
    finite = {}
    preserve = {}
    strong = {}
    violations = []
    strong_regressions = []
    counts = {
        "accepted": 0,
        "lost_correct": 0,
        "max_regression": 0,
        "both": 0,
        "passed_both": 0,
        "heldout_l1_regression": 0,
        "strong_but_heldout_l1_regression": 0,
    }
    enc = {m: single_neuron(m.relu, m.weight, m.bias) for m in models}
    maximum = {m: exact_interval_max_error(enc[m], TARGET, -20, 20)[0] for m in models}
    brute_max = {
        m: max(abs(m.predict(x) - target(x)) for x in range(-20, 21)) for m in models
    }
    brute_correct = {
        m: {x for x in range(-64, 65) if m.predict(x) == target(x)} for m in models
    }
    holdout = {m: heldout(m) for m in models}
    for (a, b), row in zip(pairs, native):
        expected = check(a, b).accepted
        if row != {"accepted": expected, "old_valid": True, "new_valid": True}:
            raise AssertionError("Python/native Lean finite-gate mismatch")
        finite[a, b] = expected
        if not expected:
            preserve[a, b] = strong[a, b] = False
            continue
        counts["accepted"] += 1
        d = universal_correctness_preserved(enc[a], enc[b], TARGET)
        lost = not d.passes
        regressed = maximum[b] > maximum[a]
        assert (
            d.passes == (brute_correct[a] <= brute_correct[b])
            and maximum[a] == brute_max[a]
            and maximum[b] == brute_max[b]
        )
        preserve[a, b] = not lost
        strong[a, b] = not lost and not regressed
        counts["lost_correct"] += lost
        counts["max_regression"] += regressed
        counts["both"] += lost and regressed
        counts["passed_both"] += strong[a, b]
        counts["heldout_l1_regression"] += holdout[b] > holdout[a]
        counts["strong_but_heldout_l1_regression"] += (
            strong[a, b] and holdout[b] > holdout[a]
        )
        if strong[a, b] and holdout[b] > holdout[a]:
            cert = certificate("preserves", (enc[a], enc[b], TARGET))
            checked = verify(cert, (enc[a], enc[b], TARGET), "preserves")
            original_holdout = list(range(-20, -3)) + list(range(4, 21))
            strong_regressions.append(
                {
                    "old": wire_bytes(a).decode(),
                    "candidate": wire_bytes(b).decode(),
                    "old_correct_integer_witness": checked[
                        "previously_correct_witness"
                    ],
                    "old_window_max_error": maximum[a],
                    "new_window_max_error": maximum[b],
                    "original_heldout_l1_before": sum(
                        abs(a.predict(x) - target(x)) for x in original_holdout
                    ),
                    "original_heldout_l1_after": sum(
                        abs(b.predict(x) - target(x)) for x in original_holdout
                    ),
                    "farther_heldout_l1_before": holdout[a],
                    "farther_heldout_l1_after": holdout[b],
                }
            )
        if lost or regressed:
            violations.append(
                {
                    "old": wire_bytes(a).decode(),
                    "candidate": wire_bytes(b).decode(),
                    "lost_correct_input": d.counterexample,
                    "old_window_max_error": maximum[a],
                    "new_window_max_error": maximum[b],
                }
            )
    assert [
        counts[k]
        for k in ["accepted", "lost_correct", "max_regression", "both", "passed_both"]
    ] == [4081, 76, 441, 12, 3576]
    write(output, "EXHAUSTIVE_COUNTEREXAMPLES.json", violations)
    write(output, "STRONG_GUARD_AGGREGATE_REGRESSIONS.json", strong_regressions)
    assert len(strong_regressions) == 46 and all(
        r["old_correct_integer_witness"] is None for r in strong_regressions
    )
    matrix_digest = hash_data([row["accepted"] for row in native])
    trained = learn(models, train, finite)
    write(output, "FROZEN_PROPOSAL_POLICY.json", trained)
    policies = {"finite": finite, "universal": preserve, "universal_window": strong}
    trials = []
    summary = []
    for name, policy in policies.items():
        for strategy in protocol["strategies"]:
            weights = trained["beta_counts"]
            if strategy == "shuffled_credit":
                weights = [weights[i] for i in [3, 4, 0, 1, 2]]
            group = []
            for index in test:
                result = run_rollout(
                    models[index],
                    models,
                    policy,
                    weights,
                    strategy,
                    SEED + 10000 + index,
                )
                result.update(policy=name, strategy=strategy, start_id=index)
                trials.append(result)
                group.append(result)
            summary.append(
                {
                    "policy": name,
                    "strategy": strategy,
                    "rollouts": len(group),
                    "proposed": sum(r["proposed"] for r in group),
                    "accepted": sum(r["accepted"] for r in group),
                    "rejected": sum(r["rejected"] for r in group),
                    "terminal_zero_loss": sum(
                        r["finite_loss_after"] == 0 for r in group
                    ),
                    "second_or_later_improvements": sum(
                        r["more_than_one_accepted"] for r in group
                    ),
                    "heldout_l1_improved": sum(
                        r["heldout_l1_after"] < r["heldout_l1_before"] for r in group
                    ),
                    "heldout_l1_worsened": sum(
                        r["heldout_l1_after"] > r["heldout_l1_before"] for r in group
                    ),
                    "no_accepted_update": sum(r["accepted"] == 0 for r in group),
                    "proposal_compute_ns": sum(r["proposal_compute_ns"] for r in group),
                    "reference_policy_lookup_ns": sum(
                        r["reference_policy_lookup_ns"] for r in group
                    ),
                }
            )
    write(output, "SEARCH_TRIALS.json", trials)
    # Multi-unit reference counterexample: A+B+window protection still fails on
    # a farther frozen domain, and a finite-perfect model cannot gain a new case.
    old = Net(())
    candidate = Net(TARGET.terms + (Term(10, 1, -21),))
    finite_points = tuple(range(-3, 4))
    old_correct = {x for x in finite_points if old.predict(x) == target(x)}
    new_correct = {x for x in finite_points if candidate.predict(x) == target(x)}
    assert old_correct < new_correct
    preservation = certificate("preserves", (old, candidate, TARGET))
    verify(preservation, (old, candidate, TARGET), "preserves")
    window = certificate("max_error", (candidate, TARGET), (-20, 20))
    verify(window, (candidate, TARGET), "max_error", (-20, 20))
    future = tuple(range(22, 33))
    old_error = sum(abs(old.predict(x) - target(x)) for x in future)
    new_error = sum(abs(candidate.predict(x) - target(x)) for x in future)
    assert (
        preservation["result"]["passes"]
        and window["result"]["max_error"] == 0
        and new_error > old_error
    )
    witness = {
        "mode": "Python multi-unit reference only, NOT authorized by PGSI1 Lean neuron gate",
        "candidate_model": {
            "terms": [[t.coefficient, t.weight, t.bias] for t in candidate.terms],
            "bias": candidate.bias,
        },
        "protected_window": [-20, 20],
        "finite_loss_before": 16,
        "finite_loss_after": 0,
        "universal_no_forgetting": True,
        "protected_max_error_after": 0,
        "far_domain": list(future),
        "far_l1_before": old_error,
        "far_l1_after": new_error,
        "far_x32_error_before": abs(old.predict(32) - target(32)),
        "far_x32_error_after": abs(candidate.predict(32) - target(32)),
        "perfect_corpus_can_gain_new_case": False,
        "correction_to_exact_target_blocked_by_new_case_requirement": True,
    }
    write(
        output,
        "FAR_DOMAIN_COUNTEREXAMPLE.json",
        {
            "witness": witness,
            "preservation_certificate": preservation,
            "window_certificate": window,
        },
    )
    scaling = []
    for width in [8, 32, 128, 512, 1024]:
        n = Net(
            tuple(
                Term((-1) ** i, (i % 5) + 1, -((i - width // 2) * ((i % 5) + 1)))
                for i in range(width)
            )
        )
        p = Net(tuple(reversed(n.terms)))
        times = []
        for _ in range(3):
            began = time.perf_counter_ns()
            assert all_integer_equal(n, p).passes
            times.append(time.perf_counter_ns() - began)
        began = time.perf_counter_ns()
        _, cells = integer_cells(n, p)
        assert all(n.affine(c.point()) == p.affine(c.point()) for c in cells)
        slow = time.perf_counter_ns() - began
        cert = certificate("equal", (n, p))
        began = time.perf_counter_ns()
        verify(cert, (n, p), "equal")
        replay = time.perf_counter_ns() - began
        scaling.append(
            {
                "width_each": width,
                "cells": len(cells),
                "sweep_median_ns": statistics.median(times),
                "retained_branch_scan_ns": slow,
                "independent_certificate_check_ns": replay,
                "scan_over_sweep_ratio": slow / statistics.median(times),
            }
        )
    # Prespecified batch includes every failed rollout, not a selected success.
    live = []
    live_trials = []
    for seed in protocol["live_rollout_seeds"]:
        rollout = run_rollout(
            Model(True, 0, 0),
            models,
            strong,
            trained["beta_counts"],
            "trained_online",
            seed,
            64,
        )
        actual = []
        with tempfile.TemporaryDirectory(prefix="pgsi-actual-adaptive-") as temp:
            store = TransactionalStore.initialize(
                Path(temp) / "state.sqlite", authority, Model(True, 0, 0)
            )
            head = store.audit()
            for i, event in enumerate(rollout["events"]):
                if not event["accepted"]:
                    continue
                assert store.load(expected=head).artifact == event["old"].encode(
                    "ascii"
                )
                raw = event["candidate"].encode("ascii")
                started = time.perf_counter_ns()
                head = store.promote(raw, head, f"{i + 1:032x}")
                wall = time.perf_counter_ns() - started
                snapshot = store.load(expected=head)
                record = {
                    "seed": seed,
                    "generation": head.generation,
                    "artifact_hex": snapshot.artifact.hex(),
                    "head": asdict(head),
                    "sample_predictions": list(snapshot.batch((-20, -3, 0, 3, 20))),
                    "promotion_wall_ns": wall,
                    "real_native_finite_authority": True,
                    "universal_guard_kernel_proved": False,
                }
                actual.append(record)
                live.append(record)
            assert store.audit() == head
        live_trials.append(
            {"seed": seed, "rollout": rollout, "actual_promotions": actual}
        )
    write(output, "LIVE_ADAPTIVE_PROMOTIONS.json", live_trials)
    obstructions = {}
    for name, policy in policies.items():
        blocked = []
        for m in models:
            neighbors = [
                Model(m.relu, m.weight + dw, m.bias + db)
                for dw, db in [(-1, 0), (1, 0), (0, -1), (0, 1)]
                if -3 <= m.weight + dw <= 4 and -3 <= m.bias + db <= 4
            ] + [Model(not m.relu, m.weight, m.bias)]
            if not any(policy[m, n] for n in neighbors) and any(
                policy[m, n] for n in models
            ):
                blocked.append(wire_bytes(m).decode())
        obstructions[name] = {
            "single_coordinate_dead_ends_with_available_larger_update": len(blocked),
            "models": blocked,
        }
    semantic = {
        "global_counts": counts,
        "matrix_sha256": matrix_digest,
        "proposal_policy": trained,
        "search_summary": [
            {k: v for k, v in r.items() if not k.endswith("_ns")} for r in summary
        ],
        "far_domain_witness": witness,
        "live_artifacts": [r["artifact_hex"] for r in live],
        "local_search_obstructions": obstructions,
    }
    result = {
        "format": "pgsi-hardening-scientific-campaign-v1",
        "protocol_sha256": protocol_sha,
        "source_sha256": sources,
        "native_authority_manifest_sha256": authority.manifest_sha256,
        "native_authority_binary_sha256": authority.binary_sha256,
        "native_gate_transitions_checked": len(pairs),
        "native_python_gate_mismatches": 0,
        "native_batch_wall_seconds": native_seconds,
        "global_counts": counts,
        "finite_bounded_brute_force_crosscheck": [-64, 64],
        "proposal_policy": trained,
        "search_summary": summary,
        "scaling": scaling,
        "far_domain_witness": witness,
        "actual_adaptive_promotions": len(live),
        "actual_live_rollouts": len(live_trials),
        "actual_live_rollouts_without_improvement": sum(
            not t["actual_promotions"] for t in live_trials
        ),
        "local_search_obstructions": obstructions,
        "strong_aggregate_regression_cases": len(strong_regressions),
        "strong_aggregate_regression_nonvacuous_old_correctness": sum(
            r["old_correct_integer_witness"] is not None for r in strong_regressions
        ),
        "semantic_results_sha256": hash_data(semantic),
        "kernel_proved_universal_analyzer": False,
        "native_execution_refinement_proved": False,
        "external_blind_empirical_validation": False,
        "accelerating_recursive_self_improvement_established": False,
        "all_training_from_this_synthetic_campaign": True,
        "untrusted_aristotle_traces_used_for_training": False,
    }
    write(output, "RESULTS.json", result)
    write(
        output,
        "SHA256.json",
        {
            p.name: hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(output.iterdir())
        },
    )
    return result


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--bundle", required=True, type=Path)
    p.add_argument("--output", required=True, type=Path)
    a = p.parse_args()
    r = run(a.bundle, a.output)
    print(
        json.dumps(
            {
                k: v
                for k, v in r.items()
                if k
                not in ["source_sha256", "search_summary", "scaling", "proposal_policy"]
            },
            indent=2,
            sort_keys=True,
        )
    )
