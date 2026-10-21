# Portable transport proof construction V2

This isolated research library constructs proofs of the **unchanged**
`PCSReal.TransportTrace.check` predicate. It does not modify production PCS,
the qualified V2 authority, prior Lean statements, signed receipt schemas, or
the source-integrity fences. Its base is frozen PR163 head
`1e41f82f5511d368b7d7309d3fa5c68a1903203e`; PR165 targets that research branch.
No merge or deployment is authorized or performed.

## Observed defect and controlled diagnosis

PR164 preserved valid-data rejection of the exact generated proof SHA256
`4e580c9253cacb77b62e481279ecd246fbf389e32e1b2d6d444553e114e4050d`.
The ordinary `decide +kernel` error displayed an irreducible rational-expression
reduction failure. Lean4.28's `Lean/Elab/Tactic/ElabTerm.lean` catches the original
kernel exception and, when elaborator reduction is also blocked, displays that
less informative error instead.

`RawDecide.lean` submits the same `mkDecideProof` term through checked
`mkAuxLemma` without that diagnostic catch. It accepts only closed monomorphic
goals. It is proof-producing metaprogramming checked by Lean's kernel, not a
native evaluator, an added axiom, or a verifier assertion.

Hosted diagnostic run39562971777 at commit
`ff491901adbf3ae204169cfa4b71576b3e2d528b` established:

| Environment | Original/default | Raw/default | Raw8M heartbeats | Raw32768 depth |
| --- | --- | --- | --- | --- |
| Ubuntu22.04 job | kernel checked | kernel checked | kernel checked | kernel checked |
| Ubuntu24.04 job, observed Linux7.0.0-1017-azure | rejected | **kernel excessive memory consumption** | same memory failure | same memory failure |

Both jobs completed the diagnostic (including intentional depth32 refusals).
The Ubuntu24 artifact12329235110 contains the unmasked exceptions. Raising
heartbeats/recursion depth did not repair the memory failure. These observations
identify an actual resource refusal, not an invalid mathematical recurrence.
They do not establish that the Linux kernel version caused different memory use.
All invocations retain the original `-M2048`, `-j1`, `Elab.async=false` settings.
`-M2048` is Lean's memory accounting limit, not an OS RSS/container guarantee.

## Implemented proof construction

`replay.py` proves one scalar recurrence at a time, assembles each row and then
the finite row family with `Fin.cases` and `Certificate.rows_sound`. The initial
row-only construction repaired the original5-cell example but hosted run39564779991
found memory exhaustion inside a16-cell row. That failed qualification remains
retained; scalar decomposition is the subsequent repair, not a weakened gate.
The final `trace_checked` statement
and all existing derived rational/real trace claims remain identical. The kernel
checks every row proof and the composition. Resource exhaustion remains a refusal.

For false data, Python proposes the first initial-value, recurrence, or time-grid
fault in deterministic order. Lean independently proves the exact observed value,
expected value, signed residual, and their inequality, then derives rejection of
the entire old checker using one of these new generic theorems:

- `PCSPortableTransportV2.initial_fault_rejects`
- `PCSPortableTransportV2.recurrence_fault_rejects`
- `PCSPortableTransportV2.time_fault_rejects`

`PCSPortableTransportV2.rows_sound` composes positive row certificates. The exact
statements and explicit bounds are in `Certificate.lean`. All four are compiled
and axiom-audited during replay; only the pre-existing standard axiom set is
permitted. There are no new axioms, sorry/admit, native-decide, or unsafe shortcuts.
Failed Lean elaborations may print rejected placeholders; any nonzero exit or
incomplete/nonstandard audit inventory prevents a positive or negative verdict.

## Reproduction

Use the repository's Lean4.28.0 toolchain (commit
`7e01a1bf5c70fc6167d49c345d3bf80596e9a79b`), pinned Mathlib
`8f9d9cff6bd728b17a24e163c9402775d9e6a365`, Python3.12.14, and hash-pinned
build/dev requirements. From a reviewed checkout:

```sh
source scripts/activate_lean_428.sh
lake exe cache get
python -m pip install --require-hashes -r requirements-build.lock -r requirements-dev.lock
python -m pip install --no-deps --no-build-isolation -e .
python -m research.portable_transport_v2.campaign --out /new/campaign-directory
python -m pytest -q research/portable_transport_v2/test_replay.py
```

Generate and independently recheck a single package:

```sh
python -m research.portable_transport_v2.replay check examples/scientific_workflow_v3/contract.json examples/scientific_workflow_v3/trajectory.csv /new/evidence-directory
python -m research.portable_transport_v2.replay verify /new/evidence-directory
```

CLI exit0 means actual kernel-supported trace; exit10 means actual kernel-proved
falsification; exit20 means refused/unavailable material. Argument syntax errors
have argparse's separate exit2. Read the returned scoped status as well. Every
output keeps PCS authority and scientific acceptance false.

The reviewer captures bounded input/evidence bytes, checks an exact file inventory
and independently reviewed source copies, regenerates the proof, and executes
Lean again. It never uses stored result JSON as a verdict, imports executable
code from a submitted package, or follows caller-selected verifier commands.
Hashes detect corruption; authentic review/bootstrap requires a separate trusted
channel. Existing evidence directories are never overwritten.

## Scientific and security scope

The deterministic campaign contains12 actual Lean cases: the original5-cell,
16-step trace; three faults; independent edge-flux-generated2/4/8/16-cell traces;
64-step oscillation; a final-step oscillation fault; a16-cell scalar fault; and
a16-cell,16-step generated trace. This independently coded
flux oracle proposes data; mathematical truth still comes from checked proofs of
the unchanged matrix/trace semantics. The fixture problems are bounded exact
discrete rational models. This is no empirical validation, general transport
solver refinement, neural improvement, or new production authority.

Tests attack forged positive result JSON, swapped source/proof files with
self-consistent hashes, forged fault locations and residuals, suppressed fault
search, traversal inventories, malformed bytes, invalid budgets and overwrite.
Positive and negative proof tests execute real Lean; no positive verifier is mocked.

The independently launched Lean processes remain under the same host/operator.
Python parsing/rendering, imported objects, compiler/OS, storage and source-to-loaded
object correspondence remain trusted/tested boundaries. No independently administered
witness, immutable root or unconditional availability claim is established.

Formal libraries are freshly compiled from captured source for each replay, while
Mathlib objects come from the existing pinned dependency cache. No rebuild of all
Mathlib objects is claimed. Source bytes are checked before/after replay. Imported
source/object provenance beyond those checks remains an explicit obligation.

Local first qualification:22tests passed without skips;10/10 campaign cases passed.
The final CLI additions and final hosted head are qualified separately in PR165's
current description and retained evidence. Do not treat an earlier run as final-head
qualification. Early development failures (ambiguous `check`, missing `fin_cases`,
and dependent `Fin.elim0` construction) are retained in the local development
records; the mathematical specification was not changed to repair them.
