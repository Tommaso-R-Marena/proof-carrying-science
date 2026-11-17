# Belnap conjunction correction

## Counterexample (old table)

Previous Lean `TruthValue.and` used `| .both, _ => .both`, so:

`both ∧ onlyFalse = both` (**incorrect**).

## Standard component definition

`T ∈ a∧b ↔ T∈a ∧ T∈b`  
`F ∈ a∧b ↔ F∈a ∨ F∈b`

Hence `both ∧ onlyFalse = onlyFalse`.

## Evidence

- Lean: `both_and_onlyFalse`, `and_truth_table` (16 cells), `and_comm`, `and_assoc`, `and_idem`
- Python: `scientific_reasoning/belnap.py` + `tests/test_belnap_and_json.py`

## Soundness

`derives_entails4 : Derives → Entails4`  
`checkCertificate_entails4`  

Classical `Entails` remains separate (vacuous on inconsistent Γ).
