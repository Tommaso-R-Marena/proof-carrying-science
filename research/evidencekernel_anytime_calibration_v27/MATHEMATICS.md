# EvidenceKernel v27: one-sided anytime e-mixture and drift-alarm mathematics

**Research prototype; not a new probability theorem, Lean proof, authenticated randomness source, or real-world experimental finding.**

## Assumptions and exact claim

For each policy state `s`, a *prestudy* calibration process has a constant, unknown conditional treatment probability `p_s`. Conditional on all preceding calibration draws (even adaptive sampling decisions), the next calibration bit in that state is Bernoulli(`p_s`). Within the main study the treatment draw for each eligible unit in the state also has conditional probability `p_s`, even given calibration data, all previous assignments/reports, fixed potential outcomes and stopping decisions. This stationarity and external custody assumption is **not** established by our code or hashes. The cohort and scientific measurement assumptions of v25 remain independently necessary.

For a candidate upper bound `u in (0,1)`, a fixed alternative multiplier `c in (0,1)`, `s` treatment bits among `t` calibrations and `f=t-s`, define

\[
L_t(u,c)=c^{s}\left(\frac{1-cu}{1-u}\right)^{f}.
\]

Under the composite null `p>=u`, each increment has conditional expectation

\[
p c+(1-p)\frac{1-cu}{1-u}=1+\frac{(p-u)(c-1)}{1-u}\le1.
\]

Thus `L_t(u,c)` is a nonnegative supermartingale under **any** constant `p>=u`, including at optional calibration stopping times. The preregistered *uniform* finite mixture `M_t(u)=(1/J) sum_j L_t(u,c_j)` remains a nonnegative supermartingale with `M_0=1`. Ville's inequality yields `P_p(sup_t M_t(u)>=1/beta) <= beta` whenever `p>=u`.

For a fixed realized sample, the failure factor `(1-cu)/(1-u)` is nondecreasing in `u` for each `c<1`; successes contribute the fixed `c^s`. Thus `M_t(u)` is nondecreasing in `u`. Search a preregistered rational grid `u=a/D` in ascending order for the first value with `M_t(u)>=1/beta`. If none exists, report the vacuous bound `U_t=1`. For any physical `p in [0,1]`, the event `U_t < p` implies `M_t(p)>=1/beta`; therefore

\[
\Pr_p\{\exists t: U_t<p\}\le\beta.
\]

This is **time-uniform**: no division by the number of allowed calibration stopping points. There is still a union bound **across preregistered states**. Every calculation is performed in exact Python `Fraction` or independent JavaScript `BigInt` rational arithmetic. A precommitted protocol pins the entire mixture and grid; changing ratios after seeing data is invalid.

## Synthetic effect on evidence and inference

We replay the same three 512-draw *synthetic* calibration streams used in v26, but now allow stopping at any sample size from 16 through 512 with the same per-state `beta=1/300` and grid denominator 1000. The result is:

| Calibrated state | v26 per-look CP/union | v27 exact e-mixture |
|---|---:|---:|
| 0 | 0.701 | **0.691** |
| 1 | 0.517 | **0.509** |
| 2 | 0.570 | **0.561** |

Under the same downstream v25 scientific observations and registered tuning parameters, the synthetic one-sided lower ATE increases from **0.1704238049** (v26 anytime union) to **0.2034182217** (v27 mixture). Both use **the same total conditional error budget of 7%**: 5% statistical, 1% externally asserted measurement-coverage risk and 1% preregistered calibration uncertainty. These particular values are not a universal superiority claim. For *fixed-sample* calibration, v26's one-sided Clopper–Pearson inversion can be substantially tighter, e.g. state 0 gives 0.668 versus v27's 0.691. Use the fixed method when a fixed endpoint is genuinely preregistered.

## Optional, separately budgeted in-study drift alarm

For each state and its externally justified ceiling `u<1`, fix alternative ratios `c_j in (0,1)` before data. Set `r_j = u + c_j(1-u)>u`. Define an upper-tail likelihood ratio for main-study assignments in the state:

\[
D_t(u,r_j)=\left(\frac{r_j}{u}\right)^{S_t}
\left(\frac{1-r_j}{1-u}\right)^{F_t}.
\]

Under *any* history-predictable conditional treatment probability `p_i <= u`, the one-step expected multiplier is `1+(p_i-u)(r_j-u)/(u(1-u)) <= 1`. Hence each `D_t`, and its registered convex mixture, is a nonnegative supermartingale. The verifier replays each state-specific subsequence and records the **first crossing** of `1/gamma_s`, rather than checking only the final e-value. A union over states yields at most `sum gamma_s` probability of a false drift alarm **when all ceiling premises really hold**.

The drift check is deliberately **not** used to claim that a calibration cap is correct when there is no alarm. Finite samples cannot prove a stationary physical device or rule out adversarial drift. The monitor marks an alarmed audit as `DRIFT_ALARM_NO_CLAIM`. The scientific type-I budget remains `alpha + delta + beta`; the additional gamma budget describes possible **false alarms**, not extra permission to make scientific claims.

## Security and evidentiary boundary

- All study records and contract values have SHA-256 bindings; the demonstration's pins are generated locally and **do not** establish chronology, witness independence, or physical custody.
- Outcome-dependent manipulation of treatment assignment, selective omission, surrogate errors, changing `p_s` between calibration and trial, or undeclared state changes invalidate the scientific guarantee.
- This finite e-mixture can be conservative; it is not claimed to dominate v26's alternative fixed-sample test or other confidence sequences.
- The independent JavaScript implementation checks arithmetic and serialization against the Python implementation. Common conceptual errors can still evade both; external review and formal proof remain outstanding.
- The entire mechanism is isolated under `research/` and confers no PCS production authority.

Prior mathematical art: Ville's maximal inequality; mixture supermartingales; Howard et al., *Time-uniform, nonparametric, nonasymptotic confidence sequences*, Annals of Statistics 49(2) (2021), doi:10.1214/20-AOS1991; Waudby-Smith & Ramdas, *Estimating means of bounded random variables by betting*, JRSS B 85(2) (2023), doi:10.1093/jrsssb/qkad009.
