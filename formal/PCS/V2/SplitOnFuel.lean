import PCS.V2.Package

/-!
# A kernel-reducible form of `String.splitOn`

`String.splitOn` (core, `Init.Data.String.Legacy`) is defined by well-founded recursion
(`String.splitOnAux`), which Lean's kernel cannot unfold: `"a/b".splitOn "/" = ["a", "b"]`
is *not* provable by kernel reduction.  `PCS.V2.Package.segments` (member-name segmentation)
is defined via `splitOn`, so every concrete namespace check is blocked on it.

Here `splitOnAuxFuel` repeats the body of `splitOnAux` verbatim, structurally recursive on
a fuel argument and returning `none` if the fuel runs out.  `splitOnAuxFuel_sound` proves
(by induction on the fuel, using the unfolding equation of `splitOnAux`) that a `some`
result is exactly `splitOnAux`'s result.  `segmentsFuel` falls back to `segments` when the
fuel runs out, so `segments_eq_segmentsFuel` holds for every name and every fuel bound,
while for concrete names `segmentsFuel` is evaluated by the kernel.
-/

set_option autoImplicit false

namespace PCS.V2.SplitOnFuel

open String

/-- `String.splitOnAux` with explicit fuel; `none` iff the fuel ran out. -/
def splitOnAuxFuel : Nat → String → String → Pos.Raw → Pos.Raw → Pos.Raw → List String →
    Option (List String)
  | 0, _, _, _, _, _, _ => none
  | n+1, s, sep, b, i, j, r =>
    if i.atEnd s then
      some ((b.extract s i) :: r).reverse
    else
      if i.get s == j.get sep then
        if (j.next sep).atEnd sep then
          splitOnAuxFuel n s sep (i.next s) (i.next s) 0
            (b.extract s ((i.next s).unoffsetBy (j.next sep)) :: r)
        else
          splitOnAuxFuel n s sep b (i.next s) (j.next sep) r
      else
        splitOnAuxFuel n s sep b ((i.unoffsetBy j).next s) 0 r

theorem splitOnAuxFuel_sound :
    ∀ (n : Nat) (s sep : String) (b i j : Pos.Raw) (r l : List String),
      splitOnAuxFuel n s sep b i j r = some l → String.splitOnAux s sep b i j r = l
  | 0, _, _, _, _, _, _, _, h => by simp [splitOnAuxFuel] at h
  | n+1, s, sep, b, i, j, r, l, h => by
    rw [String.splitOnAux]
    simp only [splitOnAuxFuel] at h
    split
    · rename_i hat
      rw [if_pos hat] at h
      exact Option.some.inj h
    · rename_i hat
      rw [if_neg hat] at h
      split
      · rename_i hget
        rw [if_pos hget] at h
        dsimp only
        split
        · rename_i hj
          rw [if_pos hj] at h
          exact splitOnAuxFuel_sound n _ _ _ _ _ _ _ h
        · rename_i hj
          rw [if_neg hj] at h
          exact splitOnAuxFuel_sound n _ _ _ _ _ _ _ h
      · rename_i hget
        rw [if_neg hget] at h
        exact splitOnAuxFuel_sound n _ _ _ _ _ _ _ h

/-- `segments` evaluated with fuel `k`, falling back to `segments` itself. -/
def segmentsFuel (k : Nat) (name : String) : List String :=
  match splitOnAuxFuel k name "/" 0 0 0 [] with
  | some l => l
  | none => PCS.V2.Package.segments name

theorem segments_eq_segmentsFuel (k : Nat) :
    PCS.V2.Package.segments = segmentsFuel k := by
  funext name
  unfold segmentsFuel
  split
  · rename_i l h
    have := splitOnAuxFuel_sound k name "/" 0 0 0 [] l h
    simp only [PCS.V2.Package.segments, String.splitOn]
    rw [if_neg (by decide)]
    exact this
  · rfl

/-- The fuel bound used for concrete member names (names are at most 1024 bytes). -/
def segmentsFuelBound : Nat := 4096

end PCS.V2.SplitOnFuel
