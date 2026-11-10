import TripleSafety
/-! Verified detached Writ/14 or Writ/13 receipt projection.
Policy: adfb888cd4fcf56ae5b966883bae56d82f2c9fef9d1efe16489d61c509bbf73a
Source commitment: e4dd5022f7456c2228c015e548451eae8b88d1fdad3816c3b4add2c568aec1dc
Audit head: 55c97a8fa36f920b5a7cec6774efa2c16c098f317f858bfa12dffe29e87e4abf
The Ed25519 signature and SHA-256 preimage are checked separately by Python. -/
namespace Writ13Receipt
def committedSource : Nat := 103518355760687384173657415247658004138150314092082632801550357129843914490332
def presentedSource : Nat := 103518355760687384173657415247658004138150314092082632801550357129843914490332
def parents : Fin 1 → List (Fin 1) :=
  fun i : Fin 1 =>
    []
def level : Fin 1 → Nat :=
  fun i : Fin 1 =>
    0
def initial : Fin 5 → Nat :=
  fun i : Fin 5 =>
    if i.val == 0 then 5 else
    if i.val == 1 then 2 else
    if i.val == 2 then 3 else
    if i.val == 3 then 4 else
    5
def charge0 : Fin 5 → Nat :=
  fun i : Fin 5 =>
    if i.val == 0 then 1 else
    if i.val == 1 then 1 else
    if i.val == 2 then 1 else
    if i.val == 3 then 1 else
    1
def trace : List (Fin 5 → Nat) := [
charge0]
-- dimension 0: budget:sends
example : (Writ13.CheckAnchored committedSource presentedSource parents level initial trace).map (fun f => f (0 : Fin 5)) = some 4 := by decide
-- dimension 1: delegate:final_tier
example : (Writ13.CheckAnchored committedSource presentedSource parents level initial trace).map (fun f => f (1 : Fin 5)) = some 1 := by decide
-- dimension 2: delegate:second_tier
example : (Writ13.CheckAnchored committedSource presentedSource parents level initial trace).map (fun f => f (2 : Fin 5)) = some 2 := by decide
-- dimension 3: delegate:worker_release
example : (Writ13.CheckAnchored committedSource presentedSource parents level initial trace).map (fun f => f (3 : Fin 5)) = some 3 := by decide
-- dimension 4: grant:publisher
example : (Writ13.CheckAnchored committedSource presentedSource parents level initial trace).map (fun f => f (4 : Fin 5)) = some 4 := by decide
example : (Writ13.CheckAnchored committedSource (presentedSource + 1) parents level initial trace).isNone = true := by decide
-- Verified lifecycle for effect 1
def effectHistory1 : List Writ14.Event := [.lease, .delivered]
example : Writ14.Replay .pending effectHistory1 = some .delivered := by decide
example : (Writ14.CheckTriple committedSource presentedSource parents level initial trace effectHistory1 .delivered).map (fun f => f (0 : Fin 5)) = some 4 := by decide
example : (Writ14.CheckTriple committedSource presentedSource parents level initial trace effectHistory1 .delivered).map (fun f => f (1 : Fin 5)) = some 1 := by decide
example : (Writ14.CheckTriple committedSource presentedSource parents level initial trace effectHistory1 .delivered).map (fun f => f (2 : Fin 5)) = some 2 := by decide
example : (Writ14.CheckTriple committedSource presentedSource parents level initial trace effectHistory1 .delivered).map (fun f => f (3 : Fin 5)) = some 3 := by decide
example : (Writ14.CheckTriple committedSource presentedSource parents level initial trace effectHistory1 .delivered).map (fun f => f (4 : Fin 5)) = some 4 := by decide
example : Writ14.Replay .pending (effectHistory1 ++ [.lease]) = none := by decide
end Writ13Receipt
