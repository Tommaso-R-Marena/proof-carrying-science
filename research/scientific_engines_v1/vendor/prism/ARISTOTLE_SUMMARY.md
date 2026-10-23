# Summary of changes for run 11280e91-0509-48a4-9f26-4dc74792ee5a
PRISM is built, and its central guarantees are proved in Lean. It is a solid foundation (Tier 1 of your rubric) with parts of Tier 2. It is not a breakthrough: almost all the mathematics is classical or elementary, and the speedup appears only on a family I designed to favour it. There was no internet access, so the literature comparison is from memory and everything about the 2025–2026 references is marked unverified.

**Formal proofs.** The Lean library `PRISM` builds cleanly with Lean 4.28.0 and Mathlib v4.28.0, with no `sorry`, `admit`, custom axioms, `native_decide`, `implemented_by` or linter warnings. `results/axiom_audit.txt` covers 73 theorems; each uses only `propext`, `Classical.choice` and `Quot.sound`. The main results:
- **Inference:** query bounds are sound and sharp (`bounds_sound`, `bounds_sharp`). An empty set of admissible models is reported as INCONSISTENT, never as vacuous certification. Certification relative to the model class does not imply real-world truth (`certified_does_not_imply_truth`).
- **Optimal experiments:** the Bellman recurrence is proved, not assumed. The value it computes is the minimax-optimal worst-case cost over *all* adaptive policies (`value_optimal`, `value_le_iff`). Termination, tie-breaking and uselessness of uninformative experiments are separate lemmas.
- **Impossibility:** `impossibility` proves your Part V statement. `identifiable_iff` gives an exact condition: a successful strategy exists iff every observational-equivalence class has query spread ≤ ε. So whenever the goal is unreachable, two models suffice as a certificate.
- **Lower bounds:** these always have a locally checkable certificate (`le_value_iff_adversary`).
- **Optimality sandwich:** a certificate checked on an outer set proves exact optimality for every model set between a small core and that outer set, without enumerating it (`checkSandwich_sound`).
- **Nuisance factors (`value_prod_eq_section`):** if each experiment depends only on the query-relevant factor or only on a nuisance factor, the optimum equals the optimum on a single nuisance slice. `nuisance_mixing_counterexample` shows the condition is necessary. This is my best candidate for a new formulation, but it is a formal version of folklore.
- **Noisy extension:** any adaptive procedure that follows the mixture rule falsely certifies with probability ≤ α (`false_certification_le`). The post-hoc maximum-likelihood variant is formally invalid (`posthoc_alternative_invalid`).
- **Families:** the OR problem has exact cost n for every n (`or_value`). The pointer family has adaptive cost ≤ 2 vs nonadaptive ≥ n+1 (`ptr_nonadaptive`). On the trap instance greedy costs at least 5 against an optimum of 4 (`trap_greedy_suboptimal`).

**Independent verification.** The Lean checkers carry soundness proofs, and certificates generated from the demos are re-checked by the Lean kernel. `python/verify.py` checks a certificate file without trusting the search engine, optionally via Lean. The Python-to-Lean translator and the parser are trusted but unverified (`docs/TRUST_BOUNDARIES.md`).

**Demonstrations:** all synthetic.
- **Biochemical:** sharp bounds [1/4, 5/6], an optimal first experiment with cost 3, and IMPOSSIBLE under a restricted assay set.
- **Causal:** finite-grid bounds [−1/3, 2/3], equal to the Manski bounds. Observational experiments alone give IMPOSSIBLE.
- **Scalable:** see the benchmarks below.

**Tests:** these pass, and the full pipeline in `scripts/run_all.py` completed:
- 400 random instances on which all exact solvers agree;
- 1,122 tampered certificates, all rejected, with 0 false accepts;
- Lean and Python checkers agree on honest and tampered certificates.

**Benchmarks** (`results/report.html`, `docs/EXPERIMENTS.md`):
- **Lesion family:** optimality is certified for up to 131,072 models in about 9 s (plus about 4 s of independent checking). With 8 pathway steps, naive DP times out at 10 s from 2,048 models and pruned DP from 32,768.
- **Random held-out instances and OR family:** no advantage, and on random instances the sandwich is 1.3–3.3× slower than pruned DP.
- **Certificate size:** a small core does not give a small certificate. For OR, the explicit lower-bound table has 2^n − 1 entries even though the core has only n+1 models.

During the work I found and fixed a quadratic-time validation bug; reported numbers are from the fixed code.

**Not done:** symbolic model representations (the method still lists every model explicitly), a verified parser, a Lean proof that the refinement loop terminates (checked at runtime only), comparison with MILP/SAT solvers, and any real-data study. `docs/NEGATIVE_RESULTS.md` lists these and the counterexamples.

**Ratings** (1–10, `docs/BREAKTHROUGH_ASSESSMENT.md`): mathematical novelty 2, formal rigor 7, algorithmic improvement 3, scientific utility 3, demonstrated impact 1.

Everything is in the project; start with `README.md`, then `docs/RESEARCH_PAPER.md` and `docs/THEOREMS.md` (`docs/` also holds the other required write-ups). The whole repository is packaged as `PRISM_artifact.tar.gz`.