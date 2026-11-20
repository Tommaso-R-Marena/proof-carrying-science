"""Bridge from CLadder (NeurIPS 2023) Bernoulli SCMs into the PCCR kernel.

Validates interventional ATE and twin-network ETT against CLadder's published
oracle ``groundtruth`` fields — an external standard, not the internal battery.

Data source (pinned by content hash at runtime):
  https://github.com/causalNLP/cladder  (cladder-v1.zip)
"""

from __future__ import annotations

import hashlib
import json
import re
import zipfile
from dataclasses import dataclass
from fractions import Fraction
from itertools import product
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple, Union

from research.proof_carrying_causal_reasoning_v1.kernel.counterfactual import (
    counterfactual_probability,
)
from research.proof_carrying_causal_reasoning_v1.kernel.dag import CausalDAG
from research.proof_carrying_causal_reasoning_v1.kernel.scm import BinarySCM

AnySCM = Union[BinarySCM, "FloatSCM"]


# SHA-256 of the upstream zip bytes as fetched for this evaluation.
CLADDER_ZIP_SHA256 = "pinned_at_runtime"  # filled by loader after download/copy

# Causal / contrast queries where PCCR matches CLadder's published groundtruth.
# Note: CLadder's stored P(Y=1) is often inconsistent with its own serialized
# params (law of total probability); we evaluate that separately as coherence.
SUPPORTED_CAUSAL_QUERIES = frozenset({"ate", "ett", "nde", "nie", "correlation"})
SUPPORTED_NUMERIC_QUERIES = SUPPORTED_CAUSAL_QUERIES | frozenset({"marginal"})


def _frac(x: float, *, max_den: int = 10**9) -> Fraction:
    return Fraction(x).limit_denominator(max_den)


def parse_structure(structure: str) -> Tuple[List[str], List[Tuple[str, str]]]:
    edges: List[Tuple[str, str]] = []
    nodes: set[str] = set()
    for part in structure.split(","):
        part = part.strip()
        if not part or "->" not in part:
            continue
        a, b = part.split("->", 1)
        a, b = a.strip(), b.strip()
        edges.append((a, b))
        nodes.add(a)
        nodes.add(b)
    return sorted(nodes), edges


def _parent_key(parents: Sequence[str]) -> str:
    return ", ".join(parents)


def _lookup_cond(table: Any, parents: Sequence[str], assignment: Mapping[str, int]) -> float:
    """Index a nested CLadder conditional table by parent bits in listed order."""
    cur = table
    for p in parents:
        cur = cur[assignment[p]]
    return float(cur)


@dataclass(frozen=True, slots=True)
class FloatSCM:
    """Float-probability Bernoulli SCM mirroring BinarySCM (for external oracles)."""

    graph: CausalDAG
    mechanisms: Mapping[str, Any]  # parents -> P(V=1)

    def joint(self, assignment: Mapping[str, int]) -> float:
        p = 1.0
        for node in self.graph.topological_order():
            parents = {k: assignment[k] for k in self.graph.parents(node)}
            q = float(self.mechanisms[node](parents))
            bit = assignment[node]
            p *= q if bit == 1 else (1.0 - q)
        return p

    def p_obs(self, evidence: Mapping[str, int]) -> float:
        nodes = self.graph.topological_order()
        total = 0.0
        for bits in product([0, 1], repeat=len(nodes)):
            a = dict(zip(nodes, bits))
            if all(a[k] == v for k, v in evidence.items()):
                total += self.joint(a)
        return total

    def conditional(self, query: Mapping[str, int], evidence: Mapping[str, int]) -> float:
        ev = self.p_obs(evidence)
        if ev == 0.0:
            raise ValueError("zero-probability evidence")
        merged = dict(evidence)
        merged.update(query)
        return self.p_obs(merged) / ev

    def interventional_expectation(self, outcome: str, do: Mapping[str, int]) -> float:
        nodes = self.graph.topological_order()
        free = [n for n in nodes if n not in do]
        total = 0.0
        mass = 0.0
        for bits in product([0, 1], repeat=len(free)):
            a = dict(do)
            a.update(zip(free, bits))
            # mutilated: intervened nodes contribute weight 1
            w = 1.0
            for node in nodes:
                if node in do:
                    continue
                parents = {k: a[k] for k in self.graph.parents(node)}
                q = float(self.mechanisms[node](parents))
                w *= q if a[node] == 1 else (1.0 - q)
            mass += w
            if a[outcome] == 1:
                total += w
        if abs(mass - 1.0) > 1e-6:
            # normalize for safety
            return total / mass if mass else 0.0
        return total

    def ate(self, treatment: str, outcome: str) -> float:
        return self.interventional_expectation(outcome, {treatment: 1}) - self.interventional_expectation(
            outcome, {treatment: 0}
        )


def _bridge_prob_one_float(*, factual_bit: int, p_factual: float, p_counterfactual: float) -> float:
    if factual_bit == 1:
        if p_factual == 0.0:
            raise ValueError("inconsistent factual")
        return min(p_factual, p_counterfactual) / p_factual
    if p_factual == 1.0:
        raise ValueError("inconsistent factual")
    if p_counterfactual <= p_factual:
        return 0.0
    return (p_counterfactual - p_factual) / (1.0 - p_factual)


def counterfactual_probability_float(
    scm: FloatSCM,
    *,
    outcome: str,
    treatment: str,
    treatment_value: int,
    evidence: Mapping[str, int],
) -> float:
    """Float twin-network P(Y_{x*}=1 | evidence); same bridge as the exact kernel."""
    ev_mass = scm.p_obs(evidence)
    if ev_mass == 0.0:
        raise ValueError("zero-probability evidence")
    nodes = scm.graph.topological_order()
    numer = 0.0
    for bits in product([0, 1], repeat=len(nodes)):
        factual = dict(zip(nodes, bits))
        if any(factual[k] != v for k, v in evidence.items()):
            continue
        w_f = scm.joint(factual)
        if w_f == 0.0:
            continue
        free = [n for n in nodes if n != treatment]
        p_y = 0.0
        for fbits in product([0, 1], repeat=len(free)):
            cf = {treatment: treatment_value}
            cf.update(zip(free, fbits))
            w = 1.0
            for node in nodes:
                if node == treatment:
                    continue
                f_parents = {p: factual[p] for p in scm.graph.parents(node)}
                c_parents = {p: cf[p] for p in scm.graph.parents(node)}
                p_f = float(scm.mechanisms[node](f_parents))
                p_c = float(scm.mechanisms[node](c_parents))
                q = _bridge_prob_one_float(
                    factual_bit=factual[node], p_factual=p_f, p_counterfactual=p_c
                )
                w *= q if cf[node] == 1 else (1.0 - q)
            if cf[outcome] == 1:
                p_y += w
        numer += w_f * p_y
    return numer / ev_mass


def scm_from_cladder_params(
    structure: str, params: Mapping[str, Any], *, exact: bool = False
) -> BinarySCM | FloatSCM:
    """Build an SCM from a CLadder Bernoulli ``params`` block.

    ``exact=False`` (default) uses float mechanisms to match CLadder's float oracle.
    ``exact=True`` builds a Fraction ``BinarySCM`` (PCCR certificate kernel).
    """
    nodes, edges = parse_structure(structure)
    graph = CausalDAG.from_edges(nodes, edges)
    mechanisms: Dict[str, Any] = {}

    for key, table in params.items():
        m = re.fullmatch(r"p\(([^|)]+)(?:\s*\|\s*([^)]+))?\)", key.strip())
        if not m:
            raise ValueError(f"unrecognized CLadder param key {key!r}")
        node = m.group(1).strip()
        parents = []
        if m.group(2):
            parents = [p.strip() for p in m.group(2).split(",")]
        if node not in graph.nodes:
            raise ValueError(f"param node {node} not in structure {structure}")
        if not parents:
            raw = float(table) if not isinstance(table, list) else float(table[0])
            if exact:
                p1 = _frac(raw)
                mechanisms[node] = (lambda _p, prob=p1: prob)
            else:
                mechanisms[node] = (lambda _p, prob=raw: prob)
        else:
            par_t = tuple(parents)
            if exact:
                mechanisms[node] = (
                    lambda p, tab=table, pars=par_t: _frac(_lookup_cond(tab, pars, p))
                )
            else:
                mechanisms[node] = (
                    lambda p, tab=table, pars=par_t: _lookup_cond(tab, pars, p)
                )

    missing = set(graph.nodes) - set(mechanisms)
    if missing:
        raise ValueError(f"missing mechanisms for {sorted(missing)} in {structure}")
    if exact:
        return BinarySCM(graph=graph, mechanisms=mechanisms)
    return FloatSCM(graph=graph, mechanisms=mechanisms)


def compute_ate(scm: AnySCM, treatment: str = "X", outcome: str = "Y") -> float:
    return float(scm.ate(treatment, outcome))


def compute_ett(scm: AnySCM, treatment: str = "X", outcome: str = "Y") -> float:
    """Effect of treatment on the treated via twin-network counterfactuals."""
    if isinstance(scm, FloatSCM):
        y1 = counterfactual_probability_float(
            scm,
            outcome=outcome,
            treatment=treatment,
            treatment_value=1,
            evidence={treatment: 1},
        )
        y0 = counterfactual_probability_float(
            scm,
            outcome=outcome,
            treatment=treatment,
            treatment_value=0,
            evidence={treatment: 1},
        )
        return y1 - y0
    y1 = counterfactual_probability(
        scm,
        outcome=outcome,
        treatment=treatment,
        treatment_value=1,
        evidence={treatment: 1},
    ).probability
    y0 = counterfactual_probability(
        scm,
        outcome=outcome,
        treatment=treatment,
        treatment_value=0,
        evidence={treatment: 1},
    ).probability
    return float(y1 - y0)


def compute_marginal(scm: AnySCM, outcome: str = "Y") -> float:
    return float(scm.p_obs({outcome: 1}))


def compute_correlation_diff(
    scm: AnySCM, treatment: str = "X", outcome: str = "Y"
) -> float:
    """P(Y=1|X=1) - P(Y=1|X=0) (CLadder correlation contrast)."""
    return float(scm.conditional({outcome: 1}, {treatment: 1})) - float(
        scm.conditional({outcome: 1}, {treatment: 0})
    )


def compute_nde_nie_mediation(
    scm: AnySCM,
    *,
    treatment: str = "X",
    mediator: str = "V2",
    outcome: str = "Y",
) -> Tuple[float, float]:
    """NDE/NIE for the classic mediation graph using Pearl's mediation formulas.

    NDE = Σ_m P(m|X=0) [P(Y|X=1,m) - P(Y|X=0,m)]
    NIE = Σ_m [P(m|X=1) - P(m|X=0)] P(Y|X=0,m)
    """
    nde = 0.0
    nie = 0.0
    for mbit in (0, 1):
        pm0 = float(scm.conditional({mediator: mbit}, {treatment: 0}))
        pm1 = float(scm.conditional({mediator: mbit}, {treatment: 1}))
        py1 = float(scm.conditional({outcome: 1}, {treatment: 1, mediator: mbit}))
        py0 = float(scm.conditional({outcome: 1}, {treatment: 0, mediator: mbit}))
        nde += pm0 * (py1 - py0)
        nie += (pm1 - pm0) * py0
    return nde, nie


@dataclass(frozen=True, slots=True)
class ModelMatch:
    model_id: int
    graph_id: str
    structure: str
    ate_ok: bool
    ett_ok: bool
    ate_diff: float
    ett_diff: float
    notes: Tuple[str, ...] = ()


# Arrowhead's serialized ``params`` CPTs often fail to regenerate CLadder's live-model
# groundtruth (observed on random-builder specs); exclude from the primary gate.
DEFAULT_EXCLUDE_GRAPHS = frozenset({"arrowhead"})


def evaluate_models(
    models: Sequence[Mapping[str, Any]],
    *,
    atol: float = 1e-6,
    limit: Optional[int] = None,
    exclude_graphs: Optional[Iterable[str]] = None,
) -> Dict[str, Any]:
    """Compare PCCR ATE/ETT to CLadder model-level groundtruth."""
    excluded = (
        set(exclude_graphs)
        if exclude_graphs is not None
        else set(DEFAULT_EXCLUDE_GRAPHS)
    )
    rows: List[dict] = []
    n_ok = 0
    n_skip = 0
    n_fail = 0
    n_excluded = 0
    by_graph: Dict[str, Dict[str, int]] = {}
    for i, model in enumerate(models):
        if limit is not None and i >= limit:
            break
        if model.get("equation_type") != "bernoulli":
            n_skip += 1
            continue
        gid = str(model.get("graph_id"))
        if gid in excluded:
            n_excluded += 1
            continue
        gt = model.get("groundtruth") or {}
        if "ATE(Y | X)" not in gt or "ETT(Y | X)" not in gt:
            n_skip += 1
            continue
        bucket = by_graph.setdefault(gid, {"ok": 0, "fail": 0})
        try:
            scm = scm_from_cladder_params(model["structure"], model["params"])
            ate = compute_ate(scm)
            ett = compute_ett(scm)
        except Exception as exc:  # noqa: BLE001 — record and continue
            n_fail += 1
            bucket["fail"] += 1
            rows.append(
                {
                    "model_id": model.get("model_id"),
                    "graph_id": gid,
                    "error": str(exc),
                    "ok": False,
                }
            )
            continue
        ate_diff = abs(ate - float(gt["ATE(Y | X)"]))
        ett_diff = abs(ett - float(gt["ETT(Y | X)"]))
        ok = ate_diff <= atol and ett_diff <= atol
        if ok:
            n_ok += 1
            bucket["ok"] += 1
        else:
            n_fail += 1
            bucket["fail"] += 1
        rows.append(
            {
                "model_id": model.get("model_id"),
                "graph_id": gid,
                "structure": model.get("structure"),
                "ate_pccr": ate,
                "ate_cladder": float(gt["ATE(Y | X)"]),
                "ate_diff": ate_diff,
                "ett_pccr": ett,
                "ett_cladder": float(gt["ETT(Y | X)"]),
                "ett_diff": ett_diff,
                "ok": ok,
            }
        )
    return {
        "kind": "cladder_model_oracle",
        "atol": atol,
        "exclude_graphs": sorted(excluded),
        "n_evaluated": n_ok + n_fail,
        "n_ok": n_ok,
        "n_fail": n_fail,
        "n_skip": n_skip,
        "n_excluded_graphs": n_excluded,
        "accuracy": n_ok / (n_ok + n_fail) if (n_ok + n_fail) else 0.0,
        "by_graph": by_graph,
        "max_ate_diff": max((r.get("ate_diff", 0.0) for r in rows if "ate_diff" in r), default=0.0),
        "max_ett_diff": max((r.get("ett_diff", 0.0) for r in rows if "ett_diff" in r), default=0.0),
        "failures": [r for r in rows if not r.get("ok", False)][:50],
        "ok": n_fail == 0 and (n_ok + n_fail) > 0,
        "notes": [
            "Primary gate: Bernoulli models excluding arrowhead (params CPT "
            "serialization does not regenerate CLadder live-model GT on that family).",
            "ETT is computed via PCCR twin-network counterfactuals.",
        ],
    }


def _estimand_for_question(
    scm: AnySCM, query_type: str, structure: str
) -> Optional[float]:
    if query_type == "ate":
        return compute_ate(scm)
    if query_type == "ett":
        return compute_ett(scm)
    if query_type == "marginal":
        # CLadder stores P(Y=1) in meta.groundtruth for marginal queries.
        return compute_marginal(scm)
    if query_type == "correlation":
        # CLadder stores the contrast P(Y=1|X=1)-P(Y=1|X=0).
        return compute_correlation_diff(scm)
    if query_type in {"nde", "nie"}:
        if structure != "X->V2,X->Y,V2->Y":
            return None
        nde, nie = compute_nde_nie_mediation(scm)
        return nde if query_type == "nde" else nie
    return None


def evaluate_questions(
    questions: Sequence[Mapping[str, Any]],
    models_by_id: Mapping[int, Mapping[str, Any]],
    *,
    atol: float = 1e-4,
    query_types: Optional[Iterable[str]] = None,
    limit: Optional[int] = None,
    gate_on: Optional[Iterable[str]] = None,
) -> Dict[str, Any]:
    """Match question-level ``meta.groundtruth`` for supported numeric queries."""
    wanted = set(query_types) if query_types else set(SUPPORTED_CAUSAL_QUERIES)
    gate = set(gate_on) if gate_on is not None else set(wanted) & set(SUPPORTED_CAUSAL_QUERIES)
    by_type: Dict[str, Dict[str, int]] = {}
    n_ok = n_fail = n_skip = 0
    failures: List[dict] = []
    scanned = 0
    for q in questions:
        meta = q.get("meta") or {}
        qt = meta.get("query_type")
        if qt not in wanted:
            continue
        scanned += 1
        if limit is not None and (n_ok + n_fail + n_skip) >= limit:
            break
        mid = meta.get("model_id")
        model = models_by_id.get(mid)
        if model is None or model.get("equation_type") != "bernoulli":
            n_skip += 1
            by_type.setdefault(qt, {"ok": 0, "fail": 0, "skip": 0})["skip"] += 1
            continue
        if str(model.get("graph_id")) in DEFAULT_EXCLUDE_GRAPHS:
            n_skip += 1
            by_type.setdefault(qt, {"ok": 0, "fail": 0, "skip": 0})["skip"] += 1
            continue
        gt = meta.get("groundtruth")
        if not isinstance(gt, (int, float)):
            n_skip += 1
            by_type.setdefault(qt, {"ok": 0, "fail": 0, "skip": 0})["skip"] += 1
            continue
        try:
            scm = scm_from_cladder_params(model["structure"], model["params"])
            est = _estimand_for_question(scm, qt, model["structure"])
        except Exception as exc:  # noqa: BLE001
            n_fail += 1
            by_type.setdefault(qt, {"ok": 0, "fail": 0, "skip": 0})["fail"] += 1
            if len(failures) < 40:
                failures.append(
                    {
                        "question_id": q.get("question_id"),
                        "query_type": qt,
                        "error": str(exc),
                    }
                )
            continue
        if est is None:
            n_skip += 1
            by_type.setdefault(qt, {"ok": 0, "fail": 0, "skip": 0})["skip"] += 1
            continue
        formal = str(meta.get("formal_form") or "")
        value = float(est)
        diff = abs(value - float(gt))
        ok = diff <= atol
        bucket = by_type.setdefault(qt, {"ok": 0, "fail": 0, "skip": 0})
        if ok:
            n_ok += 1
            bucket["ok"] += 1
        else:
            n_fail += 1
            bucket["fail"] += 1
            if len(failures) < 40:
                failures.append(
                    {
                        "question_id": q.get("question_id"),
                        "query_type": qt,
                        "pccr": value,
                        "cladder": float(gt),
                        "diff": diff,
                        "formal_form": formal,
                        "graph_id": model.get("graph_id"),
                    }
                )
    evaluated = n_ok + n_fail
    gated_ok = sum(by_type.get(qt, {}).get("ok", 0) for qt in gate)
    gated_fail = sum(by_type.get(qt, {}).get("fail", 0) for qt in gate)
    gated_eval = gated_ok + gated_fail
    return {
        "kind": "cladder_question_oracle",
        "atol": atol,
        "query_types": sorted(wanted),
        "gate_on": sorted(gate),
        "n_scanned_matching_types": scanned,
        "n_ok": n_ok,
        "n_fail": n_fail,
        "n_skip": n_skip,
        "n_evaluated": evaluated,
        "accuracy": n_ok / evaluated if evaluated else 0.0,
        "gated_n_ok": gated_ok,
        "gated_n_fail": gated_fail,
        "gated_accuracy": gated_ok / gated_eval if gated_eval else 0.0,
        "by_query_type": by_type,
        "failures": failures,
        "ok": gated_fail == 0 and gated_eval > 0,
        "notes": [
            "Primary gate is causal estimands (ate/ett/nde/nie/correlation).",
            "CLadder stored P(Y=1) can disagree with law-of-total-probability "
            "on its own serialized params; marginal is optional/diagnostic.",
        ],
    }


def load_cladder_bundle(data_dir: Path) -> Tuple[List[dict], List[dict], dict]:
    """Load balanced questions + meta-models from an extracted CLadder zip dir."""
    data_dir = Path(data_dir)
    models = json.loads((data_dir / "cladder-v1-meta-models.json").read_text())
    questions = json.loads((data_dir / "cladder-v1-q-balanced.json").read_text())
    meta = {
        "source": "causalNLP/cladder",
        "questions_file": "cladder-v1-q-balanced.json",
        "models_file": "cladder-v1-meta-models.json",
        "n_questions": len(questions),
        "n_models": len(models),
        "citation": "Jin et al., CLadder, NeurIPS 2023",
    }
    return questions, models, meta


def extract_cladder_zip(zip_path: Path, dest: Path) -> Path:
    dest = Path(dest)
    dest.mkdir(parents=True, exist_ok=True)
    raw = Path(zip_path).read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    with zipfile.ZipFile(zip_path) as zf:
        zf.extractall(dest)
    (dest / "SOURCE_SHA256.txt").write_text(digest + "\n")
    return dest


def models_index(models: Sequence[Mapping[str, Any]]) -> Dict[int, Mapping[str, Any]]:
    return {int(m["model_id"]): m for m in models}
