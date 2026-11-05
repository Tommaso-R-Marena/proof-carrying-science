# Mathematical foundations

## Stoichiometric conservation

Let `σ` be a finite set of species and `ρ` a finite set of reactions.
A stoichiometric matrix is a map `S : σ → ρ → K` over a field `K`.
A **conservation law** is a vector `γ : σ → K` such that

```text
∀ r ∈ ρ.  ∑_{s ∈ σ} γ(s) · S(s, r) = 0.
```

Equivalently, `γ` lies in the left nullspace of `S`.

A **stoichiometric firing** with firing vector `ξ : ρ → K` updates state `x` by

```text
x'(s) = x(s) + ∑_{r ∈ ρ} S(s, r) · ξ(r).
```

**Theorem (conserved_step).** If `γ` is a conservation law, then
`∑ γ(s) x'(s) = ∑ γ(s) x(s)` for every `x` and every `ξ`.

**Theorem (conserved_all_times).** The same pool is invariant under every finite
sequence of firings.

These theorems are rate-law independent: mass-action, Michaelis–Menten, or
adversarial firings are all covered once the update is stoichiometric.

## Elemental pools

Given a formula atom-count vector `A` (e.g. carbon atoms per species), if every
reaction is atom-balanced (`∑ A(s) S(s,r) = 0`), then `A` is a conservation law.
Hence every stoichiometric trajectory preserves total elemental amount.

## Transport reduction

A two-cell exchange `cell0 ⇌ cell1` has stoichiometry `(-1, +1)`. The constant
vector `(1,1)` is a conservation law. Total amount conservation for this
transport fragment is therefore an instance of the same algebra (not a separate
ad-hoc invariant).

## Continuum obligation (OPEN)

Passing from discrete stoichiometric updates to continuum mass-action ODEs
`ẋ = S v(x)` yields `d/dt (γ·x) = γ·S v(x) = 0` *formally*, but PCCA v1 does
**not** certify continuum solvers, Lipschitz uniqueness, or empirical kinetics.
That obligation remains OPEN, complementary to CertNum's interval/ODE line.
