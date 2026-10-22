# Actual local weights through the proved tool firewall

This additions-only research extension downloads and runs two official Apache 2.0
Qwen GGUF releases on CPU. It preserves every blob/mode at predecessor
`68702256fe646a235e67416dd957d7af09186e8f` (PR #174), including all 26 general Lean
theorems, the compiled monitor and production PCS authority. No merge or deployment.

These small models fit the available two-core, GPU-free machine with an 8 GiB
cgroup memory limit (the host reports roughly 10 GiB).
They are **not the 27B/120B hosted models** from the predecessor experiment and
are not claimed to establish a current global state-of-the-art ranking.

| Exact official model | Revision | Q8_0 bytes |
| --- | --- | ---: |
| `Qwen/Qwen3-0.6B-GGUF` | `23749fefcc72300e3a2ad315e1317431b06b590a` | 639,446,688 |
| `Qwen/Qwen3-1.7B-GGUF` | `90862c4b9d2787eaed51d12237eafdfe7c5f6077` | 1,834,426,016 |

[pins.json](pins.json) fixes the complete SHA-256 of each real weight file,
immutable-revision download URLs, upstream llama.cpp CPU release archive digest,
commit `970b51ce7c9ba5fff0726c5e9994f1c2f0e4eedc` / build `b11827`, and all 61
runtime file hashes. The release was hash-verified, not independently rebuilt from
source. Q8_0 quantization correspondence with original floating-point weights is
not proved. GGUF metadata/provenance is not a neural-network correctness proof.

## Run actual inference

Requires Linux x86_64, Python 3.12, the pinned Lean 4.28.0 environment, at least
3 GiB of free storage for downloads, and roughly 8 GiB of available RAM. If weights
live in tmpfs, their resident pages also count against RAM. Each engine runs
sequentially with two CPU threads, no GPU layers and a 4,096-token context.

```sh
source scripts/activate_lean_428.sh
python -m research.local_weights_v1 download /tmp/pcs-pinned-weights
python -m research.local_weights_v1 evaluate /tmp/pcs-pinned-weights ./fresh-local-experiment
```

Downloads use public upstream HTTPS with fixed revisions, enforce exact streamed
size/SHA-256 and preserve bad partial files for diagnosis. Existing wrong artifacts
are refused rather than overwritten. There is no model-loader pickle, remote
Python model code, torch install, paid compute or external model inference API.

The runner hashes the bytes while copying each weight file into a Linux memfd,
checks the complete pinned hash and length, then applies actual kernel write,
grow, shrink and unsealing protections. llama.cpp receives `/proc/self/fd/<fd>`
and inherits that descriptor. Its observed weight memory map is captured. No
mutable original weight path is reopened during inference. This binds the loaded
weight image under trusted Linux/runtime behavior; it does not prove the engine's
numerical implementation or make the host/administrator immutable.

The pinned executable/library inventory is checked before loading and after each
model run. Shared libraries and the inference engine remain trusted native code.
The engine binds only loopback, disables the web UI, has offline model loading,
and receives no inherited cloud/GitHub credentials or loader overrides. This is
not an independently administered isolation boundary against a malicious host.

## Experiment and proof boundary

Protocol/source hashes and checkout commit are recorded before the first campaign
inference, as a local ordering record rather than third-party preregistration.
Development connectivity smokes are excluded. Generation is temperature 0, seed 42,
maximum 256 tokens, JSON-object syntax constraint, thinking disabled. The syntax
constraint does not enforce tool policy or supply an affirmative Lean verdict.

Each model receives the same predecessor 20 one-proposal cases: 16 policy-aware
and four policy-blind controls, reported separately. The same raw proposal is also
dispatched in an unmediated local synthetic control. Public/private/injected-public
closed-loop tasks have at most four turns. Each captured accepted history receives
a fresh ordinary-kernel Lean proof. **Task success is measured, not required for
completion:** a small model's inability to complete a task is a retained result,
not grounds to relax the safety policy or discard the model. Safety violations or
missing cases refuse experiment qualification.

The policy is independent of model weights: it proves accepted mediated actions
satisfy the defined rules for arbitrary proposers. Compiler/OS/runtime correctness,
Python parsing/dispatch, SQLite, complete mediation and context labels remain trust
assumptions. The public-sink/taint scope, untracked-secret and conservative-refusal
negative controls from PR #174 still apply. API/logs use synthetic data only.
Network controls write a local outbox; no real exfiltration/destruction is tested.
These are constructed synthetic tasks, not an independent held-out security
benchmark, population safety estimate or general alignment proof.

## Replay and required real-weight CI tests

```sh
python -m research.local_weights_v1 replay research/local_weights_v1/evidence/local-v1.json ./fresh-local-replay
PCS_REQUIRE_LOCAL_WEIGHTS=1 PCS_REQUIRE_LOCAL_CAPTURE=1 PCS_REQUIRE_LLM_FIXTURE=1 \
PCS_LOCAL_WEIGHTS_DIR=/tmp/pcs-pinned-weights \
python -m pytest -q research/local_weights_v1/test_local.py research/llm_firewall_v1/test_firewall.py tests/test_action_shield_v1.py
```

Offline capture replay needs no weights/API key/GPU: it reconstructs requests,
reuses exact captured completions, rebuilds the actual Lean monitor, checks its
26 axiom inventories and fresh object, reexecutes local effects and regenerates all
46 history proofs. **Replay does not rerun neural inference or authenticate the
captured weight-binding observations.** CI additionally downloads and hashes both
models, runs the full fresh 40-case/six-agent neural campaign with new Lean
certificates, and tests new CPU inference from each model separately. Fresh neural
outputs may differ across CPU hardware; CI requires complete observations and
policy enforcement, not a predetermined utility score. Missing captures/weights
fail CI; no mock LLM/affirmative verifier
stands in for these tests. The suite also retains all 72 predecessor tests.

Weights are intentionally not committed or embedded in the portable evidence.
Download them by exact pins above. Temporary local copies may disappear with the
execution environment. No claim that every inference is bitwise reproducible
across CPU instruction sets, despite fixed seed/settings.
