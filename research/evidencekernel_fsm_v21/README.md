# EvidenceKernel v21 — exact finite-state adaptive randomization (research)

**Status:** isolated, unmerged, research-only prototype stacked on PR #210. No PCS
production authority or Lean theorem is changed. This code does **not** prove
that an experiment really followed the registered randomization procedure.

## Contribution

V20 allowed a fixed schedule of *independent* per-step candidate weights. This
extends exact heterogeneous binary potential-outcome inference to a bounded,
outcome-blind finite-state Markov policy. A rejected candidate changes the
registered state and can change both the next assignment law and acceptance
criterion. All states, weights, transitions, covariates, and horizon are included
in the externally pinned protocol.

The selected allocation law is computed exactly by transient-state dynamic
programming, rather than by enumerating the N^H attempt histories. An exact
suffix dynamic program then computes the conditional probability of the
lexicographic transcript prefix, given terminal assignment Z and stopping
time T. The resulting right-CDF tie value U is superuniform conditional on
(Z,T), provided the physical randomizer follows the pinned state policy.

For each complete binary potential-outcome world compatible with the observed
intervals (and up to K declared interval misses), the verifier computes:

    p_Y = P_mu(T_Y(Z)>T_Y(z)) + U * P_mu(T_Y(Z)=T_Y(z))

It maximizes this p-value over the worlds satisfying ATE(Y) <= h, then
inverts the null curve for a one-sided heterogeneous finite-population ATE
lower bound. The statistical error guarantee is conditional on real
outcome-blind policy execution and simultaneous interval coverage. If
measurement coverage fails with probability <=delta, the overall bound is
alpha+delta; delta is not established or estimated by this package.

## Exact counterexample

There are six possible allocations. Attempt 1 picks I uniformly; attempt 2
repeats I exactly; attempt 3 independently draws a uniform allocation. Each
attempt is marginally uniform, but the first two attempts are dependent.
Treating their rejected prefix as if it had 36 equally likely possibilities
gives a false rejection probability 1/6 (16.67%) under an all-zero sharp null
at a nominal 5% level. The correctly specified seven-state policy yields
right-CDF values (I+1)/6 and 0% rejection in this constructed case.

This is an attack on misapplying an independent-draw formula; v20 itself
explicitly rejects dependent candidate draws. It is not a bypass of v20.

## Reproduction, scope and limits

The reference Python implementation is in kernel.py. The full separately
packaged v21 research overlay additionally contains an independently
implemented Node.js verifier, signed-*free* synthetic demonstration, and
exhaustive finite-model and differential tests.

Finite caps: n <= 8, states <= 8, attempts <= 64. Rational arithmetic is
exact and no new algorithm is claimed to provide general large-n efficiency.
An externally supplied protocol SHA-256 and attempt-history SHA-256 are
required, but hashes do not prove the inputs were committed before outcomes,
that any hidden attempt was absent, or that the physical assignments were
independent of treatment responses. Real randomizer custody, calibration
and prospective evaluation remain open.

Related prior work includes Simon & Simon (2011) on randomization tests
for adaptive allocations; Bugni, Canay & Shaikh (2018) on covariate-adaptive
inference; and selective randomization inference for adaptive trials. Neither
Markov-state randomization nor discrete randomized p-values are claimed new.
The mathematical proof is a conditional argument, not a Lean-checked theorem.
