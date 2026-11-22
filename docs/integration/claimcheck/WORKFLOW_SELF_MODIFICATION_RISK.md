# Residual risk: a pull request can change what its own required checks run

**Owner decision (2026-11-22).** G1 is deferred. For this internal integration stage, the protection
is:

* G2, approved in principle and to be included in the final C1 admission;
* explicit owner review of every change to gate definitions and workflows.

This page records the risk that remains, how it is limited, and when to revisit it. Nothing here is
applied, and no ruleset changes.

## The risk

GitHub runs a `pull_request` workflow from the pull request's own merge commit. A pull request
that changes a workflow, or a gate's own source files, therefore decides what its required checks
run. It can make them pass without the gate running:

* replace a gate command, or mark its job `if: false` (a skipped job counts as passing);
* add a workflow with a job of the same name;
* restore the old, non-isolated gate step and add a root `json.py`. Reproduced on C1 + G2: forged
  success (independent review, F5).

No gate detects this:

* the manifest gate treats its own files as trusted configuration;
* the retained-source gate excludes its control files from the comparison (H1-b test 9);
* the workflow that would compare the bytes is the one the pull request changed.

**The files that carry the risk:**

* `.github/workflows/**` in either repository;
* core: `research/integration_v2/*.py`, `scripts/check_reconciled_prs.py`,
  `scripts/test_reconciled_prs.py`, and the control manifests;
* site: `scripts/check_reconciled_prs.py`, `scripts/test_reconciled_prs.py`, `package.json`,
  `package-lock.json` and the site's other gate scripts.

**The checks it affects:** every required check that a repository workflow produces:

* core `source-policy` and `verified-public-integration`, and `claimcheck-required` after C2;
* site `site-full-gate`, and `original-pr-ancestry-and-production-preservation` after D2b.

**What G2 changes and what it does not.** With G2 in C1, a pull request that leaves these files
alone cannot forge `source-policy`, whatever else it adds. A pull request that edits them still can.
G2 does not change that: it narrows the files to watch to the short list above.

## How it is limited now

1. **Only you can merge.** You are the sole collaborator on both repositories.
2. **The pre-merge check, before every merge** (`OWNER_EXECUTION_CHECKLIST.md`, "Before every
   merge"). It is a read-only `git diff --name-only` of the pull request against `main` over these
   files and the import paths. It runs nothing from the pull request.
3. **Any output from the pre-merge check means the pull request is a gate-definition change.**
   * Its green checks prove nothing about the gates.
   * Review the diff line by line, and merge only as its own recorded, approved protected change.
   * This is how C1 and C2b are already handled: their control commits change gate files by design.
4. **Not affected:** pull requests that leave these files alone. For them, the required checks run
   the reviewed definitions, and with G2 nothing they add can run before the gate.

## What this means for evidence

* A green required check on a pull request that touches the files above is not evidence that a gate
  passed.
* Neither is any non-required run of the manifest or retained-source gate (G2 document, section 4,
  F4). Those invocations stay non-isolated.
* CI results are never evidence of scientific correctness.

## When to revisit (G1, or an organisation-level workflow rule)

* someone else gains write or merge rights, or an automation can merge;
* CI status is to be used as evidence for third parties;
* the repositories move to an organisation. There, the ruleset rule "Require workflows to pass"
  pins a workflow at a fixed reference.

Before relying on G1, test in a scratch repository:

* which commit a `pull_request_target` check attaches to;
* that a later, same-named, passing job a pull request adds cannot satisfy the requirement.

The proposal and its evaluation are in `g1/` and in `G2_IMPORT_ISOLATION.md`, section 6. G1 must
never check out or run pull-request code.
