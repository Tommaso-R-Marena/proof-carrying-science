# Checking a translation against a Boolean contract

A reviewer supplies an ordered list of Boolean inputs, a premise, and a conclusion. A candidate supplies another contract in that signature. The receiver checks the premise and conclusion separately for *every* input assignment. It reports the specific assignment and both evaluations when either component differs. This catches the replacement of “assuming p, conclude p” by “assuming q, conclude q,” even though both conditionals are theorems. It also checks conclusions outside the premise, so a client wanting equality only on admissible inputs needs a different relation.

For an equivalent candidate, a second decision asks whether the candidate conclusion holds whenever its premise does. An accurately translated false claim can therefore receive both `SEMANTICALLY_EQUIVALENT` and `REFUTED`. In this fragment, exhaustive evaluation gives a decision for validity and a concrete falsifier when one exists.

## Input and replay

Use Lean 4.28.0. From this research directory run the following commands.

```sh
(cd lean && lake build PCS.V2.FiniteReferenceFixtures && lake env leanchecker PCS.V2.FiniteReferenceFixtures)
python -m pytest -q tests/test_finite_reference_receiver.py
```

The test corpus exercises the receiver through its file interface. To check another pair, run the following from `lean/`.

```sh
lake env lean --run tools/CheckFiniteReference.lean REFERENCE.json CANDIDATE.json
```

Each file contains one compact canonical JSON object followed by a newline. This example asserts that a Boolean input implies itself.

```json
{"contract":{"conclusion":{"var":{"name":"p"}},"premise":{"var":{"name":"p"}}},"format":"pcs-bool-contract-v1","variables":["p"]}
```

The named grammar supports variables, Boolean constants, conjunction, implication, negation, universal quantification, and existential quantification. Files use precisely the `Named` representation in `lean/PCS/V2/NamedReference.lean`. Free input names must be unique and ordered identically on the two sides. A binder can shadow a name. Scope resolution picks its most recent binding. Documents larger than 16 KiB, more than 10 free inputs, undeclared variables, unsupported constructors and comparisons exceeding the work budget receive `UNKNOWN` (exit 2). A budget of one million formula visits bounds one pass at all assignments using a structural estimate that doubles the contribution of a quantified body. Checking validity uses a second pass on an equivalent candidate. Exhaustive checking costs exponential time in the number of free variables and nested quantifiers.

The receiver exits 1 for a semantic difference and 0 for a corresponding contract. A client assessing theorem validity must also read the `validity` field. Untrusted output cannot authenticate its own reference. The caller selects the reference file independently and retains the exact input files for replay.

## Checked results

| Lean declaration | Result |
| --- | --- |
| `resolve_defined_iff` and `resolve_sound` | A named term resolves exactly when its names are in scope. Its resolved de Bruijn interpretation agrees with the named interpretation for each assignment. |
| `named_counterexample_none_iff` | For two successfully resolved contracts, the absence of a separating assignment is equivalent to agreement of both named premises and both named conclusions on all assignments. |
| `counterexample_some_sound` | The returned assignment refutes componentwise agreement. |
| `falsifier_none_iff` and `falsifier_some_sound` | The conditional is valid under every assignment exactly when the search finds no falsifier. A returned falsifier satisfies its premise and refutes its conclusion. |
| `trace_preserves_correspondence` | When the status vector is recomputed from these comparisons against fixed reference slots, every chain accepted by the branch's existing status gate retains a corresponding candidate at each previously corresponding slot. |

The fixtures include 12 kernel-reduced examples and print the transitive axiom closures of nine named declarations. The reported dependencies are `propext` and, on a subset, `Quot.sound`. The executable regression corpus includes independently authored expected verdicts, quantifier exchanges, name capture, changed premises, and an additional Python interpreter that checks the reported witnesses. It is an authored diagnostic corpus, with no population accuracy estimate.

## Interpretation and limits

The mathematical inputs are explicitly named Boolean contracts. Translating prose into those inputs and choosing the intended interpretation of each Boolean predicate require independent review. Two distinct closed tautologies can be equivalent here even if their subject matter differs; a regression case records that acceptance. The equality of meanings relative to a supplied reference does not by itself measure fidelity to arbitrary English. Measure, cardinality, and topology lie outside the grammar. `VALID_FOR_ALL_ASSIGNMENTS` establishes truth for the declared Boolean model.

The transition theorem applies to a gate supplied with statuses computed by `capability` on a common reference vector. The historical Python status artifacts alone do not establish that premise. The isolated receiver is a research interface. Translating a source text, authenticating its reference and receipt, decoding JSON, executing Lean, and maintaining reference custody retain their respective trust assumptions.

The decision procedure uses classical finite truth-table evaluation and typed de Bruijn indexing. The contribution here is its checked connection to the existing recursive status gate, plus the distinction between premise preservation, conclusion preservation, and theorem validity. There is no measured gain on unrestricted FormL4 translation.
