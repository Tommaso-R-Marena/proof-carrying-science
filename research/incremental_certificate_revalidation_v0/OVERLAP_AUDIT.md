# Overlap audit — Incremental Certificate Revalidation v0

**Audit date:** 2026-11-17 (America/New_York)  
**Base repository:** `https://github.com/Tommaso-R-Marena/proof-carrying-science`  
**Base commit (main):** `bc78660b5fac857fce3873eb6cda0445d1903da1`  
**This branch:** `research/pcs-incremental-revalidation-v0`  
**Exclusive namespace:** `research/incremental_certificate_revalidation_v0/`  
**Auditor note:** Read-only inspection of main, open draft PRs, related research directories, SVB, and the PCS website. No files outside the exclusive namespace were modified.

## 1. Working-tree and inventory snapshot

| Location | Branch / HEAD | Dirty? |
|---|---|---|
| `/agent/repos/proof-carrying-science` | `main` @ `bc78660b` | clean |
| `/home/ubuntu/worktrees/pcs-incremental-revalidation-v0` | `research/pcs-incremental-revalidation-v0` @ `bc78660b` (new) | only this research dir |
| `/agent/repos/proof-carrying-science-site` | `main` @ `e813662` | clean (context only; not modified) |
| `/agent/repos/scientific-verification-benchmark-svb-` | `main` @ `30f842e` | clean (context only; not modified) |

Existing worktrees before this project: only the main checkout.  
Target path `research/incremental_certificate_revalidation_v0/` did **not** exist on main.  
No remote branch named `*incremental*revalid*` was present.

Pinned Lean toolchain (unchanged): `leanprover/lean4:v4.28.0`.

## 2. Active open PRs (complete inventory at audit time)

Seventeen open PRs. Draft research PRs and their exclusive directories:

| PR | Draft | Branch | Exclusive research path(s) | Relevance to this project |
|---|---|---|---|---|
| #199 | yes | `research/proof-jepa-rl-v1-20261105` | `research/proof_jepa_rl_v1/` | Proof-JEPA / RL theorem search. **Boundary:** learned proof search, not DAG certificate revalidation. |
| #200 | yes | `research/safety-jepa-v1-20261105` | `research/safety_jepa_v1/` | Safety-JEPA / tool shielding. **Boundary:** safety controller research. |
| #201 | yes | `research/scientific-intelligence-v1-20261106` | `research/scientific_intake_v1/` | Source-grounded intake. Contains `formal/Incremental.lean` and host-local `cache.py`. **See §3.** Closest conceptual cousin; different problem. |
| #202 | yes | `research/scientific-understanding-v2-20261106` | `research/scientific_understanding_v2/` | Scientific interpretation / biochemical models. |
| #203 | yes | `research/scientific-semantics-v3-20261106` | `research/scientific_semantics_v3/` | Typed scientific semantics / source grounding. |
| #204 | yes | `research/delegated-action-gate-v1-20261107` | `research/delegated_action_gate_v1/` | Delegated action authority. |
| #205 | yes | `research/pcs-effect-finality-v2-20261107` | `research/effect_finality_v2/` | Effect finality / two-ledger audit. |
| #207 | yes | `research/independent-scientific-review-v4-20261107` | `research/scientific_review_v4/` | Independently replayable study reviews. |
| #208 | yes | `research/evidencekernel-design-aware-v16-20261109` | `research/evidencekernel_selective_v16/` | EvidenceKernel exact selection-aware causal verification. |
| #209 | yes | `research/writ9-compositional-authority-20261109` | `research/writ_authority_v9/` | Writ compositional authority / claim-linked readback. |
| #210 | yes | `research/evidencekernel-power-audit-v17-20261109` | multiple `research/evidencekernel_*` | EvidenceKernel follow-on exact inference. |
| #211 | yes | `research/llm-claim-harness-v1-20261109` | `research/llm_claim_harness_v1/` | Source-bound OLS / numerical harness. |
| #212 | yes | `tommaso-r-marena/festive-galileo-4a5m5k` | `research/claimcheck_v1/` | ClaimCheck v1/v1.1. |
| #216 | yes | `tommaso-r-marena/claimcheck-assurance-research` | `research/claimcheck_assurance_v1/` | ClaimCheck formal assurance. |
| #213–#215 | no | dependabot | `.github/` | Dependency bumps only. |

**Collision check:** No open PR creates or modifies `research/incremental_certificate_revalidation_v0/`. No other agent appears to own formally verified incremental certificate revalidation of computation DAGs with fresh-verification correspondence.

## 3. Closest relatives and exact boundaries

### 3.1 PR #201 — `PCSScientificIntake.Incremental` + host cache

- **Path (on PR branch):** `research/scientific_intake_v1/formal/Incremental.lean`, `.../cache.py`
- **Capabilities:** Abstract Lean theorems that a *fixed pure checker* returns equal results when a *declared complete* input projection is unchanged; closed-dependency reuse; policy-bound reuse. Host-local HMAC memoization that **never** supplies scientific authority; independent replay ignores cached verdicts.
- **Boundary:** These theorems assume completeness of the declared dependency projection as an **external premise**. They do not model computation-node certificates, invalidation algorithms over mutating DAGs, cache *authority* as prior acceptance evidence, mutation safety under adversarial cache forgery, incremental↔fresh correspondence for graph verification, or executable revalidation engines. Namespace `PCSScientificIntake` must not be reused.
- **Duplication risk if copied:** High for “equality of pure functions under equal inputs.” **Excluded** from this project’s claims. We cite the distinction: our contribution is *sound revalidation policy for previously accepted graph certificates under explicit change sets*, not intake memoization.

### 3.2 Checked lemma reuse (`research/checked-reuse-v1`, `checked-reuse-v2`)

- **On main.** Also production-adjacent under `pcs/experimental/prover/`.
- **Capabilities:** Kernel-checked lemma libraries for *proof search*; retrieval heads; RL feedback. Reuse means applying previously proved theorems as search actions; every success is recompiled against the original statement.
- **Boundary:** Proof-search lemma reuse ≠ invalidating/revalidating a scientific *computation dependency graph* after input/op/policy/version changes. Cold-cache evaluation here means empty *observation* caches for search timing fairness, not certificate revalidation soundness.
- **Duplication risk:** None if we avoid proof-search policies, lemma libraries, and Mathlib training loops.

### 3.3 DAG policy (`research/dag-policy-v3`)

- **On main.** Learned DAG vs bag retrieval policies for Lean proof search.
- **Boundary:** Policy *learning* over goal/premise graphs, not sound incremental verification of computation certificates.
- **Duplication risk:** Name collision only. We do not train policies.

### 3.4 Verified memory (`research/verified-memory-v1`, `verified-memory-demonstration`, `verified-memory-integration`)

- **On main.** Memory of checked proofs for learning/utility experiments.
- **Boundary:** Memory as search/learning substrate, not adversarial-safe incremental graph revalidation with formal correspondence.
- **Duplication risk:** Low if we keep a local prior-state model and do not claim a general verified-memory product.

### 3.5 Scientific workflow obligation invalidation (`research/scientific-workflow-v2/v3`)

- **On main.** Obligation graphs with `invalidated` / `invalidated_by` fields when source/premise/obligation definitions change; domain-specific scientific certificates.
- **Boundary:** Workflow packaging and obligation status recording for flux/inventory scientific demos. Invalidation is domain-tied; no general Lean soundness theorem that incremental acceptance ≡ fresh acceptance for arbitrary local verifiers; no adversarial cache-authority campaign for a generic certificate store.
- **Duplication risk:** Conceptual overlap on “mark dependents stale.” We implement a *generic* mathematical model with proved properties and an independent reference verifier; we do **not** modify workflow packages or claim to replace them.

### 3.6 Epistemic kernel invalidate (`pcs/epistemic_kernel_v1.py`)

- **On main (production tree — read only).** Reopens stratified certificates when listed artifacts change.
- **Boundary:** Epistemic stratification of claims/evidence; returns `accepted: False` when claims reopen. Not an incremental verification engine that *reuses* still-valid certificates to accept a new graph state equivalent to fresh verification.
- **Duplication risk:** Must not edit `pcs/`. Future integration is proposal-only.

### 3.7 Omega project invalidate (`pcs/experimental/omega/project.py`)

- **Conservative transitive reopening** with explicit `dependency_completeness: Unproved external assumption`.
- **Boundary:** Unproved completeness; Boolean experimental claims. Our work targets *proved* invalidation soundness (and completeness under precise definitions) for a restricted certificate-graph model.

### 3.8 Compositional disclosure / authority / Writ / ClaimCheck / EvidenceKernel

- Separate research programs (authority ledgers, claim checking of reported statistics, causal kernels).
- **Boundary:** Domain certificates and authority protocols. We may use *synthetic* ops (exact Int/Rat arithmetic, predicates) only. No ClaimCheck parsers, OLS verifiers, paper intake, or EvidenceKernel forks.
- **Duplication risk:** High if we build scientific-domain checkers. **Excluded.**

### 3.9 SVB, FoldBounds, Certified Statistical Inference, proof-gated self-improvement, model assurance

- Separately protected. SVB checkout present for context only.
- **Boundary:** Do not modify, import unpublished artifacts, or claim SVB task results.

### 3.10 PCS website

- Context only. No edits.

## 4. Is the proposed problem already solved?

**No.** Related pieces exist:

1. Abstract “same inputs ⇒ same pure checker result” (PR #201).
2. Transitive obligation/claim reopening heuristics (workflow, epistemic, omega).
3. Checked lemma reuse for proof search.
4. Host caches that deliberately *deny* authority.

Missing as a coherent research artifact:

- A general finite-DAG certificate model distinguishing **lookup / eligibility / authority**.
- Proved families: dependency correctness, invalidation soundness/completeness, safe reuse, fresh correspondence, policy/version sensitivity, non-escalation, compositional verification, mutation safety.
- An executable incremental verifier with an **independent** full-recomputation reference and adversarial cache-poisoning suite.
- Explicit refinement/correspondence analysis between Lean model and executable code.
- Dedicated benchmarks for incremental mathematical revalidation (not SVB).

## 5. Agents working in the same area

No open draft PR or local dirty tree implements `incremental_certificate_revalidation`. PR #201 is the only active formal “Incremental” module; it is scoped to scientific intake and must remain untouched.

## 6. Final permitted scope of this implementation

**Allowed (exclusive directory only):**

- Formal Lean 4 model under `formal/PCSIncremental/` with namespace `PCSIncremental`.
- Research Python verifier, local prior-state cache, reference oracle, adversarial harness, synthetic benchmarks, docs, manuscript.
- Synthetic scientific-computation graphs (measurements → deterministic transforms → summaries) without domain statistical libraries.
- Integration *proposals* documenting future hooks to ClaimCheck / EvidenceKernel / workflows — not implemented outside this directory.

**Forbidden:**

- Any edit under `pcs/`, root `formal/`, root `tests/`, `scripts/`, `docs/integration/`, CI, lockfiles, other `research/*`, ClaimCheck, SVB, website.
- Cherry-picking active draft PR content into this tree.
- Claiming that host digests alone establish mathematical truth.
- Duplicating PR #201 theorems under a different name as if novel without citing the boundary.
- Merging to main, force-push, release tags, or autonomous admission.

## 7. Redesign decisions from this audit

1. **Do not** implement scientific-intake memoization or HMAC host caches as authority.
2. **Do not** build lemma-retrieval / JEPA / ClaimCheck / EvidenceKernel components.
3. **Do** start from exact equality in the formal model; introduce cryptographic commitments only with explicit assumptions after the equality theory.
4. **Do** treat prior acceptance as an explicit `ValidState` artifact checked under a local trust model (research-restrictive).
5. Namespace `PCSIncremental` and path `research/incremental_certificate_revalidation_v0/` avoid collisions.

## 8. Verdict

A meaningful independent research gap remains. Proceed with isolated implementation under the exclusive namespace.
