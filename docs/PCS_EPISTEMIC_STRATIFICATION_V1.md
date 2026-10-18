# Epistemic Stratification & Compositional Assurance (ESCA) v1

Research-grade theory and executable kernel. It does **not** grant scientific,
clinical, regulatory, or causal authority, and it is **not** imported by the
production Lean package authority.

## Motivation

PCS already distinguishes formal, computational, empirical, and mixed claim
kinds. The formal-semantics draft further asks for:

1. a composition theorem for `Γ ; E ⊢ C @ L`;
2. an invalidation theorem when artifacts change;
3. no silent promotion across evidence classes.

Discrete transport work additionally leaves continuum accuracy and empirical
validity explicitly `OPEN`. ESCA v1 turns those boundaries into a first-class
ordered epistemic lattice with residual obligations.

## Theory

Epistemic strata, ordered by increasing strength:

```text
integrity < computational < formal < continuum < empirical < causal
```

Judgment:

```text
Assures Γ s C E
```

Evidence may discharge a claim only when `claim ≤ evidence` in this order.
Forbidden promotion (`evidence < claim`) cannot authorize `Assures`.

Composition target:

```text
Γ₁ ; E₁ ⊢ C₁ @ s₁
Γ₂ ∪ {asAssumption(C₁)} ; E₂ ⊢ C₂ @ s₂
-----------------------------------------
Γ₁ ∪ Γ₂ ; E₁ ∪ E₂ ⊢ C₂ @ meet(s₁, s₂)
```

with residual obligations equal to the union of both residual sets plus residuals
implied by the meet stratum. Composition never raises assurance.

Invalidation: if artifact bytes change, every evidence object citing them is
marked `UNVERIFIED` and dependent claims reopen to `OPEN`.

## Architecture

| Layer | Location | Role |
| --- | --- | --- |
| Lean reference theory | `formal/PCSEpistemic/` | Strata, `Assures`, anti-promotion, composition, invalidation, controls |
| Python receiver | `pcs/epistemic_kernel_v1.py` | Fail-closed assess/compose/invalidate/campaign + optional Lean audit |
| CLI | `pcs epistemic-kernel-v1` | Deterministic evidence export |
| Campaign | `--mode campaign` | Positive support, promotion attacks, residual retention, composition, invalidation |

The Lean library is intentionally **not** part of the production `PCS` Lake
default target. The Python receiver can compile it in an isolated temporary Lake
package and audit principal axioms against `{propext, Classical.choice, Quot.sound}`.

## Principal results

- `computational_cannot_assure_empirical`
- `formal_cannot_assure_continuum`
- `continuum_cannot_assure_causal`
- `formal_support_keeps_continuum_residual`
- `compose_meet_le_left` / `compose_meet_le_right`
- `compose_preserves_downstream`
- `single_touched_cannot_assure` / `all_unverified_cannot_assure`
- Controls: positive formal support, promotion rejections, composition meet,
  invalidation reachability

## Non-claims

- No continuum PDE accuracy theorem is proved here.
- No empirical dataset is validated.
- No causal identification result is claimed.
- No production package authority change is made.
- Signed bytes remain distinct from stratified support; stratified support remains
  distinct from scientific acceptance.

## Use

```bash
pcs epistemic-kernel-v1 --mode campaign --output /tmp/esca-campaign
pcs epistemic-kernel-v1 --mode campaign --lean-audit --output /tmp/esca-campaign-lean
pcs epistemic-kernel-v1 --mode assess --certificate examples/epistemic_stratification_v1/formal.json --output /tmp/esca-assess
```
