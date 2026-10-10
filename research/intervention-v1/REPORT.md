# Exact intervention planner: executed controls

The planner resolves declared positive-cost Boolean objectives using an ordered-diagram Bellman pass. These 27 first-party analytical controls are reproducible with `python scripts/benchmark_intervention.py --output NEW_DIRECTORY`. Sixteen resolved cases have an independent complete-world oracle through 12 variables; 200 additional seeded test cases compare every cost, count, witness and explanation with an exhaustive oracle. Larger cases use analytic expectations. Time is a single local observation, not a performance guarantee or an external benchmark result.

|Case|Decision|Minimum cost|Optimal assignments|DP node visits|Time (ms)|
|---|---|---:|---:|---:|---:|
|tied-pairs-4|optimal_plan|2|4|8|3.208|
|weighted-pairs-4|optimal_plan|2|1|8|1.145|
|locked-pairs-4|optimal_plan|2|1|8|1.174|
|tied-pairs-8|optimal_plan|4|16|20|1.938|
|weighted-pairs-8|optimal_plan|4|1|20|1.924|
|locked-pairs-8|optimal_plan|4|1|20|1.817|
|tied-pairs-12|optimal_plan|6|64|32|2.604|
|weighted-pairs-12|optimal_plan|6|1|32|2.96|
|locked-pairs-12|optimal_plan|6|1|32|2.505|
|tied-pairs-16|optimal_plan|8|256|48|3.348|
|weighted-pairs-16|optimal_plan|8|1|48|3.34|
|locked-pairs-16|optimal_plan|8|1|48|3.234|
|tied-pairs-20|optimal_plan|10|1024|60|4.174|
|weighted-pairs-20|optimal_plan|10|1|60|4.054|
|locked-pairs-20|optimal_plan|10|1|60|3.964|
|tied-pairs-24|optimal_plan|12|4096|76|4.793|
|weighted-pairs-24|optimal_plan|12|1|76|4.787|
|locked-pairs-24|optimal_plan|12|1|76|4.627|
|already-satisfied|optimal_plan|0|1|3|0.841|
|goal-impossible|no_feasible_plan|None|None|2|0.78|
|lock-impossible|no_feasible_plan|None|None|3|0.814|
|conflicting-context|inconsistent_assumptions|None|None|0|0.796|
|premise-enforcement|optimal_plan|1|1|4|0.876|
|constant-true|optimal_plan|0|1|0|0.586|
|constant-false|no_feasible_plan|None|None|0|0.51|
|node-limit|resource_limit|None|None|0|0.683|
|operation-limit|resource_limit|None|None|0|0.673|

The 24-variable tied-pair case has 4,096 optimal complete assignments of cost 12. The deliberately simple all-true proposal costs 24, giving a real optimality gap of 12. Weighted pairs have one optimal assignment; locked pairs forbid the otherwise preferred choices. This is not a learned-model accuracy experiment. Existing neural weights and scope are unchanged.

Lean 4.28 kernel-checked 12 selected minimum/count propositions with an empty axiom inventory and rejected a false minimum. General diagram compilation, Bellman optimality/count/explanation correctness and Python/JavaScript refinement are outstanding; the single consolidated Aristotle prompt requests them. All receipts retain false scientific-authority and Lean-kernel flags.
