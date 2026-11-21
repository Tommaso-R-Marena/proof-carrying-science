# G2: the source gates run before anything from the pull request (proposal; G1 evaluated)

**Status (2026-11-21).** Prepared and tested in throw-away worktrees. **Not applied.** No workflow,
gate file, manifest, tag or ruleset was changed in either repository. G2 is your decision. On the
core, make it before C1's final regeneration (section 5).

## 1. The weakness

CI runs the gates in a way that lets repository files run first:

* the core's required `source-policy` job runs `python -m research.integration_v2.reconcile
  --require-committed` from the repository root, after three steps that run repository scripts;
* the retained-source gate runs as `python scripts/check_reconciled_prs.py`.

So Python looks in the root, or in `scripts/`, before the standard library. A pull request can add a
file that runs before the gate has checked anything. It then forges the gate's report and exits 0,
without changing any gate file.

The dry run (`g2/g2-dry-run.json`, at `2ece33f7`, Python 3.12) planted each of the following and
committed it. Each planted module writes a marker, prints a forged success report and exits 0.

| Vector | Example | Today | With G2 | Flagged by the pre-merge path list |
| --- | --- | --- | --- | --- |
| module named like a gate import, at the root | `json.py`, `argparse.py`, `hashlib.py`, `pathlib.py`, `re.py`, `subprocess.py` | forged | blocked | yes |
| package at the root | `json/__init__.py` | forged | blocked | yes (added 2026-11-21) |
| bytecode without source at the root | `json.pyc` | forged | blocked | yes (added 2026-11-21) |
| compiled module at the root | `json.cpython-312-x86_64-linux-gnu.so` | forged | blocked | yes (added 2026-11-21) |
| shadow of the `research` namespace | `research.py`, `research/__init__.py` | forged | blocked | yes |
| fallback for an import the standard library misses on Linux | `nt.py` (`pathlib` imports `ntpath`, which tries `nt`) | forged | blocked | yes |
| cached bytecode beside the gate | `__pycache__/reconcile.cpython-312.pyc`, unchecked, or "checked" with the **genuine source's hash** | forged | blocked | yes |
| compiled module beside the gate | `research/integration_v2/__init__.cpython-312-x86_64-linux-gnu.so` | forged | refused | yes |
| package beside the gate | `research/integration_v2/reconcile/__main__.py` | forged | refused | yes |
| module in `scripts/` (retained-source gate) | `scripts/json.py` | forged | blocked | yes |
| a script that runs before the gate | `scripts/check_repository_integrity.py` planting bytecode for the gate | forged | blocked | yes |
| an environment variable set by an earlier step | `PYTHONPATH` | forged | ignored | only through the earlier step |
| startup hooks at the root (not vectors) | `sitecustomize.py`, `usercustomize.py`, `probe.pth` | not run | not run | yes or n/a |
| **an edit of the gate itself** | `research/integration_v2/reconcile.py` | forged | **forged: outside G2** | yes |

In this table:

* *forged*: the planted code ran and the gate reported success;
* *blocked*: the planted code did not run, and the gate then rejected the unadmitted file;
* *refused*: the launcher refused before importing anything.

The fallback row matters for the design. A planted `nt.py` defeats a launcher that appends the
repository to the end of `sys.path`. So do `research.py` and `research/__init__.py` (dry run,
`naive_launcher_appending_the_repository`). That is the launcher the earlier note in
`REQUIRED_CHECKS.md` sketched, and it is not what G2 uses.

## 2. The correction

**Core.** In `source-policy`, the gate step moves to right after checkout and setup-python, and
runs isolated:

```yaml
      - name: Exact reviewed combined-source contract
        shell: bash
        run: |
          python -I -B -X pycache_prefix="$(mktemp -d)" - "$PWD" --require-committed <<'PY'
          ...the launcher, 13 lines (g2_isolation.LAUNCHER)...
          PY
```

* `-I`: no script directory or working directory on the path, no `PYTHON*` variables, no user site.
* `-B` and an empty `pycache_prefix`: no bytecode is read from the repository or written to it, so
  every gate module is compiled from its source.
* The launcher refuses any entry beside the gate's sources other than `*.py`, `README.md` and
  `__pycache__`, which is never read. That closes the compiled-module and package cases.
* It then puts on the import path one new directory holding only `research/integration_v2`, a link
  to the gate's sources. No other file of the repository can be imported, so none can replace a
  module the gate imports. It runs the gate unchanged, with `runpy`.

Two control files change. V23 does not: it keeps V22's identity for the workflow, as for the
earlier receiver test repair.

* **`reconcile.py`**, +37 −3 lines:
  * constants: the workflow's original and new SHA-256 (`bb920a82…67cf` → `bf876c35…85fc`) and the
    launcher;
  * `_current_expected` maps exactly that original identity to the new one;
  * the `combined_source` transformation inserts the new step at the new place.
* **`test_reconcile.py`**, +44 lines:
  * three new tests: the step order, the exact-predecessor binding, and the launcher on a stand-in
    gate with planted files;
  * the existing test that freezes every adapted workflow at its reviewed bytes states this one
    change explicitly.

**Site.** `open-pr-reconciliation.yml`, a control file of the site gate, runs
`python -I scripts/check_reconciled_prs.py --site "$PWD"` first, then the tests (one comment and two
reordered lines). The retained-source gate excludes its control files from the tree comparison, so
no other site file changes.

Patches: `g2/proposed-g2-core-workflow.patch`, `g2/proposed-g2-core-controls.patch` (on top of C1's
two files) and `g2/proposed-g2-site.patch`.

## 3. Evidence (dry run, `python -m research.claimcheck_v1_1.governance.prepare_g2`; all as expected)

* **Same verdict on a good tree.** At C1 + G2, G2's step passes (72 PRs). It is read from the
  workflow file with a YAML parser and run with bash as GitHub runs it. It gives the same report as
  the current invocation. The protected suites pass (79 tests; retained-source tests OK).
* **Same verdict on a bad tree.** At the branch head without C1, G2's step fails with the same error
  as the current invocation ("combined tracked file census differs"). Exit codes pass through.
* **C2b still fits.** C1 + G2 + C2b passes and reports the retained source (80 tests).
* **C1 carries G2 only when chosen.** C1 includes G2's control edits only when the source commit
  carries G2's exact workflow. Any other change to that workflow is refused. V23 is byte-identical
  with and without G2.
* **Attacks:** the table above, 23 of 23 rows as expected.
* **Site:**
  * on protected `main`, G2's step passes;
  * with a planted `scripts/json.py`, the current step (tests first, then the gate) is forged;
  * G2's step never runs the planted file and fails ("non-control source bytes … differ").

An independent security review is in section 7.

## 4. What G2 does not cover

* **Edits of the workflow, or of the gate's own sources** (`research/integration_v2/*.py`,
  `scripts/check_reconciled_prs.py`). A `pull_request` workflow runs the pull request's definition, so
  such a pull request still decides what runs (the D2b caveat). Review, the pre-merge check or G1
  covers that. G2 turns an open-ended list of import paths into these few files.
* **Other jobs and workflows** still run pull-request code, as CI does. They cannot change the gate's
  job or its verdict.
* **Trusted components.** The runner image, the pinned actions and the interpreter remain trusted.
* **The site depends on D2b.** On the site, G2 matters once the retained-source check is required.
  Until then that check is advisory.

## 5. Order and cost

* **Core: decide before C1's final regeneration.** The workflow edit is part of the tree C1 admits.
  If you approve G2:
  1. I commit `proposed-g2-core-workflow.patch` on the ClaimCheck branch;
  2. I regenerate C1. `prepare_core_admission` then builds G2's control edits into C1's control
     commit;
  3. I rerun the consistency check, the H1-b tests and the C2b and G2 dry runs, and the independent
     review follows.

  Decided after C1, G2 would need an admission cycle of its own: a new intake, tag and control
  commit.
* **Site:** one control-file commit, at any time; meaningful together with D2b.

## 6. G1 in addition to G2? Evaluation and recommendation

G1 (`g1/gate-definition-guard.*.yml`) is a `pull_request_target` workflow on `main` with a required
check `gate-definition-unchanged`. It fails when a pull request changes a workflow, a gate-defining
file or an import path.

**`pull_request_target` safety.** The proposal is safe as written, and must stay that way:

* GitHub runs the default branch's copy "in the context of the default branch of the base
  repository" (`GITHUB_SHA`: last commit on the default branch). So a pull request cannot change
  what G1 runs for it.
* GitHub warns that running untrusted code on this trigger "may lead to security vulnerabilities …
  cache poisoning and granting unintended access to write privileges or secrets".
* G1 checks out `main`, fetches the pull request by number, and runs only
  `git diff --name-only --no-renames`. It executes nothing from the pull request.
* The values it uses (head SHA, number) come in through `env`, not interpolated into the script.
  The token is read-only (`contents: read`); there are no secrets and no cache.
* Any later edit that builds, tests or imports pull-request code would turn G1 into a privileged
  execution of untrusted code. G1 must never be extended that way.

**Self-modification.**

* A pull request cannot change G1's behaviour for itself.
* A pull request that edits G1's file, or any workflow, is flagged by G1 (`.github`). Merged, it
  would change G1 for later pull requests, which is why that path is watched.

**Required-check behaviour: two points are not documented, so G1 cannot yet be relied on as
enforcement.**

* GitHub lists `pull_request_target` among the events whose job checks "are evaluated for a pull
  request". It does not say which commit those check runs attach to, and required checks "must pass
  on the latest commit SHA".
* It documents same-name collisions only between a check and a commit status ("both must pass"). It
  does not say what happens when two workflows report jobs with the same name: G1's failing job and
  a same-named passing job that a pull request adds. The required check's "expected source" is the
  GitHub Actions app for both.
* Both points need a test in a scratch repository before G1 is adopted:
  * G1's failing check must block the merge of the pull request's head;
  * a later, same-named, passing `pull_request` job must not unblock it.

**Coverage.** G1 is a path list. Its first version missed three of the 19 working vectors above:
the root-level package, the bytecode without source and the compiled module. The G2 dry run found
them, and both G1 proposals and the pre-merge check now list them. A list can only name the
vectors someone has thought of. G2 removes the class from the gate's own job.

**Recommendation.**

* **G2 is necessary.** It closes the import vectors where the gate runs. It does not depend on
  GitHub's undocumented check semantics, and it costs nothing extra if decided before C1.
* **G1 is not necessary now.** You are the only person who can merge. The pre-merge check, a
  read-only `git diff` with the extended list, gives the same coverage as a procedure.
* **Adopt G1 later only if** others gain merge rights, or you want enforcement rather than procedure.
  Run the two scratch-repository tests first, and with G2 in place reduce its list to the
  gate-defining files.
* Do not implement a `pull_request_target` workflow that runs pull-request code. Do not change live
  rulesets for G1.

## 7. Independent review

To be completed by an independent security review (a separate agent under the same restrictions);
results recorded here when it finishes.
