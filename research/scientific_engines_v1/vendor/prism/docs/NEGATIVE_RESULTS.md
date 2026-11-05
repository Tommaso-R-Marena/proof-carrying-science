# Negative results, failed conjectures and limitations

Each item is marked **[Lean]** if machine-checked, **[exp]** if observed
experimentally (with the file containing the raw data), or **[informal]**.

## Counterexamples to attractive claims

1. **Greedy one-step optimal experiment selection is not globally optimal.** [Lean]
   `trap_greedy_choice` and `trap_greedy_suboptimal` in `PRISM/Examples/Families.lean`:
   on a 4-model instance, the experiment minimizing worst-case posterior width
   leads to cost ≥ 5. The optimum is 4 (`trap_value`, with a kernel-checked
   certificate). [exp] In the random benchmark (held-out seeds), recursive greedy was
   strictly suboptimal in 3/20, 1/20, 14/20, 14/20 and 20/20 instances across the
   five size classes (`results/benchmarks.json`, `greedy.gap`).

2. **Quotienting by observation signature alone is unsound.** [Lean]
   `signature_only_quotient_unsound`: merging observationally equivalent models
   while ignoring their query values turns an impossible problem (value ⊤) into a
   trivially solved one (value 0). Exact abstraction must preserve the query
   (`IsExactAbstraction`, `value_signatureQuotient`).

3. **Post-hoc maximum-likelihood alternatives break anytime validity.** [Lean]
   `posthoc_alternative_invalid`: if the fixed mixture in the rejection rule is
   replaced by the maximum over models of the likelihood, a true model is rejected
   with probability 1 at α = 1/2. [exp] In the noisy biochemical demo
   (`results/demo_noisy.txt`), the post-hoc rule's false-certification probability
   is 0.0586 > α = 0.05. The mixture rule stays at 0.0027 ≤ α. At α = 1/5 the
   post-hoc rule happened to stay below α, so the failure depends on the instance
   and cannot be detected by testing one α.

2b. **Nuisance elimination needs the splitting hypothesis.** [Lean]
   `nuisance_mixing_counterexample`: one experiment that reports `a xor z` makes
   the query identifiable on a nuisance section but impossible on the product.
   Projecting away nuisance factors is therefore unsound unless every experiment
   depends on only one factor.

4. **Certification is not truth.** [Lean] `certified_does_not_imply_truth`.

5. **Vacuous certification over an empty version space.** [Lean]
   `empty_certifies_everything`: both C and ¬C hold over ∅. The engine therefore
   reports INCONSISTENT instead of certifying (`classify_sound`, `checkCertified`
   requires nonemptiness).

6. **"Two distinguishable models ⇒ identifiable query" is false.** [Lean, via
   `identifiable_iff`] Identifiability requires *every* equivalence class to have
   query spread ≤ ε. The restricted biochemical and observational-only causal
   demos are concrete instances: many pairs are distinguishable, yet the query is
   not identifiable.

7. **Adaptivity gap is only linear in our families.** [Lean] Pointer family:
   adaptive cost ≤ 2 against nonadaptive cost ≥ n+1, with |E| = n+1 unit-cost
   experiments. With unit costs, any identifiable instance has nonadaptive cost
   ≤ |E| (run everything) and adaptive cost ≥ 1. The gap ratio is therefore at most
   |E|, and the pointer family attains |E|/2. No exponential separation is possible
   in this cost measure. We did not study expected-cost or weighted-cost
   separations.

## Limits of the "optimality without enumeration" programme

8. **The sandwich does not beat dynamic programming in general.** [exp]
   (`results/benchmarks.json`, `results/report.html`)
   * Random instances (held-out seeds 1000–1009): the core grows to most of K
     (mean core 5.0/8, 7.7/12, 13.1/16, 16.1/20, 19.7/24). The sandwich was faster
     than pruned DP on only 15 of 100 records (ε ∈ {0, 1}, 5 size classes × 10
     seeds; all instances are small and solved in milliseconds by both). There is
     no advantage here.
   * OR family (negative control): the core has n+1 models (provably necessary,
     because every core-supported adversary needs the zero model and all unit
     models). Run times are similar to pruned DP at these sizes, and DP remains
     feasible because the explicit space is only 2^n.
   * The sandwich wins only when the problem's difficulty lives on a small core
     while the explicit space grows multiplicatively (lesion family with nuisance
     switches).

9. **Small core ≠ small certificate.** [informal + exp] For the OR family the core
   has n+1 models. The explicit adversary *table* produced by the engine has
   2^n − 1 entries (n = 2..11 in the benchmarks: 3, 7, …, 2047). Informal argument
   that any adversary table supported on subsets of `orCore` and certifying the
   bound n must contain every set {zero} ∪ U with U nonempty: certifying lb(S) = |U|
   at S = {zero} ∪ U forces, for each probe j ∈ U, the child S \ {unit j} to have
   lb ≥ |U| − 1, because the other child {unit j} has width 0. By induction every
   such subset appears. The compact certificate exists only as a *symbolic*
   adversary (`orLB`, proved in Lean for all n). The executable checker does not
   accept symbolic adversaries. This is the main obstacle to "compact certificates
   for exponentially large hypothesis spaces" in our architecture.

10. **No asymptotic improvement without a symbolic model representation.** [informal]
    Every component of the prototype, including the sandwich, materializes the
    explicit model list. Its cost is therefore Ω(|K|) per validation. The lesion
    speedup comes from avoiding DP over *subsets* of K (exponential in practice).
    It does not come from avoiding K itself. Making validation sublinear requires
    a symbolic K (BDDs, factored models). This was **not implemented**.

11. **The refinement loop's progress lemma is not formalized.** [informal] See
    `THEOREMS.md` §10. Soundness does not depend on it; termination and the
    "≤ |K| rounds" bound do.

12. **Optimal decision trees are NP-hard in general** (Hyafil–Rivest, 1976, for the
    related identification problem). We make no claim of polynomial-time
    optimality certification for general instances. Pruned DP and the sandwich are
    both exponential in the worst case.

## Engineering failures found and fixed during the project

13. **Quadratic validation.** The first sandwich implementation simulated every
    model separately and rescanned the terminal set each time. On the lesion family
    with |M| = 4096 it was *slower* than pruned DP, and the independent checker
    took up to 27 s. Pushing the whole set down the policy tree once, and
    precomputing outcome cells inside the checker from the raw observation table,
    reduced validation and checking to O(|K|·depth) word operations (check time
    for |M| = 8192: 27 s → 0.5 s). Benchmarks recorded before the fix were
    discarded; all reported numbers are from the fixed code.

14. **Causal export restriction.** The 1716-model causal grid is not exported to
    Lean. Only the 36-model post-survey version space is, because `decide +kernel`
    on the full grid was too slow. The Lean theorems for that demo are therefore
    about the restricted space, with the version-space computation done in Python
    (trusted step).

## Tests that found nothing

* 400 random instances: Bellman DP, two independent reference solvers
  (`reference_value`, and `brute_force_value`, which enumerates all policies, on
  134 small instances) and the sandwich agree. The independent checker accepted
  every honest certificate.
* 1122 tampered certificates (understated bound, corrupted policy, weakened
  adversary, core outside K, wrong impossibility pair, …) were all rejected.
  **0 false accepts.**
* Malformed serialized inputs (`tests/test_serialization.py`) were all rejected.
* Lean/Python agreement (`tests/test_lean_agreement.py`): honest certificates were
  accepted by both checkers and tampered ones rejected by both.

Absence of found bugs is evidence, not proof. Only the Lean-side claims are proved.
