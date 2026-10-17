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

Full exhaustive kernel-campaign qualification is recorded separately below after
completion. Machine evidence preserves the frozen protocol, all generated concrete
proof modules, exact source inventory, theorem audits and positive/negative
classification. Partial qualification runs remain in the local provenance record;
they are not substituted for a completed campaign or counted as new experiments.

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
