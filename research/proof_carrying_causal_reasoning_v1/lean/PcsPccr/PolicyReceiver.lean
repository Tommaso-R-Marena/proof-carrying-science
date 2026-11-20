import PcsPccr.PolicyAdjustment

/-! Bounded data-only certificates. The separately supplied study fixes the
assumption class, policy, action domain, and observed population. Every return
from receive carries a kernel-checked consequence about that decoded study. -/
namespace PcsPccr.PolicyReceiver
open PolicyIdentification

inductive Assumptions where
  | unrestricted
  | exchangeable
  deriving DecidableEq

structure Study where
  strata : Nat
  actions : Nat
  assumptions : Assumptions
  policy : Policy strata actions
  data : List (Datum strata actions)

inductive Claim where
  | bounds (lo hi : Nat)
  | witnesses (first second : Nat)
  | adjusted (successes : Nat)

def Meaning (t : Study) : Claim → Prop
  | .bounds lo hi => t.assumptions = .unrestricted ∧ t.data ≠ [] ∧
    ∀ k, (∃ m, Compatible t.data m ∧ value t.policy m = k) ↔ lo ≤ k ∧ k ≤ hi
  | .witnesses k j => t.assumptions = .unrestricted ∧ k ≠ j ∧
    (∃ m n, Compatible t.data m ∧ Compatible t.data n ∧ value t.policy m = k ∧ value t.policy n = j) ∧
    ¬ ∃ target, ∀ m, Compatible t.data m → value t.policy m = target
  | .adjusted k => t.assumptions = .exchangeable ∧
    (∃ m, Compatible t.data m ∧ Balanced t.policy m) ∧
    ∀ m, Compatible t.data m → Balanced t.policy m → value t.policy m = k

def decimal (t : String) : Option Nat := do
  guard (t.length ≤ 9)
  let n ← t.toNat?
  guard (toString n == t)
  return n

def bounded (size : Nat) (t : String) : Option (Fin size) := do
  let n ← decimal t
  if h : n < size then return ⟨n,h⟩ else none

private def records (f : String → Option α) (t : String) : Option (List α) := do
  let parts := t.splitOn ";"
  guard (parts.length ≤ 128)
  parts.mapM f

private def datum (s a : Nat) (t : String) : Option (Datum s a) := do
  let [z, x, b] := t.splitOn "," | none
  let outcome ← match b with
    | "0" => some false
    | "1" => some true
    | _ => none
  return ⟨← bounded s z, ← bounded a x, outcome⟩

def study (line : String) : Option Study := do
  guard (line.length ≤ 8192)
  let [kind, a, policy, rows] := line.splitOn "|" | none
  let assumptions ← match kind with
    | "U" => some Assumptions.unrestricted
    | "E" => some Assumptions.exchangeable
    | _ => none
  let a ← decimal a
  guard (0 < a && a ≤ 16)
  let actions ← (policy.splitOn ",").mapM (bounded a)
  guard (0 < actions.length && actions.length ≤ 32)
  let data ← records (datum actions.length a) rows
  return ⟨actions.length, a, assumptions, fun z => actions[z.val], data⟩

private def unitModel (s a : Nat) (t : String) : Option (UnitModel s a) := do
  let [z, x, m] := t.splitOn "," | none
  let mask ← decimal m
  guard (mask < 2^a)
  return ⟨← bounded s z, ← bounded a x, fun action => mask.testBit action.val⟩

/-- Malformed, unsupported, and forged certificates all return none.
The accepted subtype enforces the mathematical interpretation on every branch. -/
def receive (t : Study) (line : String) : Option {c : Claim // Meaning t c} := do
  guard (line.length ≤ 8192)
  match line.splitOn "|" with
  | ["B", l, u] =>
    let lo ← decimal l
    let hi ← decimal u
    if h : t.assumptions = .unrestricted ∧ checkBounds t.policy t.data lo hi = true then
      return ⟨.bounds lo hi, h.1, bounds_sound h.2⟩
    else none
  | ["W", l, u, first, second] =>
    let k ← decimal l
    let j ← decimal u
    let m ← records (unitModel t.strata t.actions) first
    let n ← records (unitModel t.strata t.actions) second
    if h : t.assumptions = .unrestricted ∧ checkPair t.policy t.data m n k j = true then
      have sound := pair_sound h.2
      have ne := (of_decide_eq_true h.2).2.2.2.2.2
      return ⟨.witnesses k j, h.1, ne, ⟨m, n, sound.1, sound.2.1, sound.2.2.1, sound.2.2.2.1⟩,
        sound.2.2.2.2⟩
    else none
  | ["A", num, model] =>
    let k ← decimal num
    let m ← records (unitModel t.strata t.actions) model
    if h : t.assumptions = .exchangeable ∧ checkAdjusted t.policy t.data m k = true then
      return ⟨.adjusted k, h.1, adjusted_sound h.2⟩
    else none
  | _ => none

def Claim.render : Claim → String
  | .bounds lo hi =>
    if lo == hi then s!"IDENTIFIED {lo}" else s!"PARTIALLY_IDENTIFIED {lo} {hi}"
  | .witnesses k j => s!"NOT_IDENTIFIED {k} {j}"
  | .adjusted k => s!"IDENTIFIED {k}"

/-- This existential includes the caller's chosen raw study as well as its
successful decoding. No accepted text can render a claim without its Meaning. -/
def check (source proposal : String) : Option String := do
  let t ← study source
  let receipt ← receive t proposal
  return receipt.val.render

theorem check_sound (h : check source proposal = some reply) :
    ∃ t c, study source = some t ∧ Meaning t c ∧ reply = c.render := by
  unfold check at h
  cases hd : study source with
  | none => simp [hd] at h
  | some t =>
    cases hc : receive t proposal with
    | none => simp [hd, hc] at h
    | some r =>
      simp [hd, hc] at h
      exact ⟨t, r.val, rfl, r.property, h.symm⟩

end PcsPccr.PolicyReceiver
