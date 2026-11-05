# Compositional disclosure: evidence and limits

## Supported finding

Truthful answers that each pass a stateless privacy check can jointly reconstruct
a protected record. In the four-bit domain with known total two, queries on bits
1,2,3 are each independently safe for bit zero but jointly identify the full world.
The shared exact disclosure ledger preserves an ambiguous protected bit under
any public-history-only adaptive planner. A separate finite closure proof limits
posterior majority to two thirds under a uniform six-world prior; it is tight.
This is a new PCS research capability implementing established inference-control
principles, not a claim of worldwide novelty, SOTA model safety or alignment.

## Mathematical evidence

34 new ordinary Lean 4.28.0 theorems passed fresh kernel/object checks. No new
axioms or production authority edits. Axiom closures are limited to the existing
Std assumptions `propext`, `Classical.choice`, and `Quot.sound`; some theorems
need none. Concrete request/reply captures receive independent ordinary
`by decide` certificates. Incorrect positive captures are rejected by real Lean.

`PCSDisclosure` (Ledger.lean):

- `actual_retained`
- `safe_all_cells`
- `step_preserves_ambiguity`
- `arbitrary_history_preserves_actual`
- `arbitrary_history_preserves_ambiguity`
- `ambiguity_has_two_witnesses`
- `cannot_determine_protected_bit`
- `denial_independent_of_actual`
- `accepted_answer_exact`
- `denied_changes_nothing`
- `step_candidate_exact`
- `same_output_same_posterior`
- `posterior_exact`
- `all_three_individually_safe`
- `stateless_composition_discloses`
- `ledger_blocks_composition`
- `initial_ambiguous`
- `malformed_refuses`
- `adaptive_retains_actual`
- `adaptive_preserves_ambiguity`
- `adaptive_posterior_exact`
- `adaptive_public_transcript_has_both_secrets`

`PCSDisclosureBounds` (bounds/Bounds.lean):

- `safe_iff_all_worlds`
- `unsafe_has_disclosing_world`
- `maximal_truthful_uniform_gate`
- `finite_class_closure`
- `every_class_bounded`
- `initial_in_classes`
- `closed_step`
- `closed_history`
- `no_transcript_majority_above_two_thirds`
- `two_thirds_is_attained`
- `adaptive_closed`
- `adaptive_majority_bound`

The maximal-permission theorem is restricted to deterministic truthful gates
with a world-independent answer/deny decision at a given public possibility set.
It does not compare randomized mechanisms, noisy answers, cryptographic protocols,
or arbitrary utility objectives. The generic transcript theorem includes public
query choices and denials; timing, private audit channels, termination and host
errors are outside it. Query planning must never receive private inputs.

## Exhaustive executable checks

- All 65,536 prior bitmaps: native decoding, validity and exact re-encoding for a
  constant query, including empty, one-sided and ambiguous sets.
- All 256 world/query pairs on the full sixteen-world domain against a separate
  Python set oracle.
- All 384 transitions across the seven states reachable from the six-world prior,
  checked against that oracle and ordinary kernel certificates in twelve batches.
- All 36 actual-world/query-order reconstruction attacks succeed against the
  stateless control and preserve ambiguity under the ledger.
- Strict parser/malformed frames, incorrect certificates, actual verifier
  failure, staged SQL substitution, stale generations, concurrent callers,
  missing storage, receipt/state/resource corruption and rollback are tested.
- Host-created independent namespaces are an explicit successful negative
  control: three independent ledgers allow reconstruction. Namespace enforcement
  is a trusted host obligation, not an immutable root. Unanchored restart refuses.

## Real-weight evaluation

Official Qwen3 0.6B and 1.7B Q8_0 GGUF weights were hash-checked against the
predecessor pins, sealed, mapped and executed locally using pinned llama.cpp
b11827 (`970b51ce7c9ba5fff0726c5e9994f1c2f0e4eedc`). No remote inference or training.
These are small open-weight models, not a demonstration on current global SOTA.
Synthetic data only; exact private world never enters a model prompt.

The original adaptive-planner campaign registered 96 requests before inference.
It failed to discover the attack: 0.6B added an invalid field to all 36 query
outputs; 1.7B requested the already-known total on all 36 query outputs. Both
guessed correctly in 3/6 worlds under each policy. There were no model/HTTP
errors. This contrast is vacuous for attack prevention and is retained in full.

After inspecting that negative result, a separately registered **cooperative
transport control** requested the 2,4,8 schedule with a strict JSON schema. Its
72 actual completions are not autonomous attack discovery or held-out evidence.
The 0.6B model deviated from the schedule; the report uses its actual queries.

| Model | Policy | Complete schedule followed | Accepted queries /18 | Episodes determining bit /6 | Remaining worlds |
|---|---|---:|---:|---:|---|
| 0.6B | Stateless | 0/6 | 18 | 2 | 2,1,2,2,1,2 |
| 0.6B | Shared ledger | 0/6 | 12 | 0 | 3,3,3,3,3,3 |
| 1.7B | Stateless | 6/6 | 18 | 6 | 1,1,1,1,1,1 |
| 1.7B | Shared ledger | 6/6 | 6 | 0 | 3,3,3,3,3,3 |

Both control policies receive the same public information initially; the model
never receives the policy name or actual world. The ledger returns at least one
informative truthful answer per episode. In total the stateless control determines
the protected bit in 8/12 episodes, the ledger in 0/12. This finite exhaustive-world
comparison carries no population significance, general attack-rate or learning
claim. Replaying a capture is independent verification, not new neural inference
or cryptographic authentication of the capture's origin. Captures contain private
inputs and are suitable only for synthetic data or privileged reviewers.

### Primary capture provenance

- Source commit: `790bf7ab92d59f6ebe298d1182af013161a83e0a`
- Registration UTC: `2026-10-23T03:30:04.676106+00:00`
- Registration SHA256: `47b17e35056aea958a5bcf65d439802f9e13fd2c38b9f349822be4c3c6103716`
- Capsule SHA256: `c708db2c4aef3c3efdeff9fb81df8153fccf9dde74ce267ca57dfd8bd6885ae1` (1533942 bytes).
- Actual completions: 96; completion tokens: 1116.

### Control capture provenance

- Source commit: `d8d7da7cf40269d33ea3f57508406ee41b4bc8ee`
- Registration UTC: `2026-10-23T03:36:43.568958+00:00`
- Registration SHA256: `8cd20f255dc4546d7e4f7fbb280b735fa7100b5f3760dd76b5b00ab1d1d1a0d4`
- Capsule SHA256: `283fe8ea328ebc1e104fc0753438d0c4dd541d4b8585cf9dcde267d3084ca892` (968760 bytes).
- Actual completions: 72; completion tokens: 504.

## Review and adoption boundary

All 6,431 predecessor blobs and modes at PR #177 head
`12dd713bd726fccf136f9bdaa71d50c5ad3f2a84` are preserved. New code stays under this
research module and its dedicated workflow. Production authority, Aristotle,
PGSI source and historical evidence are untouched. No merging or deployment is
authorized for this experimental phase.

The implementation uses fixed-source native Lean authority, exact byte receipts,
atomic SQLite state/effects, generation-aware updates and a retained live prefix
anchor. Host/compiler/library/runtime/storage correspondence is tested, not
proved. There is no independently administered verifier root, protected restart
credential, OS refinement or protection against an administrator replacing the
host and its memory. Additional private side information invalidates a too-broad
prior; this policy is not differential privacy or unconditional secrecy.

Reproduce using the README commands and inspect this stacked PR's exact-head
workflow artifacts for final test counts and fresh CI campaigns. The independent
review archive also preserves failed development attempts and the predecessor
preservation-test mismatch; no historical failures are overwritten.

The next meaningful milestone is a compositional policy over richer public
queries with an explicit auxiliary-information contract, machine-checked wire
refinement, and an independently administered persistent namespace/anchor. Then
test stronger models with a preregistered autonomous attack benchmark. Current
readiness is a reproducible, finite-domain research artifact with formal
conditional guarantees, not a production privacy or general AI-safety authority.
