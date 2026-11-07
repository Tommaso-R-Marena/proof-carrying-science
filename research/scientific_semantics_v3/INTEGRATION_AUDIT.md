# Research-stack integration and security review

The four predecessor modules remain isolated research implementations. Their source confirms that model proposals, bounded computations, abstract proofs and scientific meaning have separate roles. No production authority, protected source admission or old experiment was changed by this review.

This is an internal, AI-assisted source audit at base commit `b612d3d174793ac046b5c93282b24995acadffdb`, with two executed probes on a **copy** of the P202 ranking checkpoint. It is not an external security assessment. Machine-readable findings, source line references, source hashes, exact duplicate groups and probe results are in [evidence/integration-audit.json](evidence/integration-audit.json). New v3 runtime code was still under development during this snapshot; the coordinating implementation must validate it separately.

## What is connected, and what is not

| Module | Actual representation and reused capability | Enforcement / evidence boundary |
| --- | --- | --- |
| P199 Proof-JEPA | Typed proof-state graphs; trainable online/EMA encoders and action-conditioned predictor; existing PCS proof environment and Lean receipts | Model chooses proposals. Existing checker accepts proofs. Training functions check provenance fields but are not themselves receipt validators. |
| P200 Safety-JEPA | Whitelisted tool observations converted to bounded, lossy graphs; reuses P199 `GraphEncoder`; actual synthetic-resource file workflows | Existing PCS finite action shield and environment-owned rewards remain separate from model scores. Local mock exfiltration/execution sinks are not real networking or operating-system command execution. |
| P201 scientific intake | Exact byte inventory; bounded adapters; source-bound sidecar graph and restricted Claim IR lowering; authenticated cache and independent replay | Source files remain data. Closed independent checks can pass; scientific meaning remains open. P1/P2 models run only native-domain diagnostics. |
| P202 scientific understanding | Separate scientific arithmetic/quantity records, dimensional checks, rational equivalence, strict SBML subset, numerical reproduction and a separately trained source retriever | Generic `VERIFIED_SUPPORTED` never grants scientific authority. Meaning, domain assumptions, Python/Lean refinement and empirical validity remain independent obligations. |

Equal tensor widths and shared graph machinery do not establish scientific compatibility. Safety observations lose text after bounded truncation and use a hash vocabulary; proof expressions are a different domain. P201 correctly refuses to route arbitrary scientific obligations through these models. The poor P202 source-retrieval result is evidence for retaining deterministic defaults, not a reason to activate more neural routing.

## Two reproduced ranking-checkpoint limitations

`scientific_understanding_v2/retrieval.py:96–111` caches by resolved path and modification time. On a temporary copy, the reviewer changed a weight from `0.018219461664557457` to `1.0182194616645575`, updated the public digest sidecar and restored the original modification time. `load_checkpoint` returned the old cached object and old weight. This is stale ranking guidance, **not** an authority bypass.

The same copied model was encoded with duplicate `schema` keys, an invalid first value and valid final value. After matching the digest sidecar, the old loader accepted it because ordinary `json.loads` keeps the last key. The loader also reads the full file before integrity checking and has no file-byte or vocabulary bound. Those latter bounds were confirmed by code review; no oversized allocation attack was run.

A public sibling digest detects accidental changes relative to that sibling; it is not independent custody or an immutable root. A new compatibility wrapper should bound regular-file reads, reject duplicate JSON keys and nonfinite tensors, check a separately frozen expected digest, and bind cached inference to the verified bytes. Frozen P202 must stay unchanged. The current scientific checkers neither consume these model weights as authority nor inherit this model cache.

The probes can be reproduced without training or touching original evidence:

```python
from pathlib import Path
import hashlib, json, os, tempfile
from research.scientific_understanding_v2 import retrieval

with tempfile.TemporaryDirectory() as temporary:
    path = Path(temporary) / "model.json"
    raw = Path(retrieval.DEFAULT_CHECKPOINT).read_bytes()
    sidecar = path.with_suffix(".json.sha256")
    path.write_bytes(raw)
    sidecar.write_text(hashlib.sha256(raw).hexdigest())
    stamp = path.stat().st_mtime_ns
    original = retrieval.load_checkpoint(path)
    changed = json.loads(raw)
    changed["weights"]["embedding"][0][0] += 1
    modified = json.dumps(changed).encode()
    path.write_bytes(modified)
    sidecar.write_text(hashlib.sha256(modified).hexdigest())
    os.utime(path, ns=(stamp, stamp))
    assert retrieval.load_checkpoint(path) is original
    retrieval._load_checkpoint.cache_clear()
    duplicate = b'{"schema":"invalid-shadow",' + raw.lstrip()[1:]
    path.write_bytes(duplicate)
    sidecar.write_text(hashlib.sha256(duplicate).hexdigest())
    assert retrieval.load_checkpoint(path)["schema"] == "scientific-source-encoder-v1"
```

## Source fidelity and execution assumptions

P201 snapshots regular single-link files through descriptors, rejects changes observed during reads, normalizes archive paths and enforces file/count/expansion limits. Its adapters use bounded fixed parser workers. DOCX/XLSX external relationships are rejected; workbook formulas, Python, notebooks, Lean declarations, opaque checkpoints and other imported code do not execute. P202 separately checks exact source bindings before dispatch, uses an approved mathematical/numerical fragment and never executes the upstream Octave script or arbitrary doctests.

P202 numerical workers strip credentials, set fixed working directories and resource budgets, start a new process session and kill the process group on timeout. These workers still have the same host user identity and normal filesystem capabilities. Resource limits and process separation are useful engineering controls; they are not a hostile-code sandbox, immutable storage, protected credentials or independent machine custody. The new pipeline must keep source execution unavailable rather than relying on process limits to make arbitrary imported code safe.

Scientific package manifests establish byte integrity relative to an externally trusted manifest. They cannot establish the original authorship of an entirely fabricated, self-consistent replacement project. P201/P202 replay exposes optional external manifest pinning and reconstructs extraction, graph, obligations and supported checks. HMAC caches use a host-owned key excluded from exported packages and rehash source dependencies; same-user or host compromise remains outside the claimed boundary. Fresh replay bypasses cached verdicts.

Lean certificates bind actual compiled statements, sources and compiler identity. Imported Lean-library integrity, host observation, byte correspondence and external numerical libraries remain explicit assumptions. Integer stoichiometry theorems do not establish real-valued ODE correctness or biological adequacy. Exact rational normalization proves only equality on the common defined domain, subject to original denominator obligations; it does not identify scientific roles or preserve an omitted domain automatically.

## Maintenance and computational cost

A static census of top-level runtime Python files found 54 files and 10,738 lines: P199 8/1,164; P200 13/2,259; P201 14/3,110; P202 19/4,205. These counts exclude tests, nested learning code, fixtures and Lean sources. AST-body comparison found seven exact duplicate groups, primarily small canonical JSON/hash functions, bounded JSON readers and deterministic training setup. Their exact locations are retained in the JSON audit. P200 already reuses P199's encoder.

The larger maintenance concern is the growing number of representation fragments and versioned evidence contracts. P202 has extraction arithmetic, independent direct MathML evaluation, dimensional arithmetic, rational normalization and document reconstruction. Some duplication supplies genuine differential-checking value. Merging these into a single parser/checker would remove that independence. Prefer explicit adapters and shared lexical bounds after differential tests; do not unify meanings merely because operators share names.

The existing contexts are conservative. P201 binds all its runtime files, reused prover sources, full `sys.version` and observed Lean binary identity. P202 additionally binds its runtime and learning scripts plus retrieval checkpoint for every evidence package. An unrelated retrieval, corpus or benchmark edit can therefore invalidate deterministic-check caches and replay. This causes recomputation and portability failures rather than stale-result acceptance. A future reviewed successor may use checker-specific complete dependency closures. Removing context fields to make old receipts replay is inappropriate.

PyTorch is imported lazily for retained-model diagnostics. Ordinary deterministic intake does not need P1/P2 neural inference. Numerical reproduction adds NumPy/SciPy; PDF extraction uses fixed `pdftotext`. Experimental CI installs shared prover/training locks and each predecessor workflow filters its own namespace. New-namespace changes consequently need an explicit integration workflow to run inherited suites and real Lean/numerical checks. Dedicated research CI success does not establish protected-main admission success.

## Priority regression attacks for the new stage

1. Tamper with evidence and recompute its internal manifest while retaining the original external manifest pin. The pin must reject it. Unpinned reanalysis may inspect the changed project as new data, but cannot attest original authorship.
2. Compare `x/x` with `1` without proving `x ≠ 0`, or alter a denominator to have a concrete zero. Preserve the domain obligation and a counterexample where applicable.
3. Include source text requesting checker, policy, reward or training changes, alongside Python/pickle/notebook payloads that would create a marker if executed. Ingestion must remain data-only and the marker absent.
4. Alter units, numeric tables, symbol scope and concentration/amount roles independently. Change an author prediction into an apparent empirical observation. Source/value agreement alone must not corroborate the changed meaning.
5. Supply DTD/entity XML, deeply nested data, extreme powers/number exponents, archive traversal and duplicate normalized names. Fail within the declared resource budget without successful unsupported certification.
6. Test duplicate-key/nonfinite/truncated/wrong-digest neural checkpoints and same-mtime replacement through any new compatibility interface. Independent checks must remain unchanged if learned retrieval fails.

## Integration decision

The four modules offer reusable research capabilities with explicit limitations. They do not yet constitute production scientific understanding or an independently controlled safety authority. Keep the historical experiments frozen and all four PRs unmerged. Production integration requires a reviewed successor source-admission contract, explicit Python/formal correspondence work, stronger isolation where hostile execution is required, expert semantic adjudication and external replication. None is supplied or waived by this internal audit.
