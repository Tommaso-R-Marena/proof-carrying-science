# PCS research platform technical implementation report

This report distinguishes inspected historical capability, newly executed local checks, provider CI and live production evidence. It is an implementation record, not a claim that all 59 objectives or general scientific intelligence are complete. The authoritative task inventory is `PCS_59_WORKSTREAM_IMPLEMENTATION_LEDGER.json`; descriptive statuses never grant scientific acceptance.

## Starting source and preserved results

The refreshed default revisions at the start of this execution are core `e1067e406a1a1991497e7130e1f209239e5607cc`, website `1a351144cac080a990ab6f75fe8b57b476c3b08a`, and CertiForge `415a1de40eaeadc366ac2d824c05ee52bb2bd66e`. New work is developed as a source overlay on a separate feature branch. A local baseline that sees concurrent source edits is explicitly classified as overlay evidence; a detached local checkout freezes the starting source for genuine baseline reproduction.

Verified Memory v1's historical 16-task results remain intact: structural search without checked memory solved 3, structural search with memory solved 6, the development-selected learned model solved 5, and ordinary Lean Std tactics solved 10. The 14,773-parameter graph model and 32 sequential actor–critic episodes actually trained. They do not establish neural or RL superiority, general English-to-Lean understanding, novel mathematical discoveries, or autonomous scientific discovery. Historical checkpoints and SHA-256 seals are preserved.

## Integrated authority boundaries

PCS separates ordinary-language intent, typed claims, immutable proof goals, candidate search, Lean kernel evidence, empirical assumptions, package integrity, reviewer policy and scientific acceptance. The model may propose an interpretation, tactic, lemma or experiment; it may not decide whether its own output is certified. A mathematically valid Lean proof establishes its exact proposition under its explicit assumptions. It does not establish an unrestricted English interpretation or empirical biological adequacy.

The research platform extends the existing Claim IR, obligation graph, scientific evidence packages, external-validator contracts, proof-state environment, protected public proof transport, contributor accounts and research games. New workstream reports describe their executed changes and scope; an API alone is never counted as an instantiated capability.

## Source-bound qualification and provenance

`pcs/release_qualification_v1.py` executes five reviewed local recipes: the Python baseline, repository integrity, immutable Verified Memory evidence, immutable induction evidence, and the full Lean verification script. It records exact Git commit/tree, every tracked and nonignored source byte, executable flags, dependency manifests, actual installed package versions, commands, exit codes, timeouts, wall/CPU measurements and log hashes. Logs are written outside the checkout so evidence generation does not silently alter source identity. Optional explicitly selected related repositories receive the same exact-byte snapshot; the verifier never obtains filesystem roots from an untrusted record, and cross-repository compatibility remains independently unchecked.

Missing or failed required gates and source drift veto local qualification. Dirty source is clearly identified as a development snapshot rather than immutable commit evidence. The recipe runner accepts fixed identifiers; there is no arbitrary shell-command field. Timeouts terminate the process group on POSIX. This is a reviewed local code runner, not an isolation service for arbitrary submitted programs.

Qualification JSON is unsigned. Log checksums and caller-supplied success flags cannot prove execution. The verifier checks schema, source snapshot, command policy and logs; optional independent replay reruns all required recipes. Provider CI, migration readiness and deployment remain separate `not_independently_checked` / `not_observed` states. Deployment eligibility is always false in the local record: production release requires the existing protected provider gates and authorized deployment process.

`inventory_release_provenance.py` catalogs actual license/notice/rights files, dependency manifests, workflow action pins and research manifests by hash. It identifies mutable tagged actions and unresolved transitive, asset, contributor and institutional rights questions. It preserves the existing first-party licensing and owner publication authorization. The scanner neither determines legal clearance nor automatically grants distribution rights.

## Reproduction

Use the repository's pinned Lean 4.28 activation and the existing hash-locked Python dependencies:

```bash
source /workspace/.onboarding/activate.sh
source scripts/activate_lean_428.sh
python -m pytest -q tests/test_release_qualification_v1.py tests/test_release_provenance_inventory.py
python -m pcs.release_qualification_v1 run --output /tmp/pcs-release-qualification
python -m pcs.release_qualification_v1 verify /tmp/pcs-release-qualification/qualification.json --replay-output /tmp/pcs-release-independent-replay
python scripts/inventory_release_provenance.py --output /tmp/pcs-rights-inventory.json
```

The environment-specific activation path is optional outside Codex; install the checked-in pinned dependencies and toolchain instead. A complete qualification can be expensive because it intentionally includes the full Lean gate. A selected recipe smoke run leaves absent gates as explicit blockers. It cannot be presented as full qualification.

## Execution evidence and limitations

This draft is updated from actual workstream outputs after they complete. Twenty-one focused qualification/provenance tests passed, including source drift, omitted gates, forged success/deployment flags, malicious command fields, corrupted logs, symlinks, duplicate/nonfinite/oversized JSON and untrusted related-repository roots. An actual three-recipe smoke run passed integrity (0.12 seconds), historical memory seal and fresh replay (222.78 seconds), and historical induction seal and fresh replay (144.57 seconds). It correctly failed overall qualification because the full Python/Lean gates were omitted and concurrent source edits changed the snapshot. This negative gate result is preserved, not hidden. The technical inventory found six rights files, ten dependency manifests, 65 workflow action uses (all remote references were full commit pins), and 42 experiment manifests at the recorded development overlay; this is not transitive legal clearance. `pip check` reported no broken requirements.

Machine-readable baseline evidence is kept under `.onboarding/research-platform-baseline`, including the frozen source manifest, command logs, resource receipts and formal/Rust audit results. The report must not invent CI/deployment success while those gates are pending.

CPU measurement is child-process usage; Linux RSS is the cumulative child high-water mark, not additive per-gate memory. Windows may lack child CPU/RSS measurements. Cached Lean builds are labeled cached; they do not substitute for fresh theorem compilation where a new proof is claimed. Synthetic contributor/browser fixtures remain synthetic and do not establish human participation or game-to-model generalization.

Remaining substantive boundaries include Python/JavaScript conditional source refinement, full Rust interpreter correspondence, broad semantic grounding, independent external scientific review, representative external transfer, demonstrated RL improvement, real human contributor outcomes, operational signing-key custody and actual production disaster recovery. Neither local tests nor status pages discharge these obligations.

## Frozen-baseline reproduction and integrated workstreams

The detached starting revision ran its full Python suite: **1,409 passed and 10 failed in 1,267.26 seconds**. The ten failures were setup-specific: three owner-repository tests derive their identity from the checkout basename, and seven semantic-authority tests correctly reject a symlinked Lean binary cache. Renaming the detached checkout to `proof-carrying-science` and copying the cache into a real directory resolved all affected modules: **17 passed in 1.93 seconds**. Every tracked source hash remained unchanged and the exact compiled checker SHA remained `626bb01b37a62c47278ac651cc36ccc37aa3813b76b6bd72352423f82c6c1126`. This covers all 1,419 original outcomes across staggered runs; it is **not a fresh single full green run**. Original failure logs and the correction receipt are preserved in [the public baseline seal](evidence/platform-baseline-v1/ARTIFACT_SHA256.json).

The concurrent overlay run earlier had 1,418 passes and one constructor timeout under constrained shared CPU load. It is separate development evidence, not the frozen source baseline. A child-process simulation without optional Torch/NumPy collected 1,523 tests in 0.72 seconds, without modifying trusted repository modules. Final feature-revision full provider gates remain necessary.

New work includes a source-bound Mathlib premise interface and hybrid search experiments, exact graph extraction, bounded abstraction repair, promotion-policy controls, reusable scientific contracts and real signed package replay, a 33-check contributor/browser campaign, consented synthetic game-to-gradient updates and withdrawal quarantine, local populated D1 backup/recovery and migration-copy testing, 17 cryptographic recovery controls, source-bound Rust helper proofs and 1,618 real runtime comparisons at the archived CertiForge starting revision. A new checked Rust expression API enforces canonical input payloads before the top-level interpreter and retains the exact extracted low-level source; its protected rust-and-lean gate passed and PR #3 merged as `c71e8575db2800b015a9d444f8ed572490f3a871` with the identical tested tree. Individual reports preserve exact costs, failures and limitations. The synthetic biochemical numerical claim stays OPEN in PCS because it is outside the compiled authority's builtin set; a separate receiver validates the signed numerical sidecar. No model, signature or package presence overrides that boundary.

These changes are experimental local implementation until final protected commits and provider deployment are observed. The 59-task ledger retains unresolved broader acceptance obligations instead of treating code presence as completion.
