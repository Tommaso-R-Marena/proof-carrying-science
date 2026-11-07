# Source-grounded scientific semantics, experimental v3

PCS reads a scientific project, shows what its files say, checks supported
mathematical and computational statements, and exports a review you can inspect
and replay. It does not certify that a paper's scientific conclusions are true.

This isolated research branch builds on unchanged, unmerged draft PRs199–202.
There is no production authority change, deployment or model promotion.

## Try a project

From the repository root, with Python3.12.14 and the existing locked research
dependencies installed:

```bash
source scripts/activate_lean_428.sh
python -m research.scientific_semantics_v3 review path/to/project.zip \
  --output /tmp/my-pcs-review --check
python -m research.scientific_semantics_v3 replay /tmp/my-pcs-review
```

Open `/tmp/my-pcs-review/review.html`. Read a proposed statement, open its exact
source quote, and inspect what was checked. The page also lists unsupported
files and open questions. Omit `--check` to inventory and interpret without
authorizing computations. Output directories must be new. A directory works in
place of a ZIP. Imported code never runs and uploads never become training data.

Optional `--cache /tmp/host-private-pcs-cache` reuses the unchanged parent's
authenticated check cache. New semantic checks are inexpensive and run fresh;
independent replay ignores caches. Host integrity remains an assumption.

## What is implemented

- Exact-byte intake and format adapters from PR201, and original PR202 checks.
- Typed source declarations and reported quantities, explicit quantity roles,
  scoped identifiers, literal biological names, declared units/scales, rational
  equations, dependencies, domain conditions and blocking meaning obligations.
- Real SBML/MathML and NIST regression interpretation. Static Python expressions
  and a narrow set of explicit document fields are supported. Arbitrary scientific
  prose, causal reasoning and empirical adequacy remain unsupported.
- Independently reparsed source/declaration checks and finite numerical
  reproduction from published observations and fitted coefficients. Rational
  interval enclosures distinguish printed rounding from statistical uncertainty.
- Deterministic and learned retrieval ablations; the configuration selected on
  development data is TF-IDF over combined source spans and document windows.
  Select its mode/pool explicitly in the compatibility API. Retrieval relevance
  and symbolic similarity grant no verification authority.
- Snapshot-only interpretation, bounded worker processes, independent replay,
  adversarial regression evidence, and a Lean proof of a domain-preserving
  expression rewrite with explicit standard-axiom audits.

`SEMANTIC_SCHEMA.md`, `ERROR_ATLAS.md`, `RETRIEVAL_ANALYSIS.md`,
`NUMERICAL_REVIEW.md`, `ADVERSARIAL_REVIEW.md` and `INTEGRATION_AUDIT.md` give
the actual contracts, failures and limits. `REPORT.md` records final measurements.

## Reproduce development

Use the unchanged `requirements-build.lock`, `requirements-dev.lock`,
`requirements-prover.lock` and the exact SciPy wheel lock
`research/scientific_understanding_v2/requirements-numeric.lock`.
NumPy/SciPy support the inherited numerical checks. Small new checks use the
standard library. No GPU or paid inference API is required.

```bash
source scripts/activate_lean_428.sh
python -m pytest -q research/scientific_intake_v1 \
  research/scientific_understanding_v2 research/scientific_semantics_v3/tests
python -m research.scientific_semantics_v3.error_atlas --check
python -m research.scientific_semantics_v3.assurance
python -m research.scientific_semantics_v3 benchmark --split development \
  --output /tmp/pcs-semantics-development
```

Final evaluation requires `--split final --allow-final --software-sha256 SHA`,
where SHA is the digest of the canonical pre-final `software-freeze.json`.
Use the archived frozen software when replaying historical packets: runtime
source/context mismatches must fail rather than silently accepting old verdicts.
Results, sources and references are now exposed and are diagnostic material for
future work, never a fresh held-out test a second time.

## Evidence boundaries

Source recognition, algebraic equivalence, numerical reproduction, Lean
mathematical truth and empirical scientific validity are separate results.
Rational-function equality alone does not preserve domains, units, experimental
conditions or scientific meaning. All scientific meanings remain open for review.

Annotations were independently prepared by another AI agent from source bytes,
without interpreter predictions. They are internal AI-assisted references,
requiring qualified human expert adjudication. There is no external scientific
validation or claim of general scientific understanding.

The worker uses process, time, memory and file limits. It is not a complete OS
sandbox, immutable storage boundary or protection against a hostile host. Exact
manifest hashes identify packets; they do not independently authenticate authors.

See the prospective source freeze for licensing and source limitations. BioModels
encodings have CC0 notices. The NIST reference data are pinned lmfit mirrors;
direct NIST access returned403 and byte identity with NIST was not checked today.
The biological inputs are published model encodings, not independent wet-lab data.
