# HANDOFF — continuous hardening

- **Branch:** `research/proof_carrying_scientific_reasoning_v0`
- **PR:** #218 draft — do not merge

## Latest improvements

1. Formula/Authority/Rule JSON isomorphisms (`toJsonFormula` round-trips, injectivity)
2. `json_semantic_triangle`, `derives_completeness_steps_pos`, `ProofTerm.compile_steps_pos`
3. Belnap `designated_neg` / designated table helpers
4. Depth + parse edge tests — **74** pytest total
5. Irreducible only: byte-string `json.loads` / CPython

## Reproduce

```bash
bash scripts/check_all.sh
```
