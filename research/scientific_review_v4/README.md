# Review a scientific project with v4

PCS captures a scientific project's files, proposes statements linked to their sources, runs supported checks when requested, and exports an HTML review with replayable evidence. A researcher can inspect what a file says, what a computation reproduced, and which scientific questions still need judgment.

This is an additive research sidecar on the unchanged PR199–203 stack. It grants no production authority and admits no training examples. Imported Python, MATLAB, C, notebooks, scripts and native project binaries never execute. Authorized checks run fixed, trusted PCS implementations and host tools, including SciPy, PDF extraction tools and the Lean compiler.

## Prepare the environment

Run these commands from the repository root on Linux x86_64 with CPython **3.12.14**. The inherited hash-locked CPU profile includes NumPy **2.2.6**; the existing numerical lock adds SciPy **1.15.3**. It also installs dependencies inherited from earlier research layers, including PyTorch; v4 review uses deterministic interpretation and does not train a model.

```bash
python3.12 -m venv .venv-review-v4
source .venv-review-v4/bin/activate
python -m pip install --require-hashes \
  -r requirements-build.lock \
  -r requirements-dev.lock \
  -r requirements-prover.lock \
  -r research/scientific_understanding_v2/requirements-numeric.lock
python -m pip install --no-deps --no-build-isolation -e .
source scripts/activate_lean_428.sh
python --version
lean --version
```

The activation script selects Lean **4.28.0**, downloading and checking the pinned official archive if necessary. Keep the same frozen checkout and toolchain for evidence replay: runtime or source-context drift must fail rather than silently accept an earlier verdict. Run `python -m research.scientific_review_v4 --help` from the checkout; the research namespace is not an independently installed application.

## Review your project

Keep the paper, supplements, model, configuration, data, parameter/condition/observable tables and author code together under one project directory or ZIP. Explicit configuration references must resolve within that captured project. Choose a new output directory outside the input project:

```bash
python -m research.scientific_review_v4 review path/to/project.zip \
  --output /tmp/pcs-review-v4 --check --formal
```

A directory works in place of the ZIP. Open `/tmp/pcs-review-v4/review.html` in a browser. For each statement, inspect the source quote or extraction transformation, identifiers, units, conditions, check scope and open obligations. The artifact inventory also shows files that have no supported interpretation. The exported packet contains captured original bytes, so preserve their applicable licenses and sharing restrictions when distributing it.

| Option | Effect |
| --- | --- |
| No check flags | Capture and interpret sources without authorizing check execution. |
| `--check` | Run the fixed supported source, mathematical and numerical checks. An unsupported or failed check remains unresolved. |
| `--check --formal` | Also invoke the actual Lean compiler and theorem/axiom audit for the reviewed abstract integer-residual statements. `--formal` requires `--check`. |
| `--cache /tmp/pcs-v4-private-cache` | Optionally reuse authenticated checks in the unchanged parent layer. The cache must be host-owned and outside both input and evidence directories. V4 checks run fresh. |

The HTML review presents separate evidence classes:

| Evidence | What it establishes within its recorded scope |
| --- | --- |
| Source and semantic interpretation | A proposed declaration, equation, reported value or bounded prose relation is linked to captured source evidence. Matching a source statement does not establish that it is scientifically true. |
| Reproduced computation | A supported calculation ran under the recorded inputs and numerical assumptions. Source-prediction agreement has its own tolerance/result; successful reconstruction can coexist with disagreement. |
| Formal proof | Lean checked the stated abstract mathematical theorem under its explicit assumptions. The v4 residual theorems assume aligned integer pairs; they do not prove the Python join, Fraction arithmetic, ODE solver or scientific interpretation correct. |
| Empirical evidence | Scientific applicability, causal truth and empirical validity need additional domain review and experimental evidence. They remain open in these packets. |

All records retain `authority: false`; no evidence class upgrades the others automatically. Training is denied by default, `training_examples_admitted` remains zero, and this CLI has no training opt-in path. Supplying private or unpublished research does not authorize training on it.

## Replay and share evidence

Replay the exported **directory**, rather than the source project or ZIP:

```bash
python -m research.scientific_review_v4 replay /tmp/pcs-review-v4
sha256sum /tmp/pcs-review-v4/manifest.json
```

Save the manifest digest separately when you create or receive a trusted packet. A later replay can check that saved identity; replace the placeholder below with its 64-character digest:

```bash
python -m research.scientific_review_v4 replay /tmp/pcs-review-v4 \
  --expected-manifest-sha256 SAVED_MANIFEST_SHA256
```

Replay validates packet membership, hashes, captured sources, interpretations and the supported check set. It bypasses the check cache. `--integrity-only` skips the unchanged parent's computational rechecks, while still independently recomputing authorized v4 checks, including the formal check when present. It can therefore still require SciPy and Lean. A packet created without authorized checks can report `INTEGRITY_ONLY` on ordinary replay. Hash consistency and a saved digest identify a packet; authorship or source authenticity needs separate provenance.

## Coverage and limits

Capture of a complete project means its admitted files remain inventoried; it does not mean every file or conclusion was understood. Intake remains bounded to 256 files, 5 MiB per file and 64 MiB total, with a separate 1,000,000-byte per-file semantic budget. Unsupported or oversized material remains visible with unresolved coverage. Arbitrary author programs are preserved as source and are not run to reproduce a study.

The implemented interpretation covers bounded source declarations, arithmetic/equations, selected SBML/MathML, explicit correspondence declarations, PEtab configuration links, and narrow English relations and assumptions. It does not supply general paper comprehension, figure/image understanding, OCR, arbitrary program equivalence or automatic biological variable mappings. PDF/DOCX claims may be bound to derived adapter text; extracted-text offsets are not original PDF/Office byte spans. Review every disclosed transformation.

Conditional ODE reconstruction accepts one explicit PEtab problem with one supported model and each required table, a closed SBML L2V4 reaction fragment, fixed three-dimensional compartments and bounded acyclic assignments. Events, rate rules, delays, functions, preequilibration and other unsupported semantics abstain. Original-model and structural-projection hashes and overrides are disclosed. Two solvers and 80-digit initialization provide finite cross-checks, not rigorous global error bounds or a proof of Python/SBML refinement. Residual sums are unweighted arithmetic on tabulated measurement values; PEtab noise formulas, observable transformations, likelihoods, uncertainty calibration, identifiability and optimality are not established. See [NUMERICAL_REVIEW.md](NUMERICAL_REVIEW.md), [SCHEMA.md](SCHEMA.md) and [CORRESPONDENCE.md](CORRESPONDENCE.md) for the precise boundaries.

The bounded worker and replay checks depend on trusted host tools and storage. They do not form a complete hostile-host or operating-system sandbox. The [integration audit](INTEGRATION.md) describes inherited context, cache and authority boundaries; [UI_REVIEW.md](UI_REVIEW.md) records interface review separately from scientific validation.

## Frozen sources and evaluation references

[RECOVERY.md](RECOVERY.md) records the lost uncommitted RAM workspace and reconstruction from the preserved PR203 baseline `26a8adda12dbb7fd949f14eeddee3d7d870cadd1`. The retained [source freeze](source-freeze.json) binds newly acquired original member bytes; dynamic ZIP container timestamps do not imply identity with the unavailable earlier container. The original frozen metadata accidentally prefixed that baseline with `203`. [source-freeze-errata.json](source-freeze-errata.json) preserves the original record and corrects only that field, with no source-byte or split change.

A second RAM reset lost the original private final annotation payloads. The original [annotation freeze](reference/annotation-freeze.json) is retained; [annotation-freeze-recovered.json](reference/annotation-freeze-recovered.json) explicitly records the successor annotations and exact recovery of the frozen source member identities. It does not claim recovery of the lost annotation bytes. Final source/reference access is separately gated until a software freeze; this guide exposes no final source contents or results.

Reference labels are independently prepared **internal AI-assisted annotations**, not external expert validation or scientific ground truth. The manifests record preparation without consulting new interpreter/checker predictions. The [expert worksheet](reference/EXPERT_REVIEW.md) explains the qualified human review and adjudication still required; a blank or AI-completed worksheet is not evidence of expert validation. Retrieval relevance and reference agreement also carry no verification authority.

To reproduce the public development evaluation, use a fresh output directory:

```bash
python -m research.scientific_review_v4 benchmark --split development \
  --output /tmp/pcs-review-v4-development
```

The final evaluation interface additionally requires `--split final --allow-final --software-sha256` with the digest of the prospective software freeze. `--source-root` and `--reference-root` select explicit corpus locations; they do not bypass frozen identity checks. Keep final materials out of development, training, selection and retuning. Numerical and benchmark results belong to their retained run reports; this workflow guide makes no unmeasured performance claim.

## Primary evidence and later engineering fixes

[REPORT.md](REPORT.md) gives the actual complete-study results and limitations. The primary prospective experiment used frozen commit `f8d9802587e0a2fe9a254ca3b8b8bc41d7f0bf48`, whose runtime matches the pre-final software freeze. The final materials are now exposed; reruns are reproductions, not new held-out experiments. The primary packet archives and exact hashes are listed in [experiment-index.json](evidence/experiment-index.json). Check out that frozen commit, retain the recorded dependency/toolchain context and extract the archive to replay its v4 directories. Context drift must reject the old package; do not edit its receipts or manifests to make it replay under newer code.

A subsequent resource-dispatch fix charges each raw source check its entire source length and stops dispatching checks once a fixed 32 MiB project budget would be exceeded. Every deferred check remains explicitly `UNKNOWN` with its source binding, reason and budget evidence. The full interpretation is retained. The summary's `source_check_budget` distinguishes requested/dispatched/deferred checks and bytes; workflow, numerical and Lean checks have separate execution. This improves bounded availability, not scientific understanding, and does not increase the worker timeout or manufacture positive verdicts. Its exposed-case results are labeled posthoc, leaving the original Smith timeout and final metrics unchanged.

PDF extraction requires the trusted `/usr/bin/pdftotext` executable. On Ubuntu, install it with `sudo apt-get install --no-install-recommends poppler-utils` before reviewing papers. An unavailable adapter remains an extraction error rather than successful scientific interpretation.
