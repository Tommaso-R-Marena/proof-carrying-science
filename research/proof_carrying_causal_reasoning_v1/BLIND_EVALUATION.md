# CLadder information sets and independent replay

We reproduced the original classifier at commit
`5eab9ef095dd88e17f0ea7e0a25f9a8f82798b95` before changing it. Its
10,112 matching labels came from an evaluator with access to generator slots
and ground truth. Changing only the hidden deterministic counterfactual bit
flipped its prediction on unchanged text. Its report reproduced byte-for-byte
(SHA-256 `d2742f190edc18b601065a6d44199aaad64fb8ec33f4ca0adca3dc8442b7fdce`).
The archived SOTA flag and point differences are superseded.

## What reaches each predictor

| Protocol | Public information | Rule and limits |
|---|---|---|
| A | The upstream-recommended background, given information and question, each an exact string | A restricted parser recognizes only binary marginal questions with explicit lexical complements. Both conditional rates must lie strictly on one side of 50%, which fixes the sign of their weighted average even after percent rounding. The parser abstains on all other forms. |
| B | A typed binary DAG, per-node rational CPTs, treatment and outcome, direction, assumptions and estimand | For Bernoulli ATE requests with `treated=true` and `result=true`, compute both truncated intervention laws. A yes answer needs a signed contrast of at least 1/200 in the requested direction. The public formal request is assembled using declared generator query slots. No text interpretation is asserted. |
| C | Generator slots, graph, CPTs and published targets | Historical correspondence test. Hidden targets selected 1,422 deterministic counterfactual bits, filled 948 missing effects and replaced 922 disagreeing computations. Another 1,580 decisions consumed adjustment slots or sets, 158 used collider slots, and 5,082 used computed effects with generator slots. |

The issuer uses the model ID only for joining the two source files. It reconstructs
the Protocol B graph and typed probabilities, checks parent names against edges,
and checks the topological order and complete table shapes. Only simple scalar
probabilities and nested binary tables enter the structured wire format.
The client receives no source row or raw metadata. IDs accompany records for
joining results and binding certificates. They never enter the text parser.
The predictor takes only its issued batch file. This dataflow property assumes
trusted local code and host isolation if an arbitrary replacement predictor is
used. A hash records the predictions before the scorer reads any labels. The
scorer separately reconstructs the public batch, checks its digest, and demands
an exact ordered cover of the source questions.

Each Protocol B certificate binds a claim ID and canonical public-input digest
to the rational expectations for do(X=0) and do(X=1), their difference and the
binary decision. The Python standard-library verifier independently enumerates
full outcome-positive worlds, omits the treatment factor, and requires
byte-for-byte equality with its expected certificate. The bound is eight binary
variables. Reversal of an edge, CPT substitution, modified intervention, missing
rows, extra fields, stale digests, duplicate certificate keys and noncanonical
numeric spellings cannot reuse a valid receipt. Authority comes from replay
against caller-chosen inputs. SHA-256 alone supplies neither source provenance
nor proof of prior timestamp. A valid ATE is conditional on the model having
correct exogenous independence, edges, mechanisms and intervention semantics.

## Frozen results

| Set | Correct | Incorrect | Abstained | Selective accuracy | Correct / all |
|---|---:|---:|---:|---:|---:|
| A, all exposed items | 423 | 2 | 9,687 | 99.53% | 4.18% |
| B, all exposed items | 1,422 | 0 | 8,690 | 100% | 14.06% |
| A, test partition | 337 | 1 | 7,727 | 99.70% | 4.18% |
| B, test partition | 1,152 | 0 | 6,913 | 100% | 14.28% |

The partition uses SHA-256 of the decimal model ID modulo 10. Residue 0 is
development, 1 is validation, and the others form test. The text rule was
written after inspecting development marginal templates. All three partitions
belong to a previously exposed corpus. After the initial structured run covered
906 requests, inspection of an unissued ATE showed upstream's second root-CPT
encoding (a one-element array). Supporting the documented scalar equivalent
increased coverage to 1,422. The test partition consequently measures replay
on exposed data. No score here estimates pristine holdout generalization.

Both A errors remain in the score. On question 21002 both conditional
probabilities (49%, 48%) were below 50%, but the published answer favored the
positive outcome. On 22290 both (76%, 54%) were above 50%, but the published
answer favored the negative outcome. Either mixture comparison disagrees with
its dataset label using the printed binary partition. No label was relabeled.
Wilson intervals in the reports describe binomial sampling under an iid
assumption. Shared models and language templates violate that assumption.

The new offline runs used zero model requests and zero API charges. A replay
on this host took about 2 s for A and 3 s for B, including projecting inputs
and scoring. These are single-host timings. Reports break down counts by rung,
query type, graph family and split. The compressed predictions preserve every
abstention and every Protocol B certificate. [Frozen reports and rows](qualification/blind_protocols/)

## Baseline audit and claim register

At the frozen head the documented script passed 56 unit tests, 36/36 authored
controls over 13 tasks, the oracle checks, and all 18 Lake jobs. The committed
source reconciliation passed over 8,349 files. Python was 3.12.14 and Lean
4.28.0. An older qualified-v5 result differed in witness ordering because
Python iterated unordered edges. The new path diagnostics traverse graph edges
and children in sorted order. Three distinct hash seeds reproduced result
digest `097703096af6d1f6088c17e97480f7e7e001d95f50d679ef616405bba9b48bbb`.
The old result remains available with its original digest.

| Claim | Status | Evidence and assumptions |
|---|---|---|
| Earlier CLadder pipeline beat natural-language SOTA under equivalent inputs | REFUTED | Direct hidden-bit intervention and the C source counts above exhibit a different information set. |
| Historical oracle match on the full balanced set | EXECUTABLY_VERIFIED | Byte-identical report at the frozen head, same archive, hidden fields available. |
| Historical ATE/ETT bridge agrees on scoped models | EMPIRICALLY_SUPPORTED | Replayed 5,520/5,520 model checks and 3,950/3,950 selected question checks at the original tolerances, excluding arrowhead models as specified. |
| Independent certificate verifier agrees with the exact structured producer | EXECUTABLY_VERIFIED | Every issued ATE replayed on this release. Both programs trust the declared causal model, Python and exact rational arithmetic. They share serialization and threshold semantics. |
| Identification follows from an arbitrary natural-language story | NOT_EVALUATED | Text rules cover a marginal template only. Historical battery checks use an authored identifiability flag. |
| Intervention consistency and sharp individual-benefit bounds for the formal response models | FORMALLY_PROVED | See [theorem signatures, exact scope and axiom audit](FINITE_RESPONSE.md). This gives no Lean refinement theorem for the JSON/Python implementation. |
| Production or release authority | NOT_EVALUATED | Isolated research implementation. Owner source admission, protected CI, independent machine and external reviewer qualification are separate. |

The previous battery tests known graph patterns and the numeric engine.
Its `true_identifiable` input and theorem-name fields cannot establish a general
graph identification result. A broader benchmark needs independently chosen
graphs and language, external labels, additional predeclared estimands, a
blinded semantic-parsing study and a lock on the test protocol before inspecting
new results. The exact checker is a small-model reference with exponential
worst-case time. The truncated factorization and finite enumeration are
standard methods. The contribution here is their auditable use with explicit
information boundaries and replayable numerical witnesses.

## Reproduction

Use the repository root. The pinned upstream revision is
`3d2d1169b4b939a09048a6a75956c8972a93cc38`. The upstream repository supplies
an MIT license. Its archive README specifies the three text fields. We retain
derived predictions and receipts and read the original questions from the verified
archive during replay. [CLadder release source](https://github.com/causalNLP/cladder/tree/3d2d1169b4b939a09048a6a75956c8972a93cc38)

```bash
git clone https://github.com/causalNLP/cladder /tmp/cladder-replay-src
git -C /tmp/cladder-replay-src show 3d2d1169b4b939a09048a6a75956c8972a93cc38:data/cladder-v1.zip > /tmp/cladder-replay.zip
python research/proof_carrying_causal_reasoning_v1/scripts/replay_blind_protocols.py /tmp/cladder-replay.zip
python -m unittest discover -s research/proof_carrying_causal_reasoning_v1/tests
```

The script requires archive SHA-256
`9fdae052b1ebe4ee6a19fdfb3e1eb88a381c7345df394cea524bcce97e2349b3`.
It prepares the public batch, starts a separate predictor, freezes and compares
its output bytes, then invokes the scorer and independent verifier as separate
commands. It also replays the historical generator correspondence metric.
For receipt-only replay, use `external/finite_replay.py` with the issued
B public file, decompressed B prediction file and the two digests in
`qualification/blind_protocols/B.report.json`. This verifier imports no PCS
solver, API client or dataset scorer.
