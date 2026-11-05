# One-compartment IV bolus PK/PD computational workflow

**Case ID:** `01_pkpd_one_compartment`
**PCS checks:** `pkpd_contract`, `pkpd_reference_match`
**License:** CC0-1.0

## Assumptions

- Declared model is restricted one-compartment IV bolus + direct Emax.
- Computational replay only; no empirical adequacy claim.

## Expected results

- `pcs certify` emits PASS evidence for both claims (`COMPUTATIONALLY_SUPPORTED`).
- `pcs verify` on the certificate returns valid.

## Negative controls

- `negative_controls/bad_clearance_unit_model.json` fails `pkpd_contract` (clearance has mass/time dimensions).
- `negative_controls/tampered_predictions.csv` fails `pkpd_reference_match`.

## Reproduction instructions

```bash
pcs certify independent_eval/scientific_falsification/casebook/cases/01_pkpd_one_compartment/manifest.json -o /tmp/pcs-sf-01_pkpd_one_compartment
pcs verify /tmp/pcs-sf-01_pkpd_one_compartment/certificate.json
```

## License metadata

```json
{
  "spdx": "CC0-1.0",
  "statement": "All authored fixtures under independent_eval/scientific_falsification are dedicated to the public domain under CC0-1.0. No human participants; no private data."
}
```
