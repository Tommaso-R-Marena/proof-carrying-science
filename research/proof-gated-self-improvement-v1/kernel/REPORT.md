# Affine certificate kernel integration

This research change is based on PR #129 head
`782be9e1d1744a8c5b848f94aa569fa11efffe91`, on its own implementation branch.
It introduces an independently checkable mathematical capability: finite
certificates establish universal properties of scalar-input integer ReLU sums
without trusting the optimized Python analyzer. Nothing is merged or deployed.
All existing `formal/PCS/V2/ProofGated*.lean` modules and the parent runtime,
canonicalization, receipts, policy hash and production authority remain unchanged.

## New mathematical results

The isolated modules contain **37 audited theorem declarations**: 21 in
`IntegerAffine.lean`, two in `CertificateClaims.lean`, five in `PGSI1Bridge.lean`
and nine concrete controls in `Controls.lean`. The complete exact names and
namespaces are in [THEOREMS.json](THEOREMS.json) and [Audit.lean](Audit.lean).
The axiom closure is restricted to the same existing approved set:
`propext`, `Classical.choice`, `Quot.sound`.

The principal new theorems are:

| Theorem | Proved implication |
| --- | --- |
| `IntegerAffine.nonneg_sound` | Finite endpoint/sign checks establish nonnegativity on a whole integer cell, including unbounded tails |
| `IntegerAffine.form_sound` | Checked local affine coefficients exactly equal the mathematical network prediction on every integer in the cell |
| `IntegerAffine.coverFrom_sound` | Checked contiguous cells cover every integer |
| `IntegerAffine.acceptEqual_sound` | Accepted certificate implies equal predictions for all integer inputs |
| `IntegerAffine.acceptPreserves_sound` | Every previously correct integer prediction is preserved |
| `IntegerAffine.acceptMaximum_sound` | The stated interval maximum error bounds all interval inputs and is attained at the stated in-interval peak |
| `IntegerAffine.acceptNonvacuous_sound` | Universal preservation plus an actual old-correct input witness |
| `IntegerAffine.acceptNoCorrect_sound` | The incumbent has no correct integer input anywhere |
| `IntegerAffine.refutesEqual_sound`, `refutesPreserves_sound` | Evaluated negative witnesses refute the respective universal property |
| `IntegerAffine.checkClaim_sound`, `checkBatch_sound` | Every claim in an accepted finite batch has its stated meaning |
| `PGSI1Bridge.embed_predict` | Both existing PGSI1 neuron activations equal their new ReLU-basis embedding for **all integers** |
| `PGSI1Bridge.guardAccept_sound` | The original finite predicate, universal preservation, nonvacuity and exact nonincreasing window maxima hold together |
| `PGSI1Bridge.checkGuardCase_sound`, `checkGuardBatch_sound` | Concrete stronger-guard cases compose the proved conditions |

The generic mathematics covers arbitrary finite width and integer magnitudes.
There is no completeness claim for every possible producer representation; the
soundness theorem applies whenever the checker accepts. The data-only replay
interface imposes explicit operational limits documented in [README.md](README.md).

Concrete certificates use ordinary `by decide`; the resulting proof terms are
kernel-checked. The optimized producer's branch logic, root division and maximum
algorithm are not trusted as theorem assumptions. The checker separately verifies
branch signs, coefficients, complete coverage, implications, bounds and witnesses.
In particular, the preservation checker uses a proved unique-integer-root argument,
not an assumed agreement between Python and Lean floor-division conventions.

## Implemented executable path

`replay.py` consumes a bounded canonical request containing receiver-owned exact
models, property, interval and optional nonvacuity witness. The existing Python
certificate format remains unchanged. Typed numerical constructors produce a
concrete Lean module and a theorem about precisely those encoded mathematical
models. Unknown fields, float/bool parameters, code strings and forged claim
identities are rejected. Both source and compiled checker identities are checked
before and after execution. Ordinary host files and Python objects are not an
immutable trusted boundary.

`guard.py` additionally binds the mathematical PGSI1 bridge to the unchanged
finite predicate. Its optional native bundle invokes the actual pinned Lean
finite authority on the exact canonical old/new artifact bytes. **It never
promotes a model.** The existing transactional store still enforces its existing
finite policy; other store clients do not become subject to this offline guard.
Adopting it as a mandatory promotion policy requires separate versioned authority,
storage and integration review.

Review found and repaired a request-to-receipt race before publication: the first
implementation computed the receipt's request hash by reopening the input path
after the proof. Both CLIs now hash the original captured request bytes; proof
receipts also retain the expected generated proof hash and reject changes before
or after checking. A real subprocess test replaces each request file after parsing
but before proof completion. Each returned receipt still names the original bytes.
No fake affirmative verifier is used.

## Supported PGSI1 counterexample, independently verified

A separately constructed **posthoc mathematical counterexample** uses valid
PGSI1 parameters within the existing `[-32,32]` bounds:

- Incumbent: `PGSI1|R|31|4`, or `ReLU(31x+4)`.
- Candidate: `PGSI1|R|32|-29`, or `ReLU(32x-29)`.
- The existing real pinned native Lean authority returned `ACCEPT`.
- The new concrete kernel guard proves finite benchmark loss `186 -> 91`,
  universal preservation of every previously correct integer prediction,
  a genuine old-correct witness, and exact window maximum `583 -> 570` on
  `[-20,20]`. This is dry-run authorization; no model is promoted.
- At 34, absolute error increases **989 -> 990**. More strongly,
  `SupportedTailCounterexample.every_tail_input_worsens` proves deterioration
  at **every integer input `x >= 34`**, not just a sampled tail point.

For this tail the two errors are `29x+3` and `30x-30`, so the deterioration
increases by `x-33`. `concrete_errors` is axiom-free; the universal tail theorem
uses only `propext` and `Quot.sound`. These two separately audited declarations
bring the authored library/control/counterexample inventory to **39**. Concrete
batch instance theorems are additional and are counted separately as claims.

The exact request, source, kernel guard theorem, real native receipt, axiom audit
and hashes are in [results/supported-tail-v1](results/supported-tail-v1). The case
is outside the prespecified 128-model lattice and is **not** counted in its
frequencies. It establishes a logical counterexample, not a deployment-risk rate.

The example extends to a proved family. For each integer `k >= 18`, define
`old_k(x)=ReLU(kx+4)` and `new_k(x)=ReLU((k+1)x+2-k)`.
`SupportedCounterexampleFamily.every_tail_input_worsens` proves deterioration
for **every integer `x >= k+3`**. The mathematical theorem is unbounded in `k`;
only the 14 cases `18 <= k <= 31` are claimed to meet the existing PGSI1 bounds.
All 14 were individually accepted by the real native finite authority and jointly
kernel-checked against the stronger guard. Their old/new finite losses are
`6k` and `3k-2`; their window maxima are `20k-37` and `19(k-1)`. The maximum ties
at `k=18` and strictly decreases in the other 13 cases. Each nevertheless
worsens on an infinite tail. No model was promoted.

The family theorem adds one separately audited declaration: **40 authored
library/control/counterexample declarations in total**, plus generated concrete
instance proofs. Its exact sources, native receipts and guard proof are retained
in [results/supported-family-v1](results/supported-family-v1). These are posthoc
logical counterexamples, not extra samples in the frozen transition experiment.

## Negative result proved in the kernel

Let `target(x) = ReLU(2x+1)`, `old(x)=0`, and
`new(x)=ReLU(2x+1)+10*ReLU(x-21)`.

`far_preserves_all_integers` proves universal preservation. `far_correct_witness`
provides the nonvacuous witness `x=-1`. `far_perfect_window` checks an exact
maximum error of zero on `[-20,20]`. Nevertheless, `far_error_worsens` proves that
at input 32 the old absolute error is **65** and the new error is **110**.
These facts refer to the same explicitly encoded networks. The wider network
is not a valid single-neuron PGSI1 artifact and is not promoted.

Thus even nonvacuous universal correctness preservation and perfect protected
window accuracy do not imply pointwise error improvement outside that window.
This is a mathematical counterexample, not an estimate of deployment risk.

## Validation status

The unchanged parent suite passed **119 tests, zero failures/skips**, with its
actual native bundle required. The new receiver suite adds **29 tests** for real
kernel positives/negatives, exact-zero singleton cells, negative weights,
cancellation, large integer intervals, false verdicts and witnesses, cell gaps/
overlaps, wrong coefficients/maxima/peaks, vacuous preservation, real optional
native authorization, compiled checker substitution and actual request replacement.

The full frozen campaign passed **19,169 concrete mathematical claims in 155
standalone proof modules**. Each module's batch soundness theorem passed the
kernel and its own axiom audit. The complete proof-source archive is 258,190
bytes compressed; every generated module is retained, not only successful-looking
examples. Both full and curated inventories passed bounded hash/source checks
against all **35 executed critical source files**.

| Frozen experiment | Kernel-checked result |
| --- | ---: |
| Ordered transitions of the original 128-model lattice | 16,384 |
| Universal preservation positive decisions | 8,227 |
| Universal preservation negative decisions, with real witnesses | 8,157 |
| Starting models with a genuine correct-input witness | 77 |
| Starting models with no correct integer anywhere | 51 |
| Original finite-benchmark acceptances | 4,081 |
| Finite acceptances losing a previously correct integer | 76 |
| Finite acceptances worsening window maximum | 441 |
| Both kinds of regression | 12 |
| Passed the two earlier supplemental filters | 3,576 |
| Of those, preservation was vacuous | 2,835 |
| Composed nonvacuous stronger-guard acceptances | 741 |
| Ordered exhaustive two-unit parameter configurations | 729 |
| Seeded wider-network cases | 64 |

Every model has either a concrete correct witness or a kernel proof of the
absence of one; absence is not inferred solely from a finite search. The two-unit
cases include both equivalence under permutation and exact interval maxima.
Independent bounded enumeration agrees with the analytical decisions. That
bounded oracle is a compatibility check; the kernel soundness theorems establish
the universal mathematical statements.

Kernel replay of paired equivalence/maximum claims at widths 4, 8, 16, 32 and 64
used approximately **0.586, 0.737, 1.548, 3.702 and 11.578 seconds** on this local
host. These are observed replay costs, not universal performance bounds or
measurements of an AI's improvement rate.

The frozen semantic digest is
`f0936ed94a4e8bba66ba8fcd2b5b25a30b4fa73530a65299514795be88a23575`.
[results/v1](results/v1) retains the protocol, decisions, model classification,
complete compressed concrete proof sources, audits, local test record and hashes.
The Git bundle intentionally omits repetitive per-batch logs and compiled object
files; raw local and CI records retain their own full inventories. No earlier
record is overwritten. Partial qualification runs were stopped for source-gate
review and the repaired request-hash race; their passed artifacts and stop reasons
remain in the local provenance record. They are not counted as completed campaigns.

CI runs the unchanged parent research gates and a new isolated job requiring real
native authorization, all 29 receiving tests, both supported-tail proof checks,
the 14-case family and the complete exhaustive campaign. The semantic result must
match the retained result. No mock or unisolated fallback is allowed. The job has a
30-minute ceiling because it performs ordinary kernel reduction for all concrete
claims; an individual Lean invocation is still bounded to 120 seconds and 4 GiB.
Exact CI commit/run identities are recorded in the stacked PR after execution.

## Trust and scientific scope

| Boundary | Status |
| --- | --- |
| Encoded finite integer-network mathematical claims | Kernel-proved when the concrete checker theorem accepts |
| Existing mathematical PGSI1 neuron to new mathematical network | Proved for every integer, both activations |
| Python/JSON/PGSI1 byte decoding and runtime prediction correspondence | Tested, not a new implementation-refinement proof |
| Lean executable, kernel, imported standard library and host execution | Trusted owner/toolchain configuration; not independently protected credentials |
| Native finite authorization and sealed runtime | Existing parent mechanism retained; new offline guard does not replace its authority |
| Unsigned proof/log/hash provenance | Integrity information; no historical authentication or external monotonic root |
| Floating-point/deep-network/GPU behavior | Outside this specification |
| External empirical scientific validity | Not established by these synthetic modeled-target experiments |
| Adaptive or accelerating recursive improvement | No new evidence; parent negative controls remain unchanged |

The universal target is explicitly supplied mathematical data. Knowing its entire
function is not independent performance on unseen external scientific problems.
No untrusted Aristotle proof-generation trace is used as training data. Final
Aristotle codec/architecture outputs still require a separate source-provenance,
Lean-build, axiom-audit and full semantic-differential integration. No stale
snapshot or new trusted root is silently adopted.

## Next meaningful milestones

1. Prove and implement whole-domain **pointwise error dominance**, which is stronger
   than preserving previously correct predictions plus a bounded-window maximum.
   The proved far-domain counterexample specifies the gap it must close.
2. Review a versioned binding from concrete mathematical proof artifacts to the
   exact deployed PGSI1 bytes and mandatory runtime promotion policy, preserving
   existing historical receipts and independent replay.
3. Establish an independently administered verifier/storage principal and external
   monotonic checkpoints. Hashes, user permissions and process separation alone
   do not establish that principal.
4. Integrate only Aristotle's final reviewed artifacts, then evaluate prospective
   external tasks and proposal learning with independent held-out evidence and
   negative controls. These synthetic proofs do not demonstrate general AI safety.
