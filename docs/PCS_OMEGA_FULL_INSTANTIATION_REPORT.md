# PCS Omega: instantiated Lean learning loop v1

Date: 2026-10-10. Status: experimental working vertical implementation; the broader scientific-intelligence directive remains incomplete.

## What actually executes

Controlled mathematical English → typed Math IR → generated Lean 4.28 proposition → structured elaborator goals/context/term trees → trained policy and bounded multi-step action search → independent fresh Lean kernel check → structured statement explanation → independently rechecked trajectory intake → updated checkpoint.

The separate package `pcs.experimental.prover` preserves every previous Omega checkpoint, the Claim IR/Proof Obligation Graph and registered authority interfaces. It adds real PyTorch weights and gradient updates, trainable message passing, policy/value/uncertainty heads, a local proof arena and independent Rust-checked CertiForge proposal ranking. Model proposals have no scientific certification authority.

## Reproduce

```bash
source scripts/activate_lean_428.sh
python -m pip install --require-hashes -r requirements-prover.lock
PCS_REQUIRE_PROVER=1 python -m pytest -q tests/test_lean_learning_loop.py
python -m pcs.experimental.prover.cli "For all propositions U and V, if (U and V) then (U and (U and V))." --models research/lean-learning-v1 --output NEW_LOOP.json
python -m pcs.experimental.prover.experiment --output NEW_EXPERIMENT --epochs 35 --episodes 12 --seeds 17 31 47
python scripts/evaluate_lean_formalization.py --models research/lean-learning-v1 --output NEW_FIDELITY.json
python -m pcs.experimental.prover.server --models research/lean-learning-v1 --public ../proof-carrying-science-site/public
```

Use a new output directory. The small CPU environment needs Python 3.12 on Linux x86_64 for the published wheel lock. Model tensors can run on authorized CUDA installations, but a GPU training profile was not executed. No paid resource was used.

## Frozen experiment and measured results

Protocol: [protocol.json](../research/lean-learning-v1/protocol.json). Source overlay: [source-manifest.json](../research/lean-learning-v1/source-manifest.json). Data: [data-manifest.json](../research/lean-learning-v1/data-manifest.json). All artifact bytes: [SHA256.json](../research/lean-learning-v1/SHA256.json).

Ten authored training theorems, three validation tasks and five held-out public tasks. Families partitioned before fitting; no evaluation solutions enter training or retrieval. The final set includes one underdetermined implication; unknown is the correct outcome. These are small public authored tasks, not a private blind benchmark or external-project evaluation. Earlier development runs exposed these public tasks; no claim of private untouched evaluation is made.

| Policy | Seed 17 verified / 5 | Seed 31 | Seed 47 |
|---|---:|---:|---:|
| Untrained | 1 | 3 | 1 |
| Bag of terms, supervised | 3 | 3 | 3 |
| Trainable graph, supervised | 3 | 3 | 3 |
| Graph after RL generation 1 | 3 | 3 | 3 |
| Graph after RL generation 2 | 3 | 3 | 3 |
| Symbolic baseline | 4 | same deterministic run | same deterministic run |
| Random ranking | 3 | one fixed ranking seed | one fixed ranking seed |

Each search has 96 candidate expansions, depth 18, beam 4, typed action masks and the same immutable theorem. Full traces retain invalid actions, accepted states, kernel results, expansion counts and actual Lean request counts. Warm replay caching is shared: wall times are not a fair cold-start speed comparison. Ranking/inference is included in wall time, and cache hits still consume candidate expansions.

Graph and bag models each contain 10,419 allocated trainable parameters. The bag baseline does not execute the message/update layers; its effective trained parameter count is smaller. The graph embedding, message matrix and update matrix change under supervised gradient updates; all change inventories are retained. The value head learns inverse remaining proof length; the uncertainty head has only success-trajectory supervision and is not a calibrated abstention estimator. Neither head establishes checker authority or a measured search advantage.

The trained graph solves 3/5 for each seed; the symbolic baseline solves 4/5. There is no demonstrated structural-model superiority. One untrained seed already solves 3/5. RL updates genuine sequential policy weights but does not increase held-out solve rate. The earlier stronger symbolic solver remains available, and all initial/BC/RL checkpoints are retained. Five correlated tasks do not support a breakthrough claim or statistical superiority. No pooled confidence interval across correlated seeds is warranted.

Actual training/evaluation run: 199.26 wall seconds, 457 noncached Lean requests, 173.88 seconds in Lean, two PyTorch CPU threads, no GPU. Real financial spend: zero.

## Actual sequential RL and feedback

On-policy actor–critic samples from the current Lean state, runs typed actions, receives environment-derived rewards and discounts multi-step returns by 0.97. A +1 reward requires a new kernel-checked final proof; invalid actions receive −0.2, accepted steps −0.01 with bounded subgoal-closure shaping. The policy never supplies reward or completion status. Failed and exhausted episodes remain recorded.

| Checkpoint | Verified training episodes / 12 | Maximum actual steps |
|---|---:|---:|
| rl1-17 | 8 | 7 |
| rl1-31 | 9 | 7 |
| rl1-47 | 10 | 7 |
| rl2-17 | 9 | 7 |
| rl2-31 | 10 | 7 |
| rl2-47 | 9 | 7 |

[End-to-end execution](../research/lean-learning-v1/end-to-end.json) uses a new conjunction structure absent from fitting and benchmark tasks. The trained graph takes six genuine proof actions; a fresh Lean process checks the original generated theorem without axioms. It emits eligible feedback without inferring human consent or license. Explicit Apache-2.0 local intake rechecks the proof and rejects alpha-renamed evaluation duplicates. Four more supervised epochs produce [feedback-generation.json](../research/lean-learning-v1/feedback-generation.json). Two separately frozen additional tasks are both verified before and after. This is an executed iterative loop, with no measured improvement claim.

Large trajectory files use deterministic gzip. Read with `json.loads(gzip.decompress(path.read_bytes()))`. They include real failed attempts and complete proof states, not fabricated human gameplay.

## Acceptance evidence

| Test | Executed outcome | Artifact |
|---|---|---|
| A: English formalization | 8 independently authored meaning labels matched typed IR and elaborated; 2 ambiguity + 4 unsupported/type controls rejected or exposed | formalization-evaluation.json |
| B: Lean explanation | 3 actual held-out kernel-checked declarations reconstructed and explained | formalization-evaluation.json |
| C: multi-step Lean | Learned held-out conjunction/arithmetic proofs, symbolic implication chain, unseen six-action end-to-end theorem | evaluations.json.gz, end-to-end.json |
| D: learned graph | Both trainable message/update matrices changed; graph ablation shows no advantage | supervised-training.json, evaluations.json.gz |
| E: sequential RL | 72 actual episodes across 3 seeds × 2 generations; all weight digests changed | rl-training.json.gz |
| F: repeated improvement | BC, RL1, RL2 and checked-feedback checkpoint executed; sustained improvement not demonstrated | summary.json, feedback-cycle.json.gz |
| G: optimization | 385-parameter ranker trained on 28 checked pairs; both held-out reductions rechecked exhaustively | certiforge-report.json.gz |
| H: research planning | 3 prescribed dependent arithmetic obligations verified in dependency order; failed prerequisites block descendants | formalization-evaluation.json; unit tests |
| I: adversarial integrity | Goal tampering, admissions, injected tactics, forged receipt binding, holdout alpha duplicates, fabricated score/reward fields, false goals and corrupt checkpoints rejected | tests/test_lean_learning_loop.py |
| J: end-to-end | Actual learned proof, fresh kernel receipt, English explanation, checked feedback and changed next checkpoint | end-to-end.json, feedback-cycle.json.gz |

All 1,322 Python tests passed locally, including 25 new Lean-learning tests. Browser play used the actual local Lean backend at widths 320, 390, 768 and 1440; each completed a six-action no-axiom proof, required selection for ambiguity and had no horizontal overflow. Protected CI additionally reproduces training, pinned inference, fresh proof checking and a false-certificate negative control. CI and final merge identities are recorded in the release evidence/PR checks rather than asserted before they finish.

## Formalization and authority boundaries

Supported types are Prop, Nat, Int and Nat→Nat terms; logical connectives, quantification, numeric equality/≤ and bounded arithmetic. English accepts explicit typed frames and compositional formulas. The deterministic parser grounds variable/type/scope choices. A separately trained 4,452-parameter English encoder ranks domains using 75 licensed authored pairs. It is a compact grammar classifier/reranker, not a general structured-output formalization model. The grammar can produce unseen compositions; it abstains on unsupported symbols and exposes ambiguous conjunction/disjunction grouping.

Independent typed meaning fixtures and supported syntax round trips provide evidence for this fragment. They do not establish full English meaning preservation, external theorem fidelity or human-reviewed explanation accuracy. No pretrained/external-model comparison was run. General Lean declarations, richer Mathlib objects, coercions, universes, arbitrary definitions, sets, injectivity, algebra and induction remain unresolved.

The proof-state API serializes actual elaborator Expr trees, locals, target types, subgoals and errors. It uses the pinned Lean core environment, not Mathlib-aware retrieval; [premise-catalog.json](../research/lean-learning-v1/premise-catalog.json) contains nine actual Lean arithmetic signatures. The final theorem is independently compiled and its axiom inventory checked. No arbitrary model Lean/source/shell/import action is executed. The local worker uses receiver-owned source, no credentials, timeout, heartbeat/depth bounds and Linux virtual-memory/CPU limits. It is not a general-purpose secure sandbox for arbitrary submitted Lean or Python code.

The original PCS Claim IR and Proof Obligation Graph retain blocking English-intent and registered-authority obligations. Mathematical kernel verification never grants PCS scientific acceptance. `formal/PCSProofBoundary.lean` proves four abstract evidence/reward/premise-boundary properties (standard propext in two); this does not prove Python/Lean refinement, sandbox isolation or receipt persistence. Existing Aristotle semantic source and the user-running consolidated job are preserved.

## CertiForge scope

The learned optimizer trains on actual pinned Rust package-checker outcomes including negative rewrites. Both held-out programs reach `or(x,y)` within three ranked checks and reduce AST nodes (7→3 and 5→3). The existing ForgeOpt baseline also finds reductions for all three seeds. Its weighted ForgeOpt cost differs from the package AST-node objective; no equal-time or superior-optimization claim is made. All 65,536 u8 pairs are replayed again before accepting the learned proposal. No Rust↔Lean refinement, AST-bound kernel certificate, optimization RL or empirical runtime gain is established.

## Public interface and remaining research obligations

The website provides an accessible lab with real interactive goal states, controlled action buttons, model/symbolic search, structured explanation and downloadable exact artifacts when run against the local backend. Public hosting exposes instructions and evidence and explicitly reports unavailable remote Lean execution. Production CSP, Cloudflare/D1 bindings, consent and existing games are preserved. No paid inference backend or new participant collection is introduced.

The longer directive remains open for Mathlib and external project retrieval, larger architecture comparisons, induction/sets/algebra, broad bidirectional learned language generation, PPO/MCTS/long-horizon scientific discovery, calibrated uncertainty, active-learning/curriculum experiments, learned dependency planning, automatically reusable verified lemmas, scientific empirical examples, public remote Lean hosting, exact optimizer-state training resume, private final evaluation, human fidelity/playtesting and general refinement proofs. These are unsolved obligations, not instantiated features.

Base revisions: core d062721d443140fb99e15ef804a1ed5533320b53; website 4968a20f4abd12a7952ff21c811c9edfbb7b8be6; CertiForge 758c2c7d1ef0b0c68dda09938420aa6755c581cb. The exact training overlay is retained in `training-source.tar.gz` and bound by `source-manifest.json`; `runtime-source-manifest.json` records the final local-server static-metrics extension. Training/reasoning modules are unchanged between those snapshots. Existing third-party/legal/pilot issues and site D1 ledger reconciliation remain external obligations.
