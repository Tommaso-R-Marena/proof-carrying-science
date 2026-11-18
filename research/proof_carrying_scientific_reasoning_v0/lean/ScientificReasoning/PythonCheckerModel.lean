import ScientificReasoning.Surface

/-!
# Lean model of the Python schema-v1 checker

`checkCertificatePy` is the **surface** checker (`checkSurface`), matching
`independent_checker/check_certificate_v1.check` after JSON parse:

- schema version, size bounds, unique premise ids, step id = index
- LTR reconstruction (`checkStepsLTR`)
- claimed field checks + reject `math_established = true`

**Irreducible boundary:** `json.loads` / CPython / OS I/O are not modelled.

For core-only certificates, `checkSurface_iff_checkCertificate` relates surface
acceptance to `checkCertificate` under size bounds.
-/

namespace ScientificReasoning.PythonModel

open ScientificReasoning

/-- Python-model entrypoint = Lean surface checker. -/
def checkCertificatePy (c : SurfaceCertificate) : Option VerifiedJudgment :=
  checkSurface c

theorem checkCertificatePy_eq_surface :
    checkCertificatePy = checkSurface := rfl

theorem checkCertificatePy_sound
    (c : SurfaceCertificate) (j : VerifiedJudgment)
    (h : checkCertificatePy c = some j) :
    Derives c.erase.toContext j.support j.assurance.declared j.formula :=
  checkSurface_sound c j h

theorem checkCertificatePy_entails4
    (c : SurfaceCertificate) (j : VerifiedJudgment)
    (h : checkCertificatePy c = some j) :
    Belnap.Entails4 c.erase.toContext j.formula :=
  checkSurface_entails4 c j h

theorem checkCertificatePy_mathEstablished_false
    (c : SurfaceCertificate) (j : VerifiedJudgment)
    (h : checkCertificatePy c = some j) :
    j.assurance.mathEstablished = false :=
  checkSurface_mathEstablished_false c j h

theorem checkCertificatePy_unique_ids
    (c : SurfaceCertificate) (j : VerifiedJudgment)
    (h : checkCertificatePy c = some j) :
    uniquePremiseIds c.premises = true :=
  checkSurface_requires_unique_ids c j h

theorem checkCertificatePy_implies_core
    (c : SurfaceCertificate) (j : VerifiedJudgment)
    (h : checkCertificatePy c = some j) :
    checkCertificate c.erase = some j :=
  checkSurface_implies_checkCertificate c j h

/-- Core ↔ surface for canonical embeddings (bounded, non-empty). -/
theorem checkCertificatePy_iff_core
    (c : StructuredCertificate) (j : VerifiedJudgment)
    (hne : c.steps ≠ [])
    (hprem : c.premises.length ≤ maxPremises)
    (hsteps : c.steps.length ≤ maxSteps) :
    checkCertificatePy c.toSurface = some j ↔ checkCertificate c = some j :=
  checkSurface_iff_checkCertificate c j hne hprem hsteps

end ScientificReasoning.PythonModel

#print axioms ScientificReasoning.PythonModel.checkCertificatePy_eq_surface
#print axioms ScientificReasoning.PythonModel.checkCertificatePy_sound
#print axioms ScientificReasoning.PythonModel.checkCertificatePy_iff_core
