# EvidenceKernel v17 — algebraic selection replay and calibrated randomized inference

**Status:** isolated research draft; non-authoritative. This work is stacked on the
EvidenceKernel v16 research PR and does not alter PCS production kernels, Lean
proofs, scientific receiving, approval policies, or deployed services. All
examples and signing/trust inputs here are synthetic or user-supplied. The
registered physical assignment mechanism and randomizer are **not authenticated**.

## Problem and contributions

V16 enumerates all length-`b` candidate-allocation tuples to recover the
allocation law induced by outcome-blind covariate balancing. That is exact but
scales as `N^b` (replacement) or `(N)_b` (distinct draws), where `N = C(n,k)`.
V17 derives a **closed-form count by balance-score group** without examining
any candidate tuple. Its runtime for calculating the assignment law depends on
`N` and the number of distinct scores, not on the number of candidate tuples.
This is a combinatorial engineering improvement, not a new probability theorem.

The second contribution is a single-pass inversion of all binary finite-population
average treatment-effect (ATE) nulls. This gives an exact, one-sided
**heterogeneous-effect confidence lower bound** under the registered selection
design, without imposing a constant individual treatment effect.

The third, more consequential experimental finding is that the nonrandomized
weak-null test can be severely conservative for discrete selected designs.
V17 implements an **independent auxiliary uniform tie randomizer**, yielding
an exact randomized p-value and separately inverted confidence bound. This
technique has substantial prior art; the specific compositional implementation
and adversarial evaluation are the contribution here.

## Exact algebraic selection distribution

Let `s(z)` be the preregistered baseline imbalance of allocation `z`, with
lower scores preferred, and ties resolved by the earliest drawn allocation.
For any score `s`, let:

- `A_s = #{z: s(z) >= s}`,
- `B_s = #{z: s(z) > s}`,
- `m_s = A_s - B_s`.

Every one of the `m_s` equal-score allocations receives the same selected
mass by label-exchangeability of the uniform candidate draws. The exact
*integer count* of tuples selecting a specific member of that group is

```
 IID with replacement:             (A_s^b - B_s^b) / m_s
 ordered without replacement:       ((A_s)_b - (B_s)_b) / m_s
```

Here `(v)_b = v(v-1)...(v-b+1)` and is zero when `b>v`. The denominators for
probabilities are respectively `N^b` and `(N)_b`. These identities reproduce
brute-force enumeration on every small instance tested. In one larger design,
`n=8`, `k=4`, `N=70`, `b=2048`, the implementation computes and independently
cross-checks the exact distribution over `70^2048` possible candidate tuples
without enumerating them. This **does not** mean that potential-outcome
inference scales to thousands of experimental units: latent-world enumeration
is still capped at 8 binary-outcome units here.

## Exact inference and confidence inversion

For each binary potential-outcome table `Y` compatible with the observed
`{0,1,01}` intervals and the permitted number `K` of missed intervals, the
reference test statistic is

```
T_Y(z) = (n-k) * sum_{i in z} Y_i(1) - k * sum_{i not in z} Y_i(0).
```

This is `k(n-k)` times the treated-minus-control sample mean. For a fixed
world, define the conservative and randomized upper-tail masses:

```
p_Y(z)      = P_mu(T_Y(Z) >= T_Y(z))
p_Y,U(z)    = P_mu(T_Y(Z) > T_Y(z)) + U * P_mu(T_Y(Z) = T_Y(z))
```

where `mu` is the exact selected-allocation law and `U=J/M`, with `J`
uniform on `{1,...,M}`, **independent of the entire assignment/outcome
process**. The support `M` and tie rule are pinned in the protocol.
`U` is passed as a separate external CLI parameter, never taken from the
researcher's submitted observation transcript; **this separation alone does
not authenticate independence or randomness**.

For null `ATE(Y) <= h`, v17 computes the maximum of each p-value over all
compatible null worlds and uses exact `Fraction` (Python) or `BigInt`
(JavaScript) arithmetic. Under the true null, valid selected-assignment design,
and correct measured-interval coverage, the true world is among the maximized
worlds, making the robust p-value at least as large as the true-world p-value.
The one-sided lower confidence bound is the smallest attainable ATE cutoff
`h in {-1,-(n-1)/n,...,1}` whose robust p-value exceeds `alpha`.

This lower bound has conditional coverage at least `1-alpha`. If the intervals
cover all required observations simultaneously except on an event of probability
at most `delta`, the **unconditional** failure bound is at most `alpha+delta`.
`delta` and data validity are not established here. If the confidence set is
empty, v17 reports `EMPTY_SET` rather than inventing a bound greater than 1.
Absent a trusted independent randomizer, only the **nonrandomized** calculation
should be used for scientific decisions.

## A sharp demonstration and its honest interpretation

With six units and a two-draw outcome-blind balancing design, the selected
assignment `(0,1,2)` is extremely unlikely: only `2/400` candidate tuples
select it. Treating three recorded outcomes as 1 and the other three as 0
produces a nonrandomized composite-weak-null p-value `1/200` and a lower
95% ATE bound of `1/3`. Using external demo index `J=8` out of `M=16`
produces a randomized p-value `1/400` and lower bound `1/2`.

**This is intentionally a rare-tail synthetic event, not proof of actual causal
discovery or uniformly improved power.** The maximizing weak-null world has
zero effect (`Y(0)=Y(1)` for each unit). In fact, an exact power audit exposes a
weakness of the v16 statistic. In the extreme positive-effect world with
`Y_i(0)=0, Y_i(1)=1` for every unit, the probability of rejecting at a nominal
5% threshold is:

| Procedure | Exact power under the declared design |
| --- | ---: |
| Nonrandomized weak-null test | `1/100 = 1%` |
| Randomized tie test, independent `J ~ Uniform{1,...,16}` | `701/800 = 87.625%` |

This is for this synthetic design and world only. It says nothing about power
in real trials or other allocation configurations. Randomized p-values are
well established; the contribution is exact worst-case weak-null replay,
confidence inversion, and explicit independent-randomness custody boundary.

### An attack showing why independence matters

Under a four-unit zero-effect world with observations fixed as
`(Y0,Y1) = (00,11,00,11)`, always taking `J=1` instead of drawing it uniformly
results in false rejection probability **`2/9 = 22.22%`** at nominal 5%.
The test suite reproduces this exact counterexample. **A protocol with an
operator-selectable or rollbackable auxiliary value is unsound** for the
randomized guarantee. Independent beacon operation and external ledger
retention remain open deployment requirements; v17 cannot verify them.

## Reproduction

Python >=3.12 and Node.js >=20; standard library only. From this directory:

```bash
python -m unittest discover -v -p 'test_*.py'
PIN="$(cat example_pin.txt)"   # DEMO ONLY; not independent preregistration
python kernel.py example_protocol.json example_evidence.json \
  --protocol-pin "$PIN" --external-uniform-index 8 > /tmp/ekv17-python.json
node independent.js example_protocol.json example_evidence.json "$PIN" 8 > /tmp/ekv17-node.json
python -c "import json; assert json.load(open('/tmp/ekv17-python.json')) == json.load(open('/tmp/ekv17-node.json'))"
```

Omitting the external uniform index emits the nonrandomized certificate and
sets randomized outputs to `null`. The runnable sample uses locally chosen
inputs; no signature claims are made for its randomness.

## Testing and security scope

- Independent Python and Node.js implementation agreement for 35 generated
  full inference cases, including randomized variants, plus a `70^2048`
  distribution comparison.
- Exhaustive oracle agreement for bounded small candidate-tuple spaces under
  both replacement laws.
- Exhaustive finite-model confidence coverage for `n=3` and `n=4` using
  nonrandomized inference, and for **all 256 binary potential-outcome tables**
  for an `n=4` randomized-inference configuration (joint over selected
  allocation and independent uniform index).
- Strong negative controls: tampered protocol pins, invalid candidate
  histories, tie-rule changes, unauthorized `J` values, and adversarially
  chosen `J=1` giving 22.22% false-positive rate.
- No formal proof in Lean, independent experiment, instrument attestation,
  randomness service, or production authority integration.

## Prior art and scope of originality

- Morgan and Rubin (2012), *Rerandomization to improve covariate balance in
  experiments*; related finite-population and design-based inference literature.
- Habiger (2011), *Randomised P-values and nonparametric procedures in multiple
  testing*, https://pmc.ncbi.nlm.nih.gov/articles/PMC4239670/.
- Hemerik and Goeman (2018), *Exact testing with random permutations*,
  https://doi.org/10.1007/s11749-017-0571-1.
- Exact finite-population weak-null inference via worst-case potential outcomes
  predates this work. The present system is a small bounded engineering
  composition, not an established new foundational theorem.

**PR scope:** versioned isolated `research/evidencekernel_selective_v17/`
plus a path-scoped workflow. Based on the v16 draft PR, not replacing or
merging it. No key material, external data claims, production APIs, or
changes to existing PCS trust roots.
