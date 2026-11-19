"""Self-evolving safety gate loop: formal admission + empirical fitness + attested retain.

Honest scope: finite reviewed mutations over a Lean admission lattice, scored on
attested Assurance Mirage evidence plus a pinned stealth hard suite (and optional
live arms). Not recursive self-improvement of production PCS authority.
"""
from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
import time
from typing import Any

from .catalog import (
    SEED_CANDIDATES,
    Candidate,
    adaptive_from_failures,
    bootstrap_jumps,
    detect_rank,
    detector_for,
    formal_admissible,
    mutate,
)
from .fitness import dominates_empirical, score_candidate
from .formal_check import check_formal
from .hard_suite import write_hard_suite

DEFAULT_EVIDENCE = (
    Path(__file__).resolve().parents[1] / "assurance_mirage_v1" / "evidence"
)


def _safe_name(candidate_id: str) -> str:
    """Windows-safe filename stem (no '>', ':', '|', etc.)."""
    bad = '<>:"/\\|?*'
    out = candidate_id
    for ch in bad:
        out = out.replace(ch, "_")
    return out.replace("->", "__")


def _retainable_formal(parent: Candidate, succ: Candidate) -> bool:
    """Mirror Lean retainability + same-class empiric search on admissible parents."""
    if not formal_admissible(succ.formal_class):
        return False
    if detect_rank(succ.formal_class) > detect_rank(parent.formal_class):
        return True
    return formal_admissible(parent.formal_class) and succ.formal_class == parent.formal_class


def run_evolution(
    out: Path,
    *,
    evidence_root: Path | None = None,
    generations: int = 4,
    population_cap: int = 32,
) -> dict[str, Any]:
    out = Path(out)
    out.mkdir(parents=True, exist_ok=False)
    evidence_root = Path(evidence_root) if evidence_root else DEFAULT_EVIDENCE
    start = time.monotonic()

    formal = check_formal(out / "formal-build")
    hard_meta = write_hard_suite(out / "hard_suite.json", evidence_root)
    hard_suite = list(hard_meta["episodes"])

    population: list[Candidate] = list(SEED_CANDIDATES)
    history: list[dict[str, Any]] = []
    champion: Candidate | None = None
    champion_score: dict[str, Any] | None = None

    for gen in range(0, generations + 1):
        scored = []
        for c in population:
            s = score_candidate(c, evidence_root, hard_suite=hard_suite)
            scored.append({"candidate": c.to_json(), "score": s})
            cand_dir = out / "candidates"
            cand_dir.mkdir(parents=True, exist_ok=True)
            (cand_dir / f"{_safe_name(c.id)}.json").write_text(
                json.dumps({"candidate": c.to_json(), "score": s}, indent=2) + "\n"
            )
            if s["formal_admissible"]:
                if champion_score is None or s["fitness"] > champion_score["fitness"]:
                    champion, champion_score = c, s
                elif (
                    champion is not None
                    and dominates_empirical(s, champion_score)
                    and s["fitness"] >= champion_score["fitness"]
                ):
                    champion, champion_score = c, s

        scored.sort(key=lambda r: r["score"]["fitness"], reverse=True)
        history.append(
            {
                "generation": gen,
                "n_candidates": len(scored),
                "leaderboard": [
                    {
                        "id": r["candidate"]["id"],
                        "formal_class": r["candidate"]["formal_class"],
                        "fitness": r["score"]["fitness"],
                        "formal_admissible": r["score"]["formal_admissible"],
                        "mirage_recall": r["score"]["mirage_recall"],
                        "stealth_recall": r["score"]["stealth_recall"],
                        "benign_fpr": r["score"]["benign_false_positive_rate"],
                        "gemini_clean": r["score"]["gemini_clean"],
                    }
                    for r in scored[:12]
                ],
                "champion_id": champion.id if champion else None,
            }
        )

        if gen == generations:
            break

        next_pop: list[Candidate] = []
        seen: set[str] = set()
        for c in population:
            if c.id in {"joint-v1", "ensemble-v1", "composed-v1"} or (
                champion and c.id == champion.id
            ):
                if c.id not in seen:
                    next_pop.append(c)
                    seen.add(c.id)

        parents = [
            Candidate(**r["candidate"])
            for r in scored
            if r["score"]["formal_admissible"]
        ][:6]
        if not parents:
            parents = [Candidate(**r["candidate"]) for r in scored[:1]]

        for p in parents:
            for child in mutate(p, gen + 1):
                if child.id in seen:
                    continue
                if not _retainable_formal(p, child):
                    continue
                next_pop.append(child)
                seen.add(child.id)

            # Failure-driven adaptation when stealth misses remain.
            p_score = next(
                (r["score"] for r in scored if r["candidate"]["id"] == p.id),
                None,
            )
            if p_score and (p_score.get("stealth_misses") or 0) > 0:
                missed = [
                    e
                    for e in hard_suite
                    if e.get("stealth_mirage") and not detector_for(p)(e)
                ]
                for child in adaptive_from_failures(p, missed, gen + 1):
                    if child.id in seen:
                        continue
                    # Adaptive children may jump up the lattice or stay ensemble.
                    legal = _retainable_formal(p, child) or (
                        formal_admissible(p.formal_class)
                        and formal_admissible(child.formal_class)
                        and detect_rank(child.formal_class) >= detect_rank(p.formal_class)
                    )
                    if not legal:
                        continue
                    next_pop.append(child)
                    seen.add(child.id)

        for jump in bootstrap_jumps(gen + 1):
            if jump.id not in seen and _retainable_formal(
                Candidate(
                    id="c1-blind",
                    formal_class="channel1Only",
                    generation=0,
                    parent_id=None,
                    description="",
                    weights={},
                ),
                jump,
            ):
                next_pop.append(jump)
                seen.add(jump.id)

        for neg in SEED_CANDIDATES:
            if not formal_admissible(neg.formal_class) and neg.id not in seen:
                next_pop.append(neg)
                seen.add(neg.id)

        population = next_pop[:population_cap]

    assert champion is not None and champion_score is not None
    assert champion_score["formal_admissible"], "Champion must pass Lean admission class"
    assert detect_rank(champion.formal_class) > detect_rank("channel1Only")

    lineage = {
        "format": "pcs-evolving-safety-gate-lineage-v2",
        "generations_run": generations + 1,
        "champion": champion.to_json(),
        "champion_score": champion_score,
        "history": history,
        "hard_suite": {
            "n": hard_meta["n"],
            "n_stealth": hard_meta["n_stealth"],
            "n_benign": hard_meta["n_benign"],
        },
        "formal": {
            "source_sha256": formal["source_sha256"],
            "kernel_checked": formal["kernel_checked"],
            "theorems": formal["theorems"],
            "axiom_closures": formal["axiom_closures"],
        },
        "evidence_root": str(evidence_root),
        "finding": (
            "Evolution retained an admissible champion on the Lean lattice; "
            "channel-1-only and correcting-only never won. Fitness includes classic "
            "mirage recall plus stealth hard-suite recall so ensemble probes can "
            "dominate joint-only detectors that miss note-level compliance."
        ),
        "production_authority": False,
        "recursive_self_improvement_claimed": False,
        "seconds": round(time.monotonic() - start, 3),
    }
    raw = (json.dumps(lineage, indent=2, sort_keys=True) + "\n").encode()
    lineage["lineage_sha256"] = sha256(raw).hexdigest()
    (out / "lineage.json").write_text(json.dumps(lineage, indent=2) + "\n")
    (out / "champion.json").write_text(
        json.dumps({"candidate": champion.to_json(), "score": champion_score}, indent=2) + "\n"
    )
    return lineage
