import ScientificReasoning.Retraction

/-!
# Certificate structure

**Finding D:** `Certificate.valid` below is *abstract existence* of a Derives
judgment for the final fields. It does **not** validate `steps`.
Executable step validation lives in `CheckCertificate.lean` via
`checkCertificate` / `checkCertificate_sound`.
-/

namespace ScientificReasoning

inductive RuleTag where
  | hyp
  | andI
  | andE1
  | andE2
  deriving Repr, DecidableEq, Inhabited

structure CertStep where
  tag : RuleTag
  support : Support
  authority : Authority
  conclusion : Formula
  deriving Repr, DecidableEq, Inhabited

structure Certificate where
  context : Context
  steps : List CertStep
  finalSupport : Support
  finalAuthority : Authority
  conclusion : Formula
  deriving Repr, DecidableEq, Inhabited

/-- Abstract validity (existence) — NOT step-trace integrity. -/
def Certificate.valid (c : Certificate) : Prop :=
  Derives c.context c.finalSupport c.finalAuthority c.conclusion

theorem valid_implies_sound (c : Certificate) (h : c.valid) :
    Entails c.context c.conclusion :=
  derives_sound c.context c.finalSupport c.finalAuthority c.conclusion h

theorem valid_support_in_context (c : Certificate) (h : c.valid) :
    Support.subsetOf c.finalSupport c.context.ids :=
  derives_support_in_context _ _ _ _ h

theorem valid_invalidated_by_support_member
    (c : Certificate) (i : PropId) (hi : i ∈ c.finalSupport) :
    invalidatedBy c.finalSupport [i] :=
  ⟨i, by simp, hi⟩

end ScientificReasoning

#print axioms ScientificReasoning.valid_implies_sound
