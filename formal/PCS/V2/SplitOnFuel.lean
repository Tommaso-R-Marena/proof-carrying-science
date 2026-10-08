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
def splitOnAuxFuel : Nat â†’ String â†’ String â†’ Pos.Raw â†’ Pos.Raw â†’ Pos.Raw â†’ List String â†’
    Option (List String)
  | 0, _, _, _, _, _, _ => none
  | n+1, s, sep, b, i, j, r =>
    if i.atEnd s then
      some ((b.extract s i) :: r).reverse
    else
      if i.get s == j.get sep then
        if (j.next sep).atEnd sep then
$ÑPĞ€L@øã…ªì