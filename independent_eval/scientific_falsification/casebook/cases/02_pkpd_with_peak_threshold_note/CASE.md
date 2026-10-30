# PK/PD workflow with peak-threshold declaration (v0.6 note)

**Case ID:** `02_pkpd_with_peak_threshold_note`
**PCS checks:** `pkpd_contract`, `pkpd_reference_match` (classic); `pkpd_peak_concentration_threshold` (v0.6 declaration)
**License:** CC0-1.0

## Assumptions

- Computational model only; peak bound is a table property, not clinical safety.

## Expected results

- Classic certify/verify PASS for contract+match. Peak check is declared for v0.6 path.

## Negative controls

- Tampered predictions fail reference match (see case 01 negatives pattern).

## Reproduction instructions

```bash
pcs certify independent_eval/scientific_falsification/casebook/cases/02_pkpd_with_peak_threshold_note/manifest.json -o /tmp/pcs-sf-02
pcs verify /tmp/pcs-sf-02/certificate.json
```

## License metadata

```json
{
  "spdx": "CC0-1.0",
  "statement": "All authored fixtures under independent_eval/scientific_falsification are dedicated to the public domain under CC0-1.0. No human participants; no private data."
}
```
