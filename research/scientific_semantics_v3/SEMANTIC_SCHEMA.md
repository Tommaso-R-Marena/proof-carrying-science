# Source-grounded scientific interpretation schema

`semantics.interpret_project(project_dir)` reads a directory into a bounded JSON
sidecar. It returns `artifacts`, `claims`, `symbols`, `dependencies`,
`obligations`, `unresolved`, and a `summary`. It never executes submitted code,
imports a model, calls the production verifier, or reads reference annotations.

Each artifact records its relative path, exact byte length and SHA256. Every
claim records an exact UTF-8 byte interval, source quote, original file hash and
line locator. A BOM and Unicode characters retain their actual byte offsets.
`verify_grounding` independently re-reads source bytes; assertion grounding
requires a nonempty interval. Hashes establish identity under their ordinary
cryptographic assumptions, not immutability or scientific truth.

Claim fields:

| Field | Meaning |
| --- | --- |
| `entity`, `subject` | Case-sensitive source identifier or explicitly normalized quantity. Both fields carry the same value. |
| `kind` | Quantity, equation, unit definition, variable definition, or a limited qualified scientific claim. |
| `relation` | `declared_value`, `reported_value`, `reported_approximate_value`, `equation`, `named_as`, `defined_as`, `unit_definition`, `structural_count`, or `predicts_range`. These remain distinct. |
| `quantity_role` | Parameter, local parameter, initial amount, initial concentration, kinetic law, statistical model, certified parameter, parameter standard deviation, etc. |
| `value` / `exact_value` | Literal reported/declared value; bounded decimal literals have exact numerator and denominator strings. A derived unit scale can be a rational string. |
| `lhs`, `rhs` | The existing closed arithmetic IR. Expressions are parsed as data. Source code is never evaluated. |
| `unit` | Explicit source unit or a quotient of explicit declarations. Null means unspecified, not dimensionless. |
| `unit_resolution` | Exact multiplicative factor, SI7 dimension vector, declaration evidence and supported/unknown status. Affine or unsupported units remain unknown. |
| `scope`, `model_id`, `reaction_scope` | Source/model namespace and local reaction scope. Identifiers do not collapse case or local shadowing. |
| `conditions`, `assumptions` | Explicit structured context and unresolved caveats. They are not proofs that scientific assumptions hold. |
| `symbols`, `symbol_bindings` | Mathematical identifiers and their declaration record bindings. Unknown names remain explicit. |
| `symbol_units`, `symbol_dimensions` | Only dimensions available from explicit declarations, after local shadowing and species amount/concentration semantics. |
| `domain` | Number-system interpretation and denominator nonzero obligations. Algebraic cancellation does not discharge them. |
| `source` | Exact `{path, sha256, artifact_id, byte_start, byte_end, quote, locator}`. |
| `authority` | Always false. |
| `meaning_status` | Always indicates source interpretation requiring scientific review. |

A separate open scientific-meaning obligation is emitted for every claim.
Equations with denominator restrictions have additional open domain obligations.
Exact rational comparison can establish equality on a common defined domain;
`compare_expressions` always returns `scientific_equivalence=NOT_ESTABLISHED`.
It cannot establish equivalent experimental meaning, validity of assumptions,
implementation correspondence, or empirical adequacy.

## Supported interpretation fragments

SBML: explicit compartments, parameters, initial quantities, species identifier
names, units, local parameters, assignment/rate/initial/algebraic rules, reaction
kinetics and exact structural counts. Local symbols shadow global symbols.
Species identifier units account for amount-only flags and explicit compartment
units; initial amount and initial concentration keep their distinct roles.
Selected model-closure defects fail closed: foreign structural namespaces,
duplicate identifiers, reaction/global collisions, conflicting or cyclic rules,
unknown compartments, malformed booleans and rules targeting constant symbols.
This is not a complete SBML validator. Events and advanced SBML semantics are
not numerical execution support.

MathML: the inherited bounded arithmetic fragment plus exact rational numeric
literals. Unsupported numeric bases, numeric units and integer lexical forms do
not silently become dimensionless decimal numbers.

NIST StRD: explicit starting/certified/standard-deviation columns, residual
summary statistics, degrees of freedom, observation counts, bounded multiline
regression equations retaining additive error symbols, and explicit variable
units such as kelvin. Statistical distributions, confidence intervals and
independence assumptions are never inferred from a standard-deviation column.

Documents: explicit delimited arithmetic, narrowly labeled numerical reports and
one explicitly qualified prediction pattern for oscillation-period ranges.
Arbitrary scientific prose, causal interpretation and experimental conclusions
remain unsupported. A narrow rule is capability-limited; it is not a general
scientific language model.

Python: static numeric assignments and direct mathematical return expressions.
Reachability, actual runtime values, imports and program equivalence remain
unverified. Uploaded code never executes.

## Resource and security boundaries

The reader uses directory descriptors, no-follow opens, regular-file checks and
single reads. Symlinks and nonregular files are rejected; source bytes are
hashed before interpretation. Limits are 256 files, 1,024 directory entries, 1 MB per file, 16 MB total,
16 directory levels and 6,000 records per category. Inherited XML/AST depth,
node and expression bounds apply. DTDs/entities are rejected before XML parsing.
These are bounded research defenses, not an immutable trusted root or a full
operating-system sandbox. Runtime replay and separate source admission remain
necessary.
