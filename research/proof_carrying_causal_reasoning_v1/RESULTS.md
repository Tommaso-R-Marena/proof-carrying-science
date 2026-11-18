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

## Non-claims

- Not production PCS authority
- Not frontier SOTA / not a general causality theorem
- API key material is absent from the repository and evidence files
