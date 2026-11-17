# HANDOFF — Phase IV+ (verify / break / fix)

- **Branch:** `research/proof_carrying_scientific_reasoning_v0`
- **PR:** #218 draft — do not merge
- **CI:** sealed-census failures expected — do not weaken

## Latest

1. Documented break catalog: `verification/EQUIVALENCE_BREAKS.md`
2. **Fixed (kernel):** classical `Entails` explodes on `demoΓ`; `¬ Entails4 demoΓ (atom 99)`; `traceValid` vs abstract `Certificate.valid`
3. **Locked (tests):** v1.meet ≡ authority.meet (6×6); andE-on-atom; WF empty steps / step-id; claimed authority & math_established; bool schema_version
4. Honest `PythonCheckerModel` docs (rfl = structured algorithm only)
5. `check_all.sh` audits phase4 log for `sorryAx`

## Reproduce

```bash
bash scripts/check_all.sh
```

Expect: Lean OK (no sorryAx), 46 pytest, isolation OK.
