# HANDOFF — Phase IV++ (close remaining gaps)

- **Branch:** `research/proof_carrying_scientific_reasoning_v0`
- **PR:** #218 draft — do not merge
- **CI:** sealed-census failures expected — do not weaken

## Closed this push

1. Lean `Surface.lean` / `checkSurface` — schema, sizes, step ids, claims, math_established
2. `checkCertificatePy := checkSurface`; `checkSurface_iff_checkCertificate`
3. Unified `meet_tables.py` (v1 + authority); Lean `meet_truth_table`
4. Finding F: `hyp_mathVerified_not_established`
5. Catalog: only irreducible leftovers are `json.loads`/CPython and external attestation

## Reproduce

```bash
bash scripts/check_all.sh
```

Expect: `ALL_OK`, no `sorryAx`, 46 pytest.
