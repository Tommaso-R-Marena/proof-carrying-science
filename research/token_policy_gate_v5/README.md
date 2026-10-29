# Exact token–byte–policy gate (research v5)

This adds a Lean-checked receiving boundary to the existing real-model agent experiment. A model response is eligible only when its exact token list and exact byte list decode to the same canonical action. The existing checked policy then selects an allowed action, potentially correcting the proposal. All recorded model pairs are checked together by real Lean and a fresh kernel checker **before** receiving replay executes any SQL. There is no production authority registration.

## Reproduce

Use the repository's pinned Lean 4.28.0 toolchain and frozen Python requirements. Install the hash-locked Rust tokenizer package from `research/real_model_execution_v2/requirements-tokenizer.lock` and fetch the two pinned tokenizer files:

```sh
python -m research.real_model_execution_v2 fetch /tmp/tokenizer
PCS_TOKENIZER_DIR=/tmp/tokenizer python -m pytest -q research/token_policy_gate_v5
python -m research.token_policy_gate_v5 research/structured_action_lab_v4/demo/trie /tmp/pair-receiving --tokenizer /tmp/tokenizer
```

The output directory must not already exist. The CLI returns 20 with a structured `REFUSED_OR_UNAVAILABLE` result on a verifier, input, storage or resource failure. Inputs are frozen before replay. Submitted Lean source and caller-supplied verifiers are never accepted. The proof compiler and fresh checker are pinned to the existing exact executable hashes. The checker pins its staged source and compiled import sidecars before/after capture checking.

## New kernel theorems

`PairGate.lean` adds 16 declarations in `PCSTokenPolicyGate`:

- `pair_roundtrip`, `pair_sound`, `pair_unique`: canonical token/byte identity and uniqueness.
- `invalid_never_selected`, `mismatched_actions_rejected`: malformed or inconsistent pairs grant no selection.
- `selected_from_choose`, `selected_pair_bound`, `selected_not_forbidden`: selections come from the existing checked policy and bind a canonical pair.
- `selected_all_outcomes`: every declared outcome of a selected action stays safe, stays in the certified region and strictly lowers rank.
- `canonical_available`, `forbidden_corrected`, `unsafe_corrected`: a checked non-goal region state has an available selection; forbidden/unsafe proposals are corrected.
- `erases_to_checked_path`, `adaptive_run_bound`, `adaptive_completion_at_rank`, `no_nonempty_run_at_goal`: arbitrary adaptive admitted histories inherit safety and a finite rank budget, reach a goal at the budget, and admit no action after a goal.

The hypotheses matter: safety refers to the supplied finite transition model and its declared outcomes, with `check d = true` and the initial state in its certified region where required. No theorem forces a model to supply valid tokens, forces the environment to follow declared transitions or proves eventual execution under endlessly rejected input. These are not general neural-alignment theorems.

## Evidence and limits

The local qualification checked all 16 general theorem closures and one concrete 42-pair theorem with the real compiler and `leanchecker --fresh`. All 16 receiving episodes completed through the existing native authority and SQL adapter after that pair check. The 42 pairs are **replays of already recorded real Qwen3-0.6B outputs** from PR #189, not new model inference. Twelve model episodes and four deterministic controls remain separately labeled. Controls are not represented as neural pair certificates.

The unit suite has 22 cases. Six actual Lean tests include unsafe selection, forbidden selection, byte mismatch and missing-EOS adversaries; no affirmative verifier is mocked. The core Lean declarations depend only on the audited standard axioms (`propext`, `Quot.sound` where used), not new axioms or admitted proofs.

The host Python interpreter, compiler invocation, Rust tokenizer, executable hashes' custody, OS, RAM, filesystem and SQL implementation remain trusted. Ordinary source/hash checks are not an immutable security boundary and do not resist an attacker controlling the host. The concrete theorem establishes finite symbolic equality; it does not prove Python/Lean implementation equivalence, tokenizer correctness, model quality or unseen-task competence. Elaboration is limited to 180 seconds, fresh checks to 300 seconds, 2 GiB and 64 pairs; failures refuse before SQL. A previous 180-second fresh-check timeout and a module-label error were retained as failed attempts, not successes.

Future Aristotle codecs require a separate source-pinned compatibility integration. This module imports the current PR #189 codec unchanged and does not assume unavailable V8 or newer PGSI1 artifacts.

## Review boundary

The focused workflow preserves every existing #189 regression, accounting, codec and replay job, then requires the new actual-kernel qualification as well. Its new preservation check permits only added files under this module and its own workflow; all #189 parent blobs and modes must stay exact. It intentionally refuses the broader consolidation candidate. The complete integration needs a separately reviewed successor contract rather than bypassing this narrow gate. Hosted execution of the new workflow is pending.

The compiler and fresh checker are child processes under the same host/user; this does not establish an independently controlled security domain, protected credentials or an immutable root. A checked equality returning `.invalid` is a verified rejection, not execution permission: `kernel_checked` by itself is never an authorization verdict.

Execution also requires every model row to have a selected-action expectation. A native negative-control certificate genuinely proves `.invalid` and passes fresh kernel checking, while the execution-row guard still refuses it. The post-intake data-injection test confirms this refusal happens before an output directory or SQL can be created. Mathematical truth about rejection cannot be promoted into execution permission.

The separate [policy-versioning module](POLICY_VERSIONING.md) adds 18 checked library declarations and three checked cases on the actual agent-lab contract. Together with the 16 interface declarations there are 37 new declarations: 24 general results and 13 constructed-case results. These counts include supporting lemmas. The completed execution qualification has 28 tests with no skips.
