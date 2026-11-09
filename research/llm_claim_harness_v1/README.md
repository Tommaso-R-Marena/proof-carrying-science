# Experimental PCS LLM claim extraction harness v1

**Status: research only, not PCS v0.6 authority, and not scientific validation.**

This is a hermetic, independent prototype of a model-proposes / source-checks /
Lean-checks architecture. It changes **no production paths, policy, acceptance,
verification certificates, or historical evidence**. Python 3.11+ standard
library only; no new dependency or provider SDK. It does not merge PR #203.

## Supported, testable boundary

1. Read **plain UTF-8 text** (max 32 KiB). SHA-256 binds exact original bytes;
   offsets use Python Unicode codepoints. PDF/OCR, equations with symbols,
   approximations, units, experimental data, provenance of a PDF extraction,
   and scientific conclusions are **not** supported in v1.
2. Gemini or OpenRouter proposes **literal scalar comparisons** as strict JSON.
   Provider schema hints are advisory; local validation is authoritative for
   whether a candidate can enter this narrow research experiment.
3. Each proposed comparison requires exact source quote and offsets, strict
   allowed syntax, identical numeric operands and comparator, **no assumptions**,
   bounded exact rationals, and duplicate rejection. All failures are recorded.
4. An optional independent model reviews candidates. Unmatched candidates are
   `NEEDS_REVIEW` and cannot reach Lean; agreement is **not** semantic truth.
5. Only generated integer-normalized propositions reach installed Lean 4.28:
   `example : ((a : Int) < (b : Int)) := by decide`. For a false relation the
   generated proposition is its negation. No user/model-generated Lean source,
   imports, axioms, `sorry`, system commands or custom tactics are admitted.
6. A `NORMALIZED_PROVED` / `NORMALIZED_REFUTED` status requires successful
   process invocation of Lean. The Python Fraction normalizer and external
   source-to-normalized correspondence remain **unproved TCB**. Without Lean,
   results are `KERNEL_UNAVAILABLE`, *never* “verified”. These statuses are not
   PCS production certificates. Use Lean's pinned version in actual evaluation.

This design intentionally refuses to certify a paper's interpretation: even
exactly matching `3 > 2` text can be subject to contextual qualifications outside
the span. It certifies only the generated normalized integer comparison.

## Fully offline run (no keys, no network)

From the PCS repository root:

```bash
python -m unittest discover -s research/llm_claim_harness_v1/tests -v
python -m research.llm_claim_harness_v1 \
  --source research/llm_claim_harness_v1/fixtures/source.txt \
  --offline-proposals research/llm_claim_harness_v1/fixtures/proposals.json \
  --offline-reviewer research/llm_claim_harness_v1/fixtures/reviewer.json \
  --out /tmp/pcs-harness-receipt.json
```

If Lean is absent, both fixture claims remain `KERNEL_UNAVAILABLE`.
Unrecognized or unpinned Lean binaries (including `/bin/true`) cannot pass.
The checker requires `Lean (version 4.28.0...)` from the installed binary,
but does not independently authenticate that binary or its host environment. To require
an actual kernel check, install Lean 4.28 and add `--require-lean` (exit code 2
if no candidate passes a kernel check).

## Opt-in external model operation

**Use only public/licensed data approved for external model submission.** Free
Gemini API requests can be used for provider product improvement; OpenRouter
and downstream free model providers may have separate retention/training terms.
Check policies and model availability before running. Requests are capped to
32 KiB input, 32 candidate claims, 30-second request timeout; no automatic
retries, tools, function calls, or hidden web access. Network is **disabled by
default** and API keys stay in environment variables, not receipts or URLs.

```bash
export GEMINI_API_KEY='...'
export OPENROUTER_API_KEY='...'
python -m research.llm_claim_harness_v1 \
  --source ./public-paper-extracted.txt \
  --primary gemini --primary-model YOUR_AVAILABLE_FREE_GEMINI_MODEL \
  --reviewer openrouter --reviewer-model YOUR_AVAILABLE_FREE_OPENROUTER_MODEL \
  --allow-external --lean lean \
  --cache-dir .local/pcs-llm-harness-cache \
  --out .local/pcs-llm-harness-receipt.json
```

**Do not commit `.local/`, receipts, API keys, or provider outputs.** Cache is
optional and stores proposed quotes in plaintext on local disk with 0600 file
modes (not an encrypted vault). The primary/reviewer are sequential and their
contributions are hashed independently. Configurable model choices avoid
assuming that a particular free model will always exist. Missing quota,
malformed JSON and provider errors fail closed; no automatic paid fallback.

## Unresolved obligations before production promotion

- A genuinely verified source-semantics bridge, with document-level context,
  units, scoped identifiers, uncertainty, modalities and disputed interpretations.
- Direct correspondence to existing PCS Claim IR / scientific semantics PRs,
  especially PR #203, preserving their frozen prospective results.
- Real Lean 4.28 hosted CI execution of generated proof scripts, proof-dependency
  audit and pinned toolchain provenance; local testing without Lean is not proof.
- Strict entity/paper provenance, human-reviewed external holdouts, hard negative
  tests and false-certification evaluation (not merely model agreement).
- Dataset privacy/licensing and a formally reviewed promotion gate to the
  existing production v0.6 authority. No automatic promotion is present.

Provider references: https://ai.google.dev/api/generate-content ;
https://openrouter.ai/docs/api/api-reference/chat/send-chat-completion-request .

## Experimental v2 extension: bounded arithmetic ASTs

Select `--mode arithmetic` to let Gemini or OpenRouter **propose exact source
spans**, but **not** propose formal terms or prove mathematical claims. The local
receiver independently parses the span with an explicitly limited grammar:

- Exact literals (integers and decimals, at most six digits before/after the
  decimal), unary minus, `+`, `-`, `*`, `/`, parentheses, and one comparison.
- Every intermediate value is evaluated exactly with Python `Fraction`, with
  bounds on document size, expression size, nesting depth, AST count and value.
- Division by zero, variables, scientific notation, exponents, approximations,
  units, chained comparisons, prose, extra assumptions and imported proof terms
  fail closed. Source offsets and quotes are compared character-for-character.
- Lean source **retains the full arithmetic expression AST in `Rat`** rather than
  substituting an externally computed final number. Lean recomputes the
  expression and checks either the submitted relation or its explicit negation
  using `by decide`. The Python parser, token meaning and source context remain
  external to the Lean theorem and must not be advertised as verified.

Reproduce offline without external credentials:

```bash
python -m research.llm_claim_harness_v1 \
  --mode arithmetic \
  --source research/llm_claim_harness_v1/fixtures/arithmetic_source.txt \
  --offline-proposals research/llm_claim_harness_v1/fixtures/arithmetic_proposals.json \
  --offline-reviewer research/llm_claim_harness_v1/fixtures/arithmetic_reviewer.json \
  --out /tmp/pcs-arith-receipt.json
```

To obtain a **real** Lean 4.28.0 check, install the pinned toolchain and run:

```bash
python -m research.llm_claim_harness_v1.check_live_lean
```

The new `.github/workflows/pcs-llm-claim-research.yml` runs offline tests and a
live Lean smoke gate in CI. It downloads Lean using the existing repository's
SHA-256-pinned installer and neither sends papers to providers nor accesses API
secrets. A model's agreement is only a second untrusted extraction proposal.

**Not established:** sound interpretation of prose, units, symbols, model
assumptions, the correctness of scientific code, or empirical support. The
term *ARITH_EXPR_PROVED* means the generated bounded arithmetic AST proposition
was proved by Lean under the explicitly unverified source-to-AST translation.
Nothing in this research folder is authorized to issue production PCS receipts.
