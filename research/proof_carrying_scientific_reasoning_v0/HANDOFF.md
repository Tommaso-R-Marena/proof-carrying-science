# HANDOFF — Phase III

- **Branch:** `research/proof_carrying_scientific_reasoning_v0`
- **Prior head:** `9a1ca9ce` → Phase III commit (this push)
- **PR:** #218 draft
- **CI:** `source-policy` / `verified-public-integration` census failure expected — do not weaken

## Phase III

1. Fixed Belnap ∧ (`both ∧ onlyFalse = onlyFalse`); 16-cell table; `derives_entails4` / `checkCertificate_entails4`
2. Unique premise IDs in Lean checker; `checkCertificate_mathEstablished_false`
3. JSON hardening: duplicate keys, bool schema_version, unknown fields, claimed support ints
4. Exhaustive finite-model tests; proteomics case study

## Reproduce

```bash
bash scripts/check_all.sh
```
