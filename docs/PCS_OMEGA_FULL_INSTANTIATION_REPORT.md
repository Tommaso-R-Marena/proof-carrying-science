# PCS Omega: instantiated Lean learning loops v1 and v2

Date: 2026-10-10. Status: experimental working vertical implementation; the broader scientific-intelligence directive remains incomplete.

## What actually executes

Controlled mathematical English → typed Math IR → generated Lean 4.28 proposition → structured elaborator goals/context/term trees → trained policy and bounded multi-step action search → independent fresh Lean kernel check → structured statement explanation → independently rechecked trajectory intake → updated checkpoint.

The separate package `pcs.experimental.prover` preserves every previous Omega checkpoint, the Claim IR/Proof Obligation Graph and registered authority interfaces. It adds real PyTorch weights and gradient updates, trainable message passing, policy/value/uncertainty heads, a local proof arena and independent Rust-checked CertiForge proposal ranking. Model proposals have no scientific certification authority.

## Reproduce

```bash
source scripts/activate_lean_428.sh
python -m pip install --require-hashes -r requirements-prover.lock
PCS_REQUIRE_PROVER=1 python -m pytest -q tests/test_lean_learning_loop.py
python -m pcs.experimental.prover.cli "For all propositions U and V, if (U and V) then (U and (U and V))." --models research/lean-learning-v2 --output NEW_LOOP.json
python -m pcs.experimental.prover.experiment --output NEW_EXPERIMENT --epochs 35 --episodes 12 --seeds 17 31 47
python scripts/evaluate_lean_formalization.py --models research/lean-learning-v2 --output NEW_FIDELITY.json
python -m pcs.experimental.prover.server --models research/lean-learning-v2 --public ../proof-carrying-science-site/public
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

All 1,324 Python tests passed locally, including 27 new Lean-learning tests. The 27 targeted tests passed again after reserved-name rejection; protected CI supplies the final release check. Browser play used the actual local Lean backend at widths 320, 390, 768 and 1440; each completed a six-action no-axiom proof, required selection for ambiguity and had no horizontal overflow. Protected CI additionally reproduces training, pinned inference, fresh proof checking and a false-certificate negative control. CI and final merge identities are recorded in the release evidence/PR checks rather than asserted before they finish.

## Formalization and authority boundaries

Supported types are Prop, Nat, Int and Nat→Nat terms; logical connectives, quantification, numeric equality/≤ and bounded arithmetic. English accepts explicit typed frames and compositional formulas. The deterministic parser grounds variable/type/scope choices. A separately trained 4,452-parameter English encoder ranks domains using 75 licensed authored pairs. It is a compact grammar classifier/reranker, not a general structured-output formalization model. The grammar can produce unseen compositions; it abstains on unsupported symbols and exposes ambiguous conjunction/disjunction grouping.

Independent typed meaning fixtures and supported syntax round trips provide evidence for this fragment. They do not establish full English meaning preservation, external theorem fidelity or human-reviewed explanation accuracy. No pretrained/external-model comparison was run. General Lean declarations, richer Mathlib objects, coercions, universes, arbitrary definitions, general sets, algebra and induction remain unresolved. V2 adds explicit Nat→Nat injectivity/composition and Nat→Prop predicate implications; these are precisely scoped typed meanings, not generic Mathlib Set or Function authority.

The proof-state API serializes actual elaborator Expr trees, locals, target types, subgoals and errors. It uses the pinned Lean core environment, not Mathlib-aware retrieval; [premise-catalog.json](../research/lean-learning-v1/premise-catalog.json) contains nine actual Lean arithmetic signatures. The final theorem is independently compiled and its axiom inventory checked. No arbitrary model Lean/source/shell/import action is executed. The local worker uses receiver-owned source, no credentials, timeout, heartbeat/depth bounds and Linux virtual-memory/CPU limits. It is not a general-purpose secure sandbox for arbitrary submitted Lean or Python code.

The original PCS Claim IR and Proof Obligation Graph retain blocking English-intent and registered-authority obligations. Mathematical kernel verification never grants PCS scientific acceptance. `formal/PCSProofBoundary.lean` proves four abstract evidence/reward/premise-boundary properties (standard propext in two); this does not prove Python/Lean refinement, sandbox isolation or receipt persistence. Existing Aristotle semantic source is preserved; the completed consolidated package is integrated separately below.

## CertiForge scope

The learned optimizer trains on actual pinned Rust package-checker outcomes including negative rewrites. Both held-out programs reach `or(x,y)` within three ranked checks and reduce AST nodes (7→3 and 5→3). The existing ForgeOpt baseline also finds reductions for all three seeds. Its weighted ForgeOpt cost differs from the package AST-node objective; no equal-time or superior-optimization claim is made. All 65,536 u8 pairs are replayed again before accepting the learned proposal. No Rust↔Lean refinement, AST-bound kernel certificate, optimization RL or empirical runtime gain is established.

## Public interface and remaining research obligations

The website provides an accessible lab with real interactive goal states, controlled action buttons, model/symbolic search, structured explanation and downloadable exact artifacts when run against the local backend. Public hosting adds queued real proof searches through the protected `pcs-lean-public.yml` workflow. Interactive per-action play remains local. Public requests require explicit CC0 publication consent, signed source/revision-bound polling tickets and strict daily quotas; job results are extracted from logs, with no artifact-storage charge. The deployed service is pinned to an independently checked protected core revision. Deployment and live execution are separate release obligations until their recorded checks pass. Production CSP, Cloudflare/D1 bindings, consent and existing games are preserved. No paid inference backend or new participant collection is introduced.

The longer directive remains open for Mathlib and external project retrieval, larger architecture comparisons, induction/sets/algebra, broad bidirectional learned language generation, PPO/MCTS/long-horizon scientific discovery, calibrated uncertainty, active-learning/curriculum experiments, learned dependency planning, automatically reusable verified lemmas, scientific empirical examples, general always-on remote Lean hosting, exact optimizer-state training resume, private final evaluation, human fidelity/playtesting and general refinement proofs. These are unsolved obligations, not instantiated features.

Base revisions: core d062721d443140fb99e15ef804a1ed5533320b53; website 4968a20f4abd12a7952ff21c811c9edfbb7b8be6; CertiForge 758c2c7d1ef0b0c68dda09938420aa6755c581cb. The exact training overlay is retained in `training-source.tar.gz` and bound by `source-manifest.json`; `runtime-source-manifest.json` records the current source independently of the training snapshot. V1 retains its original exact training code; V2 adds quantifier retrieval, precise injectivity/predicate lowering and lexical alpha-fingerprint correction. Subsequent reserved-name rejection, CLI resource-result handling and the public job wrapper do not pretend to be part of the training snapshot. Existing third-party/legal/pilot issues and site D1 ledger reconciliation remain external obligations.

## Expanded mathematical learning experiment v2

[Protocol](../research/lean-learning-v2/protocol.json), [source archive manifest](../research/lean-learning-v2/source-manifest.json), [full digests](../research/lean-learning-v2/SHA256.json), [measured summary](../research/lean-learning-v2/summary.json), [complete evaluation traces](../research/lean-learning-v2/evaluations.json.gz).

Twelve actual verified training families now include a nine-action proof that composing injective Nat→Nat functions preserves injectivity. The six final tasks include a separately held-out Nat→Prop predicate-transitivity theorem requiring nine actual Lean steps. Quantified local premises and conjunction projections are structurally retrieved from the real Lean expression tree. This is mathematical quantification over unbounded Nat, rather than enumerated Boolean valuations; it does not establish general first-order model finding or Mathlib-wide competence.

| Policy | Seed 17 verified / 6 | Seed 31 | Seed 47 |
|---|---:|---:|---:|
| Untrained | 1 | 3 | 1 |
| Bag supervised | 5 | 5 | 5 |
| Graph supervised | 4 | 5 | 5 |
| RL generation 1 | 4 | 5 | 5 |
| RL generation 2 | 4 | 5 | 5 |
| Symbolic | 5 | same deterministic run | same deterministic run |
| Random | 4 | one fixed ranking seed | one fixed ranking seed |

Graph-17 remains selected by the predeclared validation criterion, not by final results. It proves the predicate transfer, nested conjunctions, four-premise logic and arithmetic, but misses implication composition within the budget. The symbolic and bag baselines remain stronger on this small set. No graph or RL superiority is claimed. All 72 sequential RL episodes and both updated generations are retained; there is no additional solve-rate improvement.

This expanded collection/training/evaluation used 391.310 wall seconds, 614 actual Lean requests and 310.259 measured Lean seconds, two CPU threads, zero GPUs and zero financial spend. Fifteen 10,419-parameter checkpoints retain initial, bag, graph and both RL generations for three seeds. The existing 4,452-parameter English classifier is reused; newly supported function/predicate frames are deterministic grammar extensions, not newly trained general language generation.

Ten independent authored typed meaning labels elaborate and round-trip correctly, including explicit composition order and predicate scope; six ambiguity/abstention controls are retained. Four actual checked held-out declarations reconstruct into structured English explanations. Human fidelity review and a formal theorem about general English meaning remain open.

`python scripts/run_lean_feedback_cycle.py --models research/lean-learning-v2 --output NEW_FEEDBACK` freezes two additional evaluation statements, proves a new six-action English theorem, independently rechecks licensed feedback, changes next-generation weights through four epochs, and verifies 2/2 additional tasks before and after. [Feedback checkpoint](../research/lean-learning-v2/feedback-generation.json) digest: `d775bd1c4fa3345f73c7b57dc69ebf5f03b954245a77cc9ff98b4063f08f52d6`. [Complete cycle](../research/lean-learning-v2/feedback-cycle.json.gz) records no measured improvement. This separate demonstration is explicit authored training authorization; website publication consent does not automatically authorize training.

The public adapter treats pinned GitHub execution as a hosting trust dependency. Signed tickets bind source text, interpretation, core SHA and expiry; run provenance, duplicate results, permitted axiom inventory and result shape are checked. Final Lean proofs remain checked in a fresh process. Protocol tests mock provider HTTP to test rejection paths; actual deployed jobs and kernel results must be recorded separately. No new production D1 schema, signing key, paid service or scientific acceptance adapter is introduced.

## Outstanding Aristotle and refinement obligations

Aristotle run `b9577162-8244-44ff-83ca-dc7efe9d95a4` completed the consolidated assignment as typed Lean reference models. The [integration report and reproducible evidence](../research/aristotle-omega-dd-v1/REPORT.md) bind the exact archive and sources. The 214 named general theorem modules independently kernel-check: BDD validity/canonicity/apply/compile, assumption-aware checking, Bellman optimality/counts/mandatory/possible masks, reconstruction, replay and bounded accounting are now established for these reference models. The required release gate additionally compiles all positive controls, audits all 226 named positive theorems and rejects three false claims. Finite Lean/Python/JavaScript comparisons match on 91 tasks; they are not a refinement theorem. Python/JavaScript refinement, persistent receipt authority correspondence, general elaboration/English intent grounding, Rust/Lean CertIR correspondence and learning-environment refinement remain explicit obligations. The original consolidated prompt and all existing authority imports are preserved. Neither the reference proofs nor runtime parity establish a learned-performance improvement or scientific acceptance.

Registry entries explicitly bind checkpoint, training source archive, dataset manifest, frozen configuration and actual validation/final metrics. The final checked feedback cycle records its actual Git source revision separately from its model parent digest; the parent digest is not mislabeled as a source revision.
