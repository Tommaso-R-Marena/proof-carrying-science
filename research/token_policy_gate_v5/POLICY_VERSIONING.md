# Checked controller updates: progress must survive the version switch

The new executable Lean predicate `PCSPolicyVersioning.updateOK` requires a checked candidate controller, the same declared tool outcomes, safety labels, forbidden effects and goals, a winning current state, and a candidate rank no greater than the carried remaining budget. `VersionedRun` permits a different admissible controller at every tool call.

Eight general theorems prove predicate soundness, an available action at non-goal states, budget decrease at each selected outcome, successor certificate availability, safety and budget preservation over arbitrary adaptive controller sequences, a call-count bound, a terminal certificate and reaching the fixed goal when the budget is used. These statements concern admitted tool calls. They do not force a model, scheduler or tool to act or terminate, and they do not bound endlessly repeated policy-only proposals.

The counterexample uses one physical three-state task.

| State | Controller A rank | Controller B rank |
|---|---:|---:|
| 0 | 2 | 1 |
| 1 | 1 | 2 |
| 2 (fixed goal) | 0 | 0 |

 Action zero toggles states 0 and 1; action one reaches goal 2. Controller A ranks the states `(2,1,0)`, controller B `(1,2,0)`. Both certificates pass the original checker. Alternating A at state 0 and B at state 1 permits action zero forever. `every_rotating_step_locally_checked` and `rotating_never_goal` prove this for every natural-number time, rather than for a sampled prefix. The new rule refuses the increase from the remaining budget 1 to B's rank 2. It also accepts a productive update to B at state 0, with a tighter bound 1 instead of 2 and a selected action reaching the goal.

A second checked controller changes the goal to state 1. Its local certificate is valid; the fixed-task guard refuses it. Local mathematical correctness is insufficient permission to change the objective.

The receiving qualifier additionally constructs a rank-inflated version of the exact fixed laboratory contract used for the recorded Qwen experiment. Its local certificate remains valid; the carried-budget guard refuses the inflation. This is an adversarial contract test using the real-agent laboratory's model, not a new neural inference or model-weight update.

Run with the pinned Lean toolchain and frozen dependencies:

```sh
python -m research.token_policy_gate_v5.policy_versioning /tmp/policy-versioning
```

The qualifier independently compiles all source, prints the exact axiom closures, runs `leanchecker --fresh`, and checks six executable decisions against kernel-proved cases. Its source and import objects are checked before/after. This is a research model checker; it neither promotes a policy nor executes SQL.

The current token-policy receiver keeps its policy fixed, so the alternating-controller example is not an exploit of that receiver. Future deployment must bind the exact decoded candidate, authenticate the current state and budget, protect them against rollback, and commit changes atomically. This module does not implement that storage/authority service. Compatibility is exact ordered-list equality, not a proof that differently encoded tasks are equivalent. The shared task can itself be an inadequate model of the real world. Nothing here proves neural competence, empirical improvement, scientific validity or general alignment.

The implemented qualification checks 18 library declarations and three concrete declarations on the real-agent laboratory contract. The complete proof inventory is in the review bundle’s `NEW_THEOREMS.json`; every closure uses only `propext` and `Quot.sound` where needed. The six executed decisions are: reject the reset, accept the productive change, reject the shifted goal, accept the inflated lab certificate locally, reject its budget increase, and accept the unchanged lab controller.
