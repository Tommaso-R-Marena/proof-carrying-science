# PRISM — Proof-Carrying Research and Intervention Selection Machine

PRISM is a research prototype. It takes a finite class of candidate mechanistic
models, observations, declared assumptions, a rational query and a set of costly
deterministic experiments, and returns one of seven verdicts. Each verdict comes
with a certificate that can be checked independently:

| Verdict | Certificate | Lean soundness theorem |
|---|---|---|
| CERTIFIED | nonempty version space + claim holds on all of it | `checkCertified_sound` |
| BOUNDED | sharp `[L, U]` with attaining models | `checkBounds_sound`, `bounds_sharp` |
| FALSIFIED-WITHIN-MODEL | admissible countermodel | `checkCountermodel_sound` |
| UNIDENTIFIABLE | two observationally equivalent models with different query values | `impossibility` |
| EXPERIMENT | optimal adaptive policy + core + adversary table | `checkOptimal_sound`, `checkSandwich_sound` |
| IMPOSSIBLE | two-model certificate (complete) | `checkImpossible_sound`, `impossibilityCert_complete` |
| INCONSISTENT | empty version space (per-model refutation) | `checkInconsistent_sound`, `inconsistencyCert_sound` |

**What is proved.** The Lean 4 / Mathlib development in `PRISM/` (about 2 350
lines) proves the following. There is no `sorry`, no custom axiom and no
`native_decide`; the axiom audit is in `results/axiom_audit.txt`.

* Version-space soundness, sharp bounds and inconsistency certificates.
* The Bellman recurrence, and global minimax optimality over **all** adaptive
  policies.
* The impossibility theorem and an exact identifiability criterion
  (equivalence-class query spread ≤ ε), with complete two-model certificates.
* Complete adversary lower-bound certificates.
* The optimality sandwich, exact abstraction, and nuisance-factor elimination.
* Checker soundness.
* An anytime-valid noisy extension.
* Parametric families: OR evasiveness for every n, a Θ(n) adaptivity gap, and a
  greedy trap.

See `docs/THEOREMS.md`.

**What is not claimed.** We do not claim a new mathematical theorem of research
significance; see `docs/NOVELTY_AUDIT.md` and `docs/BREAKTHROUGH_ASSESSMENT.md`.
We do not claim laboratory validation, since all demonstrations are synthetic.
We do not claim a verified parser; the trusted components are listed in
`docs/TRUST_BOUNDARIES.md`. The literature review was done **without internet
access** and is unverified for 2025–2026 work.

## Quick start

```bash
python3 scripts/run_all.py          # build + audit + tests + demos + benchmarks + report
python3 scripts/run_all.py --quick  # faster
python3 python/verify.py examples/biochemical/problem.json \
        examples/biochemical/certificate_initial.json --lean   # independent check, incl. Lean kernel
lake build PRISM                    # Lean only
```

Requirements: the Lean toolchain from `lean-toolchain` (Lean 4.28.0, Mathlib
v4.28.0) and Python ≥ 3.11 (stdlib only).

## Layout

```
PRISM/                      Lean 4 formal development
  Models/Basic.lean           problems, width, cells, informativeness
  Inference/VersionSpace.lean version spaces, sharp bounds, claims, inconsistency
  Experiments/Policy.lean     adaptive policies, success, cost, termination
  Optimality/Bellman.lean     Bellman value and global minimax optimality
  Identifiability/Impossibility.lean  impossibility, exact identifiability
  Abstraction/Sandwich.lean   optimality sandwich, exact abstraction
  Abstraction/Nuisance.lean   nuisance-factor elimination (+ counterexample)
  Certificates/Adversary.lean lower-bound certificates (sound + complete)
  Certificates/Checker.lean   executable checkers with soundness proofs
  Probabilistic/AnytimeValid.lean  anytime-valid noisy certification
  Examples/Families.lean      OR, pointer (adaptivity gap), greedy trap
  Examples/Generated/*.lean   kernel-checked demo certificates (generated)
  AxiomAudit.lean             #print axioms for all headline results
python/prism/               untrusted engine + independent checker
  core.py, engine.py          model sets, research cycle, verdicts, assumption contract
  search/                     Bellman DP (naive/pruned), sandwich refinement, baselines
  reference/                  independent exhaustive solvers + checker mirror
  serialize.py                versioned strict schemas, canonical hashing
  lean_export.py              JSON → Lean certificate modules
  noisy.py                    exact evaluation of noisy adaptive procedures
python/verify.py            stand-alone certificate verifier (CLI)
python/benchmarks/          benchmark suite + HTML report generator
examples/{biochemical,causal,scalable}/   demonstrations A, B, C
tests/                      differential, serialization, Lean-agreement tests
results/                    raw outputs, logs, benchmarks, report.html, axiom audit
docs/                       paper, theorems, novelty, trust, experiments, negatives, ...
```

Plots are embedded as inline SVG in `results/report.html`. `figures/` is
intentionally empty, because image files are not versioned.

## Documents

* `docs/RESEARCH_PAPER.md`: the manuscript.
* `docs/THEOREMS.md`: every formal result, with informal meaning and limits.
* `docs/NOVELTY_AUDIT.md`: the prior-art comparison table and the narrow novelty claims.
* `docs/TRUST_BOUNDARIES.md`: what is proved, kernel-checked, tested or trusted;
  the schemas.
* `docs/EXPERIMENTS.md`: benchmark methodology and results.
* `docs/NEGATIVE_RESULTS.md`: counterexamples, failures and limitations.
* `docs/REVIEW.md`: the adversarial self-review.
* `docs/REPRODUCIBILITY.md`: pinned versions and how to reproduce.
* `docs/BREAKTHROUGH_ASSESSMENT.md`: tier evaluation and ratings.

## Headline numbers (from `results/`)

* Differential testing: 400 instances; all exact solvers agree; 1122 tampered
  certificates all rejected (0 false accepts).
* Lesion family, a structured family built to have a small hard core: optimality
  certified for up to 131 072 models in about 9 s plus about 4 s of independent
  checking. With n = 8 pathway steps, naive DP times out (10 s) from 2 048 models
  and pruned DP from 32 768 models.
* Random held-out instances: no advantage over pruned DP.
* OR negative control: no advantage.
* Noisy demo: the mixture rule's false-certification probability is 0.0027 ≤ α =
  0.05; the post-hoc rule's is 0.0586 > α.
