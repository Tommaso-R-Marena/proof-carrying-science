# AION — main theorems and their machine-checked counterparts

All theorems below are proved in Lean 4 / Mathlib in `RequestProject/AION/` with no
`sorry`, and no axioms beyond `propext`, `Classical.choice` and `Quot.sound`. The four
concrete certificate theorems also use `Lean.ofReduceBool` / `Lean.trustCompiler`,
which come from `native_decide` (see `results/axiom_audit.txt`).

## Setting (`Core.lean`)

A *jump model* `M : JumpModel S ι` has a state type `S` (countable or otherwise), finitely
many channels `r : ι`, rates `rate r x ≥ 0`, and targets `next r x`. Its formal generator is
\[ (Lg)(x)=\sum_r \mathrm{rate}_r(x)\,(g(\mathrm{next}_r x)-g(x)). \]
For a target set `B` and a taboo set `A`, the quantity `hitN A B n x` is defined by first-step analysis of the
embedded jump chain, and `hitProb A B x = ⨆ n, hitN A B n x`.

**Theorem P (path semantics, `PathSemantics.lean`).** For every `n` and `x`,
`hitN A B n x = ∑_{rs : Fin n → ι} pathWeight n x rs · 1[pathHits n x rs]`. The
`pathWeight`s form a probability distribution on reaction sequences (`sum_pathWeight`). So
`hitN` is the probability, under the explicit law of the stopped embedded chain, that `B` is
visited within `n` jumps before `A`. `hitProb` is the increasing limit of these probabilities.
*Interpretation:* for the minimal CTMC, this equals \(P_x(\tau_B<\tau_A,\ \tau_B<\zeta)\), where \(\zeta\) is the explosion
time. Measure-theoretic path spaces of continuous-time processes are **not** formalised (see TRUST_BOUNDARIES.md).

## Barrier and sandwich theorems (`Barrier.lean`)

**Theorem 1 (barrier upper bound, `hitProb_le_of_supersolution`).** Suppose `g ≥ 0`, `g ≥ 1` on `B`, and
`L g ≤ 0` on the complement of `A ∪ B`. Then `hitProb A B x ≤ g x` for **every** `x`. No boundedness,
integrability or nonexplosion hypothesis is needed. The proof is by induction on the monotone
iterates, so it never applies optional stopping to an unbounded function.

**Theorem 2 (Lyapunov-certified lower bound, `le_hitProb_of_subsolution`).** Assume:
- `f ≤ C`, `f ≤ 1` on `B`, and `f ≤ 0` outside `D ∪ B`;
- `L f ≥ 0` on `D`, with `D` disjoint from `A ∪ B` and having positive total rate;
- `V ≥ 0` with `L V ≤ −(total rate)` on `D` (an escape certificate).

Then `f x ≤ hitProb A B x` for all `x`.
The escape hypothesis cannot be dropped (Theorem N1).

**Theorem 3 (Foster–Lyapunov mean exit bounds).** `expectedJumps_le` states that if `L V ≤ −(total rate)` on `D`, then the
expected number of jumps spent in `D` is at most `V`. `expectedTime_le` states that if `L W ≤ −1` on `D`, then the
expected *time* spent in `D` is at most `W`. Both are stated through the recursively defined
partial expectations `survN` and `timeN`.

**Theorem 4 (`sandwich`, `relative_error_of_sandwich`).** Combining Theorems 1 and 2 gives `f x ≤ P ≤ g x`.
If `U ≤ (1+ε)L`, then both `U/P` and `P/L` are at most `1+ε`.

## Interface / composition theorems (`Composition.lean`)

- **Gluing.** `gen_le_of_le_of_eq` and `gen_le_of_le_on_jumps`: domination by a supersolution at the
  one-jump neighbours, together with equality at `x`, transfers `L ≤ 0`. `gen_min_nonpos`: the minimum of two supersolutions
  is a supersolution.
- **`hitProb_harmonic`.** `L(hitProb) = 0` off `A ∪ B` wherever the total rate is positive.
- **`max_principle`.** This holds on any region with an escape certificate.
- **Theorem 5 (relative-error transfer, `relative_error_transfer_upper/lower`).** Suppose `v` is
  harmonic on an escape-certified region `D` disjoint from `A ∪ B`, and `v ≤ (1+η)·hitProb` outside `D`.
  Then `v ≤ (1+η)·hitProb` everywhere, and the same holds for the lower side. *The relative error of a glued
  core/tail certificate is at most the relative error of its tail data on the interface, independent of how small the probability is.*
- **Theorem 6 (assume–guarantee composition, `compositional_union_bound`).** Module-local
  barriers `φ_i` on local coordinates `π_i` can be checked using only **local** data:
  each rate is known up to an interval that is valid while no module is bad. If every module passes its local check, then
  \(P(\text{some module goes bad before }A)\le\sum_i \varphi_i(\pi_i x)\). The circular
  assumption is discharged because the target is the *union* of the bad sets.
- **Theorem R (robust barrier, `AffineFamily.robust_supersolution`).** For rates that depend affinely on
  `θ ∈ ∏[lo_k, hi_k]`, a single function `g` whose robust drift is at most 0 bounds
  `P_θ` for **every** `θ` in the box. The robust drift is
  `∑_r base·Δ + ∑_k max(lo_k e_k, hi_k e_k)`, which requires one inequality per state and no enumeration of the \(2^p\) vertices.

## Reaction networks and infinite-region certificates (`MassAction.lean`)

- `MACRN d n`: a mass-action network with exact rational rate constants. `toJump` gives its CTMC on
  `ℕ^d`. By `next_add_inp`, the truncated update `x − α + β` is exact whenever the propensity is positive.
- **Theorem 7 (exact exponential factorisation, `genQ_expBar`).** For `e(x) = ∏ρ_i^{x_i}`,
  \[ L(Ce)(x)=C\,e(x)\,P(x),\quad P(x)=\sum_r k_r\Big(\prod_i\rho_i^{\beta_{ri}-\alpha_{ri}}-1\Big)\prod_i (x_i)_{\alpha_{ri}}. \]
  The identity is exact even for reactions that change several species at once.
- **Theorem 8 (falling-factorial orthant certificate, `cellCheck_sound`).** Shift `x = m + t`
  using the falling-factorial Vandermonde identity (`descFactorial_add_vandermonde`, whose
  coefficients are all ≥ 0). If every combined falling-factorial coefficient is ≤ 0, then
  `P(x) ≤ 0` on the whole infinite orthant `{x ≥ m}`. The check is finite and exact.

## Verified executable checker (`Checker.lean`)

**Theorem 9 (`checkUpper_sound`, `checkLower_sound`).** `checkUpper` and `checkLower` are executable functions on
exact rationals. Whenever `checkUpper c = true`, the glued function `c.g` bounds the hitting probability from above at every state of the
infinite network. Whenever `checkLower A c = true`, the function `c.f` bounds it from below. Concrete
certificates exported by `python/aion/emit_lean.py` are validated by `native_decide`
(`Examples/{BDcert,GeneCert,XYsmall,XYmain}.lean`, theorem `sandwich`).

## Examples and negative results

- **Theorem A (`Examples/BirthDeath.lean`, `bd_exact`).** For the linear birth–death chain with
  `0 < λ < μ`, every `N ≥ 1` and every `x ≤ N`, the probability of reaching `N` before extinction is exactly
  \(((\mu/\lambda)^x-1)/((\mu/\lambda)^N-1)\). The result is symbolic in all parameters, and both directions are obtained from Theorems 1 and 2.
- **N1 (`escape_certificate_necessary`).** Without the escape certificate, Theorem 2 is false.
- **N2 (`gen_mul`, `leibniz_fails`).** The exact product rule contains the cross term
  \(\sum_r a_r\,\Delta_r f\,\Delta_r g\). The naive Leibniz rule fails for joint reactions.
- **N3 (`mm1_hits_surely`).** In an M/M/1-type chain with λ < μ, every level is reached with
  probability **one**, even though its stationary probability \((\lambda/\mu)^N\) is tiny. Rarity over an infinite horizon is therefore not
  safety.
