import Std

/-!
Writ/11 — isolated external-witness model (not a proof of Python/SQLite).

Fingerprint equality is an idealized equality of the entire committed ledger
identity (sequence, authenticated log head, state MAC). This file does not prove
collision resistance, key isolation, OS durability, or that Python checks it.
The external witness is assumed to be controlled outside the DB rollback domain.
-/
namespace Writ11

structure Fingerprint where
  sequence : Nat
  head : Nat
  seal : Nat
  deriving DecidableEq, Repr

structure HostState where
  database : Fingerprint
  witness : Fingerprint

/-- Admission/dispatch authority requires a matching external witness. -/
def Ready (s : HostState) : Prop := s.database = s.witness

/-- Stage 1: SQLite commits, but the witness has not advanced yet. -/
def CommitDatabase (s : HostState) (next : Fingerprint) : HostState :=
  { database := next, witness := s.witness }

/-- Stage 2: operator witness is committed to the exact database identity. -/
def PublishWitness (s : HostState) : HostState :=
  { database := s.database, witness := s.database }

/-- A successful checkpoint authorizes the currently recorded identity. -/
theorem published_witness_ready (s : HostState) :
    Ready (PublishWitness s) := by
  rfl

/-- A crash between database commit and witness publication refuses work. -/
theorem interrupted_commit_fails_closed (s : HostState) (next : Fingerprint)
    (fresh : next ≠ s.witness) : ¬ Ready (CommitDatabase s next) := by
  simpa [Ready, CommitDatabase] using fresh

/-- Restoring a different database identity cannot pass the existing witness. -/
theorem rollback_snapshot_refused (old current : Fingerprint)
    (different : old ≠ current) :
    ¬ Ready ⟨old, current⟩ := by
  exact different

/-- A strictly earlier sequence is enough to demonstrate identity mismatch. -/
theorem older_sequence_refused (old current : Fingerprint)
    (earlier : old.sequence < current.sequence) :
    ¬ Ready ⟨old, current⟩ := by
  intro eq
  have same : old.sequence = current.sequence := congrArg Fingerprint.sequence eq
  omega

/-- Even with equal sequence numbers, different committed seals are refused. -/
theorem same_step_modified_state_refused (old current : Fingerprint)
    (differentSeal : old.seal ≠ current.seal) :
    ¬ Ready ⟨old, current⟩ := by
  intro eq
  exact differentSeal (congrArg Fingerprint.seal eq)

/-- The type of permission granted by a witness-gated host. -/
inductive MayExecute : HostState → Prop where
  | matched (s : HostState) (equal : Ready s) : MayExecute s

/-- No old snapshot is authorized after an independently advanced witness. -/
theorem old_snapshot_cannot_execute (old current : Fingerprint)
    (different : old ≠ current) :
    ¬ MayExecute ⟨old, current⟩ := by
  intro proof
  cases proof with
  | matched _ h => exact different h

end Writ11
