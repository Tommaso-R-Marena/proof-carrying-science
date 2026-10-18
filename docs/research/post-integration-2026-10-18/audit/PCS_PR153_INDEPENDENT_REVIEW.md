# Independent qualification of PCS PR #153

Review scope: PR #153 at `b916eec1b9d0d5c02c9cc19b070f7a47df5e5d87`, relative to main `fabc704efdbda4c8822881366e4db3d3e31f066a`. This separate-agent review uses its own clean worktree and audit-only branch. It is not approval to merge, release, deploy, or activate a model. Production and integration source were read-only throughout this review.

The current remote is still OPEN/DRAFT at the reviewed head. Its proposed merge is `6b53ba032e83e6e0ca76a8266b51135970a5e016`. All 32 original remote PR heads still match the frozen ledger. All 32 coverage source commits match the ledger. The 1,992-file source gate passes independently. All 385 protected baseline formal/configuration files equal main bytes; all 38 V7 modules equal their captured PR #149 origin; all 53 authored HECK theorem statement texts equal the original statements. The HECK source diff changes only proof bodies and one explanatory comment. This review did not rerun large Lean builds or independently rebuild the native authority.

A HIGH receipt consistency regression was independently reproduced. It does not turn a rejected package into an accepted package, but blocks reliable serialized/signed receiving rejection evidence. Trust-sensitive promotion should remain blocked pending a separately reviewed repair. Narrow research receiver development can proceed on its isolated branch without treating this baseline as release-approved.

## Evidence executed independently

- `SOURCE_GATE.json`: 1,992 source identities, exact module discovery, executable-mode and scoped Lean admission checks pass.
- `PCS_PR153_FORMAL_SOURCE_AUDIT.json`: independent Git-blob comparisons, 385 baseline identities, 38 V7 identities and 53 HECK statement comparisons.
- `INTAKE_TARGETED_TESTS.xml` and `.log`: 16 existing intake, attestation, archive-boundary and intake-schema tests passed, zero skipped. Real receiver-owned compiled Lean ran; no affirmative verifier was mocked.
- `reproduce_intake_review.py`: independently constructed 14 signed input cases over both public ZIP and directory paths, 28 old/new comparisons. Old wrappers accepted 28, new wrappers accepted 8, with zero new-only accepts. All 20 new rejections failed the existing receipt writer. Full case results are in `INTAKE_DIFFERENTIAL.json`.
- `REMOTE_PR153_SNAPSHOT.json`: current GitHub check conclusions. The required public gate and its prerequisites succeeded. Policy-skipped inherited jobs are not counted as executed successes.

The reused native authority SHA256 is `3fd286e68299ad399b59078618045cdaedac3bd0d55305d074005ade16317b49`. Its relevant source is unchanged from main. This is an executable identity and previous build provenance observation, not independent executable attestation. OS, Python, compiler, binary storage and receiver-controlled authority selection remain trusted.

Reproduce from this checkout:

```sh
export PYTHONPATH=.
export PCS_LEAN_AUTHORITY_BIN=/absolute/receiver-owned/pcs-lean-authority
/workspace/.onboarding/pcs-integration-env/bin/python docs/research/post-integration-2026-10-18/audit/reproduce_intake_review.py
```

The script executes the exact old ZIP/directory wrapper source from the pinned main Git objects under distinct module names, against independently byte-checked unchanged precheck, byte contract, Lean enforcement, policy and receipt contract dependencies. It compares the same signed bytes and receiver settings, except that only the new pipeline supports intake-policy options. It uses synthetic fixture claims and generated producer keys; no production credentials or external scientific data are used.

## Finding matrix

| ID | Severity | Result | Promotion blocker |
|---|---|---|---|
| P120-RECEIPT-001 | HIGH | Genuine Lean acceptance plus intake veto yields contradictory receipt fields; negative receipt cannot be written | Yes, for release of the affected receiving path |
| PROVENANCE-ENUM-002 | LOW | 15 byte/mode-adapted entries retain `EXACT_SOURCE_COPY` disposition | No; repair metadata in a reviewable follow-up |
| TCB-003 | INFORMATIONAL | Existing host/runtime/refinement/independent-root and history limitations remain open | Production self-modification and unqualified scientific adoption remain blocked |

### P120-RECEIPT-001

Source revision: `b916eec1b9d0d5c02c9cc19b070f7a47df5e5d87`.

Paths: `pcs/intake_verify_v06.py`, especially the veto in `enforce_package_intake_lock_v06`; `pcs/lean_authority_v06.py` builds the preceding genuine Lean result and coverage; `pcs/receipt_contract_v06.py` equates `authoritative` with the Lean result; `pcs/verifier_io_v06.py` writes audited receipts. Both public receiving wrappers are affected.

Reproduction: construct the original honest synthetic intake-bound canonical package with actual Lean, then call either public wrapper with a different well-formed `expected_intake_semantic_hash`; finally call `write_verification_receipt_v06` on that returned result. The attached script also reproduces with missing required locks, malformed present locks, inconsistent claims, invalid hashes and undeclared lock fields.

Expected: receiving rejects, actual Lean ACCEPT remains truthfully recorded as a narrower subresult, and a consistent negative receipt can be written and signed. No field should imply final receiving authorization.

Actual: `valid=false`, `authoritative=false`, `accepted=false`, `failed_stage=intake_lock`, while `lean_authority.accepted=true`, `stages.lean_authority=true`, and `formal_coverage.package_authority=LEAN_AUTHORITATIVE_ACCEPT`. Receipt writing raises `V06VerifierIOError` with four contradictions: Lean accepted vs authoritative, Lean stage vs authoritative, coverage package authority, and evidence execution authority. All 20 intake-veto results in this corpus failed writing; all 8 accepted controls wrote successfully.

Impact: CLI `--receipt` cannot persist a rejection through its normal audited receipt path; consequently its receipt-signing path cannot authenticate that negative result. A caller bypassing the writer sees conflicting authority labels. The final acceptance Boolean stays false: no affirmative acceptance bypass was observed.

Suggested repair: explicitly distinguish the real mathematical Lean subverdict from final host-policy authorization in both receipt representation and receipt contract. Do not fabricate a Lean rejection, loosen canonical input checks, or remove contract checking. Add actual ZIP/directory receipt-write and CLI signing tests plus tampered-receipt controls. A separate repair agent owns the follow-up implementation, preserving PR #153 source unchanged.

### PROVENANCE-ENUM-002

Source revision: same head. Path: `docs/integration/2026-10-18/SOURCE_ADAPTATIONS.json`.

Reproduction: compare each record's source/integrated SHA and mode when `disposition == EXACT_SOURCE_COPY`. Fifteen of 19 adaptation records differ in bytes or mode while retaining that enum. Source/origin hashes themselves all check correctly, and reasons explicitly identify adaptations. The affected file list is in `PCS_PR153_TRUST_DELTA.json`.

Expected: the disposition enum unambiguously describes adaptation, exact relocation, or mode-only adaptation. Actual: a consumer considering only the enum can incorrectly infer exact identity.

Impact: provenance presentation/automation ambiguity, not forged source content or a kernel change. Suggested fix: correct the enum in a fresh metadata follow-up and require an invariant relating exact-copy labels to matching content/mode. Preserve historical original and integrated identities. Does not block narrow research.

## Acceptance-set assessment of #120

For both relevant public v0.6 wrappers, the old normal-return pipeline remains: load exact package bytes, unchanged Python precheck, unchanged real Lean authority enforcement, unchanged reviewer policy. The new intake operation is inserted after Lean and before reviewer policy. Its only assignments to authorization Booleans are false; otherwise it preserves existing values. The reviewer policy refuses to accept invalid packages. Therefore the inspected control flow provides a source-level argument that the new normal-return accepted set is a subset of the old relevant accepted set under the same receiver configuration. Exceptions fail closed. This is not a Lean theorem about Python semantics.

The bounded differential directly observes that relationship for matching optional/required/pinned locks, absent optional/required/pinned locks, wrong expected hash, substituted claim, malformed JSON, non-UTF8, wrong root type, duplicate keys, bad semantic hash and undeclared fields. Missing optional locks remain accepted. Present malformed locks reject in both wrappers.

The public directory and ZIP routes invoke the veto unconditionally. CLI receiving, local verification, bundle construction, pilot and scientific callers route through these wrappers. The standalone Python precheck remains separately callable but explicitly `authoritative=false`. Raw Lean API acceptance remains the unchanged narrower mathematical/transcript policy and does not establish the new host intake policy. Separate version-0.5 verification is not evidence of version-0.6 intake enforcement. No producer-controlled signed file chooses the receiving executable or suppresses the wrapper veto in these inspected routes. Requiring a lock or a pre-agreed inventory still requires the reviewer to select that policy; optional absence is an intentional compatibility route.

The signed exact-member inventory, canonical archive path and archive hash recheck are unchanged. The byte-binding guarantees remain conditional on host behavior, actual executable correctness and existing source-to-runtime assumptions. The 16 executed targeted tests include actual raw canonical-archive boundary checks.

## CI and skips

GitHub was independently queried after the original final qualification. `verified-public-integration` succeeds and its workflow's final aggregation explicitly rejects missing, skipped, cancelled or failed prerequisites. The legacy private/self-hosted policy lanes remain intentionally skipped; a skipped job is never reported here as an executed pass. The retained final skip reconciliation accounts for 1,925 hosted core passes, 51 skip records, and complementary mandatory lanes covering 37 Mathlib runtime nodes, 9 prover runtime nodes and 21 nodes represented by five module skip records: 1,992 distinct tests. This review inspected the reconciliation and workflow commands but did not independently rerun those heavy whole-repository suites or every hosted log. The 16 new targeted executions had zero skips.

## Residual obligations

- V8 remains blocked on complete authoritative external release input. No stale snapshot is imported.
- General serialized scientific input and Python-to-Lean refinement remain open at #153. Its five-theorem bridge requires the explicit semantic link; one matching fixture is not that refinement theorem.
- PGSI1, PGSC6 and PGSC7 objectives and epistemic calculi remain distinct. No rank label alone authorizes production.
- Receipt/journal ordering, authenticated history completeness, executable identity and independently controlled storage/execution have documented gaps. Hashes, Python object privacy and POSIX permissions do not create unconditional immutability.
- Mathematical conservation and exact rational synthetic trajectories do not establish physical validity or observed empirical improvement.
- Dataset provenance/licensing and external participant validation remain separate obligations.

This packet identifies a concrete receiving regression and supports isolated next-stage research. It does not self-approve PR #153, certify all imported scientific algorithms, or grant release readiness.

## Independent follow-up validation of the isolated repair

The separate repair candidate `8c1aa88ec82ef9bef5274c993a17461e0192f319` was independently tested without editing its worktree. Its delta is exactly the intake verifier, receipt contract, intake tests and one repair note. All 28 original real-Lean cases retain every acceptance decision, all 20 formerly unwritable negative receipts now serialize, and 176 additional tampered receipt controls reject. Actual Lean ACCEPT and mathematical replay coverage remain truthful subresults; final receiving rejection stays false. `REPAIR_INDEPENDENT_VALIDATION.json` records the exact commit and outcomes; `validate_receipt_repair.py` is the independent validator.

The original failing evidence and source assessment at b916 remain unchanged. This fixes the observed functional defect in the separate candidate, not PR #153 itself. Its inherited source profile still intentionally detects the changed pinned bytes. An explicit, independently reviewed successor identity mechanism is pending; no source gate is declared passed for that repair until the mechanism and its negative controls execute. This observation is not merge approval.
