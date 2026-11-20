/-
Graph mutilation for do(X): delete all edges into intervened nodes.
Proved for the confounder graph fragment.
-/
import PcsPccr.ConfounderInd

namespace PcsPccr.Mutilate
open PcsPccr.ConfounderInd

/-- Edges remaining after do(X): drop parents of X. -/
def ParentAfterDoX : Node → Node → Prop
  | .Z, .Y => True
  | .X, .Y => True
  | _, _ => False

theorem doX_removes_Z_to_X : ¬ ParentAfterDoX .Z .X := by
  intro h; exact False.elim h

theorem doX_keeps_X_to_Y : ParentAfterDoX .X .Y := trivial

theorem doX_keeps_Z_to_Y : ParentAfterDoX .Z .Y := trivial

theorem doX_no_incoming_X {a : Node} (h : ParentAfterDoX a .X) : False := by
  cases a <;> exact False.elim h

/-- Surviving edges were original edges. -/
theorem doX_edges_subset {a b : Node} (h : ParentAfterDoX a b) : Parent a b := by
  match a, b with
  | .Z, .Y => exact trivial
  | .X, .Y => exact trivial
  | .Z, .X | .Z, .Z | .X, .X | .X, .Z | .Y, .X | .Y, .Y | .Y, .Z =>
      exact False.elim h

/-- Characterization: keep original edges that do not enter X. -/
theorem doX_char (a b : Node) :
    ParentAfterDoX a b ↔ (Parent a b ∧ b ≠ .X) := by
  match a, b with
  | .Z, .Y =>
      constructor
      · intro _; exact ⟨trivial, by decide⟩
      · intro _; exact trivial
  | .X, .Y =>
      constructor
      · intro _; exact ⟨trivial, by decide⟩
      · intro _; exact trivial
  | .Z, .X =>
      constructor
      · intro h; exact False.elim h
      · intro ⟨_, hb⟩; exact (hb rfl).elim
  | .Z, .Z =>
      constructor
      · intro h; exact False.elim h
      · intro ⟨hp, _⟩; exact False.elim hp
  | .X, .X =>
      constructor
      · intro h; exact False.elim h
      · intro ⟨_, hb⟩; exact (hb rfl).elim
  | .X, .Z =>
      constructor
      · intro h; exact False.elim h
      · intro ⟨hp, _⟩; exact False.elim hp
  | .Y, .X =>
      constructor
      · intro h; exact False.elim h
      · intro ⟨_, hb⟩; exact (hb rfl).elim
  | .Y, .Y =>
      constructor
      · intro h; exact False.elim h
      · intro ⟨hp, _⟩; exact False.elim hp
  | .Y, .Z =>
      constructor
      · intro h; exact False.elim h
      · intro ⟨hp, _⟩; exact False.elim hp

end PcsPccr.Mutilate
