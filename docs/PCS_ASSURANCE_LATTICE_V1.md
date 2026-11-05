# Proof-Carrying Epistemic Composition — Assurance Lattice v1

This research line discharges the long-standing composition and invalidation
targets from [`FORMAL_SEMANTICS_DRAFT.md`](FORMAL_SEMANTICS_DRAFT.md) as an
**executable typed lattice**, not as prose. It is first-party continuation on an
isolated branch. It does **not** modify production package authority, signing
roots, or the Lean v0.6 acceptance path.

## Revolutionary claim (scoped)

Scientific certificates do not compose by concatenating PASS tokens. They compose
by **typed epistemic morphisms** over an assurance lattice:

```text
Γ₁ ; E₁ ⊢ C₁ @ L₁
Γ₂ ∪ {C₁} ; E₂ ⊢ C₂ @ L₂
--------------------------------  (when L₁ discharges the premise use of C₁)
Γ₁ ∪ Γ₂ ; E₁ ∪ E₂ ⊢ C₂ @ L₂
```

Silent promotion across evidence classes is a category error. Computational or
empirical evidence cannot discharge a formal requirement without an explicit
accepted **bridge morphism**. Changed artifacts reopen the dependent cone.

## Strata and strength order

| Evidence stratum | May discharge |
| --- | --- |
| `provenance` | `provenance` |
| `computational` | `computational`, `provenance` |
| `formal` | `formal`, `computational`, `provenance` |
| `empirical` | `empirical` only |
| `unverified` | `unverified` only |

Formal may **strengthen** a weaker integrity/math requirement. Computational may
**never** silently satisfy formal. Empirical is observational and incomparable
with the integrity/math chain except through an explicit bridge.

## Architecture

```text
package JSON
   │  Python receiving gate (fail-closed)
   ▼
evaluate → PASS/FAIL + violation kinds
   │  optional
   ▼
fresh Lean kernel replay of PCSAssuranceLattice.check / Certified
```

Untrusted producers may propose evidence and bridges. Acceptance depends on:

1. exact package schema and OPEN assumptions;
2. independent Python lattice evaluation;
3. optional private Lean replay of literal-only generated proof text;
4. axiom audit limited to `propext` / `Classical.choice` / `Quot.sound`.

## Formal identities

Library: `formal/PCSAssuranceLattice.lean` (Std only; no Mathlib; not imported by
production `PCS` / `PCSAuthority`).

| Theorem | Content |
| --- | --- |
| `check_iff_certified` | Executable `check` iff semantic `Certified` |
| `silent_computational_to_formal_rejected` | Computational cannot discharge formal |
| `silent_empirical_to_formal_rejected` | Empirical cannot discharge formal |
| `bridge_enables_formal_from_computational` | Accepted bridge upgrades computational→formal |
| `composition_intro` | Support + premises + no invalidation ⇒ certified |
| `changed_artifact_blocks_certification` | Changed deps block certification |
| `missing_premise_blocks` | Unsupported premise blocks composition |

Controls: `formal/PCSAssuranceLatticeControls.lean`.

## Engineering surface

| Path | Role |
| --- | --- |
| `pcs/assurance_lattice_v1.py` | Receiver, adversarial campaign, Lean replay, CLI |
| `pcs assurance-lattice-v1` | CLI entry |
| `examples/assurance_lattice_v1/` | Positive, bridged, and forgery fixtures |
| `tests/test_assurance_lattice_v1.py` | Python + kernel gates |
| `research/assurance-lattice-v1/` | Executed experiment evidence |

```bash
pcs assurance-lattice-v1 \
  --package examples/assurance_lattice_v1/composed_scientific_chain.json \
  --output /tmp/al-out \
  --kernel
```

## Explicit OPEN obligations

- Dependency completeness of real scientific workflows.
- Soundness of any accepted bridge morphism outside this package.
- Empirical correspondence / continuum accuracy / clinical adequacy.
- Cryptographic attribution and production package authority.
- Universal composition over unbounded graphs (this kernel is finite-bounded).

A `KERNEL_CHECKED` result is a theorem about the exact finite lattice package.
It is not scientific acceptance.
