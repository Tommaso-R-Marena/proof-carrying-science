import PCSDecisionDiagram.Conditional
import PCSActionShield

/-!
Compose conditional Boolean guard equivalence with universal action-shield safety.
The context must hold for each modeled state/action encoding; it cannot be dropped
when replacing a guard. Deployed interpretation and runtime correspondence are
separate assumptions, not conclusions of this mathematical bridge.
-/
set_option autoImplicit false

namespace PCSConditionalShield

open PCSOmega PCSDD PCSActionShield

theorem equivalent_guard_matches {n : Nat} (t : CTask n) (lim : Limits)
    (hdecision : (check t lim).decision = .equivalentUnderAssumptions)
    (m : Model) (encoding : Nat → Nat → Nat → Bool)
    (hcontext : ∀ s a, allEval t.assumptions (encoding s a) = true)
    (hsource : ∀ s a, t.source.eval (encoding s a) = true ↔ (s, a) ∈ m.allowed) :
    GuardMatches m (fun s a => t.candidate.eval (encoding s a)) := by
  intro s a
  have heq := (check_equivalent t lim hdecision).2.2 (encoding s a) (hcontext s a)
  change t.candidate.eval (encoding s a) = true ↔ (s, a) ∈ m.allowed
  rw [← heq]
  exact hsource s a

/-- Every length of modeled execution is covered by induction. The proposing
    policy and choice among nondeterministic modeled successors are unrestricted. -/
theorem conditional_guard_histories_safe {n : Nat} (t : CTask n) (lim : Limits)
    (hdecision : (check t lim).decision = .equivalentUnderAssumptions)
    (m : Model) (hcertificate : PCSActionShield.check m = true)
    (encoding : Nat → Nat → Nat → Bool)
    (hcontext : ∀ s a, allEval t.assumptions (encoding s a) = true)
    (hsource : ∀ s a, t.source.eval (encoding s a) = true ↔ (s, a) ∈ m.allowed)
    {history : List Edge} {state : Nat}
    (h : GuardHistory m (fun s a => t.candidate.eval (encoding s a)) history state) :
    state ∈ m.safe ∧ ∀ e ∈ history, e.action ∉ m.forbidden :=
  optimized_guard_histories_safe hcertificate
    (equivalent_guard_matches t lim hdecision m encoding hcontext hsource) h

#print axioms equivalent_guard_matches
#print axioms conditional_guard_histories_safe

end PCSConditionalShield
