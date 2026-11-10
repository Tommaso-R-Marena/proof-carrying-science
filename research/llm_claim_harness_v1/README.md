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


## Experimental v5: exact-cell CSV-to-Lean verification

`--mode table` extends the deterministic verified-arithmetic path to actual
numeric **CSV file bytes**. A separate, caller-supplied JSON manifest declares
exact column names, units, and up to four formula templates; PCS never infers
column meanings, missing units, experimental assumptions, or mathematical
formulae from an LLM response. This path intentionally makes **zero API calls**.

```bash
python -m research.llm_claim_harness_v1 \
  --mode table --primary deterministic \
  --source research/llm_claim_harness_v1/fixtures/table_data.csv \
  --table-spec research/llm_claim_harness_v1/fixtures/table_spec.json \
  --out /tmp/pcs-table-v5.json
```

The fixture has two rows and two assertions per row. One row reports an
inconsistent force (the calculated `mass * acceleration` equals 8 N but the
reported value is 9 N). In the absence of Lean the four generated obligations
are `KERNEL_UNAVAILABLE`, not asserted as kernel verified. A real Lean 4.28.0
run can distinguish this row as a refuted closed mathematical proposition.

The table manifest uses the exact schema:

```json
{
  "schema": "pcs-tabular-evidence-v5-research",
  "columns": [
    {"name": "mass", "unit": "kg"},
    {"name": "acceleration", "unit": "m/s^2"},
    {"name": "reported_force", "unit": "N"}
  ],
  "assertions": [
    {"id": "force_check", "expression": "mass * acceleration = reported_force"}
  ]
}
```

The parser accepts only unquoted ASCII CSV with exactly matching headers,
1–16 numeric rows, at most 24 named columns and four checked assertions per
row (64 proof attempts maximum). CSV cells must be bounded exact decimal or
integer literals. Quoted cells, embedded line breaks, comments, missing values,
scientific notation, spreadsheets, uncertainties, text IDs and flexible CSV
formats fail closed. LF and CRLF records work with *byte-exact* cell offsets.
All data are parsed and all obligations constructed successfully before any
Lean proof attempts are run. Invalid units, missing columns, malicious code,
unsupported formulae, dimension mismatches, division by zero and missing
observations cause the whole table run to reject. The tabular path never
submits source files to Gemini/OpenRouter and refuses model/reviewer flags.

Every row-level receipt binds raw dataset SHA-256, manifest SHA-256, CSV row
hash, precise byte spans and per-cell hashes, a typed AST hash and generated
Lean source hash. The receipt's top-level status remains
`SEMANTIC_REVIEW_REQUIRED`, and the scientific assessment remains
`NOT_ASSESSED` even if Lean proves a closed row proposition. A caller-supplied
manifest is **not** a verified human review or a certified unit ontology.

Unproved boundaries include CSV bytes-to-cells Python parsing, quantity
lexing and translation to Lean, compiler/runtime authenticity, correctness of
supplied column meanings, statistical or physical assumptions, and whether
the mathematical template is scientifically appropriate. This does not claim
to verify arbitrary CSV formats, causal claims, model fit or research papers.
It does not modify PCS production validity or accept model-generated proof
source. Hosted Lean smoke tests include four tabular proof obligations in
addition to the earlier twelve.


### Rechecking a delivered v5 CSV receipt

For a locally generated receipt, rerun the exact source bytes, manifest, and
all proof obligations **with installed Lean 4.28.0**. The original receipt's
`kernel_checked` flags are not trusted; a source/hash mismatch, altered proof
source, modified row, noncanonical receipt, missing Lean, or incomplete replay
must fail closed:

```bash
python -m research.llm_claim_harness_v1.replay_table \
  --source research/llm_claim_harness_v1/fixtures/table_data.csv \
  --table-spec research/llm_claim_harness_v1/fixtures/table_spec.json \
  --receipt /tmp/pcs-table-v5.json --out /tmp/pcs-table-replay-v5.json \
  --lean lean
```

Exit 0 and `REPLAYED_MATHEMATICAL_RECEIPT` only when the new result is
byte-equivalent after canonical JSON parsing **and all rows pass fresh Lean**.
Missing Lean returns exit 2 (`KERNEL_UNAVAILABLE_OR_REJECTED`) rather than
trusting a stored success. The source and manifest **must be obtained through a
trusted independent channel**; otherwise an attacker can replace all three.
This replay uses the *same Python implementation* as the producer and is **not
an independent semantics implementation or scientific certification**. This is
an experimental local result, not a signed PCS v0.6 package/receipt.

## Experimental v6: finite-universe proof-carrying falsification

The new independent CLI extends the v5 CSV-bound exact arithmetic checker to
**complete finite-universe claims**. For every assertion in a caller-supplied
`pcs-tabular-evidence-v5-research` manifest, it re-parses **every** record of the
submitted CSV and emits a single generated Lean 4.28.0 obligation for the ordered
Boolean conjunction. On a false conjunction, the generated source also proves
that the **first failing record** makes the predicate false. A separate Lean
example checks the list length. All clauses use the v3 typed rational AST and
unit-aware interpreter; no LLM output or arbitrary Lean proof is accepted.

The `Option Bool` aggregator makes computation errors (`none`) distinct from
false assertions (`some false`): a malformed or undefined expression must **not**
become a certified counterexample. Full-source and strict manifest parsing occur
**before any Lean call**. Each receipt carries the source and manifest SHA-256,
ordered row spans and row hashes, exact AST digests, the generated Lean source,
and proof-status details. A first-failing row has cell-level anchors. As with v5,
this is **not** a scientific validity decision or PCS v0.6 certificate.

```bash
# Without Lean 4.28.0, this produces a receipt with KERNEL_UNAVAILABLE and exits 2.
python -m research.llm_claim_harness_v1.finite_universe \
  --source research/llm_claim_harness_v1/fixtures/table_data.csv \
  --table-spec research/llm_claim_harness_v1/fixtures/table_spec.json \
  --out /tmp/pcs-finite-universe.json

# Re-parse source + template and invoke fresh Lean before comparing all receipt fields.
python -m research.llm_claim_harness_v1.finite_universe \
  --source research/llm_claim_harness_v1/fixtures/table_data.csv \
  --table-spec research/llm_claim_harness_v1/fixtures/table_spec.json \
  --receipt /tmp/pcs-finite-universe.json \
  --out /tmp/pcs-finite-replay.json
```

The sample contains two rows. `force_check` is false on the second row, while
`positive_mass` is true on both. This deliberately demonstrates **falsification**,
not a guarantee that the physical measurements are genuine. A valid v6 proof
means *all rows in the submitted byte-exact file*, not all observations that
exist in the world. An adversary could submit a shortened CSV and obtain a true
finite proposition about that **different CSV**. If a trusted reviewer has
retained a SHA-256 of the complete intended dataset, pass it with
`--expected-data-sha256 <64-lowercase-hex>` to reject replacement/subsetting.
Passing a self-chosen hash does not establish authenticity, custody or completeness.
The replay command must use the same pin, if one was supplied initially.

A positive mathematical proof still does not establish the unit declarations,
measurement methodology, model assumptions, selection criteria, or relationship
of the chosen equation to a researcher's prose. The v6 code reuses the same
Python CSV parser and typed compiler on receipt replay; this is fresh checking,
not an independent compiler-correctness proof or a new trust root. The finite
subset remains limited to **1–16 rows**, 1–4 assertions, and the original v5
strict numeric CSV grammar. Benchmarks on adversarial or blinded scientific
projects and live LLM inference have **not** been run. Novel scientific or
algorithmic superiority is not claimed from synthetic fixture passes.

## Experimental v7: independent source-byte-to-decimal Lean checker

The v6 finite-universe result still relies on Python to translate CSV numeric
lexemes to rational constants. The new `byte_bridge.py` provides a **second
implementation of that translation in Lean**, executed on the actual ASCII byte
array embedded into the generated proof artifact. Lean checks (1) exact newline
segmentation of the full embedded dataset and (2) that independently parsing
**every selected cell's original byte slice** yields the purported rational.
Only generated constants and the fixed in-module Lean decoder are used. The
hosted smoke test includes an **executed negative control**: modifying the
expected rational in the generated source must cause Lean to reject the proof.

```bash
python -m research.llm_claim_harness_v1.byte_bridge \
  --source research/llm_claim_harness_v1/fixtures/table_data.csv \
  --table-spec research/llm_claim_harness_v1/fixtures/table_spec.json \
  --out /tmp/pcs-byte-bridge.json

python -m research.llm_claim_harness_v1.byte_bridge \
  --source research/llm_claim_harness_v1/fixtures/table_data.csv \
  --table-spec research/llm_claim_harness_v1/fixtures/table_spec.json \
  --receipt /tmp/pcs-byte-bridge.json \
  --out /tmp/pcs-byte-replay.json
```

This is separate from the v6 all-row proof and must not be confused with it.
**Both checks** are needed for the stronger *experimental* data-to-arithmetic
argument. The byte bridge is restricted to source files at most **512 bytes** and
at most **32 numeric cells**, and rejects larger files without producing partial
verified results. The fixed Lean decoder is independent of Python `Fraction`,
but Python still chooses the cell offsets/expected values and embeds the input
bytes into the proof source. Independent assurance that those embedded bytes
match a document received by a reviewer requires direct comparison or a trusted
hash/custody process; it is not guaranteed by the checker itself. Nor does this
certify CSV completeness relative to an unpublished study, physical units,
source interpretation, causal inference or empirical validity.

This addition is a narrowed trust assumption and a useful architectural advance,
not proof of novel algorithmic superiority or general scientific understanding.

## v8: One-source integrated CSV certificate (experimental)

`csv_integrated_v8.py` adds a **single Lean 4.28.0 proof script** that reads a
strict CSV from exact embedded ASCII bytes, splits **every** source line and
column, checks the header, complete row count, per-record column width and
numeric parse of every cell, and evaluates all typed all-row predicates over
those **Lean-decoded** numbers with their manifest-supplied rational SI scales.
An incorrect universal claim gets a checked counterexample at its first failing
row. No previously Python-computed CSV cell magnitude is used as a binding leaf
in the generated Lean arithmetic. This composes the independent byte checks and
finite-universe arithmetic in a *single* proof obligation rather than trusting
Python to connect two separate certificates.

From the repository root, with Lean 4.28.0 on `PATH`:

```bash
python -m research.llm_claim_harness_v1.csv_integrated_v8 \
  --source research/llm_claim_harness_v1/fixtures/table_data.csv \
  --table-spec research/llm_claim_harness_v1/fixtures/table_spec.json \
  --out /tmp/pcs-v8-integrated-receipt.json
```

Use `--expected-data-sha256` and `--expected-manifest-sha256` with independently
retained hashes to reject cropped, reordered, substituted or edited input before
proof generation. These are **caller-supplied, unauthenticated** commitments;
they do not establish original dataset completeness. To check a delivered receipt
again, add `--receipt /path/to/original-receipt.json` with the **same** pins.
Fresh replay regenerates the whole Lean script and requires an exact canonical
receipt match and successful kernel re-execution.

**Boundaries:** this supports at most 512 source bytes, 32 numeric cells,
16 records, and the reviewed CSV template's narrow rational typed grammar.
The entire received CSV is the finite universe—not all observations in a real
research study. CSV custody, template scientific meaning, correctness of the
Python-to-Lean generator, approved unit semantics, source licensing, and
original sample completeness remain unproved. A verified equation is not
scientific validation. No LLM output is executed, no API key is required, and
this script does not modify PCS v0.6 production authority. A mock Lean checker
in offline tests is **not** proof evidence; rely on hosted Lean CI or your own
pinned Lean 4.28.0 run to establish actual kernel checking.

The hosted smoke check runs three intentional negative controls against the
**actual Lean executable**: forged universal success, forged header, and forged
row count must all fail. This is a falsification exercise, not a general proof
of the generator or CSV parser's semantic refinement to a standard RFC.

## V9 experimental: exact least-squares regression over source bytes

`ols_integrated_v9.py` extends the v8 single-script source-to-Lean construction
from rowwise equations to an **ordinary least squares affine regression**. It
parses every submitted strict CSV row inside Lean, reuses the bounded decimal
and header/shape checkers, applies manifest-declared rational unit scales, then
independently recomputes the exact fit `y = slope*x + intercept` and SSE from the
raw values. It proves or refutes three *reported exact values* and checks an
independent candidate fit equality. This is arithmetic reproducibility, not
proof of inferential/statistical assumptions, model adequacy or scientific truth.

Example from repository root:

```bash
python -m research.llm_claim_harness_v1.ols_integrated_v9 \
  --source research/llm_claim_harness_v1/fixtures/ols_data.csv \
  --table-spec research/llm_claim_harness_v1/fixtures/ols_table_spec.json \
  --ols-proposal research/llm_claim_harness_v1/fixtures/ols_proposal.json \
  --out /tmp/pcs-ols-v9-receipt.json
```

The demo uses four observations in centimetres and metres. The SI-unit fit
has slope `2`, intercept `1`, SSE `0`. The exact `pcs-ols-integrated-v9-research`
proposal (a separate untrusted artifact) specifies the x/y column identifiers
and three reported numerical strings. A dishonest reported slope generates a
Lean-checked **refutation** rather than being silently replaced by the fitted
slope. A singular design matrix (all x-values equal), unsupported data, unsafe
syntax, missing evidence, or a Lean failure must not create a positive receipt.

Limits: 2–8 observations; existing v8 512-byte CSV / 32-cell bounds; exact
ASCII decimal data; two distinct named columns from the reviewed table schema;
closed finite rational regression; exactly three reported scalar metrics;
no LLM-selected subset of records. Source/manifest/proposal SHA-256 commitments
can be pinned externally. Units and their physical interpretation remain from
reviewer-supplied manifest, and proof generation is not a verified compiler.

**Open trust/meaning boundaries:** external file custody, the identity of the
scientific study population, the fit method and variable roles, rounding and
measurement uncertainty, autocorrelation, homoscedasticity, statistical
significance, causal claims, and whether an LLM matched an original paper's
reported parameters to the right data. This research engine deliberately returns
`semantic_fidelity=UNREVIEWED` and `scientific_status=NOT_ASSESSED` even when Lean
checks every generated numeric obligation. PR #203's richer source semantics
remain unmerged; importing that branch or its reference labels here would risk
misstating evidence and contaminating a prospective evaluation.

Hosted research CI runs `check_live_lean.py`, including v9 positive controls,
recertification, a forged coefficient, and a changed-data SSE negative control.
Neither a fake test checker nor a model suggestion counts as kernel evidence.

### V9.1 source-report-note bridge (restricted author/reviewer artifact)

The optional `ols_note_v9.py` input is a separate, UTF-8/ASCII, **author-
or reviewer-controlled** `PCS-OLS-NOTE/1` claim artifact, requiring independent
review before anyone may rely on it as a faithful paper interpretation. Its exact eight-line grammar includes the SHA-256 of the whole
CSV and table manifest, x/y column names, and *source-authored* slope,
intercept and SSE literals. The parser rejects duplicate lines, reordered
fields, implicit claims, confidence intervals, approximate claims and any
other unsupported prose. Unlike an LLM-generated free-form interpretation,
this strict format can be re-parsed deterministically.

The **same Lean file** re-parses the original CSV, recomputes exact OLS, and
parses the note's numerical claims directly from original note bytes with
`pcsAsciiDecimal (pcsByteSlice ...)`. A model cannot silently substitute a
numeric literal in the final formal check. A changed note value yields a
Lean-checked refutation of that exact declared numeric result. The separate
Python note-to-dataset SHA agreement, x/y role interpretation and source
custody remain named external trust boundaries.

```bash
python -m research.llm_claim_harness_v1.ols_note_v9 \
  --source research/llm_claim_harness_v1/fixtures/ols_data.csv \
  --table-spec research/llm_claim_harness_v1/fixtures/ols_table_spec.json \
  --report-note research/llm_claim_harness_v1/fixtures/ols_report_note.txt \
  --out /tmp/pcs-note-v9-receipt.json
```

This is **not automatic interpretation of arbitrary research papers**. The
strict note is an intermediate, researcher/reviewer-authored object; a model
could propose draft note content for human checking, but a correct kernel proof
does not validate the original paper's meaning or authenticate the note author.
No general scientific-validity status or production PCS authority is granted.


## v10: source-bound all-deletions exact OLS sensitivity (experimental)

`ols_stability_v10.py` adds a **complete, finite leave-one-out regression** audit on
exact source CSV bytes. Every one-row omission is considered, with `3..8`
complete data records and exact rational arithmetic. A strict seven-line
`PCS-OLS-LOO/1` note commits to the CSV and manifest hashes, predictor and
response column names, and exact nonnegative tolerance bounds (SI slope and
intercept units). This note is **not** an authenticated scientific author claim.

The generated Lean script recomputes the full regression, **refits after every
single-row deletion**, reads both tolerance values directly from the note's
original bytes, checks that the enumerated fit and verdict lists have the
expected row count, and proves either the finite *all deletions within tolerance*
claim or its negation with a row-indexed counterexample. A degenerate deletion
fails closed rather than passing vacuously. No arbitrary input Lean or dynamic
execution of scientific source code is allowed. Exactly matching source notes
and verified certificates may be independently replayed.

```bash
python -m research.llm_claim_harness_v1.ols_stability_v10 \
  --source research/llm_claim_harness_v1/fixtures/ols_data.csv \
  --table-spec research/llm_claim_harness_v1/fixtures/ols_table_spec.json \
  --stability-note research/llm_claim_harness_v1/fixtures/ols_stability_note_v10.txt \
  --lean lean --out /tmp/pcs-loo-v10.json
```

**Limits:** This is sensitivity to deletion of one supplied row. It does not
certify global regression optimality as a universally quantified theorem,
external data completeness, correct statistical model choice, distributional
assumptions, sampling representativeness, outlier resistance to larger changes,
scientific interpretation, or any production PCS v0.6 authority. Truth of
formal arithmetic on an admitted note is separate from whether the original
research paper actually claimed or justified that tolerance.

## Experimental v11: source-bound response-error uncertainty corners

The standalone `ols_uncertainty_v11` research CLI checks whether a fixed-predictor
OLS line is stable under **every corner** of an independent symmetric error box
for the observed response values. Given `n` complete CSV rows (currently 3–6),
it checks the entire `2^n` response-endpoint ensemble, never a selected subset.
All decimals and unit conversions are exact rationals. A separate note pins the
complete CSV and manifest SHA-256 and supplies the `response_error_si`,
`max_slope_shift_si`, and `max_intercept_shift_si` declarations. These bounds
are interpreted in SI units; the source schema determines x/y unit conversion.

```bash
python -m research.llm_claim_harness_v1.ols_uncertainty_v11 \
  --source research/llm_claim_harness_v1/fixtures/ols_data.csv \
  --table-spec research/llm_claim_harness_v1/fixtures/ols_table_spec.json \
  --uncertainty-note research/llm_claim_harness_v1/fixtures/ols_uncertainty_note_v11.txt \
  --out /tmp/pcs-ols-v11-receipt.json --lean lean
```

A second invocation with `--receipt /tmp/pcs-ols-v11-receipt.json` rechecks
all proof obligations with Lean and rejects modified receipts. Use independently
retained `--expected-data-sha256`, `--expected-manifest-sha256`, and
`--expected-note-sha256` pins when authenticity of input identity matters.

The kernel's generated script parses original CSV cells, constructs its OLS
fit, decodes the three bounds from original note bytes, generates all response
corners, and checks every corner against the two tolerances. It verifies a
**finite-corner statement only**. A source change, forged bound, omitted corner,
false robust verdict or bad fit must be rejected or refuted. The research
receipt separately includes an exact, externally calculated affine envelope:
with fixed predictor values, OLS coefficients are affine functions of the
responses, and the continuous-box extrema occur at corners. The generic
continuous-box theorem is **not yet Lean-proved in this module**, so the receipt
marks it `EXTERNAL_AFFINE_DERIVATION_NOT_KERNEL_PROVED` and does not promote
continuous robustness to formal authority. The source error bound itself,
measurement noise distribution, independence of errors, model choice, source
completeness, outlier effects and empirical scientific validity are not certified.

This is a bounded uncertainty verification **research capability**, not evidence
of a novel theorem or an independently demonstrated scientific breakthrough.
No provider output, selected corner, missing Lean check, or LLM agreement can
promote a scientific-validity status. Production PCS v0.6 is untouched.

## Experimental v12: continuous-real box-bound theorem

`ols_continuous_v12.py` extends the v11 finite response-uncertainty-corner
analysis with a **universally quantified Mathlib theorem** over arbitrary real
response deviations, no grid discretization. Given fixed weights `w`, arbitrary
real original responses `y` and deviations `d` satisfying `∀i, |d_i| ≤ ε`,
the formal goal is

`|Σ_i w_i (y_i + d_i) - Σ_i w_i y_i| ≤ ε Σ_i |w_i|`.

The generator brings the v11 byte-decoded CSV, manifest, and original note
into **the same Mathlib proof file**, and adds a Lean-side reconstruction of
rational slope design weights with a checked equality to the proposed weights.
The resulting all-real slope/intercept affine functionals use these numerical
weights, with the intercept weights generated by the corresponding exact OLS
formula. For the four-row fixture, the bounds are exactly `0.08` and `0.14`
for response perturbations of `±0.10` (all in the specified SI units).

**Critical remaining obligation:** the general identification of the source-
computed OLS estimator with both continuous real affine functionals is **not
kernel-proved in v12**. The weighted-sum theorem is a genuine general theorem
conditional on the specified weights; it is not an end-to-end certificate of
arbitrary floating-point regressions or scientific interpretation. Statistical
validity, units chosen by researchers, semantic fidelity, original dataset
custody, and appropriateness of uncertainty assumptions remain unverified.

The dedicated `experimental-continuous-response-bound` hosted GitHub Actions
job checks the Mathlib theorem, the source-derived numerical anchors, two
forged-case rejection controls, and a fresh kernel replay. Local testing without
pinned Lean and Mathlib correctly returns `KERNEL_UNAVAILABLE`.

Run from the repository root **after installing pinned Lean/Mathlib**:

```bash
source scripts/activate_lean_428.sh
lake exe cache get
python -m research.llm_claim_harness_v1.check_continuous_lean_v12
```

Or emit an experimental receipt (fails closed if real kernel is unavailable):

```bash
python -m research.llm_claim_harness_v1.ols_continuous_v12 \
  --source research/llm_claim_harness_v1/fixtures/ols_data.csv \
  --table-spec research/llm_claim_harness_v1/fixtures/ols_table_spec.json \
  --uncertainty-note research/llm_claim_harness_v1/fixtures/ols_uncertainty_note_v11.txt \
  --out /tmp/pcs-v12-continuous-receipt.json
```

The v11 finite-corner research workflow is preserved. Neither workflow changes
PCS v0.6 production verification or makes a claim of general scientific
verification. The finite 16-corner experiment and the continuous theorem are
related but distinct assurance claims; neither can be silently promoted into
scientific certification.

### Generic OLS slope algebra (experimental v12 continuation)

The Mathlib script also contains a **general proof obligation** identifying
the standard real-number closed-form OLS slope with the affine weighted sum for
all finite fixed-design vectors, followed by an all-real response perturbation
bound expressed in terms of that OLS coefficient. This is not yet the same as
a kernel-checked refinement from the source-decoded CSV into a particular
real-valued design vector; nor does it identify the OLS intercept with its
source-bound affine weights. Both are tracked separately. Do not report those
connections as proved until the hosted Mathlib job passes an explicit proof.

### Source-specific OLS slope instantiation (experimental, kernel required)

The source-specific extension now constructs the real-valued predictor vector
from all CSV rows, checks the exact rational `(x, y)` pairs from original bytes
in Lean, checks the real slope-weight function against the source-derived rational
weights, and instantiates the generic real OLS perturbation theorem for this
actual design. This is a stronger *mathematical* connection, but remains invalid
until the corresponding hosted Mathlib job succeeds; intercept refinement and
scientific/experimental meaning remain explicitly outside its proved scope.
