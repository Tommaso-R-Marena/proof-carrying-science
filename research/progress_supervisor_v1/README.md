# Checked safety and progress for finite tool workflows

An independently checked action shield can still admit safe idle loops or deny
every action. This research extension supplies **bounded safe completion against
every declared outcome**, or a checked losing-region witness that rules out every
finite worst-case completion bound. It uses established reachability-game and
ranking-certificate ideas; no literature novelty or general alignment is claimed.

This is an additions-only branch from protected core
`fabc704efdbda4c8822881366e4db3d3e31f066a`. Existing PCS authority, action-shield and
Aristotle/PGSI statements are unchanged. No production checker registration or
website deployment is included. All external-world premises remain explicit.

## Run it

Linux x86_64, Python 3.12, and the repository's exact Lean 4.28.0 toolchain:

```sh
source scripts/activate_lean_428.sh
python -m research.progress_supervisor_v1 demo /tmp/new-progress-demo
python -m research.progress_supervisor_v1 replay /tmp/new-progress-demo/capture.json /tmp/new-progress-replay
python -m pytest -q research/progress_supervisor_v1/test_progress.py research/progress_supervisor_v1/test_replay.py
```

Outputs must be fresh paths. Replay reconstructs the captured requests, builds a
fresh pinned supervisor, executes actual local SQL tools, compares every native
reply and receipt, and generates fresh ordinary-kernel proofs of the exact wire
replies and abstract path. Producer proof source and reported verdicts are never
executed or accepted as authority. No proof traces are used for model training. Resource exhaustion or unsupported
proof tools refuses formal support.

For another bounded finite model, use the existing action-shield model format:

```sh
# goals.json is a sorted list of safe goal IDs, such as [4].
python -m research.progress_supervisor_v1 synthesize model.json goals.json certificate.json
python -m research.progress_supervisor_v1 check model.json certificate.json /tmp/new-model-check
```

A valid certificate can prove that the initial state is **losing**. Exit 0 from
`check` means the region certificate was checked, not that the task is achievable;
inspect `analysis.initial_realizable`. The native supervisor refuses losing states.
The concrete broker exposes only its fixed preauthorized synthetic workflow; it
is not a generic executor for arbitrary model-provided tools.

## Exact formal guarantee

`Progress.lean` imports the unchanged `PCSActionShield` library and proves fifteen
named theorems. `Wire.lean` adds four; each generated concrete model adds three:

| Theorem | Scope |
| --- | --- |
| `PCSProgress.check_iff` | Finite check matches the declared region, rank, coverage and losing-witness criteria. |
| `winning_can_force` | Each winning state has a safe completion strategy within its certified rank. All declared successors are quantified. |
| `force_implies_winning` / `losing_no_finite_bound` | Any finite-horizon controller success implies membership in the checked region; outside it, no controller has a finite worst-case bound. |
| `choose_sound` / `choose_available` | Any proposed optional action is filtered or replaced by a progressing fallback; winning non-goal states always have a choice. |
| `chosen_step_progresses` | Every possible modeled successor is safe, remains winning and strictly lowers rank; forbidden actions are excluded. |
| `path_bound` / `completion_at_bound` | Every admitted path has length plus remaining rank at most initial rank; a path reaching that bound ends at a goal. |
| `preserves_existing_safety` | If initial states are winning, the original action-shield safety check follows without changing its specification. |
| `goals_halt` | No further action is selected at a goal. |
| `PCSProgressWire.selected_all_outcomes` / `halt_is_goal` | The typed native decision inherits progress/safety, and a halt is justified by a checked goal. |
| `malformed_refuses` | Undecodable requests produce the fixed malformed response. |

`force_succ`, `force_mono`, `pick_sound`, `pick_exists` and
`selected_from_choose` are the supporting named proofs. Generated
`PCSProgressData.certificate_checked`, `winning` and `losing` instantiate these
contracts with exact numeric literals. Recorded executions additionally receive
`Capture.actual` and `CapturedPath.path`, `bounded`, `completed` proofs.
All closures are audited exactly; no new axiom, `native_decide`, `sorry` or `admit`
is introduced. Current observed dependencies are subsets of `propext`, `Quot.sound`.

The synthesis algorithm constructs a least fixed-point attractor. The independent
certificate checker does not rerun synthesis: it checks every successor of every
admitted action, a decreasing rank, nonempty choices at every winning non-goal
state, and a spoiling successor for every non-forbidden enabled action outside
the winning region. Empty actions cannot satisfy the certificate vacuously.
Ranks are certified **upper bounds**, not a kernel proof of numeric optimality or
maximal permissiveness. The proposer computes minimum worst-case layers, separately
compared with exhaustive policy enumeration on small games.

## What changes for the AI proposer

A model proposes a bounded JSON action, not its own state, policy, verifier or
executable. The host holds state and generation. A denied/absent/malformed proposal
uses a separately preauthorized native fallback; no requested unsafe action is
executed. Thus repeatedly proposing idle or forbidden actions cannot stall the
modeled workflow. An oversized input is rejected without effects.

This does not force a model to answer, a scheduler to run, or a tool to terminate.
The bound counts **committed modeled tool transitions**, not elapsed time, failed
calls or crashes. Completion requires continued supervisor invocation, successful
tool execution with a declared outcome, accurate observations and enforcement with
no alternate effect entry point. These are explicit deployment obligations.

## Positive and negative scientific controls

The authored SQLite workflow reviews a preauthorized request, reads a synthetic
payload, replaces it with a fixed public summary, and publishes that summary.
Read has two declared outcomes: confidential content requiring sanitization, or
already-public content. The native supervisor completes these branches in four
and three transitions respectively. This is an actual SQL effect test with a
synthetic canary, not a human approval, a semantic sanitizer or deployed-agent study.

The model also includes safe idle loops, a safe trap, a forbidden bypass with a
safe target, and confidential sending with both a safe and an unsafe outcome.
The universal check blocks that send despite its safe branch. An all-deny shield
passes the old safety criterion but fails progress coverage.

Adding a review self-loop makes the initial state losing. A successful observed
review/read/sanitize/publish path still exists; the environment can instead keep
returning “not reviewed.” The certificate proves the absence of a **finite
worst-case bound** without inventing a fairness assumption. It does not rule out
successful runs, or almost-sure completion under an additional probabilistic model.
The original protected action-shield example can also be checked unchanged.

## Execution and evidence boundary

The authority compiles fixed first-party Lean sources and numeric-only model
literals, audits all 22 exact theorem names, runs pinned `leanchecker --fresh Main`
over the compiled import closure, and compiles the same decision to native code.
Every positive effect requires an actual native response. Linux memfd seals protect
the captured executable image against writes/growth/shrinkage; file replacement
and digest checks are tested. Sources, tools and built objects are checked around
every invocation. A submitted verifier name or forged response is not an API input.

The fixed broker qualifies one native image per trusted process and shares it
across fresh workflow ledgers. Reuse rechecks identities; no producer/on-disk cache
is adopted. This avoids repeatedly checking the identical Std import closure.
Independent replay uses a new process and builds its own image.

Effects, generation-aware updates and hash-chain receipts commit in one SQLite
transaction. The trusted host supplies fresh request IDs for new turns. Repeated IDs are
retries, do not advance progress, and are idempotent only for identical original bytes.
A live memory anchor detects prefix rollback, and replay checks materialized
payload/public rows. Existing ledgers are refused on construction: no unanchored
restart recovery or durable anti-rollback authority is claimed. Tests include
concurrent calls, actual SQL rollback and a real process exit immediately after
SQLite COMMIT. All side effects here are transactional SQL; arbitrary external
network/file/tool effects would require a different crash protocol.

The model/certificate codecs and Python/Lean correspondence are tested, not
universally source-extracted. The 6-byte wire codec is independently differentially
tested; its typed-decision theorems and concrete captured-packet proofs are not a
universal raw-byte decode/encode refinement theorem. Python, SQLite, compiler,
linker, Std/shared libraries, operating system and trusted observation/adapter code
remain outside the general kernel theorem. Hashes, Python privacy, file permissions
and a sealed image do not establish an independently administered immutable root.

No real neural-model evaluation, model gain, empirical AI-safety result, external
review, human study or world-first scientific claim is established by these tests.
The guarantee is model-conditional and policy-agnostic. Next milestones are a
separately proved concrete codec/adapter correspondence, explicit partial-observation
games, and controlled real-model experiments with independently validated tool models.
