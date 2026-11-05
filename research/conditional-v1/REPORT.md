# Assumption-aware symbolic reasoning

PCS now checks whether two explicitly declared Boolean interpretations agree in every world satisfying up to eight logical premises. The bounded experimental checker uses a reduced ordered binary decision diagram (BDD), a standard exact symbolic representation. It accepts zero to 24 declared Boolean variables, at most 128 nodes per formula and depth 12. The existing trained four-variable repair models and their frozen source bindings are unchanged; this component adds symbolic reasoning capability, not new learned weights or a language model.

Unlike descriptive assumption notes in an Omega project, these premises actually restrict the checked context. The checker returns one of four distinct outcomes: equivalent under a satisfiable context; a concrete counterexample satisfying every premise; inconsistent premises with an inclusion-minimal conflict core; or an unresolved resource limit. Contradiction never earns an equivalence result. Removing any one premise in a reported core makes that core satisfiable; each removal has a concrete witness. This is not a guarantee of minimum core cardinality or that removing one premise fixes all original assumptions.

The engine diagnoses contradictory contexts before compiling the queried formulas. It stops after 4,096 generated BDD nodes or 100,000 diagram-application calls. Counts include cache-hit application calls; the receipt also counts expression visits and witness traversal steps. Partial computation never establishes a verdict. Variable ordering can make BDDs grow exponentially; the limits matter even with 24 variables. Hashes identify content, not authenticated scientific authority. An independent verifier rebuilds the entire receipt from its immutable task and declared limits; the browser and Python implementations produce exactly matching diagrams, work counts, witnesses and hashes on the published cases.

## Actual measurements

`evaluation.json` retains 27 first-party analytical examples at 4, 8, 12, 16, 20 and 24 variables, plus constant and dense-ordering controls. They are not participant data, a learned-model evaluation or evidence of external scientific transfer. All examples were actually executed and replayed. Independent exhaustive evaluation additionally checked every valuation for the 13 cases with at most 12 variables; exhaustive evaluation above that bound was not run and no speedup is extrapolated.

The actual local Python 3.12.14 measurements below report checker wall time separately from independent replay. Timings are one observation on this machine, not a controlled hardware performance claim.

| 24-variable case | Result | Generated BDD nodes | Application calls | Checker milliseconds |
|---|---|---:|---:|---:|
| De Morgan identity | Equivalent | 152 | 679 | 3.340 |
| All requirements versus any requirement | Counterexample | 152 | 698 | 3.133 |
| All requirements assumed true | Equivalent under premises | 152 | 746 | 4.033 |
| Opposite premises | Inconsistent | 2 | 15 | 2.849 |
| Dense equality pairing with unfavorable ordering | Resource limit; unresolved | 4,096 | 8,973 | 9.246 |
| Same dense query with opposite premises | Inconsistent before query compilation | 2 | 15 | 2.575 |

A 24-variable domain has 16,777,216 possible valuations; the symbolic checker represents the function rather than enumerating them. The dense case demonstrates the failure boundary as well as the sparse cases' capability. The published report binds the actual Python source SHA-256 `4045bf1d08ec540e5113f1f15212be2901dfeadb4e3898937596abc411022bf1`.

Lean 4.28.0 independently compiled 12 selected equalities under their explicit Boolean premises, including 24-variable statements, and rejected a false equality. The axiom inventory uses only the standard `propext` axiom; no custom axiom, `sorry` or `native_decide` is used. The retained Lean sources and logs are actual compiler outputs. These selected proofs do not prove general BDD correctness or Python/JavaScript implementation refinement, and do not validate scientific interpretations. The browser runs no Lean kernel and grants no registered scientific authority.

## Reproduction

```sh
pcs conditional check task.json --output NEW_RECEIPT.json
pcs conditional verify NEW_RECEIPT.json
python scripts/benchmark_conditional.py --output NEW_DIRECTORY
python scripts/verify_conditional_lean.py NEW_DIRECTORY
```

`check` exits 0 for equivalence under satisfiable premises, 1 for a counterexample, 2 for inconsistent premises, 3 for a resource limit and 4 for malformed input or a file error. `verify` exits 0 when the recorded outcome is faithful, including faithful counterexample/limit outcomes; it does not convert that outcome into equivalence. Output files/directories must be new. Input files are bounded to 256 KiB and duplicate JSON fields are rejected. The text parser supports AND, OR, NOT, right-associative implication `->`, TRUE, FALSE and parentheses; it never executes submitted code.

The website's Assumption Workbench offers text entry, concrete conflict explanations, actual world toggles and independently replayable downloads. An edited input invalidates old evidence. Inputs stay local and clear on reload. No paid service, production migration or fabricated contribution is involved.
