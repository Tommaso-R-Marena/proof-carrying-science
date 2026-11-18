# HANDOFF — continuous hardening

- **Branch:** `research/proof_carrying_scientific_reasoning_v0`
- **PR:** #218 draft — do not merge

## Latest improvements

1. **Depth hole closed:** reconstructed step formulas (andI spines) must obey `MAX_DEPTH=64` in Python + Lean `judgmentsDepthOk`
2. **Exhaustive meet:** `meet_exhaustive` / `meet_assoc` / `meet_idem` (6×6)
3. **JsonCert:** unknown keys on premises/steps rejected; Formula depth shared with Syntax
4. **Tests:** andI depth 64/65; v0 meet drift lock — **77** pytest
5. **Irreducible only:** byte-string `json.loads` / CPython
6. **Honest residual:** `Classical.choice` only on surface↔core iff (decLt proof packages)

## Reproduce

```bash
bash scripts/check_all.sh
```
