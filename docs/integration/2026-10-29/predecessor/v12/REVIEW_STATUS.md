# Integration and new safety proof review status

This is an unpublished local candidate. Neither protected main, the research PRs nor the website has been merged or deployed in this phase. The protected heads are PCS `fabc704efdbda4c8822881366e4db3d3e31f066a`, website `89e512abd7830284227d820c0197d61cabedef6a`, Certiforge `c71e8575db2800b015a9d444f8ed572490f3a871`.

## Source integration

The candidate combines PCS PR #189 (`1e165ba06b4833a0e3fbcca2f654b581837acb68`) and #179 (`d0ab89c28347c52120c846d335049c5c100dd7fa`) without modifying their existing research theorem statements. It restores the exact historical #155 audit files, retains #129/#131/#133 PGSI1 work under its existing isolated source root, and preserves seven older #141 files in a historical archive outside the active formal namespace. Their preservation does not prove equivalence to the newer epistemic implementation.

`OPEN_PR_RECONCILIATION.json` inventories all 69 currently open PR heads and every changed source path. Forty-three have exact byte coverage at the original path or a documented isolation path. Twenty-five contain later source adaptations requiring semantic review; one (#117) remains under an explicit user hold. Byte equality, commit ancestry and archived sources are not interchangeable with tested semantic integration. No PR was closed as a substitute for that review.

The candidate includes paired CodeQL init/analyze updates from #170/#171 and setup-node pins from #169. The latest #164 transport diagnostic remains present. The old source-profile bytes and gate are preserved in `predecessor/`; the candidate gate authorizes only additional exact file hash pairs and continues to reject modified pinned bytes. Its review status remains pending independent review. The active configuration must match committed HEAD, so a WIP tree does not qualify as an admitted source profile. A disposable Git qualification fixture of the exact configured sources passes all 1,992 profile checks, 38 V7 module identities and two additional file checks. This fixture does not advance an implementation branch or supply scientific authority.

## New proof and executable capability

`research/token_policy_gate_v5` adds 16 general Lean theorems composing exact token/byte identity with the existing allowed-action and safe-progress policy. A fixed receiver proves all 42 recorded real-model token/byte/selection triples before running any SQL replay. The successful receiving run covers twelve model episodes and four separately labeled deterministic controls. It is a replay of PR #189 neural outputs, not new model inference. See the module README for precise hypotheses, native negative tests and trusted host assumptions.

## Engineering repairs

`formal/tools/LeanBuiltinCheck.lean` imports the six modules it actually uses instead of the entire PCS umbrella. Its driver body after the import block is byte-identical to protected main. Its deciders and theorem specifications are unchanged. A named exact-byte successor permits only this non-authority test driver to differ; arbitrary main formal overrides still fail. This lets the PKPD/semantic correspondence tests run without compiling unrelated golden SHA fixtures.

The transport trace checker retains its original kernel-reduction proof as the default. For the known rational-reduction error only, a fixed finite `fin_cases`/`norm_num` proof may prove the identical proposition under the unchanged overall deadline and axiom gate. The successful proof bytes, digest and original failed attempt remain separately identifiable. Generated proof sources are compared before accepting compiler responses. An actual Lean test injects only a negative first-attempt error and verifies the real alternative; no affirmative response is fabricated.

The exact old hosted transport proof still succeeds locally and fails on the previously recorded hosted runner. The alternative is locally verified; hosted confirmation and an explanation of the environment discrepancy remain outstanding. No authority is inferred from a Python-only result.

## Blocking conditions

- PR #117 has an explicit no-merge instruction. Preserve its formal research and do not promote experimental self-modification.
- PCS issues #9/#11/#13/#14 require actual key-custody/legal/external-partner/paid-pilot evidence. Site issue #2 requires owner domain/contact decisions. No completed evidence was supplied in this phase; these issues remain open.
- The initial umbrella builds failed with exit 137 while disposable test copies occupied memory-backed temporary storage. After retaining their results and removing those copies, the unchanged full `lake build PCS` completed all 161 jobs. The 24 prerequisite-skipped checks then passed on actual rerun. The raw build/recovery logs were lost in a later environment reset; the observed result and exact limitation are retained in `observed-recovered-checks.json`. Hosted qualification of the new branch remains pending.
- Earlier research CI preservation checks are scoped to their own frozen parent and additions-only paths. A combined candidate needs a reviewed successor qualification; those gates have not been bypassed or weakened to label the integration green.
- No final Aristotle V8 package matching the required source digest is available. No stale snapshot was imported.

The current user instruction conditions committing/pushing on complete integration and addressed issues. These blockers prevent claiming that condition is met. The local changes and evidence must remain reviewable and be preserved independently of ephemeral worktrees.

## Next milestone

First qualify a narrowly stacked token-policy gate on #189, preserving all existing tests and source bytes. Independently review the full integration successor contract, then run its complete hosted matrix, including the literal-transport portability case and the full Golden provenance build. Obtain real owner/partner evidence before closing the operational issues. Strengthen the next proof boundary around executable decoder/adapter correspondence; additional neural-model comparisons must remain empirical and separately labeled.

## Completed new policy-versioning result

The additive branch now has 37 new checked declarations, including a proof of an infinite locally certified controller rotation that never reaches its fixed goal. The carried-budget rule preserves safety and bounds admitted tool calls across controller versions. It rejects rank resets and locally certified goal changes and accepts a productive version change. Three additional kernel cases check rank inflation against the same contract used by the recorded Qwen laboratory. All 21 policy declarations passed a fresh kernel replay and six native decisions matched the kernel-proved cases. The separate token-policy execution suite has 28 passing tests and 42 model pairs checked before 16 receiving episodes. These are modeled-controller results and recorded-response replay; no new neural inference or production policy promotion occurred.
