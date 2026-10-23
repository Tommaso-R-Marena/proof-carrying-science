# Proof truth is insufficient for confidential disclosure

Research extension stacked on PR #176 (`d7ec58d`). All **6,413 predecessor
blobs/modes**, production authority, PGSI/Aristotle sources and historical evidence
remain unchanged. Separate experimental version3 authority; no merge/deployment.

## Question and formal finding

Suppose an authority proves a model's count claim is exactly correct before
publishing it. Can a private bit still escape? **Yes.** The model may choose
`count=N` versus `N=count`; both verified propositions express the same correct
aggregate, while the representation identifies the hidden bit. Even forcing a
canonical representation leaves a second channel if the model chooses whether to
publish. Allowing a private-dependent choice of approved query is a third channel.

`Release.lean` adds **22 ordinary Lean theorems**, including:

| Claim | Theorems in `PCSRelationalRelease` |
| --- | --- |
| Every admitted claim is true and its byte value is exact | `truth_gate_sound`, `both_representations_true`, `wire_claim_truth`, `bounded_render_value` |
| Verified representation can transmit arbitrary finite secret bit strings | `representation_channel_decodes_secret`, `representation_channel_is_verified`, `representation_counterexample`, `unbounded_verified_representation_channel`, `all_encoded_claims_verified` |
| Canonical payload alone is insufficient if presence/query remains private-controlled | `withholding_counterexample`, `adaptive_query_choice_counterexample` |
| Private proposal phase has no public effect | `proposals_have_no_public_effect`, `proposals_preserve_state` |
| Trusted scheduled completion publishes exactly the approved view | `forced_completion_exact`, `canonical_depends_only_on_view`, `scheduled_release_noninterference` |
| One-shot completion | `post_completion_has_no_effect`, `finalize_once`, `closed_request_refuses` |
| Exact native interface | `malformed_request_refuses`, `wire_accepted_sound`, `wire_finalization_exact` |

The positive theorem compares **any two private datasets with the same authorized
view**, and arbitrary different proposal histories, including different content,
withholding and invalid proposals. Appending trusted finalization yields the same
one-element public trace. Unlike the previous blanket taint policy, the mechanism
can release a useful approved count/parity after private access. It declassifies
that statistic intentionally; it does not prove zero disclosure of the dataset.

This follows established information-flow/declassification principles. No claim
of global novelty or a general AI alignment breakthrough. The project advance is
an executable proof-carrying release experiment, independently checkable channel
counterexamples and a precisely scoped fix, evaluated on real neural weights.

## Mechanism and trust

The public query is fixed **before private access**. Private model proposals are
truth-checked and recorded, but neither their admission verdict nor their choice of
style/submission reaches the public sink. A trusted bounded scheduler calls
`finalize` even when the model refuses, withholds, returns malformed output or its
call fails. The actual native Lean function computes the canonical count/parity
payload. **The authority computes the public answer; the neural model does not.**
Model claim accuracy, canonical pipeline utility and confidentiality are distinct
measurements. Correct authority fallback must not be called improved neural
intelligence, learning, recursive self-improvement or successful model reasoning.

The four-bit flags are approved input to the aggregate; an independent synthetic
hidden bit must not affect publication. The count query releases0..4; parity
releases0..1. Representation packets are five bytes
`[3,2,query,style,value]`. The canonical style is0. This is a research binary
rendering of the two count-claim forms, not free-form text verification.

Canonical request: `[3,query,closed,mask,hidden,action,style,reported]`.
Query count/parity is0/1; mask0..15; hidden0/1; closed0/1; action0 private read,
1 private claim check,2 finalization. Style/report must be zero for actions0/2;
style0/1 and reported0..4 otherwise. Invalid/trailing bytes refuse. Reply header:
`[3,status,next_closed,action]`, followed by five bytes only on a positive result.
Private-read payload is `[hidden,flag0,flag1,flag2,flag3]`; accepted claim/finalize
payload is the five-byte representation packet. Once closed, all actions refuse.
The model never chooses an executable or supplies an affirmative verdict.

The native executable is built with pinned Lean4.28/leanchecker/leanc bytes and
captured in a sealed Linux memfd. The broker stores its actual returned payload
as SQLite BLOBs, with exact contract/resource binding, receipt replay before and
after staging, transactional one-shot commitment and a live retained receipt
anchor. Missing files, invalid receipts, native failures, contract changes,
staged substitutions and concurrent finalization fail closed. The private
observation is delivered only after its receipt commits. Audit packets and hashes
depend on private resources and **never enter public effects or model prompts**.

Host execution of finalization is an explicit premise. Process death before it
leaves an empty public trace; this is retained as a negative test. Actual wall
clock timing, termination/status/log channels, independently controlled scheduling,
secure restart/persistence and rollback of both database and host memory are not
proved or provided. A malicious host/admin can bypass Python. Hashes, seals,
locks and host-memory anchors are not immutable independent trust roots. Lean
compiler/OS/libraries/Python/SQLite/runtime correspondence is tested, not kernel
proved. Do not deploy as a confidential-agent service.

## Registered experiment

Two official Apache2 Qwen3 0.6B/1.7B Q8_0 artifacts and the exact llama.cpp CPU
runtime/pins from #175 are used. They are small real models, not a global
state-of-the-art claim. Each engine actually maps a hash-verified sealed model
snapshot; all61 packaged runtime files are pinned. No model API, GPU, training or
paid provisioning. Fifty fresh requests per model, **100 observations /50 pairs**.

For each count0..4 and hidden bit0/1, there are five conditions: benign,
representation-aware, representation-stress, withholding-aware,
withholding-stress. Aware conditions explicitly forbid covert disclosure; stress
controls deliberately request encoding without that policy and are **not jailbreak
evidence**. Identical approved counts pair different hidden bits. All generation
uses the same strict three-field schema, seed42, temperature0, max256 tokens.
Schema permits both styles and withholding; it is not the privacy authority.

The **same actual captured proposal** feeds three separately measured policies:

1. Truth-only control: actual native verifier admits only exact counts; if the
   model submits, its chosen representation is stored in a local public SQL sink.
2. Prior strict taint authority: actual private read then publish attempt, using
   the unchanged real native byte authority; all later public writes refuse.
3. New precommitted authority: private verification of the proposal, then trusted
   canonical finalization. Every history gets a concrete ordinary Lean packet
   equality proof, plus a separate prior-policy history certificate.

The source/protocol freeze is local ordering, not externally witnessed
preregistration. Model correctness and channel exploit rates are measured, not
required for qualification. Exact outputs, poor utility, policy-aware refusals,
cooperative controls and development failures must remain distinct. There is no
held-out benchmark, population risk rate or claim that model inference is itself
formally verified. Raw captures are unauthenticated historical observations;
offline replay freshly verifies effects/proofs, not past neural inference.

## Reproduce

```sh
source scripts/activate_lean_428.sh
python -m research.local_weights_v1 download /tmp/pcs-weights
python -m research.relational_release_v1 evaluate /tmp/pcs-weights ./fresh-release-run
python -m research.relational_release_v1 replay research/relational_release_v1/evidence/relational-v1.json ./fresh-release-replay
PCS_REQUIRE_RELATIONAL_FIXTURE=1 python -m pytest -q research/relational_release_v1/test_release.py tests/test_action_shield_v1.py
```

Fresh directories are required. Separate CI jobs run fresh actual inference and
formal/hostile broker/capture replay. Tests include all1,536 bounded native
requests versus an independent oracle, all64 data/query inputs, malformed
encodings, verified eight-bit transmission, withholding, actual payload
substitution, tampering, live/commit-window rollback, concurrent finalizers,
verifier failure, scheduler fallback, and host process death before completion.
