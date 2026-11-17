import ScientificReasoning.Completeness
import ScientificReasoning.PythonCheckerModel
import ScientificReasoning.Belnap

/-!
# Python ↔ Lean semantic equivalence (kernel-checked core)

## Proved chain

1. `checkCertificatePy = checkCertificate` (definitional; Python algorithm model)
2. `checkCertificate c = some j → Derives ∧ Entails4 ∧ ¬mathEstablished ∧ unique ids`
3. `Derives ∧ unique ids → ∃ c, checkCertificate c = some j` (matching judgment)
4. `Derives ↔ ∃ ProofTerm.interpret` (unique ids)

## Not proved (explicit trust boundary)

- CPython interpreter / JSON `json.loads` / OS I/O
- Bit-identical Python source AST ↔ Lean AST (differential tests cover the algorithm)

The structured checking algorithm used by Python is therefore Lean-checked:
acceptance implies the formal theorems above; every formal derivation has an
accepted certificate encoding.
-/

namespace ScientificReasoning.Equivalence

open ScientificReasoning
open ScientificReasoning.PythonModel
open ScientificReasoning.Belnap

theorem python_accept_implies_derives
    (c : StructuredCertificate) (j : VerifiedJudgment)
    (h : checkCertificatePy c = some j) :
    Derives c.toContext j.support j.assurance.declared j.formula :=
  checkCertificatePy_sound c j h

theorem python_accept_implies_entails4
    (c : StructuredCertificate) (j : VerifiedJudgment)
    (h : checkCertificatePy c = some j) :
    Entails4 c.toContext j.formula :=
  checkCertificate_entails4 c j (by simpa [checkCertificatePy] using h)

theorem python_accept_implies_classical_entails
    (c : StructuredCertificate) (j : VerifiedJudgment)
    (h : checkCertificatePy c = some j) :
    Entails c.toContext j.formula :=
  checkCertificate_implies_entails c j (by simpa [checkCertificatePy] using h)

/-- Completeness for the Python-modelled checker: every unique-id derivation has
an accepted certificate. -/
theorem derives_python_complete
    (Γ : Context) (S : Support) (a : Authority) (φ : Formula)
    (h : Derives Γ S a φ)
    (hu : uniquePremiseIds Γ.premises = true) :
    ∃ (c : StructuredCertificate) (j : VerifiedJudgment),
      c.premises = Γ.premises ∧
      checkCertificatePy c = some j ∧
      j.formula = φ ∧ j.support = S ∧ j.assurance.declared = a ∧
      j.assurance.mathEstablished = false := by
  obtain ⟨c, j, h1, h2, h3, h4, h5, h6⟩ := derives_completeness Γ S a φ h hu
  exact ⟨c, j, h1, by simpa [checkCertificatePy] using h2, h3, h4, h5, h6⟩

/-- Round-trip characterization for unique-id contexts. -/
theorem derives_iff_python_certificate
    (Γ : Context) (S : Support) (a : Authority) (φ : Formula)
    (hu : uniquePremiseIds Γ.premises = true) :
    Derives Γ S a φ ↔
      ∃ (c : StructuredCertificate) (j : VerifiedJudgment),
        c.premises = Γ.premises ∧
        checkCertificatePy c = some j ∧
        j.formula = φ ∧ j.support = S ∧ j.assurance.declared = a ∧
        j.assurance.mathEstablished = false := by
  constructor
  · intro h; exact derives_python_complete Γ S a φ h hu
  · intro ⟨c, j, hprem, hchk, hform, hsup, hauth, _⟩
    have hd := checkCertificatePy_sound c j hchk
    simp [StructuredCertificate.toContext, hprem, hform, hsup, hauth] at hd
    exact hd

end ScientificReasoning.Equivalence

#print axioms ScientificReasoning.Equivalence.python_accept_implies_derives
#print axioms ScientificReasoning.Equivalence.python_accept_implies_entails4
#print axioms ScientificReasoning.Equivalence.derives_python_complete
#print axioms ScientificReasoning.Equivalence.derives_iff_python_certificate
