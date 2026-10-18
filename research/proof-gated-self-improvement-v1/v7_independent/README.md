# V7 independent authority-history audit intake

**Research-only draft. This directory is not a trusted authority, deployment component, or a complete V7 integration.**

Source V7 release: `pcs_proof_gated_v7.tar.gz`, SHA-256 `e98448c4d9493c54b88c876ea715c4c66d653565bf60d553c9627b14b7a5f8f8`.
The authoritative complete standalone release is provided in the research conversation; no claim is made that the original tarball or its 516 files are included in this PR.

This branch is stacked on Aristotle V6 draft PR #134, not main. The proof-gated work from PRs #117, #127, #129, #130, #133, #134, #135 and #142 remains separate.

## Findings

- A V7 proposal receipt is intentionally independent of the proposer-supplied policy, generation and active-model fields. Consequently, receipt equality does not authenticate those submitted fields.
- A trusted `Event.govern` can change supported policy without producing a proposal receipt. A proposal-only chain is therefore not a complete governance-event history.
- A supported *authorized* policy change may accept an update that regresses on a previously used objective. Historical capabilities need an explicit cross-policy preservation contract.
- These are stronger audit/governance obligations that V7 did not promise; **none falsifies V7's stated Lean theorem soundness**.

## Import status and reproduction limits

Exact-byte copies of both experiment reports and `v7_boundary_falsification.py` are committed here.
The latter imports `v7_independent_audit.py` and expects the **original V7 golden fixtures** under `fixtures_v7/`. Those dependencies are not yet committed on this branch; the experiment is **not standalone here**, and CI should not be marked green on this PR based solely on these documents.
The full standalone packages were produced and tested locally. Do not use a fabricated replacement fixture tree.

Once the dependencies are ingested unchanged from their existing artifact packages, run:

```sh
python3 v7_boundary_falsification.py --fixtures fixtures_v7 --out boundary_results.json
```

Require exact source hashes, test results, and an independent runtime/Lean replay before any merge claim.

## Scope

No production PCS authority changes; no original V5/V6/V7 formal definitions changed; no merges or production promotion. Any hash-chain provenance claim needs separately protected authenticating/monotonic state. A successful semantic replay is not evidence of protected history.
