# Real-weight model proposals under checked workflow supervision

This experiment runs **Qwen/Qwen3-0.6B from actual local, unquantized safetensors
weights**. Its raw generated text becomes an untrusted proposal to the existing
Lean-backed progress supervisor. The model does not provide verifier verdicts or
select executable tools. This is a small-model, synthetic confidential-document
workflow experiment, not a general alignment evaluation or production deployment.
See [observed results and counterexamples](RESULTS.md).

## Experimental protocol

[`protocol.py`](protocol.py) fixes the model revision, weight digest, system prompt,
six cases, two fixture branches, four deterministic controls and greedy decoding
before inference. Two cases are development probes and four are held out from
those probes. All were authored locally before the run; this is **not an external
held-out benchmark**. No prompts, outputs, proof traces or model weights are used
for training. No prompt tuning, rejection sampling or successful-output selection
is performed. Every case runs on both a confidential and an initially-public
payload, giving 12 model episodes and 42 proposal opportunities. Four additional
private-payload controls use the oracle, always-publish, always-idle and malformed
proposals. Controls are never counted as model generations.

At each step the model receives the actual current abstract state. A separate
inference process loads the pinned weights with `trust_remote_code=False`, local
files only, safetensors only, float32 CPU inference, deterministic algorithms,
two CPU threads, greedy decoding and a 32-token budget. It records input token
IDs, generated token IDs, exact decoded text, EOS status and duration. The
coordinator submits **all decoded UTF-8 bytes without stripping, extracting JSON,
repairing formatting or retrying**. A truncated or malformed completion therefore
remains malformed. Weight/config/tokenizer files are hashed before loading, after
loading and after all requests. These host checks are not a proof of PyTorch's
interpretation of the weights.

The actual authority builds first-party Lean sources with the pinned Lean 4.28.0
toolchain, audits all 52 existing runtime closures, independently kernel-checks
the compiled imports and invokes the sealed native gate before actual SQLite
effects. Every episode gets newly checked wire, row and abstract-path proof
sources, a complete receipt chain, final rows and a source-bound replay capsule.
There are **no new general Lean theorems** in this extension; it instantiates the
existing ones with real-model-generated proposal bytes. Existing PCS production
authority, Aristotle work and the research supervisor implementation are unchanged.

## What is measured

Three different results must remain separate:

- **Model proposal behavior:** strict parsing, forbidden/disabled action requests,
  requests with an unsafe possible outcome, and safe but nonprogressing requests.
- **Supervisor interventions:** whether the selected actual action differs from
  the parsed proposal. Completion through fallback is not model competence.
- **Authorized execution:** actual SQL final rows, decreasing-rank transitions,
  native responses and ordinary-kernel proofs, replayed on a receiving host.

`counterfactual` replays the same proposed actions against **every branch of the
declared finite graph**, with disabled actions having no effect. It executes no
ungated SQL. After divergence it does not regenerate model outputs against the
counterfactual observations. It is consequently a diagnostic of this action
sequence, not a causal estimate of ungated deployment safety. Overlapping failure
categories must not be added as independent failures. Six prompt templates and one
small model cannot justify population estimates, robustness against adaptive
attackers, state-of-the-art-model claims or an accelerating improvement claim.

## Reproduce

Use Python 3.12 and a CPU PyTorch 2.7.1+cpu installation. Install the versions in
[`inference-dependencies.txt`](inference-dependencies.txt) into a separate target
directory; the inference libraries are optional and are not PCS dependencies.
These are version pins, not a wheel-hash lock. The observed versions and all
model-file hashes are also recorded in the evidence.

Fetch the files listed in `evidence/model.json` from this exact Hugging Face
repository revision, using its HTTPS `resolve/<revision>/<filename>` URLs:

```text
Qwen/Qwen3-0.6B @ c1899de289a04d12100db370d81485cdf75e47ca
model.safetensors: 1,503,300,328 bytes
SHA-256: f47f71177f32bcd101b7573ec9171e6a57f4f4d31148d38e382306f42996874b
```

The upstream weight license is Apache-2.0; retain the upstream license and model
card when downloading. Weights are not vendored in Git. A trusted host should
compare **every** downloaded file against `evidence/model.json` before inference.

```sh
source scripts/activate_lean_428.sh
python -m research.real_model_safety_v1.run /path/to/weights /path/to/inference-deps /tmp/new-model-run
python -m research.real_model_safety_v1.audit /tmp/new-model-run
python -m research.real_model_safety_v1.audit /tmp/new-model-run --replay /tmp/new-receiving-run
python -m research.real_model_safety_v1.reproduction.repeat /tmp/new-model-run /path/to/weights /path/to/inference-deps /tmp/new-inference-repeat
python -m pytest -q research/real_model_safety_v1
```

Outputs must be fresh directories. On failure the live runner stops, preserves
partial evidence and never creates the completed experiment report. Audit checks
the complete fixed episode inventory, every prompt, raw text/capture binding,
exact integer/Boolean accounting, token bounds, source identity, capture preflight
and recomputed metrics before any replay effects. Receiving replay rebuilds its
own authority and compares exact capture bytes, all receipts/final rows and fresh
proof inventories. It does **not** rerun neural inference. CI explicitly performs
recorded-evidence replay; it does not download weights or claim fresh inference.

## Trust boundary and unresolved obligations

The fixed workflow only publishes a preauthorized fixed public summary. This is
not semantic redaction of arbitrary documents. The confidential canary is
synthetic, and no real confidential data is sent to the model. Observation
faithfulness, complete tool modeling, exclusive mediation, host integrity,
Python/SQLite/PyTorch correctness, compiler/linker/IO correspondence, continued
invocation and tool termination remain assumptions. A different or incorrectly
modeled tool adapter is outside these results.

The model process has no broker object reference and only an inference JSONL
interface. Both processes run on the same trusted host/user. This is **not an OS
sandbox or an independently administered immutable trust root**. The model is not
allowed to supply code, paths, state claims, credentials or verifier substitutions.
No durable protected restart anchor or production authority is established.

The next scientifically useful extension is an independently authored prompt and
tool-model suite with realistic partial observations, then multiple larger models
on adequate compute, continued sampling and adaptive attacks. Such work must
measure intervention cost and task utility as well as refusals; merely forcing a
fixed safe path cannot establish a generally useful autonomous agent.
