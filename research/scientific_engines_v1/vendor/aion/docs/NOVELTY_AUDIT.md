# Novelty audit

**Access caveat.** This work was done without internet access. The 2026 sources listed in the request (the
partition method in *Math. Biosci.*, Filtered FSP in SIAM, the neural rare-event tracker in *Phys. Rev.*, the
perturbation bounds for augmented truncations, and the Ripple and CRNT-Lean repositories) **could not be read**. The comparison
below relies on knowledge of the literature up to the model's training data, and on the titles given in the request.
Any novelty statement here is provisional. It must be re-checked against those papers before submission.

## Classical ingredients (NOT claimed as new)

| Ingredient | Standard source |
|---|---|
| Hitting probabilities as the minimal nonnegative solution of first-step equations; supersolution ⇒ upper bound | Norris, *Markov Chains* (1997), Thm 1.3.2/1.3.5; potential theory of Markov chains |
| Supermartingale/barrier certificates for reachability probabilities | Kushner (1967); Prajna–Jadbabaie–Pappas (2007); many later works on stochastic barrier certificates |
| Foster–Lyapunov drift ⇒ finite mean exit times | Foster (1953); Meyn–Tweedie |
| Maximum principle / uniqueness of bounded harmonic functions under recurrence-type conditions | classical |
| Finite state projection and its error bound | Munsky–Khammash (2006); stationary variant Gupta–Mikelson–Khammash (2017) |
| Exponential test functions for reaction networks, Lyapunov functions for CRNs | Gupta–Briat–Khammash (2014), Anderson et al. |
| Falling factorials and mass-action propensities | standard combinatorics; the Vandermonde identity |
| Union bound for a union of bad events | elementary |
| Vertex sufficiency for affine parameter dependence | elementary convexity |

Reproducing these in Lean is *formalisation*, not new mathematics.

## What may be new (to be verified against the inaccessible 2026 papers)

1. **A certificate format for infinite-state rare-event sandwiches, with a Lean-verified checker.** The format has:
   - a finite exact core table;
   - a product-geometric tail on the infinite exterior;
   - a falling-factorial sign check proving the drift inequality on whole orthant cells;
   - a tabulated escape (Lyapunov) certificate for the lower bound.

   The checker `checkUpper`/`checkLower` is proved sound with respect to the hitting probability of the *infinite*
   jump chain (`checkUpper_sound`, `checkLower_sound`). We do not know of a prior machine-checked checker
   of this kind for reaction networks. Ripple and CRNT-Lean (not inspected) appear to target deterministic and limit
   theory, not certified rare-event bounds.
2. **Exact factorisation `L(C∏ρ^x) = C∏ρ^x·P(x)`, combined with falling-factorial cell shifting**, used as a
   *sound decision procedure* for the infinite tail. Each ingredient is elementary. We are not aware of this
   specific nonnegative-coefficient shift being used as a verified tail check, but we cannot exclude it.
3. **The relative-error transfer principle (Theorem 5) as a design rule.** The relative error of a glued
   core/tail certificate is bounded by the relative error of its tail data on the interface, independent of the
   size of `P`. Mathematically this is a short consequence of linearity and the maximum principle. Its value is that it
   explains why the observed relative gaps (≈1e-7) do not degrade as `P` drops from 1e-3 to 1e-25.
4. **Weighted versus unweighted interface.** The upper bound charges exiting mass with a certified tail value,
   instead of charging it with 1 as FSP does. It is similar in spirit to augmented truncations and to the 2026 partition method (whose
   content we could not check). This point is the **most likely to overlap with existing work**.
5. **An assume–guarantee union bound for module-local barriers with interval-bounded coupling** (Theorem 6). It is
   simple, and we expect it to be essentially known in the barrier-certificate and compositional verification
   literature.

## What was NOT achieved (relative to the request's Tier 3 criteria)

* No proved computational separation from FSP or any strong method.
* No finite-horizon (time-bounded) certification.
* No formalised continuous-time process (the result is about the embedded jump chain; see TRUST_BOUNDARIES).
* No toggle-switch or Hill-type model.
* No verified robust checker. Only the abstract robust theorem is verified.
* Rare-event comparisons against importance sampling, splitting or neural methods were not run.

## Tier assessment

**Tier 1 (substantial formalisation): achieved.** **Tier 2 (serious original research): partially.** The
contribution is a verified certificate method with some demonstrated advantages over same-box FSP. Its novelty
depends on the unread 2026 literature. **Tier 3: not achieved.**
