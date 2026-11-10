import AnchoredExecution
import EffectLifecycle

/-!
Writ/14: product checker for three separate safety boundaries:
(i) source identity, (ii) explicit provenance plus weighted authority,
(iii) permissible effect lifecycle. The proof does NOT establish that Python,
the signing operator or external physical actions refine these definitions.
-/
namespace Writ14

def CheckTriple {n m : Nat}
    (committed current : Nat)
    (parents : Fin n → List (Fin n)) (label : Fin n → Nat)
    (budget : Fin m → Nat) (charges : List (Fin m → Nat))
    (history : List Event) (claimed : State) : Option (Fin m → Nat) :=
  if Replay .pending history = some claimed then
    Writ13.CheckAnchored committed current parents label budget charges
  else none

theorem triple_sound {n m : Nat}
    {committed current : Nat}
    {parents : Fin n → List (Fin n)} {label : Fin n → Nat}
    {budget final : Fin m → Nat} {charges : List (Fin m → Nat)}
    {history : List Event} {claimed : State}
    (accepted : CheckTriple committed current parents label budget charges history claimed = some final) :
    committed = current ∧ Writ12.FlowSound parents label ∧
      Writ9.WeightedRuns budget charges final ∧ Runs .pending history claimed := by
  have h : (Replay .pending history = some claimed) ∧
      Writ13.CheckAnchored committed current parents label budget charges = some final := by
    simpa [CheckTriple] using accepted
  have hanchored := Writ13.anchored_sound h.2
  exact ⟨hanchored.1, hanchored.2.1, hanchored.2.2, replay_sound h.1⟩

theorem triple_complete {n m : Nat}
    {committed current : Nat}
    {parents : Fin n → List (Fin n)} {label : Fin n → Nat}
    {budget final : Fin m → Nat} {charges : List (Fin m → Nat)}
    {history : List Event} {claimed : State}
    (same : committed = current) (flow : Writ12.FlowSound parents label)
    (budgetValid : Writ9.WeightedRuns budget charges final)
    (lifecycleValid : Runs .pending history claimed) :
    CheckTriple committed current parents label budget charges history claimed = some final := by
  have hlife := replay_complete lifecycleValid
  have hresources := Writ13.anchored_complete same flow budgetValid
  simpa [CheckTriple, hlife] using hresources

theorem triple_no_overspend {n m : Nat}
    {committed current : Nat}
    {parents : Fin n → List (Fin n)} {label : Fin n → Nat}
    {budget final : Fin m → Nat} {charges : List (Fin m → Nat)}
    {history : List Event} {claimed : State}
    (accepted : CheckTriple committed current parents label budget charges history claimed = some final)
    (i : Fin m) : Writ9.WeightedUsed i charges ≤ budget i := by
  have valid := (triple_sound accepted).2.2.1
  have accounting := Writ9.weighted_quota_conservation valid i
  omega

theorem triple_has_valid_lifecycle {n m : Nat}
    {committed current : Nat}
    {parents : Fin n → List (Fin n)} {label : Fin n → Nat}
    {budget final : Fin m → Nat} {charges : List (Fin m → Nat)}
    {history : List Event} {claimed : State}
    (accepted : CheckTriple committed current parents label budget charges history claimed = some final) :
    Runs .pending history claimed := (triple_sound accepted).2.2.2

end Writ14
