import PCS.V2.ProofGatedFormalization

/-!
# Proof-coupled PGRA gate — exact finite proved/unproved certificates

Same Bool-computable preserve / expand / strict-loss gate as
`ProofGatedFormalization`, specialized to a two-status proof certificate:

* `unproved`  — kernel search did not verify (maps to `CaseStatus.fail`)
* `proved`    — independently verified receipt (maps to `CaseStatus.supported`)

Abstention is unused for proof targets (they are always in-scope obligations).
Research-only; not a deployment authority.
-/

namespace PCS.V2.ProofGatedProofCoupled

open PCS.V2.ProofGatedFormalization

/-- Proof-target outcome on a frozen proof-id set. -/
inductive ProofStatus where
  | unproved
  | proved
  deriving Repr, DecidableEq, Inhabited

def ProofStatus.toCase : ProofStatus → CaseStatus
  | .unproved => .fail
  | .proved => .supported

def ProofStatus.ofCase? : CaseStatus → Option ProofStatus
  | .fail => some .unproved
  | .supported => some .proved
  | .abstain => none

def ProofStatus.toNat : ProofStatus → Nat
  | .unproved => 0
  | .proved => 1

def ProofStatus.ofNat? : Nat → Option ProofStatus
  | 0 => some .unproved
  | 1 => some .proved
  | _ => none

theorem ProofStatus.ofNat_toNat (s : ProofStatus) :
    ProofStatus.ofNat? s.toNat = some s := by
  cases s <;> rfl

abbrev ProofCapability := List ProofStatus

def toFormal (c : ProofCapability) : Capability :=
  c.map ProofStatus.toCase

def loss (c : ProofCapability) : Nat :=
  PCS.V2.ProofGatedFormalization.loss (toFormal c)

def accept (a b : ProofCapability) : Bool :=
  PCS.V2.ProofGatedFormalization.accept (toFormal a) (toFormal b)

def admissible (a b : ProofCapability) : Prop :=
  PCS.V2.ProofGatedFormalization.admissible (toFormal a) (toFormal b)

theorem accept_sound {a b : ProofCapability} (h : accept a b = true) :
    admissible a b :=
  PCS.V2.ProofGatedFormalization.accept_sound h

theorem accepted_strict_loss {a b : ProofCapability} (h : accept a b = true) :
    loss b < loss a :=
  PCS.V2.ProofGatedFormalization.accepted_strict_loss h

theorem two_accepted_steps {a b c : ProofCapability}
    (hab : accept a b = true) (hbc : accept b c = true) :
    loss c < loss a :=
  PCS.V2.ProofGatedFormalization.two_accepted_steps hab hbc

/-- Concrete: unlocking one previously unproved target is accepted. -/
example : accept [.unproved, .proved, .unproved] [.proved, .proved, .unproved] = true := by
  native_decide

/-- Concrete: dropping a proved target is rejected. -/
example : accept [.proved, .unproved] [.unproved, .unproved] = false := by
  native_decide

/-- Concrete: no-op (no expansion) is rejected. -/
example : accept [.proved, .unproved] [.proved, .unproved] = false := by
  native_decide

end PCS.V2.ProofGatedProofCoupled
