import CertNum.Util.RatAux
import Mathlib.Data.Rat.Defs
import Mathlib.Algebra.Order.Ring.Defs
import Mathlib.Tactic.SplitIfs

/-!
# Rational closed intervals

Semantic basis: nonempty closed interval `(lo, hi)` with `lo ≤ hi`.
Empty intervals are explicit. Membership is exact on `ℚ`.
-/

namespace CertNum

inductive EnclStatus where
  | ok
  | emptyDomain
  | undefined
  | unbounded
  | unsupported
  | insufficientPrecision
  | resourceExhausted
  deriving DecidableEq, Repr

inductive Interval where
  | empty
  | nonempty (lo hi : ℚ) (wf : lo ≤ hi)
  deriving Repr

namespace Interval

def mk' (lo hi : ℚ) : Interval :=
  if h : lo ≤ hi then nonempty lo hi h else empty

def singleton (q : ℚ) : Interval :=
  nonempty q q le_rfl

def ofBounds (a b : ℚ) : Interval :=
  mk' (ratMin a b) (ratMax a b)

/-- Well-formedness is enforced by the `nonempty` constructor's `lo ≤ hi` proof. -/
def WellFormed : Interval → Prop
  | empty => True
  | nonempty lo hi _ => lo ≤ hi

theorem wellFormed : ∀ I : Interval, I.WellFormed
  | empty => trivial
  | nonempty _ _ h => h

def Mem (x : ℚ) : Interval → Prop
  | empty => False
  | nonempty lo hi _ => lo ≤ x ∧ x ≤ hi

notation:50 x:50 " ∈ᵢ " I:50 => Interval.Mem x I

def Subset (I J : Interval) : Prop :=
  ∀ x, x ∈ᵢ I → x ∈ᵢ J

infix:50 " ⊆ᵢ " => Interval.Subset

def width : Interval → ℚ
  | empty => 0
  | nonempty lo hi _ => hi - lo

def midpoint : Interval → Option ℚ
  | empty => none
  | nonempty lo hi _ => some ((lo + hi) / 2)

def lo? : Interval → Option ℚ
  | empty => none
  | nonempty lo _ _ => some lo

def hi? : Interval → Option ℚ
  | empty => none
  | nonempty _ hi _ => some hi

inductive SignClass where
  | allNegative
  | allNonPositive
  | allPositive
  | allNonNegative
  | containsZero
  | empty
  deriving DecidableEq, Repr

def signClass : Interval → SignClass
  | empty => .empty
  | nonempty lo hi _ =>
    if hi < 0 then .allNegative
    else if lo > 0 then .allPositive
    else if lo ≤ 0 ∧ 0 ≤ hi then .containsZero
    else if hi ≤ 0 then .allNonPositive
    else .allNonNegative

def containsZero : Interval → Bool
  | empty => false
  | nonempty lo hi _ => decide (lo ≤ 0 ∧ 0 ≤ hi)

def excludesZero : Interval → Bool
  | empty => false
  | nonempty lo hi _ => decide (hi < 0 ∨ 0 < lo)

@[simp] theorem mem_empty (x : ℚ) : (x ∈ᵢ empty) ↔ False := Iff.rfl

@[simp] theorem mem_nonempty (x lo hi : ℚ) (wf : lo ≤ hi) :
    (x ∈ᵢ nonempty lo hi wf) ↔ (lo ≤ x ∧ x ≤ hi) := Iff.rfl

theorem mem_mk'_of_le {x lo hi : ℚ} (hlo : lo ≤ x) (hhi : x ≤ hi) :
    x ∈ᵢ mk' lo hi := by
  unfold mk'
  split_ifs with h
  · exact ⟨hlo, hhi⟩
  · exact (h (le_trans hlo hhi)).elim

theorem subset_refl (I : Interval) : I ⊆ᵢ I := fun _ hx => hx

theorem subset_trans {I J K : Interval} (hij : I ⊆ᵢ J) (hjk : J ⊆ᵢ K) : I ⊆ᵢ K :=
  fun x hx => hjk x (hij x hx)

end Interval

structure Enclosure where
  status : EnclStatus
  interval : Interval
  deriving Repr

namespace Enclosure

def ok (I : Interval) : Enclosure := ⟨.ok, I⟩
def fail (s : EnclStatus) : Enclosure := ⟨s, .empty⟩
def isOk (e : Enclosure) : Bool := decide (e.status = .ok)

end Enclosure

end CertNum
