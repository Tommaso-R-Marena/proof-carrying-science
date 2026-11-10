import Std

/-!
Writ/17 receiver-side durable first-claim calculus.

The receiver must durably and exclusively reserve the effect ID bound to
(policy, route, bytes, lease and receiver) BEFORE writing. A missing ACK after
reservation is uncertain, never an invitation to automatically resubmit.
Theorems concern this executable transition system. The OS exclusive link,
fsync, key isolation and lack of rollback are explicit trusted assumptions.
-/
namespace Writ17

structure Binding where
  policy : Nat
  effect : Nat
  route : Nat
  payload : Nat
  lease : Nat
  receiver : Nat
  deriving DecidableEq, Repr

inductive State where
  | free
  | claimed (binding : Binding)
  | written (binding : Binding)
  | acknowledged (binding : Binding)
  | uncertain (binding : Binding)
  deriving DecidableEq, Repr

inductive Event where
  | reserve (binding : Binding)
  | write (binding : Binding)
  | acknowledge (binding : Binding)
  | replay (binding : Binding)
  | crash
  deriving DecidableEq, Repr

def Next : State → Event → Option State
  | .free, .reserve b => some (.claimed b)
  | .claimed x, .write b => if x = b then some (.written x) else none
  | .written x, .acknowledge b =>
      if x = b then some (.acknowledged x) else none
  | .acknowledged x, .replay b =>
      if x = b then some (.acknowledged x) else none
  | .claimed x, .crash => some (.uncertain x)
  | .written x, .crash => some (.uncertain x)
  | .acknowledged x, .crash => some (.acknowledged x)
  | _, _ => none

def Replay (start : State) : List Event → Option State
  | [] => some start
  | event :: rest =>
      match Next start event with
      | none => none
      | some middle => Replay middle rest

def ClaimOf : State → Option Binding
  | .free => none
  | .claimed x => some x
  | .written x => some x
  | .acknowledged x => some x
  | .uncertain x => some x

theorem next_preserves_claim (b : Binding) (start finish : State)
    (event : Event) (pinned : ClaimOf start = some b)
    (h : Next start event = some finish) : ClaimOf finish = some b := by
  cases start <;> cases event <;> cases finish <;>
    simp_all [Next, ClaimOf] <;> split_ifs at h <;> simp_all [ClaimOf]

theorem replay_preserves_claim (b : Binding) (events : List Event)
    (start finish : State) (pinned : ClaimOf start = some b)
    (accepted : Replay start events = some finish) :
    ClaimOf finish = some b := by
  induction events generalizing start with
  | nil =>
      have eq : start = finish := by simpa [Replay] using accepted
      subst finish
      exact pinned
  | cons event rest ih =>
      cases hstep : Next start event with
      | none => simp [Replay, hstep] at accepted
      | some middle =>
          have htail : Replay middle rest = some finish := by
            simpa [Replay, hstep] using accepted
          exact ih middle
            (next_preserves_claim b start middle event pinned hstep) htail

theorem no_equivocation_after_claim (original other : Binding)
    (events : List Event)
    (accepted : Replay (.claimed original) events =
      some (.acknowledged other)) : other = original := by
  have h := replay_preserves_claim original events
    (.claimed original) (.acknowledged other) rfl accepted
  simpa [ClaimOf] using h

theorem no_second_different_ack (original other : Binding)
    (different : other ≠ original) :
    Next (.acknowledged original) (.acknowledge other) = none ∧
    Next (.acknowledged original) (.replay other) = none := by
  simp [Next, different, Ne.symm different]

theorem uncertain_is_terminal (original : Binding) (event : Event) :
    Next (.uncertain original) event = none := by
  cases event <;> rfl

theorem no_automatic_retry_after_crash (original new : Binding) :
    Next (.uncertain original) (.reserve new) = none ∧
    Next (.uncertain original) (.acknowledge new) = none := by
  rfl

example (b : Binding) :
    Replay .free [.reserve b, .write b, .acknowledge b] =
      some (.acknowledged b) := by
  simp [Replay, Next]

example (b c : Binding) (different : b ≠ c) :
    Replay .free [.reserve b, .write b, .acknowledge c] = none := by
  simp [Replay, Next, different]

end Writ17
