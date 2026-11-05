# Breakthrough assessment

## Strongest actual result

**In precise terms.** Fix a finite deterministic experimental problem: models
`M`, finitely many experiments `E` with nonnegative rational costs, a rational
query `q`, a version space `K` and a tolerance `ε ≥ 0`.

1. The minimax-optimal total cost over **all** finite adaptive strategies that
   guarantee final query width at most ε equals the Bellman value
   (`value_optimal`, `value_le_iff`).
2. Every value claim has a complete, locally checkable certificate:
   * a policy, for upper bounds (`checkPolicy_sound` / `_complete`);
   * an adversary table, for lower bounds (`le_value_iff_adversary`, with
     completeness through the truncated value);
   * two observationally equivalent models with query gap greater than ε, for
     infinite value (`identifiable_iff`, `impossibilityCert_complete`).
3. A certificate checked on an outer approximation `Khi` certifies exact
   optimality for every `K` with `core ⊆ K ⊆ Khi` (`checkSandwich_sound`).
4. Nuisance-factor elimination: when every experiment depends either only on the
   query-relevant factor or only on a nuisance factor, the optimum on `KA × KZ`
   equals the optimum on one section `KA × {z₀}`. The hypothesis is necessary
   (`value_prod_eq_section`, `nuisance_mixing_counterexample`).

All of this is proved in Lean 4 and Mathlib, depends only on the standard axioms,
and is checked on concrete instances by the Lean kernel.

**Comparison with established results.** (1) is the standard dynamic-programming
characterization of minimax decision trees. (2) for lower bounds is the adversary
method in exact form, and for impossibility it is the classical
observational-equivalence criterion. (3) is monotonicity. (4) is a formal version
of the folklore principle that irrelevant variables can be ignored. **None of this is a new
theorem.** As far as we know (unverified), what is new is the machine-checked
*completeness* package together with an executable, kernel-checked checker for
adaptive experimental policies.

## Tier evaluation

| Tier | Verdict | Justification |
|---|---|---|
| 1. Foundational | **Achieved** | Executable prototype; real Lean proofs (no sorry/axioms/native_decide); exact semantics; verified countermodels; sharp bounds; formally correct adaptive planning (Bellman optimality, soundness, termination, tie-breaking, uninformative experiments); impossibility with an exact characterization. |
| 2. Strong research contribution | **Partially achieved** | Achieved: an independently checked optimality-certification mechanism; honest benchmarks with negative controls; differential testing with 0 false accepts in 1122 tampering attempts; Lean/Python agreement. Not achieved: computational improvements beyond a *purpose-built* family (lesion); no comparison with MILP/SAT optimal-decision-tree solvers; literature comparison not verified. |
| 3. Major breakthrough | **Not achieved** | No new theorem of research significance. The sandwich speedup depends on structure designed into the benchmark family, and is an instance of known counterexample-guided methodology. The obstacle to compact certificates for exponential spaces, namely that small cores can still have exponential explicit certificates (OR), is identified but not overcome. |

## Ratings (1–10)

| Dimension | Rating | Reason |
|---|---|---|
| Mathematical novelty | **2** | Correct and complete, but classical or elementary. The new elements are formulations (the ε-tolerant identifiability criterion with complete two-model certificates, the local adversary form) that a specialist would regard as routine. |
| Formal rigor | **7** | About 2 350 lines of Lean with no gaps. Headline claims match the Lean statements. The axiom audit is clean, and concrete certificates are kernel-checked. Deductions: the parser and emitter are unverified, the Python checker is tested but not extracted, and the progress lemma is not formalized. |
| Algorithmic improvement | **3** | Orders-of-magnitude gains (certified at 131 072 models, where DP times out at 10 s) appear only on a family built to have a small query-relevant core. There is no gain on random or OR instances. No asymptotic theorem. |
| Scientific utility | **3** | The verdict vocabulary and certificates are useful in principle for discrete mechanism-discrimination problems. Real use would need symbolic model classes, noisy data integrated with planning, and real case studies. |
| Demonstrated impact | **1** | Synthetic demonstrations only. No external evaluation and no real data. |

The request's 9–10/10 ambition is not met. The work is a careful,
honestly-reported Tier 1 system with partial Tier 2 elements.

## What would change the assessment

* A verified **symbolic adversary checker**, with certificates expressed as
  formulas over a factored model space. Together with a theorem bounding
  certificate size for a broad structural class, for example "query depends on a
  small set of factors, and nuisance factors are independent", this could give
  provably polynomial-size optimality certificates for exponentially large spaces.
  Lesion-like families satisfy such a condition. OR does not.
* A theorem characterizing exactly when a core of size `f(structure)` suffices,
  together with a lower bound showing that it is necessary.
* An integrated noisy planner with anytime-valid guarantees *and* certified
  optimality of the expected-cost or worst-case sample complexity.
