# EvidenceKernel v19 — exact stopped-rerandomization inference

**Status:** isolated PCS research draft, stacked on EvidenceKernel v16–v18 / PR #210. No production authority, Lean kernel proof, external measurement authentication, real-world custody, or demonstrated novel foundational statistical theorem. Only synthetic examples.

## Research question

Can we reuse the randomness contained in **rejected, prespecified allocation attempts** for exact inference when the experiment stops early upon finding an acceptably balanced treatment allocation? A fixed-draw design (v18) does not express the random stopping time. A naive uniform-allocation analysis can be anti-conservative when rerandomization changes the final assignment distribution.

This prototype supports IID uniform draws *with replacement*, finite population binary potential outcomes (including heterogeneous effects), a preregistered balance threshold, a hard attempt cap, an exact bound on incorrectly reported binary intervals, and an externally pinned complete draw transcript. No transcript is assumed to have existed before outcomes solely because it hashes correctly.

## Exact stopped design

Let `S` be all `N=C(n,k)` balanced-size treatment allocations; let `G` be the preregistered acceptable set by absolute baseline imbalance; let `R=N-|G|` be the count of rejected allocations. At each attempt draw uniformly from `S` independently. Stop at the **first acceptable** candidate, or at attempt `H` (and then use the final candidate, even if unacceptable).

Every possible terminal transcript of length `t` has probability `N^-t`. For exact rational computation with common denominator `D=N^H`, the final allocation masses are:

```
for each z in G:     w_z = sum(t=1..H) R^(t-1) N^(H-t)
for each z not G:   w_z = R^(H-1)
```

They satisfy `sum_z w_z = N^H`. Calculation is polynomial in `H` and `N`, **not** exponential in the count of complete draw histories. This does **not** remove the v17 bound on enumerating binary latent potential-outcome models (`n<=8`).

## Conditional ancillary randomness with a random stopping time

For a recorded terminal allocation `z` at stop `t`, each of the `R^(t-1)` rejected prefixes is equiprobable **conditional on `(Z=z, T=t)`** under the registered design. Their lexicographic right-endpoint rank is

```
U = rank(prefix among rejected prefixes) / R^(t-1).
```

At `t=1`, `U=1`. For `t>1`, `U` is discrete uniform conditional on `(Z,T)`; averaged across stop times, it is superuniform conditional on `Z`. Thus the tail p-value for a *fixed true potential-outcome table* is conservatively randomized:

```
p = P_design(statistic(Z*) > statistic(Z))
    + U * P_design(statistic(Z*) = statistic(Z))
```

Here the probabilities use the correct stopped-design masses `w_z / N^H`. A p-value for a **composite finite-population null** `ATE<=h` takes the **maximum** of the fixed-world p-values over every compatible binary potential-outcome table satisfying `ATE<=h` and at most the registered `K` mismatching outcome intervals. Inverting this family gives a one-sided lower confidence bound, allowing different effects on different units.

**Proof of conditional validity.** Conditional on a fixed true potential-outcome table, the observed selected `Z` has precisely the stated design law. Conditional on `Z`, the right-endpoint `U` is superuniform, because each conditional-on-`(Z,T)` rank is uniform on finite right endpoints. The upper-tail randomized p-value is therefore superuniform; taking the supremum over compatible null worlds can only increase it when the true world remains compatible. If the true intervals are jointly correct with probability at least `1-delta`, the unconditional false rejection bound is at most `alpha+delta`. The program does **not** estimate or authenticate `delta`.

This theorem is design-specific and conditional on honest candidate randomization, actual preregistration, outcome-blind acceptance, complete externally retained attempts, and valid interval coverage. The compiled code is **not formally verified**.

## Adversarial finding: ignoring stopped selection breaks calibration

For `n=4`, `k=2`, covariates `[0,1,2,3]`, acceptance cutoff 2, and `H=4`, the six possible allocations have stopped-design masses `[64,64,520,520,64,64] / 1296`. Under the fixed synthetic potential-outcome table `[(1,1),(1,0),(1,0),(1,1)]`, and at a nominal 5% threshold:

- Using the **incorrect uniform** final-allocation reference with the same legitimate prefix ranks falsely rejects with exact probability `79/1296 = 6.0957%`.
- Using the **correct stopped-design** reference falsely rejects with exact probability `13/1296 = 1.0031%`.

This is a *constructed counterexample to a naive procedure*, not a real scientific discovery or a general performance estimate.

## Reproduction

Requires Python >=3.12, Node >=20, and the previously stacked v17 code. From the PCS repository root:

```bash
python -m unittest discover -s research/evidencekernel_stopping_v19 -v -p 'test_*.py'
DIR=research/evidencekernel_stopping_v19
PIN="$(cat "$DIR/example_pin.txt")"       # demo-only, NOT independently preregistered
APIN="$(cat "$DIR/example_attempts_pin.txt")" # demo-only, NOT independently witnessed
python -m research.evidencekernel_stopping_v19.kernel "$DIR/example_protocol.json" "$DIR/example_evidence.json" --protocol-pin "$PIN" --attempts-pin "$APIN"
node "$DIR/independent.js" "$DIR/example_protocol.json" "$DIR/example_evidence.json" "$PIN" "$APIN"
```

`test_kernel.py` verifies normalized exact selection counts against enumerated stopping histories, rank uniformity, **global superuniformity over every binary potential-outcome table** for small examples, composite weak-null level for a finite design, the anti-conservative naive counterexample, forged/missing/early-stop transcripts, large exponent scaling, and independent Node/Python agreement.

## Trust boundaries / no promotion

The two SHA-256 pins are supplied separately, but this alone does not establish that a trusted party published them **before outcomes**. A dishonest operator may prepare a different complete history and corresponding pins post hoc. The physical entropy source, candidate exchangeability, outcome blindness, baseline information, calibration, genuine measurements, and independent custody remain external premises. An external, monotonic preregistration / randomness custody protocol is needed before prospective science. The hosted CI verifies code and synthetic assertions only. No PCS scientific authority, data receiver, Lean theorems, deployment, license, or production gate is modified.

## Prior work and novelty limits

This extends the local v17/v18 research implementation. Acceptance–rejection rerandomization, selective randomization inference, finite exact permutation tests, and randomized tie p-values have established prior art. Relevant examples include Morgan–Rubin style rerandomization, *Selective randomization inference for adaptive experiments* (Journal of the Royal Statistical Society B, 2026), and *Langevin-gradient rerandomization* (Statistics and Computing, 2026). Our scope is a checkable composition with explicit stopped-design weights and conditional transcript-rank reuse—not a demonstrated original statistical law or breakthrough.
