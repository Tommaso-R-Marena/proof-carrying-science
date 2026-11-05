# Checked real-model execution and transcript correspondence

This is the hardened reproduction path for the actual Qwen3-0.6B experiment in
PR #186. It adds **complete artifact pinning, verified copies, request correlation,
and independent token-to-proposal checks before SQL replay**. The original
experiment, its negative findings, all formal sources and production authority
remain unchanged. This phase permits additions only and protects every one of
the 4,514 files in its parent commit, including all 4,315 protected core files.

## Why this extension exists

The parent audit bounded token IDs but did not independently decode them or
reconstruct prompt tokenization. Four actual parent-preflight experiments accepted
altered generated tokens, altered input tokens, a flipped EOS claim and a changed
configuration digest while the captured proposal bytes remained unchanged.
These are **experimental evidence-integrity gaps**, not demonstrated SQL or Lean
authorization bypasses. The original real-weight run is preserved, not relabeled.

The new path checks all nine bundle files against the reviewed manifest from
PR #186, whose own exact byte digest is pinned. It refuses missing/extra files,
changed sizes/digests, symbolic links, directories and FIFOs. Copying uses checked
regular-file descriptors, bounded reads and a fresh destination. Model loading
uses this verified copy; changing the original path afterwards does not change
the copy. Partial copies are removed on a handled failure; existing destinations
are never adopted or overwritten. Abrupt crashes can leave incomplete output
directories, which must be inspected separately and cannot be adopted as success.

`Oracle` uses the pinned Rust tokenizer directly and an independently written
renderer for exactly two messages, no tools and disabled thinking. It does not
load Transformers or execute the model's Jinja template. It recomputes prompt IDs,
decodes generated IDs, checks EOS/length consistency, rejects unknown/control
tokens and numeric aliases, and returns the exact UTF-8 proposal bytes. It
supports ordinary malformed proposal text: JSON repair and policy decisions
remain outside this correspondence check. Unsupported prompt protocols refuse.

The inference worker still uses Transformers' real model and template code. It
checks agreement with the independent renderer before inference; the coordinator
validates responses again. The two paths share the underlying Rust tokenizer
implementation, so this is independent wrapper/rendering verification, not two
independent tokenization algorithms or a kernel proof of tokenization.

Each worker creates a fresh session ID. Exact frame schemas, integer sequences,
and canonical request digests prevent accidental cross-request/session mixups.
Nonblocking pipe reads **and writes** have whole-frame deadlines and byte budgets.
Duplicate JSON keys, nonfinite values, partial EOF, oversized frames, premature
closure, extra output and unsuccessful process exit fail closed. Clean closure
rechecks all bundle files and runtime source identities. The inference child
omits the three configured PCS/Cloudflare application credential variables.
Inherited proxy, CA and runtime guard configuration is preserved.

## Run

Linux x86_64, Python 3.12, exact Lean 4.28.0 for SQL replay. The real inference
worker uses the versions recorded in PR #186: PyTorch 2.7.1+cpu, Transformers
4.57.1, Tokenizers 0.22.2 and Safetensors 0.8.0. Its optional inference dependency
directory remains trusted launcher configuration. The standalone checker only
needs the small hash-locked Rust tokenizer wheel:

```sh
python -m pip install --no-deps --require-hashes -r research/real_model_execution_v2/requirements-tokenizer.lock
python -m research.real_model_execution_v2 fetch /tmp/new-tokenizer
python -m research.real_model_execution_v2 audit /tmp/new-tokenizer

# New actual-weight inference; loads a fresh verified copy, executes no SQL.
python -m research.real_model_execution_v2 repeat /path/to/qwen-files /path/to/inference-deps /tmp/new-inference

# Check every new response and its correspondence to the frozen original corpus.
python -m research.real_model_execution_v2 audit /tmp/new-tokenizer --run /tmp/new-inference/run.json

# Then build/check the native Lean authority and replay all 16 original episodes.
source scripts/activate_lean_428.sh
python -m research.real_model_execution_v2 audit /tmp/new-tokenizer --run /tmp/new-inference/run.json --replay /tmp/new-sql-replay
PCS_TOKENIZER_DIR=/tmp/new-tokenizer python -m pytest -q research/real_model_execution_v2 research/real_model_safety_v1
```

All output directories must be fresh. `fetch --full` downloads the exact nine-file
bundle, including the upstream Apache-2.0 license and model card. Files are bounded
by pinned sizes/hashes; elapsed transfer budgets supplement the network read
timeout. The default fetch downloads only the two tokenizer files, about 11.4 MB.
Weights are never committed to Git. Downloading or hashing weights is not an
affirmative Lean authorization verdict.

The repeat command saves every response before comparing it. A mismatch is
retained, returns failure and cannot authorize replay. A file named `run.json`
is not sufficient evidence: `audit --run` must accept its complete contents.
Replay preflights every request and captures the exact input report hash,
expected capture bytes and proof metadata before creating effects. It reconstructs
all original model and control episodes with the unchanged real native authority
and SQL tools. The 42 newly checked model proposals must match the frozen replay
bytes exactly. The four deterministic controls remain separately labeled.

This is **frozen-prompt inference reproduction followed by guarded replay**, not
a new adaptive model study. CI downloads only the pinned tokenizer and validates
the committed real-weight transcript; it does not rerun neural inference. It also
runs the complete unchanged regression census and independent Lean/SQL replay.

## Evidence and limitations

`observations/run.json` records the final actual-weight run and source identities.
`observations/differential.json` records 64 Unicode/delimiter prompt pairs compared
against Transformers' tokenizer path. `observations/parent-observations.json`
records the four reproduced parent preflight gaps. The stacked PR records exact
commits, complete test counts, CI links and independently checked artifacts.

The kernel continues to prove the finite workflow policy, codecs, row properties
and captured paths through the existing 52 runtime closures and per-episode
proofs. **No general Lean theorem or axiom is added.** New model-file, protocol and
tokenizer checks are tested host implementation, not newly kernel-certified
authority. No production checker, model promotion or website deployment changes.

A verified copy is not an immutable host root. Its directory routing, subsequent
loader interpretation, memory parameters, Python/PyTorch/SQLite, compiler/shared
libraries and OS remain trusted. Same-user access and inherited proxy capabilities
are not sandboxed. Removing environment variables does not establish protected
credentials or an independently administered verifier. Hashes/session IDs do not
cryptographically attest that a model causally generated an output. A hostile host
can fabricate observations; external validation remains open.

The study remains one small model, greedy nonthinking decoding, locally authored
prompts and synthetic fixed SQL tools. It does not prove alignment, realistic
redaction, broad agent usefulness, universal neural semantics or recursive
self-improvement. No proposal data, model weights or proof-development traces are
used for training. Next priorities are independently authored tasks and validated
tool observations, then larger/multiple models and adaptive attacks with measured
task utility, plus independently controlled deployment enforcement.
