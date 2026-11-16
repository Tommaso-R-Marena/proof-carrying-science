# Model access for the prospective evaluation (owner decision A5)

**Status: prepared, nothing authorised, no paid call made.** Draft 2, 2026-11-15.

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

| | Calls | Failed attempts | Prompt tokens per call | Output tokens per call |
| --- | ---: | ---: | ---: | ---: |
| Nemotron free tier, day 1 | 14 | 0 | about 4,400 | about 3,000 |
| Gemini free tier, day 2 | 14 | 7 | about 2,600 | about 300 |
| later prefetch, both | 15 + 3 | 5 + 1 | | |

The Gemini free tier refused about half of the attempts and allowed roughly 20 calls a day.

## Requirements

| | 60 papers | 120 papers |
| --- | ---: | ---: |
| documents (original + planted-error copy) | 120 | 240 |
| calls (one per model per document) | 240 | 480 |
| worst case with three repeats of every call | 960 | 1,920 |

## Two configurations for the owner to choose from

**F. Free tiers only.** Gemini free tier and `…:free` on OpenRouter. Cost 0. At about 20 Gemini calls
a day, 120 Gemini calls take at least 6 days plus repeats; a model withdrawn or changed during the run
makes that arm "not run" for the remaining papers (no substitute model). Given v1's failure rate, the
90 % primary-complete rule of the protocol is at real risk; the result may well be "not evaluable".

**P. Capped paid route.** OpenRouter's paid Nemotron and Gemini's paid tier, each with a hard spending
limit set in the provider account by the owner (the code's per-provider call budget is a second
limit). Nemotron, 120 calls at the measured sizes: 120 × 4,400 × 0.60e-6 + 120 × 3,000 × 2.40e-6
≈ 1.2 USD, at most about 5 USD if every call were repeated. Gemini: price to be read and entered by
the owner. Proposed total cap: 15 USD for 60 papers, 30 USD for 120. Requires the owner's explicit
authorisation; no paid call will be made before it.

## Frozen with the protocol (section 12)

* model identifiers above; endpoint URLs as in `claimcheck_v1/providers.py`;
* prompt and response handling: `claimcheck_v1/propose.py` SHA-256 `a666f065…38edb` and
  `claimcheck_v1/providers.py` SHA-256 `0c56ec87…a6ecca` as of 2026-11-15 (re-pinned at the freeze);
* sampling: temperature 0, at most 16,384 output tokens;
* failures: as in protocol section 2 (repeat only transport, quota and server errors, three times, on
  the fixed schedule; never substitute a model; record every attempt);
* every answer cached by request digest; a re-run never sends a request that already succeeded.

## Data handling

Models receive only sentences of openly licensed articles and the column names of the deposited
table, never data rows, never credentials, never unpublished or uploaded material. Keys stay in the
session's secret store and appear in no prompt, log, receipt or commit. Free tiers may use inputs to
improve the provider's models; that is acceptable only because the inputs are already public.
