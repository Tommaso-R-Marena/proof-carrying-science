# Canonical action lab

This separate research interface lets you compare real local model proposals
under raw greedy decoding and a finite token constraint, then independently
replay actual Lean-gated SQL effects. It preserves PR #188 and its failed raw
format baseline unchanged. It does not modify production PCS, Aristotle/PGSI
modules, the protected policy or any incumbent authority.

## Open a checked visual demonstration

The retained qualification report and CI receiving artifact contain an offline
`index.html` with links to the two checked workflow reports. No server, JavaScript,
external fonts or telemetry is needed. The report explains each proposed action,
what actually ran, corrections, public output and local proof sources.

To regenerate a recorded profile on Linux x86_64 with Python 3.12 and the normal
frozen repository dependencies:

```sh
source scripts/activate_lean_428.sh
python -m pip install --no-deps --require-hashes -r research/real_model_execution_v2/requirements-tokenizer.lock
python -m research.structured_action_lab_v4 doctor
python -m research.structured_action_lab_v4 demo /tmp/new-action-demo --profile trie
```

Open `/tmp/new-action-demo/report.html`. This fetches about 11 MB of pinned
decoder files when needed, validates every token/byte response, builds the native
Lean authority and executes actual SQLite transitions. **It runs no neural
inference and needs no neural weights or Torch.** Cold builds take minutes.
Use `--profile raw` to replay the unchanged raw-decoding arm of this new paired
study. `--tokenizer PATH` reuses the pinned two-file decoder without downloading.
All outputs must be fresh; existing evidence and ledgers are never adopted or
replaced. Failure retains diagnostics without issuing success.

## Run an explicitly registered comparison with real weights

Reuse the nine-file full Qwen3-0.6B snapshot and optional inference dependency
profile documented in `research/live_agent_lab_v3/README.md` / PR #187. It uses
full 1,503,300,328-byte safetensors weights, revision
`c1899de289a04d12100db370d81485cdf75e47ca`, SHA-256
`f47f71177f32bcd101b7573ec9171e6a57f4f4d31148d38e382306f42996874b`,
CPU float32, two threads, deterministic greedy nonthinking generation, 32-token
budget. Torch 2.7.1+cpu, Transformers 4.57.1, Tokenizers 0.22.2 and Safetensors
0.8.0 must match. The inference dependency directory remains trusted configuration.

```sh
python -m research.structured_action_lab_v4 run /tmp/new-paired-actions \
  --profile paired --bundle FULL_BUNDLE --dependencies INFERENCE_DEPS
```

The complete plan, profile order and source hashes are written to
`registration.json` before inference/effects. `raw` runs first, then `trie` in
separate fixed worker sessions. Each arm has 12 model episodes (42 proposals)
and four separately labeled deterministic controls (16 proposals). Every proposal
uses the actual current broker observation and last executed action. The private
synthetic payload is never supplied to the model. The full model bundle is
checked before/after execution, and clean correlated shutdown is required.

For a smaller study, supply `--profile raw` or `--profile trie` and `--plan PLAN`,
using the same bounded v3 plan schema (1–16 cases, unique safe IDs, reserved
`authority` name, exact fixture Booleans, bounded titles/tasks). Task text is
untrusted proposer data; plans cannot change the fixed policy or tool effects.
Controls are never counted as model inference. No prompt tuning or training is
performed by the harness.

## What the constraint does

The output language contains exactly these seven byte strings:

```text
{"action":0}  {"action":1}  {"action":2}  {"action":3}
{"action":4}  {"action":5}  {"action":6}
```

A reviewed Rust tokenizer encodes each byte string. Its complete five-token path
must decode to exactly those bytes; EOS is the sixth token. The model's greedy
next-token choice is restricted to prefixes of those seven paths. All seven are
available in **every** modeled state, including idle (4), forbidden bypass (5)
and dead end (6). The constraint has no state/policy argument and cannot authorize
an action. The unchanged native Lean gate checks proposed actions before SQL
execution. No Markdown removal, JSON extraction, output repair or response
selection occurs. Raw mode retains the original parser behavior.

This deliberately restricts both spelling and tokenization. It excludes other
valid JSON spellings/tokenizations. Masking logits changes the proposal algorithm;
canonical syntax is imposed, not learned. It may change task competence. The
experiment does not establish a general causal effect, alignment or utility.

## Mathematical result versus implementation evidence

`ActionCodec.lean` proves 11 finite-format results, including universal decoding
soundness for arbitrary byte lists, canonicality, round trips, injectivity and
explicit byte/token tables. Captured bypass remains representable. Axiom audits
allow only the recorded `propext` dependency (two closures are axiom-free). There
are no new axioms, `sorry`, unsafe proof shortcuts or edits to existing Lean work.

```sh
python -m research.structured_action_lab_v4 qualify-codec /tmp/new-codec-audit
```

This uses exact Lean 4.28.0 tool bytes, fresh kernel checks and a fixed Lean
runner. It compares Python/Lean decoding across every single-byte substitution,
insertion and deletion of all seven encodings plus fixed adversarial cases:
43,145 distinct inputs. The Rust token table is separately checked for all seven
values, and tests enumerate every reachable trie state/terminal sequence.

**These are not Lean proofs of the Python trie, Rust tokenizer, Transformers,
PyTorch, compiler, neural computation or SQLite.** Existing finite-model safety
and progress theorems remain distinct from implementation correspondence and
empirical behavior. See `RESULTS.md` for observed outcomes rather than assuming
format compliance implies model competence.

## Inspect and independently replay

```sh
python -m research.structured_action_lab_v4 view INPUT_PROFILE /tmp/loaded.html
python -m research.structured_action_lab_v4 replay INPUT_PROFILE /tmp/new-receiver
python -m research.structured_action_lab_v4.analyze PAIRED_ROOT TOKENIZER_DIR /tmp/new-comparison.json
```

`view` freezes/validates complete token, observation, receipt and comparison
metadata, but labels producer claims **not replayed on this host** and does not
link unchecked producer proof files. `replay` reads the whole submitted suite
before creating effects; it rebuilds actual native authority and SQL state and
regenerates wire/row/path proofs. It never executes submitted Lean proof sources.
Producer proof metadata is comparison input, not an adopted verdict. Profiles,
source hashes, request identities, sequences and token/byte correspondence must
match exactly. Replay uses recorded responses and cannot attest that neural
computation originally produced them.

## Testing and limits

```sh
PCS_TOKENIZER_DIR=TOKENIZER_DIR python -m pytest -q research/structured_action_lab_v4/test_actions.py
python -m pytest -q research/structured_action_lab_v4/test_native.py
# Optional Playwright + Chromium checks:
python -m research.structured_action_lab_v4.ui_smoke PAIRED_ROOT/index.html /tmp/new-browser-check
python -m research.live_agent_lab_v3.ui_smoke PAIRED_ROOT/trie/report.html /tmp/new-profile-browser-check
```

CI retains all preceding 440 tests and receiving replay, adds new adversarial
unit/native integration tests, fresh codec audits and independent receiving replay
of both profiles. Aggregation requires unique passing tests, no failures/errors/
skips, all required modules and all job families. Browser smoke is local evidence,
not a human-user study or comprehensive accessibility certification.

The tool domain is a synthetic fixed document workflow with constant approved
summary. This does not test realistic redaction, arbitrary network/file tools,
general model alignment or recursive self-improvement. Complete tool modeling,
faithful observations, exclusive mediation and trusted loader/compiler/libraries/
OS remain assumptions. Same-user processes and hash checks are not a hostile-host
sandbox or immutable root. There is no protected restart anchor, production
deployment, model-computation attestation or training on outputs/proof traces.
