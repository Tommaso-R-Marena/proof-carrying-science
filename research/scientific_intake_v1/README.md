# Scientific project review (experimental)

Give PCS a folder or ZIP. It preserves the files, organizes their contents, proposes narrow statements, checks the supported ones you authorize, and produces a review you can open in a browser. It does not decide whether a paper's scientific conclusions are true.

This is local research software, stacked on unmerged PRs [#199](https://github.com/Tommaso-R-Marena/proof-carrying-science/pull/199) and [#200](https://github.com/Tommaso-R-Marena/proof-carrying-science/pull/200). It is not a production website feature.

## Try it

From the repository root, use Python 3.12 and the existing dependency locks:

```bash
python -m venv .venv
. .venv/bin/activate
python -m pip install --require-hashes -r requirements-build.lock -r requirements-dev.lock -r requirements-prover.lock
python -m pip install --no-deps --no-build-isolation -e .
source scripts/activate_lean_428.sh
# Ubuntu: sudo apt-get install poppler-utils
python -m research.scientific_intake_v1 demo --output /tmp/pcs-demo
python -m research.scientific_intake_v1 inspect /tmp/pcs-demo/rcsb_1crn --output /tmp/pcs-review --check
python -m research.scientific_intake_v1 replay /tmp/pcs-review
```

Open `/tmp/pcs-review/review.html`. Start with statements contradicted by the files, then inspect each source and assumption. The original files and JSON evidence remain available alongside the review. Use new output paths; existing evidence is never overwritten.

For your own project:

```bash
python -m research.scientific_intake_v1 inspect path/to/project.zip --output /tmp/my-review
# Add --check to authorize the documented closed checks.
# Add --cache /tmp/my-private-check-cache to reuse unchanged checks.
```

The cache must be outside the input and evidence directories and private to the host user. Replay bypasses cached verdicts. An externally recorded SHA-256 of `manifest.json` can be supplied using `replay ... --expected-manifest-sha256 HEX`; without that independent reference, package hashes establish internal integrity, not source origin.

## What it reads

| Input | Implemented scope |
| --- | --- |
| PDF | Actual `pdftotext`, bounded pages, page locators; no OCR, equation recognition or reliable table reconstruction |
| DOCX | Bounded OOXML paragraphs/tables; no macros, external relationships or embedded-code execution |
| CSV/TSV | Strict headers and rectangular rows, row/line locators |
| XLSX | Bounded worksheet cells, shared strings and stored formula metadata; formulas are not executed and cached values are unverified |
| JSON | Strict duplicate/nonfinite rejection and JSON pointers |
| Python | Static AST imports, definitions and literal observations; never imported or executed |
| Notebook | Stored source/output with cell locators; outputs remain unverified and cells never run |
| Lean | Source declarations/imports as data; only bounded closed theorem types are reconstructed independently |
| FASTA | Bounded sequence records, symbols and source lines; alphabet compatibility is not biological classification |
| PDB/mmCIF | Bounded coordinate/sequence/metadata records; no folding, energy, geometry-quality or biological-function validation |
| Safetensors/ONNX | Bounded headers/wire metadata only; no model loading or inference |
| Other model files | Preserved opaque bytes; pickle and arbitrary model loaders are never invoked |
| ZIP | Traversal/collision/symlink/encryption/expansion defenses and original-archive/member replay |

See `adapters.capabilities()` for machine-readable scope. Unsupported files are preserved and reported. Parsing runs in a fixed resource-limited subprocess. This is not an OS security sandbox.

## Statements and evidence

The explicit proposal grammar supports, for example:

```text
PCS-CLAIM: rows(data.csv)=12
PCS-CLAIM: sum(data.csv,y)=123.4
PCS-CLAIM: mean(data.csv,y)=10.5
PCS-CLAIM: sequence_length(protein.fasta,identifier)=46
PCS-CLAIM: coordinate_count(protein.pdb)=327
PCS-CLAIM: sequence_matches_structure(protein.fasta,protein.pdb,A)=true
PCS-CLAIM: ols_optimality(data.csv,ols_experiment.json)=true
PCS-CLAIM: has_field(config.json,/case_id)=true
PCS-CLAIM: imports(analysis.py,csv)=true
For all natural numbers n, n + 0 = n.
For all lists of natural numbers xs, xs appended to the empty list = xs.
```

CSV arithmetic is exact rational arithmetic on finite decimal cells, with no implicit unit conversion or tolerance. Mixed units can still satisfy a numerical sum; scientific meaning remains open. OLS checks independently recompute the declared polynomial design's normal equations and SSE, not coefficient uniqueness or design rank. Their Python implementation is not kernel-proved.

Every candidate retains an artifact hash, source locator/quote, extraction version, assumptions and blocking meaning review. Supported kinds reuse the existing PCS Claim IR and obligation graph helpers. Statistical/unsupported meanings remain research sidecars; no production registry or verifier is extended.

Discovery is deliberately bounded: at most 256 claims, 16 automatic JSON field observations and 32 automatic Lean declarations per artifact. Explicit source and extraction limits are recorded. A complete inventory is not a complete understanding of the project.

## Reproduce and inspect

```bash
python -m pytest -q research/scientific_intake_v1
python -m research.scientific_intake_v1.verify_formal
python -m research.scientific_intake_v1 diagnostics
python -m research.scientific_intake_v1 diagnostics --effects
python -m research.scientific_intake_v1.benchmark --split development --output /tmp/pcs-development
# Final is an evaluation split, never a training or model-selection split.
python -m research.scientific_intake_v1.benchmark --split final --output /tmp/pcs-final
```

Real upstream inputs: RCSB crambin/ubiquitin structures (CC0 data), official NIST Dataplot calibration files (NIST public-domain notice), and pinned Lean4 source (Apache-2.0). Original source URLs, versions, hashes and licensing evidence are retained. PDF/DOCX/XLSX/notebook summaries are explicitly first-party derivatives, not independently sourced papers. Evaluator labels live outside the project. The NIST source substitution and Nat theorem-context discrepancy are recorded rather than hidden.

No new model is trained on imported projects. The actual earlier graph encoders, EMA predictors and RL policies remain intact with their checkpoints and negative results. Diagnostics execute their pinned models on original compatible states and independently replay original-domain effects/proofs. Scientific routing defaults to deterministic checks; requested learned routing currently falls back because those models have incompatible inputs. This provides no evidence of neural benefit for scientific intake.

Read [REPORT.md](REPORT.md), [TRUST_BOUNDARY.md](TRUST_BOUNDARY.md), and [MODEL_CARD.md](MODEL_CARD.md) before interpreting results.
