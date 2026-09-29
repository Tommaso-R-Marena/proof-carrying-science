from __future__ import annotations

import json
import math
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable

from .certificate_semantics_v06 import artifact_ids_from_predicate


SCHEDULER_FORMAT_V06 = "pcs-replay-scheduler-v1"
TELEMETRY_FORMAT_V06 = "pcs-replay-telemetry-v1"
SCHEDULER_REPORT_FORMAT_V06 = "pcs-scheduler-report-v1"
SCHEDULER_STRATEGIES_V06 = (
    "manifest",
    "cheapest-first",
    "failure-rate-first",
    "failure-per-second",
    "bandit",
)

# Conservative deterministic priors used only before enough telemetry exists.
# They affect execution order, never check semantics or PASS/FAIL.
_PRIOR_DURATION_MS = {
    "reaction_balance": 0.10,
    "unit_compatible": 0.10,
    "pkpd_contract": 1.0,
    "csv_disjoint": 2.0,
    "pkpd_reference_match": 4.0,
    "external_formal_proof": 0.05,
    "external_empirical_validation": 0.05,
    "external_statistical_validation": 0.05,
    "provenance_record": 0.05,
}
_PRIOR_FAILS = 1.0
_PRIOR_OBSERVATIONS = 2.0
_RIDGE = 1.0
_MIN_DURATION_MS = 0.001


class V06SchedulerError(ValueError):
    pass


def _evidence_artifact_ids(evidence: dict[str, Any]) -> list[str]:
    spec = evidence.get("check_spec")
    if not isinstance(spec, dict):
        return []
    try:
        ids = artifact_ids_from_predicate(spec)
    except Exception:
        ids = []
    return sorted(set(ids))


def evidence_candidate_v06(
    evidence: dict[str, Any],
    *,
    original_index: int,
    artifact_sizes: dict[str, int],
) -> dict[str, Any]:
    spec = evidence.get("check_spec")
    if not isinstance(spec, dict) or not isinstance(spec.get("type"), str):
        raise V06SchedulerError(
            f"evidence {evidence.get('id')!r} lacks typed check_spec"
        )
    artifact_ids = _evidence_artifact_ids(evidence)
    return {
        "evidence_id": evidence["id"],
        "check_type": spec["type"],
        "original_index": original_index,
        "artifact_ids": artifact_ids,
        "artifact_count": len(artifact_ids),
        "input_bytes": sum(int(artifact_sizes.get(a, 0)) for a in artifact_ids),
    }


def _history_checks(history: Iterable[dict[str, Any]]) -> Iterable[dict[str, Any]]:
    for run in history:
        if not isinstance(run, dict):
            continue
        if run.get("format") != TELEMETRY_FORMAT_V06:
            continue
        checks = run.get("checks")
        if not isinstance(checks, list):
            continue
        for check in checks:
            if not isinstance(check, dict):
                continue
            if not isinstance(check.get("check_type"), str):
                continue
            duration = check.get("duration_ms")
            if not isinstance(duration, (int, float)) or isinstance(duration, bool):
                continue
            if duration < 0:
                continue
            yield check


def history_stats_v06(
    history: Iterable[dict[str, Any]],
) -> dict[str, dict[str, float]]:
    accum: dict[str, dict[str, float]] = defaultdict(
        lambda: {
            "observations": 0.0,
            "failures": 0.0,
            "duration_ms": 0.0,
        }
    )
    for check in _history_checks(history):
        row = accum[check["check_type"]]
        row["observations"] += 1.0
        if check.get("outcome") == "FAIL":
            row["failures"] += 1.0
        row["duration_ms"] += float(check["duration_ms"])

    out: dict[str, dict[str, float]] = {}
    for check_type, row in accum.items():
        n = row["observations"]
        out[check_type] = {
            "observations": n,
            "failures": row["failures"],
            "failure_rate": row["failures"] / n if n else 0.0,
            "mean_duration_ms": row["duration_ms"] / n if n else 0.0,
        }
    return out


def _smoothed_failure_rate(
    check_type: str,
    stats: dict[str, dict[str, float]],
) -> float:
    row = stats.get(check_type)
    if row is None:
        return _PRIOR_FAILS / _PRIOR_OBSERVATIONS
    return (
        row["failures"] + _PRIOR_FAILS
    ) / (
        row["observations"] + _PRIOR_OBSERVATIONS
    )


def _expected_duration_ms(
    candidate: dict[str, Any],
    stats: dict[str, dict[str, float]],
) -> float:
    row = stats.get(candidate["check_type"])
    if row is not None and row["observations"] > 0:
        return max(_MIN_DURATION_MS, float(row["mean_duration_ms"]))

    base = _PRIOR_DURATION_MS.get(candidate["check_type"], 1.0)
    # Deterministic weak size prior: I/O-heavy checks become slightly more
    # expensive before historical measurements exist.
    size_term = candidate["input_bytes"] / (1024 * 1024) * 0.25
    return max(_MIN_DURATION_MS, base + size_term)


def _feature_vector(candidate: dict[str, Any]) -> list[float]:
    return [
        1.0,
        math.log1p(max(0, int(candidate["input_bytes"]))) / 20.0,
        min(8, int(candidate["artifact_count"])) / 8.0,
    ]


def _identity(n: int, scale: float) -> list[list[float]]:
    return [
        [scale if i == j else 0.0 for j in range(n)]
        for i in range(n)
    ]


def _solve(matrix: list[list[float]], vector: list[float]) -> list[float]:
    n = len(vector)
    aug = [list(matrix[i]) + [float(vector[i])] for i in range(n)]
    for col in range(n):
        pivot = max(range(col, n), key=lambda r: abs(aug[r][col]))
        if abs(aug[pivot][col]) < 1e-12:
            raise V06SchedulerError("singular contextual-bandit matrix")
        if pivot != col:
            aug[col], aug[pivot] = aug[pivot], aug[col]
        scale = aug[col][col]
        aug[col] = [v / scale for v in aug[col]]
        for row in range(n):
            if row == col:
                continue
            factor = aug[row][col]
            if factor == 0.0:
                continue
            aug[row] = [
                aug[row][j] - factor * aug[col][j]
                for j in range(n + 1)
            ]
    return [aug[i][n] for i in range(n)]


def _quadratic_form_inverse(
    matrix: list[list[float]],
    vector: list[float],
) -> float:
    solved = _solve(matrix, vector)
    return max(0.0, sum(vector[i] * solved[i] for i in range(len(vector))))


def _bandit_models(
    history: Iterable[dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    dim = 3
    models: dict[str, dict[str, Any]] = {}

    def model_for(check_type: str) -> dict[str, Any]:
        if check_type not in models:
            models[check_type] = {
                "A": _identity(dim, _RIDGE),
                "b": [0.0] * dim,
                "observations": 0,
            }
        return models[check_type]

    for check in _history_checks(history):
        candidate = {
            "input_bytes": int(check.get("input_bytes", 0)),
            "artifact_count": int(check.get("artifact_count", 0)),
        }
        x = _feature_vector(candidate)
        reward = 1.0 if check.get("outcome") == "FAIL" else 0.0
        model = model_for(check["check_type"])
        for i in range(dim):
            model["b"][i] += reward * x[i]
            for j in range(dim):
                model["A"][i][j] += x[i] * x[j]
        model["observations"] += 1
    return models


def _bandit_score(
    candidate: dict[str, Any],
    *,
    models: dict[str, dict[str, Any]],
    stats: dict[str, dict[str, float]],
    alpha: float,
) -> dict[str, float]:
    x = _feature_vector(candidate)
    model = models.get(candidate["check_type"])
    if model is None:
        A = _identity(len(x), _RIDGE)
        b = [0.0] * len(x)
        observations = 0
    else:
        A = model["A"]
        b = model["b"]
        observations = int(model["observations"])

    theta = _solve(A, b)
    mean = sum(theta[i] * x[i] for i in range(len(x)))
    uncertainty = math.sqrt(_quadratic_form_inverse(A, x))
    failure_ucb = max(0.0, min(1.0, mean + alpha * uncertainty))
    duration_ms = _expected_duration_ms(candidate, stats)
    return {
        "predicted_failure_probability": max(0.0, min(1.0, mean)),
        "failure_ucb": failure_ucb,
        "expected_duration_ms": duration_ms,
        "score": failure_ucb / max(_MIN_DURATION_MS, duration_ms),
        "observations": float(observations),
    }


def plan_evidence_v06(
    evidence: list[dict[str, Any]],
    artifact_sizes: dict[str, int],
    *,
    strategy: str = "manifest",
    history: list[dict[str, Any]] | None = None,
    bandit_alpha: float = 1.0,
    shadow_bandit: bool = False,
    candidate_overrides: dict[str, dict[str, int]] | None = None,
) -> dict[str, Any]:
    if strategy not in SCHEDULER_STRATEGIES_V06:
        raise V06SchedulerError(f"unsupported v0.6 scheduler strategy: {strategy!r}")
    if not isinstance(bandit_alpha, (int, float)) or isinstance(bandit_alpha, bool):
        raise V06SchedulerError("bandit_alpha must be numeric")
    if bandit_alpha < 0 or not math.isfinite(float(bandit_alpha)):
        raise V06SchedulerError("bandit_alpha must be finite and nonnegative")

    history = history or []
    candidates = [
        evidence_candidate_v06(
            item,
            original_index=i,
            artifact_sizes=artifact_sizes,
        )
        for i, item in enumerate(evidence)
    ]
    if candidate_overrides:
        for candidate in candidates:
            override = candidate_overrides.get(candidate["evidence_id"])
            if not isinstance(override, dict):
                continue
            if isinstance(override.get("input_bytes"), int) and override["input_bytes"] >= 0:
                candidate["input_bytes"] = override["input_bytes"]
            if (
                isinstance(override.get("artifact_count"), int)
                and override["artifact_count"] >= 0
            ):
                candidate["artifact_count"] = override["artifact_count"]
    stats = history_stats_v06(history)
    models = _bandit_models(history)

    scored: dict[str, dict[str, float]] = {}
    for candidate in candidates:
        check_type = candidate["check_type"]
        duration = _expected_duration_ms(candidate, stats)
        fail_rate = _smoothed_failure_rate(check_type, stats)
        scored[candidate["evidence_id"]] = {
            "expected_duration_ms": duration,
            "smoothed_failure_rate": fail_rate,
            "failure_per_second": fail_rate / max(_MIN_DURATION_MS, duration),
            **{
                f"bandit_{k}": v
                for k, v in _bandit_score(
                    candidate,
                    models=models,
                    stats=stats,
                    alpha=float(bandit_alpha),
                ).items()
            },
        }

    def sort_for(which: str) -> list[dict[str, Any]]:
        if which == "manifest":
            return sorted(candidates, key=lambda x: x["original_index"])
        if which == "cheapest-first":
            return sorted(
                candidates,
                key=lambda x: (
                    scored[x["evidence_id"]]["expected_duration_ms"],
                    x["original_index"],
                ),
            )
        if which == "failure-rate-first":
            return sorted(
                candidates,
                key=lambda x: (
                    -scored[x["evidence_id"]]["smoothed_failure_rate"],
                    scored[x["evidence_id"]]["expected_duration_ms"],
                    x["original_index"],
                ),
            )
        if which == "failure-per-second":
            return sorted(
                candidates,
                key=lambda x: (
                    -scored[x["evidence_id"]]["failure_per_second"],
                    x["original_index"],
                ),
            )
        return sorted(
            candidates,
            key=lambda x: (
                -scored[x["evidence_id"]]["bandit_score"],
                x["original_index"],
            ),
        )

    actual = sort_for(strategy)
    shadow = sort_for("bandit") if shadow_bandit and strategy != "bandit" else None

    return {
        "format": SCHEDULER_FORMAT_V06,
        "strategy": strategy,
        "history_runs": len(history),
        "bandit_alpha": float(bandit_alpha),
        "all_mandatory_checks_execute": True,
        "scientific_verdict_uses_scheduler": False,
        "execution_order": [x["evidence_id"] for x in actual],
        "shadow_bandit_order": (
            [x["evidence_id"] for x in shadow] if shadow is not None else None
        ),
        "candidates": [
            {
                **candidate,
                "scores": scored[candidate["evidence_id"]],
            }
            for candidate in candidates
        ],
    }


def simulate_time_to_first_failure_v06(
    order: list[str],
    checks_by_id: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    elapsed = 0.0
    for evidence_id in order:
        check = checks_by_id[evidence_id]
        elapsed += float(check["duration_ms"])
        if check.get("outcome") == "FAIL":
            return {
                "failure_found": True,
                "evidence_id": evidence_id,
                "time_to_first_failure_ms": elapsed,
            }
    return {
        "failure_found": False,
        "evidence_id": None,
        "time_to_first_failure_ms": None,
    }


def scheduler_report_v06(
    history: list[dict[str, Any]],
    *,
    bandit_alpha: float = 1.0,
) -> dict[str, Any]:
    stats = history_stats_v06(history)
    strategies = list(SCHEDULER_STRATEGIES_V06)
    aggregates = {
        strategy: {
            "evaluated_runs": 0,
            "runs_with_failure": 0,
            "sum_time_to_first_failure_ms": 0.0,
        }
        for strategy in strategies
    }
    run_rows: list[dict[str, Any]] = []

    prior: list[dict[str, Any]] = []
    for index, run in enumerate(history):
        if not isinstance(run, dict) or run.get("format") != TELEMETRY_FORMAT_V06:
            continue
        checks = run.get("checks")
        if not isinstance(checks, list) or not checks:
            prior.append(run)
            continue

        artifact_sizes: dict[str, int] = {}
        fake_evidence: list[dict[str, Any]] = []
        checks_by_id: dict[str, dict[str, Any]] = {}
        candidate_overrides: dict[str, dict[str, int]] = {}
        for check in checks:
            evidence_id = check.get("evidence_id")
            check_type = check.get("check_type")
            if not isinstance(evidence_id, str) or not isinstance(check_type, str):
                continue
            fake_evidence.append(
                {
                    "id": evidence_id,
                    "check_spec": {"type": check_type},
                }
            )
            checks_by_id[evidence_id] = check
            candidate_overrides[evidence_id] = {
                "input_bytes": int(check.get("input_bytes", 0)),
                "artifact_count": int(check.get("artifact_count", 0)),
            }

        if not fake_evidence:
            prior.append(run)
            continue

        comparisons: dict[str, Any] = {}
        for strategy in strategies:
            plan = plan_evidence_v06(
                fake_evidence,
                artifact_sizes,
                strategy=strategy,
                history=prior,
                bandit_alpha=bandit_alpha,
                candidate_overrides=candidate_overrides,
            )
            sim = simulate_time_to_first_failure_v06(
                plan["execution_order"],
                checks_by_id,
            )
            comparisons[strategy] = sim
            aggregates[strategy]["evaluated_runs"] += 1
            if sim["failure_found"]:
                aggregates[strategy]["runs_with_failure"] += 1
                aggregates[strategy]["sum_time_to_first_failure_ms"] += float(
                    sim["time_to_first_failure_ms"]
                )

        run_rows.append(
            {
                "history_index": index,
                "certificate_semantic_hash": run.get("certificate_semantic_hash"),
                "comparisons": comparisons,
            }
        )
        prior.append(run)

    summary: dict[str, Any] = {}
    for strategy, row in aggregates.items():
        failures = row["runs_with_failure"]
        summary[strategy] = {
            "evaluated_runs": row["evaluated_runs"],
            "runs_with_failure": failures,
            "mean_time_to_first_failure_ms": (
                row["sum_time_to_first_failure_ms"] / failures
                if failures
                else None
            ),
        }

    manifest_mean = summary["manifest"]["mean_time_to_first_failure_ms"]
    for strategy, row in summary.items():
        mean = row["mean_time_to_first_failure_ms"]
        row["speedup_vs_manifest"] = (
            manifest_mean / mean
            if isinstance(manifest_mean, (int, float))
            and isinstance(mean, (int, float))
            and mean > 0
            else None
        )

    return {
        "format": SCHEDULER_REPORT_FORMAT_V06,
        "history_runs": len(history),
        "check_type_stats": stats,
        "chronological_counterfactuals": {
            "interpretation": (
                "Each run is evaluated using scheduler statistics learned only from "
                "earlier history lines. Reported times reuse observed per-check durations "
                "as a counterfactual estimate; they do not prove wall-clock speedups."
            ),
            "summary": summary,
            "runs": run_rows,
        },
    }


def load_telemetry_history_v06(path: str | Path | None) -> list[dict[str, Any]]:
    if path is None:
        return []
    p = Path(path)
    try:
        lines = p.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        raise V06SchedulerError(
            f"cannot read replay telemetry history: {type(exc).__name__}: {exc}"
        ) from exc
    out: list[dict[str, Any]] = []
    for line_no, line in enumerate(lines, start=1):
        if not line.strip():
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError as exc:
            raise V06SchedulerError(
                f"invalid telemetry JSONL at line {line_no}: {exc}"
            ) from exc
        if not isinstance(value, dict) or value.get("format") != TELEMETRY_FORMAT_V06:
            raise V06SchedulerError(
                f"telemetry history line {line_no} has unsupported format"
            )
        out.append(value)
    return out


def write_telemetry_v06(
    telemetry: dict[str, Any],
    output: str | Path,
    *,
    overwrite: bool = False,
) -> Path:
    if telemetry.get("format") != TELEMETRY_FORMAT_V06:
        raise V06SchedulerError("refusing to write non-v0.6 replay telemetry")
    path = Path(output).resolve()
    if path.exists() and not overwrite:
        raise V06SchedulerError(
            f"refusing to overwrite existing replay telemetry: {path}"
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(telemetry, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return path


def append_telemetry_history_v06(
    telemetry: dict[str, Any],
    output: str | Path,
) -> Path:
    if telemetry.get("format") != TELEMETRY_FORMAT_V06:
        raise V06SchedulerError("refusing to append non-v0.6 replay telemetry")
    path = Path(output).resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(
        telemetry,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )
    with path.open("a", encoding="utf-8", newline="\n") as fh:
        fh.write(line + "\n")
    return path


def write_scheduler_report_v06(
    report: dict[str, Any],
    output: str | Path,
    *,
    overwrite: bool = False,
) -> Path:
    if report.get("format") != SCHEDULER_REPORT_FORMAT_V06:
        raise V06SchedulerError("refusing to write non-v0.6 scheduler report")
    path = Path(output).resolve()
    if path.exists() and not overwrite:
        raise V06SchedulerError(
            f"refusing to overwrite existing scheduler report: {path}"
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return path
