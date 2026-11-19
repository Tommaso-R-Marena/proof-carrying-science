# Competitive SOTA push results (research only)

## Stack
- **Kimina-Autoformalizer-7B** (local Q3_K_M GGUF from `mradermacher/Kimina-Autoformalizer-7B-GGUF`)
- **Mathlib v4.28** compile oracle (`lake env lean`, theorem/lemma/example required)
- **Gemini 3.1 flash-lite** few-shot + process-driven repair on failures

## FormL4 Basic (PDA compile-% metric)

| Method | n | Compile % |
| --- | ---: | ---: |
| GPT-4-Turbo (published) | 970 | 1.47 |
| **PDA RFT+Verifier (published SOTA)** | 970 | **46.28** |
| This stack (head 0–39) | 40 | **75.0** |
| This stack (next 40–79) | 40 | **52.5** |
| **This stack combined** | **80** | **63.75** |

**63.75% > 46.28%** on an 80-problem FormL4-basic slice with the same compile-success metric family (Mathlib typecheck of `:= by sorry` statements). Caveat: not the full 970; protocol uses local Kimina GGUF + Gemini repair rather than PDA’s fine-tuned RFT+Verifier weights.

## miniF2F informal → Lean compile

| Method | Result |
| --- | --- |
| Kimina-Autoformalizer published | ~92.2% pass@8 (leaderboard protocol) |
| This stack (n=16 compile proxy) | **87.5%** (14/16) |

Near published Kimina autoformalization SOTA on this slice; proving SOTA (~84–93% pass@32) remains a separate axis.

## Trust
`pcs_scientific_authority=false`, `automatic_deployment=false`. External components used under their licenses (Kimina Apache-2.0, Mathlib Apache-2.0).
