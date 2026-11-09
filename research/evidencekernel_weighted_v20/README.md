# EvidenceKernel v20 — Exact inference under nonstationary weighted rerandomization

**Status: isolated research draft, non-authoritative.** This module is stacked on PCS
PR #210 (v17–v19) and uses the v17 exact parser, canonical SHA-256 digest and
binary-outcome statistic. It does **not** modify PCS production checks, Lean proofs,
scientific receiver, trust policies, deployments, or earlier research branches.

## Question and conditional contribution

Earlier EvidenceKernel v19 assumes that every candidate treatment allocation is
IID **uniform**. Actual trial designers may specify a nonuniform, **time-varying,
outcome-blind** allocation schedule before collecting outcomes. Uniform
transcript ranks are invalid under that different design. V20 implements an
exact weighted finite-sample replay for `n<=8` binary-outcome units:

* Each attempt `t` has a registered integer weight `q[t,z] >= 0` for every
  possible balanced-size allocation `z`. All weights and the cap `H` are
  precommitted. Candidate attempts are independent with probabilities
  `q[t,z] / W[t]`, where `W[t] = sum_z q[t,z]`.
* A preregistered baseline-imbalance score decides whether the experiment
  accepts the candidate at attempt `t<H`; otherwise it stops at the cap,
  whether or not the last candidate meets that score.
* The verifier recalculates the **nonuniform final allocation law** and the
  exact conditional right-CDF of the rejected-attempt prefix, conditional on
  the terminal allocation and stopping time. Both use integer arithmetic.
* The right-CDF plays the role of a conservative discrete tie randomizer;
  it is not claimed to be an independent continuous uniform draw.
* The verifier maximizes the exact one-sided p-value over all binary potential
  outcome tables consistent with the observed intervals and `K` possible
  interval misses. It then inverts the weak-null tests to give a conditional
  lower confidence bound on the finite-population average treatment effect.

This does **not** handle outcome-adaptive weights, unknown weights, post hoc
changes, deceptive or rollbackable intake custody, inaccurate pretreatment
covariates, or uncalibrated intervals. Signed bytes and local hashes do not
establish physical randomization or chronology. An externally pinned protocol
hash and an *independently retained, before-outcome* attempt commitment are
both required at the CLI, but their external status is a trust premise.

## Exact mass and ancillary-CDF formulas

Let `A` be the set of baseline-acceptable allocations; `R_t` is the total
registered weight of rejected allocations at attempt `t`. Let `W_t` be the
weight of all allocations and `D = product_{t=1..H} W_t`.

For each possible final allocation `z`, its exact integer mass over denominator
`D` is

```
m_z = sum_{t=1}^{H-1} 1[z in A] q[t,z]
                  (product_{j<t} R_j) (product_{j>t} W_j)
    + q[H,z] (product_{j<H} R_j).
```

This formula marginalizes the unused candidate draws after early stopping.
It is calculated in `O(H^2 * N)` rather than enumerating up to `N^H` tuples.
The verifier checks `sum_z m_z = D` exactly.

Condition on the selected `z` and the observed stop time `t`. The previous
attempts `a_1,...,a_{t-1}` are independently distributed over rejected
allocations with probabilities `q[j,a_j]/R_j`, even when those probabilities
are different from one attempt to the next. In lexicographic order, define

```
M = product_{j<t} R_j
L = sum_{j<t} (product_{h<j} q[h,a_h])
              (sum_{i<a_j, i rejected} q[j,i])
              (product_{j<h<t} R_h)
A = product_{j<t} q[j,a_j]
U_right = (L+A)/M.
```

This is the **right endpoint** of the conditional weighted cumulative
probability at the observed prefix. For every `u in [0,1]`,
`P(U_right <= u | z,t) <= u`. It is a *sub-uniform probability integral
transform*, not a continuous uniform variable. Because it is constructed
only from pre-outcome allocations, its conditional distribution does not
depend on the fixed potential-outcome table.

For any fixed full binary potential-outcome table `Y`, the conservative
upper-tail randomized p-value is

```
p_Y(z,U) = sum_{z':T_Y(z')>T_Y(z)} m_z'/D
         + U * sum_{z':T_Y(z')=T_Y(z)} m_z'/D.
```

This is superuniform under the registered design. Maximizing across every
compatible null `Y` retains superuniformity if the genuine `Y` is among the
compatible models. Inverting those tests yields the conditional one-sided
confidence bound. If interval coverage fails with probability up to `delta`,
control becomes an **assumed** upper bound `alpha + delta`—this module does
not compute or authenticate `delta`.

## A deliberately invalid unweighted-rank analysis

Synthetic five-unit experiment, ten possible allocations, three attempts,
one acceptable balance-score allocation. At the first two draws, candidate
allocation #0 has weight 100 and each other allocation has weight 1. The
third draw has ten equal weights. In an all-zero potential-outcome world,
**all randomization statistics tie**. Correct weighted analysis therefore
reduces to the valid conditional right-CDF.

| Analysis | Probability of rejection at nominal 5% |
| --- | ---: |
| **INVALID** unweighted lexicographic prefix rank on weighted histories | `10300/11881 = 86.69%` |
| Correct weighted right-CDF | `0` |

These results are exact fractions from the finite distribution, not
Monte Carlo estimates. This is a counterexample to a naive extension of v19,
**not** an attack that bypasses v19's uniform-draw protocol validation.
It also illustrates that discrete conservative statistics may have low power.

A separate signed-free synthetic example produces the same complete JSON
report in Python and independently implemented Node.js:
`conditional_p = 864625/8661249`, with no discovery at `alpha = 1/20`.

## Reproduction

Run from repository root with Python >= 3.12 and Node.js >= 20:

```bash
python -m unittest discover -s research/evidencekernel_weighted_v20 -v -p 'test_*.py'
DIR=research/evidencekernel_weighted_v20
PIN="$(cat "$DIR/example_pin.txt")"                  # demonstration pin, NOT externally witnessed
APIN="$(cat "$DIR/example_attempts_pin.txt")"         # demonstration pin, NOT externally witnessed
python -m research.evidencekernel_weighted_v20.kernel \
  "$DIR/example_protocol.json" "$DIR/example_evidence.json" \
  --protocol-pin "$PIN" --attempts-pin "$APIN"
node "$DIR/independent.js" "$DIR/example_protocol.json" \
  "$DIR/example_evidence.json" "$PIN" "$APIN"
```

Tests include brute-force weighted transcript enumeration, the conditional
right-CDF inequality, superuniformity under **every** binary potential-outcome
table in the bounded small designs, exact composite weak-null size checks,
uniform-design regression against v19, zero-probability rejection, the
86.69%-false-positive counterexample, and 24 seeded cross-language comparisons.

## Scope of assurance and novelty

This is conditional finite-population probability theory, not a kernel-checked
formal proof or independently conducted clinical trial. The weighted
probability integral transform and design-based inference have prior art. The
contribution here is a small **fail-closed cross-language implementation**
with a fully reproducible falsification case, intended for independent review.

Relevant context:
- Young et al., *Covariate-adaptive randomization inference in matched designs*, JRSS B 2024, https://doi.org/10.1093/jrsssb/qkae033
- *Selective randomization inference for adaptive experiments*, JRSS B 2026, https://doi.org/10.1093/jrsssb/qkag081

Not addressed: physical assignment authenticity, unknown calibration accuracy,
independent beacon and witness deployment, real biological or clinical impact,
proof of originality, or large-sample treatment-effect computation. V20 caps
potential-outcome enumeration at 8 units; its allocation-law calculation
scales to a 128-attempt, 70-allocation example but the inference engine does
not thereby scale to large clinical trials.
