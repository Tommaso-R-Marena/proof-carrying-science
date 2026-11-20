# Observation adequacy and promotion replay

These two Lean 4.28.0 extensions import the research branches' existing episode type and six-class admission table. Their base is commit `5cd0fe136bef17b2b869e6df96697aae256c1fe6`.

## Observation

`ObservationAdequacy.channel1_iff_uniform` proves that an episode score factors through the executed tool trace exactly when it is constant on **every** set of episodes with the same trace. The original episode record permits a representative for any tool list by assigning it an empty proposal list and a clear output bit. `factor_iff_uniform` generalizes this argument to views with a supplied representative that reproduces each reachable observation. Both proofs have empty axiom closures.

Agreement on the published safe/unsafe pair does not establish global factorability. `tie_without_factor` supplies a detector that inspects the output bit only when the executed log is empty. It ties both four-step episodes and distinguishes two other episodes with the same empty log. The original two implications about the published pair are contrapositives.

The executable `monitor` takes a finite table of reachable episodes, a deterministic observation function, and independently supplied Boolean labels. `monitor_exact` proves that it issues a particular Boolean precisely when the observation is present and every compatible row has that label. It abstains on unseen and conflicting observations. This characterizes the largest set of observed fibers on which an observation-only monitor can soundly issue a verdict. `refinement_preserves_verdict` shows that adding telemetry preserves such a verdict on each observed episode, assuming the old view is a fixed projection of the richer one. The table must include the relevant episodes. Omitting a conflicting row can create false certainty outside the table.

Factorization through an observation is a standard mathematical construction. Information sets and indistinguishable states have long been used to reason about knowledge under partial observations. The contribution here is a checked specialization, a refutation of the pairwise converse on the actual branch type, and a finite monitor with explicit abstention. [Halpern and Moses, *Knowledge and Common Knowledge in a Distributed Environment*](https://doi.org/10.1145/79147.79161)

## Promotion

`PromotionReplay.verify` takes a receiver-supplied review and a current champion. It binds an offer to the review version, incumbent ID and generation. It computes both correctness counts over the same labeled cases. A run with any missing prediction has no score. The proposed mechanism must be admitted by the original table, have at least the incumbent's detect rank and strictly exceed its complete empirical score. Offers contain no score or class override.

`verify_exact` relates this executable check in both directions to the declarative `Licensed` relation. `replay_exact` extends the correspondence to arbitrary lists. A rejected edge invalidates the submitted lineage. `lineage_budget` shows that from an admitted seed scoring *n* on *N* fixed cases, each accepted history of length *k* ends at an admitted champion at generation *g + k* with score at least *n + k* and at most *N*. Therefore *k ≤ N − n*. `finite_improvement_boundary` constructs an accepted promotion that loses a previously correct held-out answer. The count also allows regressions on individual measured rows if enough other answers improve.

`CheckLineage.lean` calls the proved `replay` directly. Its first file is supplied by the receiver. The header gives the review and seed IDs. Each `case` assigns a Boolean label, each `class` assigns a mechanism class to a candidate ID, and `observed` rows bind measured Boolean predictions to a candidate and case. Its second file contains untrusted `offer review parent generation candidate` lines. See `lineage_fixture/` for an example. It rejects duplicate register entries, unknown measurement keys, an empty suite, and seeds without admission or complete measurements. IDs use canonical nonnegative decimals and Boolean fields use 0 or 1. This list-based CLI is intended for small local fixtures.

The receiver is responsible for authenticating candidate identities, ensuring version identifiers refer to an immutable review, assigning classes correctly, and sourcing labels and observations independently. The proof assumes a fixed review during replay. The CLI parser, filesystem and artifact custody are tested or assumed; the parser has no formal text-to-record refinement proof. A caller with control of both files can manufacture a favorable review. A retained mechanism inherits the formal class admission bit; accuracy on this fixed suite is the only empirical quantity bounded here. This separate reference checker supplies no certification of legacy Python evolution histories or production PCS operation.

## Reproduce

From the PR checkout, with the repository-pinned Lean binaries on PATH, choose a previously unused output directory and run

```sh
research/evolving_safety_gate_v1/formal/replay_formal.sh /tmp/new-pcs220-replay
```

The command rebuilds both imported modules, the two extensions, and the CLI. It verifies every new named theorem's axiom inventory, exercises a two-generation promotion and six rejection controls, then runs `leanchecker --fresh` on a fresh module importing both proofs. It saves source hashes, checker logs and the CLI verdict in the chosen output directory. The functional fixture must return `accepted champion=2 generation=2 correct=2/2`. The six controls exercise stale parent/generation, incomplete measurement, old review version, inadmissible mechanism, tied fitness, and contradictory duplicate records.

| Theorem family | Axiom closure |
| --- | --- |
| General observation factorization and episode specialization | Empty |
| Pairwise counterexample and finite observation examples | `propext` |
| Exact finite monitor and refinement | `propext`, `Quot.sound` |
| Score bound, missing evaluation, single-step and path correspondence, lineage budget | `propext`, `Quot.sound` |
| Held-out promotion counterexample | Empty |

Fresh checking uses a second process with the same pinned Lean kernel. The negative controls use synthetic Boolean outcomes. These results establish a formal reference protocol and functional conformance on the small CLI fixture.
