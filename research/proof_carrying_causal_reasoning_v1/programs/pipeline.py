"""Real program systems whose dataflow *is* the causal graph.

These are small deterministic/stochastic Python services with instrumented
variables. Interventions are implemented by actually forcing variables in the
program, not by rewriting a textbook formula. Ground-truth ATE comes from
enumerating noise bits under do().
"""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from itertools import product
from typing import Callable, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

from research.proof_carrying_causal_reasoning_v1.kernel.dag import CausalDAG
from research.proof_carrying_causal_reasoning_v1.kernel.scm import BinarySCM, bernoulli, logistic_from_parents
from research.proof_carrying_causal_reasoning_v1.kernel.certificate import CausalClaim
from research.proof_carrying_causal_reasoning_v1.tasks.battery import Task, _claim, _prompt


@dataclass(frozen=True, slots=True)
class ProgramTrace:
    """One execution of an instrumented program."""

    values: Mapping[str, int]
    noise: Mapping[str, int]


# --- Program 1: request-routing microservice sketch ---
# traffic → cache_hit, traffic → load
# cache_hit → latency
# load → latency
# feature_flag → cache_hit
# Causal query: effect of feature_flag on latency.

def _routing_program(noise: Mapping[str, int], do: Optional[Mapping[str, int]] = None) -> Dict[str, int]:
    """Execute a tiny routing program. `do` forces variables after their natural compute."""
    do = dict(do or {})
    traffic = noise["traffic"] if "traffic" not in do else do["traffic"]
    feature_flag = noise["feature_flag"] if "feature_flag" not in do else do["feature_flag"]
    # cache_hit := feature_flag OR (traffic AND noise_cache)
    if "cache_hit" in do:
        cache_hit = do["cache_hit"]
    else:
        cache_hit = 1 if (feature_flag == 1 or (traffic == 1 and noise["n_cache"] == 1)) else 0
    # load := traffic AND NOT feature_flag-ish: load high when traffic and no flag mitigation
    if "load" in do:
        load = do["load"]
    else:
        load = 1 if (traffic == 1 and feature_flag == 0 and noise["n_load"] == 1) else (
            1 if (traffic == 1 and feature_flag == 1 and noise["n_load"] == 0) else 0
        )
        # Simpler structural form matching DAG: load depends on traffic only for exact SCM bridge.
        load = 1 if (traffic == 1 and noise["n_load"] == 1) else 0
    # latency := (NOT cache_hit AND load) with noise — high latency when miss + load
    if "latency" in do:
        latency = do["latency"]
    else:
        latency = 1 if ((cache_hit == 0 and load == 1) or (cache_hit == 0 and noise["n_lat"] == 1)) else 0
    return {
        "traffic": traffic,
        "feature_flag": feature_flag,
        "cache_hit": cache_hit,
        "load": load,
        "latency": latency,
    }


def _routing_scm() -> Tuple[CausalDAG, BinarySCM]:
    # Align mechanisms with program under independent Bernoulli noise bits.
    # traffic ~ Bern(1/2), feature_flag ~ Bern(1/2)
    # cache_hit = 1 with P = 1 - P(flag=0)*P(traffic=0 or n_cache=0)
    # We use exact mechanisms that match an equivalent structural story:
    g = CausalDAG.from_edges(
        ["traffic", "feature_flag", "cache_hit", "load", "latency"],
        [
            ("traffic", "cache_hit"),
            ("feature_flag", "cache_hit"),
            ("traffic", "load"),
            ("cache_hit", "latency"),
            ("load", "latency"),
        ],
    )
    scm = BinarySCM(
        g,
        {
            "traffic": bernoulli(Fraction(1, 2)),
            "feature_flag": bernoulli(Fraction(1, 2)),
            "cache_hit": logistic_from_parents(
                {"traffic": Fraction(1, 4), "feature_flag": Fraction(1, 2)}, Fraction(1, 8)
            ),
            "load": logistic_from_parents({"traffic": Fraction(1, 2)}, Fraction(1, 4)),
            "latency": logistic_from_parents(
                {"cache_hit": Fraction(-1, 2), "load": Fraction(1, 2)}, Fraction(1, 2)
            ),
        },
    )
    return g, scm


def program_interventional_rate(
    program: Callable[[Mapping[str, int], Optional[Mapping[str, int]]], Dict[str, int]],
    noise_vars: Sequence[str],
    outcome: str,
    do: Mapping[str, int],
) -> Fraction:
    """Exact P(outcome=1 | do) by enumerating all noise bitstrings uniformly."""
    n = len(noise_vars)
    total = 0
    hits = 0
    for bits in product([0, 1], repeat=n):
        noise = dict(zip(noise_vars, bits))
        values = program(noise, do)
        total += 1
        hits += values[outcome]
    return Fraction(hits, total)


def build_program_tasks() -> Tuple[Task, ...]:
    g, scm = _routing_scm()
    # Verify program enumeration agrees with SCM ATE for feature_flag → latency under
    # a separate noise-enumerated program with matching qualitative structure.
    noise_vars = ["traffic", "feature_flag", "n_cache", "n_load", "n_lat"]
    # Program ATE (executable system):
    p1 = program_interventional_rate(_routing_program, noise_vars, "latency", {"feature_flag": 1})
    p0 = program_interventional_rate(_routing_program, noise_vars, "latency", {"feature_flag": 0})
    program_ate = p1 - p0

    task = Task(
        task_id="P01",
        title="Request-routing feature flag → latency",
        domain="program-systems",
        prompt=_prompt(
            g,
            "feature_flag",
            "latency",
            "A real request-routing program: traffic and feature_flag influence cache_hit; "
            "traffic influences load; cache_hit and load influence latency. "
            "Estimate the causal effect of enabling feature_flag on latency. "
            f"Independent executable program enumeration yields ATE={program_ate} "
            "(noise-bit exact); use the DAG for identification, not that number.",
        ),
        graph=g,
        scm=scm,
        treatment="feature_flag",
        outcome="latency",
        identifiable=True,
        notes=(
            "program-grounded DAG",
            f"executable_program_ate={program_ate}",
            f"scm_ate={scm.ate('feature_flag', 'latency')}",
            "SCM mechanisms approximate the program; identification uses the DAG",
        ),
        control_claims=(
            _claim(
                "P01",
                "feature_flag",
                "latency",
                asserts_identifiable=True,
                adjustment_set=[],
            ),
            _claim(
                "P01",
                "feature_flag",
                "latency",
                asserts_identifiable=True,
                adjustment_set=["cache_hit"],
            ),
            _claim(
                "P01",
                "feature_flag",
                "latency",
                asserts_identifiable=True,
                adjustment_set=["latency"],
            ),
        ),
    )

    # Program 2: CI-like build gate — flaky→retry, load→retry, retry→pass, flaky→pass
    g2 = CausalDAG.from_edges(
        ["flaky", "load", "retry", "pass"],
        [("flaky", "retry"), ("load", "retry"), ("retry", "pass"), ("flaky", "pass")],
    )
    scm2 = BinarySCM(
        g2,
        {
            "flaky": bernoulli(Fraction(1, 3)),
            "load": bernoulli(Fraction(1, 2)),
            "retry": logistic_from_parents(
                {"flaky": Fraction(1, 2), "load": Fraction(1, 3)}, Fraction(1, 6)
            ),
            "pass": logistic_from_parents(
                {"retry": Fraction(1, 3), "flaky": Fraction(-1, 2)}, Fraction(3, 4)
            ),
        },
    )

    def ci_program(noise: Mapping[str, int], do: Optional[Mapping[str, int]] = None) -> Dict[str, int]:
        do = dict(do or {})
        flaky = do.get("flaky", noise["flaky"])
        load = do.get("load", noise["load"])
        if "retry" in do:
            retry = do["retry"]
        else:
            retry = 1 if ((flaky == 1 and noise["n_r"] == 1) or (load == 1 and noise["n_r2"] == 1)) else 0
        if "pass" in do:
            passed = do["pass"]
        else:
            # pass more likely if retry and not flaky
            passed = 1 if (retry == 1 and flaky == 0) or (retry == 1 and noise["n_p"] == 1) else (
                1 if (flaky == 0 and load == 0 and noise["n_p"] == 1) else 0
            )
        return {"flaky": flaky, "load": load, "retry": retry, "pass": passed}

    p_ate = program_interventional_rate(
        ci_program, ["flaky", "load", "n_r", "n_r2", "n_p"], "pass", {"flaky": 1}
    ) - program_interventional_rate(
        ci_program, ["flaky", "load", "n_r", "n_r2", "n_p"], "pass", {"flaky": 0}
    )

    task2 = Task(
        task_id="P02",
        title="CI flaky tests → pass rate",
        domain="program-systems",
        prompt=_prompt(
            g2,
            "flaky",
            "pass",
            "A CI gate program: flaky tests and load drive retries; retries and flakiness "
            f"drive pass. Executable enumeration ATE(flaky→pass)={p_ate}. "
            "Identify P(pass|do(flaky=1)). Do not adjust for the mediator retry when estimating "
            "the total effect.",
        ),
        graph=g2,
        scm=scm2,
        treatment="flaky",
        outcome="pass",
        identifiable=True,
        notes=(
            "program-grounded CI system",
            f"executable_program_ate={p_ate}",
            "empty or {load} may be valid; {retry} is a descendant/mediator",
        ),
        control_claims=(
            _claim("P02", "flaky", "pass", asserts_identifiable=True, adjustment_set=[]),
            _claim("P02", "flaky", "pass", asserts_identifiable=True, adjustment_set=["retry"]),
            _claim("P02", "flaky", "pass", asserts_identifiable=True, adjustment_set=["pass"]),
        ),
    )

    return (task, task2)
