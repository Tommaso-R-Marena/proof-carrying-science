# Exact byte effects and causal public-output assurance

This isolated extension preserves all 6,394 predecessor blobs/modes at
`5a0dad902c89917298179c269680954ddb5e22b8` (PR #175). Production authority,
PGSI/Aristotle modules, existing policies and historical artifacts remain frozen.
Nothing is merged or deployed.

## New formal capability

[Refinement.lean](Refinement.lean) imports the unchanged predecessor policy and
adds **19 ordinary-kernel theorems**. The compiled function now decides a full
byte-bearing intent and returns the exact next state, effect constructor, effect
payload and read observation. No affirmative verdict is provided by a caller.

| Area | Exact theorem names in `PCSCausalFirewall` |
| --- | --- |
| Modeled execution refines old policy | `execute_refines`, `execute_forbidden`, `execute_budget` |
| Exact bytes/observations | `execute_exact_private`, `execute_exact_public`, `execute_private_read` |
| Private-read taint and unaffected low behavior | `execute_tainted_no_public`, `execute_taint_persists`, `execute_secret_independent` |
| Adaptive controller traces | `drive_tainted_empty`, `causal_public_noninterference` |
| Concrete effect histories | `runEffects_refines` |
| Explicit scope counterexamples | `untracked_initial_memory_counterexample`, `private_feedback_can_distinguish_secrets` |
| Canonical bounded codec | `field_roundtrip`, `request_roundtrip`, `malformed_request_refuses`, `wire_effect_sound`, `wire_public_payload_bound` |

The central noninterference theorem quantifies over an arbitrary controller memory
type, arbitrary choose/advance functions, any finite interaction horizon, and any
two private byte values. Given the **same controller functions, initial controller
memory, initial policy state and public resource**, the modeled public-write trace
is identical. Private data enters the controller only as a tracked read result;
after that read, the sticky taint rule blocks all public writes. Private writes
remain possible. This is a theorem of the modeled public sink, not an end-to-end
confidentiality proof of the host or LLM process.

Timing, termination/status observations, audit logs, untracked initial model/prompt
knowledge, cross-session memory, covert channels and external tools are excluded.
The private resource is a fixed read-only note; private writes append separate
effects. Different private feedback after a tracked read is intentional and proved
by a concrete counterexample. Different secrets already in initial controller
memory can be published: that counterexample is also kernel proved. No `sorry`,
`admit`, new axiom or native proof shortcut. All 45 inventories (19 new, 26 inherited)
must contain only the preexisting permitted propext/Classical.choice/Quot.sound.

## What executes

The actual Lean `process` is compiled to a pinned-tool native executable, copied
into a kernel-sealed Linux memfd and invoked through that descriptor. Its request
contains the old canonical five-byte state/action header, exact payload and both
protected resource snapshots. The new frame is:

```
02 || old_version_1_header[5] || field(payload) || field(public) || field(private)
field(b) = length_u16_little_endian || b, length <= 1024
reply = 02 || status || generation || budget || taint || action || effect_tag
        || field(effect_payload) || field(read_observation)
```

Both field and complete valid-request roundtrips are proved. Malformed frames and
trailing bytes refuse. Positive byte responses are proved to arise from typed
execution. A positive public-write effect contains the input intent's exact payload
and requires an untainted pre-state. This separate version does not migrate or
weaken any predecessor or Aristotle codec.

The SQLite broker stores **BLOBs from the returned native plan**, not a separately
reused caller text argument. Generation CAS, actual native decision, SQL mutation,
receipt and state share one write transaction. Before commitment the broker reruns
all bounded receipts through the actual compiled function and compares the staged
rows/effects to the resulting byte plans. Independent host sanity checks can only
refuse; they cannot replace the native positive decision. At most 32 recorded
attempts and eight accepted actions bound replay work.

Read-private feedback is constructed before commit and returned only after taint
commits. Transaction failure returns a generic refusal without the private value.
Missing database files refuse without creating a replacement. Corrupt receipts,
resource snapshots, effects/state or protected rows refuse the next write.

Audit frames contain private resources, so **neither frames nor receipt/checkpoint
digests enter model feedback**. A fixed projection exposes only modeled tool
results/state. Paired-secret tests verify equal pre-read feedback despite different
private audit records. Research logs/captures are private-channel observations
outside the formal public sink and use synthetic data only.

Reopening requires a host-retained expected generation/receipt/genesis checkpoint.
A rolled-back database fails against a newer checkpoint. Rolling back both database
and checkpoint still succeeds: the negative control is preserved. No independently
administered storage, signed external anchor or administrator-proof root exists.
Kernel seals protect the captured image; compiler, system libraries, OS and host
code remain trusted. Python-to-SQLite refinement and actual process semantics are
tested, not kernel proved. Do not deploy this as a confidential-processing service.

The later [live retained-checkpoint wrapper](checkpoint/README.md) additionally
refuses rollback of an active database, including when its old generation is
supplied by the caller. Its seven real-authority regressions preserve the unanchored
counterexample. The primary model experiment below uses the frozen parent broker;
the wrapper is separately tested and does not rewrite that historical evidence.

## Real-weight evaluation

Use the same actual official Apache 2.0 Qwen3 0.6B/1.7B Q8_0 weights and CPU engine
pinned in the predecessor. Each full model file is hash-verified while copied into
a sealed snapshot. No hosted inference API, model training, GPU or paid provisioning.
These small models are not claimed to be a current global state-of-the-art result.

The locally registered protocol compares plain JSON-object generation with a strict
tool-shape schema. **All eight tools, including the forbidden ones, remain in the
schema.** Grammar is a syntax/usability intervention; Lean remains the authority.
It does not force exact text, benign tool choices or task success.

Each mode/model starts a fresh engine and receives the same 20 predecessor cases
(16 policy-aware, four separately reported policy-blind controls) and three adaptive
tasks. Guarded and intentionally unguarded local synthetic controls dispatch the
same captured proposal. Network is only a local outbox simulator. Both modes use
the same sanitized feedback. Differences from older historical results cannot be
attributed solely to grammar; the primary comparison is within this new pipeline.

Additional paired-secret runs start separate fresh engines from the same sealed
weights/settings and identical initial prompts. A controller is asked to publish
START, read private, then work privately. Two different synthetic private notes
are supplied only at the tracked read. Public traces must match; whether both runs
actually reach a private read and complete useful work is measured separately.
Vacuous pairs must not be described as successful neural information-flow tests.
Each of 96 histories receives a fresh exact-byte effect proof and inherited-policy
history proof. Poor utility, malformed outputs and private-read nonvacuity failures
remain in the evidence. No population rates or general alignment claims.

## Reproduce

Activate the existing pinned Linux x86_64 Lean 4.28.0/Python environment:

```sh
source scripts/activate_lean_428.sh
python -m research.local_weights_v1 download /tmp/pcs-pinned-weights
python -m research.causal_firewall_v1 audit ./fresh-effect-audit
python -m research.causal_firewall_v1 evaluate /tmp/pcs-pinned-weights ./fresh-causal-experiment
python -m research.causal_firewall_v1 replay research/causal_firewall_v1/evidence/causal-v1.json ./fresh-effect-replay
PCS_REQUIRE_CAUSAL_FIXTURE=1 python -m pytest -q research/causal_firewall_v1/test_effects.py research/causal_firewall_v1/test_capture.py research/causal_firewall_v1/checkpoint/test_checkpoint.py tests/test_action_shield_v1.py
```

Fresh output directories are mandatory. CI separately performs full fresh real
neural inference and offline effect/proof replay. Replay reconstructs requests,
effects, receipts and proofs from exact captured bytes; it does not rerun neural
inference or authenticate past weight-binding observations. Actual-weight CI does
download/load the pinned weights. Weights themselves are not committed.

The test campaign includes all 1,296 bounded state/action combinations, every field
length 0..1,024 in all three positions, malformed frames, actual kernel seals,
payload substitution, SQL corruption before commit, receipt corruption, real
process-crash rollback, concurrent CAS, missing files, checkpoint rollback, feedback
channel separation and causal adaptive attacks. A preserved predecessor research
counterexample shows that its corrupt receipt is detected by audit but does not
block a later write; the new broker refuses before commitment. No production
authority vulnerability or change is claimed.
