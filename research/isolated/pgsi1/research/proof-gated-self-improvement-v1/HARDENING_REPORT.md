# PR #117 hardening and scientific qualification

This is a stacked research change based on PR #117 head
`db1cacf5c750ee108c9d946f5ee0839a53be25f6`. It does not change production PCS
authority, deploy a model, merge either research PR, or import new Aristotle
outputs. Every `formal/PCS/V2/ProofGated*.lean` file remains byte-identical.
The new `authority/Bridge.lean` is an IO adapter over those existing definitions,
not a new universal theorem or a proof of machine-code execution.

## Reproduced baseline

The unmodified head passed 76 Python tests, six Lean 4.28 module builds and all
31 specifically named theorem axiom audits. Actual file-based Lean authorization
performed two promotions and 201 sealed predictions. Exhaustive enumeration
reproduced 16,384 transitions, 4,081 finite-gate acceptances, 76 losses of a
previously correct integer input, 441 window-maximum regressions, and 12 overlaps.
The older out-of-corpus aggregate-error campaign also reproduced its 283 cases.

## Implementation and executed guarantees

| Layer | Implemented and tested | Boundary |
| --- | --- | --- |
| Formal mathematics | Existing finite-gate soundness, exact-text CAS/inference, bounded traces, two-unit examples, symbolic rewrites; 31 named axiom inventories | Frozen Lean specification; no Python/OS/compiler refinement proof |
| Canonical bytes | Strict PGSI1, both activations, all 8,450 bounded parameter configurations; native/Python model identity and 363,350 predictions | Exhaustive configuration tests, not a new all-input host-refinement theorem |
| Authority execution | Owner-built native executable pin; kernel write-sealed executable/input snapshots; Bubblewrap with separate user/PID/network namespaces, minimal read-only libraries and no host store/checkout mounts | Kernel, Bubblewrap, system libraries, compiler and owner configuration remain trusted |
| Service | Separate owner-launched process; bounded data-only protocol, no verifier/path/code fields; `SO_PEERCRED` plus retained pidfd; nondumpable server memory | Owner must supply the actual launched process identity. Same-UID filesystem/owner compromise remains possible |
| Promotion | One SQLite FULL/WAL transaction for blobs, receipt and HEAD; generation/hash CAS, request idempotency, full semantic receipt replay | SQLite/filesystem durability and trusted owner storage, not Lean theorems |
| Inference | Same validated byte snapshot decoded once; constructor checks artifact/head/model consistency; prediction never reopens a mutable model pathname | Python object freezing is consistency machinery, not an immutable security root |
| Independent receiving | Portable exact-byte history; fresh receiver-owned native checks and active-inference comparison; explicit external expected head | Unsigned producer history is not authenticated; copied-from-package checkpoints do not establish rollback protection |
| Universal analysis | Exact activation sweep and replayable whole-cell affine certificates, independent sign/coverage checker | Python-only; no Lean-certified universal authority or production promotion |

The sandbox qualification actually tested a hidden host-file canary, cleared
parent secret, inaccessible host loopback listener (with a successful host-side
positive control), distinct network namespace and unwritable executable.
Memfd write/truncate attempts failed in the kernel. An on-disk binary substitution
after loading did not change the verified executable snapshot; a fresh loader
rejected the altered pin. A substituted same-UID socket listener failed the
process-identity check, and the client could not open the nondumpable service's
process memory. These are conditional Linux observations, not universal security.

Real-authority tests include competing promotions, stale state, duplicate/rebound
request IDs, malformed artifacts/records, missing blobs, rehashed fake-positive
history, receipt mutation, crashes before COMMIT and after COMMIT before reply,
old acknowledgements after later promotions, and post-load database removal.
An interrupted transaction rolls back or is durably committed and idempotently
recoverable. No affirmative mock verdict validates these authorization tests.
Legacy v2 fake-oracle tests remain explicitly labelled storage fault tests.

A deliberate negative control restores an entire earlier valid database. Replay
alone accepts that internally consistent history. A separately retained later
checkpoint rejects the rollback. No external monotonic store or protected signing
credential was provisioned, and no stronger claim is made.

## Exact neural analysis and new negative findings

The producer now sweeps sorted activation events in `O(W log W + N W)` time for
`W` total units and `N` compared networks. The retained direct branch scanner and
bounded brute-force enumeration are independent comparison paths. At width
1,024, the local measurement was 1.98 ms for the sweep versus 159.72 ms for the
retained branch scan (about 80.6x); the independent certificate checker took
652.51 ms and remains quadratic. This is a single-host algorithm measurement,
not an end-to-end universal-verification speed claim.

Certificates bind the receiver's exact models/property/interval. The receiver
checks complete contiguous integer-line coverage, branch-sign inequalities on
each entire cell, affine coefficients, positive decisions or actual negative
witnesses, and attained interval maxima. It does not call the producer's cut,
sweep or affine methods. It also exposes whether previously correct inputs
exist, so a vacuous preservation result is visible.

The actual compiled Lean gate was independently compared with Python on all
16,384 old/new lattice pairs: **zero mismatches**. The analytic decisions also
matched independent enumeration on `[-64,64]` for this bounded lattice, and
window maxima matched a separate full scan. The stored exhaustive result is:

| Outcome among 4,081 finite-admissible transitions | Count |
| --- | ---: |
| Lost a previously correct integer prediction | 76 |
| Increased maximum error on `[-20,20]` | 441 |
| Failed both | 12 |
| Passed both stronger filters | 3,576 |
| Passed both filters but worsened aggregate held-out error | **46** |

All 46 last-row cases have **no previously correct integer input**, so universal
preservation is vacuous. A concrete supported PGSI1 example is
`PGSI1|L|-1|0 -> PGSI1|R|-3|-3`: the maximum error decreases `61 -> 57`, yet
aggregate error on `[-20,-4] ∪ [4,20]` increases `833 -> 986`.

There is also a **nonvacuous multi-unit reference** counterexample:
`old(x)=0`, `new(x)=ReLU(2x+1)+10*ReLU(x-21)`. It preserves the infinitely many
old-correct inputs `x <= -1`, attains zero benchmark/window error on `[-20,20]`,
but error on `22..32` increases `605 -> 660`; error at 32 increases `65 -> 110`.
This is NOT authorized by the current single-neuron PGSI1 gate. Its Python
certificates are independently replayable. Because the new model is already
perfect on the finite corpus, the required new-correct-case condition blocks
correcting its distant failure by switching to the exact target.

Thus three claims remain separate: **A**, finite-gate improvement; **B**,
modeled universal preservation (which can be vacuous); and **C**, genuinely
independent empirical improvement. These experiments establish neither C nor
accelerating recursive self-improvement.

## Proposal learning and evaluation

The frozen protocol splits 128 starting models into 64 training and 64 evaluation
states before training. Five mutation operators include joint edits and restarts;
a bounded Thompson-sampling proposal learner updates from finite-gate feedback.
Six strategies are compared against finite, universal, and universal-plus-window
policies. Held-out aggregate scores do not select proposals or train the policy.
However, the analytic policies know the mathematical target on all integers;
their evaluation is **not independent unseen scientific validation**.

Under the finite gate, uniform operators reached zero loss in 14/64 evaluation
rollouts; frozen learned proposals reached 15/64, shuffled-credit control 17/64,
and online adaptation 21/64. Under the strongest policy the corresponding counts
were 14, 15, 17 and 22. Frozen learning does not beat its negative control, and
one fixed synthetic test set does not demonstrate a reliable general advantage.
All proposal/rejection counts, later-generation gains, losses and timings are
retained in the machine reports.

A separately prespecified eight-seed live batch proposed real modifications from
zero: **four actual native-authorized transactional promotions across three runs**,
including one two-generation adaptive chain. **Five runs made no progress**.
The first pilot run also failed and remains in the earlier local record. No
successful seed or transition sequence was substituted for these failed runs.
Single-coordinate local dead ends with available larger accepted edits numbered
49, 50 and 55 under the three acceptance policies.

## Validation and reproducibility

The final local suite passed **119 tests, zero failures, zero skips** with the
native bundle mandatory. It includes the original 76 tests, 22 native/process/
transaction receiving tests, and 21 additional reference/search tests. There are
also 729 exhaustive ordered two-unit parameter cases, randomized branch-scan and
brute-force comparisons, large-integer/permutation/cancellation controls, and
corrupt-certificate tests. These are case counts within unit tests, not extra
unit-test totals.

Two complete executions reproduced semantic result digest
`dfd865fbecdc21b3ec22568f268ccda48b3933972c6a80ea441a18a482ca6a43`.
Timing and host/compiler pins are deliberately outside that semantic digest.
[evidence/hardening-v1](evidence/hardening-v1) retains the frozen protocol,
producer manifest, all 505 earlier stronger-guard violations, all 46 new
aggregate-error witnesses, all eight actual receiving histories, failed search
runs, learned policy and complete compressed proposal traces. `SHA256.json`
checks the original uncompressed bytes; the source checker binds 19 executed
research source files. The inventory is unsigned, not independent authentication.

The research workflow retains the original test/build/promotion job and adds a
mandatory native sandbox job. It rebuilds the pinned program, checks the frozen
formal sources and exact approved axiom set (`propext`, `Classical.choice`,
`Quot.sound`), runs the complete real suite, verifies retained evidence and repeats
the campaign. Missing namespaces or a missing authority fail the job; they do
not select a mock or an unisolated fallback. Native binaries are not uploaded;
small reports and logs use the existing public Actions artifact mechanism.

## Outstanding obligations and next milestone

1. Obtain Aristotle's **final exact** codec/architecture outputs with provenance;
   independently build/audit them and run the full differential matrix before
   changing the explicit source fence or any store policy/version. An older
   uploaded snapshot is not treated as the reported final migration.
2. Formalize the finite whole-cell certificate checker and relate its accepted
   certificates to universal model semantics in Lean. Keep the optimized producer
   untrusted; extend to deeper networks only with explicit semantics and budgets.
3. Establish a genuine independently administered authority/storage principal,
   authenticated build provenance and externally retained monotonic checkpoints.
   Prove/refine host serialization, native execution and transactional loading
   where feasible. Containers, hashes, permissions and object privacy alone do
   not discharge these obligations.
4. Freeze multi-domain capability/error budgets and prospective external tasks;
   evaluate proposal learning on genuinely unseen problems with independent
   reviewers and repeated negative controls. Allow no scientific/production
   claim merely from synthetic finite-benchmark improvement.

No untrusted Aristotle proof-generation traces were used for training. No
production authority, production model, website, Cloudflare resource or protected
main branch is modified by this stacked research work.
