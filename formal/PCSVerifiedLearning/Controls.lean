import PCSVerifiedLearning.Shaping
import PCSVerifiedLearning.Data

/-!
# Executed controls: a full proof-learning cycle and adversarial learning controls
-/

namespace PCSVerifiedLearning.Controls

open PCSVerifiedLearning PCSReasoningLibrary

def A : Fm := .atom 0
def goalAA : Fm := .imp A A

/-- An untrusted observation oracle that *lies*: it reports every proposal as closed. -/
def lyingObs : Fm → List Tok → Obs := fun _ _ => .closed

/-- An honest-looking oracle: one open goal after one action, closed after two. -/
def obs2 : Fm → List Tok → Obs := fun _ as => if as.length ≥ 2 then .closed else .opened 1

def s0 : EState Fm Tok := reset obs2 goalAA

/-! ### Full cycle: episode → verified reward → receipt replay → intake → export -/

def ep : List (StepOut Fm Tok) := run tokenVerifier obs2 24 s0 [.lam A, .hyp A]

example : ep.map (·.reward) = [-1, 100] := by decide
example : ep.map (·.status) = [.opened, .verified] := by decide

theorem cycle_certifies : Valid goalAA :=
  run_success_certifies_original tokenVerifier obs2 24 goalAA [.lam A, .hyp A]
    (ep[1]'(by decide)) (List.getElem_mem ..) (by decide)

example : (ep.getLast?.bind (·.receipt)).map (replay tokenVerifier) = some true := by decide

def fb : Feedback Fm Tok := ⟨goalAA, [.lam A, .hyp A], 999, true, none⟩
example : intake tokenVerifier fb = some ⟨goalAA, [.lam A, .hyp A], true, 100, "pcs-token-checker-v1"⟩ := by
  decide

/-! ### Forged success, forged reward, unverified closure, stale receipts -/

/-- A forged success claim with a producer-chosen reward is rejected. -/
example : intake tokenVerifier ⟨goalAA, [.hyp A], 100, true, some ⟨goalAA, [.hyp A], "pcs-token-checker-v1"⟩⟩
    = none := by decide

/-- The lying oracle reports `closed`, but independent verification fails: reward `-0.2`. -/
example : (step tokenVerifier lyingObs 24 (reset lyingObs goalAA) (.hyp A)).toOption.map (·.reward) =
    some (-20) := by decide

/-- Changed checker revision: a stored receipt no longer replays. -/
example : replay { tokenVerifier with revision := "pcs-token-checker-v2" }
    ⟨goalAA, [.lam A, .hyp A], "pcs-token-checker-v1"⟩ = false := by decide

/-- A receipt for a different goal does not certify the original. -/
example : replay tokenVerifier ⟨.imp A (.atom 1), [.lam A, .hyp A], "pcs-token-checker-v1"⟩ = false := by
  decide

/-! ### Hidden evaluation labels and family splits -/

def recTrain (hidden : Option (List Tok)) : Record Fm Tok :=
  ⟨"t1", "famA", .train, goalAA, some [.lam A, .hyp A], ⟨"MIT", "rev1"⟩, hidden⟩
def recEval (hidden : Option (List Tok)) : Record Fm Tok :=
  ⟨"e1", "famB", .eval, goalAA, none, ⟨"MIT", "rev1"⟩, hidden⟩

def D₁ : List (Record Fm Tok) := [recTrain none, recEval (some [.lam A, .hyp A])]
def D₂ : List (Record Fm Tok) := [recTrain (some [.topI]), recEval none]

theorem hidden_labels_do_not_leak :
    exportTrain tokenVerifier (D₁.map Record.pub) = exportTrain tokenVerifier (D₂.map Record.pub) :=
  export_noninterference tokenVerifier D₁ D₂ rfl

example : (exportTrain tokenVerifier (D₁.map Record.pub)).map (·.id) = ["t1"] := by decide

/-- A training record from an evaluation family is excluded. -/
example : (exportTrain tokenVerifier ([{ recTrain none with family := "famB" }, recEval none].map
    Record.pub)).length = 0 := by decide

/-! ### Dense reward versus potential shaping -/

example : Shaping.denseValid 1 3 + Shaping.denseValid 3 1 = 2 := Shaping.dense_reward_cycle_positive

end PCSVerifiedLearning.Controls
