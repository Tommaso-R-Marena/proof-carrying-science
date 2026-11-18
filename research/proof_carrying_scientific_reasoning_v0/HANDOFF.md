# HANDOFF — Phase IV+++ (JsonCert + exhaustive tests)

- **Branch:** `research/proof_carrying_scientific_reasoning_v0`
- **PR:** #218 draft — do not merge

## Closed

1. `JsonCert.lean` — typed post-parse JSON graph → `checkSurface`; soundness + reject unknown keys / deep formulas
2. `checkCertificateJson` in Python model
3. Exhaustive pytest suite (**66** tests)
4. Only irreducible boundary: byte-string `json.loads` / CPython

## Reproduce

```bash
bash scripts/check_all.sh
```
