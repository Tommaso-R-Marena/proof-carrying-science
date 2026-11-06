# Review a scientific project

PCS reads a project's files, proposes source-linked equations and findings, and checks what it can. It separates what the files say, what a computation reproduces, and what still needs scientific judgment.

This is an isolated research prototype stacked on draft PR #201. It does not change production verification or deploy a website feature.

## Try the local upload screen

Use Linux x86_64, Python 3.12, the existing CPU dependency locks, and the additional numerical lock:

```bash
python -m pip install --require-hashes -r requirements-build.lock -r requirements-dev.lock -r requirements-prover.lock -r research/scientific_understanding_v2/requirements-numeric.lock
python -m pip install --no-deps --no-build-isolation -e .
source scripts/activate_lean_428.sh
python -m research.scientific_understanding_v2 serve --output /tmp/pcs-science-session
```

Open the local address printed in the terminal. Choose a ZIP, decide whether to authorize supported checks, and select **Review project**. The review links each proposed statement to its original source. Uploaded code never runs, and the files do not become training data.

The service binds only to loopback. It is a local research interface, not a hardened public upload service or an OS sandbox. Its output directory must be new. No browser or human usability study has been conducted.

## Run a reproducible example

```bash
python -m research.scientific_understanding_v2 demo --output /tmp/pcs-science-projects
python -m research.scientific_understanding_v2 inspect /tmp/pcs-science-projects/biomodels_tyson1991 --output /tmp/pcs-science-review --check
python -m research.scientific_understanding_v2 replay /tmp/pcs-science-review
```

Open `/tmp/pcs-science-review/review.html`. Source statements and numerical results appear separately. Read the scope and assumptions before using a result. Pass `--cache /tmp/pcs-private-cache` to reuse unchanged supported results; cache storage must be outside the input and evidence directories. Replay bypasses cached verdicts.

`inspect` accepts the same directory/ZIP inputs as PR #201. PDF/Office/tabular/notebook/Lean/biological intake remains available through the reused intake package. New interpretation adds bounded MathML/SBML reaction equations, assignment rules, stoichiometry, parameters, initial conditions, arithmetic ASTs, document numerical findings, units, approximation and uncertainty. Unsupported meanings and ambiguous LaTeX scope remain unresolved.

## What is checked

- Exact source-declared numbers, independently parsed from bound bytes. This does not establish their physical meaning or empirical truth.
- Rational source-to-expression comparison on the common defined domain, with denominator obligations preserved. The Python algebra implementation is not kernel-certified.
- Dimensional typing with exact rational scale factors. Missing declarations lead to abstention; no physical time unit is invented for a legacy model.
- Exact stoichiometric conservation certificates, including concrete Lean checks for supported integer matrices. Continuous real-valued trajectories and biological applicability are outside those proofs.
- Supported SBML model dynamics with two pinned SciPy algorithms, explicit tolerances and a bounded horizon. Solver agreement is not a rigorous global error bound.
- Static finite correspondence with the BioModels-generated Octave derivative export. The export is not executed, and this is not full program equivalence.
- Supported numerical documentation examples reconstructed from literal data and approved mathematical operations. Arbitrary doctest code never runs. Iteration counts and printed precision may differ by library version.

Every claim retains a blocking meaning-review status. None receives production scientific authority.

## Scientific evaluation

Four authentic cases are pinned by source hashes and versions before testing: two BioModels cell-cycle models and two SciPy projects. Separate AI agents prepared source-based reference annotations without consulting PCS extraction output. These are independent internal, AI-assisted annotations, not human domain-expert or external validation.

The computational models are CC0; SciPy code/docs are BSD licensed and its 2020 paper is CC BY. Full 1991 biochemical papers are not redistributed without permission; attributed excerpts and publication links are preserved. Reference labels stay outside ingested projects.

A small new scientific retrieval encoder was actually trained on a separate authored corpus. It underperformed lexical baselines. Frozen Proof-JEPA/Safety-JEPA weights are not repurposed for incompatible scientific text. Retrieval scores never become verification or scientific authority.

```bash
python -m pytest -q research/scientific_understanding_v2
python -m research.scientific_understanding_v2.verify_formal --profile dimensions
python -m research.scientific_understanding_v2.verify_formal --profile conservation
python -m research.scientific_understanding_v2.verify_formal --profile sampling
python -m research.scientific_understanding_v2 benchmark --split development --output /tmp/pcs-science-development
# Explicit post-freeze evaluation; never training or model selection:
python -m research.scientific_understanding_v2 benchmark --split final --output /tmp/pcs-science-final
```

See `REPORT.md`, reference provenance, learned-model card, and retained evidence for exact measurements and failures. Use a fresh output directory for every run. Source/toolchain drift requires a successor replay; historical evidence is never rewritten.
