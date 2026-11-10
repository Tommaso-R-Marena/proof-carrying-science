# EvidenceKernel v25 — conditional finite-population anytime inference under propensity ceilings

**Status:** research argument, not a kernel-checked theorem; foundational probability tools have prior art. Binary outcomes and a prospectively fixed, ordered cohort only.

## 1. Filtration and estimand

Fix `n` units, ordered before enrollment, each with fixed binary potential outcomes `Y_i(0),Y_i(1)`. Define `τ_i=Y_i(1)-Y_i(0) ∈ [-1,1]` and `τ̄_n = (Σ_i τ_i)/n`. There is no interference or future-unit reordering. Immediately before assigning unit `i`, the history `F_{i-1}` determines an observable policy state `s_i`, and **the actual conditional probability** `p_i = P(A_i=1 | F_{i-1}, Y(0),Y(1))` exists and satisfies `0 ≤ p_i ≤ u_{s_i}`, where `u_s` is prospectively asserted. This is an assumption on the true *conditional* assignment law, not merely its marginal treatment frequency. The reported feedback may be stochastic, untruthful, or outcome-dependent after assignment, but it must not influence its own earlier assignment beyond the predictable history.

The stopping time `T ≤ n` is determined by registered state transitions, assignments and reports; it must be a stopping time for the observed filtration. The protocol and finitely many analysis strategies are fixed **before** seeing outcome data. A cryptographic SHA256 pin identifies bytes, not chronological registration or physical custody.

## 2. One-sided propensity upper bound

For any predictable `q_i ∈ (0,1)` chosen from a preregistered strategy, put

```
X_i(q) = A_i Y_i(1)/q_i - (1-A_i)Y_i(0)/(1-q_i).
```

Conditionally on the past and all fixed potential outcomes,

```
E[X_i(q)]-τ_i
 = (p_i-q_i) [Y_i(1)/q_i + Y_i(0)/(1-q_i)]
 ≤ max(0,u_{s_i}-q_i) [1/q_i + 1/(1-q_i)] =: b_i.
```

Thus only an **upper** bound on the actual treatment assignment probability is needed for a *lower* effect bound. If `q_i≥u_{s_i}`, then `b_i=0`: the reference estimate is systematically conservative in conditional expectation. This is one-sided; an **upper confidence bound on effects** would instead need complementary control (including a lower bound on `p_i`). It is not valid to infer this premise from marginal treatment counts or to treat it as a cure for confounding.

Because `X_i(q)` lies in `[-1/(1-q_i), 1/q_i]` for binary potential outcomes, its conditional range has width at most `w_i = 1/q_i+1/(1-q_i)`. Hoeffding's conditional lemma yields

```
M_t = exp( λ Σ_{i≤t}[X_i(q) - τ_i - b_i]
           - λ² Σ_{i≤t} w_i² / 8 )
```

as a nonnegative test **supermartingale** for each fixed predictable strategy and fixed `λ>0`. Under Ville's inequality,

```
P(∃t: Σ_{i≤t}τ_i < Σ_{i≤t}X_i(q) - Σ_{i≤t}b_i
                            - c/λ - (λ/8)Σ_{i≤t}w_i²) ≤ α_j
```

if `c≥log(1/α_j)`. To verify that bound without floating-point logarithms, the implementation checks the exact rational inequality `α_j * Σ_{k=0}^m c^k/k! ≥ 1`, whose left sum is a lower bound on `α_j exp(c)` for nonnegative `c`. The test is valid because `exp(c)≥Σ c^k/k!≥1/α_j`. The total registered `Σ_j α_j` cannot exceed `α` and a union bound supports a simultaneous maximum over the strategies.

## 3. Inaccurate intervals and optional stopping

Let each measured outcome be reported as `0`, `1` or `01` (unknown). Define the interval-based lower Horvitz–Thompson statistic `H_T(q)` by using a reported lower outcome if treated and reported upper outcome if control. For each registered unit `i` define `m_i(q)=lower_i/q_i` if treated and `m_i(q)=(1-upper_i)/(1-q_i)` if control. If at most `K` observed intervals omit their actual binary outcome, then pathwise

```
Σ_{i≤T} X_i(q) ≥ H_T(q) - Σ_{K largest} m_i(q).
```

For the remaining `n-T` unobserved registered units, `τ_i≥-1` without assumptions on their outcomes. Consequently, at every registered stopping time `T`, simultaneously across registered strategies,

```
τ̄_n ≥ [ H_T(q) - C_K(q) - Σ_{i≤T} b_i
          - c/λ - (λ/8)Σ_{i≤T}w_i² - (n-T) ] / n
```

except with conditional probability at most `α` if all interval-miss conditions hold. If simultaneous interval-failure allowance `K` holds on an event with probability at least `1-δ`, an unconditional union bound is `α+δ`, **provided** the propensity premise holds. The code merely accepts the stated `δ`: it has not independently proven any calibration coverage.

## 4. Exact robustness frontier

For each strategy, with the observed history fixed, simultaneously relax upper bounds to `u_s(ε)=min(1,u_s+ε)` for `ε ∈ [0,1]`. The only changing part of the certified lower bound is

```
B_q(ε) = Σ_s N_s max(0, min(1,u_s+ε)-q_s) [1/q_s + 1/(1-q_s)].
```

This is a continuous, nondecreasing **piecewise-affine** function whose breakpoints belong to `{0,1}∪{max(0,q_s-u_s),1-u_s}`. All coefficients are exact rationals. The verifier computes the zero crossings of `L_q(ε)-null` exactly within each interval, then reports the maximum frontier over registered strategies. When the initial decision rejects, every `0≤ε<frontier` retains rejection, and the result at the frontier itself is reported separately (strict `>` may become equality). If the original result does not reject, the frontier is `0` by convention. The frontier is **sensitivity to an asserted bound**, not a measured or verified model error.

## 5. Limits and falsification

- Actual conditional treatment probabilities above the asserted ceiling break the premise. In an all-null 64-unit example, claiming `q=u=1/2` when the actual physical treatment probability is `9/10` yields a nominal 5% false-positive probability about 99.999988%. A valid `u=9/10` removes that false-positive result in the same exact construction.
- Stable potential outcomes, predictable assignment, no interference, no selective nonrecorded enrollment, and authentic measurement remain **physical assumptions**.
- Hashes, witness signatures, ordinary test results and same-host validation do not prove independence, time ordering, true propensities, or external calibration. These findings are synthetic.
- The program is not machine-checked in Lean. Conditional supermartingale arguments are given for external scrutiny and need formalization and independent prospective evaluation before any PCS production authority is considered.

**Statistical antecedents:** Horvitz–Thompson weighting; Hoeffding's lemma; Ville's inequality; Howard et al. (2021), DOI `10.1214/20-AOS1991`; Cook, Mishler and Ramdas (2024), CLeaR; propensity-sensitivity literature (e.g., DOI `10.1002/bimj.201100042`). The project does not claim these mathematical ideas are novel.
