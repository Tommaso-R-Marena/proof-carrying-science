# PCS generalization and learning evaluation

The new experimental hybrid solves seven of eight frozen typed final problems,
compared with five for ordinary Std tactics and four for either structural memory
or the selected historical learned checkpoint. Its five Std successes and two
structural-memory successes are attributed separately. No final problem was
uniquely solved by the neural fallback. This is evidence of a useful bounded
portfolio, not neural superiority, new mathematical discovery or general
scientific intelligence.

## Executable implementation

- `pcs.experimental.prover.hybrid`: three fixed Std whole-goal tactics followed
  by bounded structural-memory and frozen neural action search. The immutable
  typed theorem, resource budget, winning component and independently replayed
  proof remain explicit. Models cannot submit imports, arbitrary tactics or code.
- `pcs.experimental.prover.hybrid_cli`: controlled English through typed IR,
  round-trip statement checking, attributed search and deterministic statement
  explanation. Unsupported input and unresolved ambiguity stop before model or
  Lean execution. Feedback is unapproved and never automatically trains a model.
- `pcs.experimental.prover.mathlib_retrieval`: a bounded catalog extracted from
  actual elaborated theorem declarations in Mathlib, pinned to revision
  `8f9d9cff6bd728b17a24e163c9402775d9e6a365` and Lean 4.28.0. Fixed imports cover
  set functions, elementary groups and factorials. Lexical and structural ranking
  only propose actions; a fresh kernel process checks every successful theorem
  and another compiler independently reconstructs it. This is a local authored
  benchmark tool, not a public arbitrary-Lean endpoint.
- `pcs.experimental.prover.state_graph`: bounded expression sharing with exact
  universe-bearing constants, local metadata and occurrence-specific binder
  edges. Four actual Lean states round-trip losslessly. The new DAG is an
  experimental representation; the historical model still uses its original
  learned graph encoder. No new DAG-trained model is claimed.
- `pcs.experimental.prover.abstraction_repair_v2`: typed anti-unification,
  kernel-checked source statements, checked counterexample rejection and
  independent admission of successful generalized lemmas.
- `pcs.experimental.prover.promotion`: a fail-closed experimental review filter
  checks held-out membership, split leakage, budgets, checker/checkpoint/data
  bindings, independently verified success and cost limits. It never changes a
  registry or deploys a candidate. Digest presence alone is not an attestation of
  how training was performed.
- `pcs.experimental.prover.mathematical_evidence`: exact corpus/policy membership,
  immutable goals, recorded independent kernel evidence, raw-byte hashes and
  explicit incomplete status; deterministic audit sampling reads pre-resume rows
  as well as newly produced rows.
- `pcs.experimental.prover.evidence_storage`: lossless gzip evidence with exact
  original-byte and archive digests, bounded readers, transparent resume support
  and privately retained original bytes. Storage does not alter result values.

## Frozen protocol and exposure

`research/prospective-hybrid-v2/protocol.json` binds 24 authored tasks: four typed
utility, four typed selection, eight typed final, two Mathlib selection and six
Mathlib final. `checkpoint-transfer-protocol.json` separately freezes five
historical checkpoints against the same eight typed final tasks. The resulting
matrix contains 144 comparisons: 80 typed, 24 Mathlib and 40 checkpoint transfer.
No new training, checkpoint selection or model promotion uses these outcomes.

Tasks are public developer-authored problems, not private blind evaluation or an
independently authored external project. Their statements were frozen before
evaluation, but the mathematics is already available in Std/Mathlib. The
historical final benchmark is explicitly exposed. The structural-fingerprint
contamination audit finds one historical training overlap in the new selection
split (`selection-order-chain`); it finds no exact alpha-structure overlap in the
new final split. This is not a complete semantic near-duplicate analysis.

Preserved selection failures led to dependency-path, catalog-interface,
bounded-output, identifier and syntactic-head extraction repairs before Mathlib
final evaluation. The freeze, failed receipts/logs, successive exact source
manifests and source overlays remain in the experiment folder. Those interface
repairs do not make this a once-only blind test. No final outcome selected a new
policy.

Typed action search uses 48 expansions, depth 18 and beam four. The hybrid's
three fixed whole-goal attempts count against that expansion budget; its
remaining budget is split between structural and neural search. One whole-goal
tactic can do more internal deduction than one typed action, so expansion counts
are not an equal measure of deduction. Physical execution attempts and wall time
are reported in addition. Mathlib retrieval uses eight declarations, each tried
with a constrained apply and rewrite; its baseline tries three fixed whole-goal
tactics (`simp_all`, `omega`, `aesop`).

"Physical calls" here counts compiler and proof-state worker attempts recorded
by the execution ledger, including failed attempts. Metadata commands such as
Lean version/prefix queries, Python loading and file hashing are not checker
calls. They can affect the recorded wall time. Separate inference CPU time,
peak RSS and host-wide CPU consumption were not instrumented; this report does
not substitute invocation counts for complete computation accounting.

## Main typed results

| Policy | Utility / 4 | Selection / 4 | Final / 8 | Final physical calls | Final expansions | Final warm wall seconds |
|---|---:|---:|---:|---:|---:|---:|
| Grounded primitives without discovered memory | 1 | 2 | 2 | 185 | 173 | 22.35 |
| Structural ranking with selected memory | 2 | 2 | 4 | 179 | 163 | 31.40 |
| Frozen selected learned checkpoint with memory | 2 | 2 | 4 | 234 | 218 | 46.59 |
| Ordinary Std tactics | 3 | 3 | 5 | 19 | 14 | 26.01 |
| Attributed hybrid | 4 | 3 | 7 | 71 | 77 | 36.41 |

Raw evidence is under `research/prospective-hybrid-v2/results/`; logical JSON
names may be published as `.json.gz`. The four utility problems do not select a
new memory configuration. Existing v1 utility-selected memory is frozen.
`final-function-offset` remains unknown in every main policy. The two additional
hybrid final solves are predicate induction using structural memory, beyond the
five Std successes. The learned-only comparison has the same solve count as
structural memory and uses more physical calls on this tiny suite.

Final costs include successful proof checking and the recorded independent
replay. They exclude separately measured shared library construction and the
additional full-library audit sample. Shared construction is 19 physical calls
and 34.10 seconds for selected memory, 15 calls and 18.28 seconds for the grounded
primitive library, plus one Std setup call whose elapsed constructor time was
not separately recorded. All final main rows use pooled environments with
proof-state caches cleared per theorem/policy. Failed execution attempts are
included by the physical-call ledger.

Some earlier utility rows used cold construction and a legacy replay helper;
their cost fields explicitly exclude uninstrumented helper calls. They must not
be silently combined with warm final costs. Original incomplete constructor and
checkpoint runs were stopped or timed out during contention on the four-CPU
host. Partial results and logs remain preserved; no aggregate cost is invented
for incomplete runs. A fixed audited library is compiled once per environment,
its source/compiled artifact/receiver hashes are checked, and every success is
checked in a fresh compiler. Selected final samples additionally reconstruct
the complete library from typed source/actions.

## External Mathlib results

| Policy | Selection / 2 | Final / 6 | Final physical calls | Final wall seconds |
|---|---:|---:|---:|---:|
| Lexical retrieval | 1 | 2 | 96 | 300.06 |
| Structured-expression retrieval | 1 | 4 | 50 | 176.51 |
| Ordinary Mathlib tactic baseline | 1 | 3 | 27 | 81.63 |

Structural retrieval solves image composition, preimage union, surjective
composition and factorial positivity. It does not solve the injective-cancellation
context or group right-inverse task under this protocol. The standard baseline
solves the injective task, so neither system subsumes the other. Two selection
tasks include a solved injective-composition statement and unresolved group
double-inverse statement. All successful receipts bind the exact theorem,
Mathlib revision, imported artifacts, catalog, retrieval source and Lean version.
Per-row physical calls include failed attempts and two successful independent
compiler checks. Catalog extraction/setup costs were not separately archived;
the table does not claim total experiment compute.

## Generalized lemma experiment

`research/abstraction-repair-v2/` freezes two source pairs and two transfer tasks.
Anti-unification of two specialized cancellation statements proposes a quantified
shared-offset cancellation lemma. It survives independent kernel admission.
Generalizing two unrelated true arithmetic identities proposes a false identity;
an independently checked counterexample rejects it. Both outcomes are retained.

On the two transfer problems, the primitive baseline and generalized-lemma memory
each solve one, with the same recorded per-task calls (13 for the unknown task,
12 for the solved task). The admitted generalization therefore demonstrates
well-typed checked abstraction, but **does not demonstrate useful transfer gain**.
Discovery/baseline cost is 85 measured calls; memory construction records 15
completed calls; the recorded execution spans 363.39 seconds. Legacy independent
replay helper costs are explicitly excluded. No claim of novel mathematics,
optimal memory selection, submodularity or statistical superiority follows.

## Learning and checkpoint transfer

The existing v1 models contain 14,773 trainable parameters. The transfer protocol
evaluates untrained, supervised, bag ablation and two sequential actor–critic
generations for seed 17. Their original weights, training data and digests remain
unchanged. This continuation performs inference and verification only. Historical
sequential updates are not a new training run; a changed historical checkpoint
does not itself establish improved reasoning.

| Historical frozen checkpoint | Final / 8 |
|---|---:|
| Untrained graph, seed 17 | 4 |
| Supervised graph, seed 17 | 4 |
| Supervised bag ablation, seed 17 | 4 |
| Actor–critic generation 1, seed 17 | 4 |
| Actor–critic generation 2, seed 17 | 4 |

All five policies solve the same four final tasks. This is a negative result for
learned/graph/RL advantage on this transfer suite. The 40 exact rows are under
`checkpoint-transfer/`, and their summary is in `checkpoint-transfer-summary.json`.
Three initial untrained rows are preserved from the earlier cold run; the 37
resumed rows use pooled loading. The continuation separately records 18 memory
construction calls (35.74 seconds), 14 primitive-library construction calls
(19.28 seconds), and no new Std setup call because its probe was already built.
Those overheads and the mixed cold/warm initial rows must not be hidden in a
single inference-cost comparison.

`evidence-audit.json` confirms all 144 frozen comparisons, correct membership,
unchanged goals/checkpoints and independent kernel evidence on successful rows.
There are 78 verified policy/task rows (58 main and 20 checkpoint transfer),
including repeated proofs of the same mathematical problem, not 78 discoveries.
The earlier incomplete summary is retained in `history/initial-incomplete-summary.json`;
the current summary references the completed audit. Lossless publication archives
bind 299,790,646 original main-result bytes to 5,327,762 compressed bytes and
357,744,638 original transfer bytes to 6,261,980 compressed bytes.

## Actual post-evaluation demonstration and independent audits

The local hybrid CLI ran on a separately authored quartic-index predicate
problem: assuming `R(0)` and closure under successor, prove
`R(Nat.succ ((u * u) * (u * u)))` for every natural number `u`. Its exact
alpha-structure is absent from both the historical v1 corpus and the new frozen
corpus; it remains a familiar induction family, not independent mathematics.
`local-hybrid-demonstration-input.json` records this overlap check and CC0
provenance. `local-hybrid-demonstration.json` contains controlled interpretation,
typed statement, five actual proof actions, independent full replay, explanation
and unapproved feedback. Structural memory solved it after Std failed; the
neural fallback did not act on this successful request. No weights were updated.
Its cold wall time is 58.99 seconds, with 32 measured checker attempts excluding
the additional uninstrumented legacy full-library replay helper.

The main driver reconstructed the complete source/actions of three final library
samples in fresh independent environments (`selected-full-library-replays.json`).
The resume-inclusive auditor reconstructed those three again, selecting from all
saved final rows rather than only rows generated in its current invocation
(`resume-independent-replays.json`). An initial relative-cache-path failure in
the new auditor is retained in its failure log; resolving the path fixed the
interface without changing proof actions, tasks, policy or results. Future cache
files live under ignored `.lake` directories, not in published research evidence.

All 23 focused tests pass with `PCS_REQUIRE_PROVER=1`, including real Std kernel
replay, immutable-goal tampering, corpus/policy membership, missing replay,
unapproved axioms, unchanged transfer budgets/libraries, input ambiguity,
bounded archive reading and corrupted archive rejection. Exact output is in
`focused-validation.log`. Every published archive verifies against its original
raw-byte and compressed-byte manifest.

The original Mathlib source overlays, the ten-source main continuation overlay,
the eleven-source checkpoint continuation overlay and the current reproduction
overlay are separately retained. Post-evaluation changes add lossless storage,
resume membership/protocol validation, an absolute replay cache and accurate
library-import documentation. They do not alter frozen search allocation,
ranking, theorem statements, checkpoint weights or recorded outcomes. Current
reproduction source identities and complete experiment membership are sealed
under `release-reproduction-source-manifest.json` and `EVIDENCE_SHA256.json`.

## Reproduction

Use the pinned cloud activation script and CPU research extra. Keep one heavy
Lean/search process active on the available four-CPU host and set Torch/BLAS to
one thread. These commands resume exact saved rows without refitting:

```sh
source /workspace/.onboarding/activate.sh
OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 python -m pcs.experimental.prover.pooled_hybrid_evaluation research/prospective-hybrid-v2
OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 python -m pcs.experimental.prover.pooled_hybrid_evaluation research/prospective-hybrid-v2 --variants
python -m pcs.experimental.prover.mathematical_evidence research/prospective-hybrid-v2
python -m pcs.experimental.prover.mathematical_evidence research/prospective-hybrid-v2 --replay
python -m pcs.experimental.prover.hybrid_cli 'For all natural numbers n, (n + 0) equals n.' --output /tmp/pcs-hybrid-result.json
```

The Mathlib portion is reproducible with
`python -m pcs.experimental.prover.prospective_hybrid evaluate research/prospective-hybrid-v2 --kind mathlib`.
Completed abstraction generations reject overwrite attempts; rerun the source
with a new directory by invoking its `freeze` then `execute` commands.

## Directive coverage and remaining research

Tasks 18, 19, 23, 27, 28 and 58 have executable bounded components, adversarial
tests and reproducible comparisons. Task 18 covers a small real Mathlib catalog,
not general theorem-dependency retrieval. Task 19 is lossless representation work
with the historical graph/bag ablation, not new DAG training or kernel-derived
validity masks. Task 23 has a measured portfolio benefit on eight authored final
problems, with correct symbolic attribution. Task 27 is a review filter, not a
complete new deployed-model lifecycle. Tasks 28/58 have a frozen transfer suite,
not a large independent external-project benchmark or an intelligence breakthrough.

Tasks 20/21 show one admitted generalization and one rejected false proposal;
their useful-transfer completion conditions remain unmet. Task 22 measures the
frozen selected memory but does not find a new optimal memory subset. Task 24
tests existing real Nat induction on new predicate indices; function-offset and
stronger/list induction remain unresolved. Task 25 rejects a false generalization
with actual counterexample evidence but does not deliver general missing-premise
proof repair. Task 26 compares existing real sequential-RL checkpoints; no new
RL algorithm or improved held-out policy is claimed. All components remain
experimental, proposal-only and scientifically nonauthoritative. No paid compute
or financial information is used.
