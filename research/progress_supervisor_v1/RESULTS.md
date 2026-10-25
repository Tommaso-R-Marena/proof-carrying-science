# Executed qualification and limits

Implementation snapshot: `306a0246539395521de72f5122ddeeda58ca088f`.
The retained local package is `evidence/local-306a024/`; it contains exact inputs,
actual generated Lean declarations, native build/axiom/command records, captures,
fresh-process replay, and the unchanged original model's negative certificate.
Evidence files are observations, not a PCS scientific acceptance receipt.

- Existing action-shield/control baseline: **38 passed**, zero failures/skips.
- New core suite: **17 passed**, zero failures/skips, in 372.81 seconds.
- Fresh-process replay/effect-corruption/post-COMMIT-exit suite: **3 passed**,
  zero failures/skips, in 355.86 seconds.
- Additional post-publication hard-exit control: **1 passed** in 118.25 seconds.
  SQLite retained four committed transitions and exactly one public row; unanchored
  restart remained refused. This extends the original post-first-commit test.
- Exhaustive finite campaign: **8,160** two-state/two-action games, including all
  nonempty edge sets, nonempty safe sets, all safe goal subsets and forbidden-action
  subsets. The attractor ranks agree with a separate exhaustive memoryless-policy
  enumeration oracle. Every proposed certificate passes its independent criteria.
- Native boundary: **1,626** actual packet cases, covering all 256 values in every
  byte position and all declared state/action choices plus unknown IDs. Native
  replies agree with a separate Python wire/choice oracle. Short frames refuse.
  Twenty actual request/reply pairs receive an ordinary-kernel equality proof.
- Real false controls: all-deny, unsafe nondeterministic branch and false-rank
  certificates are rejected by actual Lean compilation. No mock positive verdict
  was used. Linux image writes/truncation fail; mutable-path replacement is detected.
- Actual synthetic SQL effects complete under forbidden, malformed and idle
  proposals. Confidential input follows four transitions; already-public input
  follows three. Native responses and actual observed paths are kernel replayed.
- Concurrent calls cannot duplicate committed tools; identical request IDs are
  idempotent, changed bytes with the same ID refuse, transaction failure rolls back
  effects, and a recomputed prefix is rejected by the live anchor.
- A real process exits immediately after SQLite COMMIT; the committed state and
  receipt survive. Construction refuses that existing ledger without an external
  restart anchor. This verifies refusal, not availability or power-loss durability.

## A supported negative research finding

The original protected `examples/action_shield_v1/model.json` is checked **without
changing its bytes**. Model SHA256:
`58ed24d8a71cec93b873276c8fe1359ea15ad5535e94054bc159049cef65f7cf`.
Its complete winning region for safe completion at goal 4 is `{1,2,3,4}`, with
ranks `{1:3,2:2,3:1,4:0}`. Initial state 0 is losing. The spoiling outcomes include
`(0,0,0)` (review may stall) and `(0,1,5)` (unauthorized loading).

All 22 generic/typed/concrete theorem closures and the complete imported objects
were checked with the pinned tools. `PCSProgressData.losing` instantiates the
proof that no safe controller can force completion from a losing state within
any finite bound. This does not claim that successful runs are impossible or
that a probabilistic fairness assumption could not support a different guarantee.

The original safety shield remains correct: it guarantees a different property.
No mathematical specification, historical evidence or production authority was
weakened to turn this negative result into success. The concrete positive SQL
adapter implements a separate preauthorized, bounded-review workflow, with a
separately identified transition model. Its correspondence to arbitrary external
tools is not established.

## What remains open

The universal mathematical theorems apply to the declared transition game.
Concrete Python/codec/SQL/source correspondence is tested, not generally extracted
into Lean. Model completeness, accurate observations, mediation without a bypass,
continued invocation, tool termination and transactional commitment are deployment
obligations. Crashes can stop availability; unanchored restart is intentionally
refused. The compiler, linker, Std/shared libraries, OS and trusted host code remain
trusted. A sealed image is not an immutable independently administered verifier.

No real neural-model experiment, benchmark gain, general AI alignment guarantee,
external scientific review or real-world safety validation was performed. The
advance is a reusable checked safe-progress/impossibility mechanism and a concrete
replayable implementation, using established reachability-game mathematics.
