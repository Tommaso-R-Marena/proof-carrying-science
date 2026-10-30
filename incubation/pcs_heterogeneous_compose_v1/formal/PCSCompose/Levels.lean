/-!
# Assurance levels for heterogeneous evidence composition

Formal > Computational > Empirical > Provenance > Open.

Composite assurance is the *meet* (weakest link). Empirical evidence never
promotes to Formal. These are reference-level contracts for the HECK kernel;
they do not authorize production PCS package acceptance.
-/

namespace PCSCompose.Levels

/-- Ordered assurance classes. `formal` is strongest; `open_` is weakest. -/
inductive Level where
  | formal
  | computational
  | empirical
  | provenance
  | open_
  deriving DecidableEq, Repr, Inhabited

/-- Rank: larger means stronger assurance. -/
def Level.rank : Level → Nat
  | .formal => 4
  | .computational => 3
  | .empirical => 2
  | .provenance => 1
  | .open_ => 0

/-- Partial order on assurance strength. -/
def Level.le (a b : Level) : Prop := a.rank ≤ b.rank

instance : DecidableRel Level.le := fun a b =>
  inferInstanceAs (Decidable (a.rank ≤ b.rank))

theorem Level.le_refl (a : Level) : a.le a := Nat.le_refl _

theorem Level.le_trans {a b c : Level} (hab : a.le b) (hbc : b.le c) : a.le c :=
  Nat.le_trans hab hbc

theorem Level.rank_inj {a b : Level} (h : a.rank = b.rank) : a = b := by
  cases a <;> cases b <;> simp [Level.rank] at h ⊢

theorem Level.le_antisymm {a b : Level} (hab : a.le b) (hba : b.le a) : a = b :=
  Level.rank_inj (Nat.le_antisymm hab hba)

/-- Meet = weakest of two levels (lattice meet under `le`). -/
def Level.meet (a b : Level) : Level :=
  if a.rank ≤ b.rank then a else b

theorem Level.meet_comm (a b : Level) : a.meet b = b.meet a := by
  cases a <;> cases b <;> rfl

theorem Level.meet_idempotent (a : Level) : a.meet a = a := by
  cases a <;> rfl

theorem Level.meet_assoc (a b c : Level) : (a.meet b).meet c = a.meet (b.meet c) := by
  cases a <;> cases b <;> cases c <;> rfl

theorem Level.meet_le_left (a b : Level) : (a.meet b).le a := by
  cases a <;> cases b <;> decide

theorem Level.meet_le_right (a b : Level) : (a.meet b).le b := by
  cases a <;> cases b <;> decide

/-- Empirical never equals Formal; their meet is Empirical. -/
theorem empirical_meet_formal : Level.empirical.meet Level.formal = Level.empirical := rfl

theorem empirical_ne_formal : Level.empirical ≠ Level.formal := by decide

/-- Computational meets Empirical yields Empirical (no silent upgrade). -/
theorem computational_meet_empirical :
    Level.computational.meet Level.empirical = Level.empirical := rfl

/-- Provenance cannot discharge a Formal requirement by itself. -/
theorem provenance_meet_formal : Level.provenance.meet Level.formal = Level.provenance := rfl

/-- Folded meet over a list; empty meet is Formal (vacuous strongest identity). -/
def Level.meetList : List Level → Level
  | [] => .formal
  | a :: as => a.meet (meetList as)

theorem meetList_singleton (a : Level) : Level.meetList [a] = a := by
  cases a <;> rfl

theorem meetList_cons_le (a : Level) (as : List Level) :
    (Level.meetList (a :: as)).le a := by
  simpa [Level.meetList] using Level.meet_le_left a (Level.meetList as)

/-- Levels at most Empirical (cannot alone authorize Formal). -/
def Level.atMostEmpirical : Level → Bool
  | .formal | .computational => false
  | .empirical | .provenance | .open_ => true

theorem atMostEmpirical_rank {a : Level} (h : a.atMostEmpirical = true) : a.rank ≤ 2 := by
  cases a <;> simp [Level.atMostEmpirical, Level.rank] at h ⊢

theorem meetList_head_bound (a : Level) (t : List Level) :
    (Level.meetList (a :: t)).rank ≤ a.rank :=
  meetList_cons_le a t

/-- A nonempty list of at-most-empirical levels cannot meet to Formal. -/
theorem meet_of_atMostEmpirical_ne_formal
    (as : List Level) (h : ∀ a ∈ as, a.atMostEmpirical = true)
    (hne : as ≠ []) : Level.meetList as ≠ Level.formal := by
  match as with
  | [] => exact (hne rfl).elim
  | a :: t =>
    intro hf
    have ha : a.atMostEmpirical = true := h a List.mem_cons_self
    have hrank : a.rank ≤ 2 := atMostEmpirical_rank ha
    have hle : (Level.meetList (a :: t)).rank ≤ a.rank := meetList_head_bound a t
    have h4 : (Level.meetList (a :: t)).rank = 4 := by rw [hf]; rfl
    have boom : (4 : Nat) ≤ 2 := Nat.le_trans (h4 ▸ hle) hrank
    exact absurd boom (by decide : ¬((4 : Nat) ≤ 2))

end PCSCompose.Levels
