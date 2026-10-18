# Real-world mutation campaign

## Command

```bash
python incubation/pcs_next_v1/scripts/run_real_world_campaign.py
```

## Latest scored run

| Metric | Value |
|---|---|
| Mutations | 37 |
| Expected-detection probes | 34 |
| Caught | 34 |
| Missed | 0 |
| False alarms | 0 |
| Boundary controls (BENIGN_OK) | 3 |
| Catch rate | 1.0 |

## Targets

PCS examples (PK/PD, mass-action, biopharma, translation benchmark, workflow v3), journal Theoph/Puromycin/Indometh/e-Drug3D, OSP DDI+Pediatrics, nlmixr2data (`theo_sd`, `warfarin`, `Bolus_1CPT`), packaged evidence, metamorphic PK, evidence-store tamper, OSP CL/AUC synthetic, proof-gated certificates, unit adapter↔oracle differential.

## Detectors

Unit-aware PK, nonnegative/longitudinal integrity, group-label registration, Emax PD adapter, conservation adapter, metamorphic dose homogeneity, evidence-chain verify, OSP CL≈Dose/AUC (coarse).

## Interpretation

Catch rate is suite-specific, not a production security proof. External lab validation remains OPEN. Production trees were not modified.
