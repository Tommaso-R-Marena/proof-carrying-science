import AnchoredExecution
/-! Verified detached Writ/13 receipt projection.
Policy: 78fde2f2c8ebe499d40e83fdd9efb2746edf3f656806190481e90f94c9f47cd4
Source commitment: 35508ee5c4f886ef8a2154b81ce39a5318ec6d0334995d2dc1179087ac78eb8a
Audit head: 34a3184c624d95c4ce9d34dda679c01782668d779d058571d73a1ab664e318fa
The Ed25519 signature and SHA-256 preimage are checked separately by Python. -/
namespace Writ13Receipt
def committedSource : Nat := 24114914982647867650610484457234773246074996170021575180031113844343262735242
def presentedSource : Nat := 24114914982647867650610484457234773246074996170021575180031113844343262735242
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
end Writ13Receipt
