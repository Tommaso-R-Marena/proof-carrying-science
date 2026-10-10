# Conditional Boolean reasoning

`pcs conditional` checks explicitly chosen logical meanings under actual logical assumptions. It is experimental, bounded, local reasoning and grants no registered scientific authority. Use the website's Assumption Workbench for text entry and interactive world exploration; the Python CLI independently rebuilds its downloaded receipts.

For entailment, compare the original meaning `TRUE` with the claim you want to establish. For example, assumptions `A` and `A -> B` entail `B`; assumption `A -> B` alone does not. For equivalence, enter the two meanings you want to compare. An empty assumption list checks all valuations. A contradictory context returns a conflict rather than accepting vacuous equivalence.

The wire task uses exactly these fields:

```json
{
  "format": "pcs-conditional-boolean-task-v1",
  "variables": ["A", "B"],
  "source": {"op": "true"},
  "candidate": {"op": "atom", "symbol": "B", "args": []},
  "assumptions": [
    {"op": "atom", "symbol": "A", "args": []},
    {"op": "implies", "left": {"op": "atom", "symbol": "A", "args": []}, "right": {"op": "atom", "symbol": "B", "args": []}}
  ]
}
```

Symbols are distinct, sorted uppercase names, zero to 24 per task. Each formula supports atom, true, false, not, and, or and implies, with at most 128 nodes and depth 12. Up to eight assumptions are accepted. The text parser accepts logical words and `!`, `&`, `&&`, `|`, `||`, `->` with explicit parentheses. AND binds more tightly than OR, and implication is lowest-precedence and right-associative. Associative sequences are balanced without changing their Boolean meaning. JSON files have a 256 KiB bound; duplicates and non-finite constants are rejected.

```sh
pcs conditional check task.json --output NEW_RECEIPT.json
pcs conditional verify NEW_RECEIPT.json
```

`check` exit codes: 0 equivalent under satisfiable premises; 1 counterexample; 2 inconsistent premises; 3 resource limit; 4 rejected input/file error. `verify` confirms faithful replay of the recorded outcome and prints its decision; it does not claim a counterexample or resource-limit result is equivalence. Output files must be new. Lower limits can be supplied with `--nodes` and `--operations`, bounded by 4,096 and 100,000 respectively.

Receipts bind the exact original task and limits, record generated BDD nodes/application calls/expression visits/witness steps, and contain either a concrete counterexample, satisfiable context, inclusion-minimal conflict with removal witnesses, or unresolved resource-limit state. Contradictory premises are diagnosed before compiling the compared formulas. Conflict witnesses establish necessity within the listed core, not that removing one premise repairs all original assumptions. Content hashes are not authenticated signatures. The complete receipt is regenerated during replay; a caller can generate a new valid receipt for a new task or limit, but cannot turn an unsupported verdict into a faithful one by resigning a hash.

The engine uses a standard reduced ordered BDD algorithm, not an invented theorem or newly trained model. Ordering can cause exponential growth, and large supported inputs may return a resource limit. The frozen Omega four-variable checkpoints and training provenance remain unchanged. [Measured examples and proof limits](../research/conditional-v1/REPORT.md) include the dense failure case and actual Lean checks of selected statements. General BDD soundness and implementation refinement remain open proof obligations, as does scientific grounding of user-selected meanings.
