# Before/after verification observations

Original heads were tested in isolated detached worktrees. Source/index cleanliness and exact commits appear in evidence/. An original-head PASS is not relabeled as final-head evidence.

Main baseline: first full Python run lacked Lean on PATH (1797 passed,111 skipped,3 failed,10 setup errors). The explicit-toolchain retry gave1880 passed,40 skipped,1 failure because the full PCS.olean had not yet been completed. These were environment/build-precondition problems, not repaired by weakening tests. Several large default Lean jobs exited137 under the9.7GiB local memory limit; exact modules were subsequently built serially with unchanged source. Full production qualification remains mandatory and is tracked separately.

Integrated imported streams at815f97a:330 tests pass after restoring Cargo's pinned local toolchain; the first121 attempt had2 skips and its full8-test retry passed. Other integrated suites: modern PGSI139; frozen PGSI1173; root epistemic49; native intake19 with1 cleanroom case explicitly deferred to its mandatory separate job. These are per-profile suite counts, with inherited overlap; do not sum them as distinct scientific validations.

Real regressions found and fixed: reviewer export ignored an explicitly absent component when a sibling was present; causal action exchange removed the wrong arrows. Numerical incomplete coverage, missing upper-bound witness, and preflight false-success defects were independently reproduced before repair. All original tests remain; focused receiving regressions were added.

First cross-PR run:14 passed,1 failed closed because this checkout lacked the actual V7 certificate build. The final run requires that build and a real production authority; no mock verdict or test skip substitutes for them. Fresh campaigns, full production/Mathlib builds, final cross-PR run and hosted CI are still being qualified at report creation. See current evidence and PR checks for later observations.
