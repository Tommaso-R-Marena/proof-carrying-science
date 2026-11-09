import Std

/-!
Writ/14: proof-carrying effect lifecycle (abstract, finite-state).
A signed event is not proof that an external side effect occurred. This model
checks structural consistency: delivery must follow a lease, terminal states
cannot be reentered, and uncertain outcomes cannot be automatically retried.
An actual runtime bridge must authenticate events and bind effect identifiers.
-/
namespace Writ14

inductive State where
  | pending | working | delivered | uncertain | canceled | suppressed | expired
  deriving DecidableEq, Repr

inductive Event where
  | lease | delivered | uncertain | cancel | suppress | expire
  deriving DecidableEq, Repr

def Allowed (before : State) (event : Event) (after : State) : Prop :=
  (before = .pending ∧ event = .lease ∧ after = .working) ∨
  (before = .working ∧ event = .delivered ∧ after = .delivered) ∨
  (before = .working ∧ event = .uncertain ∧ after = .uncertain) ∨
  (before = .pending ∧ event = .cancel ∧ after = .canceled) ∨
  (before = .pending ∧ event = .suppress ∧ after = .suppressed) ∨
  (before = .pending ∧ event = .expire ∧ after = .expired)

def Next : State → Event → Option State
  | .pending, .lease => some .working
  | .working, .delivered => some .delivered
  | .working, .uncertain => some .uncertain
  | .pending, .cancel => some .canceled
  | .pending, .suppress => some .suppressed
  | .pending, .expire => some .expired
  | _, _ => none

theorem next_iff_allowed (before : State) (event : Event) (after : State) :
    Next before event = some after ↔ Allowed before event after := by
  cases before <;> cases event <;> cases after <;> simp [Next, Allowed]

def Replay (before : State) : List Event → Option State
  | [] => some before
  | event :: rest =>
      match Next before event with
      | none => none
      | some middle => Replay middle rest

inductive Runs : State → List Event → State → Prop where
  | done (before : State) : Runs before [] before
  | step (before : State) (event : Event) (middle : State)
      (rest : List Event) (after : State)
      (valid : Allowed before event middle)
      (tail : Runs middle rest after) :
      Runs before (event :: rest) after

theorem replay_sound {before after : State} {trace : List Event}
    (accepted : Replay before trace = some after) : Runs before trace after := by
  induction trace generalizing before with
  | nil =>
      have eq : before = after := by simpa [Replay] using accepted
      subst after
      exact Runs.done before
  | cons event rest ih =>
      cases h : Next before event with
      | none =>
          simp [Replay, h] at accepted
      | some middle =>
          have htail : Replay middle rest = some after := by
            simpa [Replay, h] using accepted
          exact Runs.step before event middle rest after
            ((next_iff_allowed before event middle).mp h) (ih htail)

theorem replay_complete {before after : State} {trace : List Event}
    (valid : Runs before trace after) : Replay before trace = some after := by
  induction valid with
  | done _ => simp [Replay]
  | step before event middle rest after good tail ih =>
      have hstep : Next before event = some middle :=
        (next_iff_allowed before event middle).mpr good
      simpa [Replay, hstep] using ih

def Terminal : State → Prop
  | .delivered | .uncertain | .canceled | .suppressed | .expired => True
  | .pending | .working => False

theorem terminal_has_no_next {state : State} (terminal : Terminal state)
    (event : Event) : Next state event = none := by
  cases state <;> cases event <;> simp_all [Terminal, Next]

theorem terminal_replay_refuses_nonempty {state : State}
    (terminal : Terminal state) (event : Event) (rest : List Event) :
    Replay state (event :: rest) = none := by
  simp [Replay, terminal_has_no_next terminal event]

example : Replay .pending [.delivered] = none := by decide
example : Replay .pending [.lease, .delivered] = some .delivered := by decide
example : Replay .pending [.lease, .delivered, .delivered] = none := by decide
example : Replay .pending [.lease, .delivered, .cancel] = none := by decide
example : Replay .pending [.lease, .uncertain, .lease] = none := by decide
example : Replay .pending [.cancel, .lease] = none := by decide

end Writ14
