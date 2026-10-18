# Before/after verification observations

Original heads were tested in isolated detached worktrees. Source/index cleanliness and exact commits appear in evidence/. An original-head PASS is not relabeled as final-head evidence.

Main baseline: first full Python run lacked Lean on PATH (1797 passed,111 skipped,3 failed,10 setup errors). The explicit-toolchain retry gave1880 passed,40 skipped,1 failure because the full PCS.olean had not yet been completed. These were environment/build-precondition problems, not repaired by weakening tests. Several large default Lean jobs exited137 under the9.7GiB local memory limit; exact modules were subsequently built serially with unchanged source. Full production qualification remains mandatory and is tracked separately.

Integrated imported streams at815f97a:330 tests pass after restoring Cargo's pinned local toolchain; the first121 attempt had2 skips and its full8-test retry passed. Other integrated suites: modern PGSI139; frozen PGSI1173; root epistemic49; native intake19 with1 cleanroom case explicitly deferred to its mandatory separate job. These are per-profile suite counts, with inherited overlap; do not sum them as distinct scientific validations.

Real regressions found and fixed: reviewer export ignored an explicitly absent component when a sibling was present; causal action exchange removed the wrong arrows. Numerical incomplete coverage, missing upper-bound witness, and preflight false-success defects were independently reproduced before repair. All original tests remain; focused receiving regressions were added.

First cross-PR run:14 passed,1 failed closed because this checkout lacked the actual V7 certificate build. The final run requires that build and a real production authority; no mock verdict or test skip substitutes for them. Fresh campaigns, full production/Mathlib builds, final cross-PR run and hosted CI are still being qualified at report creation. See current evidence and PR checks for later observations.


Subsequent qualification repaired a genuine protected-configuration regression: adding145/146 to the main Lake configuration violated its exact historical identity. The root file is restored, and the research builds now use isolated configurations. An unstable partial full-Python run is retained (1116passed,2failures before interruption); one failure was this configuration defect, the other was cleanroom network transport stripping. Neither is hidden or counted as a passing final run.

The cleanroom now preserves only required OS/proxy/CA transport settings, strips authority/Python/API overrides, installs exact build/dev hash locks, and disables build isolation. It performs no floating pip/setuptools/wheel upgrade. All22 native-intake tests including a real fresh authority rebuild pass, with a poisoned parent authority path. All15 cross-PR tests then pass in27.12seconds with zero skips and real Lean authorization. The complete stable production gate is being rerun at its separately recorded commit.

All10 isolated research theorem environments build and audit successfully. Authored theorem counts and generated public declarations are distinct. The actual final protected/hosted checks must still be inspected at the final head; the initial hosted formal failure was an audit-runner scope defect, now independently repaired locally.


## Completed local qualification

The complete prescribed core gate now passes:1,992 Python tests, zero failures/skips, both25-case foundational and12-case v0.6 adversarial campaigns rejected every attack, actual standard Lean builds/audits passed, and the Mathlib real-analysis bridge plus its3 statistics checks passed. All15 cross-PR tests,22 native-intake tests including a fresh cleanroom, and five new authored bridge theorems pass. The two deliberate false claims are rejected by actual Lean. The exact source profile and executed commands are in evidence/LOCAL_QUALIFICATION.json and retained logs. Earlier failures remain preserved and are not counted as final successes.

All32 source PR heads were rechecked unchanged. V8 remains incomplete. Hosted verification must be assessed on the final PR head/merge SHA through https://github.com/Tommaso-R-Marena/proof-carrying-science/pull/153/checks; this snapshot does not fabricate a future CI conclusion. The PR remains draft for independent review, with no main merge or deployment.
