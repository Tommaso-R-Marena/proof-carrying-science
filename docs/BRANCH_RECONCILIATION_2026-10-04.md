# PCS Branch Reconciliation Record — 2026-10-04

## Baseline

Authoritative baseline after the audit and repair:

```text
main = 2f5c9aa49f18ba3af03bbaf5590bae380d038de3
```

At that commit, CircleCI reported green status for the production formal gate, product-demo hardening, restoration regression, both Python architecture replays, both R architecture replays, and their aggregate completion gates.

This record is a dated reconciliation snapshot, not a permanent substitute for fresh branch inspection.

## Executive conclusion

No existing non-`main` branch is approved for wholesale merge into current `main`.

The apparent large divergences are primarily:

- squash-merged feature history;
- superseded stacked v0.6/formal work;
- old Aristotle handoff material;
- CI/runtime probes;
- branches that received diagnostic or follow-up commits after the original PR;
- archival development history.

If future review identifies a specific unique residual change, port that change onto a fresh branch from current `main`; do not merge the stale branch wholesale.

## 2026-10-04 formal-gate incident

The audit found that the Aristotle frontier integration commit:

```text
cec96c3b4a15a028a143b6ed00cb1b77a61dc69e
```

changed the Git mode of `scripts/verify_lean.sh` from `100755` to `100644` while preserving exactly the same blob bytes.

CircleCI invoked the script as:

```bash
./scripts/verify_lean.sh
```

so `formal-wire-lean` failed on subsequent `main` commits even though the Lean build and source audits themselves were healthy.

Independent diagnostic jobs established:

- `lake build PCS` — PASS;
- `lake build pcs-lean-authority` — PASS;
- default `lake build` in `formal/` — PASS;
- production source audit — PASS;
- exact direct script invocation with mode `100644` — FAIL;
- exact direct script invocation after restoring mode `100755` — PASS.

PR #52 restored executable metadata for both:

- `scripts/verify_lean.sh`;
- `scripts/verify_lean_real.sh`.

The repair changed zero source lines and no script bytes. Current `main` then returned to green `formal-wire-lean`.

## Recent proof-translation / product branches

These branches preserve development history for capabilities now represented on `main`, superseded by later work, or both. They are not wholesale merge candidates:

- `core/proof-translation-engine`
- `core/proof-obligation-graph-v1`
- `core/proof-repair-contract-v1`
- `core/proof-search-coordinator-v1`
- `core/recursive-claim-ir-v1`
- `core/decompose-claim-search-action-v1`
- `core/decomposition-proposer-protocol-v1`
- `core/bounded-artifact-inspection-v1`
- `core/formal-coverage-receipt`
- `core/receipt-attestation-auditor`
- `core/signed-external-validator-receipts-v1`
- `core/pkpd-peak-threshold-checker-v1`
- `product/pkpd-realistic-translation-benchmark-v1`

Current `main` contains the integrated Grounded Proof Translation Engine path, structured proof obligations/search/repair, recursive Claim IR and decomposition, bounded artifact inspection, validator receipt binding, and PK/PD translation/checking work.

### Corpus branches

`core/proof-search-corpus-v1` is an earlier corpus implementation and was superseded by the later consent-aware corpus work.

`core/proof-search-corpus-v2` carried the implementation merged through PR #50. It later received a diagnostic-only CircleCI commit used to isolate corpus test failures; PR #51 was closed without merge because that diagnostic configuration was not product functionality.

Do not merge either corpus branch wholesale. New corpus work must start from current `main`.

## Product / release history

These branches are historical and must not be merged wholesale:

- `product/p0-p1-demo-hardening`
- `product/verifier-artifact-validation`
- `release/main-wiring`

The P0/P1 branch received post-merge launcher/CI commits, but their functionality is already present on current `main` in evolved form, including standalone verifier construction, mandatory Lean authority, smoke testing, and artifact publication.

## v0.6 / formal stacked history

The following branches are archival or superseded stacked development. Their large ahead/diverged counts are not evidence that current functionality is missing:

- `formal/checked-raw-wire-v1`
- `formal/end-to-end-refinement-push`
- `formal/serialized-refinement-v1`
- `formal/v06-wire-e2e`
- `formal/v06-e2e-refinement`
- `formal/lean-authoritative-production`
- `formal/integrate-wire-v1-main`
- `formal/csv-numeric-bound-v1`
- `formal/aristotle-proof-promotion-2026-09-29`
- `v06/canonical-json`
- `v06/frozen-byte-contract`
- `v06/typed-certificate-internals`
- `v06/replay-normalized-wire-v2`

Current production formal imports include the wire, normalized-wire, package/archive, signature/hash, workflow/environment, certified built-in checker, high-assurance, canonical archive, and frontier layers.

Any future salvage from these branches must identify a specific unique change and port it onto a fresh branch from current `main`.

## Aristotle handoff / integration history

Treat these as archival handoff/integration history:

- `aristotle-handoff-2026-09-28`
- `aristotle-handoff-final-2026-09-29`
- `aristotle/frontier-tcb-final`
- `integrate/aristotle-frontier-tcb`

They are useful for provenance but are not current integration branches.

## CI / runtime diagnostics

Treat these as diagnostic or setup history:

- `circleci-project-setup`
- `ci/host-os-probe`
- `ci/runtime-boundary-probe`

Their configurations should not be reintroduced wholesale. Promote only a specific diagnostic into permanent CI when the permanent policy explicitly needs it.

## Restoration fixes

These are historical fix branches whose relevant fixes are represented on current `main`:

- `fix/restoration-lean-authority`
- `fix/restoration-shared-lean`

## Audit-created branches

The following branches were created during the 2026-10-04 audit and then reset to the repaired `main`, so they contain no outstanding branch-only work:

- `diag/formal-wire-lean-2026-10-04`
- `fix/formal-wire-executable-mode`

They may be deleted when convenient.

## Future reconciliation procedure

Before deciding that any old branch contains missing work:

1. fetch current remote refs;
2. run `python scripts/audit_branch_reconciliation.py --base origin/main`;
3. identify the PR associated with the branch and the head SHA actually reviewed;
4. account for squash merges;
5. compare actual content, not just commit ancestry;
6. check for post-merge commits;
7. determine whether current `main` contains an evolved implementation;
8. port only proven unique residual work into a fresh PR.

Never use "ahead by N commits" as a merge instruction.
