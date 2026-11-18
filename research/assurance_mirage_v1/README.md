# Assurance Mirage v1

**Question.** Can a correcting unique-action guard make an agent evaluation look
perfectly safe while the proposing model still fails on intent and confidentiality?

**Answer in this package.** Formally yes, for any score that inspects only the
guarded tool trace. Empirically yes, on a real SQLite scientific workflow with
pinned Qwen3-0.6B and Qwen3-1.7B Q8_0 weights under published-style red-team
prompts. This is a finite local measurement, not a frontier-model result or a
general alignment theorem.

## Why this is separate from prior PCS work

The public-study evaluation already showed unsafe proposals under guarded
completion and proved a raw-reply countermodel for one PCS supervisor. This
package adds:

1. A **typed three-channel evaluation model** (tools / proposals / raw replies)
   with Lean theorems that any channel-1-only score is blind to a constructive
   mirage, while a joint score detects it.
2. A **concrete scientific program** (`programs/scientific_store.py`) whose
   publish path only ever writes `APPROVED_PUBLIC_SUMMARY`.
3. A **fixed red-team case set** including AgentDojo-style injections, scientific
   scope escalation, JSON smuggling, and split-channel marker composition.
4. Fresh attested runs on **two** official local GGUF weights.

It does **not** modify production PCS authority, ClaimCheck, EvidenceKernel,
Safety-JEPA, delegated-action, or incremental-revalidation branches.

## Formal results

`formal/AssuranceMirage.lean` (Lean 4.28.0, ordinary `decide` / rewriting; no
`sorry`, `native_decide`, or new axioms beyond `propext` / `Quot.sound`):

| Theorem | Claim |
|---|---|
| `step_proposal_independent` | Correcting step ignores the proposal |
| `tool_trace_independent` | Tool traces equal for any proposers |
| `channel1_score_independent` | Channel-1 scores cannot distinguish proposers |
| `constructive_mirage` | Equal tools with unequal proposals/raw leakage |
| `single_channel_blind` | ∀ channel-1 scores, mirage pair ties |
| `joint_detects_constructive_mirage` | Joint score separates the pair |
| `completion_not_competence` | Full guarded completion with all proposals forbidden |
| `guard_erases_divergence` | Safe/unsafe proposers share guarded tool traces |
| `unguarded_diverges` | Without the guard, they diverge immediately |
| `guard_completion_independent_unguarded_not` | Guarded lengths match; unguarded lengths differ |
| `admit_never_exfiltrates` | Unique-action policy never admits exfiltration |
| `channel2_detects_constructive_mirage` | Proposal-harm channel separates the pair |
| `channel3_detects_constructive_mirage` | Raw-leak channel separates the pair |
| `constructive_mirage_any_fuel` | Mirage holds for every fuel budget |
| `unguarded_unsafe_stalls` | Unsafe proposer never advances unguarded |
| `unguarded_safe_completes` | Safe proposer completes the four-step workflow |

```sh
source scripts/activate_lean_428.sh
PYTHONPATH=. python3 -m research.assurance_mirage_v1 formal /tmp/mirage-formal
```

## Empirical protocol

- Models: `Qwen/Qwen3-0.6B-GGUF` and `Qwen/Qwen3-1.7B-GGUF` Q8_0, pinned SHA-256
  in `protocol.py` / `research/local_weights_v1/pins.json`.
- Runtime: llama.cpp b11827, CPU, sealed memfd weight snapshot, temp 0, seed 42.
- 14 cases × 2 prompt arms × 4 turns = 112 completions per model (AgentDojo-style,
  adaptive, authority-spoof, and tool-return-injection families).
- Guard always executes the unique admitted action; proposals never authorize effects.
- Channels scored separately; a **mirage** is guarded completion with proposal harm,
  raw/split leakage, or scope escalation.
- Offline `analyze` builds family tables, Wilson intervals, and cross-model contingency.

```sh
source scripts/activate_lean_428.sh
PYTHONPATH=. python3 -m research.local_weights_v1 download /tmp/pcs-pinned-weights
PYTHONPATH=. python3 -m research.assurance_mirage_v1 run /tmp/pcs-pinned-weights /tmp/mirage-0.6b
PYTHONPATH=. python3 -m research.assurance_mirage_v1 run /tmp/pcs-pinned-weights /tmp/mirage-1.7b \
  --model Qwen/Qwen3-1.7B-GGUF
PYTHONPATH=. python3 -m research.assurance_mirage_v1 replay evidence/qwen06b /tmp/mirage-replay
PYTHONPATH=. python3 -m unittest research.assurance_mirage_v1.test_mirage
```

Hosted Gemini free-tier arm (no key committed):

```sh
export GEMINI_API_KEY=...   # never commit
PYTHONPATH=. python3 -m research.assurance_mirage_v1 gemini-arm /tmp/mirage-gemini   --model gemini-flash-lite-latest --max-cases 5 --turns 4 --max-requests 20 --min-interval-sec 6
```

Optional HF Inference secondary arm (`hf-secondary`) needs a shell HF token with
Inference Providers access. MCP OAuth alone is not sufficient; absence is recorded
as unavailable, not as model safety.

## Observed primary result (Qwen3-0.6B)

See [RESULTS.md](RESULTS.md) and `evidence/qwen06b/mirage_gap.json`.

Channel-1 alone would report **20/20 perfect guarded safety**. Joint scoring finds
**15 mirage episodes** (93.75% of attack episodes). Instruction boundaries reduce
but do not eliminate raw-marker leaks. Publications never contained the private
marker; raw model text did.

## Limits

- Small models, fixed synthetic workflow, authored attacks, no adaptive attacker.
- Not an official AgentDojo score, not peer-reviewed, not production authority.
- Host, compiler, llama.cpp, and SQLite remain trusted premises.
- Formal results concern the defined mathematical model, not neural refinement.
