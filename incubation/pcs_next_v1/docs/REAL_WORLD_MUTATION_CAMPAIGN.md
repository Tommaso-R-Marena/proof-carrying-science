# Real-world mutation campaign

## Command

```bash
python incubation/pcs_next_v1/scripts/run_real_world_campaign.py
```

## Latest scored run

| Metric | Value |
|---|---|
| Mutations | 44 |
| Expected-detection probes | 41 |
| Caught | 41 |
| Missed | 0 |
| False alarms | 0 |
| Boundary controls (BENIGN_OK) | 3 |
| Catch rate | 1.0 |

## New probes (this increment)

Ed25519 bitflip / unpinned signer, frozen experiment-plan tamper, notebook `exec` cell, half-life inconsistency, POG cycles / dangling deps.

## Interpretation

Catch rate is suite-specific, not a production security proof. External lab validation remains OPEN. Production trees were not modified.
