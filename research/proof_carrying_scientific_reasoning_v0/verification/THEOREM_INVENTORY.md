# Theorem inventory (Phase III–IV)

Lean **4.28.0**. No `sorry` / `admit` / custom axioms.

| Theorem | File | Claim | Axioms |
|---|---|---|---|
| `and_truth_table` / `both_and_onlyFalse` | Belnap | Correct 16-cell ∧; fixes both∧onlyFalse | none |
| `and_comm` / `and_assoc` / `and_idem` | Belnap | ∧ algebra | none |
| `designated_and` | Belnap | designated(a∧b) ↔ designated a ∧ designated b | propext |
| **`derives_entails4`** | Belnap | Derives ⇒ Entails4 | propext |
| **`checkCertificate_entails4`** | Belnap | check ⇒ Entails4 | propext |
| `checkCertificate_sound` | CheckCertificate | check ⇒ Derives | propext |
| `checkCertificate_implies_entails` | CheckCertificate | check ⇒ classical Entails | propext |
| **`checkCertificate_mathEstablished_false`** | CheckCertificate | accepted ⇒ mathEstablished=false | propext |
| **`checkCertificate_requires_unique_ids`** | CheckCertificate | accepted ⇒ unique premise ids | propext |
| `meet_comm` | Authority | commutative meet | none |
| **`checkCertificatePy_eq_lean`** | PythonCheckerModel | Python algorithm model = Lean checker | none (rfl) |
| **`compile_ok` / `interpret_checkCertificate`** | Completeness | ProofTerm.compile accepted by checker | propext, Quot.sound |
| **`derives_iff_interpret`** | Completeness | Derives ↔ ∃ interpret (unique ids) | propext, Quot.sound |
| **`derives_completeness`** | Completeness | Derives ⇒ ∃ accepted structured cert | propext, Quot.sound |
| **`derives_iff_python_certificate`** | Equivalence | Derives ↔ ∃ Python-model acceptance | propext, Quot.sound |
| **`demoΓ_classically_unsatisfiable` / `classical_entails_atom99_demoΓ`** | Contradictions | Classical Entails explodes on demoΓ | propext |
| **`not_entails4_atom99_demoΓ`** | Belnap | Entails4 does **not** explode on demoΓ | propext |
| **`traceValid_implies_derives` / `traceValid_implies_entails4`** | CheckCertificate / Belnap | Finding D: executable trace validity | propext |
| **`checkSurface` / `checkSurface_iff_checkCertificate`** | Surface | Surface WF+claims ↔ core (bounded) | propext, Quot.sound |
| **`checkCertificatePy_eq_surface`** | PythonCheckerModel | Python model = `checkSurface` | none (rfl) |
| **`hyp_mathVerified_not_established`** | Surface | Finding F (Hyp): declared ≠ established | propext |
| **`meet_truth_table`** | Authority | Exhaustive meet lock | none |

See `PYTHON_LEAN_EQUIVALENCE.md` and `EQUIVALENCE_BREAKS.md`.

## Distinctions

- Classical `Entails` ≠ `Entails4`
- Abstract `Certificate.valid` ≠ executable `checkCertificate`
- Declared authority ≠ `mathEstablished`
- Python **algorithm** Lean-checked ≠ CPython runtime proved
