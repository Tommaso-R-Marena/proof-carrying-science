import Std

/-!
Research-only abstract guarded interface. These theorems are not proofs of
Python/file-system refinement, authentic state observation, model completeness,
or an uncompromised host. Model scores are deliberately absent from admission.
The existing PCSActionShield finite certificate is checked separately.
-/
set_option autoImplicit false
namespace PCSSafetyJEPA

variable {State Action Proposal : Type}

/-- The host fixes a policy and effect; proposals have no authority parameter. -/
def guardedStep (allowed : State → Action → Bool) (effect : State → Action → State)
    (state : State) (action : Action) : State :=
  if allowed state action then effect state action else state

/-- Refusing an operation does not change abstract protected state. -/
theorem rejected_unchanged (allowed : State → Action → Bool)
    (effect : State → Action → State) (state : State) (action : Action)
    (denied : allowed state action = false) :
    guardedStep allowed effect state action = state := by
  simp [guardedStep, denied]

/-- Arbitrary learned proposal/score updates cannot change the fixed admission
    decision for the same observed state/action. -/
def scoredAdmission (allowed : State → Action → Bool) (_model : Proposal)
    (state : State) (action : Action) : Bool := allowed state action

theorem model_cannot_authorize (allowed : State → Action → Bool)
    (model : Proposal) (state : State) (action : Action)
    (denied : allowed state action = false) :
    scoredAdmission allowed model state action = false := denied

theorem model_updates_preserve_policy (allowed : State → Action → Bool)
    (oldModel newModel : Proposal) (state : State) (action : Action) :
    scoredAdmission allowed oldModel state action =
      scoredAdmission allowed newModel state action := rfl

/-- Concrete effects preserve an invariant only under this explicit host/tool
    correspondence premise for every permitted state/action. -/
theorem permitted_step_preserves (allowed : State → Action → Bool)
    (effect : State → Action → State) (safe : State → Prop)
    (preserves : ∀ s a, safe s → allowed s a = true → safe (effect s a))
    (state : State) (action : Action) (initial : safe state) :
    safe (guardedStep allowed effect state action) := by
  by_cases admission : allowed state action = true
  · simpa [guardedStep, admission] using preserves state action initial admission
  · have denied : allowed state action = false := Bool.eq_false_iff.mpr admission
    simpa [guardedStep, denied] using initial

/-- Any finite sequence of arbitrary proposals preserves the invariant under
    the same transition-preservation premise; there is no liveness conclusion. -/
def run (allowed : State → Action → Bool) (effect : State → Action → State)
    (state : State) (actions : List Action) : State :=
  actions.foldl (guardedStep allowed effect) state

theorem arbitrary_proposals_preserve (allowed : State → Action → Bool)
    (effect : State → Action → State) (safe : State → Prop)
    (preserves : ∀ s a, safe s → allowed s a = true → safe (effect s a))
    (actions : List Action) (state : State) (initial : safe state) :
    safe (run allowed effect state actions) := by
  induction actions generalizing state with
  | nil => exact initial
  | cons action rest ih =>
      exact ih (guardedStep allowed effect state action)
        (permitted_step_preserves allowed effect safe preserves state action initial)

/-- A rejected prefix can contain any number of model recommendations without
    gaining mutation authority. -/
theorem all_rejected_unchanged (allowed : State → Action → Bool)
    (effect : State → Action → State) (actions : List Action) (state : State)
    (denied : ∀ action ∈ actions, allowed state action = false) :
    run allowed effect state actions = state := by
  induction actions with
  | nil => rfl
  | cons action rest ih =>
      simp only [run, List.foldl_cons]
      rw [rejected_unchanged allowed effect state action (denied action (by simp))]
      exact ih (fun a ha => denied a (by simp [ha]))

#print axioms rejected_unchanged
#print axioms model_cannot_authorize
#print axioms model_updates_preserve_policy
#print axioms permitted_step_preserves
#print axioms arbitrary_proposals_preserve
#print axioms all_rejected_unchanged
end PCSSafetyJEPA
