import ScientificReasoning.Completeness
import ScientificReasoning.PythonCheckerModel
import ScientificReasoning.Belnap
import ScientificReasoning.Surface

/-!
# Python ↔ Lean semantic equivalence (kernel-checked)

## Proved chain

1. `checkCertificatePy = checkSurface` (surface WF + claims + LTR)
2. `checkSurface = some j → checkCertificate erase = some j → Derives ∧ Entails4`
3. Bounded core ↔ surface round-trip (`checkCertificatePy_iff_core`)
4. `Derives ∧ unique ids ↔ ∃ core cert` (`derives_iff_core_certificate`)
5. Classical Entails explodes on `demoΓ`; Entails4 does not

## Irreducible boundary

- CPython / `json.loads` / OS I/O (bytes → Lean AST)
- External math attestation beyond labels (Finding F proved for Hyp path)

See `verification/EQUIVALENCE_BREAKS.md`.
-/

namespace ScientificReasoning.Equivalence

open ScientificReasoning
open ScientificReasoning.PythonModel
open ScientificReasoning.Belnap

theorem python_accept_implies_derives
    (c : SurfaceCertificate) (j : VerifiedJudgment)
    (h : checkCertificatePy c = some j) :
    Derives c.erase.toContext j.support j.assurance.declared j.formula :=
  checkCertificatePy_sound c j h

theorem python_accept_implies_entails4
    (c : SurfaceCertificate) (j : VerifiedJudgment)
    (h : checkCertificatePy c = some j) :
    Entails4 c.erase.toContext j.formula :=
  checkCertificatePy_entails4 c j h

theorem python_accept_implies_core
    (c : SurfaceCertificate) (j : VerifiedJudgment)
    (h : checkCertificatePy c = some j) :
    checkCertificate c.erase = some j :=
  checkCertificatePy_implies_core c j h

theorem derives_core_complete
    (Γ : Context) (S : Support) (a : Authority) (φ : Formula)
    (h : Derives Γ S a φ)
    (hu : uniquePremiseIds Γ.premises = true) :
    ∃ (c : StructuredCertificate) (j : VerifiedJudgment),
      c.premises = Γ.premises ∧
      checkCertificate c = some j ∧
      j.formula = φ ∧ j.support = S ∧ j.assurance.declared = a ∧
      j.assurance.mathEstablished = false :=
  derives_completeness Γ S a φ h hu

theorem derives_iff_core_certificate
    (Γ : Context) (S : Support) (a : Authority) (φ : Formula)
    (hu : uniquePremiseIds Γ.premises = true) :
    Derives Γ S a φ ↔
      ∃ (c : StructuredCertificate) (j : VerifiedJudgment),
        c.premises = Γ.premises ∧
        checkCertificate c = some j ∧
        j.formula = φ ∧ j.support = S ∧ j.assurance.declared = a ∧
        j.assurance.mathEstablished = false := by
  constructor
  · intro h; exact derives_core_complete Γ S a φ h hu
  · intro ⟨c, j, hprem, hchk, hform, hsup, hauth, _⟩
    have hd := checkCertificate_sound c j hchk
    simp [StructuredCertificate.toContext, hprem, hform, hsup, hauth] at hd
    exact hd

/-- Surface acceptance for a bounded core witness of a derivation. -/
theorem derives_python_complete
    (Γ : Context) (S : Support) (a : Authority) (φ : Formula)
    (h : Derives Γ S a φ)
    (hu : uniquePremiseIds Γ.premises = true)
    (c : StructuredCertificate) (j : VerifiedJudgment)
    (hprem : c.premises = Γ.premises)
    (hne : c.steps ≠ [])
    (hb1 : c.premises.length ≤ maxPremises)
    (hb2 : c.steps.length ≤ maxSteps)
    (hchk : checkCertificate c = some j)
    (hform : j.formula = φ) (hsup : j.support = S)
    (hauth : j.assurance.declared = a)
    (hmath : j.assurance.mathEstablished = false) :
    checkCertificatePy c.toSurface = some j ∧
      c.toSurface.premises = Γ.premises ∧
      j.formula = φ ∧ j.support = S ∧ j.assurance.declared = a ∧
      j.assurance.mathEstablished = false := by
  refine ⟨(checkCertificatePy_iff_core c j hne hb1 hb2).2 hchk,
    by simpa [StructuredCertificate.toSurface] using hprem,
    hform, hsup, hauth, hmath⟩

theorem derives_iff_python_certificate
    (Γ : Context) (S : Support) (a : Authority) (φ : Formula)
    (hu : uniquePremiseIds Γ.premises = true)
    (c : StructuredCertificate) (j : VerifiedJudgment)
    (hprem : c.premises = Γ.premises)
    (hne : c.steps ≠ [])
    (hb1 : c.premises.length ≤ maxPremises)
    (hb2 : c.steps.length ≤ maxSteps)
    (hchk : checkCertificate c = some j)
    (hform : j.formula = φ) (hsup : j.support = S)
    (hauth : j.assurance.declared = a) :
    checkCertificatePy c.toSurface = some j ∧
      Derives Γ S a φ := by
  refine ⟨(checkCertificatePy_iff_core c j hne hb1 hb2).2 hchk, ?_⟩
  have hd := checkCertificate_sound c j hchk
  simp [StructuredCertificate.toContext, hprem, hform, hsup, hauth] at hd
  exact hd

end ScientificReasoning.Equivalence

#print axioms ScientificReasoning.Equivalence.python_accept_implies_derives
#print axioms ScientificReasoning.Equivalence.python_accept_implies_entails4
#print axioms ScientificReasoning.Equivalence.derives_iff_core_certificate
#print axioms ScientificReasoning.Equivalence.derives_python_complete
#print axioms ScientificReasoning.Equivalence.derives_iff_python_certificate
