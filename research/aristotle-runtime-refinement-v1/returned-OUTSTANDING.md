# Outstanding theorem obligations

None of these is imported as a placeholder.  No `sorry` stands in for any of them, and every
completed module builds without them.

## 1. `python_conditional_refines_reference`

The source is `pcs/experimental/conditional.py` (class `Diagram`: `node`, `apply`, `compile`,
`conjunction` and `world`; plus `check`).

The obligation: for every task accepted by `validate` and every valid `limits`, the extracted
`check` returns the encoding of the Lean reference.  The reference is
`PCSDecisionDiagram.Apply.compile`/`apply` with `PCSDecisionDiagram.Conditional`.  The result
covers the decision, the context example, the counterexample, the unsat core, the necessity
witnesses, the node list, the roots, the `resource_limit` outcome and the work counters
(`bdd_nodes`, `apply_calls`, `ast_visits`, `witness_steps`).  It must hold for both successful
and resource-limited runs.

What is missing: the shared Python/JS semantics (`PCSRuntimeRefinement.Core`) has no classes
with mutable attributes, no dictionaries keyed by tuples (`unique`, `memo`), no `while` loops,
no recursive method calls, and no `raise`/`try ... except ResourceLimit`.  These constructs
have to be added to the semantics and the extractor before a byte-bound certificate for
`conditional.py` can be produced.  `digest` (SHA-256 of canonical JSON) would be treated as an
index, as in the rest of the package.

## 2. `javascript_conditional_refines_reference`

The source is `public/conditional-core.mjs`.  The obligation has the same shape as §1.  It
also needs JS `class`, `Map` and `throw` in the semantics, with safe-integer exactness of the
counters.

## 3. Byte-level extraction of `pcs/experimental/omega/adaptive.py`

`omega_execution_replay_correct` is proved for the existing Lean reference model of the
adaptive search (`PCSOmega.search`) and its independent replay (`PCSOmega.replay`).  A source
certificate binding that model to the bytes of `adaptive.py` (and `omega-adaptive.mjs`) is not
yet provided.

## 4. The English regex stage of `prover/language.py`

`language_candidates_exact` covers the formal body language: tokenizer, Pratt parser, precedence
tables, ambiguity detection and candidate loop.  The preceding English-to-symbol regex rewriting
is not formalized.  Agreement with the actual file was tested on 1523 differential cases
(`tools/difftest/language_diff.log`); that is testing, not proof.

## 5. Program-level `eval` of the Rust CertIR interpreter

`rust_certir_extraction_sound` extracts and proves `eval_expr` and all of its callees.  The
top-level `eval` (arity check, the `for` loop with `let mut store` and `format!` error text) is
not extracted.  It remains covered only by the Lean transcription `PCSForgeRefinement.eval`
(`optimization_sequence_preserves_program`).  Extracting it requires `for`, `let mut`,
`HashMap::insert` and `return` in the Rust-subset semantics.

## 6. Recorded source counterexamples (kept, with patches)

These are not obligations, but they are part of the return package:

* `counterexamples/language_recursion/`: `language.py` lets a `RecursionError` escape for 995
  nested parentheses.  The patch adds a depth guard of 256, and the proved language theorems
  are about the patched parser.
* `PCSForgeRefinement/Counterexample.lean`: the original `Program::check` accepts a program that
  fails on every input (`typecheck_admits_failing_program`).  The proposed repair is the
  patched checker `Program.checkG true` (boolean comparisons restricted to `eq`/`ne`), which
  rejects that program and is the checker used by the certificate checker.
