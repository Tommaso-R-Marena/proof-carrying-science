# Source-bound conditional runtime correspondence — status report

## 1. Closed: `python_conditional_refines_reference`

**Statement** (`PCSConditionalRuntime/PyMain.lean`, namespace `PCSCR.Py`):

```lean
theorem python_conditional_refines_reference (ext : Ext) (dg : T → String) {names : List String}
    (hnd : names.Nodup) (tj : T) (t : CTask names.length) (htask : TaskDen names tj t) (lim : Limits)
    (hlv : lim.valid = true) (hval : ValidateAccepts ext tj) (hdg : DigestOK ext dg) :
    ∃ v h, Eventually (fun k => pyRunCheck ext k tj (limT lim)) (.ok v h) ∧
      (∀ k, pyRunCheck ext k tj (limT lim) = .fuel ∨ pyRunCheck ext k tj (limT lim) = .ok v h) ∧
      ∃ fu, readback fu h v = some (receiptT names tj dg (check t lim))
```

Meaning: for every JSON task `tj` that denotes a typed conditional task `t` over distinct
declared names (`TaskDen`: fields are read by key, so key order and extra keys do not matter)
and every valid limit pair, the extracted current `check(task, limits)` run in the heap
semantics on freshly allocated inputs

* returns one and the same `ok v h` for every sufficiently large interpreter fuel;
* with any fuel returns either `fuel` (interpreter exhaustion — claims nothing) or exactly
  that `ok v h`;
* `v` reads back to the JSON receipt of the Lean reference `PCSDD.check t lim`, field by field
  and in insertion order: `format`, `checker`, `original_task`, `task_sha256`, `limits`,
  `decision`, `context_example`, `counterexample`, `unsat_core`, `core_necessity_witnesses`,
  `diagram` (all nodes, `source`, `candidate`, `context`, `difference` roots), `limit_reached`,
  `scope`, `pcs_authority`, `lean_kernel_checked`, `work` (`bdd_nodes`, `apply_calls`,
  `ast_visits`, `witness_steps`) and `receipt_sha256`.

This covers successful runs (inconsistent / equivalent / counterexample) and runs that raise
`ResourceLimit` (decision `resource_limit`, partial results reset to `None`, the reached limit
and the counters at the point of exhaustion), because the proof is a case analysis on the
reference `PCSDD.pipeline`. The semantic content of the reference receipts (inclusion-minimal
unsat cores, necessity witnesses, lexicographically least disagreement witness, resource
exhaustion establishes nothing) is proved separately in `PCSDecisionDiagram/Conditional.lean`
(`check_inconsistent`, `check_equivalent`, `check_counterexample`, `check_resource_limit`).

**Axioms** (printed on every build by `PCSConditionalRuntime/PyAudit.lean`):
`propext`, `Classical.choice`, `Quot.sound`. No `sorry`, no `native_decide`, no new axioms.

**Explicit assumptions (contracts of unextracted callees).** `validate` and `digest` are not
extracted (they are recorded as opaque segments in the whole-file certificate). The theorem
assumes only:

* `ValidateAccepts ext tj` — `validate` accepts (every heap copy of) the task and returns its
  argument unchanged;
* `DigestOK ext dg` — `digest` returns `dg` of the JSON value of its argument without heap
  effects. The receipt digests are stated in terms of this same `dg`.

## 2. Source binding chain

| step | Lean | checked by |
|---|---|---|
| exact file lines of the current `conditional.py` (`CURRENT_RUNTIME_SOURCES.json`, SHA-256 `4045bf1d…22bf1`) | `conditionalPySrc` (`source_lines%` elaborator reads the archived file) | elaboration |
| whole-file segmentation; every extracted segment renders byte-for-byte; precedence/bracket discipline | `conditional_py_source_bound` | kernel (`decide`) |
| lowering of the concrete syntax into the heap semantics; program table resolving `check`'s callees by name (`exact`, `evaluate`, `Diagram.__init__/node/apply/compile/conjunction/world/work`, `ResourceLimit`, externs `digest`, `validate`) | `conditional_py_lowers` | `rfl` |
| module initialisation (constants, `DEFAULT_LIMITS`) | `py_init_result` | `rfl` |
| run of `check` | `pyRunCheck` = `run (pyCtx ext) k "check" …` | definition |

## 3. Proof structure (all in `PCSConditionalRuntime/`)

| file | content |
|---|---|
| `Semantics.lean`, `Mono.lean`, `EnvKeep.lean` | heap semantics (classes with mutable fields, tuple-key dictionaries, recursive methods, `while`, `for`, exceptions, `try/except … as`), fuel monotonicity, local-store frame rule |
| `PyNode`, `PyApply`, `PyCompile`, `PyConj`, `PyWalk`, `PyWorld`, `PyEval` | method simulations against the reference manager (`MRel`: unique table, memo cache, node list, counters) |
| `PyCheckPrefix` | `deepcopy`, `validate`, limit checks, `Diagram(...)`, initial result dictionary |
| `PyPrem`, `PyShrink`, `PyWits`, `PyIncons` | premise loop, core shrinking, necessity witnesses, inconsistent branch |
| `PyDecided`, `PyCex`, `PyReport` | decided branch, disagreement report, `result['diagram']` |
| `PyTry` | the body of `try` against `PCSDD.pipeline` (success and `ResourceLimit`) |
| `PyHandler` | `except ResourceLimit as error:` handler |
| `PyTail` | the `try` statement, `manager.work()`, `digest(result)`, `return` |
| `PyReceipt` | the written fields equal `receiptT … (PCSDD.check t lim)` |
| `PyInput` | shape of the deep copy of an accepted typed task |
| `PyMain` | `check_run` and `python_conditional_refines_reference` |

Independent runtime comparison (a test, not a proof): `runtime_tests/conditional_py/` with
`tools/PyConditionalCompare.lean`; log in `build_logs/runtime_compare_conditional_py.log`
(3 × 1500 random cases, all exactly equal).

Build: `lake build PCSConditionalRuntime` (log `build_logs/conditional_runtime_python_build.log`).

## 4. Closed: `javascript_conditional_refines_reference`

**Statement** (`PCSConditionalRuntime/JsMain.lean`, namespace `PCSCR.Js`):

```lean
theorem javascript_conditional_refines_reference (ext : Ext) (dg : T → String) {names : List String}
    (hnd : names.Nodup) (tj : T) (t : CTask names.length) (htask : TaskDen names tj t)
    (hb : JsTaskBounds t) (lim : Limits) (hlv : lim.valid = true) (hval : JValidateAccepts ext tj)
    (hexact : JExactOK ext) (hint : JIntegerOK ext) (hdg : DigestOK ext dg) :
    ∃ v h, Eventually (fun k => jsRunCheck ext k tj (limT lim)) (.ok v h) ∧
      (∀ k, jsRunCheck ext k tj (limT lim) = .fuel ∨ jsRunCheck ext k tj (limT lim) = .ok v h) ∧
      ∃ fu, readback fu h v = some (receiptT names tj dg (check t lim))
```

`jsRunCheck ext k task lim` allocates the task and the options object `{limits}` on the heap
produced by the extracted module initialisation (`js_init_result`, `rfl`) and runs the extracted
current `checkConditional(task, {limits})` of `public/conditional-core.mjs` (SHA-256
`f25a31d5…8c0d`) in the shared heap semantics, dialect `js` (`===` on values / reference
identity, `undefined`, plain-object/`Map` keys, `structuredClone`, `Object.keys`, arrow-callback
lowering, `push`/`at`, `Object.assign` as keyword update, `new Error`, and exact safe-integer
arithmetic: an unsafe integer raises, and the simulation shows this never happens for the
counters `bdd_nodes`, `apply_calls`, `ast_visits`, `witness_steps` or the node identifiers).

The conclusion is the same as for Python: one outcome `ok v h` returned with all large fuel,
every other fuel gives only `fuel` (claims nothing), and `v` reads back to the JSON receipt of
`PCSDD.check t lim`, every field in insertion order (decision, context example, counterexample,
inclusion-minimal unsat core, necessity witnesses, diagram nodes and roots, reached limit with
the `ResourceLimit` message, flags, the four work counters, both digests). The receipt layout
is the same `receiptT` as for Python, so both checkers are proved to produce the same receipt.

**Axioms** (printed on every build by `PCSConditionalRuntime/JsAudit.lean`): `propext`,
`Classical.choice`, `Quot.sound`. No `sorry`, no `native_decide`, no new axioms.

**Explicit assumptions.**

* `JsTaskBounds t` — at most 24 declared names, at most 8 assumptions, at most 128 nodes per
  formula: exactly the bounds the current `validateConditional` rejects beyond
  (`names.length>24`, `t.assumptions.length>8`, `++count>128`). They are used only to show that
  `ast_visits` and `witness_steps` stay below `Number.MAX_SAFE_INTEGER`.
* Contracts of the unextracted callees (`validateConditional` is recorded as an opaque segment;
  `exact`, `integer`, `digest` are imported from `omega-core.mjs`):
  `JValidateAccepts ext tj` (accepts every heap copy of the task and returns its argument),
  `JExactOK ext` (`exact(x, keys)` returns `x` without heap effects when the own keys of `x` are
  `keys`, as in its source), `JIntegerOK ext` (`integer(x, lo, hi)` returns `x` without heap
  effects for an integer in range, as in its source), `DigestOK ext dg` (`digest` returns `dg` of
  the JSON value of its argument; `await` on it is the resolved value).

**Source binding.** `conditional_js_source_bound` (kernel `decide`: whole-file segmentation of the
archived current file read by `source_lines%`, byte-exact rendering of every extracted segment
under the precedence/syntax discipline), `conditional_js_lowers` (kernel check that the
certified extractor `lowerJSegs` produces exactly the program table `conditionalJsModule`,
resolving `checkConditional`'s callees by name: `Diagram.__init__/node/apply/compile/
conjunction/world/work`, `evaluateConditional`, externs).

**Proof files** (`PCSConditionalRuntime/`, mirroring the Python proof): `JsProofBase`,
`JsNode`, `JsApply`, `JsCompile`, `JsConj`, `JsWalk`, `JsWorld`, `JsEval`, `JsCheckBase`
(method simulations, `JMRel`), `JsPrem`, `JsComp`, `JsShrink`, `JsWits`, `JsIncons`,
`JsDecided`, `JsCex`, `JsReport`, `JsTry`, `JsTail` (premise loop, core shrinking, witnesses,
branches, `try`/`catch (e) { if (!(e instanceof ResourceLimit)) throw e; … }`, `m.work()`,
`await digest(r)`), `JsInput` (shape of the structured clone), `JsCheckPrefix` (options default,
`DEFAULT_LIMITS`, clones, `exact`, the `integer` loop over `Object.keys(limits)`, `new Diagram`,
initial receipt object), `JsMain` (`jcheck_run`, main theorem), `JsAudit`.

Independent runtime comparison (a test, not a proof): `runtime_tests/conditional_js/` with
`tools/JsConditionalCompare.lean`; log `build_logs/runtime_compare_conditional_js.log`
(random cases against Node.js running the actual file, all exactly equal).

Build: `lake build PCSConditionalRuntime` (log `build_logs/conditional_runtime_build.log`).

## 5. Remaining obligations (not yet done)

* Extensions 1–4 of the task (current `adaptive.py` / `omega-adaptive.mjs` extraction; language
  tokenizer/parser/candidate loop; Rust top-level `eval`/`Program::check`/`type_of`; carrying
  the authority results to these runtimes): not started.
* The unextracted callees above (`validate`/`validateConditional`, `digest`, and for JavaScript
  `exact`/`integer`) are assumed through the stated contracts rather than extracted.
