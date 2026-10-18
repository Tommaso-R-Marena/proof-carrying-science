# ESCA v1 research report

**Branch intent:** independent hard push into stratified compositional assurance
without touching production package authority, open operational issues, or other
active research tracks.

## Claim

Proof-carrying science needs more than package `ACCEPT` and discrete matrix
theorems. It needs an epistemic lattice where:

1. lower-stratum evidence cannot silently promote to higher-stratum claims;
2. certificate composition is meet-bounded and residual-preserving;
3. artifact invalidation reopens dependent support;
4. continuum/empirical/causal obligations remain first-class `OPEN` residuals
   after formal/discrete support.

## Delivered artifacts

- Lean library `formal/PCSEpistemic/` with strata, judgment, composition,
  invalidation, and kernel controls.
- Python receiver `pcs/epistemic_kernel_v1.py` and CLI
  `pcs epistemic-kernel-v1`.
- Deterministic adversarial campaign covering positive support, promotion
  attacks, residual retention, composition, and invalidation.
- Examples under `examples/epistemic_stratification_v1/`.
- Design note `docs/PCS_EPISTEMIC_STRATIFICATION_V1.md`.

## Boundaries

- Not a continuum PDE accuracy proof.
- Not an empirical validation of any dataset.
- Not a causal identification theorem.
- Not a production Lean authority change.
- Scientific acceptance remains false in every exported result.

## Relation to existing PCS work

Complements the discrete transport kernel (which already keeps continuum and
empirical obligations `OPEN`) and the formal-semantics draft composition /
invalidation targets. Does not modify `PCS.Core.Assures`; instead provides a
research stratified judgment intended for later careful integration.
