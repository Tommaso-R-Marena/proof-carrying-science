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

## Additional rigor

- Finite lattice laws in `formal/PCSEpistemic/Lattice.lean` (assoc/absorb/glb/lub/discharge table).
- Typed residual bridges in `formal/PCSEpistemic/Bridge.lean` rejecting computational→continuum raise.
- Executable checker controls in `formal/PCSEpistemic/Checker.lean`.
- Exhaustive Python lattice self-check over all stratum triples.
- Transport OPEN-obligation lift that preserves continuum/empirical residuals.
- JSON schema `pcs/schemas/epistemic_certificate_v1.schema.json` with `scientific_acceptance: false`.
- Isolated verifier script: `scripts/verify_epistemic.sh`.

## Use

```bash
pcs epistemic-kernel-v1 --mode campaign --output /tmp/esca-campaign
pcs epistemic-kernel-v1 --mode campaign --lean-audit --output /tmp/esca-campaign-lean
pcs epistemic-kernel-v1 --mode assess --schema --certificate examples/epistemic_stratification_v1/formal.json --output /tmp/esca-assess
pcs epistemic-kernel-v1 --mode lattice --output /tmp/esca-lattice
pcs epistemic-kernel-v1 --mode transport-lift --output /tmp/esca-transport-lift
pcs epistemic-kernel-v1 --mode bridge --bridge examples/epistemic_stratification_v1/bad_bridge.json --output /tmp/esca-bridge
./scripts/verify_epistemic.sh
```
