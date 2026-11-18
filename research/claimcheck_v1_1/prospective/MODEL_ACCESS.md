# Model access for the prospective evaluation (owner decision A5)

**Status: prepared, nothing authorised, no paid call made.** Draft 3, 2026-11-18 (changes: [`AMENDMENTS_DRAFT_3.md`](AMENDMENTS_DRAFT_3.md), items 12 to 15 and 18). The frozen, machine-readable form of the identifiers, prices and caps is [`model_config.json`](model_config.json).

## What was verified, and how

On 2026-11-15 about 16:40 UTC the providers' public model listings were read (metadata requests only;
no prompt, article or data was sent):

| Proposer | Identifier in the frozen v1 code | Listed on 2026-11-15 | Price |
| --- | --- | --- | --- |
| Gemini | `gemini-3.6-flash` (Generative Language API, `generateContent`) | yes | not in the listing; must be read from Google's price page before paid use |
| Nemotron | `nvidia/nemotron-3-ultra-550b-a55b:free` (OpenRouter) | yes | 0 on the free tier |
| Nemotron, paid route | `nvidia/nemotron-3-ultra-550b-a55b` (OpenRouter) | yes | 0.60 USD per million prompt tokens, 2.40 USD per million completion tokens |

Newer models are listed by both providers (for example `gemini-3.7-flash`, `gemini-3.8-flash`).
The protocol keeps the v1 identifiers so that v1 and v1.1 results are comparable; changing them is
the owner's choice and must happen before the freeze.

**Not verified, and why:** free-tier quotas cannot be checked without spending them, and providers
change them without notice. The figures below were observed in this project's v1 runs
(November 2026) and are not a promise.

## Measured in v1 (`claimcheck_v1/benchmark/results/heldout/prefetch_ledger*.json`)

| | Attempts | Failed attempts | Prompt tokens per successful call | Output tokens per successful call |
| --- | ---: | ---: | ---: | ---: |
| Nemotron free tier, day 1 | 14 | 0 | 4,404 | 3,032 |
| Gemini free tier, day 2 | 14 | 7 | 5,160 | 563 |
| later prefetch, Gemini | 15 | 5 | 2,846 | 643 |
| later prefetch, Nemotron | 3 | 1 | 2,088 | 134 |

The ledgers record tokens only for attempts that returned text. Draft 2 divided Gemini's totals by
all 14 attempts, failed ones included, and printed about 2,600 and 300 tokens per call; per
successful call they were twice that.

The Gemini free tier refused about half of the attempts and allowed roughly 20 calls a day.

## Requirements

| | 60 papers | 120 papers |
| --- | ---: | ---: |
| documents (original + planted-error copy) | 120 | 240 |
| calls (one per model per document) | 240 | 480 |
| worst case with three repeats of every call | 960 | 1,920 |

## Two configurations for the owner to choose from

**F. Free tiers only.** `gemini-3.6-flash` on Gemini's free tier and
`nvidia/nemotron-3-ultra-550b-a55b:free` on OpenRouter. Cost 0. Calls are paced at 20 Gemini requests
per UTC day (the v1 observation; `model_config.json`), so 120 Gemini calls take at least 6 days and
240 at least 12, plus repeats; a call deferred by the limit is made on a later day, and a call that
failed with a retryable error may be sent again in at most three sessions, at least 24 h apart,
before verification starts (protocol 2). A model withdrawn or changed during the run makes that arm
"not run" for the remaining papers (no substitute model). The 90 % primary-complete rule is at
real risk; the result may well be "not evaluable".

**P. Capped paid route.** `nvidia/nemotron-3-ultra-550b-a55b` (OpenRouter's paid route; the
identifier differs from v1's `…:free`) and `gemini-3.6-flash` on Gemini's paid tier. The cap is
enforced in three layers: (1) the calling code, `prospective/budget.py`, refuses before sending any
request whose worst case (prompt bytes and the maximum output, at the frozen prices) could take
committed spending past the provider's sub-cap or the total cap, refuses a provider without a frozen
price, and keeps a synced spend log from which a resumed run continues; (2) the frozen ledger's
attempt budget, four attempts per call; (3) a hard limit in each provider account, set by the owner
where the provider offers one (an alert that only notifies is not a limit). Nemotron, 120 calls at the measured sizes: 120 × 4,400 × 0.60e-6 + 120 × 3,000 × 2.40e-6
≈ 1.2 USD, at most about 5 USD if every call were repeated. Gemini: price to be read and entered by
the owner in `model_config.json`; until then the guard refuses every paid Gemini request. Proposed
total cap: 15 USD for 60 papers (sub-caps Gemini 10, Nemotron 5), 30 USD for 120 (20 and 10).
Requires the owner's explicit authorisation, which the guard records; no paid call will be made
before it.

## Frozen with the protocol (section 12)

* model identifiers above; endpoint URLs as in `claimcheck_v1/providers.py`;
* prompt and response handling: `claimcheck_v1/propose.py` SHA-256 `a666f065…38edb` and
  `claimcheck_v1/providers.py` SHA-256 `0c56ec87…a6ecca` as of 2026-11-15 (re-pinned at the freeze);
* sampling: temperature 0, at most 16,384 output tokens;
* failures: as in protocol section 2 (repeat only transport, quota and server errors, three times, on
  the fixed schedule; never substitute a model; record every attempt);
* every answer cached by request digest; a re-run never sends a request that already succeeded;
* the proposer calls are made only through `prospective/budget.py` (`fetch_proposals`): one
  `propose_with_model` call per model per document, no critic calls, every attempt in the spend log
  with the version and route the provider reports.

## Data handling

Models receive only sentences of openly licensed articles and the column names of the deposited
table, never data rows, never credentials, never unpublished or uploaded material. Keys stay in the
session's secret store and appear in no prompt, log, receipt or commit. Free tiers may use inputs to
improve the provider's models; that is acceptable only because the inputs are already public.
