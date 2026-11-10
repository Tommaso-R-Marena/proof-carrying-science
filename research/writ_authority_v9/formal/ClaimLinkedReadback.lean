import Std

/-!
Writ/18: executable, claim-linked live-readback checker.

The real receiver must independently read and compare its durable original
reservation, historical ACK and actual output bytes before signing a fresh
nonce-bound readback. In this model, claim/readback/signature booleans are
trusted projections of those real checks, NOT Lean proofs of Ed25519, POSIX,
fsync, source authenticity, OS isolation, or Python refinement.
-/
namespace Writ18

structure Binding where
  policy : Nat
  effect : Nat
  route : Nat
  payload : Nat
  lease : Nat
  receiver : Nat
  deriving DecidableEq, Repr

structure Readback where
  binding : Binding
  challenge : Nat
  claimLinked : Bool
  signatureVerified : Bool
  deriving DecidableEq, Repr

def Valid (expected : Binding) (claim : Option Binding)
    (ack : Binding) (nonce : Nat) (fresh : Readback) : Prop :=
  claim = some expected ∧ ack = expected ∧
  fresh.binding = expected ∧ fresh.challenge = nonce ∧
  fresh.claimLinked = true ∧ fresh.signatureVerified = true

def CheckLinked (expected : Binding) (claim : Option Binding)
    (ack : Binding) (nonce : Nat) (fresh : Readback) : Bool :=
  decide (claim = some expected) && decide (ack = expected) &&
  decide (fresh.binding = expected) && decide (fresh.challenge = nonce) &&
  fresh.claimLinked && fresh.signatureVerified

theorem checkLinked_iff (expected : Binding) (claim : Option Binding)
    (ack : Binding) (nonce : Nat) (fresh : Readback) :
    CheckLinked expected claim ack nonce fresh = true ↔
    Valid expected claim ack nonce fresh := by
  simp [CheckLinked, Valid, Bool.and_eq_true]

theorem no_fresh_receipt_without_claim (expected ack : Binding)
    (nonce : Nat) (fresh : Readback) :
    CheckLinked expected none ack nonce fresh = false := by
  simp [CheckLinked]

theorem no_readback_with_different_claim (expected observed ack : Binding)
    (nonce : Nat) (fresh : Readback)
    (different : observed ≠ expected) :
    CheckLinked expected (some observed) ack nonce fresh = false := by
  simp [CheckLinked, different]

theorem old_nonce_refused (expected ack : Binding) (claim : Option Binding)
    (fresh : Readback) (nonce : Nat) (different : fresh.challenge ≠ nonce) :
    CheckLinked expected claim ack nonce fresh = false := by
  simp [CheckLinked, different]

theorem verified_claim_attested (expected : Binding) (claim : Option Binding)
    (ack : Binding) (nonce : Nat) (fresh : Readback)
    (accepted : CheckLinked expected claim ack nonce fresh = true) :
    claim = some expected ∧ ack = expected ∧
    fresh.binding = expected ∧ fresh.challenge = nonce ∧
    fresh.claimLinked = true ∧ fresh.signatureVerified = true := by
  exact (checkLinked_iff expected claim ack nonce fresh).mp accepted

/-!
An erased original reservation, ACK and output present the same local data
as a never-used receiver. Any policy preventing complete local rollback must
therefore rely on an external, non-rollbackable witness.
-/
inductive History where
  | neverUsed | usedAndFullyErased
  deriving DecidableEq

structure LocalView where
  claim : Option Binding
  ack : Option Binding
  deriving DecidableEq

def afterCompleteErasure : History → LocalView
  | .neverUsed => ⟨none, none⟩
  | .usedAndFullyErased => ⟨none, none⟩

theorem no_local_history_distinction (decision : LocalView → Bool) :
    decision (afterCompleteErasure .neverUsed) =
      decision (afterCompleteErasure .usedAndFullyErased) := by
  rfl

end Writ18
