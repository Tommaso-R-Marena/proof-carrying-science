# Unit compatibility for concentration spellings

**Case ID:** `04_unit_compatible_concentration`
**PCS checks:** `unit_compatible`
**License:** CC0-1.0

## Assumptions

- Dimensional compatibility only.

## Expected results

- mg/L vs ug/mL PASS.

## Negative controls

- mg/L vs L/h FAIL.

## Reproduction instructions

```bash
pcs certify independent_eval/scientific_falsification/casebook/cases/04_unit_compatible_concentration/manifest.json -o /tmp/pcs-sf-04_unit_compatible_concentration
pcs verify /tmp/pcs-sf-04_unit_compatible_concentration/certificate.json
```

## License metadata

```json
{
  "spdx": "CC0-1.0",
  "statement": "All authored fixtures under independent_eval/scientific_falsification are dedicated to the public domain under CC0-1.0. No human participants; no private data."
}
```
