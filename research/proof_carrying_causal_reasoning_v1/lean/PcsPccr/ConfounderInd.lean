/-
Inductive formalization of the classic confounder DAG Z→X, Z→Y, X→Y.

Proofs are by cases / induction on inductive predicates — not `native_decide`
on string BFS. Concrete finite graph only; not a general causality theorem.
-/
namespace PcsPccr.ConfounderInd

inductive Node where
  | Z | X | Y
  deriving DecidableEq, Repr, Inhabited

/-- Directed parent relation: `Parent a b` means a → b. -/
def Parent : Node → Node → Prop
  | .Z, .X => True
  | .Z, .Y => True
  | .X, .Y => True
  | _, _ => False

instance (a b : Node) : Decidable (Parent a b) :=
  match a, b with
  | .Z, .X | .Z, .Y | .X, .Y => isTrue trivial
  | .Z, .Z | .X, .X | .X, .Z | .Y, .Y | .Y, .Z | .Y, .X =>
      isFalse (by intro h; exact False.elim h)

inductive Descendant : Node → Node → Prop where
  | refl : ∀ a, Descendant a a
  | step : ∀ {a b c}, Descendant a b → Parent b c → Descendant a c

theorem parent_X_Y : Parent .X .Y := trivial
theorem parent_Z_X : Parent .Z .X := trivial
theorem parent_Z_Y : Parent .Z .Y := trivial

theorem no_parent_of_Z {a : Node} (h : Parent a .Z) : False := by
  cases a <;> exact False.elim h

/-- Z is not a descendant of X. -/
theorem not_descendant_X_Z : ¬ Descendant .X .Z := by
  intro h
  -- `refl` is impossible (X ≠ Z) and is eliminated automatically.
  cases h with
  | step hab hbc => exact no_parent_of_Z hbc

theorem descendant_X_Y : Descendant .X .Y :=
  Descendant.step (Descendant.refl .X) parent_X_Y

def ProperDescendant (a b : Node) : Prop :=
  Descendant a b ∧ a ≠ b

theorem proper_descendant_X_Y : ProperDescendant .X .Y :=
  ⟨descendant_X_Y, by decide⟩

theorem not_proper_descendant_X_Z : ¬ ProperDescendant .X .Z := by
  intro h
  exact not_descendant_X_Z h.1

def NoDescendantsOfTreatment (treatment : Node) (Zset : List Node) : Prop :=
  ∀ z ∈ Zset, ¬ ProperDescendant treatment z

theorem adjust_Z_ok : NoDescendantsOfTreatment .X [.Z] := by
  intro z hz
  cases hz with
  | head => exact not_proper_descendant_X_Z
  | tail _ h => cases h

theorem adjust_Y_forbidden : ¬ NoDescendantsOfTreatment .X [.Y] := by
  intro h
  exact (h .Y (List.Mem.head _)) proper_descendant_X_Y

theorem adjust_empty_ok : NoDescendantsOfTreatment .X [] := by
  intro z hz
  cases hz

/-- Unique confounder backdoor mid-node Z on walk X ← Z → Y. -/
def backdoorMid : Node := .Z

theorem backdoor_into_X : Parent backdoorMid .X := parent_Z_X
theorem backdoor_into_Y : Parent backdoorMid .Y := parent_Z_Y

def blocksChain (m : Node) (Zset : List Node) : Prop := m ∈ Zset

theorem Z_blocks_backdoor : blocksChain backdoorMid [.Z] :=
  List.Mem.head _

theorem empty_does_not_block_backdoor : ¬ blocksChain backdoorMid [] := by
  intro h
  cases h

def SatisfiesBackdoor (Zset : List Node) : Prop :=
  NoDescendantsOfTreatment .X Zset ∧ blocksChain backdoorMid Zset

theorem Z_satisfies_backdoor : SatisfiesBackdoor [.Z] :=
  ⟨adjust_Z_ok, Z_blocks_backdoor⟩

theorem empty_fails_backdoor : ¬ SatisfiesBackdoor [] := by
  intro h
  exact empty_does_not_block_backdoor h.2

theorem Y_fails_backdoor : ¬ SatisfiesBackdoor [.Y] := by
  intro h
  exact adjust_Y_forbidden h.1

theorem singleton_backdoor_iff (n : Node) :
    SatisfiesBackdoor [n] ↔ n = .Z := by
  constructor
  · intro h
    match n with
    | .Z => rfl
    | .X =>
        have : blocksChain .Z [.X] := h.2
        -- `head` would require Z = X; only `tail` remains and is empty.
        cases this with
        | tail _ th => cases th
    | .Y =>
        exact (adjust_Y_forbidden h.1).elim
  · intro hn
    cases hn
    exact Z_satisfies_backdoor

end PcsPccr.ConfounderInd
