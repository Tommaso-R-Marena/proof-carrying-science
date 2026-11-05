# Trust boundaries

This file lists what a reader must trust in order to accept each claim.

## 1. The Lean kernel and the axioms used

The headline abstract theorems use only `propext`, `Classical.choice` and `Quot.sound`
(`results/axiom_audit.txt`). There are no `sorry`, `admit`, `axiom` or `@[implemented_by]` declarations in
`RequestProject/AION/`.

The concrete certificate theorems (`Examples/{BDcert,GeneCert,XYsmall,XYmain}.lean`, theorem
`sandwich`) also depend on `Lean.ofReduceBool` and `Lean.trustCompiler`, because the
boolean `checkUpper c = true ∧ checkLower A c = true` is evaluated by `native_decide`. Accepting these
four numerical results therefore means trusting the Lean compiler and its runtime (GMP big-integer arithmetic).
The *soundness of the checker* (`checkUpper_sound`, `checkLower_sound`) does **not** depend on
`native_decide`. Only the evaluation of the checker on one specific large certificate does.
The kernel `decide` would need no compiler trust, but it is too slow for certificates with thousands of rationals.

## 2. Semantic gap: discrete path sums versus the continuous-time process

`hitProb A B x` is defined as the least fixed point of first-step analysis on the embedded jump chain.
`PathSemantics.lean` proves that this equals \(\sup_n\) of an explicit probability of hitting within \(n\) jumps, under the
product law on reaction sequences. Hitting events before explosion do not depend on holding times. Hence, for the
*minimal* CTMC, this quantity is \(P_x(\tau_B<\tau_A,\ \tau_B<\zeta)\), where \(\zeta\) is the explosion time. That statement is
standard (the jump chain/holding time construction), but **it is not formalised**. No measure on càdlàg paths is
built in Lean. A reader who wants the continuous-time interpretation must accept this standard
correspondence on paper.

Consequences:
* No nonexplosion hypothesis is needed for any hitting-probability bound. If the process explodes, the bounds
  concern hitting before explosion.
* The statement `expectedTime_le` concerns the recursively defined expected-time functional `timeN`
  (sums of mean holding times \(1/\text{total rate}\)). It is not an integral over a path space.

## 3. Executable components that are NOT verified

| Component | Status |
|---|---|
| `python/aion/synth.py` (Gauss–Seidel solve, rounding, tail search, repair) | untrusted by design; its output is always checked |
| `python/aion/checker.py` | an independent re-implementation of the Lean checker; agrees on all tests, but not verified |
| `python/aion/robust.py` (interval-rate robust check) | executable, **not** verified. The Lean theorem `AffineFamily.robust_supersolution` covers the abstract principle, but no verified checker for interval certificates was built |
| `python/aion/reference.py` (FSP, SSA, exact birth–death) | floating-point/Fraction baselines used only for comparison |
| `python/aion/emit_lean.py` | untrusted. If it mistranslates a certificate, the Lean statement simply concerns whatever network was emitted; read the `def` of the network in the `.lean` file |

## 4. What is not covered at all

* Finite-horizon probabilities \(P(\tau_B\le T)\): uniformization and Poisson-tail enclosures were not implemented.
* Stationary distributions, positive recurrence and geometric ergodicity: only the Foster–Lyapunov mean-exit
  bounds (Theorem 3) are formalised. Nonexplosion is not formalised (it is not needed, see §2).
* Non-mass-action propensities (Hill functions): the abstract theorems apply, but the checker supports only
  mass-action networks.
* Targets other than "species `jB` reaches level `lvl`" with taboo "some species in a given set is 0".

## 5. Modelling trust

All models are synthetic, with illustrative rate constants. No claim is made that they quantitatively describe
a real biological system.
