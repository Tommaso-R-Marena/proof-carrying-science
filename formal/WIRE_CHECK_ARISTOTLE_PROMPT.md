# Aristotle task — finite wire checker soundness

The production PCS decision and normalized-state soundness layer is already
machine-checked. This task should close only the small finite checker bridge in
ProofTasks/WireCheck.lean.

Target: prove every sorry in that file without changing the statement of
PCS.Wire.WellFormed, PCS.Wire.toDecisionInput, existing PCS.SerializedBridge
soundness theorems, or existing Assures semantics.

The central theorem is:

wireCheck w = true -> WellFormed w

The Boolean checker covers:
1. source claim ID equality;
2. exact evidence ID scope;
3. no duplicate evidence IDs;
4. exact context ID scope;
5. every evidence predicate commitment equals the claim commitment;
6. recomputed decideClaim equals the recorded decision.

Intended decomposition:
1. Prove decodedEvidence_unique_of_wire_ids_nodup by pulling decoded list members
   back through List.map, using no duplicate source IDs, then mapping equality
   forward through decodeEvidence.
2. Prove contextCovers_of_exact_context_scope from exact equality between mapped
   context IDs and claim assumption IDs.
3. Prove requiredEvidenceBound_of_commitments by pulling a required decoded
   evidence member back into the wire evidence list and using commitment equality
   plus decodePredicateCommitment.
4. Decompose the Boolean conjunction in wireCheck_sound and turn each successful
   Boolean check into its proposition, using the three lemmas above.

Requirements:
- Lean 4.28.0.
- No new axiom, sorry, admit, unsafe, implemented_by, extern, or native_decide.
- Do not weaken the full predicate commitment comparison.
- Run lake env lean ProofTasks/WireCheck.lean and then lake build.
- Return exact source changes and #print axioms for wireCheck_sound and the four
  wireCheck_*_sound corollaries.
- If a target is false, report the counterexample or missing precondition instead
  of changing it silently.
