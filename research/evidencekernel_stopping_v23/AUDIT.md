# Adversarial findings and unresolved assurances

**Scope:** research-only bounded finite experiment. The production PCS authority and Lean checker were not modified.

| Attack / issue | Defense or observed outcome |
| --- | --- |
| Report-based enrollment stopping ignored | Model uses the unconditional distribution over *all* terminal paths and all stop times, not a fixed-length randomization distribution |
| Counterfactual report differs from scientific outcome | Enumerates separate potential-report and potential-truth schedules; maximizes p over their compatible pairs |
| Post-hoc truncation of recorded enrollment | Rejects premature stops and histories continuing after an obligated stop |
| Replaced assignment, report or scientific outcome | Rejects changed evidence when externally retained evidence digest remains pinned |
| Changed preregistration | Rejects changed protocol when externally retained protocol digest remains pinned |
| Malformed schema, floating-point JSON or duplicate keys | Python/Node.js strict parsers reject them |
| Unenrolled units silently omitted from causal estimand | Registered-population ATE uses **all n** potential outcomes, not the observed t units |
| Naive repeated fixed-horizon p-value peeking | Independent seven-unit sharp-null counterexample: nominal 5% test rejects 8/128=6.25% under repeated inspection; supported finite-state policies have a different, explicitly modeled stop rule |
| Biased conditional randomization, hidden study starts, invented external timing or measurements | **Not solved** by this implementation; external witnessing, calibration and real experimental validation required |

Exhaustive small-model tests check probability normalization and fixed-world superuniformity. Additional tests verify that worst-case robust p-values dominate the true-world exact p-values for selected small designs. Python/Node.js differential checks are deterministic. All examples are synthetic, and matching independent implementations are not substitutes for a formal proof or external physical validation.

**Release decision:** suitable for an isolated draft research PR only. Do not merge into production scientific authority, use to authorize physical clinical/biological decisions, or represent its conditional statements as a wet-lab result.
