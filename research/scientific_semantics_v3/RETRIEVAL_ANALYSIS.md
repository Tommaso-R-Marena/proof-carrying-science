# Scientific source retrieval: diagnosis and measured alternatives

Retrieval identifies a relevant source passage. It does not establish the truth
of a question, authorial entailment, semantic equivalence, or checker authority.
False questions are included in the relevance benchmark. Finding their source
is useful, but is not evidence that their false conclusions are accepted.

## Frozen PR #202 failures reproduced

`retrieval.py --diagnostic` loads the historical, byte-preserved evidence
packages and reproduces every BM25, TFIDF and neural rank exactly. Historical
results and their original relevance protocol are unchanged. The exposed final
sources are now diagnostic development material, never fresh generalization
evidence.

On those 25 historical final questions, the original candidate pool contains a
relevant passage for only **11/25**: 7/12 Goldbeter questions and 4/13 integration
questions. This limits every ranker before prediction. Original BM25 finds 7/25
at rank one, TFIDF 2/25 and the neural retriever 0/25. Both a missing candidate
and an incorrect ranking contribute zero to the original end-to-end metric.
The original lexical relevance predicate is retained for this diagnostic, even
though the new prospective evaluation uses exact source-span overlap.

The candidate generator excludes unrecognized formats, excludes assumption
records, and can omit an unresolved whole-file record exceeding its 4,000
character validity bound. Thus it often omits prose required by a scientific
question. A retrieval model cannot recover content absent from its candidate
pool. This is separate from neural model quality.

The neural model is a 12,720-parameter mean-pooled supervised dual encoder, not a
JEPA or a scientific language model. It was trained on 96 authored examples from
eight wording families. Its authored held-out top-one result was already below
lexical retrieval, 17/24 versus 24/24. The authentic sources add XML, identifiers,
formula syntax and prose not represented in that small training set.

Actual authentic-source diagnostics show word-vocabulary OOV fractions of
48–62% for queries and 54–63% for candidate text. Unknown words still receive
hashed character features; these percentages do not mean the entire input is
discarded. The tokenizer lowercases identifiers and splits alphanumeric names,
while mean pooling loses scope, order and expression structure. Neither this
architecture nor its objective ensures exact quantity or identifier matching.

On the historical final Goldbeter case, query-pair cosine similarity averages
0.586; integration averages 0.654. The vectors vary substantially, so the data
do **not** establish complete representation collapse. These are transfer
symptoms and plausible mechanisms, not a causal attribution experiment.
Retraining a larger model on the exposed final sources would not repair the
original generalization claim. No source or uploaded document is used here for
training.

## Additive implementation

The new module retains old lexical scoring as an exact baseline and adds:

- Full identifier tokens plus camel/snake components and exact rational spelling
  for numeric retrieval features. NFKC normalization is retrieval spelling only;
  it is never scientific equality. Case-sensitive identifier overlap is a
  separate hybrid feature.
- Bounded, query-independent source windows that prefer line boundaries, overlap
  by 200 characters, and bind the complete original SHA256 and exact text span.
  They cover unsupported textual formats without executing code or interpreting
  their meaning.
- An optional combined pool retaining narrow, already parsed PR #202 spans and
  the full-source windows, deduplicated by source identity and span.
- Reciprocal-rank fusion of raw BM25, raw TFIDF and normalized BM25, plus explicit
  identifier overlap. These components all see the same pool.
- A narrow symbolic ranking feature for explicit equations. It reparses literal
  equations in candidate text, ignores forged expression metadata, and uses the
  existing exact rational-function comparator. Denominator obligations remain
  open and scientific-context equivalence is always `UNRESOLVED`.
- A new evaluation function with exact original SHA, relative source path,
  literal quote, and annotated UTF-8 byte offsets where supplied. Matching
  algebra or common words cannot replace source provenance.

`rank(query, candidates, mode=...)` returns aligned finite scores. Modes are
`bm25`, `tfidf`, `normalized_bm25`, `hybrid`, and `neural`.
`candidate_pool(inventory, pool=..., interpretation=...)` supports `structural`,
`v2`, and `combined`. The latter two require an existing PR #202 interpretation.
`evaluate_references(refs, inventory, mode=..., pool=..., interpretation=...)`
is evaluation-only; references never enter the ranker or candidate generator.

## Development ablations, not final evaluation

The new development sources and independent internal annotations were frozen
before these measurements. They contain 28 relevance questions: 15 for the
Kholodenko MAPK project and 13 for NIST Hahn1. Counterquestions are included.
The same candidate IDs and matched pools are used for every method within a
row group. Between-pool comparisons include an explicit coverage intervention.

| Pool | Candidates, MAPK/Hahn1 | Coverage | BM25 | TFIDF | Normalized BM25 | Hybrid | Neural |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Original parsed spans | 69 / 7 | 12/28 | 4/28 | 6/28 | 7/28 | 9/28 | 0/28 |
| Full-source windows | 111 / 23 | 28/28 | 10/28 | 11/28 | 14/28 | 12/28 | 5/28 |
| Combined | 179 / 29 | 28/28 | 10/28 | **16/28** | 13/28 | 12/28 | 5/28 |

Numbers are top-one source retrieval, not semantic extraction accuracy. The
combined TFIDF MRR is 0.6662; combined BM25 is 0.4670 and neural is 0.2555.
Combined TFIDF ranks all 28 questions in approximately 0.184 seconds of measured
ranking time, compared with neural 3.811 seconds in this run. Candidate
generation, reference checking and application end-to-end latency are excluded
from these timing values. No isolated-memory or GPU-utilization result is
claimed.

These measurements favor **combined-pool TFIDF** as a prospectively frozen
deterministic default, with the other methods retained as ablations. They do not
justify neural routing or an RL intervention. Normalization and hybrid fusion
are not universally better: combined normalized BM25 loses fine-grained MAPK
rankings, and adding source windows increases distractors. The negative
comparisons are retained in `evidence/retrieval-development.json`.

The exposed old final also improves diagnostically under some changes:
hybrid ranks 10/25 on its original pool, and 14/25 on the separate source-window
pool, versus BM25 7/25 and 10/25 respectively. These are post-exposure
measurements with a different candidate pool in the latter comparison, not
prospective generalization evidence.

## Security and remaining obligations

The inherited neural baseline is now loaded in the new wrapper through a fixed
content hash, a bounded regular-file read with `O_NOFOLLOW`, strict JSON and
shape validation. A caller-controlled sibling digest or restored modification
time cannot admit different weights. Alternate model admission is unsupported.
This preserves the old learned model and exact scores, while avoiding its
mtime-based cache and mutable sibling-digest admission behavior. This is content
integrity checking, not an immutable host security boundary.

Adversarial tests cover Unicode and case collisions, scoped identifiers,
algebraically identical equations in different contexts, fabricated expression
metadata, false questions, forged source hashes, UTF-8 byte-offset errors,
symlink and oversized checkpoints, replaced weights with restored mtime, and
duplicate JSON keys. The tests confirm fail-closed binding and explicit limits;
they do not establish universal robustness against all uploaded documents.

Still unresolved: source-window overlap may retrieve only part of a claim;
cross-file reference resolution is not a learned capability; local scientific
scope must be resolved by the semantic system; equation equality does not prove
compatible units, experimental conditions or biological meaning. The final
prospective benchmark must test the frozen selection before any claim of
generalization can be made. Internal AI-assisted relevance annotations require
external domain-expert adjudication for stronger scientific conclusions.

Reproduce from the repository root:

```sh
python -m pytest -q research/scientific_semantics_v3/tests/test_retrieval.py
python -m research.scientific_semantics_v3.retrieval --diagnostic /tmp/retrieval-diagnostic.json
python -m research.scientific_semantics_v3.retrieval --development /tmp/retrieval-development.json
```

The original neural weights are retained; PyTorch is not required for inference.
