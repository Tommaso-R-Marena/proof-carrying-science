# Novelty audit

## Method and an important limitation

**No internet access was available while this project was carried out.** The
literature comparison below is written from memory. Nothing in it was checked
against the current literature, and in particular **none of the 2025–2026
references the request lists (Akbari–Etesami–Kiyavash 2025; Maringgele–Etesami
2026; Choe et al. UAI 2026; Tan–Syrgkanis 2026) could be read.** What we say about
them is based on their titles and on what the request says about them. Treat
every 2025–2026 statement as **unverified**.

We tried to disprove each novelty claim by asking whether the result follows in a
few lines from a classical one. Almost all of them do. The default verdict below
is therefore "known or elementary".

## Comparison table

| Item | Category | Closest prior work (from memory) | Verdict |
|---|---|---|---|
| Version space, sharp min/max bounds over a finite model set | Established mathematics | Version spaces (Mitchell, 1982); partial identification (Manski); sharp bounds by LP (Balke–Pearl, 1997) | Known. Our finite-set version is trivial. |
| Bellman recurrence for minimax adaptive testing | Established mathematics / algorithm | Decision-tree complexity; minimax DP for adaptive group testing and active diagnosis; AND/OR search; the "optimal decision tree" problem (NP-hard, Hyafil–Rivest 1976) | Known. Our contribution is a machine-checked proof of global optimality over the full adaptive policy class, including non-informative and repeated experiments, with `WithTop` for unattainability. |
| Observational-equivalence impossibility; identifiability iff the query is constant on equivalence classes (up to ε) | Established mathematics | Observational equivalence in econometrics (Koopmans, Rothenberg); identifiability in causal inference (Pearl); "the query factors through the observation map" | Known in substance. The ε-tolerance version and the completeness of two-model certificates are immediate consequences. Formalized here. |
| Adversary (lower-bound) certificates, complete via the truncated value | Established mathematics | The adversary method for decision trees; strong duality for finite zero-sum games / AND-OR trees | Known in spirit. The exact local checkable form (`IsAdversary`) and the completeness proof `le_value_iff_adversary` are formalized here; we found no claim that this specific formulation is new. |
| Optimality sandwich (core ⊆ K ⊆ K_hi) | Elementary mathematics | Monotonicity; abstraction-refinement bounds in game solving and in MDP abstraction (upper/lower bounds) | Elementary; the request itself anticipates this. |
| Exact abstraction (observation- and query-preserving quotient) preserves the value | Established | Bisimulation / lumpability; "query-aware" quotients in planning | Known. |
| Nuisance-factor elimination (`value_prod_eq_section`) with the mixing counterexample | Elementary mathematics | "Irrelevant variables" and factored-model decomposition in planning and diagnosis; product/independence decompositions | Folklore in spirit. The exact form for minimax adaptive experiment design, and its use to explain certificate-size independence, are formalized here; we found no specific prior statement, but could not search. |
| Signature-only quotient is unsound (counterexample) | Established (folklore) | Folklore | Folklore; included as a guard. |
| Core-guided refinement loop (CEGAR-style) for exact minimax experiment design | Algorithm | CEGAR (Clarke et al., 2000); counterexample-guided inductive synthesis (CEGIS); lazy constraint generation; scenario/row generation in robust optimization | An instance of known methodology. We did not find (but could not search for) the exact combination "solve DP on a core, validate the policy on the full space, refine with failing models, emit a sandwich certificate". **Novelty unverified; assume modest.** |
| Anytime-valid mixture likelihood-ratio rejection under adaptive experiment selection | Established mathematics | Ville's inequality; universal inference (Wasserman–Ramdas–Balakrishnan, 2020); e-values and e-processes (Grünwald, Shafer, Vovk, Ramdas); sequential probability ratio tests (Wald) | Known. Formalized here in finite exact form for arbitrary adaptive trees over heterogeneous experiments. |
| Post-hoc maximized alternative is invalid (counterexample) | Established | Standard warning in the e-value literature | Known; formalized as a concrete instance. |
| OR evasiveness, value `n` with an (n+1)-model core | Established mathematics | Evasiveness of monotone Boolean functions; decision-tree complexity of OR | Known; our closed-form adversary proof for all `n` is a formalization. |
| Pointer family adaptivity gap 2 vs n+1 | Established | Adaptivity gaps; pointer-chasing / "address function" constructions | Known construction. |
| Greedy trap | Established | Greedy is suboptimal for optimal decision trees (known approximation gaps) | Known phenomenon; small explicit instance. |
| Lean checker with `decide +kernel` re-checking of external certificates | Verification capability | Certificate checking for SAT (DRAT/LRAT), LP certificates checked in proof assistants (e.g. the Lean `lp` project named in the request; Coq/Isabelle LP checkers) | Same architecture applied to a new certificate type (adaptive experiment policies plus adversary tables plus impossibility pairs). An integration contribution, **not** a mathematical one. |
| Statistical foundations in Lean (StatLean, Mathlib probability) | Existing formalization | Mathlib's measure-theoretic probability, martingales, optional stopping | Our noisy extension avoids measure theory: everything is finite-tree, exact-rational arithmetic. Narrower, and not a replacement. |
| CausalSmith/CausalForge (Tan–Syrgkanis, 2026) | Existing software | Agentic, formally grounded causal-inference research (per the request) | **Not read.** Positioning unknown. It may overlap with the "research engine" loop (Part XI). |
| Optimal experiments for causal effect identification (Akbari et al., 2025; Maringgele–Etesami, 2026) | Established algorithms | Per the titles: cost-optimal intervention sets for (partial) identification in causal graphs, probably via hitting-set / ILP formulations | **Not read.** These address graph-structured, mostly nonadaptive intervention selection. PRISM addresses finite explicit model sets with adaptive policies. The overlap may be substantial at the conceptual level. |
| Canonical domain reduction (Choe et al., 2026) | Established | Per the title: reducing response-function domains for partial counterfactual bounds | **Not read.** Plausibly related to our exact-abstraction results. |
| Active learning for intervention design (Zhang et al., NMI 2023) | Established | Bayesian/active intervention design | Different objective (statistical, not worst-case certified). |

## What we claim as new, stated narrowly

1. **Verification capability (integration).** To our knowledge, though unverified,
   this is a machine-checked chain from a serialized finite model space and
   certificate, through a kernel-checked Boolean checker, to the theorem "this
   adaptive experimental policy is globally minimax-optimal, and the query bounds are
   sharp, under the declared model class". The chain also gives complete
   certificates for impossibility (two models) and for lower bounds (adversary
   tables).
2. **Algorithmic observation (modest).** On families where the hard part of the
   problem lives on a small core while the model space grows multiplicatively
   (nuisance factors), core-guided refinement with sandwich certificates beats
   memoized DP over sub-version-spaces by orders of magnitude (`EXPERIMENTS.md`).
   This is an instance of known counterexample-guided methodology. We present it
   as an engineering result with an exact certificate, not as a new theorem.
3. **Negative findings** (`NEGATIVE_RESULTS.md`), most notably: a small core does not
   imply a small explicit certificate. For OR, the core has n+1 models, yet the
   core-supported explicit adversary table has 2^n − 1 entries. Compact
   certificates for such families need symbolic adversaries, which we only have as
   hand-written Lean proofs.

We do **not** claim a new mathematical theorem of research significance.
