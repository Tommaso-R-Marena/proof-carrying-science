import PCSActionShield

set_option autoImplicit false

namespace PCSActionShieldControls
open PCSActionShield

/-- 0 unreviewed, 1 reviewed, 2 secret loaded, 3 sanitized, 4 complete, 5 leak.
    Action 3 (network send) at state 2 has both a safe and an unsafe outcome. -/
def toolModel : Model :=
  ⟨[0], [0, 1, 2, 3, 4],
   [⟨0, 0, 0⟩, ⟨0, 0, 1⟩, ⟨0, 1, 5⟩, ⟨0, 5, 0⟩, ⟨1, 1, 2⟩, ⟨1, 5, 5⟩,
    ⟨2, 2, 3⟩, ⟨2, 3, 4⟩, ⟨2, 3, 5⟩, ⟨2, 5, 5⟩, ⟨3, 3, 4⟩, ⟨3, 5, 5⟩,
    ⟨4, 4, 4⟩, ⟨4, 5, 5⟩, ⟨5, 4, 5⟩],
   [(0, 0), (1, 1), (2, 2), (3, 3), (4, 4)], [5]⟩

theorem tool_certificate_passes : check toolModel = true := by decide

theorem tool_all_histories_safe {history : List Edge} {s : Nat}
    (h : History toolModel history s) :
    s ∈ toolModel.safe ∧ ∀ e ∈ history, e.action ∉ toolModel.forbidden :=
  admitted_histories_safe tool_certificate_passes h

def unsafePolicy : Model := { toolModel with allowed := toolModel.allowed ++ [(2, 3)] }

theorem unseen_nondeterministic_branch_rejected : check unsafePolicy = false := by decide

/-- A producer can exhibit a safe run for send, while another admitted outcome
    leaks. Observed trajectories cannot replace the universal certificate. -/
theorem safe_observation_and_unsafe_admitted_history :
    History unsafePolicy [⟨0, 0, 1⟩, ⟨1, 1, 2⟩, ⟨2, 3, 4⟩] 4 ∧
    History unsafePolicy [⟨0, 0, 1⟩, ⟨1, 1, 2⟩, ⟨2, 3, 5⟩] 5 ∧
    4 ∈ unsafePolicy.safe ∧ 5 ∉ unsafePolicy.safe := by
  have h1 : History unsafePolicy [⟨0, 0, 1⟩] 1 :=
    History.step (History.initial 0 (by decide)) ⟨0, 0, 1⟩ rfl (by unfold Admitted; decide)
  have h2 : History unsafePolicy [⟨0, 0, 1⟩, ⟨1, 1, 2⟩] 2 :=
    History.step h1 ⟨1, 1, 2⟩ rfl (by unfold Admitted; decide)
  exact ⟨History.step h2 ⟨2, 3, 4⟩ rfl (by unfold Admitted; decide),
    History.step h2 ⟨2, 3, 5⟩ rfl (by unfold Admitted; decide), by decide, by decide⟩

def forbiddenPolicy : Model := { toolModel with allowed := toolModel.allowed ++ [(0, 5)] }

/-- Forbidden-action exclusion is an independent obligation even if this one
    modeled transition returns to a safe state. -/
theorem forbidden_action_safe_target_rejected :
    check forbiddenPolicy = false ∧ (⟨0, 5, 0⟩ : Edge).target ∈ forbiddenPolicy.safe := by
  decide

def incompleteModel : Model :=
  { unsafePolicy with edges := toolModel.edges.filter (fun e => e != ⟨2, 3, 5⟩) }

/-- A certificate for an incomplete model may be true. It cannot model the
    omitted concrete outcome; deployment correspondence must remain explicit. -/
theorem omitted_branch_exposes_correspondence_failure :
    check incompleteModel = true ∧ (⟨2, 3, 5⟩ : Edge) ∉ incompleteModel.edges ∧
      (⟨2, 3, 5⟩ : Edge) ∈ toolModel.edges := by decide

def allDeny : Model := { toolModel with allowed := [] }

theorem deadlock_does_not_establish_liveness :
    check allDeny = true ∧ ∀ e, ¬ Admitted allDeny e := by
  refine ⟨by decide, ?_⟩
  intro e h
  simp [Admitted, allDeny] at h

end PCSActionShieldControls
