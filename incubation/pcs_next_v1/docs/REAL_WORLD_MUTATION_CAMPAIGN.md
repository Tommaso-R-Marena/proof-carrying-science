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
| nlmixr2data `theo_sd` + `warfarin` + `Bolus_1CPT` | Public R teaching package subset |
| Packaged PK/PD evidence | Freeze / policy / stale / duplicate-key probes |
| Unit conversion adapter↔oracle | Differential check |

Production trees were **not** modified. Mutations run only under `results/real_world_campaign/work/`.

## Detectors hardened after gap probes

| Former gap | Detector |
|---|---|
| Clearance unit label-only (`L/h`→`mL/min`) | `challenge_clearance_unit_value_consistency` (unit-aware PK) |
| Puromycin treated/untreated swap | `check_labels_against_registration` |
| Indometh zero concentration | `check_nonnegative_concentrations` |
| Warfarin / Bolus 1e-12 time jitter | `check_subject_time_integrity` |

## Deliberate errors

Gross and subtle mutations across the targets above, plus near-tolerance boundary controls (expected BENIGN_OK).

## Interpretation

- `CAUGHT` / `MISSED` apply only to mutations with `expected_detection=true`.
- Catch rate = caught / expected-detection probes (boundary controls excluded).
- Catch rate ≠ production security proof; external lab validation remains OPEN.
- Lean `PcsNext.Units` and `PcsNext.Conservation` are discrete Nat fragments, not IEEE/runtime proofs.
