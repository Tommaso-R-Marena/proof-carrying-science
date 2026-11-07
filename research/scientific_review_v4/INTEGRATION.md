# Five-PR source and runtime integration audit

PR199–203 preserve every protected source identity but do not satisfy the unchanged V22 admission contract on their combined tree. Their research capabilities can be reused behind explicit adapters; they do not form a production scientific authority. The staged proposal in [source_admission_plan.json](source_admission_plan.json) is **PENDING_REVIEW_NOT_IMPLEMENTED**. This audit changes no protected controller, contract, policy, theorem, historical experiment or production authority.

This is an internal, AI-assisted source audit with five executed probes on synthetic inputs and checkpoint copies. It is not external independent validation. The source-bound records, exact duplicate groups, Git path/blob/mode ledger, probe inputs/results and limitations are in [evidence/stack-audit.json](evidence/stack-audit.json). [tests/test_stack_integrity.py](tests/test_stack_integrity.py) reproduces the material boundaries without reading the new heldout corpus or reference annotations.

## Exact source preservation and the V22 boundary

The reviewed five-PR commit is `26a8adda12dbb7fd949f14eeddee3d7d870cadd1`, tree `cb83cd044adbe918cd379b6bf7daf4dea0c01400`. Protected main is `bc78660b5fac857fce3873eb6cda0445d1903da1`, tree `93cc797fabafc30c23730c0399a7be13c8263e94`.

| Census | Protected main | Five-PR tree |
| --- | ---: | ---: |
| Tracked Git paths | 8,047 | 8,556 |
| Historical PR identities required by V22 | 72 | Proposed successor: 77 |
| Changed old Git blobs or modes | — | 0 |
| Deleted old paths | — | 0 |
| Added paths | — | 509 |

The 509 additions consist of 45 Proof-JEPA files, 189 Safety-JEPA files, 64 intake files, 95 understanding files, 111 semantics files and five research workflows. These counts use Git objects, not the physically incomplete recovery checkout. All 8,047 old path/blob/mode identities are preserved.

V22's manifest, `docs/integration/2026-11-05/RECONCILIATION_V22.json`, retains SHA-256 `28cc42a65a20f1d7697833d8a6ecca0f8cb37ac787f9eaeeb7ffc3686d26ce83`. It specifies 8,042 snapshot paths plus five explicitly trusted controls. `research/integration_v2/reconcile.py` fixes the 72-entry PR registry, control list, compiled manifest digest and complete path census. Its complete-census comparison is expected to refuse the five-PR tree; increasing a displayed count cannot qualify it. `boundary.py` still emits the historical label `EXPLICIT_COMBINED_SOURCE_V20` while its checker requires V22; that stale label is not another accepted admission profile.

This recovery checkout omits older `research/integration_v1` and `research/integration_v2` files physically. Their unchanged committed sources and contract were inspected through Git. **The audit did not execute V22 on either tree and claims no V22 pass.** Baseline verification must first materialize a clean, exact protected checkout with the retained Git objects/tags and run:

```sh
python -m research.integration_v2.reconcile --require-committed
python -m research.integration_v1.source_gate
python scripts/audit_current_readmes.py --check docs/integration/2026-11-05/README_AUDIT.json
python -m pytest -q research/integration_v2/test_reconcile.py tests/test_integration_source_successor.py
```

The separate successor proposal freezes the 509 additions and all old identities; preserves the original 72 registry entries; adds reviewed base/head/path identities for PR199–203 to obtain 77 unique entries; and defines separately reviewed, versioned manifest/checker/test/CI controls. PR117 remains HELD. Any new v4 namespace and controls require their own eventual committed identity closure; they are not silently included in the five-PR census. Negative controls must refuse unexpected or missing paths, changed bytes/modes, altered old controls, retargeted heads, duplicate PRs, dirty sources and unrelated/squashed history. Only subsequent maintainer review and required protected checks can authorize integration.

## What the five layers actually connect

| Layer | Reuse and representation | Boundary retained |
| --- | --- | --- |
| P199 Proof-JEPA | Proof-state graphs, online/EMA encoders and action-conditioned prediction | Learned proposals do not replace the existing proof checker. |
| P200 Safety-JEPA | Reuses P199 `GraphEncoder`; bounded lossy graphs of whitelisted tool observations | Existing finite shield and environment rewards remain separate. Mock execution/exfiltration sinks do not execute arbitrary host commands or real network attacks. |
| P201 scientific intake | Descriptor-bound byte snapshots, bounded extraction, graph/Claim IR sidecars, authenticated cache and fresh replay | Imported programs remain data; mathematical checks do not certify scientific meaning. Retained P1/P2 model diagnostics stay in their original domains. |
| P202 scientific understanding | Quantitative records, dimensions, rational equivalence, bounded SBML/model checks, numerical reproduction and source ranking | Source value, mathematical equivalence, implementation correspondence and empirical validity remain separate. Ranking weights have no check authority. |
| P203 scientific semantics | Scoped declarations, equations, quantity roles, symbol dependencies and independent byte-bound checks over the preceding stack | Source declarations and rounded computations use scoped statuses; scientific meaning remains OPEN and authority false. |

Shared tensor widths, graph machinery or arithmetic operator names do not establish representation compatibility. Proof expressions, truncated tool observations, generic Claim IR and scientific entity/role/unit/domain records require explicit, tested adapters. The existing native-domain restriction on neural scientific routing is appropriate.

## Reproduced runtime gaps

A valid synthetic 1,001,599-byte PDF is admitted, preserved byte-for-byte and successfully extracted by intake. Intake's per-file bound is 5 MiB. The v3 semantic worker and direct reader instead reject files larger than 1,000,000 bytes. Running the complete v3 pipeline with `check=False` therefore raises `bounded semantic worker failed; no result accepted` after its baseline work, and produces no v3 summary. One ordinary admitted document can abort the whole semantic stage. A reviewed successor should negotiate stage limits or retain per-artifact unsupported results; this audit leaves the old implementation unchanged.

The same synthetic statement, `Iterations: 7`, produces one typed claim as plain text. In JATS-shaped XML it produces no claim and reports that a supported SBML namespace is required; in PDF it produces no claim and reports no semantic adapter. Intake's extracted PDF text is not an exact-byte semantic grounding bridge. General article XML and published-paper prose therefore need an explicit original-byte mapping and source-role contract before they can inherit meaning support.

A copied v3 package replays with the same pinned manifest before and after an unlisted physical text file is added. Its listed bytes, original manifest, semantic output and replay result are unchanged, and the extra statement is not consumed. Replay validates the manifest's members and nested manifest closure, rather than every physical directory entry. This is a package-scope limitation, **not a demonstrated evidence or authority bypass**. A stricter exported-directory census would be a separate reviewed profile.

Two copied P202 ranking-checkpoint probes also reproduce the earlier audit. Replacing a weight, updating its public digest sidecar and restoring the original nanosecond modification time returns the cached old object and old weight. Encoding an invalid first `schema` key and valid last key is accepted after recomputing the sibling digest because ordinary JSON parsing keeps the last value. The loader also reads the entire file before validation and has no file-byte/vocabulary cap; those latter properties were inspected, not stress-tested. These issues affect relevance guidance. No independent scientific checker consumes those weights as its authority, and the historical loader and model remain unchanged.

## Maintenance, dependencies and checking independence

The census excludes tests, nested learning programs, fixtures and Lean files:

| Runtime namespace | Top-level Python files | Lines |
| --- | ---: | ---: |
| `proof_jepa_rl_v1` | 8 | 1,164 |
| `safety_jepa_v1` | 13 | 2,259 |
| `scientific_intake_v1` | 14 | 3,110 |
| `scientific_understanding_v2` | 19 | 4,205 |
| `scientific_semantics_v3` | 16 | 3,345 |
| Total | 70 | 14,083 |

Function-body AST comparison finds 11 exact duplicate groups, including one-line canonical JSON/hash helpers; six groups contain a multi-line body. Small lexical/resource helpers are candidates for reviewed consolidation. Separate direct MathML evaluation, rational normalization, interpretation and byte-position checking provide legitimate differential-checking value. Merging those implementations blindly would remove useful independence without proving their semantic contracts equivalent.

Cache/replay contexts are broad. P201 binds its whole top-level runtime, reused prover sources, full Python version and observed Lean binary identity. P202 adds runtime and learning code, retrieval checkpoint and NumPy/SciPy versions. P203 adds all its top-level Python and formal files. A corpus, benchmark or retrieval edit can invalidate a deterministic checker cache or old replay. This increases recomputation and portability cost; it does not permit a stale deterministic-check verdict. Checker-specific complete dependency closures would require a new reviewed contract, not deletion of context fields to make old evidence replay.

Neural modules use PyTorch, numerical work uses NumPy/SciPy, and PDF extraction calls fixed `/usr/bin/pdftotext`; ordinary deterministic intake does not require neural inference. Normal package discovery in `pyproject.toml` includes only `pcs*`, so the research namespaces are excluded from the installed PCS distribution and run from a repository checkout. Research workflows filter their own namespaces. P203's workflow runs inherited suites when triggered, but a new v4-only change does not automatically trigger it. New integration CI must explicitly exercise inherited suites and real formal/numerical dependencies. A research CI pass is separate from source admission.

Descriptor snapshots, HMAC caches, stripped environments, fixed worker modules, process-group termination and resource limits do not provide a hostile-code sandbox or independently administered custody. Original source execution remains unavailable. A Lean theorem, actual Python/Lean correspondence, model adequacy and outside scientific replication remain distinct obligations.

## Validation and frozen metadata erratum

Five copy/synthetic probes ran without reading new heldout sources or annotations and without editing the frozen original stack. The accompanying seven regressions verify source preservation, contract separation and the reproduced limits. Their exact command and result are retained in the machine-readable audit. The protected admission gate itself was not executed.

The frozen source manifest's `frozen_software_baseline` field contains `20326a8adda12dbb7fd949f14eeddee3d7d870cadd1`: the PR number `203` was concatenated with its SHA. That 43-character value is not a Git object. The correct 40-character commit is `26a8adda12dbb7fd949f14eeddee3d7d870cadd1`. This explicit metadata erratum leaves the frozen source manifest, selected files, source hashes and evaluation selection unchanged.
