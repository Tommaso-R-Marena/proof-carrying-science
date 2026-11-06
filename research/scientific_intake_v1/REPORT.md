# Scientific project intake: measured research result

This implementation makes mixed projects inspectable and their supported checks replayable. It demonstrates a useful deterministic workflow and cache optimization. It provides no evidence that JEPA or RL improves scientific intake.

## Source and evaluation contract

Base: exact PR #200 head `3f257ac1e2d197a420da5a79b90822e09c2374e5`, stacked on #199 `0b95715834addb6f8712a33aa6154e4eed254af2`. Live audit found both PRs open/draft/unmerged and protected main at `bc78660b5fac857fce3873eb6cda0445d1903da1`. They are preserved.

The retained freeze binds source context `fd261a927a24c5750169639993c292586bbcae0e0b837e7465611fe93bee166d`, exact Python/Lean identities, protocol and input-selection policy. No training or model selection used imported projects. Development cases are 1CRN/Norris/Nat; final cases are 1UBQ/Pontius/List. Project identities/splits were frozen before downloads; final inputs were materialized only after the component freeze. The cases share derivative claim templates, so project-level holdout is not theorem-template or broad scientific OOD validation.

NIST StRD endpoints returned HTTP 403. A recorded pre-evaluation amendment uses official, pinned `usnistgov/dataplot` originals for the same study names. Norris has 12 rows; Pontius has 40. They are not asserted to be StRD-certified datasets/results. Downloaded Nat source references `Nat.add_zero` but supplies the quoted `Nat.zero_add` declaration; a separately labeled arithmetic identity is independently reconstructed. The List case uses a separately labeled `List Nat` append identity, not execution of its polymorphic source.

## Results

Two frozen CPU sweeps with unchanged source/labels, Python 3.12.14, Lean 4.28.0. The table shows the first sweep. Each project used the same 1,000 fixed scheduling-work-unit budget in three conditions. Work units are not wall-time guarantees. Timing includes ingestion/checking and excludes the separate replay measurement; high-water memory is cumulative process measurement rather than isolated per-case allocation.

| Project | Split | Annotated agreement | Cold calls | Warm calls | Cold seconds | Warm seconds |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| Crambin 1CRN | Development | 10/10 | 47 | 0 | 4.007 | 1.265 |
| NIST Dataplot Norris | Development | 12/12 | 79 | 0 | 5.749 | 0.919 |
| Lean4 Nat | Development | 7/7 | 39 | 1 | 12.922 | 4.740 |
| Ubiquitin 1UBQ | Final | 10/10 | 47 | 0 | 4.021 | 1.169 |
| NIST Dataplot Pontius | Final | 12/12 | 81 | 0 | 5.292 | 0.914 |
| Lean4 List | Final | 7/7 | 37 | 1 | 9.860 | 4.174 |

- 88 artifacts preserved; 80 parsed, eight explicitly unsupported, zero parsing errors. The formats include real PDB/mmCIF/FASTA/Lean/Dataplot originals and labeled derived CSV, PDF, DOCX, XLSX, JSON, Python and notebook files. PDF summaries are first-party derivatives, not published-paper comprehension evidence.
- 403 proposed statements matched retained extraction spans. All 58 annotated statements were found and agreed with their expected bounded-check status. These are internal source-derived annotations, not independent expert labels. Span matching does not establish semantic interpretation accuracy.
- 330 cold checks: 306 supported successes, 22 exact refutations, two `UNKNOWN` false mathematical claims. Bounded proof failure alone did not label a false theorem refuted. Six independent package replays reran all 330 checks, with cache bypassed.
- Zero annotated unsupported promotions and zero scientific claims certified. Every scientific meaning remains open. All cases had identical verdicts under cold deterministic, warm deterministic and requested-learned/fallback routing. No graph was truncated in this run.
- Warm runs reused 328 results and repeated the two unknown mathematical checks. Aggregate time fell from **41.851 s to 13.182 s** in this sweep (3.18×). An isolated second sweep reproduced all annotated outcomes/verdicts and 330 actual independent checks, with totals **41.114 s cold / 12.935 s warm**. The first sweep overlapped some focused test execution; the replication had no overlapping tests. These two sweeps do not supply confidence intervals or a neural improvement.
- Peak parent RSS was 73,296 KiB; cumulative child high-water RSS was 768,260 KiB. CPU-only execution; no GPU measurement or accelerated-training claim.
- Controlled incremental experiment: initial four checks; unchanged and unrelated-edit runs needed zero checks; changing a bound CSV reran three checks, reused one unrelated check and found a newly false sum. The changed project independently replayed.

Independent NumPy SVD fits agreed with exact rational certificates: Norris maximum prediction difference `5.684341886080802e-14`, Pontius `1.7763568394002505e-15`. Exact normal equations and SSE were recomputed from bound observations; the checker does not establish design rank or coefficient uniqueness. No causal conclusion follows from a calibration fit.

## Formal evidence

Five actual Lean theorems compile with empty axiom lists:

1. `PCSScientificIntake.projection_congr`
2. `PCSScientificIntake.fixed_checker_reuse`
3. `PCSScientificIntake.policy_bound_reuse`
4. `PCSScientificIntake.closed_contains_reachable`
5. `PCSScientificIntake.closed_dependency_reuse`

These specify conditional equality/dependency reuse. They assume complete dependency inputs, a fixed pure checker/policy and genuine named-byte equality. They do not prove Python refinement, scientific applicability, hash injectivity or host immutability. They are useful integration specifications, not new foundational mathematical discoveries.

The project run also independently accepted `∀ n : Nat, 0 + n = n`, `∀ n : Nat, n + 0 = n`, and `∀ xs : List Nat, xs ++ [] = xs` through the existing typed PCS Lean interface. Imported proof bodies, attributes and code were not executed. These are existing standard mathematical identities, not newly discovered theorems.

## Prior models and negative findings

Two pinned retained models performed real CPU inference on four original-domain observations each, without tensor changes or new training. Original checkpoint hashes, observation/action records and timing are retained. Two original Proof-JEPA receipts were freshly kernel-replayed, and two Safety-JEPA guarded/unguarded histories were re-executed with matching concrete outcomes. An additional **69 foundation tests passed**. The full historical three-seed training experiments were not retrained or rerun here; their frozen evidence remains unchanged.

The earlier Proof-JEPA benchmark did not beat deterministic 5/10 held-out proof completion. Safety-JEPA's selected combined model matched 48/48 task completion but used 262 steps/two denials versus deterministic 260/zero. RL/transfer/proof-guided results were unstable, and the small Qwen pilot completed 0/6 tasks. This package does not revise those findings.

Native proof/action logits cannot honestly rank biochemical evidence obligations, and tool-state embeddings do not supply scientific semantics. Scientific learned routing therefore records incompatibility and falls back. Model diagnostics are compatibility/regression evidence, not proof of an intelligent cross-domain contribution. No accelerating recursive self-improvement, general alignment or deception-detection claim is established.

## Adversarial findings and repairs

Independent internal review reproduced rehashed packages with omitted checks and invented summaries, substituted original ZIP bytes, orphan source objects, malformed cross-format checker crashes and loose OLS certificate schemas. These now fail closed or return `UNKNOWN`, with regression tests. The same review reran its attacks after repair and found no remaining blocker within its stated research/host-integrity scope. This is not external validation.

Additional coverage includes traversal, NUL/Unicode/case ambiguity, symlinks/hardlinks/FIFO entries, archive bombs, empty-directory bounds, malicious caller working directories, code/notebook/pickle nonexecution, source and receipt tampering, invalid exact numbers, mixed-unit assumptions, fake authority metadata, changed dependencies, cache forgery, HTML injection, and real canonical source replay. The final local research suite passed **152 tests**, with zero skipped/failed tests; repository-integrity and Python compile checks passed.

One initial development freeze was invalidated by concurrent completion of its fixture builder. The first full frozen run then stopped during the first development-case replay because HTML locator dictionary order differed from canonical JSON. This was fixed with deterministic display ordering; cases/labels were unchanged and no training followed the exposure. The failed freeze/log is retained in `engineering-events.json`, rather than being represented as successful final evidence.

## Evidence and reproduction

`evidence/benchmark.json.gz` and `benchmark-replication.json.gz` hold exact measurements, per-annotation outcomes, resource data and replay records. `replayable-cases.zip` retains six complete portable cold evidence packages (about 1.1 MB compressed). `package-index.json` binds their manifests and retained artifact hashes. Host cache keys are excluded.

Extract only the reviewed, digest-pinned evidence archive into a fresh directory, then run `python -m research.scientific_intake_v1 replay PATH --expected-manifest-sha256 HASH` for each case using its index hash. Source/toolchain drift causes a replay failure; such a failure requires an explicit successor evaluation, not editing old receipts. Reproduction from licensed upstream fixtures and commands is documented in the README. No paid service, external model download, production deployment or production authority modification was used.

A dedicated experimental GitHub workflow runs the actual suite, formal audit, bounded retained-effect replay and development benchmark. Hosted [run 42188673417](https://github.com/Tommaso-R-Marena/proof-carrying-science/actions/runs/42188673417) executed successfully on implementation commit `fb9aa8c34f7fc7c3ec38ba4e949f567777be3ca4`, including actual tests/Lean checks and the development benchmark. `evidence/hosted-ci-code.json` retains execution-step evidence. Subsequent documentation/evidence commits preserve that runtime-source context and receive their own workflow run. Frozen main source-admission gates remain intact and need a reviewed successor before production integration.

## Scientific assessment

| Question | Evidence-based answer |
| --- | --- |
| Does JEPA improve theorem proving? | Not established; the frozen primary experiment did not surpass symbolic search. |
| Does RL beat supervised/deterministic methods? | Not established; prior sequential results were unstable and did not beat the best deterministic policy. |
| Does proof-guided learning improve representations? | Some prior training diagnostics changed, but useful held-out generalization is not established. No new scientific representation is trained here. |
| Does Safety-JEPA improve prevention? | Prior reactive-stream efficiency improved; independent guards supplied enforcement, and the strong deterministic planner remained better. No new universal safety claim. |
| Can PCS process real projects with provenance? | Yes, within the implemented bounded formats/claim grammar: six projects, 330 replayed checks. General scientific understanding is unsupported. |
| Does combining components outperform them individually? | No learned-combination benefit measured. Provenance, exact checks, existing Lean interfaces and cache reuse form a useful deterministic workflow. |
| What is formally proved? | Five conditional dependency theorems and the reconstructed closed mathematical instances above. |
| What is empirically demonstrated? | Real parsing, finite source-bound checks/refutations, cache-independent replay using the same checker implementation, numerical-oracle agreement, native-model regression diagnostics and reduced repeated-check cost. |
| What remains negative/inconclusive? | Neural superiority, RL stability, cross-domain semantic routing, broad paper comprehension, complete dependency discovery, Python refinement and independent external scientific validation. |
| Highest-value next experiment? | Freeze expert-annotated real scientific review tasks with genuinely consequential sequential evidence choices, then compare deterministic retrieval/checking with one compatible learned ranker under matched budgets and a fresh untouched set. |

Current readiness: usable by technical researchers as an inspectable local prototype. The HTML helps reviewers, but no novice user study or production website integration has occurred. Production adoption needs source admission, security confinement/refinement work, independent domain annotations and external replication. More architectural complexity is not presently justified by these measurements.
