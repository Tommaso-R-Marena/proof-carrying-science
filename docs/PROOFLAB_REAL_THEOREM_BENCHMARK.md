# PCS ProofLab: authentic theorem benchmark and honest validation

**61 source-backed Lean theorem declarations**, pinned to core commit `cff0b67595abd4862ab0c156b157f262b169eca5` and each module's exact Git blob. Each record stores theorem name, full header (without proof body), line, provenance and lightweight syntactic identifier mentions. The latter are **not extracted kernel-verified proof dependencies**. A statement existing in Lean source does not itself establish that the exact pinned revision compiled. No new Lean build or authority promotion is claimed by this benchmark.

**Public training material:** 32 declarations from Units (13), Binding (8), EnvFacts (6), Checkers (5). **Public practice challenges:** 14 from IndexProofs (6) and PackageProofs (8). **Held-out module evaluation:** 15 from PKPDCheck (8) and Workflow (7); these two entire modules must never be included in public gameplay or training donation. This is a module-level holdout within PCS, **not** a genuine external-project benchmark.

Run `python3 scripts/validate_prooflab_benchmark.py` or `pytest -q tests/test_prooflab_benchmark.py`. Validation recomputes exact source Git SHA-1 blob identities and checks the declaration headers and row splits; it does not invoke Lean. Public site has a reviewed copy of only the 46 allowed headers. The core project remains private. Do not publish full proof bodies or infer license/third-party data-use permissions.

In ProofLab the human performs a visual **educational planning task** on each genuine theorem statement: plan scaffold prerequisites, repair an intentionally omitted edge, classify what can legitimately be concluded, and observe why a simulated completed plan is not a Lean term. Those pedagogical labels are not proof-search ground truth. To upgrade, require actual candidate Lean 4 proof terms and fresh kernel verification in the separate core engine, plus independent external research tasks and systematic evaluation against a baseline.

Formal safety P0 (unregistered evidence checkers) remains open and outside this benchmark; no game score can bypass it.
