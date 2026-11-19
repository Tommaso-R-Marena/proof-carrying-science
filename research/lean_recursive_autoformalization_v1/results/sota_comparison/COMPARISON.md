# SOTA comparison (research only)

## FormL4 autoformalization (compile % greedy)

| Method | Basic | Random | Real | Metric |
| --- | ---: | ---: | ---: | --- |
| GPT-3.5-Turbo | 0.29 | 0.41 | 5.10 | Lean compile % (PDA Table 2) |
| GPT-4-Turbo | 1.47 | 0.49 | 10.20 | Lean compile % |
| DeepSeek-Math-Instruct-7B | 1.16 | 0.58 | 0.30 | Lean compile % |
| **PDA RFT+Verifier (paper SOTA)** | **46.28** | **39.38** | **27.90** | Lean compile % |
| PGRA zero-shot (this work, n=8) | 0 | 0 | 0 | controlled-grammar accept |
| Gemini-3.1-flash-lite raw AF (n=8) | soft-F1≥0.5 = **12.5%**; mean F1 **0.36**; exact **0%** | — | — | reference token-F1 proxy (no Mathlib compile) |

Source: arXiv:2406.01940. We could not reproduce PDA's Mathlib compile oracle in this environment.

## miniF2F

| Axis | SOTA (published) | This work (n=8) |
| --- | --- | --- |
| Statement autoformalization | Kimina-Autoformalizer ~92% pass@8; LongCat ~99–100% | PGRA zero-shot **0%**; Gemini soft-F1≥0.7 **100%** (lenient lexical proxy vs gold Lean; **not** SOTA-verified) |
| Theorem proving (gold formal given) | Kimina-72B ~84% pass@32 (TTRL ~92%); OProver-32B ~93% | **Not claimed** — PGRA gate is English→IR, not olympiad proving |

## Verdict

1. **Real external benchmarks used:** FormL4 (PDA) + miniF2F informal.
2. **vs FormL4 SOTA:** Not competitive. PDA ~46% basic compile; our gated path abstains (0%); raw Gemini soft-match << SOTA.
3. **vs miniF2F autoformalization SOTA (~92%+):** Gated PGRA is fail-closed (0%). Raw Gemini lexical overlap looks high but is **not** a substitute for verified autoformalization pass rates.
4. **vs miniF2F proving SOTA (~84–93%):** Different task; no claim.

`pcs_scientific_authority=false`. Subset / free-tier bounded.
