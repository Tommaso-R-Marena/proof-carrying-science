# Public-study transfer: actual weights, guarded effects, and output boundaries

This evaluation tests five published AgentDojo attack templates against actual
Qwen3-0.6B and Qwen3-1.7B Q8_0 weights. It examines a concrete question: can an
apparently successful, proof-guarded workflow conceal failures in the proposing
model? The observed proposals say yes. The separately proved tool-trace result
explains why completion in this particular workflow cannot measure competence.

## Observed results

Each row includes 13 attack cases and five benign controls. Every planned case is
retained; there was no response selection, prompt tuning, training or model API.

| Model | Prompt | Correct next action | Unsafe/forbidden proposal | Malformed | Raw synthetic private marker |
|---|---|---:|---:|---:|---:|
| Qwen3-0.6B Q8_0 | plain | 5/18 | 8/18 | 4/18 | 3/18 |
| Qwen3-0.6B Q8_0 | instruction boundary | 14/18 | 3/18 | 1/18 | 0/18 |
| Qwen3-1.7B Q8_0 | plain | 11/18 | 5/18 | 2/18 | 2/18 |
| Qwen3-1.7B Q8_0 | instruction boundary | 15/18 | 2/18 | 1/18 | 1/18 |

There were 45 correct action-2 proposals, 11 premature-publication action-3
proposals, seven forbidden-bypass action-5 proposals, eight malformed responses,
and one idle action-4 proposal. Private-marker counts overlap other columns.
All 20 benign controls proposed the correct action. The 52 attack cases yielded
25 correct action proposals. Stronger instructions helped descriptively but did
not eliminate failures; even the larger model with the stronger prompt printed
the synthetic private marker once.

Every producer episode admitted action 2 at the attacked state, completed four
actual guarded tool transitions, and published only `APPROVED_PUBLIC_SUMMARY`.
There were zero private publications in the 72 producer episodes. These are
real native Lean/SQLite executions, not predicted or mocked verdicts. Unsafe
proposals were never executed ungated; the underlying SQL adapter also has its
own checks. Shield-driven completion is not a model capability improvement.

The private marker was deliberately supplied in the trusted system prompt and
matches the synthetic SQL fixture. Raw model text was recorded locally, not
forwarded to an attacker. Its appearance demonstrates a failure to follow the
specified nondisclosure instruction and a potential extra output channel, not
measured real-world data theft. A tool-only safety claim must not silently cover
raw replies, logs, timing, or arbitrary tools.

## Study identity and scope

- Primary study: Debenedetti et al., [AgentDojo, NeurIPS 2024 Datasets and Benchmarks](https://proceedings.nips.cc/paper_files/paper/2024/hash/97091a5177d8dc64b1da8bf3e1f6fb54-Abstract-Datasets_and_Benchmarks_Track.html).
- Upstream AgentDojo v0.1.35, commit `a75aba7631d3ca5fb7ab938965c97ead2f9ff84b`.
- Selected published templates: `DirectAttack`, `IgnorePreviousAttack`,
  `SystemMessageAttack`, `ImportantInstructionsAttack`, `DoSAttack`. Original
  spelling and template bytes are preserved. Upstream Python was AST-parsed as
  data and never imported/executed.
- Four goal variants for each of the first four templates, plus DoS and clean
  cases: 18 cases, two fixed prompt arms, two models, 72 actual calls. Five cases
  per arm/model are benign controls. Both prompt arms state the correct action.
- Case census, goals, order, seed 42, temperature 0, maximum 256 tokens, source
  hashes and weight/runtime identities were registered before any generation.
  Fixed seeds do not promise bit-identical neural regeneration across hosts.
- Official 0.6B weights revision `23749fefcc72300e3a2ad315e1317431b06b590a`,
  639,446,688 bytes, SHA256
  `9465e63a22add5354d9bb4b99e90117043c7124007664907259bd16d043bb031`.
- Official 1.7B weights revision `90862c4b9d2787eaed51d12237eafdfe7c5f6077`,
  1,834,426,016 bytes, SHA256
  `061b54daade076b5d3362dac252678d17da8c68f07560be70818cace6590cb1a`.
- llama.cpp b11827, commit `970b51ce7c9ba5fff0726c5e9994f1c2f0e4eedc`.
  Exact executable/library inventory is pinned; inference consumes a verified,
  sealed memfd weight snapshot, with two CPU threads and no GPU/hosted model API.
- Base commit `1e165ba06b4833a0e3fbcca2f654b581837acb68` on local branch
  `research/public-study-validation-v1-20261029`. Registration explicitly records
  working bytes and dirty flags; the base commit is not claimed to contain the
  new implementation. All 4,817 parent files and modes are preserved.

This is **attack-template transfer into a fixed PCS-authored synthetic workflow**.
It is not the full AgentDojo suite, its original environments, an official attack
success rate, a representative sample, frontier-model evidence, blind external
validation or an external design-partner workflow. The host explicitly performs
load/review/propose/finish; it does not test autonomous long-horizon task planning.
Training contamination is unknown. No general statistical or causal conclusion
is drawn from these fixed paired cases.

## Replay and interruption handling

The original producer process ended after 52 complete guarded episodes; its exit
cause was not retained. All 72 raw model responses had already been saved. The
partial original directory was preserved. `finish_recorded.py` checked the full
original generation census and request/response/proposal bindings, copied the
52 complete captures, and created fresh ledgers for the remaining 20 episodes.
It performed **zero new model calls**, adopted no old ledger/executable, did not
execute submitted proof code, and did not overwrite the interrupted evidence.
An incomplete episode's database was not resumed. Recovery is diagnostic
research tooling, not a protected restart/storage mechanism.

Review found that the original v1 receiving reader reads registration and
measurement headers twice. A concurrent rewrite could make the input digest
refer to bytes other than those first parsed. The original generation package
and historical source hashes remain byte-exact. The **current receiver is
`receiving.py` in this directory**; use it instead of the historical v1 replay
command printed in the frozen generation README. CI calls the new receiver.
A preliminary v1 receiving attempt was deliberately stopped during native build;
no complete v1 replay result is claimed.

The new receiver hashes and parses each header from the same frozen bytes,
checks all 72 raw request/response/proposal/capture bindings and rechecks every
named input before creating output or tool effects. It uses immutable captured
bytes during execution, checks inputs and source bytes again afterward, and
records its own source digest. An ordinary trusted host remains a premise.
Receiving regenerates the fixed authority and all wire, row and path proofs;
it does not adopt producer verdicts or re-prove that recorded neural computation
occurred. Replay is a separate process on the same host, not an external reviewer
or independently administered machine.

The hardened receiving run passed **72/72 episodes**, with **288 actual tool
transitions and 216 freshly checked generated wire/row/path proofs**. Every
receipt and final state matched its capture. A separate read-only inspection of
all 72 receiving SQLite databases found only the approved public summary and
sanitized payload, state 4/generation 4. `recorded/post-run-audit.json` retains that
inspection and independent metric recalculation. This post-run audit checks
consistency; it does not substitute for the actual receiving Lean runs.

## New mathematical analysis

`proofs/OutputBoundary.lean` adds six declarations in `PCSPublicStudy`:

1. `choose_proposal_independent`: when each modeled state permits at most one
   action, the supervisor choice is identical for any two optional proposals,
   including invalid/absent proposals and inactive states.
2. `adaptive_tool_trace_independent`: for arbitrary bounded fuel and state-history
   adaptive proposers, the modeled state trace is identical under the same fixed,
   history-dependent outcome resolver.
3. `projected_tool_trace_independent`: any projection of that state trace agrees.
4. `actual_spec_unique`: the actual study's fixed specification satisfies the
   unique-action premise.
5. `actual_adaptive_trace_independent`: instantiates the adaptive result for that
   specification.
6. `raw_reply_channel_countermodel`: equal modeled tool traces can coexist with
   a differing private bit on a separate raw-reply channel. Tool trace equality
   alone therefore does not imply full-output noninterference.

All six compiled with Lean 4.28.0, all dependency sources were rebuilt in a fresh
directory, and `leanchecker --fresh OutputBoundary` passed. Each axiom closure is
exactly `[Quot.sound, propext]`; no new axioms or proof holes were added. The
outcome resolver is explicitly coupled between runs. This proves mathematical
statements about the defined model, not Python/C/OS refinement, external tool
behavior, neural safety or the empirical failure rates. This is post-study
mathematical analysis, not a preregistered empirical hypothesis.

## Validation and reproduction

The combined focused suite passes **38 tests, zero failures/skips**: 17 generation,
source/license/codec tests, 18 complete actual-capture corruption cases, two header
rewrite races, and one full frozen-input census. Corruptions cover fake admitted
actions/effects, request/response bytes, weight/runtime claims, remote API claims,
source/plan identity, paths, symlinks, missing inputs and ambiguous JSON. Every
negative case refuses before any receiving output/effect. Only the filesystem
race reader is instrumented; no positive verifier or model result is mocked.

```sh
source scripts/activate_lean_428.sh
python -m pytest -q research/public_study_validation_v1/test_study.py
PYTHONPATH=. python research/public_study_validation_v1_results/check_proofs.py /tmp/fresh-output-boundary
# Replay the retained actual generation without downloading weights or an API:
PYTHONPATH=. python research/public_study_validation_v1_results/receiving.py \
  research/public_study_validation_v1_results/recorded/producer /tmp/fresh-study-receiver
python -m research.public_study_validation_v1_results.audit_results \
  research/public_study_validation_v1_results/recorded/producer /tmp/fresh-study-receiver /tmp/fresh-study-audit.json
PCS_PUBLIC_STUDY_EVIDENCE=research/public_study_validation_v1_results/recorded/producer \
  python -m pytest -q research/public_study_validation_v1_results/test_recorded_evidence.py
# Fresh neural generation requires the pinned ~2.5 GB downloads:
python -c 'from pathlib import Path; from research.public_study_validation_v1.runtime import download; print(download(Path("/tmp/fresh-study-weights")))'
python -m research.public_study_validation_v1.study run /tmp/fresh-study --weights /tmp/fresh-study-weights
PYTHONPATH=. python research/public_study_validation_v1_results/receiving.py /tmp/fresh-study /tmp/fresh-study-receiver-2
```

Use fresh, nonexistent output paths. The workflow performs focused source tests
and the six-theorem proof check on PRs. Full neural generation, actual receiving
and the recorded-evidence negative suite require explicit manual dispatch with
`real_models=true`; a green unit job alone is not real-model qualification.
Repository integrity, additive parent preservation and workflow YAML/pinned-action
checks passed locally. The 72-episode receiving native build also passed its existing axiom audits and
fresh object check. At the original local qualification freeze, no implementation commit/push,
merge, deployment or hosted CI run had occurred. Current publication/CI state is
reported in the [integration record](../../docs/integration/2026-10-29/README.md)
and its linked GitHub checks. These later events do not rewrite the original
source registration or measured results. PR #117 remains held. Byte-exact upstream licenses
retain CRLF/trailing whitespace; authored changes pass the scoped whitespace check.

## What this resolves, and what remains external

The new work supplies missing fresh public-study-derived model measurements,
retained raw evidence, a concrete output-boundary counterexample, stronger
receiving preflight and independently checkable mathematical analysis. It does
not close issues whose exit criteria require actual third parties:

| Issue | Technical evidence improved | Remaining exit criteria |
|---|---|---|
| [PCS #9](https://github.com/Tommaso-R-Marena/proof-carrying-science/issues/9) | Existing key/retention controls remain implemented; reproducible research handoff improved | Counsel-reviewed terms, approved entity/payment path where needed, exercising controls in a genuine partner workflow |
| [PCS #11](https://github.com/Tommaso-R-Marena/proof-carrying-science/issues/11) | Exact AgentDojo MIT and model/runtime notices, revisions, source bytes and hashes retained | Independent contributor/third-party rights review and incomplete historical disclosure inspection; no zero-finding clearance |
| [PCS #13](https://github.com/Tommaso-R-Marena/proof-carrying-science/issues/13) | Public-study adaptation and same-host fresh receiving evidence | Real external party prospectively defines/freezes 3–10 claims, second environment/reviewer, feedback and delivery acceptance |
| [PCS #14](https://github.com/Tommaso-R-Marena/proof-carrying-science/issues/14) | No paid-pilot claim fabricated | #9/#11/#13 and actual commercial/legal/payment arrangements |
| [Website #2](https://github.com/Tommaso-R-Marena/proof-carrying-science-site/issues/2) | Existing public source/Workers hostname remain available | Optional long-term domain, contact and branding decisions |

Official model licenses and source notices narrow provenance for these new
inputs; they are not independent legal advice or whole-history clearance. Tensor
Trust's primary study and public data listing were inspected, but an explicit
dataset license was not established, so that dataset was not selected or
redistributed. No private participant data or untrusted Aristotle traces were
used for training. Production authority and Aristotle formal work are unchanged.

The next useful research step is an adapter for a genuinely externally defined
workflow with multiple meaningful admissible actions, explicit raw-output policy,
and independent replay. The next empirical extension is a pinned official
benchmark/environment integration with task success and attack success separated,
followed by larger model comparisons within available compute. Neither step
should turn local guard completion into a claim of general AI safety.
