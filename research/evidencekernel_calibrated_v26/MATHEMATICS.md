# EvidenceKernel v26 — exact binomial calibration and anytime-valid downstream inference

**Status:** standard finite-sample statistical argument and bounded executable reconstruction, not a Lean theorem, independent review or proof that a physical experiment was randomized correctly. No new probability-theory theorem is claimed.

## 1. Scientific premise: statewise stationarity and separation

For every registered policy state `s`, there exists an unknown constant treatment-assignment probability `p_s ∈ [0,1]`. A separate prestudy calibration phase records `m_s` binary assignment draws, **each conditionally Bernoulli(`p_s`) given all previous calibration history, including states and draws**. The study's fresh treatment assignments have the **same** conditional Bernoulli `p_s` whenever its policy visits state `s`, even conditioned on the entire calibration history, study past, and all fixed potential outcomes. This excludes hidden policy changes, dependence from reusing finite randomness, cohort-dependent assignment probabilities, selective calibration reports, and interventions by the operator.

The calibration phase must precede the study, the order and state labels must be complete, and sample-size policy/alpha budgets must be frozen before seeing calibration draws. The provided SHA-256 pins **do not** establish any of these facts. The confidence statement below is *conditional on this physical premise*.

## 2. Exact one-sided binomial inversion (no floating-point arithmetic)

With `m` calibration draws and `x` treatment successes, for any rational `u=g/D` on a preregistered finite grid, compute the **exact** lower-tail probability

```
F_u(x) = P_{Binomial(m,u)}(S ≤ x)
       = [Σ_{j=0}^{x} C(m,j) g^j (D-g)^{m-j}] / D^m.
```

At nominal per-look error `η>0`, define `U_m(x)` as the **smallest** positive grid point with `F_u(x) ≤ η`, or `1` if no nontrivial candidate exists. This is a conservative discretized Clopper–Pearson one-sided upper confidence bound. For a true fixed `p`, the event `U_m(S)<p` implies `F_p(S)≤η`, because `F_u(x)` decreases as `u` increases. The probability-integral transform for discrete distributions gives `P_p(F_p(S)≤η)≤η`; hence

```
P_p(p>U_m(S)) ≤ η.
```

No union correction is needed across tested **grid values**: the tests are nested in `u`, and the choice of the smallest valid point is an inversion of one tail test. The implementation checks exact integer products and the preceding grid point to ensure the selected ceiling is minimal.

## 3. Correct optional calibration stopping

If the prestudy calibration cohort size may be selected after inspecting draws within a preregistered range `[L_s,H_s]`, a single fixed-size binomial bound used repeatedly is *not anytime valid*. V26 assigns a per-look budget

```
η_s = β_s / (H_s - L_s + 1).
```

For each permitted stopping size, `P_{p_s}(p_s>U_m(S_m))≤η_s`, regardless of how stopping is chosen. Therefore, **without independence between looks**, the union bound gives

```
P(∃ permitted m: p_s>U_m(S_m)) ≤ β_s.
```

`L_s=H_s` recovers the exact fixed-sample bound. Union over policy states yields

```
P(∃s: p_s>U_s) ≤ β_total := Σ_s β_s.
```

The calibration sample-size range is checked against the actual sealed record length. An explicit `fixed_per_state` setting rejects any different length; `anytime_within_registered_range` accepts any length inside the prospective range but spends probability across every allowed look.

**Falsification:** with true `p=1/2`, grid denominator `32`, `β=1/20`, and a calibration operator permitted to inspect after every draw from 16 through 48, reusing an *uncorrected fixed-sample* upper bound results in exact undercoverage probability

```
17440361441103 / 281474976710656 ≈ 0.061960610655 > 0.05.
```

The probability was computed by exact absorbing-state dynamic programming over Bernoulli prefixes; no Monte Carlo sampling. V26's beta-spending method remains within the 5% calibration risk for every stopping time in this range. The bound can be conservative.

## 4. Composition with EvidenceKernel v25

Let the calibrated ceiling vector be `U=(U_s)`. The receiver requires the entire *separately pinned* v25 study protocol to contain the **exact, canonical** `U` in `propensity_upper_by_state`. Any underreported, manually selected, or altered ceiling fails closed. V25 then checks the entire registered stopping and observation history and computes a one-sided anytime-valid lower bound on the finite registered-cohort average treatment effect, using a predictable reference probability and explicit positive-bias allowance when `U_s>q_s`.

Assume the v25 scientific hypotheses: fixed ordered population, stable binary potential outcomes, no interference, treatment assigned independently of the current unit's potential outcomes conditional on past and calibrated state, coverage of at most `K` incorrect measured intervals except with probability `δ_measure`, and correct registered stopping semantics. With `α` total v25 martingale tuning budget, the complete procedure has

```
P(ever false positive lower-confidence claim) ≤ α + δ_measure + β_total.
```

To see this, first take the union of all statewise calibration failures (probability at most `β_total`). On the complementary event, the frozen ceilings dominate all study conditional propensities; because the subsequent fresh study assignment law remains conditionally Bernoulli `p_s` given calibration, the v25 supermartingale argument applies to every preregistered tuning strategy at arbitrary study stopping times (conditional risk `α`). The interval-coverage failure event adds at most `δ_measure`. This is an additive finite-sample error-budget composition, not evidence that `δ_measure` or the physical assumptions hold. The external study receiver's original summary does not include `β_total`; v26 provides the full composed budget separately and never silently treats the two figures as interchangeable.

## 5. Explicit limits

- **Stationarity is not tested:** calibrating a device at `p_s=1/2` does not protect a study whose actual probability changes to `9/10`. Conditional drift, response-adaptive changes within a supposedly fixed state, manipulation, calibration-data selection, or selective stopping outside registered bounds invalidate the premise.
- Fixed calibration sample counts or a bounded range must be registered *before* their outcomes. A hash printed after the data does not prove preregistration.
- A signed/pinned calibration record is not an authenticated external randomness witness; physical assignment and measurement custody are still required.
- If a ceiling is `1`, the calibration information is vacuous. The contract can fail closed using `require_nontrivial_ceiling`.
- The code is bounded research software, not a formally proved Lean checker. The independent JS verifier cross-checks algebra and exact bytes; it is not independent experimental custody.
- The demonstration is **synthetic** and uses deterministic pseudorandom numbers. Its numerical effect estimate is not a biological finding.

Prior art: Clopper and Pearson (1934) exact binomial inversion; confidence sequences, Bonferroni/union bounds and optional-stopping-safe inference; Ville's inequality and predictable martingale tests. This version is a compositional verification implementation, not a claim to have invented these tools.
