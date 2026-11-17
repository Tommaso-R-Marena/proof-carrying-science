# HANDOFF — Phase IV (Python↔Lean equivalence)

- **Branch:** `research/proof_carrying_scientific_reasoning_v0`
- **PR:** #218 draft — do not merge
- **CI:** `source-policy` / `verified-public-integration` census failure expected — do not weaken

## Phase IV

1. Lean model of schema-v1 checker (`PythonCheckerModel`) definitionally `=` `checkCertificate`
2. Completeness: `Derives` ↔ `ProofTerm.interpret`; `compile_ok` / `interpret_checkCertificate` (no `sorryAx`)
3. Equivalence package: `derives_iff_python_certificate` + Entails4 acceptance
4. Docs: `verification/PYTHON_LEAN_EQUIVALENCE.md`; differential harness `tests/test_python_lean_differential.py`

## Reproduce

```bash
bash scripts/check_all.sh
# or:
cd lean && lake build
cd .. && python -m pytest tests/ -q
```
