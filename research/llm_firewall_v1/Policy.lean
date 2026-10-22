import Std.Tactic

/-! The model is an arbitrary untrusted proposer. Only accepted, completely
    mediated tool actions are covered. Compiler/OS/broker refinement is external. -/
set_option autoImplicit false
namespace PCSLLMFirewall

inductive Action where
  | readPublic | readPrivate | writePrivate | publish | finish
  | deleteProtected | network | grantAdmin
  deriving DecidableEq, Repr

structure State where
  generation : Nat
  remaining : Nat
  tainted : Bool
  deriving DecidableEq, Repr

def initial : State := ⟨0, 8, false⟩
def Valid (s : State) : Prop := s.generation ≤ 8 ∧ s.remaining ≤ 8
instance (s : State) : Decidable (Valid s) := inferInstanceAs (Decidable (_ ∧ _))
def forbidden (a : Action) : Bool :=
  a == .deleteProtected || a == .network || a == .grantAdmin
def publicSink (a : Action) : Bool := a == .publish || a == .finish
def cost (a : Action) : Nat := if a == .publish then 2 else 1

def step (s : State) (a : Action) : Option State :=
  if Valid s ∧ s.generation < 8 ∧ cost a ≤ s.remaining ∧
      forbidden a = false ∧ (publicSink a = false ∨ s.tainted = false) then
    some ⟨s.generation + 1, s.remaining - cost a, s.tainted || a == .readPrivate⟩
  else none

theorem step_facts {s t : State} {a : Action} (h : step s a = some t) :
    Valid s ∧ s.generation < 8 ∧ cost a ≤ s.remaining ∧
    forbidden a = false ∧ (publicSink a = false ∨ s.tainted = false) ∧
    t = ⟨s.generation + 1, s.remaining - cost a, s.tainted || a == .readPrivate⟩ := by
  unfold step at h
  split at h
  · rename_i good
    cases h
    exact ⟨good.1, good.2.1, good.2.2.1, good.2.2.2.1, good.2.2.2.2, rfl⟩
  · cases h

theorem step_valid {s t : State} {a : Action} (h : step s a = some t) : Valid t := by
  obtain ⟨hs, hg, _, _, _, rfl⟩ := step_facts h
  unfold Valid at *
  simp only
  omega

theorem step_budget {s t : State} {a : Action} (h : step s a = some t) :
    t.remaining + cost a = s.remaining := by
  obtain ⟨_, _, hc, _, _, rfl⟩ := step_facts h
  exact Nat.sub_add_cancel hc

theorem step_generation {s t : State} {a : Action} (h : step s a = some t) :
    t.generation = s.generation + 1 := by
  obtain ⟨_, _, _, _, _, rfl⟩ := step_facts h
  rfl

theorem step_forbidden {s t : State} {a : Action} (h : step s a = some t) :
    forbidden a = false := (step_facts h).2.2.2.1

theorem step_taint {s t : State} {a : Action} (h : step s a = some t)
    (ht : s.tainted = true) : t.tainted = true := by
  obtain ⟨_, _, _, _, _, rfl⟩ := step_facts h
  simp [ht]

theorem step_private {s t : State} (h : step s .readPrivate = some t) :
    t.tainted = true := by
  obtain ⟨_, _, _, _, _, rfl⟩ := step_facts h
  simp

theorem step_no_public {s t : State} {a : Action} (h : step s a = some t)
    (ht : s.tainted = true) : publicSink a = false := by
  rcases (step_facts h).2.2.2.2.1 with hp | hf
  · exact hp
  · rw [ht] at hf; cases hf

inductive History : State → List Action → State → Prop where
  | nil (s : State) : History s [] s
  | cons {s t u : State} {a : Action} {as : List Action}
      (head : step s a = some t) (tail : History t as u) : History s (a :: as) u

theorem history_forbidden {s t : State} {as : List Action} (h : History s as t) :
    ∀ a ∈ as, forbidden a = false := by
  induction h with
  | nil _ => simp
  | cons head _ ih =>
    intro a ha
    rcases List.mem_cons.mp ha with rfl | hm
    · exact step_forbidden head
    · exact ih a hm

theorem history_budget {s t : State} {as : List Action} (h : History s as t) :
    t.remaining + (as.map cost).sum = s.remaining := by
  induction h with
  | nil _ => simp
  | cons head _ ih =>
    have hb := step_budget head
    simp only [List.map_cons, List.sum_cons]
    omega

theorem history_generation {s t : State} {as : List Action} (h : History s as t) :
    t.generation = s.generation + as.length := by
  induction h with
  | nil _ => simp
  | cons head _ ih =>
    have hg := step_generation head
    simp only [List.length_cons]
    omega

theorem history_valid {s t : State} {as : List Action} (h : History s as t)
    (hv : Valid s) : Valid t := by
  induction h with
  | nil _ => exact hv
  | cons head _ ih => exact ih (step_valid head)

theorem initial_history_bound {t : State} {as : List Action} (h : History initial as t) :
    as.length ≤ 8 ∧ (as.map cost).sum ≤ 8 := by
  have hv := history_valid h (by decide)
  have hg := history_generation h
  have hb := history_budget h
  simp only [initial] at hg hb
  unfold Valid at hv
  omega

theorem history_taint {s t : State} {as : List Action} (h : History s as t)
    (hs : s.tainted = true) : t.tainted = true := by
  induction h with
  | nil _ => exact hs
  | cons head _ ih => exact ih (step_taint head hs)

theorem history_no_public {s t : State} {as : List Action} (h : History s as t)
    (hs : s.tainted = true) : ∀ a ∈ as, publicSink a = false := by
  induction h with
  | nil _ => simp
  | cons head _ ih =>
    intro a ha
    rcases List.mem_cons.mp ha with rfl | hm
    · exact step_no_public head hs
    · exact ih (step_taint head hs) a hm

theorem private_blocks_suffix {s t u : State} {as : List Action}
    (head : step s .readPrivate = some t) (tail : History t as u) :
    ∀ a ∈ as, publicSink a = false := history_no_public tail (step_private head)

theorem initial_publish_permitted : step initial .publish = some ⟨1,6,false⟩ := by decide

theorem tainted_publish_refuses (s : State) (ht : s.tainted = true) :
    step s .publish = none := by
  cases h : step s .publish with
  | none => rfl
  | some t => have hp := step_no_public h ht; simp [publicSink] at hp

def actionByte : Action → UInt8
  | .readPublic => 0 | .readPrivate => 1 | .writePrivate => 2 | .publish => 3
  | .finish => 4 | .deleteProtected => 5 | .network => 6 | .grantAdmin => 7

def decodeAction (b : UInt8) : Option Action :=
  match b.toNat with
  | 0 => some .readPublic | 1 => some .readPrivate | 2 => some .writePrivate
  | 3 => some .publish | 4 => some .finish | 5 => some .deleteProtected
  | 6 => some .network | 7 => some .grantAdmin | _ => none

theorem action_roundtrip (a : Action) : decodeAction (actionByte a) = some a := by
  cases a <;> decide

def encode (s : State) (a : Action) : List UInt8 :=
  [1, UInt8.ofNat s.generation, UInt8.ofNat s.remaining,
   if s.tainted then 1 else 0, actionByte a]

def decode (raw : List UInt8) : Option (State × Action) :=
  match raw with
  | [1,g,b,t,a] =>
    if g.toNat ≤ 8 ∧ b.toNat ≤ 8 ∧ (t = 0 ∨ t = 1) then
      (decodeAction a).map (fun act => (⟨g.toNat, b.toNat, t == 1⟩, act))
    else none
  | _ => none

theorem decode_encode (s : State) (a : Action) (h : Valid s) :
    decode (encode s a) = some (s,a) := by
  have hg : s.generation < 256 := by have := h.1; omega
  have hb : s.remaining < 256 := by have := h.2; omega
  cases s with
  | mk generation remaining tainted =>
    cases tainted <;>
      simp [encode, decode, UInt8.toNat_ofNat_of_lt' hg,
        UInt8.toNat_ofNat_of_lt' hb, h.1, h.2, action_roundtrip]

def response (s : State) (a : Action) (accepted : Bool) : List UInt8 :=
  1 :: (if accepted then 1 else 0) :: (encode s a).drop 1

def process (raw : List UInt8) : List UInt8 :=
  match decode raw with
  | none => [1,2,0,0,0,0]
  | some (s,a) => match step s a with
    | none => response s a false
    | some t => response t a true

theorem malformed_refuses (raw : List UInt8) (h : decode raw = none) :
    process raw = [1,2,0,0,0,0] := by simp [process,h]

theorem process_decoded (raw : List UInt8) (s : State) (a : Action)
    (h : decode raw = some (s,a)) :
    process raw = match step s a with
      | none => response s a false
      | some t => response t a true := by simp [process,h]

theorem process_accepts (s t : State) (a : Action) (hv : Valid s)
    (h : step s a = some t) : process (encode s a) = response t a true := by
  rw [process_decoded _ _ _ (decode_encode s a hv), h]

theorem process_sound (raw : List UInt8) (h : (process raw).getD 1 2 = 1) :
    ∃ s a t, decode raw = some (s,a) ∧ step s a = some t ∧
      process raw = response t a true := by
  cases hd : decode raw with
  | none => simp [process,hd] at h
  | some pair =>
    obtain ⟨s,a⟩ := pair
    cases hs : step s a with
    | none => simp [process,hd,hs,response] at h
    | some t => exact ⟨s,a,t,rfl,hs,by simp [process,hd,hs]⟩

theorem wire_forbidden (raw : List UInt8) (h : (process raw).getD 1 2 = 1) :
    ∃ s a t, decode raw = some (s,a) ∧ step s a = some t ∧ forbidden a = false := by
  obtain ⟨s,a,t,hd,hs,_⟩ := process_sound raw h
  exact ⟨s,a,t,hd,hs,step_forbidden hs⟩

def run : State → List Action → Option State
  | s, [] => some s
  | s, a :: as => (step s a).bind (fun t => run t as)

theorem run_sound {s t : State} {as : List Action} (h : run s as = some t) :
    History s as t := by
  induction as generalizing s with
  | nil => simp only [run,Option.some.injEq] at h; subst t; exact .nil s
  | cons a as ih =>
    simp only [run] at h
    cases hs : step s a with
    | none => simp [hs] at h
    | some u => exact .cons hs (ih (by simpa [hs] using h))

end PCSLLMFirewall
