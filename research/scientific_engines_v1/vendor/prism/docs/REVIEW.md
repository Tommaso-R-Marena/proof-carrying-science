# Adversarial self-review

This document was written as an attempt to falsify the project's headline claims,
following the ten questions of the brief. Each answer either says how the issue
was checked or concedes it.

## 1. Does every theorem say what its description claims?

We checked the headline theorems (`THEOREMS.md`) against their Lean statements by
reading them. Points a reviewer should watch:

* `Succeeds` quantifies over the **true model** `m ∈ K` and inspects the version
  space at which the policy stops, starting from `K`. It does not condition on
  data outside the policy. This matches "terminal admissible version space has
  width ≤ ε for every admissible model/outcome path". Outcome paths are generated
  by models, so the only paths considered are those some model in `K` can produce.
  Infeasible outcomes are never followed, as Part IV requires.
* `value_optimal` and `checkOptimal_sound` quantify over **all** `Policy E O`,
  including non-informative and repeated experiments. Optimality is therefore not
  relative to a restricted class.
* `worstCost` is `Finset.sup` in `ℚ≥0`, so it is 0 on `∅`. On an empty version
  space every policy "succeeds" with cost 0. This is why the engine and checkers
  report INCONSISTENT first. `checkOptimal` does **not** itself reject an empty
  `K`, and `python/verify.py` rejects empty version spaces explicitly. A
  certificate over `∅` would prove only the vacuous statement, which is true.
* The impossibility theorem needs `ε < q m₁ − q m₂`. The order of the two models
  matters only for the sign. `checkImpossible` checks exactly this.
* `identifiable_iff` needs `ε ≥ 0` and `Fintype E`. With infinitely many
  experiments, "run them all" is not a finite policy and the converse can fail.
  We did not study that case.

## 2. Do hypotheses trivialize results?

* Soundness theorems have the form `checker = true → claim`. The checkers are
  ordinary recursive Boolean functions, not definitions that contain the claim.
  `checkPolicy_complete` shows `checkPolicy` is not trivially false, and
  `optimal_certificate_exists` shows that accepted optimality certificates exist
  whenever the value is finite.
* The concrete instances (`Biochem`, `Causal`, `trapCert_ok`) evaluate the checker
  to `true` in the kernel. They are therefore not vacuous.
* `false_certification_le` has the hypothesis `¬ C mstar`, the false-claim case.
  It is a bound on the error probability, not an assumption of success.

## 3. Does an advertised novelty already exist?

Probably yes for all the mathematics; see `NOVELTY_AUDIT.md`. We could not access
the literature. We claim no new theorem.

## 4. Does the implementation match the specification?

* The Python checker is a hand-written mirror of the Lean checker, not extracted
  code. Its agreement with Lean is *tested* (`test_lean_agreement.py`, 6 instances
  per full run), not proved.
* The authoritative path for any single certificate is the Lean export, which
  `python/verify.py --lean` follows. Its residual trust is the emitter
  (`TRUST_BOUNDARIES.md`).
* The Bellman DP in Python (`search/bellman.py`) is unverified, and it does not
  need to be verified: its outputs are certificates.

## 5. Does the checker trust producer output?

No. The Python checker recomputes outcome cells from the raw observation table,
not from the producer's cached masks (fixed during the project), and recomputes
widths and costs. It reads the policy and adversary only as data to verify. The
Lean checker recomputes everything from the `Problem` literal.

## 6. Are benchmark comparisons fair?

* All methods run in the same process, language and time limit (20 s), on the
  same instances.
* The pruned DP baseline is strong (exact branch-and-bound pruning). A weaker
  baseline would exaggerate the gains.
* The **lesion family was designed to favour the sandwich**. We say so, and we
  include the OR family (negative control) and held-out random instances where the
  sandwich does not win.
* We did not compare against MILP/SAT-based optimal decision tree solvers (none
  were available offline). This is a gap.
* Peak memory is measured with `tracemalloc` in separate runs and only for some
  records.

## 7. Is real scientific validity inferred from formal consistency?

No. All demos are synthetic and labelled so, and `certified_does_not_imply_truth`
is part of the formal development.

## 8. Is the generality only finite enumeration?

Largely yes. The deterministic core works with explicit finite model sets. The
sandwich avoids DP over subsets, but it still enumerates `K` for validation. The
only results that are not enumeration are the parametric Lean theorems (`or_value`
for all n, `ptr_*` for all n) and the abstract theorems, which hold for arbitrary
finite types.

## 9. Does the stated complexity match the algorithm?

* Bellman DP: exponential in |K| in the worst case. Memoized on reachable
  sub-version-spaces, which are intersections of cells, so at most the number of
  distinct cell-intersections.
* Validation and checking: O(|K| · depth) bitset operations, plus O(leaf size) per
  leaf (after the fix described in `NEGATIVE_RESULTS.md` §13).
* Adversary checking: O(|table| · |E| · |outcomes|) cell computations, each linear
  in the set size. Table lookups are linear scans (as in Lean `lbOf`), so the total
  is quadratic in the table size. This could be improved with hashing.
* Lean `decide +kernel` checking is far slower than Python: each generated instance
  takes seconds to tens of seconds. This is why the 1716-model causal grid is not
  exported.

## 10. Omitted edge cases?

Tested: empty version spaces, contradictory data, duplicate experiments,
uninformative experiments, identical signatures, zero costs, negative costs
(rejected), malformed and truncated certificates, wrong model identifiers, hash
mismatch, deep policies, non-canonical rationals, duplicate JSON keys.

Not tested or not handled:
* ε given as a non-canonical decimal (rejected by the schema, by design).
* Outcome sets declared but never predicted by any model. These are harmless:
  only feasible outcomes are followed.
* Very large rationals. These are bounded at 4096 digits, and performance is not
  characterized.
