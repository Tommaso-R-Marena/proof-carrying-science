# Technical Report — PCS Causal Laboratory v1

## 1. Repository / branch / isolation

| Field | Value |
|-------|--------|
| Preferred repo | `Tommaso-R-Marena/proof-carrying-causality` — **creation blocked** (GitHub token lacks `create_repository`) |
| Fallback host | `https://github.com/tommaso-r-marena/proof-carrying-science` |
| Branch | `feature/pcs-causal-laboratory-v1-4972` |
| Write namespace | `incubation/pcs_causal_laboratory_v1/` only |
| Base | `origin/main` |

See `NONINTERFERENCE_BASELINE.md` and `reports/NONINTERFERENCE_AUDIT.md`.

## 2. Implemented subsystem inventory

| Subsystem | Location | Status |
|-----------|----------|--------|
| Finite DAG / ADMG | `src/pcs_causal/graphs/` | Working |
| Exact rational PMF | `src/pcs_causal/probability/` | Working |
| Finite SCM + hard `do` | `src/pcs_causal/scm/` | Working |
| Backdoor / frontdoor / do-calc steps | `src/pcs_causal/identification/` | Working (soundness scoped) |
| Non-identifiability search + verifier | `src/pcs_causal/nonident/` | Working |
| Certificate format + fail-closed verifier | `src/pcs_causal/certificates/` | Working |
| Estimation (DIM, IPW, g-comp, AIPW) | `src/pcs_causal/estimation/` | Working |
| Positivity diagnostics | `src/pcs_causal/estimation/positivity.py` | Working |
| PC discovery (oracle + statistical) | `src/pcs_causal/discovery/` | Working |
| Sensitivity / Manski bounds | `src/pcs_causal/sensitivity/` | Working |
| Simulated experiment design | `src/pcs_causal/experiments/` | Working |
| Hypothesis engine + status enum | `src/pcs_causal/hypothesis/` | Working |
| Synthetic / adversarial benchmarks | `src/pcs_causal/benchmarks/` | Working |
| Synthetic drug-response case | `src/pcs_causal/cases/` | Working |
| Local Flask UI | `src/pcs_causal/ui/` | Working |
| Lean 4 + Mathlib formal core | `lean/` | Builds; see formal status |
| CI reference workflow | `ci/github-actions-workflow.yml` | Reference (namespaced) |

## 3. Exact causal model semantics

Finite SCM \(M=\langle U,V,F,P(U)\rangle\):

- Endogenous \(V\), exogenous \(U\), domains finite.
- Mechanisms \(f_v\) evaluated in DAG topological order.
- Observational law = pushforward of \(P(U)\) through \(F\).
- Hard intervention `do(X=x)` replaces mechanisms for intervened variables by constants and mutilates incoming edges — **not** conditioning.

Evidence: `results/backdoor_demo.json`, `tests/test_scm_intervention.py`.

## 4. Lean theorems and axiom audit

Toolchain: Lean 4.28.0, Mathlib v4.28.0. Build: **success** (`results/lean_build.log`).

Proved (no `sorry`):

- Graph mutilation lemmas (`Digraph.mutilate_*`)
- `FinitePMF.eventProb_univ`, `FinitePMF.condition_zero_event`
- Abstract non-identifiability: `nonidentifiable_of_witness`

Open blocker: full backdoor soundness for concrete SCMs (`Identification.lean`).

Axiom audit: `results/lean_axioms.txt`.

## 5. Verified identification

- Backdoor checker recovers exact ATE on synthetic confounding SCM (`identified_ate = true_ate = 1/5`).
- Frontdoor graphical checks with failure cases.
- Do-calculus step checker for delete-obs / action-exchange fragments.

## 6. Non-identifiability

Accepted witness: observational TV = 0, interventional TV = 1/2 (`results/witness.json`). Certificate example verifies independently.

## 7. Estimation

Difference-in-means, IPW, g-computation, AIPW with explicit assumptions; positivity report.

## 8. Discovery

PC oracle on d-separation; Gaussian / discrete CI tests; ambiguous edges preserved.

## 9. Sensitivity / partial ID

Additive bias sensitivity, E-value (RR), Manski ATE bounds → `PARTIALLY_IDENTIFIED`.

## 10. Experiment design

TV-based simulated intervention selection between competing finite SCMs (`simulated_only=true`).

## 11. Scientific case study

Synthetic confounding-by-indication: naive contrast ≠ ATE; Severity backdoor identifies ATE (`results/drug_case.json`). Not clinical advice.

## 12. Counterexamples / negatives

Adversarial suite all true (`results/adversarial.json`). Forged certificates / forged witnesses rejected.

## 13. Trust boundaries

Mathematical acceptance ≠ scientific validation. UI is not authority. Finite witnesses scoped to declared model class.

## 14. Reproduction

```bash
cd incubation/pcs_causal_laboratory_v1
source .venv/bin/activate  # or uv venv
uv pip install -e ".[dev,ui]"
./scripts/run_tests.sh
pcs-causal backdoor-demo && pcs-causal witness && pcs-causal demo-drug
cd lean && lake build
```

## 15. Performance

See `results/performance.json` (backdoor enum <1ms on ≤13 nodes; witness verify ~1ms).

## 16. Security / adversarial

Malformed graphs rejected; float probs rejected; zero conditioning raises; forged `producer_pass` ignored; unsupported cert versions fail closed.

## 17. Noninterference

Audit OK — all paths under `incubation/pcs_causal_laboratory_v1/`.

## 18. Unfinished / blockers

1. Separate private repo creation (token scope).
2. Lean backdoor soundness for SCMs.
3. FCI / PAG latent discovery (researched, not claimed implemented).
4. Root GitHub Actions enablement (outside write namespace).
5. Broader do-calculus completeness (not claimed).
6. Clean-room third-party reproduction package packaging polish.

## 19. Publication notes

Candidate manuscript themes exist (finite identification core; non-identifiability certificates) but are **not** claimed as completed papers. Novelty vs Pearl / Shpitser / existing software is engineering + formalization + exact witnesses, not a claimed breakthrough theorem beyond `nonidentifiable_of_witness` abstractly.

## 20. PCS interoperability

Proposal only: `docs/INTEROPERABILITY_PROPOSAL.md`.
