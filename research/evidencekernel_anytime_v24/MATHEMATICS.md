# v24 mathematical assurance argument (not a Lean kernel proof)

All inequalities below refer to an externally fixed finite cohort, stable
binary potential outcomes and a physically correct predictable randomized
allocation mechanism. There is no assumption that policy-driving reports
are identical to scientific outcomes, or even deterministic. `K`-miss
coverage and the stated `delta` are separate **unverified** premises.

## 1. Filtration and inverse propensity weighting

Let `n` be the preregistered number of ordered units. For every `i<=n`, let
`Y_i(0),Y_i(1) in {0,1}` be fixed potentials and `tau_i=Y_i(1)-Y_i(0)`.
Let `F_(i-1)` contain all history prior to choosing treatment for unit `i`,
including previous outcomes, policy feedback and any external state.
The registered, physically correct probability `p_i=P(A_i=1 | F_(i-1))`
is measurable with respect to `F_(i-1)` and lies strictly between 0 and 1.
The current assignment uses conditionally fresh randomness. Reports may be
arbitrarily stochastic and history-dependent, provided they arrive after the
current assignment and affect only later actions/stopping.

Define

`H_i = A_i Y_i(1)/p_i - (1-A_i) Y_i(0)/(1-p_i)`.

Then `E(H_i | F_(i-1)) = Y_i(1)-Y_i(0) = tau_i`. Thus `D_i=H_i-tau_i`
is a martingale difference. Given the past, `D_i` lies in an interval of
width at most `W_i = 1/p_i + 1/(1-p_i)`; `W_i` is predictable. Hoeffding's
conditional lemma yields

`E[ exp(lambda D_i - lambda^2 W_i^2/8) | F_(i-1) ] <= 1`.

Therefore, for a **fixed preregistered** `lambda>0`,

`E_t(lambda) = exp(lambda sum_(i<=t) D_i -
                   lambda^2 sum_(i<=t) W_i^2/8)`

is a nonnegative supermartingale with starting value 1. Ville's inequality
bounds `P(exists t: E_t(lambda)>=1/alpha_j) <= alpha_j`, including any
stopping time based on actual historical reports or outcomes.

## 2. Exact-rational exponential certificate

Rather than evaluating `exp` or `log` numerically, the protocol includes
positive rational `lambda_j`, a rational error spend `alpha_j`, and a rational
`c_j>=0` with a finite-Taylor lower-bound witness:

`sum_(k=0..m) c_j^k/k! >= 1/alpha_j`, with `1<=m<=32`.

Because all omitted Taylor coefficients are nonnegative, `exp(c_j)>=1/alpha_j`.
This witness is checked with Python `Fraction` and independently with Node
`BigInt`. It follows that

`B_t,j = c_j/lambda_j + (lambda_j/8) sum_(i<=t) W_i^2`

is a simultaneous upper bound for `sum_(i<=t) D_i`, except on a crossing
event of probability at most `alpha_j`. More precisely,

`P(exists t: sum D_i >= B_t,j) <= alpha_j`.

For a registered finite family of tuning choices with
`sum_j alpha_j <= alpha`, a union bound gives simultaneous validity for all
`t` and all `j`. Choosing the best resulting lower bound **after seeing data**
is sound only because its entire tuning family and cumulative spending were
fixed and checked in advance.

## 3. Incorrect measurement intervals and early stopping

For the recorded treatment bit and interval label, let `(l_i,u_i)` be `(0,0)`,
`(1,1)`, or `(0,1)`. The signed inverse-propensity lower contribution is

`L_i = A_i l_i/p_i - (1-A_i) u_i/(1-p_i)`.

When that interval is correct, `L_i<=H_i`. Even when it is incorrect, its
maximum excess above `H_i` is at most

`C_i = A_i l_i/p_i + (1-A_i) (1-u_i)/(1-p_i)`.

If at most `K` of the `t` observed intervals are wrong, then *deterministically*

`sum_(i<=t) H_i >= sum_(i<=t) L_i - topKsum(C_1,...,C_t)`.

This remains valid when interval errors are dependent or adversarial, as long
as their total count is bounded. A physical calibration protocol must justify
that count with simultaneous coverage probability at least `1-delta`.

After stopping at observed `t<=n`, each unobserved unit has
`tau_i >= -1`. Consequently, on the simultaneous noncrossing event,

`ATE_n = (sum_(i=1..n) tau_i)/n`

`>= [ sum_(i<=t) L_i - topKsum(C) - B_t,j - (n-t) ] / n`

for every registered `j`. The verifier takes the **maximum** over `j`.
For every actual stopping time consistent with the protocol, the bound fails
with probability at most `alpha` when all interval-count premises hold;
unconditionally it fails with probability at most `alpha+delta` by the union
bound **if** the physical `delta` premise is valid. The added risks need no
independence assumption.

For the finite-population weak null `ATE_n <= h`, rejection occurs only if the
computed one-sided lower bound is **strictly greater than h**. This is not a
claim that the derived lower bound is tight, or that evidence is sufficient
when no rejection occurs.

## 4. What is and is not established

- The proof is mathematical reasoning, backed by exact arithmetic and finite
  exhaustive tests; the theorem has **not** been formalized and checked in
  the Lean kernel.
- The tail bound follows known work: conditional Hoeffding, test
  supermartingales, Ville (1939), and time-uniform confidence sequences
  (Howard et al., Annals of Statistics 2021). Inverse-propensity adaptive
  experimental designs have established statistical prior art, including
  Cook, Mishler and Ramdas (CLeaR 2024). No theoretical priority is claimed.
- The cohort must be fixed and ordered *before* data collection. Outcomes
  may depend on assigned treatment but not earlier units' treatments,
  enrollment, or observed policy reports. If the population changes based on
  trial history, the proof does not apply.
- The assignment probability must describe the **actual** conditional law,
  not merely a nominal randomized algorithm recorded in the repository.
  A hash pin does not establish this physical claim or its chronology.
- `delta` is not empirically derived in this module. Its numeric value in the
  synthetic examples is a declared assumption, **not calibration evidence**.
- The observed-record integrity check does not guarantee no hidden excluded
  subjects or aborted earlier studies.
