# Arbitrary-carrier set algebra

The interpreter handles universally bound subsets of an arbitrary carrier, including the empty carrier. Atomic claims compare two set expressions by equality or inclusion. A contract has an ordered conjunction of atomic premises and one atomic conclusion. Expressions include union, intersection, difference, complement, empty and universal sets. Infimum and supremum have independent order-theoretic definitions through all lower and upper bounds. There are no existential set binders, quantifier alternations, global disjunctions, cardinality tests or distinguished points.

## What Lean checks

In `PCS.SetAlgebra`, an expression with `n` bound sets addresses variables by `Fin n`. The translation compiles it to a circuit on the membership bits of a single element. The following results use ordinary classical set algebra, truth tables and extensionality. Evaluating at each point is the usual representation of a powerset as a product of two-element Boolean algebras. Product and subalgebra constructions are standard in universal algebra. The research contribution is the connection between this decision procedure, executable correspondence checks and closed proof receipts. [Burris and Sankappanavar, *A Course in Universal Algebra*](https://www.math.uwaterloo.ca/~snburris/htdocs/ualg.html)

| Theorem | Hypotheses and conclusion | Axiom closure on Lean 4.28.0 |
| --- | --- | --- |
| `compile_preserves` | For every expression, carrier, set environment, point and bit vector agreeing with membership there, the circuit outputs true iff the point belongs to the denoted set. | propext |
| `expression_iff` | For two expressions in the same signature, the membership circuits agree on all Boolean vectors iff the expressions denote equal subsets for every carrier in `Type` and set environment. | propext, Classical.choice, Quot.sound |
| `correspondence_iff` | For contracts of the same arity, the checker accepts iff corresponding premise and conclusion roles have the same relation and both operands have the same extensions under every environment. Premise count and order must agree. | propext, Classical.choice, Quot.sound |
| `validity_iff` | For any contract, a true result on every membership vector is equivalent to validity of the global implication for every carrier in `Type` and every set interpretation. | propext, Classical.choice, Quot.sound |
| `singleton_countermodel` | Given any failing vector, taking each bound set to be the singleton universe or the empty set as indicated satisfies every premise and falsifies the conclusion. | propext, Classical.choice, Quot.sound |
| `function_reference_iff` | For any two binary set expressions, validity of their premise-free equality is equivalent to equality of the corresponding binary functions on predicates, for every carrier in `Type`. | propext, Quot.sound |

A true implication on all singleton models suffices because each *atomic* premise holding globally establishes its local relation at every point. A global disjunction would invalidate this argument. For example, every subset of a singleton is empty or universal, while a two-element set has a proper nonempty subset. The parser rejects this global disjunction.

## Source and proof interface

`set_algebra.parse_english` accepts controlled sentences such as “For all sets A, B and C, if A is a subset of B and B is a subset of C then A is a subset of C.” It requires full input consumption. The pair constructions in “the infimum of two sets” and “their intersection” share the same two anonymous operands. A clause such as “for any two sets, their difference” leaves operand order ambiguous and receives an abstention. Explicitly bound names may be consistently alpha-renamed by position. Duplicate binders, shadowing and out-of-scope variables are rejected. The Python resolver and English interpretation are trusted parts of the implementation.

`set_algebra.check_pair(reference, candidate)` receives two typed contracts. It limits either side to eight variables, eight premises, 128 expression nodes and depth 24. Its Python search proposes a verdict or singleton countermodel by enumerating the at most 256 membership vectors. Its Lean renderer accepts only checked constructors and validated binder positions. Names, prose, benchmark code and model-supplied tactics never enter the Lean program. The receiver rebuilds its private semantics library from the bound source and requires the published Lean compiler revision. It checks the emitted proof with Lean, enforces a declaration-specific axiom allowlist, and replays the resulting object with leanchecker. Each subprocess has a 40-second budget. An infrastructure or resource failure yields UNKNOWN.

A positive validity receipt proves the arbitrary-carrier implication of the rendered contract. A refutation includes the membership vector, and the kernel checks that this exact vector supplies a countermodel. Correspondence and truth are separate fields. A different signature is reported through a kernel-checked arity mismatch. Same-arity differences carry a proof of failed contract correspondence. An extensional correspondence receipt can miss a conceptual change. Replacing “infimum equals intersection” with “intersection equals intersection” preserves both extensions and passes. The regression suite records this result. No receipt validates the intended English meaning by itself.

## External evaluation

The complete public FormL4 Basic split contains 970 rows and 962 distinct prompts. The evaluator gives only `nl_problem` to the candidate and finishes all proposals before projecting any formal reference. It compares the previous controlled parser and this deterministic parser on all 970 English strings with zero demonstrations and model calls. The previous parser abstained 970 times. The new one parsed and elaborated four items and abstained on 966. Rows 498 and 499 received both correspondence and arbitrary-carrier proof receipts. Rows 747 and 758 proved as standalone set statements, but their independently published formal signatures use `Finset α`. Both received formal-reference abstentions. Thus 968 items lacked a corresponding proof against an external reference.

For 498 and 499 the reader accepts a closed signature for equality of binary `Set α` functions and maps four specific operator symbols to typed constructors. It discards the theorem name and proof text. The kernel checks the projected reference. `function_reference_iff` justifies its passage from function equality to pointwise equality. Mapping the external Mathlib symbols to the local set semantics still requires interpretation. The experiment did not build Mathlib or replay the upstream proof text. Source rows were exposed in fragment selection. These counts establish coverage on this release under a declared reference projection. They provide no estimate of blind neural translation accuracy or comparison to PDA's published model protocol. The full population was counted, so there is no sampling interval.

The separate two-point differential check compares all 16,384 one-premise implications formed from 128 atomic predicates on two bound sets with actual powerset semantics. The two procedures agreed on 7,105 valid implications and 9,279 refutations. Every reported refuting vector was tested independently on the two-point carrier as well. This checks the Python forecast and witness mapping. The general theorem and per-receipt kernel replay provide the formal assurance.

## Replay

Run from the repository root with the published Lean 4.28.0 binaries and Python with pytest on PATH. The upstream checkout must contain the pinned Basic data from PDA commit `7f65d2c27e79239d754e08af2de84a4cea58acc7`. The evaluator checks the data digest before reading any record.

```sh
pkg=research/lean_recursive_autoformalization_v1
(cd "$pkg/lean" && lake build PCS.V2.SetOperatorReference && lake env leanchecker PCS.V2.SetAlgebra && lake env leanchecker PCS.V2.SetOperatorReference)
python -m pytest -q "$pkg/tests/test_set_algebra.py"
python -m research.lean_recursive_autoformalization_v1.set_algebra_evaluation /tmp/pcs221-pda/data/FormL4/basic_test.json > /tmp/set-algebra-basic.json
cmp "$pkg/results/set_algebra/forml4_basic.json" /tmp/set-algebra-basic.json
```

[FormL4 upstream release](https://github.com/rookie-joe/PDA/tree/7f65d2c27e79239d754e08af2de84a4cea58acc7)
