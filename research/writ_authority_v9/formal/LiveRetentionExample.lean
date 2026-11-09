import LiveRetention

/-!
Illustrative bounded and independently challenge-bound readback fixture.

The key and filesystem assertions themselves are trusted inputs here:
the kernel checks structural freshness and combination with authority,
not Ed25519 or physical durability.
-/
namespace Writ16Fixture

def acknowledged : Writ16.RetainedBinding :=
  { policy := 11, receiver := 29, effect := 1,
    route := 17, payload := 23, size := 18, lease := 31,
    acknowledgment := 37 }

def challenged : Writ16.Readback :=
  { binding := acknowledged, challenge := 101,
    bytesPresent := true, signatureVerified := true }

example : Writ16.CheckFresh acknowledged 101 challenged = true := by decide
example : Writ16.CheckFresh acknowledged 102 challenged = false := by decide
example : Writ16.CheckFresh {acknowledged with payload := 24}
    101 challenged = false := by decide
example : Writ16.CheckFresh acknowledged 101
    {challenged with bytesPresent := false} = false := by decide
example : Writ16.CheckFresh acknowledged 101
    {challenged with signatureVerified := false} = false := by decide
example : Writ16.CheckFresh acknowledged 101
    {challenged with binding := {acknowledged with receiver := 30}}
    = false := by decide

end Writ16Fixture
