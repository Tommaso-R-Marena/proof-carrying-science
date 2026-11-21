# Required checks for ClaimCheck (owner decision C2): recommendation

**A recommendation. No ruleset, required check, workflow trigger of an existing gate, or bypass
setting has been changed.** Rulesets are repository settings only the owner can change, and the tools
available to this work cannot read them. On 2026-11-19 the owner confirmed the required checks of
both `main` rulesets and the absence of bypass actors (below). What remains to confirm is listed in
"The live rulesets".

## What was checked

| | How | Result |
| --- | --- | --- |
| workflow triggers and job names, both repositories | parsed every workflow on the draft PR heads | inventory below |
| the names GitHub actually reports | check runs on core PR 212 (head `c526d05c`) and site PR 149 (head `272579f`) | names equal the job names; matrix jobs carry their parameters, e.g. `portability-ubuntu-24.04-py3.13` |
| the live rulesets | not readable here | **confirmed by the owner on 2026-11-19**: core requires `verified-public-integration`, site requires `site-full-gate`, no bypass actors |

Documented required checks: core `verified-public-integration` (strict aggregate) and `source-policy`
(`docs/HOSTED_CONTRIBUTION_CI.md`, 2026-10-09); site `site-full-gate`
(`docs/HOSTED_CI_REPLACEMENT.md` on the site, 2026-10-17). Older documents name Cloudflare and CircleCI
contexts that were later retired; they should not be re-added.

Two GitHub behaviours decide everything here (GitHub documentation, "Troubleshooting required status
checks"): a **workflow** skipped by a path or branch filter reports nothing, so a check required from
it stays *pending* and blocks every pull request that does not touch those paths; a **job** skipped by
its `if:` condition reports *success*, so a required job that is skipped passes the requirement.

## Core repository

### What exists

| Workflow | Runs on pull requests | Jobs (= check names) | Notes |
| --- | --- | --- | --- |
| `pcs-public-full-verification.yml` | every PR to `main` | `source-policy`, `core-full-gate`, `real-analysis-bridge`, `certiforge-integration`, `portability-*`, `lean-learning-loop`, `independent-pilot-cleanroom`, `verified-public-integration` | `verified-public-integration` runs with `always()` and fails unless every prerequisite **succeeded** (skipped, cancelled or missing fail it): the right kind of required check |
| `pcs-ci.yml`, `pcs-required-self-hosted.yml` | every PR to `main` | `repository-integrity`, `python-assurance`, `lean-kernel`, `v06-byte-contract`, `verified-integration`, `required-gate` | **every job is skipped on every pull request** (they run only for non-PR events in a private repository with a self-hosted runner) |
| `pcs-claimcheck-v1.yml` (added by this branch) | every PR (since commit `99637e67`) | `changes`, `offline-and-kernel`, `meaning-theorems`, `claimcheck-required` | see below |

### Finding: requirements that a skipped job would satisfy

On PR 212 the six jobs of `pcs-ci.yml` and `pcs-required-self-hosted.yml` report **skipped**. If any of
`repository-integrity`, `python-assurance`, `lean-kernel`, `v06-byte-contract`, `verified-integration`
or `required-gate` is a required check, it is satisfied on every pull request without anything having
run. The documented required checks do not include them; please confirm that the live ruleset does
not either. Separately, `core-full-gate` and three other jobs have `needs: source-policy` without
`always()`: when `source-policy` fails they are skipped, so they must never be required on their own.
`verified-public-integration` is safe because it rejects skipped prerequisites. And if the repository
were made private, every job of `pcs-public-full-verification.yml` would be skipped (they require a
public repository), so a required `verified-public-integration` would pass vacuously: re-examine the
ruleset before any visibility change.

### The ClaimCheck checks, and why only one should be required

Until commit `99637e67` the ClaimCheck workflow ran only on pull requests that touched its paths. Its
jobs could not be required: every other pull request would have waited for them forever. The
workflow now runs on every pull request:

* `changes` (seconds) decides whether the pull request touched `research/claimcheck_v1/`,
  `research/claimcheck_v1_1/`, the Lean bootstrap `scripts/activate_lean_428.sh` (which ClaimCheck
  runs and which the old path filter missed) or the workflow itself. It diffs GitHub's merge commit
  against its first parent with renames disabled, so a file moved out of ClaimCheck still counts, and
  it fails (it does not guess) if the checked-out commit is not that merge;
* `offline-and-kernel` and `meaning-theorems` run only when `changes` says so;
* `claimcheck-required` always runs and fails unless `changes` succeeded and, when a ClaimCheck path
  changed, both jobs succeeded.

Tested by `research/claimcheck_v1_1/governance/test_required_check.py`, which runs the two shell steps
verbatim: 13 change scenarios on real Git merge commits (documentation only, production code only, a
look-alike directory `claimcheck_v1_10/`, each ClaimCheck root, a new file, the Lean bootstrap, the
workflow, a deletion, a rename out of the tree, an empty pull request, a non-merge checkout, a manual
run), and all 192 combinations of job results for the aggregate, of which exactly the 17 intended
ones pass. The positive path also runs live on PR 212.

Actions in this workflow are now pinned to the commits the repository's other workflows use, and the
checkout does not keep credentials.

**Recommendation (core):** add exactly **`claimcheck-required`** (GitHub Actions) to the required
checks of the `main` ruleset, after the source admission (C1) is merged. Do not require
`offline-and-kernel` or `meaning-theorems` directly: they are skipped (= passing) on unrelated pull
requests by design, and the aggregate already requires them when they matter. Keep
`verified-public-integration` and `source-policy` as they are. Adding `claimcheck-required` cannot
leave a pull request pending (it runs on every pull request) and weakens nothing (it only adds a
condition).

A required check from a workflow in the pull request cannot stop a pull request that edits that
workflow. Here that is covered by the source admission: the V23 manifest pins the workflow's bytes,
so an edited workflow fails `source-policy` until the owner admits it.

If PR 216 is admitted, its `proofs-and-refinement` job has the same path-filter problem; give it the
same aggregate before requiring it (not done: that PR stays separate until decided).

## Website repository

| Workflow | Runs on pull requests | Jobs | Notes |
| --- | --- | --- | --- |
| `site-public-verification.yml` | every PR to `main` | `site-full-gate` and its prerequisites | `site-full-gate` runs `bash scripts/cloudflare_build.sh`, which runs `npm run ci:zero-minutes`, the complete website gate |
| `claim-check.yml` | PRs touching 10 ClaimCheck paths | `claim-check-page` | path-filtered: **must not be required as it is** |
| `site-check.yml`, `open-pr-reconciliation.yml`, `countermodel-lean.yml`, `site-contract.yml` | every PR | `site-check`, `original-pr-ancestry-and-production-preservation`, `countermodel-lean-kernel`, `site-contract` | unchanged |

**Recommendation (site):** no new required check. Proposed patch 03 (decision D3) appends
`npm run test:claim-check` to `ci:zero-minutes`, so ClaimCheck's mandatory tests (served runner
digest, catalog, withdrawn receipts refused, local-run labels, receipt rules) run inside
`site-full-gate`, which is already required and runs on every pull request. That adds no pending
check and changes no ruleset. `claim-check-page` (the browser journey with the real Lean kernel)
stays a supplementary, path-scoped check; if the owner wants it required too, give it the same
change-detection aggregate as the core workflow first.

## The live rulesets: confirmed by the owner on 2026-11-19

The tools used for this work cannot read rulesets. They report only whether a branch is protected
(both `main` branches are). The owner checked the rulesets and stated, on 2026-11-19:

* the active **core `main`** ruleset requires **`verified-public-integration`**;
* the active **site `main`** ruleset requires **`site-full-gate`**;
* neither has a configured **bypass actor**.

What this implies, from the workflows:

* `verified-public-integration` fails unless every prerequisite succeeded, `source-policy` included.
  So the source-admission gate is enforced through the required aggregate even if `source-policy`
  is not listed separately.
* `site-full-gate` runs the complete website gate (`npm run ci:zero-minutes`). With patch 03 (D3) it
  also runs ClaimCheck's tests.

Not covered by the owner's statement, and still to confirm when convenient:

* that none of the six core jobs skipped on every pull request is required;
* that no retired Cloudflare or CircleCI context is required;
* the repository's default workflow-token permission. Two core workflows
  (`build-verifier-artifacts.yml`, `product-hardening.yml`) declare no `permissions:` and so receive
  the default (**Settings → Actions → General → Workflow permissions**; "Read repository contents"
  is the safe setting);
* the retained-source tags (next section).

After C1: add `claimcheck-required` (GitHub Actions) to core `main` (decision C2).

## Which gates bind on every pull request (found 2026-11-19)

With the required checks the owner confirmed, source authority is enforced as follows:

| Gate | Core | Site |
| --- | --- | --- |
| reviewed manifest of every tracked file (`research/integration_v2/reconcile.py --require-committed`, V22, V23 after C1) | runs in `source-policy` on every pull request; **binding**, through the required `verified-public-integration` | no equivalent manifest |
| retained-source lineage and exact non-control bytes (`scripts/check_reconciled_prs.py`) | runs only in `model-assurance-studio-research.yml`, which is **path-filtered** (integration paths) and **not required** | runs on every pull request as `original-pr-ancestry-and-production-preservation`; **not required** |
| site `public/` tree equals protected `main` (same script, site mode) | not applicable | same job as above; **not required** |
| complete website gate (`npm run ci:zero-minutes`, including the reading-help verifier of D1) | not applicable | `site-full-gate`; **binding** |

**Consequences.**

* On the core, widening the admitted tree needs a change to the manifest, which is pinned in
  `reconcile.py` and so is protected. The retained commit and its tag (C1) add a lineage check that
  runs only when integration files change; the control commit of C1 itself triggers it.
* On the site, the retained-source rule, and the rule that the whole `public/` tree (the deployed
  tree) equals `main`, bind only if `original-pr-ancestry-and-production-preservation` is required.
  As confirmed, it is advisory. `site-full-gate` pins some public files through its own checks (for
  example the reading-help verifier, which is why D1 is needed). But no required check enforces the
  whole-tree rule.

Options for the owner, separate decisions in [`OWNER_EXECUTION_CHECKLIST.md`](OWNER_EXECUTION_CHECKLIST.md):

* **D2b:** require `original-pr-ancestry-and-production-preservation` on site `main`, after D2.
  Before D2 it would block PR 149, which is its purpose.
* **C2b:** add `python scripts/check_reconciled_prs.py --core "$PWD"` to the `source-policy` job.
  That is a protected workflow change, needed because a path-filtered job cannot be required. With
  it, the core's retained-source rule binds on every pull request too.

## Proposed changes C2b, D2b and T1 (exact; none applied)

### C2b: the core retained-source gate in the required path (protected code, two control files)

`reconcile.py --require-committed` already runs in `source-policy` on every pull request. With C2b it
also runs `scripts/check_reconciled_prs.py --core` in a separate process, with `PYTHONOPTIMIZE`
removed so its assertions cannot be stripped. It fails the source contract if that gate fails.

| | |
| --- | --- |
| files changed | `research/integration_v2/reconcile.py` (+26 −1 lines), `research/integration_v2/test_reconcile.py` (+25 lines, one test) |
| unchanged | workflows, manifests, pinned files, retained commits, rulesets |
| order | after C1. It edits C1's versions of the two files, which are control paths of both gates, so it is its own control commit with no manifest change |
| patch and dry run | `python -m research.claimcheck_v1_1.governance.prepare_c2b --out docs/integration/claimcheck/c2b --pytest-python <python>` writes `proposed-c2b.patch` and `c2b-dry-run.json` |
| negative controls | the manifest gate alone passes, and C2b rejects: the retained tag deleted; the tag pointing at another commit; an untracked file in the working tree |
| no false failure | the `source-policy` steps that run before the gate leave no untracked file; `__pycache__` is ignored |
| caveats | annotated tags are not enforced (a lightweight tag at the right commit passes), and authority rests on the commit ID in the gate. Every workflow that runs `reconcile --require-committed` checks out full history with tags |

**C2b dry run (regenerated 2026-11-21 at `ad43f21c` after the independent review, `c2b/c2b-dry-run.json`,
patch `c2b/proposed-c2b.patch`, SHA-256 `c8d96303…560e`): all as expected.** The gate's child
process now runs in isolated mode (`-I`). It ran on top of C1's dry-run control commit with the H1-b
retained commit:

* the gate passes on 72 PRs and reports `retained_source.passed: true`;
* the protected suites pass: `test_reconcile.py`, 76 tests (75 plus the new one), and
  `scripts/test_reconciled_prs.py`, OK;
* the CI steps that run before the gate in `source-policy` leave no untracked file, including
  `check_pr_contributions.py`; the gate passes after them;
* three negative controls each pass under C1 alone and are rejected with C2b: the retained tag
  deleted, the tag moved, an untracked file present;
* the required workflow runs `source-policy` on every pull request to `main`, with full history and
  tags, and its aggregate rejects a skipped or failed `source-policy`. A pull request can still edit
  that workflow, or `reconcile.py` itself (D2b's caveat; H1-b test 9).

The patch changes two files and adds 51 lines. Regenerate it at the commit after C1.

### D2b: require the website's retained-source and public-tree check (ruleset)

**The change, in the site repository:** Settings → Rules → Rulesets → the active ruleset that
targets `main` (the one requiring `site-full-gate`) → **Require status checks to pass** → **Add
checks** → `original-pr-ancestry-and-production-preservation`, with the source **GitHub Actions** →
Save. Leave every other setting as it is, including whether branches must be up to date.

REST equivalent (`PUT /repos/Tommaso-R-Marena/proof-carrying-science-site/rulesets/<id>`): add
`{"context": "original-pr-ancestry-and-production-preservation", "integration_id": 15368}` to the
`required_status_checks` parameters. `15368` is the GitHub Actions app; confirm it in the UI's source
field.

**Why it cannot stay pending:**

* the job is in `.github/workflows/open-pr-reconciliation.yml`, which triggers on every
  `pull_request` with no `paths` filter;
* the job has no `if:`;
* so it reports on every pull request;
* the file is identical on `main` and on the PR 149 head (checked 2026-11-19).

**When:** at any time after D2's control commit is on PR 149. Before that, PR 149 fails the check by
design and cannot merge, which is what D2b is for.

**Consequence:** every later site pull request must keep:

* the non-control files equal to the retained intake's tree;
* `public/` equal to the intake's `public/` (patch 02).

So **every website change then needs a retained-source admission** (new retained commit, tag and gate
patch), the same regime the core manifest already imposes. Without D2b, those rules stay advisory.

**Caveat:** the workflow is itself a control file of the site gate. A pull request that edits it can
make the check vacuous. See the next section, which also proposes the smallest protection (G1).

### D2b: can a pull request make the required check vacuous? (checked 2026-11-19)

**Yes, by editing its own workflow.**

* GitHub runs a `pull_request` workflow from the pull request's merge commit ("`GITHUB_SHA` is the
  SHA of the merge commit on the merge branch"; docs, *Events that trigger workflows*). So a pull
  request that edits `.github/workflows/open-pr-reconciliation.yml` gets a passing
  `original-pr-ancestry-and-production-preservation` without the gate running: it can replace the
  two gate commands with `true`, or add `if: false` (a skipped required job counts as passing). It
  can also add a new workflow with a job of the same name.
* The ruleset's "expected source" (GitHub Actions, integration 15368) restricts which app reports the
  check, not which workflow file produces it. Every workflow reports through that app.
* The rule that would pin the workflow, *Require workflows to pass before merging* (a workflow file at
  a fixed ref of a fixed repository), "can be configured at the organization or enterprise level"
  (docs, *Available rules for rulesets*, Enterprise Cloud edition). These are personal-account
  repositories. The repository-level list of rules does not include it, although the REST
  description has a `workflows` rule type.
* The site gate lists the workflow among its control files (`CONTROLS` in
  `scripts/check_reconciled_prs.py`). Controls are excluded from the tree comparison, so the gate
  itself does not notice a changed workflow.
* The same holds in the core for `source-policy` inside `verified-public-integration`. V23 pins the
  workflow's bytes there, but the step that compares them runs from the same workflow the pull
  request controls.

**How material.** Only the owner, the sole collaborator, can merge, and a workflow change shows in
the diff. The check protects against a pull request that leaves its workflow alone, which covers
ordinary mistakes. It does not protect against one that edits it: a green check then proves only
that some GitHub Actions job of that name passed under a workflow the pull request controls. That
weakens the statement "every merged change passed the retained-source gate". Material in principle;
limited in practice by who can merge.

**Smallest effective additional protection.**

1. **Procedural (recommended now; no change).** Before merging any pull request, run the
   gate-definition check in the owner execution checklist ("Before every merge"). It lists changes to:
   * workflows;
   * gate-defining files;
   * the paths through which a gate's own imports could be replaced (next section).

   Any output means the pull request needs its own protected decision.
2. **Enforced (optional): G1, a gate-definition guard** (protected: one workflow on `main` and one
   required check). The proposals are `g1/gate-definition-guard.core.yml` and
   `g1/gate-definition-guard.site.yml`.
   * It is a `pull_request_target` workflow. GitHub runs the copy on the default branch ("This event
     runs in the context of the default branch of the base repository, rather than in the context of
     the merge commit"), so a pull request cannot change what it runs.
   * It reads the pull request's commits as data (file names only) and executes nothing from them.
     Its token is read-only and it uses no secret.
   * It fails when the pull request changes any workflow, any gate-defining file, or any path through
     which a gate's own imports could be replaced (next section): `.github/`, `scripts/`, root `*.py`,
     a new `research/__init__.py` (core), `conftest.py`, `sitecustomize.py`, `usercustomize.py`, and
     the manifests and registry. It compares with `main` fetched at run time and runs again when a
     pull request is retargeted.
   * Required as `gate-definition-unchanged`, it never stays pending: it has no path filter.
   * Consequence: every gate change (C1, C2b, D2, later admissions) merges only through your
     recorded ruleset bypass. That is the intended meaning.
   * Tested on scratch repositories (2026-11-19): 14 cases in each repository, all as intended.
     * Pass: an unrelated change, and a new module deep in the tree.
     * Fail in both: an edited or added workflow, an edited gate script, an edited registry, a
       `json.py` at the root or in `scripts/`, a nested `conftest.py`, a `sitecustomize.py`.
     * Fail in the core: `research/__init__.py`, the manifest, `reconcile.py`.
     * Fail in the site: `package.json`.
   * **On the site, G1 alone does not protect `site-full-gate`.** Its tests and build scripts are
     bound only by D2b's retained-source rule, so G1 there assumes D2b.
   * **Residual risk, not verifiable here.** GitHub does not document how a required check is decided
     when two workflows report jobs with the same name. A pull request could add a workflow with a
     job named `gate-definition-unchanged`. G1 itself would then fail, because a workflow was added.
     But if GitHub accepted the later of two same-named results, the imitation could mask it. Before
     relying on G1, test this in a scratch repository: a failing `pull_request_target` job and a
     same-named `pull_request` job that passes later. Merging must stay blocked.
   * **Also not documented:** which commit a `pull_request_target` job's check attaches to. GitHub
     lists the event among those whose job checks are evaluated for a pull request, and `GITHUB_SHA`
     is the default branch's last commit. The same scratch test must show that G1's failing check
     blocks the pull request's head.
   * **Evaluation (2026-11-21):** G1 is not necessary now. G2 is
     ([`G2_IMPORT_ISOLATION.md`](G2_IMPORT_ISOLATION.md), section 6).

### The gates can import a module the pull request adds (independent review, 2026-11-19; reproduced)

Both gates import standard-library modules before they check anything:

* the manifest gate runs as `python -m research.integration_v2.reconcile` from the repository root;
* the retained-source gate runs as `python scripts/check_reconciled_prs.py`;
* Python puts the root, or `scripts/`, first on its import path. So a `json.py` (or `hashlib.py`, …)
  that a pull request adds there replaces the standard module, and runs before the census or tree
  check that would reject it;
* `research/` has no `__init__.py`, so one added there would run on import too;
* the scripts `source-policy` runs before the gate are also taken from the pull request. V23 pins
  them, but only the later gate checks that.

Reproduced in a scratch clone with a harmless marker module: it ran before either gate checked
anything. Under Python's isolated mode (`-I`) it did not, and the retained-source gate ran its own
checks. A pull request can therefore make both gates report success without touching a gate file,
which is the same class as editing the workflow. It predates this work.

**Wider than first described (G2 dry run, 2026-11-21).** The dry run reproduced 19 working vectors:

* a package, bytecode without source or a compiled module at the root;
* cached bytecode beside the gate, including a "checked" cache entry that carries the genuine
  source's hash;
* a compiled module or a package beside the gate's sources;
* a fallback for an import the standard library misses on Linux (`nt.py`);
* a script that runs before the gate and plants bytecode for it;
* `PYTHONPATH` set by an earlier step.

The full table is in [`G2_IMPORT_ISOLATION.md`](G2_IMPORT_ISOLATION.md).

**Mitigations (none applied):**

* the pre-merge check and G1 list these paths. Since 2026-11-21 they also list root-level packages,
  bytecode and compiled modules, which their first version missed;
* C2b's child process runs in isolated mode (`-I`);
* **G2 (protected; prepared and tested, `G2_IMPORT_ISOLATION.md`):**
  * core: the manifest gate is the first step of `source-policy`, as
    `python -I -B -X pycache_prefix="$(mktemp -d)"` through a fixed launcher, which checks those flags
    itself;
  * site: the retained-source gate is first, as `python -I`;
  * 24 of 24 dry-run rows as expected;
  * the independent review: the claim holds, and its two minor findings are fixed.

  An earlier sketch here, a launcher that appends the repository to the end of `sys.path`, is
  **not safe**: a planted `nt.py`, `research.py` or `research/__init__.py` defeats it (dry run). G2's
  launcher puts no file of the repository on the path except the gate's own sources.

### T1: retained-source tag rulesets (both repositories)

**In each repository:** Settings → Rules → Rulesets → New ruleset → **New tag ruleset**:

* name `Retained-source tags (owner only)`, enforcement **Active**;
* **Bypass list:** Repository admin role, "Always allow". You are the only admin of each repository
  (collaborators listed 2026-11-19);
* **Target tags:** include by pattern `pcs-source-intake/*`;
* **Rules:** Restrict creations, Restrict updates, Restrict deletions, Block force pushes.

REST equivalent (`POST /repos/<owner>/<repo>/rulesets`; check the role ID in the UI):

```json
{"name": "Retained-source tags (owner only)", "target": "tag", "enforcement": "active",
 "bypass_actors": [{"actor_id": 5, "actor_type": "RepositoryRole", "bypass_mode": "always"}],
 "conditions": {"ref_name": {"include": ["refs/tags/pcs-source-intake/*"], "exclude": []}},
 "rules": [{"type": "creation"}, {"type": "update"}, {"type": "deletion"}, {"type": "non_fast_forward"}]}
```

**Effect:**

* The existing intake tags can no longer be deleted or moved except by you: core
  `core-open-prs-v1-20261105` and `historical-v22-objects-20261105`, site
  `site-open-prs-v1-20261105`.
* The new tags of C1 and D2 can be created only by you.
* Installed apps (including the one that pushes this work) and workflow tokens can neither create,
  move nor delete them.

**What it does not do:** sign tags, or change what the gates trust. They keep comparing the tag's
target with the commit ID compiled into them.

### T1 and D2b checked against GitHub's published REST API description (2026-11-19)

* **Source:** GitHub's REST API description (`github/rest-api-description`,
  `descriptions/api.github.com/api.github.com.json`), version 1.1.4, downloaded 2026-11-19, SHA-256
  `6d9bbb20d8865b01464028937f2403954ad46598b4ebd3513dcb1a15b1a84aa7`.
* **T1 validates** against the request schema of `POST /repos/{owner}/{repo}/rulesets` (JSON Schema,
  every `$ref` inlined):
  * `target` is one of `branch`, `tag`, `push`;
  * the rule types `creation`, `update`, `deletion` and `non_fast_forward` exist;
  * `actor_type` `RepositoryRole` and `bypass_mode` `always` are allowed.
* **The check is not vacuous:** four malformed variants are rejected (unknown target, unknown rule,
  unknown actor type, unknown bypass mode).
* **Role ID.** `actor_id` is required for `RepositoryRole`, but the description does not list role
  IDs. `5` for the repository-admin role is the commonly used value, not documented there. Choose
  "Repository admin" in the UI rather than relying on the number. The docs make "Repository admins,
  organization owners, and enterprise owners" and "the maintain or write role" eligible for bypass.
* **Availability:** rulesets are available "in public repositories with GitHub Free". Both
  repositories are public.
* **`update`:** its optional parameter `update_allows_fetch_and_merge` concerns branches; omit it for
  tags.
* **D2b validates** too: a `required_status_checks` rule with
  `{"context": "original-pr-ancestry-and-production-preservation", "integration_id": 15368}` and
  `strict_required_status_checks_policy`. A `PUT` replaces the whole ruleset, so it must carry every
  existing rule as well. The UI path avoids that.
* **Existing tags stay usable.** The rules restrict creating, updating and deleting matching refs
  ("Only allow users with bypass permission to create matching refs", and likewise for update and
  deletion). Nothing restricts reading or fetching. The gates read tags with
  `git rev-parse refs/tags/<tag>^{commit}` after a full fetch, which a ruleset does not affect.
  Creating a ruleset changes no tag. On 2026-11-19 the tags were: core
  `core-open-prs-v1-20261105` → `0b521f39…`, site `site-open-prs-v1-20261105` → `d35e2b5e…`.
* **Not verifiable here:** the live behaviour; no tool here can read or write rulesets. After
  installing, check that the tag list is unchanged, and that a push of a `pcs-source-intake/*` tag
  by anyone but you is refused.

## Retained-source tags: what protects them, and what is not confirmed

**Not confirmed.** Whether a tag ruleset restricts the creation, update or deletion of
`pcs-source-intake/*` tags cannot be read with the tools available here. What could be checked on
2026-11-19:

| | Core | Site |
| --- | --- | --- |
| tag the gate names | `pcs-source-intake/core-open-prs-v1-20261105` | `pcs-source-intake/site-open-prs-v1-20261105` |
| exists, and points at the commit the gate pins | yes, `0b521f39…` | yes, `d35e2b5e…` |
| kind | annotated tag object `2823ceb2…`, unsigned, created by the owner on 2026-11-05 | annotated tag object `9cc9b06b…`, unsigned, created by the owner on 2026-11-05 |
| collaborators with write access | the owner only (admin) | the owner only (admin) |
| other `pcs-source-intake/*` tags | `historical-v22-objects-20261105` (not named by the gate) | none |

**What the gates trust.** `scripts/check_reconciled_prs.py` holds the retained commit's 40-hex ID in
its own (protected) source. It requires `refs/tags/<tag>^{commit}` to equal that ID: "A mutable
branch/tag name is not trusted in place of its exact object ID." So a tag cannot widen source
authority:

* a moved tag fails the gate;
* a deleted tag fails the gate;
* a look-alike tag is ignored;
* a squatted future tag name (created before the owner creates the real one) blocks the owner's
  step and fails the gate, but admits nothing.

The admission dry runs test the moved-tag case (core negative control `the_tag_points_elsewhere`;
site `tag_points_at_another_commit`). Authority comes from the commit ID inside the protected gate,
which changes only through a reviewed control commit under the `main` ruleset.

**What tag protection adds:** availability and an intact audit trail. Without a tag rule, any actor
with contents-write access could delete or move a retained-source tag and so break every pull
request's gate until the owner restores it. Such actors are:

* the owner;
* an installed GitHub App with write access, such as the one that pushes this work's branches;
* a workflow token with `contents: write`, such as the site's scheduled `proof-source-sync.yml`,
  which runs only code from protected `main`.

The tag is also not signed, so its tagger is not cryptographically attested. The commit ID is the
attestation that matters.

**Sufficient? Recommended configuration** (owner decision T1 in
[`OWNER_EXECUTION_CHECKLIST.md`](OWNER_EXECUTION_CHECKLIST.md)): a tag ruleset on
`refs/tags/pcs-source-intake/*`, enforcement active, with:

* "Restrict creations", "Restrict updates" and "Restrict deletions";
* a bypass list holding only the repository-admin role, or empty, temporarily relaxed by the owner
  when a new retained-source tag is created;
* optionally, signing new retained-source tags.

With that ruleset, and with the commit IDs pinned in the gates, the retained-source mechanism is
protected against widening (by the pins) and against disruption (by the ruleset).

## Consequences

| Decision | If approved | If not |
| --- | --- | --- |
| require `claimcheck-required` (core) | a ClaimCheck change cannot merge without both ClaimCheck jobs passing; unrelated pull requests are unaffected (one job of a few seconds) | ClaimCheck failures are visible but advisory, as today |
| apply patch 03 (site) | ClaimCheck's mandatory tests become part of the existing required website gate | the tests run only in the path-scoped `claim-check-page` job |
| confirm the core ruleset does not require the always-skipped jobs | removes a requirement that gives no protection on pull requests, if one exists | nothing changes |
