# Independent internal adversarial review

The independent internal review used authored inputs and actual PCS ingestion,
independent source checks, numerical reconstruction and evidence replay. No
prospective final source or reference was read by this reviewer. This is
AI-assisted internal testing, without external security or domain-expert review.

The latest focused run passes **60 tests**: 9 historical-atlas checks, 36
adversarial checks and 15 independent-check/replay boundary checks. The authored
machine-readable campaign passes **25/25 cases**. These counts have different
denominators: the tests include additional independent assertions and actual
portable-package forgeries, while the campaign retains specific input/output
traces.

The first campaign passed **21/25**. Four actual failures were retained before
repair: a foreign-namespace SBML container admitted declarations; contradictory
assignment rules lacked an unresolved status; a reaction/global identifier
collision lacked an ambiguity status; and an empty source quote passed the
grounding predicate. The hardened successor passes the same 25 cases. Initial
negative evidence was preserved in
`evidence/adversarial-development-initial.json`; successive observations have
separate paths, ending with `evidence/adversarial-development-closed.json`.
These files include exact input hashes, compact outputs and runtime-source
hashes. They are internal regression experiments, not authentic scientific
held-out results.

The review also discovered and repaired these problems:

- A correct source digest and a true but unrelated quotation could obtain a
  positive declaration result. The independent checker now identifies the
  actual XML node with independent Expat byte positions, or the actual NIST
  table/statistic line. Hash integrity alone does not establish assertion
  grounding.
- A proposed global parameter could claim a fabricated model/reaction scope or
  local-parameter role. Independent scope, role and node-kind checks reject the
  mismatch.
- An equation could change its left-hand variable, invert its relation to
  `not_equal`, or introduce a foreign MathML descendant while retaining a
  correct right-hand expression. These are now negative checks. Algebraic
  right-hand equality is insufficient for scientific identity.
- A source constant with more decimal digits than a float could preserve was
  rounded by Python AST construction before exact interval evaluation. The
  numerical checker now retains source literal spelling; an unbound float AST
  literal cannot issue a false exact singleton interval. A regression compares
  the complete 30-digit decimal against its exact rational value.
- The text parser emitted positive reports from explicitly negated prose,
  including “The claim mean: 3 is false,” and discarded “geometric” from a mean
  qualifier. Three exact counterexamples are retained in
  `evidence/adversarial-prose-initial.json`. Bounded field-label parsing now
  abstains on these inputs; actual successor outputs are in
  `evidence/adversarial-prose-hardened.json`.
- A NIST-like marker previously supplied a nonlinear least-squares condition
  without an explicit procedure declaration. The interpretation now derives
  the method from the procedure text and leaves absent methods unspecified.
- Integrity-only replay did not reject fabricated check authority/meaning
  fields. It now rejects those fields even when the attacker rewrites the
  summary, HTML and manifest consistently. Full replay also independently
  rejects changed claims and omitted checks. The tests build and replay a real
  checked package before attacking copies; no mocked verifier is substituted.

Independent XML span hardening initially rejected a valid self-closing parameter
declaration because an Expat end callback pointed after the tag. The positive
control caught that regression, and a quote-aware opening-tag check repaired
it. The test suite requires both attack rejection and acceptance of unchanged
supported declarations.

Other covered cases include uploaded Python that would create a marker and
raise if executed, source instructions impersonating checker messages,
case-sensitive local/global symbol binding, squared scaled litre units,
metres versus molarity, unsupported affine Celsius conversion, malformed
namespaces, duplicate parameters, undeclared dependencies, XML entities/depth,
oversized files, source/quote substitutions, symlinks, integer-power limits,
altered observations, fabricated residual sums and incorrect degrees of freedom.
The old `2N`-equation-count-as-2-newtons failure is also retained as a regression.

## Reproduce

```bash
python -m pytest -q \
  research/scientific_semantics_v3/tests/test_error_atlas.py \
  research/scientific_semantics_v3/tests/test_adversarial.py \
  research/scientific_semantics_v3/tests/test_independent_boundary.py
python -m research.scientific_semantics_v3.adversarial \
  --output /tmp/new-adversarial-observation.json
```

The command refuses to overwrite an existing campaign output. Use the project's
documented Python environment and pinned Lean path for complete parent-stack
replay. No source is executed during ingestion. Numerical reconstruction uses
the closed supported mathematical fragment.

## Limits

The tests establish finite behavior on these inputs, without proving universal
semantic correctness. The source checker certifies only its listed fields;
scientific meaning, domain preservation, empirical validity, statistical
assumptions, physical applicability and Python/Lean refinement remain separate
obligations. A source-bound report can still be an incorrect scientific claim.

No hostile-host isolation, immutable root, external reviewer identity or general
prompt-injection/deception detection is established. A resource-bounded process
is useful failure containment; it is not a complete OS security sandbox.
Manifest binding and independent replay do not authenticate an author's
scientific conclusions. Broader language understanding must be tested on the
new frozen prospective corpus, rather than inferred from successful attacks or
from regrading the exposed historical probes.
