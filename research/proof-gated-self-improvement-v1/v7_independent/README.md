# V7 independent authority-history audit intake

**Research-only draft. This directory is not a trusted authority, deployment component, or a complete V7 integration.**

Source V7 release: `pcs_proof_gated_v7.tar.gz`, SHA-256 `e98448c4d9493c54b88c876ea715c4c66d653565bf60d553c9627b14b7a5f8f8`.
The authoritative complete standalone release is provided in the research conversation; no claim is made that the original tarball or its 516 files are included in this PR.

This research branch is proposed as a draft PR stacked on Aristotle V7 PR #149, itself based on V6 PR #134, not main. The proof-gated work from PRs #117, #127, #129, #130, #133, #134, #135 and #142 remains separate.

## Findings

- A V7 proposal receipt is intentionally independent of the proposer-supplied policy, generation and active-model fields. Consequently, receipt equality does not authenticate those submitted fields.
- A trusted `Event.govern` can change supported policy without producing a proposal receipt. A proposal-only chain is therefore not a complete governance-event history.
- A supported *authorized* policy change may accept an update that regresses on a previously used objective. Historical capabilities need an explicit cross-policy preservation contract.
- These are stronger audit/governance obligations that V7 did not promise; **none falsifies V7's stated Lean theorem soundness**.

## Reproduction and requirements

The exact-byte independent `v7_independent_audit.py`, `v7_boundary_falsification.py`, and both source reports are committed here. The complete V7 golden fixtures are committed separately in the formal V7 base (PR #149), at `formal/fixtures/proof_gated/v7/`. This PR should be reviewed **stacked on that V7 branch**; it does not duplicate fixtures.

From the PCS repository root after the V7 branch and this PR are combined:

```sh
python3 research/proof-gated-self-improvement-v1/v7_independent/v7_independent_audit.py --fixtures formal/fixtures/proof_gated/v7 --mutations 20000
python3 research/proof-gated-self-improvement-v1/v7_independent/v7_boundary_falsification.py --fixtures formal/fixtures/proof_gated/v7 --out /tmp/v7_boundary_results.json
```

Both scripts use Python standard library only and were independently rerun against the full V7 fixture tree locally. Their results do **not** establish universal Python/Lean implementation equivalence or production history authenticity. A dedicated GitHub CI workflow is requested for this exact combination; keep this PR draft until hosted replay and code review are complete.

## Scope

No production PCS authority changes; no original V5/V6/V7 formal definitions changed; no merges or production promotion. Any hash-chain provenance claim needs separately protected authenticating/monotonic state. A successful semantic replay is not evidence of protected history.
