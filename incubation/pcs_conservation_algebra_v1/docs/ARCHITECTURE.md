# PCCA architecture

```
 Untrusted producer                 Independent receiver              Authority surface
 ┌──────────────────┐               ┌──────────────────────┐          ┌─────────────────┐
 │ contract JSON    │──bytes───────▶│ rebuild S            │          │ Lean theorems   │
 │ formulas         │               │ elemental / nullspace│─────────▶│ conserved_step  │
 │ proposed γ       │               │ Euler → fire replay  │          │ check_sound     │
 │ trajectory CSV*  │               │ emit pcca-cert-v1    │          │ Controls        │
 └──────────────────┘               │ re-check certificates│          └─────────────────┘
                                    └──────────┬───────────┘
                                               │
                                               ▼
                                    Python checker (no producer verdict)
```

\*Trajectory is optional; when present it must be exactly reconstructed as
stoichiometric fires. Continuum accuracy remains OPEN.

## Layers

1. **Algebra** — stoichiometric matrix `S`, conservation laws `γᵀS = 0`, pool `γ·x`.
2. **Dynamics** — fire `x ↦ x + Sξ`; iterate; Euler mass-action is one schedule of ξ.
3. **Elemental** — formula atom vectors that annihilate `S`.
4. **Certificate** — `pcca-cert-v1` JSON with claim + witness; checker recomputes.
5. **Lean** — general theorems + finite controls; axiom-audited.

## Isolation

All code under `incubation/pcs_conservation_algebra_v1/`. Production PCS,
CertNum, PGSC/PGSI and website trees are forbidden touch targets
(`scripts/noninterference_check.sh`).
