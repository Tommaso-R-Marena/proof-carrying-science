# Integration proposal (not implemented)

This document proposes future, separately reviewed integration with PCS
production and sibling research. **No integration edits are included in this
branch.**

## Candidates

1. **Scientific workflow obligation graphs** — use PCSIncremental invalidation
   as a generic core beneath domain-specific workflow packages.
2. **Epistemic kernel** — replace heuristic reopen with proved Affected closure
   while preserving stratum semantics.
3. **ClaimCheck / EvidenceKernel** — treat domain certificates as `LocalCheck`
   instances; do not merge code without admission review.
4. **Checked-reuse** — orthogonal; lemma libraries remain proof-search artifacts.

## Admission requirements (owner-gated)

- Path allowlist under repository integrity policy.
- Independent review of trust boundaries.
- No silent authority elevation from research cache to production signing.
- Publication/IP clearance before public disclosure of novel results.

## Explicit non-actions of this PR

- Does not modify `pcs/`, root `formal/`, CI, or source manifests.
- Does not merge to `main`.
- Does not claim production authority.
