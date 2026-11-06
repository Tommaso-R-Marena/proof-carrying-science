# Implementation map

The CLI (`__main__.py`) supplies a project path and a fresh output directory.

1. `intake.py` inventories files using descriptor-relative traversal, checks limits, snapshots exact bytes and binds ZIP membership. `worker.py` receives captured bytes through stdin in a fixed parser process.
2. `adapters.py` and `bio_adapters.py` declare and implement format-specific bounded observations. They preserve opaque/unsupported inputs and never run submitted code.
3. `knowledge.py` makes deterministic source-bound proposals and explicit assumptions, then lowers closed claims into research checks. Existing `pcs.proof_translation_v06` helpers build compatible Claim IR/obligation views with blocking scientific-meaning obligations. Unsupported meanings stay sidecars.
4. `routing.py` schedules supported checks under a fixed work budget. Retained JEPA/RL models have their own native-domain diagnostic path; incompatible scientific inputs get an explicit fallback.
5. `checks.py` rehashes all dependencies, reproduces the proposal from its original source, and performs fixed independent checks. Mathematical claims reuse PCS's typed induction language and real Lean environment. Imported source, proof tactics and model-chosen executables are never run.
6. `cache.py` binds local authenticated receipts to exact obligations, dependencies, policy, checker-source context and Python/Lean identity. It caches only supported successes/refutations. Unknowns are checked again. It does not store the key in the evidence package.
7. `pipeline.py` exports portable originals, graph, route, results, assumptions and an escaped local HTML review. Replay re-extracts source, reconstructs graph/route/display, verifies summaries/archive provenance and invokes real checks without cache. External manifest pinning is optional and explicit.
8. `formal/Incremental.lean` specifies conditional pure-checker reuse and dependency closure. `verify_formal.py` compiles and audits actual axioms through Lean 4.28.
9. `projects.py` materializes provenance-preserving licensed projects and separate annotation records. `benchmark.py` freezes component hashes before opening evaluation inputs, compares matched routes/caching and retains resource measurements and independent replay.

All additions live in this research namespace plus a dedicated experimental workflow. No production schema, authority registry, source-critical Lean module or source census changes.
