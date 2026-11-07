# Scientific review v4 sidecar schema

`semantics.interpret_artifacts(dict[path, bytes])` is the public snapshot API.
`interpret_project(root)` snapshots files with the unchanged v1 intake
`_walk` reader, then calls that API. The sidecar has the v3 JSON shape:
`artifacts`, `claims`, `symbols`, `dependencies`, `obligations`, `unresolved`,
`summary`, source context hash and `authority: false`. Its schema version is
`scientific-review/v4.0`; the inherited schema is explicitly recorded.
No submitted code executes. Scientific truth, empirical validity and proof
obligations remain open.

The v3 semantic adapters and scalar `exp`/`log` mathematical interpretation are
reused without changing historical files. V4 adds these source-backed field
placements:

| Source declaration | V4 field | Value semantics |
| --- | --- | --- |
| species `hasOnlySubstanceUnits` | `conditions.hasOnlySubstanceUnits` | Explicit `true`/`1` or `false`/`0` becomes a JSON boolean. |
| assignment, rate, initial or algebraic rule | `conditions.rule_type` | Original XML element name. |
| Single-term unit definition | `conditions.multiplier`, `.scale`, `.exponent` | String forms of retained v3 unit terms. Missing source attributes are explicitly labeled specification defaults in evidence. |
| NIST `Predictor Variable (x = pressure)` | Variable definition | The optional source token `Variable` is accepted; pressure does not imply an unstated unit. |

Claims carry `field_evidence`, mapping semantic fields to exact original source
evidence objects. Promoted explicit XML attributes have narrow attribute spans;
rule and derived/default fields retain their complete original element source.
Every evidence object binds path, artifact ID, SHA256, UTF-8 byte start/end and
quote. A transformation marker explains any default or XML-text processing.
Quotes remain original bytes. They never contain a reconstructed XML paragraph.

Every artifact and interpretation record has a new v4 `id` and preserves its
previous `origin_id`. Internal claim, symbol, dependency, obligation and source
artifact references are remapped consistently. IDs identify records, not
scientific authority. Each claim retains an open scientific-meaning obligation;
inherited equation-domain obligations remain open.

## Explicit biological report fragment

Bounded active-voice sentences support `inhibits`, `represses`, `activates` and
`stimulates`, including their singular grammatical forms. A general report has
`kind: scientific_claim`, source noun phrase `entity`/`subject`, relation,
`value`/`object` target, and `quantity_role: biological_relation`. Conditions
retain explicit `negated`, source modality (`may`, `might`, `can`, `could`,
`would`, `should`, or `asserted`) and bounded `when`/`under`/`if`/`in the presence
of` context. An unqualified source assertion still has `authority: false` and
an unresolved scientific-meaning obligation.

A separate narrow grammar supports source-explicit protein/mRNA bindings of
the form `RegA (variable a is the mRNA, variable pA is the protein) inhibits ...
targetB (b, pB describe mRNA and protein)`. It records `kind: interaction`,
protein variable as entity, target mRNA as value, `scope: biological_model`,
`transcriptional_repression` or `transcriptional_activation`, and all original
role bindings. No variable correspondence is inferred from names alone.
Negation, modality and explicit bounded conditions are retained here too.

Model notes use same-namespace XHTML paragraphs in accepted SBML. JATS sources
use `article` roots and same-namespace `p` elements in the bounded supported
namespace set. XML lexical spans come from the unchanged v2 lexical parser.
For matching, paragraph `itertext` removes markup and decodes XML character
references. `source.transformation` discloses that operation, while source quote
and byte offsets cover the exact original paragraph including markup. Foreign
namespace declarations, XML entities/DTDs, duplicate SBML IDs and rejected model
structure cannot authorize claims. Biological role prose such as `A is an
inhibitor of B` is outside this active-voice fragment. Outer negation and
unsupported qualification abstain; instruction-like source prose remains data.
These are deliberately narrow source interpretations, not a general biological
language model or causal inference system.

## Inventory, budgets and validation

V1 intake bounds remain 256 files, 5 MiB per file and 64 MiB total. The v3
semantic interpretation bound remains 1,000,000 bytes per file. Files admitted
by intake but exceeding that semantic bound stay in the inventory with exact
size and SHA256 and an explicit unresolved budget record. Binary or invalid
UTF-8 files similarly stay inventoried and unresolved. They cannot abort the
interpretation of other admitted files. The public snapshot API validates paths,
normalized path uniqueness and byte types before any interpretation.

All claim evidence must have a nonempty original byte span. Only unresolved
records may use empty evidence when no textual interpretation is available.
`schema.validate_interpretation(result, original_artifacts=None)` (also `validate`)
returns `{valid, errors, authority: false, ...}`. With original bytes it checks
artifact hashes and every record/field evidence span; without original bytes it
checks only structural consistency. It also checks remapped references and open
scientific-meaning obligations. Validation is separate from scientific
correctness. `verify_grounding(claim, root)` independently snapshots and checks
a claim against source bytes.
