# Architecture reconnaissance — PCS + this research

**Date:** 2026-11-17 (America/New_York)  
**Auditor worktree:** `/home/ubuntu/worktrees/pcs-scientific-reasoning-v0`  
**Base:** `main` @ `bc78660b`  
**Exclusive namespace:** `research/proof_carrying_scientific_reasoning_v0/` (absent on main before this project)

## 1. Capability map (read-only)

| Capability | Where | Maturity | Relation to this project |
|---|---|---|---|
| Kernel-checked Lean proofs / proof-gating | root `formal/`, PGSI research | Production-adjacent / mature | Use Lean 4.28.0 pin; do not edit |
| ClaimCheck reported statistics | PR #212 draft | Active research | Overlap: claim certificates — **different**: statistics vs scientific argument calculus |
| ClaimCheck assurance / non-escalation | PR #216 draft | Active | Conceptual cousin for *verdict non-escalation*; do not copy namespace or edit |
| Incremental DAG certificate revalidation | PR #217 draft | Active | Overlap: certificates/reuse — **forbidden** to build competing incremental engine; we only model logical retraction |
| Writ compositional authority | PR #209 draft | Active | Execution readback / authority — study boundary only |
| EvidenceKernel causal verification | PR #208/#210 | Active | Causal claims as *external premises* here, not EK internals |
| Scientific intake / semantics / understanding | PR #201–#203 | Active | Source grounding / interpretation ≠ argument calculus |
| Independent scientific review | PR #207 | Active | Replayable reviews — complementary, not duplicated |
| Epistemic obligation lattice | `research/epistemic-lattice-v1` on main | Experimental | Epistemic packaging; not a typed scientific sequent calculus |
| Scientific authority v2 | `research/scientific_authority_v2` on main | Experimental | Intake + Lean receiver + witnesses; not contradiction-aware argument semantics |
| Scientific assurance demos | `research/scientific-assurance-v1` | Demo packages | Fixture-level assurance stories |
| Proof-JEPA / Safety-JEPA | PR #199/#200 | Active | Learning/search — out of scope |
| Checked-lemma reuse | `research/checked-reuse-v*` | On main | Proof-search reuse ≠ scientific argument certificates |

## 2. Open draft PR conflict check

Open drafts #199–#217 inspected. **No open PR creates or owns** `research/proof_carrying_scientific_reasoning_v0/`.  
Closest conceptual cousins: #216 (non-escalation), #217 (certificates), #209 (authority), #201 (intake Incremental.lean). All have exclusive paths we must not touch.

## 3. No-conflict implementation plan

1. All writes under exclusive namespace only.  
2. Pin Lean `leanprover/lean4:v4.28.0` locally in `lean/lean-toolchain` (copy pin; no root edit).  
3. Object-level scientific calculus *inside* Lean (not modifying PCS kernel libraries).  
4. Retraction = recompute/invalidate certificates logically; **no** Affected-closure cache engine.  
5. Case studies synthetic; no private lab data.  
6. Draft PR after Lean build + tests; expect `source-policy` census failure until admission (do not weaken).

## 4. Study but do not modify

Root `pcs/`, root `formal/`, `.github/`, integration manifests, SVB, website repo, all other `research/*` paths, PR branches for #212/#216/#217/#209/#208/#201.

## 5. Do not reinvent

- ClaimCheck statistic certificates.  
- EvidenceKernel identification proofs.  
- ICR incremental revalidation.  
- Writ execution authority.  
- Scientific authority v2 intake/signing stack.

## 6. Critical missing capability (gap this project targets)

PCS can check mathematical/statistical artifacts and bind sources, but lacks a **standalone, contradiction-aware scientific argument calculus** that:

- separates mathematical validity from empirical assertion;  
- records indispensable assumptions;  
- contains contradictions without classical explosion;  
- emits independently replayable argument certificates;  
- refuses authority escalation from “derived under assumptions” to “empirically verified.”

## 7. Trust-boundary analysis

| Layer | Trust |
|---|---|
| Lean kernel + this package's checked theorems | Mathematical (object-level) |
| Python reference evaluator | Research prototype — differential vs Lean / independent checker |
| Independent checker | Small TCB; must not import reference evaluator |
| Empirical observations / citations in arguments | **Externally asserted** — never auto-promoted |
| LLM proposals (if any) | Untrusted input only |
| OS / filesystem / JSON parser | Trusted for research; not proved |

## 8. What current PCS does / does not establish (relevant slice)

**Does (in various subsystems):** kernel-checked math; some source binding; research-level authority packaging; incremental *computation DAG* certificate revalidation (PR #217); causal verification research (EK).

**Does not (hence our target):** prove that a scientific narrative is true of the world; globally paraconsistent classical Lean; automatic resolution of conflicting studies; production scientific-argument certificates with assumption/retraction semantics as specified here.

## CI note

Research-only additions typically fail sealed `source-policy` / `verified-public-integration` until admission. **Do not weaken those gates.**
