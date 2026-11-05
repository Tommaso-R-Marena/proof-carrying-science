# Summary of changes for run e693828f-ae95-4029-aeff-54f4e13ee127
I proved `javascript_conditional_refines_reference` for the current `public/conditional-core.mjs`. It checks with no `sorry`, and its axioms are only `propext`, `Classical.choice` and `Quot.sound`. The Python theorem is unchanged and still proved. Extensions 1–4 from the original task were not started this session.

**What the theorem says** (`formal/PCSConditionalRuntime/JsMain.lean`)
The checked code is the extracted current `checkConditional(input, {limits})`, bound byte-for-byte to the archived current source by `conditional_js_source_bound` and `conditional_js_lowers`. It runs in the shared heap semantics using JavaScript `===`, `undefined` and exact safe-integer numbers. For every JSON task that denotes a typed task over distinct declared names, and every valid limit pair:
- The run has a single outcome `ok v h`, returned for every large enough fuel.
- Any other fuel gives only `fuel`, which claims nothing.
- `v` reads back to the same receipt (`receiptT … (PCSDD.check t lim)`) as the Python theorem. That covers decision, context and disagreement witnesses, unsat core and necessity witnesses, diagram nodes and roots, the reached limit, all four counters (`bdd_nodes`, `apply_calls`, `ast_visits`, `witness_steps`), flags and both digests.
- Successful runs and `ResourceLimit` runs are both covered.

**What the theorem assumes**
- **Task size limits (`JsTaskBounds`):** at most 24 names, at most 8 assumptions, at most 128 nodes per formula. These are the limits the current `validateConditional` enforces, but they are stated as a hypothesis rather than derived, because that function is not extracted. They are used only to show the counters stay exact safe integers.
- **Contracts for functions that aren't extracted:**
  - `validateConditional` accepts the task and returns its argument.
  - `exact` and `integer` (imported from `omega-core.mjs`) return their argument with no heap effects on the inputs used here, matching their source.
  - `digest` returns some function `dg` of the JSON value.

**Files added this session** (in `formal/PCSConditionalRuntime/`)
- `JsInput.lean`: the shape of the structured clone of the input.
- `JsCheckPrefix.lean`: the start of `checkConditional` up to the initial receipt object (default options, clones, the `exact` call, the `integer` loop over `Object.keys(limits)`, the `new Diagram` constructor) and the callee contracts.
- `JsMain.lean`: `jcheck_run` and the main theorem.
- `JsAudit.lean`: axiom printout for the main theorem and its supporting results.

The root `PCSConditionalRuntime.lean` now imports the JS files. `lake build PCSConditionalRuntime` in the standalone `formal/` workspace succeeds and prints the axiom audit for both theorems; the log is in `formal/build_logs/conditional_runtime_build.log`. I left `build_targets` empty because the repository root only has a stub lakefile; the real project is under `formal/`. The existing comparison against Node.js running the actual file (`build_logs/runtime_compare_conditional_js.log`, all cases exactly equal) is a test, kept separate from the theorem.

`formal/PCS_CONDITIONAL_RUNTIME_REPORT.md` now has a JavaScript section covering the statement, assumptions, source binding, proof files and what remains. Still open:
- Extensions 1–4: `adaptive.py` / `omega-adaptive.mjs`, the language parser, the Rust `eval` / `Program::check`, and carrying the authority results over to these runtimes.
- The callee contracts above are assumptions, not extracted code.

The Properties table has a new entry for the JavaScript theorem, marked proved. All work is committed.

# Summary of changes for run 70331266-6f21-4032-b9f0-9463628ce366


## Suggested follow-up

I reached this run’s time limit. Send “continue” to pick up where I left off.

# Summary of changes for run de37e8d4-c552-4af4-b9f3-e2fc38cce9ee


## Suggested follow-up

I reached this run’s time limit. Send “continue” to pick up where I left off.

# Summary of changes for run c7ffbf33-38a9-483e-9da6-c98c1cb94fff


## Suggested follow-up

I reached this run’s time limit. Send “continue” to pick up where I left off.

# Summary of changes for run 551c829c-89af-43c5-b62e-4bd91f8e498a


## Suggested follow-up

I reached this run’s time limit. Send “continue” to pick up where I left off.

# Summary of changes for run e175a478-4d5b-45b5-823b-74b580c0a79c


## Suggested follow-up

I reached this run’s time limit. Send “continue” to pick up where I left off.