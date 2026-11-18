import ScientificReasoning.Completeness
import ScientificReasoning.PythonCheckerModel
import ScientificReasoning.Belnap
import ScientificReasoning.Surface
import ScientificReasoning.JsonCert

/-!
# Python ↔ Lean semantic equivalence (kernel-checked)

## Proved chain

1. JSON object graph → surface → core → Derives / Entails4
2. Bounded core ↔ surface round-trip
3. Derives ↔ core certificate (unique ids)
4. Classical Entails explodes on `demoΓ`; Entails4 does not
5. Formula/Authority JSON isomorphisms

## Irreducible boundary

- Byte-string `json.loads` / CPython / OS I/O → typed `JsonCertificate`

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
    (hne : 0 < c.steps.length)
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
  have hne' : c.steps ≠ [] := fun he => by simp [he] at hne
  refine ⟨(checkCertificatePy_iff_core c j hne' hb1 hb2).2 hchk,
    by simpa [StructuredCertificate.toSurface] using hprem,
    hform, hsup, hauth, hmath⟩

theorem derives_iff_python_certificate
    (Γ : Context) (S : Support) (a : Authority) (φ : Formula)
    (hu : uniquePremiseIds Γ.premises = true)
    (c : StructuredCertificate) (j : VerifiedJudgment)
    (hprem : c.premises = Γ.premises)
    (hne : 0 < c.steps.length)
    (hb1 : c.premises.length ≤ maxPremises)
    (hb2 : c.steps.length ≤ maxSteps)
    (hchk : checkCertificate c = some j)
    (hform : j.formula = φ) (hsup : j.support = S)
    (hauth : j.assurance.declared = a) :
    checkCertificatePy c.toSurface = some j ∧
      Derives Γ S a φ := by
  have hne' : c.steps ≠ [] := fun he => by simp [he] at hne
  refine ⟨(checkCertificatePy_iff_core c j hne' hb1 hb2).2 hchk, ?_⟩
  have hd := checkCertificate_sound c j hchk
  simp [StructuredCertificate.toContext, hprem, hform, hsup, hauth] at hd
  exact hd

theorem json_accept_implies_derives
    (c : JsonCertificate) (j : VerifiedJudgment)
    (h : checkCertificateJson c = some j) :
    ∃ sc, decodeJsonCert c = some sc ∧
      Derives sc.erase.toContext j.support j.assurance.declared j.formula :=
  checkCertificateJson_sound c j h

theorem json_accept_implies_entails4
    (c : JsonCertificate) (j : VerifiedJudgment)
    (h : checkJsonCert c = some j) :
    ∃ sc, decodeJsonCert c = some sc ∧ Entails4 sc.erase.toContext j.formula :=
  checkJsonCert_entails4 c j h

/-- Completeness witnesses always have a positive-length step list. -/
theorem derives_completeness_steps_pos
    (Γ : Context) (S : Support) (a : Authority) (φ : Formula)
    (h : Derives Γ S a φ)
    (hu : uniquePremiseIds Γ.premises = true) :
    ∃ (c : StructuredCertificate) (j : VerifiedJudgment),
      c.premises = Γ.premises ∧
      0 < c.steps.length ∧
      checkCertificate c = some j ∧
      j.formula = φ ∧ j.support = S ∧ j.assurance.declared = a ∧
      j.assurance.mathEstablished = false := by
  obtain ⟨t, ht⟩ := derives_to_proofterm Γ S a φ h hu
  refine ⟨
    { premises := Γ.premises
      steps := (ProofTerm.compile t).1
      conclusionStep := (ProofTerm.compile t).2 },
    { formula := φ, support := S,
      assurance := { declared := a, mathEstablished := false } },
    rfl, ProofTerm.compile_steps_pos t,
    interpret_checkCertificate Γ t S a φ hu ht, rfl, rfl, rfl, rfl⟩

end ScientificReasoning.Equivalence

#print axioms ScientificReasoning.Equivalence.python_accept_implies_derives
#print axioms ScientificReasoning.Equivalence.derives_iff_core_certificate
#print axioms ScientificReasoning.Equivalence.derives_completeness_steps_pos
#print axioms ScientificReasoning.Equivalence.json_accept_implies_derives
#print axioms ScientificReasoning.Equivalence.json_accept_implies_entails4
