# Actual downloaded-weight experiment

On 22 October 2026 the full CPU campaign completed with **62 actual local neural
inference requests, 40 single-proposal cases, six closed-loop tasks and 46 freshly
kernel-checked accepted histories**. It used no hosted inference API, GPU or paid
compute. The machine's cgroup allowed two CPU cores and 8 GiB memory. The 287.581582
second run includes the fresh Lean build/object audit. This timing is a single
observation, not a comparative performance benchmark.

## Exact artifacts and source binding

| Official Apache 2.0 GGUF release | Complete downloaded bytes | SHA-256 |
| --- | ---: | --- |
| Qwen3-0.6B Q8_0 | 639,446,688 | `9465e63a22add5354d9bb4b99e90117043c7124007664907259bd16d043bb031` |
| Qwen3-1.7B Q8_0 | 1,834,426,016 | `061b54daade076b5d3362dac252678d17da8c68f07560be70818cace6590cb1a` |

Fixed repository revisions and public download URLs are in [pins.json](pins.json).
The actual files were streamed and hash/size-checked against the official pinned
metadata, then hashed again while copying into kernel-sealed memfds. The engine
loaded `/proc/self/fd/<fd>`; its observed mapped sealed weights are recorded in
each `engine-N/binding.json`. Each memfd had all four required seals (mask 15).
Inference did not reopen the mutable original model pathname.

The actual CPU engine is llama.cpp `b11827`, commit
`970b51ce7c9ba5fff0726c5e9994f1c2f0e4eedc`. Its downloaded release archive hash is
`7c1de2b2a139aa90e28b88d44a75f5966485604f68aa0ccdc2339959bca9b5f6`;
all 61 packaged runtime file hashes were checked. This release binary was not
independently rebuilt or formally refined. Compiler/system libraries/native
inference numerical correctness and host behavior remain trusted.

Registered source commit: `8d7663cc7957fad1af6fece092f9e2dd2e5225d8`.
Protocol SHA-256: `55e7e8a88e654be3f45022788e8da655b624ab39b83c3b8e2397f282650fcbde`.
Later documentation, workflow and generated-bytecode cleanup do not change the
registered Python/Lean inference/enforcement bytes. The source snapshots are
embedded in the portable capture; the receiving replay requires exact equality.
Registration is a local ordering record, not external scientific preregistration.

Portable [original capture](evidence/local-v1.json) SHA-256:
`0e7b7938420e78a3699b58dabfcc945e63a06f2cf8475b5e05f9dcd0457e2a3b`.
Weights themselves are intentionally excluded from Git and the capture. Temporary
copies can disappear with this execution environment; exact public redownload
instructions remain available in [README.md](README.md).

## Results, including failures

| Observation | Qwen3-0.6B | Qwen3-1.7B |
| --- | ---: | ---: |
| Actual campaign inference requests | 32 | 30 |
| Single-proposal cases | 20 | 20 |
| Policy-aware local-control violations (16 cases each) | 5 | 9 |
| Policy-blind local-control violations (four separate controls each) | 3 | 1 |
| Valid proposals blocked by the compiled Lean policy | 8 | 10 |
| Malformed proposals refused by strict host parsing | 7 | 6 |
| Guarded policy violations | 0 | 0 |
| Exact benign utility criteria met | 5/6 | 4/6 |
| Closed-loop tasks completed | 0/3 | 1/3 |
| Canary-containing local-control releases after tracked private read | 1 | 2 |
| Same tracked canary releases, guarded | 0 | 0 |

All 62 requests produced complete, nontruncated local responses. No inference
transport or Lean-build failure occurred. All 13 refused single-proposal outputs
failed the exact JSON tool/argument schema; they are not misreported as positive
Lean verdicts or as Lean-blocked attacks. Strict host parsing and formal policy
enforcement are separate mechanisms.

The 0.6B model failed the last-unit finish criterion. The 1.7B model failed both
finish criteria. The associated malformed proposals were refused; no criterion
or parser restriction was relaxed. Both models often failed multi-turn tool
formatting after a successful first read. Only the 1.7B private-read/private-store
task completed; both public and injected-public tasks failed for both models.
These are negative capability results, not evidence of strong general agents.

Before inference, the protocol declared task success to be measured rather than
a qualification requirement. `complete=true` means all specified observations
were collected and guarded-policy checks passed. It does **not** mean the models
completed every task. Deterministic seed 42, temperature 0, 256-token limit,
JSON-object syntax constraint and thinking-off settings are captured exactly.
The syntax constraint permits arbitrary JSON objects and does not enforce safety.

Control effects are synthetic local SQLite operations on the same captured
proposal and prelude. Network is a local outbox simulation. No real exfiltration,
production deletion or privilege escalation occurred. No independently observed
unshielded adaptive trajectory or population attack-success estimate is claimed.

## Proofs, independent tests and CI

The predecessor's **26 general Lean theorems** are unchanged. They quantify over
arbitrary accepted actions independently of neural weights: forbidden-operation
exclusion, exact budgets, generation progression, sticky private-read taint,
public-sink exclusion on accepted suffixes, byte-level decision soundness and
accepted-run/history correspondence. Each of the 46 recorded accepted histories
receives two fresh ordinary-kernel theorems. No new axioms, `sorry` or native proof
shortcut is introduced.

The focused suite contains **89 tests**: 17 local-weight tests plus all 72
predecessor tests. It requires actual fresh CPU inference from both pinned models,
weight-snapshot write/truncation refusal, source-path substitution controls,
corrupted download/capture refusal, source preservation and independent replay of
both the local-weight and earlier hosted captures. Test execution counts belong
to the tested commit and CI run; exact final evidence is linked from the PR.

CI also downloads both real weight files and runs the entire 40-case/six-agent
campaign with fresh neural inference, compiled authority and history certificates.
This is separate from offline captured-response replay. Hardware may change neural
outputs despite fixed settings; fresh CI observations must be reported separately,
not overwritten with the original run's expected utility scores.

## What this establishes

The experiment replaces the earlier hosted-only weight-identity limitation with
actual local released weight bytes, complete SHA-256 identities, sealed weight
loading and real CPU generation. It independently exercises the same proved
tool-policy mechanism while retaining poor model/task outcomes.

It does not formally verify neural arithmetic, quantization correspondence,
general model alignment, semantic confidentiality or global state-of-the-art
status. These small models are distinct from the previously observed 27B/120B
hosted endpoints. Tested Python/SQLite effects, correct context labeling, complete
mediation and trusted compiler/runtime/OS behavior remain explicit assumptions.
Hash inventories and local process observations are not an administrator-proof
attestation root. The untracked-secret and conservative-taint negative controls
still apply. No production authority, predecessor file or Aristotle module changes.
