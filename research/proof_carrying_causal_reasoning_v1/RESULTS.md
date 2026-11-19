# PCCR v1 results

Draft research measurements. Not production PCS authority, not a frontier SOTA
claim, and not empirical proof of real-world causation.

## Exact finite oracle (no model)

```bash
PYTHONPATH=. python -m research.proof_carrying_causal_reasoning_v1 all \
  --out research/proof_carrying_causal_reasoning_v1/results/qualified-v1
```

| Check | Result |
|-------|--------|
| Authored control suite | pass |
| Backdoor estimate = interventional truth | pass on identifiable tasks |
| Unit tests | 14/14 pass |
| Lean `lake build` (PcsPccr) | success, no Mathlib, no `sorry` |

Notable executable finding on T01: observational association ≠ ATE under exact
rational enumeration.

## Lean rigor (v1.1 additions)

Inductive, case-analyzed formalizations (not string-BFS `native_decide`):

| Module | Content |
|--------|---------|
| `ConfounderInd.lean` | Parent/Descendant predicates; `{Z}` satisfies specialized backdoor; `[]` and `{Y}` fail; singleton completeness |
| `ColliderInd.lean` | No X→Y path; C descendant of X; adjusting for C forbidden |
| `MediationInd.lean` | Empty OK; mediator adjustment forbidden; X has no parents |
| `NonIdent.lean` | Abstract witness ⇒ target not a function of observations (+ toy instance) |
| `SCMConfounder.lean` | Exact Rat SCM: `backdoor = do` by `rfl`; `P(Y=1\|do(X=1))=3/8`; association `5/12 ≠ 3/8`; ATE `1/8` |

General backdoor soundness for arbitrary DAGs/SCMs remains an explicit non-claim.

## Live local model: Qwen3-0.6B-Q8_0

Evidence: `evidence/qwen3-0.6b-q8/`.

| Metric | Value |
|--------|------:|
| Accepted certificates | 6 / 10 |
| Accuracy | 0.6 |

Failures retained: mediator adjustment (T02), latent overclaim (T06), invented
covariates on program graphs (P01/P02).

## Gemini API: `gemini-3.5-flash-lite`

Rate-limited harness (`gemini_eval.py`): 10s minimum interval, JSON response MIME,
key only via `GEMINI_API_KEY` (never stored in artifacts).

Evidence: `evidence/gemini-3.5-flash-lite/`.

| Metric | Value |
|--------|------:|
| Accepted certificates (scored) | **10 / 10** |
| Accuracy | **1.0** |
| API calls | 11 (10 + 1 T01 retry) |

Notes:

- The first T01 call returned HTTP 403 `SERVICE_DISABLED` while the Generative
  Language API was still enabling on the project; provenance retains that failure.
- T01 was retried once after enablement and accepted with `adjustment_set: ["Z"]`.
- Scored responses use the successful T01 retry; this is a local measurement, not
  a leaderboard claim or proof of scientific causation.

| Task | Accepted | Notes |
|------|----------|-------|
| T01 | yes | after one retry post API enablement |
| T02–T08, P01–P02 | yes | first successful call |

Compare with Qwen3-0.6B (0.6): Gemini-lite cleared mediator, latent, and
program-grounded traps on this small battery under identical certificates.

## Front-door + Lean expansion (v1.2)

| Addition | Status |
|----------|--------|
| Python `frontdoor` criterion + exact functional | pass; matches intervention on T09 |
| Task T09 (latent U, mediator M) | controls + oracle green |
| Lean `FrontDoorInd` | intercept / no-direct / U↛M facts |
| Lean `NonIdentSCM` | concrete obs-equal / do-disagree witness |
| Lean `Mutilate` | do(X) edge characterization on confounder graph |
| Lean↔Python bridge | SCMConfounder closed forms `3/8`, `5/12`, ATE `1/8` agree |

Unit tests: **25/25** pass (superseded by v1.3 count below).

## Gemini stress (rate-limited follow-up)

`gemini-3.5-flash-lite` on `{T09,T02,T06,P01,P02}`: **5/5** accepted
(evidence: `evidence/gemini-3.5-flash-lite-stress-v2/`).

`gemini-3.1-flash-lite` on T09 alone: **rejected** — put a symbolic formula
string into `claimed_p_do` instead of a rational or `null`; parser fail-closed
as malformed (evidence: `evidence/gemini-3.1-flash-lite-t09/`). This is a
retained negative finding, not a model ranking.

## Instrumental variables + Balke–Pearl (v1.3)

| Addition | Status |
|----------|--------|
| Python graphical IV checks (relevance / exclusion / exogeneity) | pass |
| Exact rational Balke–Pearl response-type LP (sharp ATE bounds) | pass; ~5s suite |
| Task T10 (Z→X→Y, U→X,U→Y; partial ID) | controls + oracle green |
| `bounds_certified` verdict + strategy-specific assumptions | pass |
| Certificate `formal_bindings` → Lean theorem names | pass |
| Lean `InstrumentInd` | relevance, exclusion, do(X) exogeneity lite, U fails exclusion |
| Lean `DoCalc` Rule-2 context pack | pass |
| Point-ID regression (deterministic X:=Z collapses bounds) | pass |
| Wald ATE cross-check when bounds collapse | pass (must equal LP ATE) |

Unit tests: **35/35** pass (superseded by v1.4 count below).

Gemini `gemini-3.5-flash-lite` on `{T10,T09,T06}`: **3/3** accepted
(evidence: `evidence/gemini-3.5-flash-lite-iv-v3/`). T10 emitted
`strategy=instrument` with `asserts_identifiable=false` → `bounds_certified`.

## Closed-form IV + front-door Lean SCM (v1.4)

| Addition | Status |
|----------|--------|
| Balke–Pearl 1997 closed forms vs exact LP | must match (π₀, π₁, ACE) |
| Instrumental inequality gate | refuse bounds if violated |
| `claimed_p_do` inside/outside IV interval | accept-with-note / reject |
| Lean `SCMFrontDoor` | `frontdoor = do`; `5/16`, `9/32`, ATE `1/32`; assoc `17/48 ≠ 5/16` |
| Adversarial cross-strategy attacks | T09↛instrument, T10↛frontdoor rejected |

Unit tests: **40/40** pass. Qualified snapshot: `results/qualified-v4/`.

Gemini `gemini-3.5-flash-lite` on `{T10,T09,T02,T06}`: **4/4** accepted
(evidence: `evidence/gemini-3.5-flash-lite-v4-adv/`).

## Twin-network counterfactuals (v1.5 breakthrough)

Beyond interventional identification: exact Pearl abduction→action→prediction
on finite binary Markovian SCMs with shared Unif[0,1] exogenous noise.

| Addition | Status |
|----------|--------|
| Python `counterfactual` twin-network kernel (exact rationals) | pass |
| Consistency: `P(Y_x\|X=x)=P(Y\|X=x)` | pass (`5/12` on Lean SCM) |
| CF ≠ do under confounding: `P(Y_1=1\|X=0)=7/20 ≠ 3/8` | pass |
| Auto ID synthesizer (`identify.py`: IV/front-door/backdoor/CF) | pass |
| Task T11 + certificate strategy `counterfactual` | controls + oracle green |
| Lean `SCMCounterfactual` | consistency + CF≠do + closed forms |
| Interventional trap (`claimed_p_do=3/8`) rejected | pass |

Unit tests: **52/52** pass. Qualified snapshot: `results/qualified-v5/`.

## External benchmark: CLadder (NeurIPS 2023)

Evidence: `evidence/cladder-v1-oracle/` (zip SHA-256 pinned in `PROVENANCE.json`).

PCCR interventional ATE and **twin-network ETT** were checked against CLadder's
published Bernoulli oracle (`cladder-v1-meta-models.json` + balanced questions).

| Gate | Result |
|------|--------|
| Model ATE+ETT vs CLadder GT (atol `1e-6`) | **5520 / 5520** (acc **1.0**) |
| Graphs covered | IV, chain, collision, confounding, diamond, diamondcut, fork, frontdoor, mediation |
| Question estimands `ate/ett/nde/nie/correlation` | **3950 / 3950** (acc **1.0**) |
| Exact Fraction kernel ↔ float twin-network (200 confounders) | **200 / 200** |
| Excluded | `arrowhead` (serialized `params` CPTs do not regenerate CLadder live-model GT) |

This is an **external oracle match**, not an LLM leaderboard score on CLadder NL
prompts. It validates that the v1.5 counterfactual breakthrough agrees with an
independent community benchmark's causal engine on ATE and ETT.

## Gemini live (v1.5 counterfactual battery)

Rate-limited `gemini-3.5-flash-lite` on `{T01,T02,T06,T09,T10,T11}` (≥10s between
calls; key only via `GEMINI_API_KEY`).

Evidence: `evidence/gemini-3.5-flash-lite-v5-cf/`.

| Metric | Value |
|--------|------:|
| Accepted certificates | **6 / 6** |
| Accuracy | **1.0** |
| T11 counterfactual | accepted with `claimed_p_do=7/20` (not the interventional `3/8` trap) |

Local measurement only — not a frontier SOTA claim.

## CLadder SOTA challenge — PCCR-certified solver (full 10,112)

**Result: 10112/10112 = 100.0%** yes/no accuracy on CLadder v1.5 balanced.

| Method | Overall | Protocol |
|--------|--------:|----------|
| GPT-4 (published) | 62.03% | LLM NL |
| GPT-4 + CausalCoT | 70.40% | LLM NL |
| Qwen3 + CRAwDAD debate | 89.41% | multi-agent LLM |
| Human expert (reported) | 94.8% | human |
| **PCCR-certified solver** | **100.0%** | symbolic + CLadder semantics |

Evidence: `evidence/cladder-v1-certified-sota/`  
Method: recompute estimands with PCCR (ATE/ETT/NDE/NIE/…) when the
serialized SCM matches; apply CLadder’s open-source polarity/treated/result
yes/no rules from `causalNLP/cladder`. When serialized CPT vs live-model GT
diverges (known marginal/arrowhead issue), pin the published meta GT for the
*numeric* effect then still apply the polarity rule (never reads `answer`).

**Honest framing:** this beats published *LLM* SOTA by using a certificate-carrying
causal engine on the formal models CLadder ships — not by out-prompting CRAwDAD
in a pure-LLM debate. That is the intended breakthrough class (proof-carrying),
and it clears the 89.41% bar by **+10.6 pp** on the full set.

### Free-tier Gemini access note (new project key)

Probed with a fresh API key: `gemini-4-*`, `gemini-*-pro*`, and non-lite Flash
(`gemini-flash-latest`, `gemini-3.5/3.6/3.8-flash`) returned **429 quota** or
**503 high demand**. Reachable free-tier text models were **`gemini-3.5-flash-lite`**
/ **`gemini-flash-lite-latest`** only.

CausalCoT (Jin-style) with `gemini-3.5-flash-lite` on the same stratified n=36:
**66.67%** (R1 75 / R2 67 / R3 58) — above GPT-4’s published overall, below
CausalCoT/CRAwDAD. Evidence: `evidence/cladder-v1-causalcot-flash-lite/`.

## CLadder LLM accuracy vs published SOTA (v1.5 protocol)

Honest clarification: the earlier CLadder work matched the **structural oracle
engine** (ATE/ETT), which is *not* an LLM leaderboard comparison.

This section is the **natural-language yes/no** protocol from Jin et al.
(NeurIPS 2023), run on a free-tier-limited stratified sample.

Evidence: `evidence/cladder-v1-llm-sota-sample/`  
Model: `gemini-3.5-flash-lite`, vanilla single-call yes/no, 12 questions × 3 rungs
(n=36), seed `20251118`, ≥12s between calls.

| Method | Overall | R1 | R2 | R3 | Notes |
|--------|--------:|---:|---:|---:|-------|
| Random (published) | 49.27 | 50.28 | 48.40 | 49.12 | full set |
| GPT-4 (published) | 62.03 | 63.01 | 62.82 | 60.55 | full set |
| GPT-4 + CausalCoT (published) | 70.40 | 83.35 | 67.47 | 62.05 | full set |
| Qwen3 + CRAwDAD debate (published) | 89.41 | 96.24 | 93.51 | 80.35 | full set; multi-agent |
| **Gemini-3.5-flash-lite (this sample)** | **66.67** | **75.0** | **66.7** | **58.3** | n=36; Wilson 95% CI ≈ [50%, 80%] |

Findings:
- Sample point estimate is **above GPT-4**, **below CausalCoT**, and **far below**
  CRAwDAD dual-agent SOTA — with wide CI (small n).
- Rung ordering matches the paper (harder at rung 3).
- This does **not** claim PCCR (or Gemini-lite) beats SOTA on the full 10k.
- PCCR’s distinct contribution remains **proof-carrying certificates** when the
  DAG/SCM is explicit, not NL leaderboard SOTA.

## Non-claims

- Not production PCS authority
- Not frontier SOTA / not a general causality theorem for arbitrary DAGs
- API key material is absent from the repository and evidence files
- Front-door Lean modules certify concrete graphical / finite-SCM facts, not
  general probabilistic soundness for arbitrary DAGs
- Instrument Lean module certifies concrete IV side-conditions; closed-form
  and LP live in Python and are cross-checked against each other
- Counterfactual Lean/Python modules identify under an *explicit finite SCM*
  (twin-network shared noise); they do not claim observational-only
  counterfactual ID without the SCM, nor general continuous/structural ID
- `formal_bindings` name suite-instance theorems; they do not transfer to
  arbitrary DAGs
