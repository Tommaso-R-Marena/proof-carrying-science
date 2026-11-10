# v23 mathematical assurance scope

This is a mathematical **argument** checked by exhaustive small-model testing and independent code, not a Lean kernel proof. Exact probabilities are rational.

## 1. Registered finite experiment

Let `n` be the fixed number of **registered** units (including those who might not be enrolled before stopping). Every unit `i` has fixed binary scientific potential outcomes `Y_i(0),Y_i(1)` and fixed binary policy-report potentials `R_i(0),R_i(1)`. They are different schedules, with no obligation to agree. There is no unit interference, anticipation, or outcome/report instability across counterfactual allocations.

At step `i`, the registered policy has state `s_i`. Given the previously observed reports and allocations, it samples action `A_i` with the registered positive or zero probability `q(s_i,a)`, using fresh randomness conditionally independent of both complete potential schedules and of all previously used random bits. On recording `R_i(A_i)`, the policy decides whether to stop according to the registered table (with forced stopping at the horizon). Otherwise state changes deterministically according to `next_state[s_i][A_i][R_i(A_i)]`.

For a fixed complete potential-report schedule `R`, the stopping procedure induces an exact probability measure `μ_R` on the finite set of **terminal assignment histories** of varying lengths `2,...,n`. Each terminal history `z=(a_1,...,a_t)` has probability

`μ_R(z) = ∏_{i=1}^t q(s_i(z,R), a_i)`,

provided each earlier step does not satisfy the stop predicate and the terminal step does. The complete terminal-path measure normalizes to 1. `law()` enumerates it and verifies normalization.

## 2. Test statistic and fixed-world validity

For any fixed complete scientific schedule `Y` and terminal treatment history `z`, define the integer test statistic

`T_Y(z) = n0(z) * ∑_{i≤t:a_i=1} Y_i(1) - n1(z) * ∑_{i≤t:a_i=0} Y_i(0)`,

with `T=0` when an arm has zero sampled units. This is `n0*n1` times a treated-versus-control difference of observed means, using the actual stopped enrollment. It is an **ordering statistic**, not an estimator asserted to be unbiased for the full registered population.

For the observed random terminal history `Z`, set

`p_(Y,R)(Z) = ∑_{z': T_Y(z') ≥ T_Y(Z)} μ_R(z')`.

**Finite superuniformity:** For any fixed `Y,R`, and any `0≤α≤1`,

`P_(Z~μ_R)[p_(Y,R)(Z) ≤ α] ≤ α`.

Proof: order distinct statistic values in decreasing order and let their probabilities be `q_1,...,q_m`. For a terminal history in the `j`-th score group, the upper-tail p-value is the cumulative mass `q_1+...+q_j`. The union of all groups whose cumulative mass is at most `α` has mass at most `α`. This does not require normality, identical outcomes, or a fixed stopping time. It **does** require the actual randomization and stopping rule to agree with `μ_R`.

## 3. Adversarial latent-world maximization

The observed stopped record contains `A_1:t`, realized reports `r_1:t`, and scientific-outcome intervals. A complete potential-report schedule `R` is compatible if `R_i(A_i)=r_i` for all observed `i≤t`. A complete `Y` is compatible if no more than the preregistered `K` observed scientific outcome labels are violated. Unenrolled units and unobserved counterfactual potential outcomes/reports remain unconstrained binary values. Let `C(E)` be their Cartesian-compatible set.

For a null restriction on the finite registered-population average effect,

`ATE(Y) = (1/n)∑_{i=1}^n (Y_i(1)-Y_i(0)) ≤ h`,

set

`p_robust(h,E) = max_{(Y,R)∈C(E), ATE(Y)≤h} p_(Y,R)(A_1:t)`.

If no compatible null world exists, the outcome is *null-incompatible*, not a fabricated p-value. If the true fixed pair `(Y*,R*)` belongs to `C(E)` and satisfies the null, the robust p-value is pointwise at least `p_(Y*,R*)`, and hence is superuniform. This remains valid with arbitrary dependencies between the scientific and reporting schedules because their entire schedules are treated as fixed, not as independent random variables.

The robust p-curve is monotone in `h`, as enlarging the null's compatible-world set can only increase the maximum. The one-sided lower confidence bound is the smallest grid value `h∈{-1,-(n-1)/n,...,1}` with `p_robust(h)>α`; when the corresponding nonrejection set is empty, the verifier reports `None` rather than an out-of-range lower bound. Under the assumptions above it covers the true registered-population ATE with probability at least `1-α`.

If `P((Y*,R*)∈C(E)) ≥ 1-δ` comes from an independent, valid measurement-calibration argument, unconditional error is at most `α+δ`. The module itself only accepts a **deterministic** miss allowance, and does not derive `δ`.

## 4. Computational and physical boundaries

Exhaustive enumeration grows exponentially, and so the reference implementation hard caps units and model-work estimates. It is not an efficient general-purpose clinical-trial engine. The exact test is conservative (as illustrated by a non-significant four-unit demo). The proof addresses **validity conditional on the specified physical randomization and stopping**. Neither a signature nor a SHA-256 digest proves that the future potential schedules were stable, that reports were authentic, or that unreported/aborted trials did not occur.

The underlying probability principles are established; neither the proof sketch nor the implementation asserts methodological priority.
