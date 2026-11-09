import AttestedProduct

/-!
Illustrative numeric projection extracted from a synthetic Writ/15 execution
after the separate Python verifier checked BOTH operator and receiver Ed25519
signatures. Full signed JSON transcript and independently pinned public keys
are shipped with the companion Writ/15 distribution, not this Lean file.

Lean verifies the projected source, weighted budget, and receipt-binding
semantics. It does not itself check Ed25519 or identify the signer as honest.
-/
namespace Writ15Fixture

def sourceCommitment : Nat :=
  97554329882246246114229875910268885102600221186505824932191165658316970476428

def parents : Fin 1 → List (Fin 1) := fun _ => []
def labels : Fin 1 → Nat := fun _ => 0
def starting : Fin 2 → Nat := fun i => if i.val == 0 then 5 else 2
def charge : Fin 2 → Nat := fun _ => 1
def charges : List (Fin 2 → Nat) := [charge]

def expected : Writ15.Binding :=
  { policy := 87544343482768502469636812256405526291546689157509696428648409483797335737600
    effect := 1
    route := 27773815423176766703613532310480320232833473674259864844586109163621006755969
    payload := 20105344810655015188488190450198287757521411006383763366373856062732475737022
    lease := 302511813199519734631724711080220965361
    receiver := 93950817961167377765049842699077221743960953085394373545371963814999453520397 }

def observed : Writ15.Binding := expected
def receiverProof : Writ15.Attestation :=
  { binding := observed, signatureVerified := true }
def history : List Writ15.Event :=
  [.lease expected.lease, .acknowledgment receiverProof]

example : Writ15.Replay expected .pending history = some (.delivered receiverProof) := by decide

example : (Writ15.CheckAttested sourceCommitment sourceCommitment parents labels
      starting charges expected history receiverProof).map
        (fun balance => balance (0 : Fin 2)) = some 4 := by decide

example : (Writ15.CheckAttested sourceCommitment sourceCommitment parents labels
      starting charges expected history receiverProof).map
        (fun balance => balance (1 : Fin 2)) = some 1 := by decide

example : Writ15.Next { expected with receiver := expected.receiver + 1 }
      (.working expected.lease) (.acknowledgment receiverProof) = none := by decide

example : Writ15.Next expected (.working expected.lease)
      (.acknowledgment { receiverProof with signatureVerified := false }) = none := by decide

example : Writ15.Replay expected .pending
      (history ++ [.lease expected.lease]) = none := by decide

end Writ15Fixture
