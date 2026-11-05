import PCSCountermodel.Fixtures

/-!
# Axiom audit for the principal theorems

Every `#print axioms` below is part of the build; the expected output is recorded in
`PCSCountermodel/README.md`.
-/

open PCSCountermodel PCSCountermodel.Fixtures

-- Items 1–4: evaluation correctness
#print axioms evalBool_iff_holds
-- Item 5: witness acceptance
#print axioms checker_iff
-- Item 6: enumeration coverage, search soundness / minimality / exhaustiveness, limitation
#print axioms allWorlds_complete
#print axioms enumeration_covers
#print axioms searchAt_none_iff
#print axioms search_sound
#print axioms search_minimal
#print axioms search_none
#print axioms search_none_not_unbounded
-- Named-to-de-Bruijn bridge
#print axioms lower_sound
#print axioms lower_closed_sound
#print axioms lower_isSome_iff
#print axioms namedChecker_sound
#print axioms namedChecker_isSome_iff
-- Concrete positive reference counterexample
#print axioms implicationFlip_lowering
#print axioms implicationFlip_checker_accepts
#print axioms implicationFlip_counterexample
#print axioms implicationFlip_named_counterexample
#print axioms implicationFlip_search_size
#print axioms capture_search_size
