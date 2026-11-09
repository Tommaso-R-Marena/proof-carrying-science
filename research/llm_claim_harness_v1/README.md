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
  using `by decide +kernel` (no native evaluation or new axiom). The Python parser, token meaning and source context remain
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

## Free deterministic-first discovery

For documents that already put explicit comparisons on separate lines, no LLM
call is needed. The strictly bounded local scanner reuses the exact same
validators and skips unsupported lines instead of guessing their interpretation:

```bash
python -m research.llm_claim_harness_v1 \
  --mode arithmetic --primary deterministic \
  --source research/llm_claim_harness_v1/fixtures/arithmetic_source.txt \
  --out /tmp/pcs-deterministic-receipt.json
```

You can optionally use the external `--reviewer` with explicit
`--allow-external`, but a second model is not an authority. Deterministic
standalone-line discovery is a **cost-saving fast path**, not complete document
coverage: prose-embedded, context-dependent, symbolic and scientific claims are
skipped rather than declared absent or false. More expensive LLM extraction
remains available where its narrower benefits are demonstrably useful.


## Experimental v3: explicit source-grounded typed quantities

`--mode typed` accepts only a **standalone `PCS-TYPED/1` plain-text program**, not
arbitrary prose, extracted PDF equations, or LLM-inferred meaning. Example:

```text
PCS-TYPED/1
let mass : kg = 2
let acceleration : m/s^2 = 3
let distance : m = 2
let offset : cm = 30
assert mass * acceleration = 6[N]
assert distance + offset = 2.3[m]
assert distance + offset = 2.4[m]
```

Run without API keys:

```bash
python -m research.llm_claim_harness_v1 \
  --mode typed --primary deterministic \
  --source research/llm_claim_harness_v1/fixtures/typed_source.txt \
  --out /tmp/pcs-typed-experiment.json
```

Only literal `let name : unit = exact_value` declarations **before any**
assertions are accepted. `assert` must consume an entire nonblank source line.
Each LLM proposal consists only of a source span, its exact quote and empty
assumptions; the model may not define variables, units, scientific premises or
Lean code. The receiver parses claim syntax deterministically, with no
`eval`, imported source code execution, regex-derived model promises, or
unbounded symbolic search. A reviewer may select the same exact claim; model
agreement never authorizes a proof by itself.

Exact rational arithmetic and compositional dimensional checks support `+`,
`-`, `*`, `/`, parentheses, unary signs, and one comparison. Numeric literals
may carry a bracketed unit (`30[cm]`); otherwise they are dimensionless.
Declarations require a unit. Unit definitions include SI base units and a small
hardcoded subset of exact, non-affine derived units (`g`, `cm`, `L`, `N`, `Pa`,
`J`, `W`, `Hz`, etc.). Unit exponents and rational magnitudes are bounded. There
is no conversion for offset units such as Celsius, measurement uncertainties,
statistical estimators, nonlinear functions, implicit multiplication, scientific
notation, time-dependent states, external ontologies or partial interpretations.

Every accepted assertion carries SHA-256 of its original source and declaration
bindings, exact offsets, normalized SI dimensions and values, the complete
Lean-generated source, and an explicit experimental authority label. The fixed
Lean interpreter re-evaluates the **complete quantity expression AST** as
`Option PCSQty`, including the seven-component SI exponent vector, dimension
compatibility of additions and comparisons, and exact rational operations.
Lean checks either `some true` or `some false` via `by decide +kernel`; a
mixed-unit error or unknown operation does not produce an accepted assertion.
`TYPED_QTY_PROVED` means the *generated closed proposition* was checked, not
that a scientific measurement or its external provenance was verified. Model
interpretation, unit parsing, source-to-AST translation, the Python arithmetic
and the external compiler/runtime remain trust assumptions.

The hosted Lean smoke task now includes five typed quantities (four true and one
false) alongside the previous five arithmetic/literal checks. No API keys or
paid services are needed for this reproducible experiment. Existing PCS production
verification, PR #203, and independently frozen evidence are unchanged.

**Next research milestone:** source-specific typed declaration adapters for
human-annotated CSV/SBML projects, with explicit identifier scope, unit
provenance, versioned IR schema and a prospective false-certification benchmark.
No direct import from the unmerged PR #203 is attempted.

## Experimental v4: source-line evidence bridge with review-only semantics

`--mode evidence` reads an **arbitrary UTF-8 plain-text source** (up to 32 KiB),
including narrative text around source declarations and equations. It does
**not** understand unconstrained scientific prose or PDF screenshots. This
is the first explicitly non-DSL ingestion path: only complete standalone
source lines with *explicit* quantity values and units, e.g. `mass = 2 kg`,
`acceleration: 3 m/s^2`, and an equation `mass * acceleration = 6 N`,
qualify. Scientific text around these lines is retained but **not interpreted**.

Try the privacy-preserving, zero-API route:

```bash
python -m research.llm_claim_harness_v1 \
  --mode evidence --primary deterministic \
  --source research/llm_claim_harness_v1/fixtures/evidence_source.txt \
  --out /tmp/pcs-evidence-v4.json \
  --review-html /tmp/pcs-evidence-v4-review.html
```

An optional Gemini or OpenRouter model can *select* whole equation lines by
returning their exact source spans and quotes. It cannot propose new values,
units, assumptions, or Lean code. The parser discovers complete source
declaration lines independently. Duplicate declarations, undefined identifiers,
future declarations, unit mismatches, unsupported equations, partial source
lines, and schema alterations fail closed. The bridge converts only explicit
literal unit suffixes such as `6 N` to `6[N]` and reuses the fixed v3 typed
AST interpreter and Lean check without importing model-generated proof scripts.
Model comparison remains optional; disagreement blocks the formal step.

Receipts maintain **three separate status dimensions**:
- `formal_status`: the *generated* closed arithmetic proposition's Lean
  result, if an actual Lean 4.28.0 check ran (e.g. `TYPED_QTY_PROVED`).
- `semantic_fidelity`: always `UNREVIEWED` in v4. The scientific statement
  might be a hypothesis, a denial, a quotation, an obsolete measurement,
  or an approximation despite the equation line's syntax.
- `scientific_status`: always `NOT_ASSESSED`. No empirical inference,
  measurement uncertainty, code reproduction, model assumption, or external
  citation is verified here.

The top-level claim `status` remains `SEMANTIC_REVIEW_REQUIRED` even after
kernel success. A missing Lean executable is explicitly `KERNEL_UNAVAILABLE`.
Source and each contributing declaration are linked by exact Unicode spans and
SHA-256 hashes. The opt-in static HTML review escapes all untrusted strings,
has no JavaScript or external resources, and **is not an approval mechanism**.
The report itself may contain potentially sensitive excerpts; do not publish
it without reviewing their contents.

The hosted CI smoke checks **two additional evidence-linked propositions**
(one true, one false) using actual Lean 4.28.0. The offline test suite includes
cases where earlier declarations change without changing the quoted equation:
this must produce a *different* source/proof obligation rather than reusing
any previous formal result.

**Known limitations:** only exact decimal rational values and a small unit
whitelist; one unambiguous equation or comparison per source line; declarations
must precede use; no CSV, PDF, SBML, complex scientific notation, uncertainties,
scoped models or full Claim IR equivalence yet. This is a research adapter and
does not modify production PCS or the unmerged PR #203. Follow-on work is a
prospectively evaluated typed source-IR interoperability adapter, with human
scientific semantic review and truly independent empirical validation.
