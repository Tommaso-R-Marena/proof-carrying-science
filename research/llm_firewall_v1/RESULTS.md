# Compiled Lean enforcement on real hosted open-model proposals

## Qualified experiment, 22 October 2026

The primary run completed at executable-source commit
`f33ae5969b7d00dbffb274aee5bd314e7feb01dc`. Its protocol was recorded before the
first campaign inference, SHA-256
`ee47d181e710eaea8201a38fa80d292e3c22ee969ed8fb7fe4ac06b04ba6e2f9`.
This local registration is an auditable ordering record, not third-party
preregistration or a tamper-proof timestamp. Later evidence/documentation commits
retain the same Python and Lean source bytes.

The portable primary capture is [evidence/live-v1.json](evidence/live-v1.json),
SHA-256 `283dccf58dc9749b17c759105ad95754746ea78af7ddabe660c78ccd712900cf`.
It contains original HTTP response/request bytes, selected transport metadata,
catalog observations, source snapshots, protocol and complete case/agent records.
The experiment made **52 actual inference requests**, using provider-reported
**1052.078432281494 neurons**, on the existing account with an observed empty
subscription list. No account upgrade, deployment, model training or GPU purchase
occurred. Total run time, including fresh Lean compilation and object audit, was
175.851534 seconds. Timing is one observation, not a performance benchmark.

| Observation | Nemotron-3 120B/A12B | Qwen3.8-27B |
| --- | ---: | ---: |
| Policy-aware one-proposal cases | 16 | 16 |
| Same proposals violating policy in unmediated local control | 8 | 4 |
| Policy-blind stress cases (separate cohort) | 4 | 4 |
| Policy-blind local-control violations | 4 | 4 |
| Guarded policy violations across all 20 cases | 0 | 0 |
| Guarded proposals blocked by Lean | 12 | 8 |
| Exact benign utility criteria satisfied | 6/6 | 4/6 |
| Canary-containing local releases after tracked private read, unguarded | 3 | 1 |
| Same tracked canary releases, guarded | 0 | 0 |
| Closed-loop agent tasks completed | 3/3 | 3/3 |

No transport, model-identity or verifier failure occurred in the primary run.
All six actual agents completed the public, private and injected-public tasks
within the four-turn limit. **46 accepted histories** (40 cases, 6 agents) each
received fresh ordinary-kernel Lean certificates, including histories containing
only safe preludes when the subsequent proposal was refused.

Qwen's two benign failures were `PUBLIC_OK.` and `DONE_OK.` rather than the required
exact strings `PUBLIC_OK` and `DONE_OK`. The outputs were policy-permitted and
committed, but correctly failed the predeclared task utility criterion. The
criterion was not relaxed. Safety and usefulness are distinct measurements.

The unmediated controls execute the **same captured proposal** after the same safe
prelude in a separate local SQLite database. They are counterfactual tool tests,
not observed unshielded multi-turn agent trajectories. The network operation only
writes a local outbox; no external exfiltration or real destructive action occurred.
These 40 constructed cases are not a representative sampling distribution and
must not be converted into a population attack-success or model-alignment rate.

## What is actually proved and executed

The [policy](Policy.lean) has 26 named theorems, listed exactly in [README.md](README.md).
Their conclusions cover arbitrary accepted finite histories: no protected deletion,
network operation or privilege grant; exact budget accounting; monotone generation;
sticky private-read taint; no modeled public release after a tracked private read;
and a maximum of eight accepted actions from the initial state.

`private_blocks_suffix` quantifies over arbitrary future accepted proposals after
a private read. `process_sound` connects any positive byte-level Lean decision to
a decoded typed request and accepted transition. `wire_forbidden` excludes forbidden
actions for arbitrary input bytes. `decode_encode` proves the valid-state codec
roundtrip. `run_sound` connects each freshly proved concrete accepted run to the
inductive history specification. There is no `sorry`, `admit`, new axiom or native
decision proof shortcut. All observed closures contain only the existing permitted
`propext`, `Classical.choice` and `Quot.sound` axioms.

The actual tool gate is C compiled from the proved Lean `process` definition.
Linux kernel seals protect a captured executable image against writes/truncation;
inference proposals invoke that descriptor. SQLite generation comparison, Lean
decision, synthetic effect, new state and hash-linked attempt are committed in one
transaction. Public model JSON cannot choose a verifier, executable, file path,
URL, policy or affirmative verdict. This is executable enforcement, not a proof
that an LLM will voluntarily obey a prompt.

## Independent replay and hostile engineering tests

With the existing pinned Lean 4.28.0 Linux x86_64/Python environment:

```sh
source scripts/activate_lean_428.sh
python -m research.llm_firewall_v1 replay research/llm_firewall_v1/evidence/live-v1.json ./fresh-replay
PCS_REQUIRE_LLM_FIXTURE=1 python -m pytest -q research/llm_firewall_v1/test_firewall.py tests/test_action_shield_v1.py
```

Replay uses no API key, network inference or GPU. It snapshots bounded capture
bytes, checks their inventory and the receiving reviewed source hashes, reconstructs
every prompt/context, rebuilds the real monitor, performs `leanchecker --fresh
Policy`, reruns every guarded/control effect and regenerates all 46 history proofs.
It compares reconstructed records against captured originals. Stored success flags
never authorize an operation. Capture hashes establish integrity relationships,
not provider authentication or model-weight identity.

The 72-test focused suite includes 39 new tests and all 33 inherited action-shield
tests. The new tests exercise all **1,296** bounded state/action configurations,
**1,251** invalid single-field byte values and additional truncated/trailing frames;
actual memfd write/truncation refusal; executable-path substitution during invocation;
verifier timeout; strict JSON/operation mapping; eight-way concurrent stale-generation
promotion; rollback after dispatch; actual process exit with an uncommitted SQLite
transaction; receipt corruption; and the complete real-model capture replay.
Focused CI requires the capture: missing live evidence is a failure, not a skip.
Test/CI execution evidence belongs to the tested commit and published run artifacts.

## Negative findings and preserved failed pilot

The [unqualified pilot](evidence/PILOT.md) and its original
[capture](evidence/pilot-v1.json) are retained. Nineteen of 23 requested Gemma4
responses reported a different `-external` backend ID. The identity gate refused
them; the primary run excludes that endpoint. No backend alias or weight equivalence
was assumed. The pilot also exposed a utility-denominator defect. It was corrected
before this primary run and covered by a regression test; the original pilot metrics
are preserved and explicitly unqualified. Formal policy, byte codec and broker
rules were not changed between pilot and primary runs.

Two deliberately retained mechanism limits have executable negative controls:
an untracked initial secret can be published, and harmless public text after a
private read is blocked. The taint mechanism is neither semantic secret detection
nor a complete noninterference proof.

## Trust boundary and scientific interpretation

The mathematical policy and ordinary-kernel histories are formally proved.
Correctness of the Lean/C compiler, shared libraries, OS and hardware remains
trusted. Python parsing/mapping, SQLite effects, complete mediation, context labeling
and faithful capture are tested implementation assumptions. The Python process and
its administrator can bypass this harness; seals and hashes do not establish an
independently administered immutable root. Hash-linked receipts have no external
authentication or anti-rollback anchor.

Only synthetic data were used. API traffic, research logs, untracked model context,
cross-session private memory and covert/timing channels are outside the modeled
public sink. This is not a production confidential-processing service.

These are actual hosted 2026 open-model families identified by provider metadata,
not local verified weight executions. No hosted weight hash/quantization attestation
or independent global state-of-the-art ranking was obtained. Qwen's upstream
metadata reports Apache 2.0; Nemotron has its own open-model license. Do not equate
all open weights with OSI open source. Provider assertions and upstream metadata
observations are not external validation of the safety mechanism.

The supported advance is **a compiled, kernel-proved tool policy with independently
replayable successful enforcement and useful real-model agent execution**. It is
not a proof of general model safety, alignment, neural-network correctness or
accelerating recursive self-improvement. Production PCS authority and every
predecessor source blob/mode remain frozen; nothing is merged or deployed.

## Next research milestone

1. Refine the JSON/SQLite dispatch boundary against the formal transition system,
   including persisted state and effect correspondence; preserve the current codec.
2. Isolate the broker under independently controlled credentials and carry context
   labels across sessions; test actual isolated service adapters and recovery.
3. Evaluate a richer, proved information-flow policy on independently held-out
   public agent-security tasks, with blinded controls and useful-task scoring.
   Benchmark selection and backend-weight uncertainty must remain explicit.

Future Aristotle artifacts require their own exact-source and differential audit;
none were imported or rewritten for this experiment.
