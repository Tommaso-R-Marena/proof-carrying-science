# EvidenceKernel v22: exact causal inference when adaptive reports differ from scientific outcomes

**Research-only; draft; no PCS authority.** This is an additive module stacked on the v16–v21 EvidenceKernel drafts. It neither changes nor strengthens any production Lean theorem, scientific receiver, kernel, or deployed PCS service. Python 3.12+ and Node.js 20+; standard library only.

## The problem

In a response-adaptive experiment, the treatment assignment for patient/unit `i` may depend on a *reported* response from earlier units. That report may be noisy, a surrogate marker, or otherwise distinct from the final scientific outcome. Regenerating the treatment-assignment distribution under the **true** biological outcomes instead of the actual policy-driving **reports** can invalidate a randomization test. Merely knowing the reported values along the one realized assignment path does not reveal what the reports would have been under alternative assignments.

### Contribution

The verifier keeps two distinct fixed potential-outcome schedules for each experimental unit:

- `Y_i(0), Y_i(1)` are binary **scientific** potential outcomes (what the causal claim concerns).
- `R_i(0), R_i(1)` are binary **policy-driving reports** (what determines the next assignment probability).

The full `R` schedule is counterfactual and *unknown*. For each compatible `R`, it reconstructs exactly the potentially nonuniform response-adaptive assignment law `mu_R`, using an externally pinned finite-state protocol. It computes the exact randomization tail probability under each compatible pair `(Y,R)` and uses the **maximum** over all pairs satisfying the proposed ATE null.

This supports heterogeneous scientific effects and a bounded number of missed scientific-outcome intervals, *without* assuming that the reported values equal the scientific truth. Worst-case inference can be conservative. The deterministic report schedule must be fixed independently of the trial's allocation randomness and must remain stable across counterfactual assignments; this is a **physical modeling assumption**, not a property of a hash.

## Exact mathematical argument

Let `Z` denote the complete assignment vector and `mu_R(z)` the probability of `Z=z` when the registered sequential policy interacts with a fixed potential-report schedule `R`. Let `T_Y(z)` be the registered scientific outcome statistic, here `n_control * treated_successes - n_treated * control_successes` (defined as zero when one group is empty). For any fixed true `Y,R`, the exact upper-tail randomization p-value is

```
p_(Y,R)(z) = sum_{z': T_Y(z') >= T_Y(z)} mu_R(z')
```

It is superuniform under `Z ~ mu_R`: `Pr[p_(Y,R)(Z) <= alpha] <= alpha` for any alpha in `[0,1]`. This follows by ordering the finite support by statistic value and observing that each cumulative upper-tail probability is at least the probability mass of the upper-tail event.

The observed allocation and reports constrain `R_i(Z_i)`; signed/labeled scientific intervals and the preregistered `max_interval_misses` constrain `Y_i(Z_i)`. Let `C(E)` denote the resulting set of compatible complete `(Y,R)` schedules. The robust p-value for the weak null `ATE(Y) <= h` is

```
p_robust(E,h) = max_{(Y,R) in C(E) and ATE(Y)<=h} p_(Y,R)(Z)
```

Whenever the actual complete pair is inside `C(E)` and the true ATE is `<=h`, the robust p-value is at least the true-world tail p-value. Thus a test that rejects for `p_robust<=alpha` has rejection probability at most `alpha` **conditional on the complete true pair always being compatible**. If that compatibility fails with probability at most delta, an unconditional bound of `alpha+delta` follows by the union bound. Neither an empirical delta nor externally attested measurement accuracy is derived in v22. The one-sided lower ATE bound is obtained by inverting the complete set of finite `h` null tests. If no null is accepted, it returns `null`, not a fabricated bound.

Both complete verifiers independently calculate all fractions exactly: Python `Fraction` and Node.js `BigInt` rationals. Each recognizes a strict, bounded schema; no LLM or external mathematical oracle is trusted. We do **not** claim a formally kernel-checked proof; exhaustive small models corroborate the argument. Fixed reporting schedules are insufficient for arbitrary *history-dependent* reporting, cross-unit interference, post-hoc changes to the randomization policy, missing trial records, or arbitrary outcome-dependent censorship.

## A failure that matters: 99.31% vs 4.29%

A fully specified synthetic **sharp-null** world uses four units with identical treatment/control true outcomes `Y=(1,0,1,0)` and separate potential reports `R=(0,1,0,0)` independent of treatment. The policy has two states, with action weights `(19,1)` and `(1,19)`; the report sets the next state. Exact enumeration of every assignment gives:

| Method at nominal 5% | Exact probability of rejecting a true sharp null |
|---|---:|
| Invalid shortcut: simulate allocation as if `R=Y` | `158897/160000 = 99.310625%` |
| v22: maximize over every compatible `R,Y` | `6859/160000 = 4.286875%` |

The first method is **not an attack that bypasses an existing version's registered restrictions**: it is an intentionally invalid approach illustrating why the report/truth distinction must be explicit. The second is a **single synthetic finite-world result**, not an average over experiments. Reproduce with `counterexample.py`.

## Running locally

From the PCS repository root with this overlay installed:

```sh
python -m unittest discover -s research/evidencekernel_feedback_v22 -v -p 'test_*.py'
python -m research.evidencekernel_feedback_v22.counterexample
P=research/evidencekernel_feedback_v22
python -m research.evidencekernel_feedback_v22.kernel "$P/example_protocol.json" "$P/example_evidence.json" \
  --protocol-pin "$(cat "$P/example_protocol_pin.txt")" \
  --evidence-pin "$(cat "$P/example_evidence_pin.txt")"
node "$P/independent.js" "$P/example_protocol.json" "$P/example_evidence.json" \
  "$(cat "$P/example_protocol_pin.txt")" "$(cat "$P/example_evidence_pin.txt")"
```

The example pin files are generated **in the same local environment**, so they cannot establish pretrial commitment chronology or independent evidence custody. A production prospective deployment would require external timestamping and independent custody of the protocol, true measurement references, assigned treatments, reports, and withdrawals.

## Relationship to prior work and remaining blockers

Response-adaptive randomization tests and finite-sample exact methods have substantial prior art, including Baas, Jacko, and Villar (2025), *Exact statistical analysis for response-adaptive clinical trials: A general and computationally tractable approach* (https://doi.org/10.1016/j.csda.2025.108207), and adaptive re-randomization work reviewed by Simon and Simon and others. **This is an integrated bounded verification experiment, not a demonstrated novel statistical theorem.** The separated surrogate-report potential-outcome enumeration and transparent counterexample may motivate a focused methodological paper only after a substantial novelty review.

Hard blockers before a scientific authority: independent registration timing, real randomization beacons, complete enrollment and withdrawal records, original surrogate and reference outcomes, calibrated measurement coverage, instrument/proxy behavior under counterfactuals, external validation, and independent review of PCS integration and permission boundaries. No physical experiment is supplied.
