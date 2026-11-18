import ScientificReasoning.Surface
import ScientificReasoning.JsonCert

/-!
# Lean model of the Python schema-v1 checker

Layers (bottom → top):

1. `checkCertificate` — structured core LTR
2. `checkSurface` / `checkCertificatePy` — WF + claims
3. `checkJsonCert` — typed post-parse JSON object graph → surface

**Irreducible:** byte-string `json.loads` / CPython / OS I/O.
-/

namespace ScientificReasoning.PythonModel

open ScientificReasoning

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

theorem checkCertificatePy_iff_core
    (c : StructuredCertificate) (j : VerifiedJudgment)
    (hne : c.steps ≠ [])
    (hprem : c.premises.length ≤ maxPremises)
    (hsteps : c.steps.length ≤ maxSteps)
    (hdepth : ∀ js, checkStepsLTR c.premises c.steps = some js → judgmentsDepthOk js = true) :
    checkCertificatePy c.toSurface = some j ↔ checkCertificate c = some j :=
  checkSurface_iff_checkCertificate c j hne hprem hsteps hdepth

/-- Top-level Python path after parse: typed JSON graph. -/
def checkCertificateJson (c : JsonCertificate) : Option VerifiedJudgment :=
  checkJsonCert c

theorem checkCertificateJson_eq :
    checkCertificateJson = checkJsonCert := rfl

theorem checkCertificateJson_sound
    (c : JsonCertificate) (j : VerifiedJudgment)
    (h : checkCertificateJson c = some j) :
    ∃ sc, decodeJsonCert c = some sc ∧
      Derives sc.erase.toContext j.support j.assurance.declared j.formula :=
  checkJsonCert_sound c j h

end ScientificReasoning.PythonModel

#print axioms ScientificReasoning.PythonModel.checkCertificatePy_eq_surface
#print axioms ScientificReasoning.PythonModel.checkCertificatePy_sound
#print axioms ScientificReasoning.PythonModel.checkCertificatePy_iff_core
#print axioms ScientificReasoning.PythonModel.checkCertificateJson_sound

