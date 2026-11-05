# Exact intervention planning

The experimental planner finds minimum positive-cost changes to a Boolean baseline
that satisfy a target, explicit assumptions and locks. It is a decision component
for model or player proposals: `audit_proposal` returns real feasibility, cost and
an optimality gap when the bounded planner resolves the task. An unresolved search
never supplies a gap. Variable meanings and costs are supplied by the user.
These are logical interventions, not identified causal effects.

## Executable protocol

`pcs-intervention-task-v1` has exactly `format`, `problem`, `baseline`, `costs`,
`locked`. `problem` is a `pcs-conditional-boolean-task-v1` task whose `source` is
the target and whose `candidate` is exactly `{"op":"false"}`. Its existing
24-variable, eight-premise and AST bounds apply. Both baseline and costs contain
exactly the declared variable keys. Baseline values are Booleans; costs are
integers in 1–1,000,000, excluding Booleans. Locks are a sorted distinct subset.
A baseline may violate premises; the resulting plan must satisfy them.

The existing conditional engine builds `context AND target`. With an append-ordered
decision diagram, the new Bellman pass visits each node once. Its two terminals
are infeasible and `[0,1,0,0]`. Each other cell is
`[minimum cost, optimal assignment count, mandatory flip mask, possible flip mask]`.
Disallowed locked branches are omitted. A changed variable adds its cost and bit.
At equal minimum costs, counts add, mandatory masks intersect and possible masks
unite. False is chosen before true at a tie, producing the lexicographically least
optimal total assignment in sorted variable order. Skipped variables retain their
baseline: strict positivity makes that completion uniquely optimal. Zero costs
would invalidate the counting rule and are rejected.

`optimal_count` counts distinct *complete assignments*, not diagram paths with
arbitrary values in skipped variables. Mandatory changes occur in every optimal
assignment; possible changes occur in at least one. Neither describes all feasible
assignments. The maximum count is 2^24; maximum cost is 24,000,000. Both are exact
integers in Python and JavaScript.

The planner returns `optimal_plan`, `no_feasible_plan`, `inconsistent_assumptions`
or `resource_limit`. A goal blocked by locks is infeasible, rather than evidence of
contradictory premises. Inconsistent premises are diagnosed before optimization.
The original bounded symbolic checker and its receipt are embedded unchanged.
Partial symbolic work exposes no optimization cells, costs, counts or assignment.
The DP adds at most 4,096 node visits and two branch inspections per node.

The full receipt records the original task, symbolic receipt, all Bellman cells,
assignment, costs, counts and masks. Verification independently regenerates the
entire deterministic receipt and compares canonical content, including scope flags.
Before returning a plan, a direct AST evaluation also checks its target, every
premise, all locks and the reported objective. This guard remains active under
Python optimization. It checks the concrete point; global optimality/count still
depend on the actual diagram/Bellman implementations. General correctness is now proved for the typed Lean reference models; Python/JavaScript refinement remains open.
Hashes identify content; they do not authenticate an authority or prove correctness.

```sh
pcs intervention plan task.json --output NEW_RESULT.json
pcs intervention verify NEW_RESULT.json
python scripts/benchmark_intervention.py --output NEW_DIRECTORY
python scripts/verify_intervention_lean.py NEW_DIRECTORY
```

The CLI reads at most 1 MiB, rejects duplicate/nonfinite JSON and writes compact,
exclusive-create output. Plan exit codes are 0 optimal, 1 infeasible, 2 conflicting
premises, 3 work limit, 4 invalid input/output. Verify exit 0 means faithful replay
of the recorded decision, including an unresolved result.

## Evidence and proof boundary

`tests/test_intervention.py` includes 200 seeded independent complete-world
comparisons, weighted/locked/skipped-variable controls, count and necessity checks,
resigned forgery rejection, limits and actual CLI replay. The benchmark has 27
analytical cases through 24 variables; 16 resolved cases independently enumerate
up to 12 variables. Larger cases use stated analytic expectations, not exhaustive
world enumeration or external benchmark claims. The all-true proposal comparison
is a deliberately simple baseline, not a learned-model performance comparison.

Lean 4.28 kernel-checks 12 selected minimum-cost/count propositions with no axioms
and rejects an intentionally false minimum. This does not prove the general BDD
or Bellman implementation correct. The completed [Aristotle package](../research/aristotle-omega-dd-v1/REPORT.md) proves general reference-model compilation, Bellman optimality/count/mask semantics, lexicographic reconstruction, positive-cost skipped-variable behavior and replay contracts. The release gate checks its kernel controls and complete axiom inventories. Its finite three-language receipt comparisons do not prove implementation refinement. Parser/decoder, serialization/authentication and scientific grounding boundaries remain open.
Existing learned Omega weights, source provenance and four-variable scope are
preserved. This release does not establish a new trained-model accuracy result,
a scientific discovery or algorithmic novelty.
