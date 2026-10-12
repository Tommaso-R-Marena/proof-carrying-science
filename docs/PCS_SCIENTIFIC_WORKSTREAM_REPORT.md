# Bounded scientific assurance workstream

This workstream delivers an executable scientific project intake, package and
independent replay, built on the existing PCS v0.6 authority. It does not add a
competing certificate authority or establish biological/clinical adequacy.

## Actual case and results

The authored CC0 case is a three-species, two-reaction synthetic biochemical
network: glucose cleavage into two lactate molecules, followed by an isomerization
between species with the same molecular formula. These are authored kinetics, not
an empirically validated metabolic pathway. A separate standard-library project
implements simultaneous Euler updates using a stoichiometric matrix and writes
13 rational concentration observations. It imports no PCS code.

The PCS adapter independently checks four source-derived primitive obligations
(two element balances and two rate-unit dimensions), the exact time grid,
nonnegative concentrations, agreement with the declared rational Euler method,
and elemental amount conservation within explicit absolute/relative tolerances.
All eight bounded predicates passed. The existing compiled Lean 4.28 authority
accepted the four builtin computational claims. The original numerical claim is
**OPEN** in the certificate, because these new Python numerical predicates are
outside the certified builtin set. The scientific receiver separately checked the
producer's external signature and reran the numerical predicates.

The frozen experiment [SUMMARY.json](../research/scientific-assurance-v1/SUMMARY.json)
and [protocol](../research/scientific-assurance-v1/PROTOCOL.json) record:

| Control | Actual outcome |
| --- | --- |
| Positive package, fresh receiver process | PCS package valid; eight bounded predicates PASS |
| Repeat package from identical inputs, key and declared timestamp | Byte-identical canonical ZIP |
| Deliberate mass leak in the last observation | Conservation and reference witnesses; original workflow BLOCKED |
| Valid producer signature over a false numerical report | Ordinary PCS package remains valid; scientific receiver rejects the false report |
| Changed closed-compartment assumption | Dependent obligations and aggregate INVALIDATED |
| Bounded investigation of mass leak | Original failure retained; separate regenerated table checked PASS; no automatic replacement |
| Clinical/unbounded English claim | OPEN with advisory typed suggestions |
| Synthetic reviewer revisions | Append-only digest chain; identity unauthenticated; no human review/training authority asserted |

The experiment used three fresh Python receiver processes. It took **21.188029 s**
wall time, **6.227729 s** self CPU and **4.359728 s** waited-child CPU. Recorded peak
RSS was 31,344 KiB for the parent and 38,576 KiB for children. The subprocess ledger
records 15 parent-observed Lean authority launches; it explicitly excludes the
nested authority launches within the three receiver processes. These are observed
resource costs for this small case, not a scalability claim. There were zero human
participants, zero independent human reviewers, and zero financial spend.

## Exact evidence

The immutable directory is [research/scientific-assurance-v1](../research/scientific-assurance-v1).
Its 16 public artifact members include the positive and honest-failure ZIPs, a
clearly labeled producer-signed false-report ZIP, independently generated receipts,
the original model/observations, dependency invalidation, investigation history,
review fixtures and a readable HTML receipt. Only the ephemeral **public** signing
key is exported; the temporary private key was deleted with its workspace.

| Artifact | SHA-256 |
| --- | --- |
| Frozen protocol | `75cfa3d866df7c139ec32afdc21748aaddfcf985de10adc994148d5541211deb` |
| Positive canonical ZIP | `73b5b6c2f98852f7181b31b7fe507a657ed30a7900f9412d4d39528efbc33f41` |
| Honest mass-leak ZIP | `22a279a03c71a7bf0e08e00c16a71109f270a180c0e13d7ad8f5c88fb25b17cf` |
| Artifact seal | `807c4911c1b00e3ff0598f23d51b315acb2cb437947783c048b93df26608e2b7` |
| Receiver-owned compiled Lean authority | `3fd286e68299ad399b59078618045cdaedac3bd0d55305d074005ade16317b49` |

Python was 3.12.14 on Linux x86_64. The exact executed source hashes are in the
frozen protocol. Source commit identity is the integrated release commit plus
these hashes; this report does not invent a commit for uncommitted implementation.
The demonstration producer fingerprint is
`5c1688ef48cdd60f06323727b9e3f6deda1ab5a84572625a7dda39ca0a104e7b`.
It is a published test identity, not a production signing key or independent
scientific review authority. A different regeneration key changes the signed
archive digest; independent replay of the exported archive needs no private key.

## Interfaces and authority

`pcs.scientific_contracts_v1` validates an explicit versioned mass-action contract,
derives existing builtin predicates, computes bounded rational Euler trajectories,
and returns exact counterexample witnesses. Supported inputs have 1–16 species,
1–32 reactions, 1–128 steps, mass-action order at most eight, flat molecular
formulas, rational/decimal **strings**, fixed `mol/L` and `s` units, explicit
assumptions, a declared CC0 license and rational tolerance definitions. Rational
numerators/denominators are bounded at 4,096 bits. Unsupported types, syntax,
scale conversions and missing premises remain OPEN; arithmetic exhaustion returns
RESOURCE_LIMIT with no passing evidence. Formula parsing follows the existing
PCS grammar; it does not validate real chemical species or mechanisms.

`pcs.scientific_obligations_v1` creates a versioned planning sidecar rather than
changing canonical Claim IR. Nodes retain dependencies, interpretation, evidence
IDs, provenance, assumptions and authority scope. Topological scheduling rejects
cycles and unknown prerequisites. Failed prerequisites block dependents; revised
node/premise definitions invalidate transitive cached results. The free-text
question is retained as original provenance, but is not certified as equivalent
to the typed contract. Aggregate satisfaction refers only to the explicit bounded
predicates. Biological adequacy remains an unresolved separate obligation.

`pcs.scientific_assurance_v1` exposes:

- `prepare_scientific_project`: static discovery, safe copied workspace, exact
  source inventory, a reviewable manifest and review document. Original source
  files are unchanged; source code is never executed during discovery.
- `build_scientific_bundle`: explicit caller confirmation, existing snapshot
  confirmation, existing attestation and canonical bundle creation, followed by
  a fresh numerical replay. No historical evidence is overwritten.
- `verify_scientific_bundle`: existing package/signature/compiled Lean verification
  first; exact local adapter-source binding, source-derived predicate and premise
  correspondence, existing external receipt validation and numerical replay next.
  Wrong keys, altered source, omitted artifact bindings and false reports fail.
- `render_scientific_receipt_html`: escaped, responsive inspection of a receipt.

An actual integration test found that the existing Python external-validator
replayer can verify signed external receipts, but the compiled Lean package
authority rejects external validator **check types**. That gate remains intact.
The numerical spec and receipt therefore live as signed artifact sidecars. Only
the existing builtin checks acquire PCS authority, and the numerical claim has no
certified evidence and remains OPEN. The additional receiver does not relabel a
signature or a Python computation as a kernel proof.

`pcs.scientific_research_v1` is a bounded deterministic investigator. It constructs
the dependency plan, retains failed checked attempts, identifies an admissible
separate regenerated Euler table, and checks that proposal against the immutable
original typed contract. It has no learned-policy advantage over its explicit
deterministic baseline, no permission to replace data or sign production evidence,
and no autonomous scientific-discovery claim.

Reviewer feedback is versioned, evidence-bound, append-only proposal metadata.
The existing authenticated reviewer policy remains the acceptance interface.
Fixture reviewer identifiers and independence claims are not verified human
identity; they cannot authorize training or change historical evidence.

## Validation and reproduction

Run with the repository's installed dependencies and receiver-owned compiled Lean
authority (`cd formal; lake build pcs-lean-authority` if needed):

```bash
python -m pytest tests/test_scientific_contracts_v1.py tests/test_scientific_assurance_v1.py -q
python scripts/run_scientific_assurance_v1.py --output /tmp/pcs-scientific-new-run
python scripts/replay_scientific_bundle_v1.py research/scientific-assurance-v1/positive.pcs.zip research/scientific-assurance-v1/producer-public.pem --expected-fingerprint 5c1688ef48cdd60f06323727b9e3f6deda1ab5a84572625a7dda39ca0a104e7b --output /tmp/pcs-positive-independent-replay.json
```

The 37 new focused tests passed, including actual signed package replays and
adversarial controls. Existing static workflow, environment and external-validator
regressions are included in the broader workstream validation; the final release
gate remains controlled by the integration agent. Heavy tests use real compiled
authority and require no Torch, GPU, remote model service or financial service.

## Directive coverage and remaining dependencies

| Task | Delivered scope | Remaining dependency |
| --- | --- | --- |
| 9 | Explicit unfamiliar authored Python workflow discovered, confirmed, attested and independently replayed | General scientific intent inference, arbitrary project execution isolation and public external-project evaluation |
| 10 | Typed scientific sidecars with finite quantifiers, units, assumptions, provenance and dependency invalidation; existing Claim IR preserved | Broader canonical mathematical/scientific IR extension and source-level formal refinement |
| 11 | Existing signed deterministic PCS package plus numerical receipts, source digests, obligations and readable report | New adapter kernel refinement and authenticated independent scientific review |
| 12 | OPEN unsupported diagnostics, missing evidence/premise/domain support and actionable suggestions | General semantic understanding; lexical advice is not certified meaning |
| 13 | Reaction balance, dimensions, rational parameter domains, reference/grid/nonnegativity and elemental conservation | Continuous ODE accuracy, floating-point implementation refinement and real scientific applicability |
| 14 | Versioned evidence-bound reviewer proposals; existing policy passthrough preserved | Authenticated independent reviewer participation and authorized feedback ingestion |
| 55 | Real finite multi-obligation investigation, counterexamples, preserved failure and separate checked repair proposal | General scientific planning, learned advantage and externally reviewed discovery |
| 56 | No new AI-safety adapter in this workstream | Existing AI-safety system and a separate properly scoped safety case |
| 57 | Reusable bounded biochemical contracts and substantive authored computational case | External scientific datasets and empirical biological validation |
| 59 | Existing PCS authority and numerical validator exchange exact signed contracts; receiver rejects invalid/mismatched evidence | Cross-component generalization to CertiForge/model services and formal correspondence proofs |

No statistical superiority, novel mathematical discovery, general English-to-
science capability, clinical assurance or Python-to-Lean refinement is claimed.
These are implementation and integrity results for a transparently scoped case.
