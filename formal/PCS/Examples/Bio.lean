/-!
# Example symbols: residue annotations (Semantic Intelligence v2 registry)

Uninterpreted placeholder declarations for the v2 computational-biology fixtures.  No
biological fact (binding, sites, index validity) is asserted: every predicate is `opaque`.
-/

namespace PCS.Examples.Bio

/-- A residue of a sequence. -/
structure Residue where
  index : Nat
  deriving Repr, DecidableEq, Inhabited

/-- A sequence position. -/
structure Pos where
  index : Nat
  deriving Repr, DecidableEq, Inhabited

/-- The position of a residue (uninterpreted). -/
opaque posOf : Residue → Pos
/-- The residue is annotated as binding (uninterpreted). -/
opaque binding : Residue → Prop
/-- The position lies inside the annotated site (uninterpreted). -/
opaque inSite : Pos → Prop
/-- A legacy site annotation with a similar name and a different meaning (uninterpreted). -/
opaque inSiteLegacy : Pos → Prop
/-- The position is a valid index (uninterpreted). -/
opaque validIndex : Pos → Prop

end PCS.Examples.Bio
