# Negative results, failures and limitations

## Machine-checked obstructions (`RequestProject/AION/NegativeResults.lean`)

1. **N1. The lower-bound principle needs an escape certificate** (`escape_certificate_necessary`).
   Take the deterministic two-cycle on `Bool` with `A = B = ∅`, `D = univ` and `f ≡ 1`. Here `f` is a bounded
   subsolution (`L f = 0`) that is ≤ 1 on `B` and ≤ 0 off `D ∪ B` (vacuously). Yet `hitProb = 0`. The naive claim
   "every bounded subsolution is a lower bound" is therefore false. Theorem 2 has the extra hypothesis
   `L V ≤ −totalRate` on `D` for this reason, and `checkLower` requires an explicit tabulated escape function `V`.
2. **N2. The generator is not a derivation** (`gen_mul`, `leibniz_fails`).
   `L(fg) = f Lg + g Lf + Σ_r a_r Δ_r f Δ_r g`. A concrete one-reaction instance makes the cross term nonzero.
   For reactions that change several modules jointly (for example, `X + Y → Y` changes one module but its rate
   depends on another), a product barrier cannot be verified module by module. This is why the compositional theorem we
   proved (Theorem 6) is a *union* (additive) bound with interval-bounded coupling, and not a multiplicative one.
3. **N3. Infinite-horizon rarity is not safety** (`mm1_hits_surely`). For an M/M/1-type chain with
   `λ < μ`, every level `N` is hit with probability one from every state, although the stationary mass above `N` is
   `(λ/μ)^N`. A barrier with `g(x₀) < 1` cannot exist. All our infinite-horizon claims therefore concern *competing*
   events ("reach `B` before `A`"), with `A` absorbing (extinction) or reached almost surely first with positive
   probability.

## Executable negative tests (`tests/test_checker.py`)

* The recurrent immigration–death chain with no taboo: the synthesiser cannot produce an upper certificate
  below 1 (consistent with N3).
* Corrupted table entries (upper and lower), overclaimed bounds, negative rates, floating-point numbers instead of
  rationals, missing entries, a tail that is too steep (the cell check fails), a decreasing tail (`ρ < 1`), a certificate
  re-labelled with a different model, a missing escape certificate and a changed target are **all rejected**.
* Explosive network `2X → 3X`, `X → 0`: certificates are still produced and accepted. This is correct, because
  hitting probabilities before explosion need no nonexplosion hypothesis. It is a deliberate test that the theory
  does not secretly rely on one.

## Approaches that failed or were abandoned

* **Pointwise checking of the tail.** Checking the generator inequality on sampled states is unsound for an infinite
  region. It was replaced by the falling-factorial orthant check (Theorem 8). Monomial (power-basis) shifting was also
  tried first and abandoned: shifting `x^k` produces mixed signs. Falling factorials shift with nonnegative
  Vandermonde coefficients, so a sign condition on coefficients is sufficient.
* **Taboo states in the synthesis solve (bug, fixed).** An early synthesiser version assigned tail values to taboo
  states inside the box. The resulting certificates were *rejected by the checker*, not accepted. This is an
  example of the checker catching an optimiser bug.
* **Unweighted interface (FSP-style) upper bound.** Bounding the exterior by "probability 1 after leaving the box"
  is valid but loose when the box boundary is close to the typical region. In the small-box Example C, FSP
  gives `U = 7.15e-4` for an event of probability `3.9e-8`. Our weighted exponential tail gives a relative gap of `6.4e-4`.
* **Multiplicative composition of module barriers.** This was abandoned because of N2.
* **Robust certification without the interval drift.** Checking only the nominal parameters is unsound. Checking all
  `2^p` vertices separately is sound for affine rates, but needlessly expensive. The implemented robust check uses a single
  function and a per-state worst case over each interval. This check is executable but not verified (see TRUST_BOUNDARIES).

## Unresolved limitations

* **Finite-horizon probabilities** \(P(\tau_B\le T)\) are not supported. Uniformization with Poisson-tail enclosures was
  planned, but not implemented.
* **No continuous-time path measure is formalised** in Lean. See TRUST_BOUNDARIES §2.
* **Tail template.** Only products of geometric functions `C·∏ρ_i^{x_i}` are supported outside the box. Models whose
  committor tails are not asymptotically geometric (for example, with super-linear degradation, leading to Poisson-like tails) give loose or no
  certificates. Bimolecular *production* (such as `2X → 3X`) works only when the target level is below the explosive
  regime. The synthesiser found certificates for the small explosive test but was not explored further.
* **Toggle switches** (mutual repression with Hill kinetics) are not mass-action. They would need an encoding with
  promoter species, and that was not benchmarked. Example B is a gene-expression burst model, not a toggle.
* **No proved complexity separation.** Certificate size equals the core box size plus O(d) tail data. We did *not*
  prove that FSP or any other method requires asymptotically more resources on any family (see PERFORMANCE.md).
* **Hardness.** We did not formalise any undecidability result. Note that general CRNs simulate register machines with
  arbitrarily small error (Soloveichik–Cook–Winfree–Bruck, 2008). Consequently, no terminating procedure can decide, for all
  networks, whether a given rational threshold bounds a hitting probability. This is cited, not proved here.
