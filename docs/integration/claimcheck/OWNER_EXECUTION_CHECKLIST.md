# Owner execution checklist: C1, C2, D1–D3, R1 (and the decisions that must precede them)

**Nothing in this file has been executed.** Each block is a separate decision: approving one
authorises only its own steps. No protected patch, tag, merge or deployment happens without the
owner's explicit authorisation of that block. The independent review
([`INDEPENDENT_REVIEW_CHECKLIST.md`](INDEPENDENT_REVIEW_CHECKLIST.md)) should pass first.

Order:

* **Core:** L1–L3, then T1 (recommended), then C1, then C2 (and optionally C2b), then R1.
* **Website:** D1 and D3, then regenerate, then D2 (and optionally D2b).
* **Both:** merge and deployment are separate decisions after these.

Any change to the branch after the evidence was generated (an L decision, D1, D3) changes the
source commit. The evidence must then be regenerated and reviewed again.

## Before admission

### L1–L3. Recorded model outputs ([`MODEL_OUTPUT_LICENSING.md`](MODEL_OUTPUT_LICENSING.md))
* **L1 Gemini (23 files):** keep, adding a provenance note.
* **L2 Nemotron (21 files):** choose (a) obtain confirmation, then keep; (b) replace the texts with
  digests before C1; or (c) keep as is.
* **L3 Cohere (1 file):** remove before C1.
* **Effect:** L2(b) and L3 are ordinary commits on the branch. Each changes the census, so
  regenerate the evidence afterwards.

### T1. Retained-source tag ruleset ([`REQUIRED_CHECKS.md`](REQUIRED_CHECKS.md), "Retained-source tags")
* **Authorises:** in each repository, a tag ruleset on `refs/tags/pcs-source-intake/*` with
  "Restrict creations", "Restrict updates" and "Restrict deletions", and a bypass list holding only
  the repository-admin role.
* **Verify:** listing tags still shows the two existing intake tags at `0b521f39…` (core) and
  `d35e2b5e…` (site).
* **Undo:** delete the ruleset.

## Core

### C1. Admit the ClaimCheck sidecar (protected)
* **Authorises:**
  * the retained commit;
  * the annotated tag `pcs-source-intake/core-claimcheck-v1-20261114` on it;
  * one control commit with the four files from `--emit`;
  * merging that control commit after its checks pass.
* **Does not authorise:** any other file change, ruleset change (C2), deployment, or the research
  branch (R1).
* **Steps:**
  1. Fix `H`, the PR 212 head after the L decisions. Run
     `python -m research.claimcheck_v1_1.governance.check_admission_consistency`; it must report
     `consistent: true`.
  2. Run
     `python -m research.claimcheck_v1_1.governance.prepare_core_admission --out D1 --pytest-python <python> --emit D2`.
     It must report `all_as_expected: true`. The V23 digest, the control-file digests and the
     retained commit must equal the PR description for `H`, and
     `review_v23_manifest --emit D2 --head H` must report `consistent: true`.
  3. Create the retained commit with the exact command in `ADMISSION_PROPOSAL.md` (fixed identity,
     date and message). Its ID must equal `proposed_retained_source_commit.commit` in `D1/dry-run.json`.
  4. Check that the tag name is free:
     `git ls-remote --tags origin 'refs/tags/pcs-source-intake/core-claimcheck-v1-20261114'` prints
     nothing. Then run
     `git tag -a pcs-source-intake/core-claimcheck-v1-20261114 <retained commit> -m "<message>"` and
     `git push origin refs/tags/pcs-source-intake/core-claimcheck-v1-20261114`. If T1 is in force,
     act as the admin bypass.
  5. On top of `H`, commit exactly the four files from `D2` as one commit, and open or update the
     pull request.
* **Verify:**
  * on the control commit, `source-policy` and `verified-public-integration` pass;
  * `model-assurance-studio-research.yml` runs (the control commit touches integration paths) and
    `check_reconciled_prs.py --core` passes;
  * `claimcheck-required` passes.
* **Stop if:**
  * any digest differs from the reviewed value;
  * the tag name already exists;
  * the control commit touches a fifth file;
  * any required check fails.
* **Undo before merge:**
  * delete the tag (`git push origin :refs/tags/pcs-source-intake/core-claimcheck-v1-20261114`);
  * drop the control commit;
  * the retained commit then becomes unreferenced.

  After merge, undoing it is a new reviewed change.

### C2. Require `claimcheck-required` on core `main` (ruleset)
* **Authorises:** adding the GitHub Actions check `claimcheck-required` to the core `main` ruleset,
  after C1 is merged.
* **Verify:** an unrelated pull request still gets `claimcheck-required` reported (it runs on every
  pull request) and is not left pending.
* **Undo:** remove it from the ruleset.

### C2b (optional). Make the core retained-source gate bind on every pull request (protected workflow)
* **Authorises:** a reviewed change adding `python scripts/check_reconciled_prs.py --core "$PWD"` to
  the `source-policy` job of `pcs-public-full-verification.yml`.
* **Not prepared:** a patch and dry run would be prepared on request.
* **Why:** today that gate runs only on pull requests that touch integration paths.

### R1. Research assurance branch (PR 216)
* **Decision:** confirm the route. Recommended: a separate V24 successor after C1 is merged, built by
  the same script on the research branch.
* **Authorises now:** nothing. A V24 proposal, with its own census, dry run and review, would be
  prepared on request after C1.

## Website

### D1. Reading-help successor (protected verifier, patch 01)
* **Authorises:** `git apply -p0 docs/governance/claimcheck-proposals/01-reading-help-verifier.patch`
  as one commit on the site branch (digest `98218343…d398`).
* **Verify:** `beginner-browser` and `lean-learning-browser` pass. `site-full-gate` passes once D3
  also holds and the evidence is regenerated.
* **Undo:** revert the commit.

### D3. ClaimCheck tests in the complete gate (patch 03)
* **Authorises:** `git apply docs/governance/claimcheck-proposals/03-complete-gate.patch` as one
  commit (digest `53e96704…98fd1`).
* **Verify:** `npm run ci:zero-minutes` runs the 15 ClaimCheck tests.
* **Undo:** revert the commit.

### Regenerate (after D1 and D3, not protected)
Fix the new site head `S_site'` and run:

* `python3 scripts/dry_run_claimcheck_proposals.py --commit S_site'`;
* `python3 scripts/prepare_claimcheck_site_admission.py --commit S_site'`;
* `python3 scripts/check_claimcheck_proposals_consistency.py`, which must report `consistent: true`;
* `python3 scripts/claim_check_journey_record.py check --record docs/evidence/claim-check-v2`, which
  must pass.

The retained commit changes from `6c1ec33e…`, because `S_site'` differs from `e0b9136`. Review the
new values.

### D2. Admit the website change (protected gate, patch 02, retained commit and tag)
* **Authorises:**
  * the retained commit recorded in the regenerated `02-reconciliation-gate.dry-run.json`;
  * the annotated tag `pcs-source-intake/site-claimcheck-v1-20261117` on it;
  * the regenerated patch 02 as one separate control commit.
* **Steps:**
  1. Reproduce the retained commit (`successor.reproducible_with`); its ID must equal
     `successor.retained_commit`.
  2. Check that the tag name is free with `git ls-remote`, then create and push the annotated tag.
  3. Apply patch 02 and commit.
* **Verify:** `original-pr-ancestry-and-production-preservation`, `beginner-browser`,
  `lean-learning-browser` and `site-full-gate` pass.
* **Stop if:** an ID or digest differs, the tag exists, or a check fails.
* **Undo before merge:** delete the tag and drop the control commit.

### D2b (optional). Require `original-pr-ancestry-and-production-preservation` on site `main` (ruleset)
* **Why:** after D2, it is the only check that enforces the `public/` anchor and the retained-source
  rule.
* **Undo:** remove it from the ruleset.

## After all of the above (separate decisions)

* **Merge** each pull request under the existing linear-history rules.
* **Deploy** the website page: a separate decision, not requested.
