# Checked mathematical reuse and verified feedback learning

This release adds executable checked-lemma reuse, a trainable goal/premise graph retrieval head, richer actual Lean actions, and a verified feedback cycle. Every mathematical success is independently compiled against the original typed theorem; the model never supplies acceptance or rewards. Existing Boolean reasoning, Aristotle reference proofs, PCS authority, scientific adapters and CertiForge remain intact.

## What runs

`LibraryEnvironment` reconstructs up to 16 lemmas exclusively from bounded typed declarations and constrained actions, compiles each proof, checks its transitive axioms, then compiles a fixed module. It binds requests to exact module/source/receiver digests and rejects artifact tampering even for cached observations. Module writes are atomic. A fresh final compiler verifies the original theorem. A source-bound receipt carries the entire library and can be independently rebuilt. Forward/cyclic references, producer flags, raw source, reserved namespaces and exact alpha holdout duplicates are rejected.

The research planner can actually apply preceding checked results through `investigate(..., reuse=True, source_license=..., source_revision=...)`. Dependencies still gate eligibility. Returned plans expose available verified nodes and construction costs. This is explicit scheduling and verified reuse, not learned research planning or autonomous discovery.

The receiver now offers typed local-variable existential witnesses, quantified equality rewriting, and six real Nat/Int order signatures. Metavariable-aware retrieval checks consistent structural substitutions and ignores binder display names; it is only a hint and never authorizes an action. Actual proofs cover unbounded natural numbers, integers, quantified predicates, function congruence and multi-edge order chains. No truth-table simulation substitutes for Lean.

The public and local lab can run the trained reuse portfolio, inspect actual lemmas/goals, download standalone proofs including their dependencies, and compare measured baselines. The portfolio reserves one quarter of the expansion budget for learned shortcuts and the remaining actual budget for basic symbolic actions. It attributes the final proof to the stage that checked it. Both stages retain the immutable original statement. Local servers amortize their checked library construction; standalone CLI commands report it separately.

## Models and actual training

Each reuse network has **11,620 trainable parameters**: the existing 10,419-parameter term/state graph model plus trainable goal-query, premise-key and premise-gate layers consuming actual kernel-extracted signatures. Graph and bag variants have equal parameter counts. Two learned message-passing rounds are used by the graph version. Checkpoints are SHA256-bound JSON arrays, never executable pickle.

V1 trained graph and bag policies for seeds 17/31/47, 12 epochs over 14 verified transitions, followed by two real sequential actor-critic generations of six episodes per seed. This produced 15 frozen checkpoints, 36 RL episodes and 129 actual environment steps. All six RL runs changed weights. V1 took 357.63 elapsed seconds on available CPU with two PyTorch threads; GPU use and added financial expenditure were zero. Its 4,265 instrumented parent-environment requests exclude nine independent library-reload replays and any probe setup: they are not a complete CPU consumption metric. The nine reloads add at least 63 completed Lean requests. CPU-seconds and peak memory were not instrumented.

V2 independently replayed 14 explicitly exposed authored training trajectories, prioritizing 11 prior raw-model failures and retaining earlier reuse examples. The 72 checked transitions trained three feedback candidates for 16 epochs, initialized from the same V1 checkpoint. Source, tasks, selection protocol and evaluation firewall were frozen first. Candidate selection occurred on validation and was written to disk before final evaluation. V2 took 196.38 elapsed seconds, CPU only, no added financial expenditure. Its three-seed outcomes demonstrate sensitivity rather than robust automatic improvement.

## Measured results

All search rows below use 64 candidate expansions per task and a beam of four. False controls are included in denominators and must stay unresolved. No final labels were used as gradients or to select the V2 model.

| Evaluation | Policy | Kernel-verified | Expansions | Final proof actions |
| --- | --- | --- | --- | --- |
| V1 cold-cache, 8 public tasks | Symbolic | 6/8 | 223 | 35 |
| V1 cold-cache | Selected raw graph-31 | 5/8 | 273 | 16 |
| V1 cold-cache | Bag-31 | 6/8 | 266 | 25 |
| V1 cold-cache | RL1-31 / RL2-31 | 6/8 each | 283 / 278 | 22 each |
| V1 cold-cache | Graph-47 → RL1/2-47 | 5/8 → 4/8 | 277 → 274 / 285 | 16 → 12 |
| V2 new authored compositions, 8 tasks | Parent, same feature extractor | 0/8 | 512 | 0 |
| V2 | Validation-selected refined-17 | 5/8 | 384 | 45 |
| V2 | Refined-31 / refined-47 | 0/8 each | 512 each | 0 |
| V2 | Symbolic | 6/8 | 301 | 53 |
| V2 | Selected portfolio | 6/8 | 413 | 53 |

The selected feedback checkpoint learned to solve five new compositions, including ten-action Nat/Int order chains and repeated function rewriting. Both false conclusions remained unresolved under every policy. The symbolic baseline remains stronger in solve rate and efficiency. Neither graph superiority nor robust RL superiority was demonstrated. The fallback preserves all six positive results in this suite, at an additional search cost; it does not guarantee dominance for every possible budget/problem.

The development retrieval audit separately improved symbolic capability from 6/12 to 10/12 by correcting premise matching and order action priorities. This is an engineering repair evaluated on an exposed authored suite, not a blind learning result. Of that suite, the Int identity-witness statement had already appeared in V1 validation, and the integer exchange statement had already run as a demonstration; the original prospective protocol overstated novelty. `EXPOSURE_AUDIT.json` records this correction without rewriting the original frozen protocol. V2 explicitly promotes those exposed examples into training and excludes exact alpha duplicates from its new evaluation. The new evaluation shares mathematical families with training; no external-project, secret-holdout or scientific-discovery claim is made.

V1 original evaluation reused cross-policy observation caches. Its solve counts and expansion counts remain useful, but timings and actual invocation counts are not a fair latency comparison. `cold-audit/` reruns frozen checkpoints with empty observation caches. Search-wall metrics exclude initial observation; whole-evaluation metrics include first-worker startup for the first policy. Construction and independent replay remain separate. Small, correlated authored suites and three seeds do not justify a broad statistical superiority claim.

## Reproduce and inspect

Activate the pinned Lean 4.28/Python CPU environment, then run:

```bash
python -m pcs.experimental.prover.reuse_experiment --output /tmp/reuse-v1 --epochs 12 --episodes 6 --seeds 17 31 47 --budget 64
python -m pcs.experimental.prover.reuse_evaluate --experiment research/checked-reuse-v1 --output /tmp/reuse-cold
python -m pcs.experimental.prover.reuse_prospective --experiment research/checked-reuse-v1 --output /tmp/reuse-development
python -m pcs.experimental.prover.reuse_refine --experiment research/checked-reuse-v1 --output /tmp/reuse-v2 --epochs 16
python -m pcs.experimental.prover.cli 'For all natural numbers a, b, c and d, if ((a is less than or equal to b) and ((b is less than or equal to c) and (c is less than or equal to d))) then (a is less than or equal to d).' --models research/checked-reuse-v2 --output /tmp/checked-chain.json
PCS_REQUIRE_PROVER=1 python -m pytest -q tests/test_lean_learning_loop.py tests/test_checked_reuse.py
```

Original V1 training uses its exact `training-source.tar.gz`, not later controller code. V1 cold/development/retrieval audits and V2 include exact source overlays and manifests. Subsequent atomic artifact writes, prepared-environment amortization, CLI and public routing are recorded in runtime source manifests. Restoring an overlay should use a disposable copy of the pinned baseline, preserving current production source. All raw trajectories, invalid attempts, kernel axiom inventories, per-seed checkpoints, data partitions and timings are retained. `EVIDENCE_SHA256.json` binds the complete evidence package.

Artifacts: [V1 protocol](../research/checked-reuse-v1/protocol.json), [V1 source](../research/checked-reuse-v1/training-source.tar.gz), [V1 training](../research/checked-reuse-v1/training.json), [cold audit](../research/checked-reuse-v1/cold-audit/summary.json), [retrieval repair](../research/checked-reuse-v1/retrieval-audit/summary.json), [V2 protocol](../research/checked-reuse-v2/protocol.json), [V2 checkpoints](../research/checked-reuse-v2/registry.json), [V2 full trajectories](../research/checked-reuse-v2/evaluations.json.gz), [V2 independent replay](../research/checked-reuse-v2/independent-final-replay.json).

## Trust boundaries and remaining obligations

A checked theorem certifies its exact formal statement and explicit premises. The controlled English grammar does not certify unrestricted English intention. Library licenses/source tags require cleared provenance and do not adjudicate rights. Alpha fingerprints are structural deduplication, not full mathematical equivalence. Compiled-byte hashes detect changes under the declared cryptographic/filesystem assumptions; they are not a formal refinement proof.

Aristotle's running assignment covers broader runtime correspondence, conservativity and learning/search interfaces. This implementation does not claim those obligations closed. The new IO worker is receiver-owned trusted execution code, not a mathematical proof. Models load only JSON weights and propose bounded receiver-generated actions. The existing local backend is not a sandbox for arbitrary submitted Lean/Python code. Kernel, production signing keys, scientific acceptance adapters and release gates remain independently controlled.

Remaining research dependencies include robust curriculum/seeds, calibrated uncertainty, graph architecture gains, Mathlib/external-project retrieval, induction/sets/algebra, general language generation and semantic fidelity, long-horizon RL advantages, verifier/runtime refinement and autonomous scientific discovery. No production authority is acquired through checkpoint registration. Public mathematical statements require explicit publication consent, never automatic training authorization; local work is not uploaded.
