import AnchoredExecution
import DestinationAttestation

/-!
Writ/15 abstract destination-attested source/provenance/authority checker.

The receiver validation Boolean in an Attestation is trusted input from the
external Ed25519 verifier. The source commitment is assumed to bind pinned
trusted roots. The result is a conditional, compositional mathematical theorem
about the executable Lean predicate, NOT Python/SQLite or physical delivery.
-/
namespace Writ15

def CheckAttested {n m : Nat}
    (committed current : Nat)
    (parents : Fin n → List (Fin n)) (label : Fin n → Nat)
    (budget : Fin m → Nat) (charges : List (Fin m → Nat))
    (expected : Binding) (history : List Event) (proof : Attestation) :
    Option (Fin m → Nat) :=
  if Replay expected .pending history = some (.delivered proof) then
    Writ13.CheckAnchored committed current parents label budget charges
  else none

theorem attested_sound {n m : Nat}
    {committed current : Nat}
    {parents : Fin n → List (Fin n)} {label : Fin n → Nat}
    {budget final : Fin m → Nat} {charges : List (Fin m → Nat)}
    {expected : Binding} {history : List Event} {proof : Attestation}
    (accepted : CheckAttested committed current parents label budget charges
                   expected history proof = some final) :
    committed = current ∧ Writ12.FlowSound parents label ∧
    Writ9.WeightedRuns budget charges final ∧ Valid expected proof := by
  have h : (Replay expected .pending history = some (.delivered proof)) ∧
      Writ13.CheckAnchored committed current parents label budget charges = some final := by
    simpa [CheckAttested] using accepted
  have x := Writ13.anchored_sound h.2
  exact ⟨x.1, x.2.1, x.2.2,
         delivered_requires_verified_receiver expected history proof h.1⟩

theorem attested_complete {n m : Nat}
    {committed current : Nat}
    {parents : Fin n → List (Fin n)} {label : Fin n → Nat}
    {budget final : Fin m → Nat} {charges : List (Fin m → Nat)}
    {expected : Binding} {history : List Event} {proof : Attestation}
    (matched : committed = current)
    (flow : Writ12.FlowSound parents label)
    (accounted : Writ9.WeightedRuns budget charges final)
    (received : Replay expected .pending history = some (.delivered proof)) :
    CheckAttested committed current parents label budget charges
      expected history proof = some final := by
  simpa [CheckAttested, received] using
    Writ13.anchored_complete matched flow accounted

theorem attested_no_overspend {n m : Nat}
    {committed current : Nat}
    {parents : Fin n → List (Fin n)} {label : Fin n → Nat}
    {budget final : Fin m → Nat} {charges : List (Fin m → Nat)}
    {expected : Binding} {history : List Event} {proof : Attestation}
    (accepted : CheckAttested committed current parents label budget charges
                   expected history proof = some final)
    (i : Fin m) : Writ9.WeightedUsed i charges ≤ budget i := by
  have h := (attested_sound accepted).2.2.1
  have exact := Writ9.weighted_quota_conservation h i
  omega

theorem attested_rejects_wrong_receiver {n m : Nat}
    (committed current : Nat)
    (parents : Fin n → List (Fin n)) (label : Fin n → Nat)
    (budget : Fin m → Nat) (charges : List (Fin m → Nat))
    (expected : Binding) (history : List Event) (proof : Attestation)
    (wrong : proof.binding.receiver ≠ expected.receiver) :
    CheckAttested committed current parents label budget charges
      expected history proof = none := by
  cases h : CheckAttested committed current parents label budget charges
      expected history proof with
  | none => rfl
  | some final =>
      have valid := (attested_sound h).2.2.2
      exact False.elim (wrong (congrArg Binding.receiver valid.1))

end Writ15
