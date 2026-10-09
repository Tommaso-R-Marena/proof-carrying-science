# PCS Omega v1: a reproducible experimental reasoning loop

This first Omega cycle implements a narrow vertical slice: explicit scientific source → typed Boolean interpretation → existing Claim IR / Proof Obligation Graph → budgeted repair actions → CPU-trained ranking → independently checked result → replayable learning feedback. It does not implement a general scientific language model, automatic interpretation of papers, arbitrary program execution, or autonomous scientific discovery.

## Run the actual loop

Install the normal PCS Python environment. No NumPy, Torch, GPU, model API or model download is required. Lean checking requires the project-pinned Lean 4.28.0.

```bash
pcs omega intake examples/omega/project.json -o intake.json
pcs omega search examples/omega/task.json --checks 8 -o episode.json
pcs omega replay episode.json
pcs omega reproduce --output NEW_RUN --seed 20261009 --per-family 24 --epochs 24 --bandit-episodes 1600
pcs omega verify-lean NEW_RUN
pcs omega search examples/omega/task.json --strategy learned --model NEW_RUN/models/graph.json -o learned-episode.json
pcs omega check examples/omega/task.json --lean-output original-false.lean
```

The last command deliberately returns exit 1 because the example candidate is false. `lean original-false.lean` must reject it. Invalid inputs return 2; an exhausted search returns 1. JSON outputs and experiment directories refuse replacement. `check --lean-output` emits proof *source*, never a claim that the kernel ran.

`generate`, `train`, `evaluate`, `bandit`, `env`, `impact` and `memory` expose the individual stages. `pcs omega --help` and each subcommand's help document their arguments. `env` consumes a task and a bounded JSON action list; rewards come from its checker, not action-supplied labels. `impact --changed CLAIM_ID` conservatively reopens explicitly declared dependent claims.

## Scientific intake and canonical formats

`pcs-omega-project-v1` is a versioned envelope around the **existing** `pcs-claim-ir-v1` and `pcs-proof-obligation-graph-v1`, rather than a replacement authority format. Each claim specifies an exact source line range, a statement occurring there, an explicit interpretation, scope, assumptions, and an acyclic dependency list. The source's UTF-8 bytes and separate name/revision/license metadata are committed; receipts bind the exact task and interpretation. Existing semantic compilation independently checks the zero-arity typed predicate fragment. Declaring an experimental registry digest does not approve the registry or the scientific meaning.

Interpretations admit 1–4 sorted Boolean symbols, seven operators (`atom`, `true`, `false`, `not`, `and`, `or`, `implies`), at most 63 nodes and depth 8. Numbers, units, quantifiers and executable code are rejected. An example protocol models review and tests as Boolean predicates; whether these predicates describe a real protocol remains an external assumption. This cycle accepts explicit JSON projects, not raw-paper understanding.

All scientific claims retain blocking obligations for intent grounding and registered authority. A mismatch adds a concrete counterexample obligation. A successful repair removes that mismatch when recompiled, while grounding and authority remain blocked. Dependencies identify conservative invalidation within the declared graph; their completeness is not proved. No experimental receipt becomes a trusted production premise automatically.

## Search and independent acceptance

Candidate edits use a closed action vocabulary: insert/remove negation, swap binary operands, or replace a binary connective at a typed path. The original goal is immutable. Enumeration is deterministic, capped at 128 actions, and deduplicated by canonical candidate digests. Search limits depth to 4 and checker calls to 128, including the initial check. Strategies are BFS, seeded random, structural distance, and learned action ranking. Every visited proposal is checked; an exhausted run records exhaustion without a guessed answer.

The Python checker evaluates **all** valuations (at most 16). Episode replay regenerates every action, checks original source and parent commitments, replays every receipt, rejects transitions after success, validates budgets and terminal state, and only then permits memory retention. Hashes ensure binding, not truth; even rehashed forged receipts are rejected. Independent browser JavaScript provides a second implementation. Fixed Lean templates prove concrete solved Boolean equalities; they do not prove equivalence of the Python interpreter and Lean compiler, or scientific intent.

## Dataset and model cards

The generator produces first-party synthetic Apache-2.0 tasks with eight fixed families. Training uses connective confusion, negation loss and swapped implication. Validation uses nested connective changes. Test uses De Morgan, implication expansion, distribution and absorption. Alpha-normalized source fingerprints and normalized source/candidate truth pairs are deduplicated across the complete corpus. This prevents those exact duplicates; it is not a proof of absence of every possible semantic or statistical leakage. Public family holdouts are **not blind** evaluation or external research tasks.

Labels are recomputed from the checker for each legal action. No participant data, imported papers, downloaded proof solutions, personal information or hinted game sessions train these models. The provenance tag describes the controlled generator; it is not evidence that an arbitrary imported corpus has consent or rights. This version only accepts the generated-corpus contract.

The bag model is a 38-parameter weighted logistic ranking head. The graph model is a 91-parameter head using a fixed two-round mean-message AST encoder, parent type, edge kind and local source correspondence. The encoder is **not** trained; this is a graph-feature experiment, not an end-to-end GNN. Both use pre-action syntax and context, never future checker feedback or labels as input features. SGD uses seed 20261009, positive weight 8, rate 0.03 and L2 0.0001. Checkpoints contain actual nonzero learned weights, exact training task digests, corpus binding and source-code digest. The checkpoint corpus digest covers training records only.

`ReasoningEnv` is a genuine constrained transition/reward interface: candidate repair, equivalence check, counterexample request, and abstention. Invalid actions consume budget. A verified repair earns 1; unsuccessful checks cost 0.02; invalid actions cost 0.1; abstention earns 0. The goal cannot be supplied by an action. Observations are copies. The baseline policy trains a real one-step contextual REINFORCE bandit (rate 0.08) from actual checker rewards. It demonstrates this interface, **not** long-horizon RL, learned theorem proving or robustness to arbitrary adversarial Python agents. Models supply JSON decisions; they do not execute Python in this process.

Evaluation compares BFS, random and strong structural search against the bag, graph and bandit heads at matching checker budgets. Inference and feature costs differ, so actual wall times are reported separately. Whole-family results, failures and descriptive Wilson intervals are retained. One seed and correlated generated tasks do not justify statistical superiority or generalization claims. If learning loses to a deterministic strategy, retain that strategy as the default. The full experiment's `REPORT.md` records the actual measurements, including negative results.

## CertiForge and execution boundary

`pcs omega optimize-check PACKAGE --proposal PROPOSAL --checker BINARY --checker-sha256 SHA --checker-source-commit COMMIT` routes through the existing pinned CertiForge adapter. Successful finite-domain checks produce the existing research claim graph, retaining its four unresolved obligations. Use `scripts/run_certiforge_integration_v1.py` for the actual u8 OR optimization, independently checked across 65,536 input pairs, and the malicious rebound-program rejection control. This cycle does not train an optimization policy, prove a Rust/Lean refinement theorem, or claim compiler-general speedups.

Untrusted project text and model files are data. No arbitrary Lean, Python or shell program is accepted. Proof execution first compares templates against exact regeneration from replayed tasks, pins Lean 4.28.0, removes inherited API credentials and sets wall timeouts. AST bounds constrain generated proofs. This is a fixed-template execution boundary, not a general-purpose hostile-code sandbox. Manual editing of proof files is rejected by `verify-lean`. Models cannot approve proof authority, overwrite the checker or register scientific claims.

## Reproducibility and acceptance

`reproduce` writes corpus, actual checkpoints, reward trace, per-task evaluation, complete test graph trajectories, replayed memory, positive and negative Lean templates, source commit/dirty state, exact module digest, Python/platform metadata, counts and timings. `verify-lean` adds actual kernel outcomes and theorem axiom inventory. Deterministic training is tested; wall timings naturally vary. Required public CI repeats a bounded real experiment and the positive/negative Lean controls, alongside all existing kernel, semantic, serialization, Mathlib and CertiForge gates.

See [the source integration audit](OMEGA_SOURCE_AUDIT.md) for prior capabilities and the remaining research program. The canonical production checker, approved registry, receipt issuer and finite-countermodel game contracts remain separate from this experiment.
