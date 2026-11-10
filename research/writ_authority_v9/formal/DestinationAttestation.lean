import Std

/-!
Writ/15 abstract destination attestation calculus.

A successful delivered state carries the exact expected receipt binding plus
a signatureVerified=true fact. The Boolean is supplied by the independent
cryptographic verifier; Lean does NOT prove Ed25519 itself, key custody, honest
receiver behavior, source authenticity, or actual physical delivery.

This model supports one effect ID at a time. Cross-effect replay protection
requires the executable gateway's binding and independent receiver journal.
-/
namespace Writ15

structure Binding where
  policy : Nat
  effect : Nat
  route : Nat
  payload : Nat
  lease : Nat
  receiver : Nat
  deriving DecidableEq, Repr

structure Attestation where
  binding : Binding
  signatureVerified : Bool
  deriving DecidableEq, Repr

def Valid (expected : Binding) (proof : Attestation) : Prop :=
  proof.binding = expected ∧ proof.signatureVerified = true

def VerifiedB (expected : Binding) (proof : Attestation) : Bool :=
  decide (proof.binding = expected) && proof.signatureVerified

theorem verifiedB_iff (expected : Binding) (proof : Attestation) :
    VerifiedB expected proof = true ↔ Valid expected proof := by
  simp [VerifiedB, Valid, Bool.and_eq_true]

inductive State where
  | pending
  | working (lease : Nat)
  | delivered (proof : Attestation)
  | uncertain
  | canceled
  deriving DecidableEq, Repr

inductive Event where
  | lease (value : Nat)
  | acknowledgment (proof : Attestation)
  | uncertain
  | cancel
  deriving DecidableEq, Repr

def Next (expected : Binding) : State → Event → Option State
  | .pending, .lease value =>
      if value = expected.lease then some (.working value) else none
  | .working value, .acknowledgment proof =>
      if decide (value = expected.lease) && VerifiedB expected proof then
        some (.delivered proof)
      else none
  | .working _, .uncertain => some .uncertain
  | .pending, .cancel => some .canceled
  | _, _ => none

def Replay (expected : Binding) (start : State) : List Event → Option State
  | [] => some start
  | event :: rest =>
      match Next expected start event with
      | none => none
      | some middle => Replay expected middle rest

def StateSafe (expected : Binding) : State → Prop
  | .delivered proof => Valid expected proof
  | _ => True

theorem step_preserves_safety (expected : Binding) (start finish : State)
    (event : Event) (safe : StateSafe expected start)
    (step : Next expected start event = some finish) :
    StateSafe expected finish := by
  cases start <;> cases event <;> cases finish <;>
    simp_all [Next, StateSafe, Valid, VerifiedB]
  all_goals
    rcases step with ⟨⟨_, hbinding, hsignature⟩, hequal⟩
    cases hequal
    exact ⟨hbinding, hsignature⟩

theorem replay_preserves_safety (expected : Binding) (events : List Event)
    (start finish : State) (safe : StateSafe expected start)
    (accepted : Replay expected start events = some finish) :
    StateSafe expected finish := by
  induction events generalizing start with
  | nil =>
      have eq : start = finish := by simpa [Replay] using accepted
      subst finish
      exact safe
  | cons event rest ih =>
      cases h : Next expected start event with
      | none => simp [Replay, h] at accepted
      | some middle =>
          have tail : Replay expected middle rest = some finish := by
            simpa [Replay, h] using accepted
          exact ih middle (step_preserves_safety expected start middle event safe h) tail

/-- No accepted trace from pending can end as delivered without an exactly
matching attestation that the separately trusted verifier marked valid. -/
theorem delivered_requires_verified_receiver (expected : Binding)
    (events : List Event) (proof : Attestation)
    (accepted : Replay expected .pending events = some (.delivered proof)) :
    Valid expected proof := by
  exact replay_preserves_safety expected events .pending (.delivered proof) trivial accepted

theorem wrong_receiver_rejected (expected : Binding) (lease : Nat) (proof : Attestation)
    (bad : proof.binding.receiver ≠ expected.receiver) :
    Next expected (.working lease) (.acknowledgment proof) = none := by
  have neq : proof.binding ≠ expected := by
    intro h
    exact bad (congrArg Binding.receiver h)
  simp [Next, VerifiedB, neq]

theorem forged_signature_rejected (expected : Binding) (lease : Nat) (proof : Attestation)
    (bad : proof.signatureVerified = false) :
    Next expected (.working lease) (.acknowledgment proof) = none := by
  simp [Next, VerifiedB, bad]

theorem terminal_outcomes_are_absorbing (expected : Binding) (proof : Attestation)
    (event : Event) :
    Next expected (.delivered proof) event = none ∧
    Next expected .uncertain event = none ∧
    Next expected .canceled event = none := by
  cases event <;> simp [Next]

end Writ15
