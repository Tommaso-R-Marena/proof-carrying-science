# Summary of changes for run 34bc6452-b7bb-4147-b44f-5084e1d84178
`pcs-lean-authority` now fails closed. If any evidence item's `check_spec.type` is missing or unregistered, the verdict is `REJECT:unsupported_check_type`, in both `--zip` and directory mode. The transcript can no longer supply a replay outcome. A correctly signed archive is therefore not accepted just because its signatures verify. The full `lake build` succeeds (255 jobs), and the axiom audit, fixture tests and golden-file check all pass. Full details are in `PCS_FAIL_CLOSED_REPORT.md`.

**What the executable now does** (`PCS/V2/FailClosedGate.lean`, `PCS/V2/ExecutableAuthority.lean`)
- Replay outcomes come only from the six verified built-in checkers and the three registered domain checkers. Anything else falls back to a constant `FAIL`, never to the transcript.
- A new check-type gate runs before replay and covers *every* evidence item, including items no claim requires.
- I also found a second default-accept path while checking claim aggregation. A claim recorded as supported was accepted once its evidence replayed, even if that evidence certified different parameters. Now every supported AI-safety or biology claim must be backed by its own certified evidence through the checked obligation graph; otherwise the verdict is `REJECT:claim_binding`.
- Directory mode and ZIP mode go through the same decision path.

**Inputs that now fail** (all were `ACCEPT` before)

| fixture | new verdict |
|---|---|
| signed counterexample archive (type `trace_invariant_v2`, false claim) | `unsupported_check_type` |
| unknown type with a *safe* trace | `unsupported_check_type` |
| evidence with no type at all | `unsupported_check_type` |
| valid claim plus an extra unrequired `external_python` item | `unsupported_check_type` |
| claim budget 2 backed by evidence that certifies budget 4 | `claim_binding` |

The golden archive is still `ACCEPT`, the tampered one still `REJECT:package`, and the insider one still `REJECT:replay`.

**Backward-compatibility cost:** any archive that uses a check type outside the nine registered ones is now rejected, even if no claim depends on that item. A new type is supported only by registering a certified checker for it.

**Kernel-checked theorems about the actual decision functions** (`executableAuthority`, `executableAuthorityEntries`, `zipModeOutput`, `dirModeOutput`), for every input, transcript, key and fingerprint pin:
- **Rejection:** `*_rejects_unregistered_type` in four forms (zip, directory, and the two command-line wrappers), plus `*_rejects_false_supported_ai_claim`.
- **Concrete fixtures:** `cx_rejected`, `cx_entries_rejected`, `cx_cli_rejected`, `cx_signed_but_rejected`. The last one shows the archive is signature- and package-valid, was accepted by the old authority, and is rejected now. There are also rejection theorems for four campaign fixtures, valid for every signature pair (`m7`, `m7b`, `m7c`, `m15`).
- **Acceptance:** on `ACCEPT`, every evidence outcome comes from a certified checker (`executableAuthority_evidence_certified`). Every supported AI-safety or biology claim holds of the committed bytes, with no extra graph, `NoForgery` or transcript assumption (`executableAuthority_supported_claims_sound`). The verdict is the same whatever the fallback is (`acceptPCSStrictWith_fallback_irrelevant`).
- The golden-acceptance and refinement theorems were re-proved.

**Theorems removed or weakened:**
- `cx_accepts` and the old impossibility theorem were replaced by `legacyAuthority_cx` and `legacy_no_unconditional_claim_bridge`. These now describe only the old transcript-fallback authority, which is kept for analysis but no longer run by the binary.
- `executableAuthorityWith_nil` now goes in one direction only (strict `ACCEPT` implies old `ACCEPT`); the converse is false.
- `executableAuthorityEntriesWith_nil` was removed.

**Still not proved, or still trusted:**
- The compiler, runtime and file IO are trusted.
- The transcript is still used for the workflow and environment checks and for transcript binding; it no longer affects replay outcomes.
- Claims outside the AI-safety and biology domains (e.g. PK/PD, chemistry) only get the evidence-level guarantee.
- Statements about the deployed world still need the separate external-world hypotheses.
- The earlier generic theorems are unchanged and still proved.

**Checks run**
- `lake build`: success, 255 jobs.
- `lake env lean --run tools/WriteGeneralFixtures.lean` regenerates the fixtures. New ones are under `fixtures/failclosed_*/` and `fixtures/ai_safety_counterexample/package/`.
- `bash tools/run_fixture_tests.sh`: 14 of 14 expected verdicts, both modes. This tests the compiled binary; it is not a proof.
- `lake env lean --run tools/CheckGoldenFileLiterals.lean`: OK.
- Axiom audit (`PCS/V2/FailClosedAudit.lean`): only `propext`, `Classical.choice` and `Quot.sound`; no `sorryAx` and no `Lean.ofReduceBool`.
- Search for sorry/admit/axiom/unsafe/extern/implemented_by/native_decide: only comment text, plus a pre-existing function that happens to be named `admit`.

The state before the change is preserved at tag `checkpoint-before-failclosed-unregistered-tags` and branch `checkpoint/pre-failclosed`. I added "superseded in part" notes at the top of the two earlier executable reports, and everything is committed.

# Summary of changes for run 983406c7-faa6-489c-8eb9-a1dabce6244b
I proved a general theorem connecting the executable's actual decision to the bounded safety invariant, for every archive and transcript. It is necessarily conditional: I also proved, with a kernel-checked counterexample, that the unconditional version is false. `lake build` on the default targets succeeds (245 jobs). The only warning is the existing unused variable in `PCS/V2/SHA256.lean`. Every new result depends only on `propext`, `Classical.choice` and `Quot.sound`; `PCS/V2/ExecutableGeneralAudit.lean` prints this for 19 results on every build. The production sources contain no `sorry`, `admit` tactic, axioms, `unsafe`, `extern`, `implemented_by` or `native_decide`; the only search hits are prose about "unsafe traces" and an existing function named `admit`.

**Checkpoint.** The previous state is preserved as git tag `checkpoint-golden-results-before-generalization`. Since then the only change to an existing file is one import line in `PCS.lean`. The golden acceptance, committed-trace and deployed-run theorems are unchanged and still build. The binary still prints `ACCEPT` on the golden fixture in both modes, and the fixture-literal check still prints `OK`.

**What was missing.** `executableAuthority_domain_sound` already covered all archives, but only for claims accepted together with an obligation graph. The executable never takes or checks such a graph. What was needed was a statement about the executable's verdict alone, phrased in terms of the bytes it reads.

**General results** (`PCS/V2/ExecutableGeneral.lean`; no `NoForgery`, no transcript assumption):
- `executableAuthority_trace_evidence_sound`: if the verdict is `ACCEPT`, the raw bytes are a canonical ZIP. Every evidence item the signed certificate records as PASS, with the certified tag `trace_invariant` and parameters \((a,b,f)\), points to an archive member whose digest is bound by the certificate and whose bytes satisfy `TraceSafe · b f`.
- The same holds in directory mode and for the command-line function (`zipModeOutput_trace_evidence_sound`).
- `executableAuthority_registered_evidence_sound` is the domain-independent form, for any registered certified checker.
- `executableAuthority_trace_claim_sound` gives the claim-level form without a graph, provided each trace is covered by PASS evidence with the certified tag.
- `executableAuthority_deployed_trace_safe` carries this to a deployed run, but only under the explicit `FaithfulLog` premise.
- `executableAuthority_rejects_unsafe_trace_evidence` (zip and directory mode) is the contrapositive, stated using only parsing before acceptance. An archive whose certificate records a certified PASS over unsafe bytes is rejected for every transcript and every key.

**Negative results checked by the kernel:**
- `tamperedRaw_rejected`: the golden archive with only its trace swapped to one containing action 7, keeping the genuine signatures, is rejected for all transcripts and trust anchors. The binary prints `REJECT:package` on it.
- `insider_rejected_entries`: the consistently rebuilt and re-signed unsafe-trace archive is rejected for every possible signature, transcript and key. The original transcript-only authority accepts this archive. In zip mode it is proved for any bytes that decode to these members; that the concrete re-signed bytes decode to them is only checked by evaluation.

**Impossibility** (`PCS/V2/GoldenCx/Counterexample.lean`):
- `cx_accepts` proves, stage by stage in the kernel and including both Ed25519 checks, that the executable accepts a properly signed archive whose AI-safety claim is false of its committed trace. Its evidence uses the unregistered tag `trace_invariant_v2`, whose PASS comes from the transcript.
- `no_unconditional_claim_bridge` follows: "`ACCEPT` ⇒ every AI-safety claim predicate holds" is false.
- `cx_no_graph_accepted` shows the existing generic theorem correctly refuses: no obligation graph can domain-accept that false claim.
- `PCS/V2/ExecutableLimits.lean` adds that a certified tag cannot be overridden by the transcript. It also shows that a FAIL recorded honestly passes the replay stage, so `ACCEPT` without PASS implies nothing about safety.

**Trust boundaries:**
- *Proved:* the statements above, about the pure decision functions.
- *Trusted:* that the compiled binary computes those functions (compiler and runtime), the file-reading and printing part of `main`, and the transcript for evidence with uncertified tags (§2.4 shows that last trust cannot be removed).
- *Needs `FaithfulLog`:* every statement about a deployed run.
- *Needs `NoForgery`:* only attribution, i.e. who signed. Canonical decoding is proved, not assumed.

**Not covered:** a kernel proof that the concrete insider ZIP bytes decode to its members, and the order in which the filesystem lists directory members.

The full theorem inventory, statements, axiom audit and commands are in `PCS_EXECUTABLE_GENERAL_ASSURANCE_REPORT.md`; a pointer was added to the existing AI-safety report. Three cross-check fixtures can be regenerated with `tools/WriteGeneralFixtures.lean` (the binary prints REJECT, REJECT, ACCEPT on them); `*.zip` files are git-ignored. The properties table has 8 new proved entries.

## Suggested follow-up

Possible design issue, not a proof bug: evidence whose `check_spec.type` is not registered falls back to the transcript's reported outcome. As a result, `pcs-lean-authority` prints `ACCEPT` on a properly signed archive whose AI-safety claim is false (`GoldenCx.cx_accepts`). If unregistered tags should not be able to support claims, the executable could reject them outright, or refuse to count their PASS toward a claim's decision. I can make either change and re-prove the affected theorems if you want.

# Summary of changes for run 104c8573-7b7c-4577-a3fa-0e5599e17c91
I closed the gap left open last time. That the binary accepts the signed golden AI-safety archive is now a theorem checked by Lean's kernel, not just observed by running the binary. `lake build` on the default targets (`PCS`, `pcs-lean-authority`) succeeds (215 jobs, about 11 minutes from clean). The only warning is the existing unused variable in `PCS/V2/SHA256.lean`. The production sources contain no `sorry`, `admit` tactic, `axiom`, `unsafe`, `extern`, `implemented_by` or `native_decide`. Every new theorem depends only on `propext`, `Classical.choice` and `Quot.sound`; `PCS/V2/Golden/Audit.lean` prints this on every build.

**Repairs needed first.** The project as handed over did not build.
- `PCSAuthority.lean` used `PCS/V2/AuthorityCLI.lean`, but that module was never imported. I added the import to `PCS.lean`.
- Two files defined a lemma with the same name, so they could not both be imported. I renamed the copy in `PCS/V2/SHA256Fast.lean`.
- The half-finished files under `PCS/V2/Golden/` were not part of the build. They are now imported by `PCS.lean`, so they build by default.

**New results** (in `PCS/V2/Golden/`):
- **The binary's verdict is `ACCEPT`:** `aiSafetyGoldenArchive_accepts` proves that the exact function `pcs-lean-authority --zip` runs returns `ACCEPT` on the raw golden bytes. `aiSafetyGoldenArchive_entries_accepts` proves the same for directory mode.
- **The trace property, with no premise:** `aiSafetyGoldenArchive_committed_safe` concludes that the committed trace satisfies the bounded invariant: action 7 never occurs and cumulative risk stays at most 4 after every step. This follows from the acceptance through the existing soundness theorem; it is not checked separately. It needs neither `NoForgery` nor `FaithfulLog`.
- **The deployed-run version:** `aiSafetyGoldenArchive_deployed_safe` gives the same property for a deployed run, but still requires the explicit `FaithfulLog` premise.
- **The committed files themselves:**
  - `archiveBytes_eq_goldenRaw` proves the bytes of the committed `archive.zip` are exactly the canonical encoding of the golden entries, every CRC-32 included.
  - Further theorems show the committed transcript, public key and fingerprint decode to the expected inputs.
  - Together these give `pcsLeanAuthority_golden_zip_output` and `pcsLeanAuthority_golden_dir_output`: on those exact inputs, the function behind the command line returns `ACCEPT`.

**How it was made feasible.** Checking a whole stage in the kernel at once had taken more than 15 minutes. The proof instead checks each stage separately and replaces expensive steps with versions proved equal to the production code. This includes a new ZIP decoder completeness theorem (`decodeZip_encodeZip`) and faster SHA-256 and CRC-32 evaluation, each proved equal to the original. The two Ed25519 signatures are checked by running the production verifier in the kernel, which takes about 70 seconds.

**Still outside the kernel proof:**
- That the byte copies of the fixture files inside the Lean sources match the files on disk. `lake env lean --run tools/CheckGoldenFileLiterals.lean` compares them byte for byte and currently prints `OK`.
- The file-reading and printing part of `main`, and the Lean compiler that builds the binary.
- Directory mode only for members listed in canonical order; the order the filesystem returns them in is not modelled.
- The signing key is the public RFC 8032 test key, so no claim is made about who signed the archive. Nothing here is a claim of global AI safety.

The binary still prints `ACCEPT` on the fixture in both modes.

**Other changes:**
- Updated `PCS_AI_SAFETY_EXECUTABLE_ASSURANCE_REPORT.md` (§2, §8 and §9 rewritten, new files listed).
- Added a status note to `PCS_GENERIC_DOMAIN_SOUNDNESS_REPORT.md`.
- Updated the docstring in `AISafetyCampaign.lean`.
- Removed the leftover `Scratch/` directory of experiment files.
- Updated the properties table with the two new proved results.

# Summary of changes for run df6cdcee-e831-459d-a388-2202e892aa7f


## Suggested follow-up

I reached this run’s time limit. Send “continue” to pick up where I left off.

# Summary of changes for run 32246810-c407-4774-b274-073d135650d5
The real `pcs-lean-authority` binary now runs the certified domain-checker registry, including the AI-safety checker. A genuinely Ed25519-signed golden AI-safety archive is accepted by that binary end to end. One gap remains: that acceptance is shown by build-time evaluation and by running the binary, not by a kernel proof. `lake build` on the default targets (`PCS`, `pcs-lean-authority`) succeeds (175 jobs). All earlier generic-domain results are unchanged.

**1. Certified authority on the executable path.** `PCSAuthority.lean` now prints the verdict of `executableAuthority` (zip mode) and `executableAuthorityEntries` (directory mode), both in `PCS/V2/ExecutableAuthority.lean`. They run the existing certified extended authority with a fail-closed registry: the two biology checkers plus the AI-safety `trace_invariant` checker.
- `executableAuthority_refines_certifiedAuthority`: the binary prints `ACCEPT` exactly when the certified authority accepts. This is an iff rather than an equality because one returns a text stage and the other an optional result.
- Duplicate tags, or tags that shadow one of the six built-ins, reject every archive.
- An empty registry gives exactly the original production authority, and the six built-in checkers are unchanged.
- A checker cannot be registered without its soundness proof, because the proof is a field of the checker.
- `executableAuthority_sound` gives full assurance assuming the signing key cannot be forged (`NoForgery`). `executableAuthority_domain_sound` gives the AI-safety property with no cryptographic assumption.
- Unknown checker tags still fall back to the host transcript, so old packages keep verifying. Such a pass never counts as AI-safety or biology assurance, and an unknown tag without a reported pass is rejected.

**2. Golden signed archive.** The archive is in `fixtures/ai_safety_golden/` (7745 bytes, sha256 `741da649…`). It commits the trace `[0,1,2,4,1,8]` with forbidden action 7 and cumulative-risk budget 4.
- The signatures are real: a test-only signer in the project produced them, and the production verifier checks them.
- The signing key is the **published RFC 8032 test key**, so `NoForgery` is false for it. The golden theorems are stated without that assumption.
- The binary prints `ACCEPT` in both modes and rejects a corrupted byte.
- `aiSafetyGoldenArchive_domain_sound` and `aiSafetyGoldenArchive_deployed_safe` are proved, but each takes "the verdict is `ACCEPT`" as a premise. A kernel proof of that verdict was not feasible: kernel evaluation of the decoding stages on this archive took more than 15 minutes per stage before I aborted it, and `native_decide` is excluded.

**3. Adversarial campaign.** All the requested mutations are checked on every build, and each fails at the intended stage. One finding: an insider who re-signs a trace containing the forbidden action, or one that exceeds the risk budget, is **accepted by the original production authority** but rejected by the new executable. Kernel theorems explain the rejections.

**4. Distributed contributors.** `accepted_contributions_cannot_forge_assurance` (`PCS/V2/DistributedContributors.lean`) holds for any population, any strategy (adaptive, randomised, adversarial or colluding) and any interleaving. Its only premise is that the trusted validator is sound; nothing is assumed about contributors.
- It is proved from a store invariant, not as a wrapper around `root_assurance_sound`.
- Supporting facts are proved: an unverified leaf is rejected, accepted entries cannot be overwritten, collusion is no more than a joint submission list, and the accepted conclusion does not depend on ordering.
- `protocol_graph_accepted` shows an accepted store passes the existing graph checker.
- Limitation, proved: an adversary can block acceptance by claiming an id first. Ordering can change *whether* the root is accepted, never *what* it means.

**5. External-world bridge.** `ExternalWorldBridge` and `external_world_transfer_sound` (`PCS/V2/ExternalWorld.lean`) require an explicit correspondence premise; PCS never establishes it. In the AI-safety instance the premise is `FaithfulLog`. `committed_safe_deployed_unsafe` shows it cannot be dropped: a safe committed trace is compatible with an unsafe deployed run.

**6. Faster graph checker.** `checkGraphMemo_eq` (`PCS/V2/ClaimGraphMemo.lean`) proves the memoized checker equals the original on every input, so cycle, duplicate-id and missing-node rejection carry over. `checkGraph_iff` also proves the original checker complete, which closes an earlier open item. The speed-up is shown only by evaluating a graph with 2^40 paths; no complexity theorem was proved.

**Audit.** The production sources contain no `sorry`, `admit` tactic, `axiom`, `unsafe`, `extern`, `implemented_by` or `native_decide`. The only search hits are comments and a function named `admit` in the contributor protocol. `PCS/V2/ExecutableAudit.lean` prints axioms on every build, and every new major theorem depends only on `propext`, `Classical.choice` and `Quot.sound`.

None of this proves global AI safety: the result covers the declared bounded trace property of committed bytes, and reaches a deployed run only under the explicit faithfulness premise.

`PCS_AI_SAFETY_EXECUTABLE_ASSURANCE_REPORT.md` has the exact theorem statements, the campaign table, trusted components, open items and the commands to rebuild and rerun the fixture.

# Summary of changes for run 8c7bb79c-ade2-49b7-93c7-fa1411c9e4ca
All five theorems you asked for are now proved in Lean, along with three witness domains and a set of formal falsification attempts. One part of the desired statement needs an explicit qualification (below). `lake build` on both default targets (`PCS` and `pcs-lean-authority`) succeeds (157 jobs) with no new warnings. A search of all production sources finds no `sorry`, `admit`, `axiom`, `unsafe`, `extern`, `implemented_by` or `native_decide`. A new audit file prints axioms for all 56 new results: only `propext`, `Classical.choice` and `Quot.sound`. Apart from the new imports in `PCS.lean`, no existing file was changed, so `pcs_frontier_archive_acceptance_sound` is untouched. The full write-up is in `PCS_GENERIC_DOMAIN_SOUNDNESS_REPORT.md` at the root of the formal project.

**The qualification.** The pseudo-signature concludes `D.Holds c` with no world attached. That is not provable for claims about the external world (a real protein, a deployed policy): two worlds that agree on the committed artifacts get the same accepted archive. What is proved is `D.Holds (A.world r.table) c`, where `A.world` is the adapter's interpretation of the delivered, digest-bound, signed artifacts. Carrying a result over to the external world needs a separate, domain-specific data assumption, which is not assumed anywhere.

**The five theorems** (all in `PCS/V2/`):
1. **Domain adapter soundness** — `DomainAdapter.domain_adapter_sound`. You define a domain (claims, world, `Holds`) and an adapter (decode, compile, world, semantics, leaf and rule checks). The adapter must prove `AdapterSound`, a set of local obligations that never mention a particular claim's truth:
   - compilation reflects semantics;
   - accepted decomposition rules preserve semantics;
   - evidence that passed replay denotes its node.

   Given PCS acceptance and replay faithfulness, any obligation graph accepted for a signed claim then yields `Holds`, the claim's binding to the signed certificate, PCS `Assures`, and the graph's structural guarantees.
2. **Obligation-graph soundness** — `ClaimGraph.root_assurance_sound` works over arbitrary finite graphs with heterogeneous leaf kinds. `accepted_graph_facts` shows, with no soundness assumption, that acceptance rules out cycles, missing children, duplicate ids, unsupported nodes, undischarged leaves and a wrong root claim.
3. **Untrusted proposer** — `Proposer.untrusted_proposer_cannot_forge_assurance`. It holds for every proposer strategy, including adaptive and stochastic ones, with no assumption about the proposer. Any proposal accepted by the propose–check–repair loop is sound, and the proposed translation must equal the deterministic decoding of the signed claim.
4. **Workflow refinement** — `WorkflowRefinement.pipeline_refines` (and `pipeline_total`) covers pipelines of any length whose intermediate types differ. A small three-stage evaluator instance is included.
5. **End-to-end flagship**, in two forms:
   - `DomainAuthority.pcs_generic_domain_archive_acceptance_sound` runs on the **unchanged production authority**. It gives everything the existing frontier theorem gives, plus the domain proposition. The `…_builtin` variant needs only `NoForgery` and `AdapterSound`.
   - `…_with` and `…_certified` cover an authority extended with registered domain checkers. The existing six built-in checkers still run first, so their meaning is preserved, and an empty registry is provably identical to the production authority. The `…_certified` variant again needs only `NoForgery` and `AdapterSound`.

**Witness domains.** Each gets its assurance theorem as a one-line application of the generic flagship:
- **Computational biology:** every reported residue index lies within the committed sequence, and a deterministic score meets the declared threshold. Two new checkers, extended authority.
- **AI safety:** a bounded trace invariant — no forbidden action, and cumulative risk stays within budget after every transition. This is not a global safety claim. One new checker, extended authority.
- **ML evaluation:** train, validation and test tables are pairwise disjoint on a key, using the existing `csv_disjoint` checker. This one runs on the production authority with only `NoForgery`.

Concrete runs show each checker passing on good data and failing on bad data, and each honest graph being accepted.

**Falsification attempts** (`GenericCounterexamples.lean`):
- Rejected by evaluation: cycles, missing leaves, duplicate ids, unsupported nodes, a wrong root claim, swapped artifacts, failed or stale evidence, evidence belonging to another claim, a weaker leaf than the parent expects, and an adaptive adversary cycling through these attacks.
- Shown to be genuine premises, with a counter-model for each: unsound rules, unsound leaves, a checker that reports success without semantics (`AdapterSound` is then false), lossy compilation, and two domains registering the same check tag.

**What remains unproved or open:**
- I did not prove that every well-formed acyclic graph is accepted; this is shown only on the concrete examples.
- The graph checker re-checks shared sub-graphs, so it can take exponential time on heavily shared graphs. This affects speed, not soundness.
- The compiled `pcs-lean-authority` binary does not yet run the extended authority, so the biology and AI-safety theorems cover the extended authority, not the binary.
- No fully signed archive accepted end to end was constructed.
- The meaning of transcript-reported external validator results remains an explicit hypothesis where it is used.
- No theorem can certify that a decoded claim matches what a human intended in natural language.