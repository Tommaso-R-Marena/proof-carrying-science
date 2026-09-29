# Static workflow discovery for PCS v0.6

Status: **implemented on the v0.6 MVP branch; repository gate execution remains pending hosted-runner availability**.

## Goal

Guided project onboarding should not stop at filenames. PCS can now statically inspect
Python scripts and Jupyter notebooks to draft a reviewable artifact-dependency graph
without executing user code.

The intended producer journey is:

```text
existing scientific project
        ↓
artifact inventory + SHA-256 snapshots
        ↓
static Python/Jupyter dependency analysis
        ↓
scientific-check recommendations + workflow graph
        ↓
human review
        ↓
confirm-v06
        ↓
signed workflow provenance in the v0.6 certificate
```

Static workflow discovery is a usability/provenance feature. It is not a theorem about
the program's behavior.

## Format

The discovery report embeds:

```text
pcs-static-workflow-map-v1
```

Each accepted workflow node records a bounded contract with:

- the static workflow inference ID;
- source artifact/path and source kind;
- `static_only: true`;
- `user_code_executed: false`;
- inference confidence;
- imported module names;
- a bounded sample of resolved local file references;
- whether the reference sample was truncated.

The full discovery report can retain a larger reference set than the signed workflow
contract. The certificate-bound proposition is intentionally bounded to protect the
v0.6 16 KiB workflow-contract limit.

## Python analysis

The authoritative CLI path uses Python's `ast` module. It never imports or executes
the inspected script.

Currently recognized static path patterns include:

- `pandas.read_csv/read_json/read_parquet/read_excel/read_feather/read_pickle`;
- direct/imported `read_csv`-style calls when the first path is statically resolvable;
- NumPy `load/loadtxt/genfromtxt`;
- NumPy `save/savetxt/savez/savez_compressed`;
- DataFrame `to_csv/to_json/to_parquet/to_excel/to_feather/to_pickle`;
- built-in `open(...)`;
- `Path(...).open(...)`;
- `Path.read_text/read_bytes/write_text/write_bytes`;
- literal and top-level constant path expressions;
- `Path(__file__).resolve().parent` and repeated `.parent`;
- `os.path.join` and `os.path.dirname(__file__)`;
- common keyword path arguments such as `filepath_or_buffer`, `path_or_buf`,
  `excel_writer`, `file`, and `fname`.

Only statically resolvable local paths are mapped to artifacts. Dynamic paths are
reported as unresolved rather than guessed.

## Jupyter analysis

PCS parses notebook JSON and analyzes code cells as Python without executing cells.

Single-line IPython magics and shell escapes beginning with `%` or `!` are blanked
before AST parsing so they do not unnecessarily prevent analysis of the remaining
Python in the cell. Their commands are not executed and their file effects are not
inferred.

Reference locations retain the notebook cell index.

## Resolution and ambiguity

A literal path is tested conservatively against:

1. the project root; and
2. the directory containing the source file.

If exactly one project artifact matches, the reference is resolved.

If no project artifact matches, the reference stays unresolved.

If more than one candidate interpretation matches, PCS marks the reference
ambiguous rather than choosing one.

If multiple statically analyzed source files appear to produce the same artifact,
PCS records a `multiple_static_producers` unresolved item and removes that artifact
from the inferred output sets. This prevents discovery from generating an invalid
workflow DAG with two claimed producers.

## Confidence

The current CLI confidence convention is:

- **0.98** — source parsed cleanly and every recognized reference for that source was
  statically resolved;
- **0.90** — at least one useful local dependency was resolved, but parsing or
  recognized references remain incomplete.

The default workflow-selection threshold is **0.95**.

Therefore clean AST inferences can enter the draft automatically, while partial
inferences remain visible in `pcs-discovery.json` for human review without entering
the draft workflow by default.

The website Project Mapper uses a lower-assurance regex heuristic rather than a
Python AST and labels its workflow candidates **0.90 heuristic**. With the same 0.95
default threshold, browser workflow candidates are shown but remain unselected until
the user explicitly chooses them.

## Confirmation boundary

A discovery draft remains non-attestable.

`pcs confirm-v06`:

1. validates the draft;
2. re-hashes every selected artifact;
3. changes the intake status from `draft` to `confirmed`;
4. records confirmed artifact hashes/sizes;
5. marks static workflow contracts `human_confirmed: true`;
6. records that confirmation covers only the static dependency inference, not program
   correctness or actual runtime behavior.

`attest-v06` then rechecks the same discovery snapshots before packaging or signing.

Changing a selected script, notebook, input, or output after confirmation therefore
fails closed before the package is signed.

## Signed provenance

Selected source-code artifacts are packaged and signed like other scientific
artifacts.

Their certificate artifact metadata carries:

```text
pcs_discovery_sha256
pcs_discovery_size
pcs_discovery_confirmed = true
pcs_discovery_inventory_commitment_sha256
```

The normalized workflow node contract carries the static inference as an external
proposition. Independent reviewers can therefore inspect both the exact source bytes
and the human-confirmed dependency claim that was made about them.

## Browser Project Mapper

The public local-only Project Mapper provides a complementary workflow view:

- local folder selection;
- local SHA-256 hashing;
- scientific-check recommendations;
- heuristic literal Python/Jupyter file-reference mapping;
- independent include/exclude controls for workflow candidates;
- unresolved-reference count;
- visual selected workflow graph;
- downloadable `pcs-manifest.draft.json` and `pcs-discovery.json`.

The site contains no PCS upload endpoint for these files and the mapper uses no
`fetch`, `XMLHttpRequest`, or `WebSocket` API.

The Python CLI remains authoritative for static source analysis.

## Non-claims

Static workflow discovery does **not** establish:

- that a script was actually executed;
- that the inferred path branch is reachable;
- that dynamic paths have been resolved;
- that source code is correct;
- that a notebook's execution order matches cell order;
- that generated artifacts were really produced by the inferred source;
- arbitrary Python/R/Julia correctness;
- empirical or biological adequacy.

Those are separate assurance obligations.

## Regression coverage

`tests/test_workflow_discovery_v06.py` covers:

- Python literal reads/writes;
- top-level constant path expressions;
- `Path(__file__).resolve().parent`;
- keyword path arguments;
- `Path.open`;
- Jupyter code cells and line magics;
- dynamic path refusal;
- proof that discovery does not execute inspected Python;
- multiple-producer ambiguity;
- merging with PK/PD domain recommendations without duplicate producers;
- explicit human confirmation;
- signed workflow provenance surviving full attestation;
- source-code mutation after confirmation failing before signing.

The suite is part of `scripts/run_v06_contract_gate.py`.
