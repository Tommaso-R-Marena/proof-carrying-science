/-!
# Example symbols: reproducible computational experiments (Semantic Intelligence v2 registry)

Uninterpreted placeholder declarations for the v2 reproducibility fixtures.  No fact about any
real experiment, dataset or digest is asserted.
-/

namespace PCS.Examples.Repro

/-- A computational run. -/
structure Run where
  id : Nat
  deriving Repr, DecidableEq, Inhabited

/-- A dataset partition. -/
structure Dataset where
  id : Nat
  deriving Repr, DecidableEq, Inhabited

/-- An output digest. -/
structure Digest where
  hex : String
  deriving Repr, DecidableEq, Inhabited

/-- Two runs use the same configuration (uninterpreted). -/
opaque sameConfig : Run → Run → Prop
/-- The output digest of a run (uninterpreted). -/
opaque outputDigest : Run → Digest
/-- Run `r` is evaluated on dataset `d` (uninterpreted). -/
opaque evaluatedOn : Run → Dataset → Prop
/-- Run `r` is trained on dataset `d` (uninterpreted). -/
opaque trainedOn : Run → Dataset → Prop

end PCS.Examples.Repro
