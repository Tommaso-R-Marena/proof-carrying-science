import ScientificReasoning.CheckCertificate

/-!
# Lean model of the Python schema-v1 checker

This module names the *structured* algorithm implemented by
`independent_checker/check_certificate_v1.py` (unique ids, LTR step
reconstruction, conclusion index) as Lean definitions.

**Important honesty:** `checkCertificatePy` is currently definitional
(`:= checkCertificate`). That is intentional: the Python LTR core was written
to match Lean `checkStep`/`checkStepsLTR`. The JSON *surface* (schema version,
unknown keys, `step.id == index`, claimed-field checks) is **not** modelled
here — see `verification/EQUIVALENCE_BREAKS.md`.

**Claim boundary:** algorithm-level Lean check ≠ CPython/`json.loads` proof.

See `verification/PYTHON_LEAN_EQUIVALENCE.md`.
-/

namespace ScientificReasoning.PythonModel

open ScientificReasoning

/-- Python `meet` (rank-min + tie-break) — identical to `Authority.meet`. -/
def meetPy (a b : Authority) : Authority := Authority.meet a b

theorem meetPy_eq : meetPy = Authority.meet := rfl

/-- Python step reconstruction (same cases as `checkStep`). -/
def checkStepPy (ps : List Premise) (prior : List VerifiedJudgment) (st : StepSpec) :
    Option VerifiedJudgment :=
  checkStep ps prior st

theorem checkStepPy_eq : checkStepPy = checkStep := rfl

/-- Python left-to-right accumulation over steps. -/
def checkStepsPy (ps : List Premise) (steps : List StepSpec) : Option (List VerifiedJudgment) :=
  checkStepsLTR ps steps

theorem checkStepsPy_eq : checkStepsPy = checkStepsLTR := rfl

/-- Full Python structured checker (unique premise ids + steps + conclusion). -/
def checkCertificatePy (c : StructuredCertificate) : Option VerifiedJudgment :=
  checkCertificate c

/-- Definitional equivalence: the Python-model entrypoint *is* the Lean checker. -/
theorem checkCertificatePy_eq_lean :
    checkCertificatePy = checkCertificate := rfl

/-- Acceptance by the Python-model algorithm yields a formal derivation. -/
theorem checkCertificatePy_sound
    (c : StructuredCertificate) (j : VerifiedJudgment)
    (h : checkCertificatePy c = some j) :
    Derives c.toContext j.support j.assurance.declared j.formula :=
  checkCertificate_sound c j (by simpa [checkCertificatePy] using h)

/-- Python-model acceptance never sets mathEstablished. -/
theorem checkCertificatePy_mathEstablished_false
    (c : StructuredCertificate) (j : VerifiedJudgment)
    (h : checkCertificatePy c = some j) :
    j.assurance.mathEstablished = false :=
  checkCertificate_mathEstablished_false c j (by simpa [checkCertificatePy] using h)

/-- Python-model acceptance implies unique premise ids. -/
theorem checkCertificatePy_unique_ids
    (c : StructuredCertificate) (j : VerifiedJudgment)
    (h : checkCertificatePy c = some j) :
    uniquePremiseIds c.premises = true :=
  checkCertificate_requires_unique_ids c j (by simpa [checkCertificatePy] using h)

end ScientificReasoning.PythonModel

#print axioms ScientificReasoning.PythonModel.checkCertificatePy_eq_lean
#print axioms ScientificReasoning.PythonModel.checkCertificatePy_sound
