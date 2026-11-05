# PCS formal assurance and refinement evidence

The exact [local evidence seal](evidence/platform-baseline-v1/ARTIFACT_SHA256.json) preserves the inspected source windows, fresh axiom audits, cached build logs, parser checks and bounded differential receipts. This report distinguishes source extraction from reference-model proofs and testing. It does not authorize scientific acceptance.

## Environment and executed proofs

Lean is pinned to 4.28. The default formal build completed 288 jobs and the explicitly selected extended libraries completed 78 jobs, using existing cached dependencies. These are reproducible build checks; job counts are not counts of newly proved theorems. The runtime source-binding audit freshly elaborated its source extraction certificates and audited 54 named theorems. The complete names and axiom sets are in [runtime-refinement.json](evidence/platform-baseline-v1/runtime-refinement.json). All reported axiom sets are subsets of `propext`, `Classical.choice` and `Quot.sound`; some are empty. This is not a proof of those axioms or of the compiler/operating system.

The separate statistics gates freshly elaborated against Mathlib commit `8f9d9cff6bd728b17a24e163c9402775d9e6a365`. Their build environment and exact command outcome are retained in [statistics evidence](evidence/platform-baseline-v1/statistics-gates-fresh.json). Neither a statistical theorem nor a threshold function establishes an empirical improvement without a valid experiment.

| Principal contracts | Actual assurance and assumptions |
| --- | --- |
| `python_intervention_refines_reference`, `javascript_intervention_refines_reference` | Exact extracted intervention arithmetic source windows and typed semantic model; not whole conditional runtimes |
| `language_candidates_exact`, `render_parse_alpha_roundtrip`, `typed_lowering_preserves_denotation` | Restricted typed/parser models, supported grammar, explicit typing/alpha-equivalence; not unrestricted English meaning |
| `omega_execution_replay_correct` | Replay/model theorem; adaptive Python source bytes are not extracted |
| `admitted_library_conservative`, `macro_expansion_preserves_proof`, `research_plan_composes_checked_results` | Reference contracts with checked premises; not a proof of the entire Python memory service |
| `adaptive_fair_search_complete`, `cost_guided_search_optimal`, reuse separation theorems | Explicit reference search/fairness/cost assumptions; no completeness or asymptotic advantage of the deployed heuristic search inferred |
| Assumption-discovery projection, CEGAR, optimum/count/masks and replay theorems | Finite typed reference decision-diagram domain and stated positive-cost/precondition contracts |
| Reward, feedback, shaping, label noninterference and generation authority contracts | Reference learning interfaces; no intelligence, model accuracy or actual RL superiority guarantee |
| `rust_certir_extraction_sound`, `rust_certificate_preserves_eval_expr` | Source-bound supported Rust `eval_expr` and called helpers, sufficient call-depth fuel, well-typed canonical stores; no extracted top-level `eval` loop or native compiler correctness theorem |
| `end_to_end_acceptance_sound`, policy independence | Composition of explicit reference authorities and assumptions; actual runtime components need separate correspondence evidence |

## New source-bound helper and canonical-input boundary

`formal/tools/RuntimeValueType.lean` extracts Rust `Value::ty` at the exact current source window, verifies its token/precedence correspondence, and proves four helper contracts for every value and positive call-depth fuel, including the zero-fuel case. [The fresh result](evidence/platform-baseline-v1/value-type-refinement.json) records source/proof digests and axiom sets. This expands the exact extracted helper coverage without claiming that the Rust type checker or top-level evaluation loop has been extracted.

`formal/tools/RuntimeCanonicalInputs.lean` proves five concrete kernel controls explaining why the existing `Value.WF` hypothesis matters. An externally constructed raw u8 bitvector payload of 256 has a matching type tag but is not canonical: `x OR x` masks it to 0, whereas replacing the expression by `x` returns 256. The archived native Rust at `415a1de40eaeadc366ac2d824c05ee52bb2bd66e` and the Lean transcription agree on that behavior. The existing rewrite theorem requires canonical inputs and is not contradicted. The CLI constructs bitvectors through a masking constructor. New CertiForge work adds `eval_expr_checked`, validates canonical caller-built stores, and routes the top-level `eval` through it; source-bound low-level `eval_expr` is unchanged. Two new Rust regression cases target this guard, and CertiForge PR #3 passed protected CI and merged as `c71e8575db2800b015a9d444f8ed572490f3a871` with the identical tested tree. The new wrapper/top-level routing is not source-extracted or universally refined by the historical Lean proof. This is a real public-enum API precondition witness, not an asserted website/CLI exploit. [The axiom audit](evidence/platform-baseline-v1/canonical-input-axioms.log) and four-width runtime controls retain the exact boundary.

The prior six `PCSVerifiedMemoryBoundary` theorems were freshly audited as reference contracts. They do not establish Python/JavaScript source refinement, authentication or browser correctness. Existing formal sources and principal runtime proofs remain intact.

## Bounded executable comparisons

The expanded seeded campaign compared **1,618** cases in **842.36 seconds**, with no mismatches. The campaign is bound to the archived CertiForge `415a1de40eaeadc366ac2d824c05ee52bb2bd66e` source, before the new checked-entry guard. The full receipt is [compressed JSON](evidence/platform-baseline-v1/runtime-differential-512.json.gz), preserving every input/output and exact source revision/digest. Conditional Python/JavaScript whole receipts are compared; Lean covers modeled semantic/work/diagram fields on valid typed tasks. Malformed validator controls compare Python/JavaScript only. Forge controls execute actual native evaluation and the patched Lean type checker across four widths, arithmetic/comparison/unary operations, lazy selection, arity, bindings, type mismatches and error classes. Normalization abstracts formatted error payloads. Full process-tree CPU/memory was not recorded for this large run.

A separately recorded **130-case** release smoke took **60.44 seconds**, 59.95 child user CPU seconds and 15.05 child system CPU seconds; largest-child RSS was 827,740 KiB. These are child-process measurements, not simultaneous total system memory. A **142-case** historical negative-control campaign deliberately compared the pre-repair Lean Boolean-ordering checker, found and shrank the expected witness, while the current repaired native/reference outputs agreed. It is detection evidence, not a newly discovered production divergence.

The restricted parser differential check passed **1,523** cases. Nested-parentheses regression controls through depth 995 returned unsupported without uncaught recursion. These checks are finite testing; the English rewriting stage, JSON grammar and actual parser implementation are not universally refined by them.

## Reproduction and open obligations

```sh
source scripts/activate_lean_428.sh
python scripts/verify_runtime_value_type.py --help
python scripts/verify_runtime_canonical_boundary.py --help
python scripts/runtime_differential.py --help
python -m pytest -q tests/test_runtime_differential.py
```

Exact recipes and probe source are checked in. The historical full source audit remains separately available under `research/aristotle-runtime-refinement-v1`.

Still open: `python_conditional_refines_reference`, `javascript_conditional_refines_reference`, complete parser/English rewriting extraction, `adaptive.py` source binding, full Rust top-level loop and type-checker extraction, compiler/native executable correspondence, cryptographic primitives, serialization/authentication implementation refinement and browser behavior. Numerical scientific adapters establish bounded Python predicates and signed replay, not kernel-certified empirical or clinical validity. Resource exhaustion cannot grant success.
