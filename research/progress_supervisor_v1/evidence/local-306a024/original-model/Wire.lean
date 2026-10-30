import Progress
set_option autoImplicit false
namespace PCSProgressWire
open PCSProgress
structure Request where
  state : Nat
  proposal : Option Nat
  deriving DecidableEq, Repr
inductive Reply where
  | halt | selected (action : Nat) | refused | malformed
  deriving DecidableEq, Repr

def decode : List Nat → Option Request
  | [1,sl,sh,p,al,ah] =>
      if sl<256 ∧ sh<256 ∧ al<256 ∧ ah<256 then
        if p=1 then some ⟨sl+256*sh,some (al+256*ah)⟩
        else if p=0 ∧ al=0 ∧ ah=0 then some ⟨sl+256*sh,none⟩ else none
      else none
  | _ => none

def typed (d : Spec) (r : Request) : Reply :=
  if check d = true ∧ r.state ∈ region d ∧ r.state ∈ d.goals then .halt
  else match choose d r.state r.proposal with
    | some a => .selected a
    | none => .refused

def encode (d : Spec) (s : Nat) : Reply → List Nat
  | .halt => [1,0,0,0,0,0]
  | .selected a => [1,1,a%256,a/256,(rank d s)%256,(rank d s)/256]
  | .refused => [1,2,0,0,0,0]
  | .malformed => [1,3,0,0,0,0]

def process (d : Spec) (raw : List Nat) : List Nat :=
  match decode raw with
  | none => encode d 0 .malformed
  | some r => encode d r.state (typed d r)

def batch (d : Spec) (raw : List Nat) : List Nat :=
  (List.range ((raw.length+5)/6)).flatMap (fun i => process d ((raw.drop (i*6)).take 6))

theorem selected_from_choose {d : Spec} {r : Request} {a : Nat}
    (h : typed d r = .selected a) : choose d r.state r.proposal = some a := by
  unfold typed at h
  split at h
  next => contradiction
  next =>
    cases hc : choose d r.state r.proposal with
    | none => simp [hc] at h
    | some b => simp [hc] at h; subst b; rfl

theorem selected_all_outcomes {d : Spec} {r : Request} {a : Nat}
    (h : typed d r = .selected a) {e : PCSActionShield.Edge}
    (he : e ∈ d.base.edges) (hs : e.source = r.state) (ha : e.action = a) :
    e.target ∈ region d ∧ e.target ∈ d.base.safe ∧
      rank d e.target < rank d r.state ∧ a ∉ d.base.forbidden :=
  chosen_step_progresses (selected_from_choose h) he hs ha

theorem halt_is_goal {d : Spec} {r : Request} (h : typed d r = .halt) :
    check d = true ∧ r.state ∈ region d ∧ r.state ∈ d.goals := by
  unfold typed at h
  split at h
  next cond => exact cond
  next => cases hc : choose d r.state r.proposal <;> simp [hc] at h

theorem malformed_refuses (d : Spec) (raw : List Nat) (h : decode raw = none) :
    process d raw = [1,3,0,0,0,0] := by simp [process,h,encode]
end PCSProgressWire

#print axioms PCSProgressWire.selected_from_choose
#print axioms PCSProgressWire.selected_all_outcomes
#print axioms PCSProgressWire.halt_is_goal
#print axioms PCSProgressWire.malformed_refuses
