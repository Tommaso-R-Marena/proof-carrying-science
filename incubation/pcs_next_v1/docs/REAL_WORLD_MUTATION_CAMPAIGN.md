# Real-world mutation campaign

## Command

```bash
python incubation/pcs_next_v1/scripts/run_real_world_campaign.py
```

## What was tested

| Target | Origin |
|---|---|
| `pcs_pkpd_one_compartment` | PCS example snapshot |
| `pcs_mass_action` | PCS example snapshot |
| `pcs_biopharma_demo` | PCS example snapshot |
| `pcs_pkpd_translation_benchmark` | PCS example snapshot (PK + Emax PD) |
| `pcs_scientific_workflow_v3` | PCS finite-volume transport example |
| Journal Theoph / Puromycin / Indometh | Public redistributed teaching datasets |
| e-Drug3D + OSP DDI + OSP Pediatrics | Public chemistry / observed-PK tables |
| nlmixr2data `theo_sd` + `warfarin` | Public R teaching package subset |
| Packaged PK/PD evidence | Freeze / policy / stale / duplicate-key probes |

Production trees were **not** modified. Mutations run only under `results/real_world_campaign/work/`.

## Deliberate errors

Gross: concentration scale, unit nonsense, causal overclaim, stoichiometry break, `exec`/`eval`, train/test leakage, missing columns, Theoph/Puromycin spikes, inconsistent t½, blank DDI/Pediatrics references, negative CL/DV, policy swap, stale artifact, duplicate JSON keys, CSV value-order swap, PD effect halve, conservation leak, over-tolerance PK scale.

Subtle / gap probes: 1e-9 and 5e-7 within-tolerance scales, clearance unit label-only swap (`L/h`→`mL/min` with value unchanged), treated/untreated label swap, zero concentration dropped by filters, 1e-12 time jitter, correct non-causal claim (must not false-alarm).

## Interpretation

- `CAUGHT` / `MISSED` apply only to mutations with `expected_detection=true`.
- Catch rate = caught / expected-detection probes (boundary controls excluded).
- Near-tolerance perturbations are labeled expected non-detections (`BENIGN_OK`).
- `MISSED` outcomes are reported honestly as detector gaps for this suite.
- Catch rate ≠ production security proof; external lab validation remains OPEN.
