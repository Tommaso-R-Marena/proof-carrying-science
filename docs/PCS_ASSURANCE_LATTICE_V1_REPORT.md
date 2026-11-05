# Assurance Lattice v1 — Executed Experiment Report

This report records the first executed proof-carrying epistemic composition
campaign. It is a research result about a finite typed lattice, not a scientific
acceptance record and not a production authority change.

## What was built

1. **Theory.** Strength-ordered evidence strata with fail-closed silent-promotion
   rejection, typed composition, bridge morphisms, and invalidation duals.
2. **Architecture.** A receiving lattice kernel beside (not replacing) existing
   v0.6 package authority.
3. **Formalization.** Lean 4.28 `PCSAssuranceLattice` with `check_iff_certified`
   and silent-promotion / composition / invalidation theorems (Std only).
4. **Engineering.** `pcs/assurance_lattice_v1.py`, CLI
   `pcs assurance-lattice-v1`, fixtures, tests, and adversarial campaign.
5. **Experiment.** Kernel-checked positive composition, bridged upgrade, and
   rejected computational→formal forgery.

## Results (acceptance criteria)

| Criterion | Required | Result |
| --- | --- | --- |
| Composed chain Python PASS | yes | yes |
| Composed chain fresh Lean KERNEL_CHECKED | yes | yes |
| Silent formal forgery Python FAIL | yes | yes |
| Forgery grants no kernel support | yes | yes |
| Bridged computational→formal PASS | yes | yes |
| Adversarial false formal accepts on composed package | 0 | 0 |

Exact machine evidence is frozen under
`research/assurance-lattice-v1/final/EXPERIMENT.json`.

## Negative controls that must keep failing

- Computational evidence for a formal requirement without a bridge.
- Empirical evidence for a formal requirement without a bridge.
- Accepted claim whose premise claim lost its evidence.
- Accepted claim whose artifact appears in `changed_artifacts`.

## Limits (honest)

- Finite packages only (≤64 claims, ≤128 evidence atoms, ≤64 bridges).
- Bridge soundness outside the package remains OPEN.
- Dependency completeness remains an assumption, not a proved universal.
- No continuum / empirical / clinical / regulatory claim is established.
- Not wired into production `verify-v06` acceptance.

## Relationship to the founding paper targets

This line instantiates the composition and invalidation theorem targets from
`docs/FORMAL_SEMANTICS_DRAFT.md` §§6–7 as an independently replayable research
kernel, while preserving evidence-class separation from §2.
