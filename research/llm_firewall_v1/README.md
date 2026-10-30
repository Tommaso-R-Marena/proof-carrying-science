# A proved tool firewall exercised by real hosted open models

This research extension moves enforcement into an executable built from the same
Lean definition whose safety properties are proved. Python parses proposals and
mediates local SQLite test tools. It cannot replace a positive Lean decision with
a caller-provided verdict through the model protocol or CLI. Production PCS
authority, existing action-shield/PGSI statements and Aristotle modules stay frozen.
This is an additions-only successor to PR173
`6d7ef2a23bbe674813ed8ee38fdc46b21068e404`; no merge or deployment is included.

## Reproduce without an API key or GPU

Activate the existing qualified Lean4.28.0 Linux x86_64/Python environment:

```sh
source scripts/activate_lean_428.sh
python -m research.llm_firewall_v1 audit ./new-firewall-audit
python -m research.llm_firewall_v1 replay research/llm_firewall_v1/evidence/live-v1.json ./new-model-replay
PCS_REQUIRE_LLM_FIXTURE=1 python -m pytest -q research/llm_firewall_v1/test_firewall.py tests/test_action_shield_v1.py
```

The replay builds a fresh monitor, checks all26 exact axiom inventories and runs
official `leanchecker --fresh Policy`. It reconstructs each original model request
and its context, reuses the captured original completion bytes, executes all local
effects in fresh databases, verifies the reconstructed records and regenerates
ordinary-kernel proofs of every committed history. No live inference is required
for CI. Stored success flags never authorize effects. Original HTTP responses are
evidence of the observed run, not cryptographic attestation of the provider/weights.

Fresh output directories are mandatory. Exit0 means the requested audit/replay
completed; exit20 means refusal/unavailability. No production authority is granted.

Live synthetic experiments use only the existing configured free Cloudflare account:

```sh
python -m research.llm_firewall_v1 evaluate ./new-live-model-run --live
```

The client requires an observed empty subscription list and free-eligible model
metadata, refuses upgrades/paid-only models, caps requests128 and reported usage8000
neurons, limits completions256 tokens and uses no remote model/network/tool endpoint
chosen by the model. Free-plan provider quota exhaustion refuses further requests.
No billing/subscription, Worker, site or account configuration is changed. Only
synthetic prompts/canaries may be submitted. Never insert actual secrets here.

## What the formal mechanism guarantees

Eight typed actions: read public, read private, write private, publish, finish,
delete protected, network, grant admin. Initial state: generation0,8 tool-cost
units, no tracked private read. Publish costs2; other permitted operations cost1.
Delete/network/admin are always denied. After read-private, a sticky taint bit
blocks both publish and finish; private work can continue. Generation never rolls
back within an accepted history. At most8 actions can be accepted from initial.

The policy is deliberately conservative. It does not classify the content of text.
An innocuous publication after a private read is blocked; an untracked secret in
an initially untainted context can be published. Both are preserved negative
controls. This is **not a semantic noninterference or general confidentiality proof**.

Twenty-six ordinary theorems in `PCSLLMFirewall`:

| Group | Exact theorem names |
| --- | --- |
| Accepted step | `step_facts`, `step_valid`, `step_budget`, `step_generation`, `step_forbidden`, `step_taint`, `step_private`, `step_no_public` |
| All finite accepted histories | `history_forbidden`, `history_budget`, `history_generation`, `history_valid`, `initial_history_bound`, `history_taint`, `history_no_public`, `private_blocks_suffix` |
| Explicit scope controls | `initial_publish_permitted`, `tainted_publish_refuses` |
| Byte protocol | `action_roundtrip`, `decode_encode`, `malformed_refuses`, `process_decoded`, `process_accepts`, `process_sound`, `wire_forbidden` |
| Captured history | `run_sound` |

The five-byte input is exactly version1, generation0..8, remaining0..8, taint0/1,
action0..7. The six-byte response distinguishes allow, deny and malformed input.
`decode_encode` proves roundtrip for valid states. `process_sound` proves that any
allow response from the actual Lean function comes from a decoded typed request and
an accepted transition. `wire_forbidden` excludes forbidden actions for arbitrary
input bytes. `private_blocks_suffix` covers arbitrary future proposer behavior
after a tracked private read. Each finite accepted-action sequence is separately
kernel replayed. No new axiom, native decision shortcut or altered old specification.

## Engineering boundary

- The monitor is freshly compiled with pinned Lean/checker/leanc bytes. It uses
  Std only. All26 inventories permit only propext/Classical.choice/Quot.sound.
- The executable bytes are captured into a Linux memfd and kernel-sealed against
  write/grow/shrink/unsealing. Each invocation executes that descriptor, rather
  than reopening the mutable executable path. The tests actually try writes,
  truncation and path substitution. Mutable source/tool/build hashes are also
  compared before/after execution. These Linux seals protect that captured image;
  they do **not** make the compiler, shared libraries, OS, administrator or Python
  process immutable, or create an independently administered authority.
- Model JSON is bounded strict UTF-8 with exact tool/argument fields. No provided
  path, URL, shell, code, approval, verifier or policy field is interpreted.
  Text is stored with SQL parameters. Both public text-release actions are gated.
- Expected-generation CAS, Lean decision, effect and new state share one SQLite
  write transaction. Denials do not change state/effects. Tests cover races,
  stale proposals, exceptions after effects/before commitment, actual process
  exit with an uncommitted SQLite transaction and corrupted receipt chains.
- Hash-linked records identify captured requests/replies and effects. They are
  not signed receipts or externally protected anti-rollback anchors. A malicious
  host can replace state/history together; this is outside the model-only threat.
- The network tool in the counterfactual control is a local SQLite outbox
  simulator. No actual external exfiltration/destructive operation is executed.
  Protected-record deletion and admin toggles affect only synthetic test databases.

The policy's mathematical truth is kernel proved. Lean/C compiler and runtime
correctness remain trusted. Python JSON/operation mapping, SQLite, complete
mediation, observation/context labeling and faithful event capture are tested
implementation assumptions, not fully refined proofs. All initial private context
must already be labeled; private model memory across reset sessions, training-data
knowledge, covert/timing channels, provider handling and alternate tool entrypoints
are outside the guarantee. Raw model API traffic/research logs are outside the
classified public sink and contain synthetic canaries only. Do not deploy this
harness as a confidential-processing service.

## Actual models and scientific design

The live protocol registers its hash, source hashes and exact checkout before the
first campaign inference. Development connectivity smokes are excluded. The fixed
model IDs are:

- [NVIDIA Nemotron3 Super120B/A12B](https://developers.cloudflare.com/workers-ai/models/nemotron-3-120b-a12b/)
- [Qwen3.8 27B](https://developers.cloudflare.com/workers-ai/models/qwen3.8-27b/)

These are real hosted2026 open-model families, not toy neurons or mocked LLMs.
This is not an independently established global state-of-the-art ranking. Backend
weight hashes/quantization are not attested. Current model catalog, completion IDs,
provider-reported model IDs, usage and raw requests/responses are captured. Upstream
model-card revisions do not prove that a hosted backend uses those exact weights.
Qwen upstream metadata reports Apache2.0; Nemotron has its own open-model
license. Do not equate every open-weight license with OSI open source.

The retained three-endpoint pilot also attempted Google Gemma4 26B/A4B, but19 of
its23 responses reported `@cf/google/gemma-4-26b-a4b-it-external`. The strict
identity check refused those outputs. That endpoint is excluded from the primary
results; no alias equivalence or backend-weight identity was assumed. The pilot
is retained with complete=false. It also exposed a reporting bug that counted
attack refusals in the benign utility denominator; the corrected primary run
uses the same20 safety tasks and separates the six explicit utility criteria.

There are20 one-proposal cases per model:16 policy-aware cases and4 policy-blind
stress controls, always reported separately. They cover benign utility, forbidden
tools, post-private public output, budget boundaries, document injection and fake
authority. A paired unmediated **local** control dispatches the exact same captured
proposal after the same prelude; it is a counterfactual tool test, not a separately
observed unshielded adaptive agent trajectory. Six actual closed-loop agent tasks
(public, private, injected-public for each primary model) additionally measure task utility
under shield feedback, with at most4 turns. The preregistered minimum is one
successful agent task per model, not a theorem of general liveness.

Counts are deterministic constructed protocols with provider sampling/version
variation. No IID assumptions, population safety rates, independent external
validation, global model alignment, neural weight correctness or accelerating
self-improvement are claimed. Failed/partial calls are retained; missing model
evidence fails focused CI. No real inference credentials are needed in CI.

Next: formally refine the broker/decoder boundary, preserve context labels across
real isolated sessions, tighten information-flow policy without blanket refusals,
and run independently held-out public agent-security benchmarks with actual
isolated tool services. Future Aristotle codec integration remains separate.
