# Integration and regression qualification

This source/evidence snapshot precedes publication of the final integration PR.
Final head, GitHub-proposed merge SHA, tree identity and hosted run conclusions
must be recorded after execution in the PR description and external handoff.
Previous green parent runs are not final-stack qualification.

## Executed local results

| Scope | Actual result | Evidence |
| --- | --- | --- |
| Existing receiver/history/join baseline | 208 passed,50 subtests passed,0 failures/skips,176.59s | `research/scientific_authority_v2/reports/baseline-configured.*` |
| Initial restored environment | 185 passed,10 failed,13 errors,50 passing subtests | Retained unconfigured log; missing mandatory actual Lean environment, corrected by explicit profile, no changed tests |
| Complete-history replay |17 passed,0 skipped | `research/scientific_history_v2/reports/` |
| Witness |25 unique passed,0 skipped | `research/scientific_witness_v1/reports/`;24 serial and1 actual concurrent Lean race |
| Signed-checkpoint retention delta |1 focused actual-server pass | Witness report; overlaps a prior test, not an extra unique test |
| Coordinator and process-crash qualification |17 passed,0 skipped,385.10s | Coordinator JUnit/log;10 actual process termination windows |
| New formal project |64 authored theorems,133 total namespace closures,standard three axioms only | Fresh independent source builds, complete inventory and logs |
| Independent formal controls |14 kernel-checked countermodel/control theorems | `independent-formal-review/`; no runtime positive-verdict mocks |
| Independent hostile-client campaign |18 expected outcomes passed,39.233s | `independent-review/`; includes2 retained negative security findings |
| Complete inventoried executable profile |2 real admissions, false science rejection, full replay, rollback detection and2-record recovery | `reports/full-profile-demo/`;19,878 dependency pins,54 source pins |

These are separate executed suites, not an invented combined test invocation.
The new workflow runs the combined suite on the final proposed merge tree and
retains its actual JUnit and per-case crash JSON. Its hash-pinned build dependency
installation and crash-report collection do not alter application behavior.

## Preservation

The integration is additions only relative to PR158 at
`7be674df70eb3108c9dbd8b0b97f42a728bde000`. Every predecessor tracked blob and
mode is frozen in `SOURCE_AND_PR_BASELINE.json`. The executable preservation
check rejects any modification, deletion or mode change. The existing source
fences, old authority, Lean statements, archived reports and source-integrity
gates remain unchanged. New formal code is an isolated project; new execution
is research-only. Original PR heads, main and production remain unwritten.

Required final qualification includes the inherited full public workflow,
receiver campaign/pilot and new authority suite on the exact server-proposed
merge tree. Hosted conclusions are not asserted in this pre-publication record.
