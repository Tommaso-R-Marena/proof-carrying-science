# Source concept roles for two FormL4 identities

FormL4 Basic row 498 says that the infimum of two sets is their intersection. Replacing the infimum with another intersection still gives an extensional correspondence and a proved equality. The opt-in receiver `operator_role_receipts.verify(index, english, formal, candidate)` checks whether the candidate preserves each named operator and its argument positions for rows 498 and 499.

| Row | English left, right | Formal left, right | Declared alignment |
| --- | --- | --- | --- |
| 498 | infimum, intersection | infimum, intersection | Same order |
| 499 | union, supremum | supremum, union | Equality symmetry |

The receiver authenticates the English and published formal text against their exact release hashes. A researcher supplied the side alignment above after reading the two source sentences. The restricted formal reader supplies the two operator tags, binder signature and argument order. A generated Lean theorem `alignment` checks that the aligned contract and the projected published contract have equivalent validity. Equality symmetry justifies row 499's reversal. The editorial assertion that this alignment captures the English remains a trust assumption.

A second generated theorem, `operatorRoles`, checks equality or inequality of the entire candidate AST and the aligned AST. Their binders use typed positions, so consistent alpha-renaming preserves the result. Both operands must retain their operators and apply them to the two bound sets in order. Ordered arguments are a deliberately stricter syntactic convention here, since these operators commute. Different arities fail through an arity inequality. Each positive verdict also requires the original extensional correspondence and proof and an axiom-audited Lean kernel replay. The generated alignment and operator-role proofs had empty axiom closures on all ten replayed receipts. The extensional correspondence and validity proofs used propext, Classical.choice and Quot.sound. The original external candidates regenerate byte-identical extensional proof programs.

## Matched controls

On each row, the original translation and a consistent alpha-renaming passed both checks. Removing the lattice operator, exchanging the two English sides, or exchanging the arguments of the first operator satisfied the extensional checker and yielded a valid theorem each time. The stricter receipt rejected all six mutations. In particular, row 498's “intersection equals intersection” produced a checked AST inequality. A separate exhaustive regression forecast checked all 256 choices of these four binary operators and two ordered or repeated arguments per side on each row. Exactly one positional AST per row met the declared role specification.

All three operator mutations here are extensional equivalences. The concept criterion measures fidelity to these fixed role annotations. It can reject mathematically acceptable paraphrases or reordered commutative terms. Its two source alignments were authored after benchmark exposure. Source substitution, alternate release text and additional operator signatures receive an abstention. This experiment supplies no population estimate of general source fidelity.

From the repository root, use the pinned Lean 4.28.0 and the published Python environment.

```sh
pkg=research/lean_recursive_autoformalization_v1
python -m research.lean_recursive_autoformalization_v1.operator_role_receipts /tmp/pcs221-pda/data/FormL4/basic_test.json > /tmp/operator-roles.json
cmp "$pkg/results/set_algebra/operator_roles.json" /tmp/operator-roles.json
python -m pytest -q "$pkg/tests/test_operator_role_receipts.py"
```

[Extensional receiver and census](SET_ALGEBRA.md) · [Pinned upstream data](https://github.com/rookie-joe/PDA/tree/7f65d2c27e79239d754e08af2de84a4cea58acc7/data/FormL4)
