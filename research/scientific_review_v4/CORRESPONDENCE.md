# Bounded source correspondence

`correspondence.analyze(interpretation, artifacts)` accepts the v3 interpretation
shape and an in-memory `{relative_path: bytes}` inventory. It returns
`schema_version`, `schema`, `mappings`, `correspondences`, `conflicts`,
`obligations`, and `authority: false`. Every emitted record has
`scientific_equivalence: NOT_ESTABLISHED` and `authority: false`.

A repeated identifier, matching number, equal equation, or similar biological
name does not create a cross-document mapping. This adapter records explicitly
declared correspondence and bounded algebraic consequences; scientific meaning
and empirical adequacy remain open.

## Explicit source pointers

The supported declaration is a whole line in a `.md`, `.txt`, or `.rst` file:

```text
Mapping: implementation.py::response[scope=response] = paper.txt::y[scope=model]
Mapping: implementation.py::x[scope=response] = paper.txt::t[scope=model]
```

`Variable Mapping:`, `Equation Mapping:`, and `Unit Mapping:` use the same
pointer grammar. Identifiers, paths, and scopes are case sensitive. Both files
must be present; pointers use project-relative canonical paths. Scope is optional
when exactly one grounded claim matches the endpoint. Multiple declarations or
roles for the same endpoint produce an open resolution obligation.

The additional narrow sentence form is:

```text
x in implementation.py corresponds to t in paper.txt.
```

Each accepted declaration carries its exact source quote, UTF-8 byte interval,
and SHA256. Referenced claims must also reproduce a nonempty interval of the
current supplied bytes. This module performs no filesystem or network reads.

Mapped equations require an explicit bijective input-symbol mapping covering
every symbol on both right-hand sides. Equal spelling alone does not satisfy
that premise. The existing closed arithmetic IR and bounded rational normalizer
are reused after this explicit renaming. Comparison reports equality on the
common defined domain or distinct rational functions. Original nonzero
denominator conditions remain open. Equality does not establish scientific
equivalence. Unsupported mathematics produces an open obligation.

Explicit mapped declarations with resolved multiplicative units can expose a
dimension or scale conflict. Missing and unsupported unit declarations never
become implicit dimensionless units. A scale conflict concerns the mapped
source declarations; a valid explicit conversion could require further review.

## PEtab configuration API

`parse_project_links(artifacts)` returns a list of records with this public shape:

```json
{
  "config_path": "project/problem.yaml",
  "sbml_files": ["project/model.xml"],
  "measurement_files": ["project/measurements.tsv"],
  "observable_files": ["project/observables.tsv"],
  "condition_files": ["project/conditions.tsv"],
  "parameter_file": "project/parameters.tsv",
  "source": {"path": "project/problem.yaml", "sha256": "...", "byte_start": 0, "byte_end": 100, "quote": "...", "locator": {}},
  "pointer_sources": {"/problems/0/sbml_files/0": {"path": "project/problem.yaml", "sha256": "...", "byte_start": 50, "byte_end": 59, "quote": "model.xml", "locator": {}}}
}
```

`pointer_sources` maps JSON pointers to original scalar intervals, including
quoted delimiters when present. The returned paths resolve relative to the
configuration directory; the pointer quote retains the literal source path.

Only the exact integer `format_version: 1` is accepted. The required top-level
keys are `format_version`, `parameter_file`, and `problems`. Each nonempty
problem requires nonempty `sbml_files`, `observable_files`, and
`measurement_files` lists; `condition_files` and `visualization_files` are
optional lists. Visualization references are validated and source-bound but do
not add a field to the public link record. Other fields are outside this bounded
subset. Quoted `"1"`, boolean values, floating-point
`1.0`, and other format versions are rejected.

JSON objects/arrays, string literals, and bounded integer literals are read by a
small nonexecuting parser that preserves source intervals and rejects duplicate
keys. YAML supports even-space indentation, standard indentless block sequences,
block mappings/lists, flat flow
lists, plain path literals, single/double quoted strings, and comments. It
rejects duplicate keys, anchors, aliases, tags, directives, document separators,
includes, general flow mappings, multiline scalars, ambiguous implicit literals,
tabs, and excessive nesting. PyYAML is not required or imported.

Configuration references must resolve to present entries in the supplied
inventory. Absolute paths, parent traversal, dot/repeated path components,
backslashes, URI syntax, escaped path components, duplicate targets, and
ambiguous file roles are rejected. No network resource is fetched. Candidate
`.yaml`, `.yml`, or `.json` configurations are identified by explicit PEtab
field names; unrelated metadata files are ignored. A malformed candidate raises
`ValueError` from `parse_project_links`; `analyze` records an open configuration
obligation and emits no links from that candidate.

For one configured model, observable formulas bind case-sensitive identifiers
only to unique grounded declarations in that exact model's global scope.
Local reaction parameters cannot supply global observable identifiers. A
measurement `observableId` links only to one configured observable row. Missing
or duplicate rows remain unresolved. Multiple configured SBML models require
further explicit disambiguation.

`observableParameter1` and suffixed PEtab observable placeholders are retained
with an open `petab_observable_parameter` obligation. Measurement-specific
replacement values, conditions, transformations, numerical execution, and
scientific interpretation belong to separate checks. The correspondence layer
does not discharge that obligation merely because the placeholder occurs in a
formula.

## Bounds and fresh verification

The supplied inventory is bounded at 256 files, 1 MB per file, and 16 MB total.
Configurations have at most 8,192 nodes, 16 levels, 64 problems, and 64 files per
role. Output categories and table rows are bounded at 6,000 records. Inherited
closed arithmetic and exact rational normalization bounds apply.

The rebuilt module was verified with a fresh run of:

```sh
/workspace/proof-carrying-science/.venv/bin/python -m pytest -q research/scientific_review_v4/tests/test_correspondence.py
```

Result: **46 passed**. A separate fresh development-source run parsed the Fiedler
PEtab v1 configuration and emitted two source-bound observable formulas and 72
measurement-to-observable links. The two observable-parameter placeholders and
scientific meaning remained open. These results concern the current reconstructed module;
they are not recovered results from the earlier lost environment.
