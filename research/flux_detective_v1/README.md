# Flux Detective — a playable exact-model audit

Six small puzzles turn the PR166 counterexample lesson into a usable research
exercise: preserving mass, bounds and decreasing quadratic energy does not establish
that a recorded trajectory obeys its declared update rule. Find the one correct
trace among two plausible impostors, inspect exact residuals, then take either a
correct or incorrect trace to the existing Lean replay checker.

This is an opt-in, standalone static research interface, stacked on frozen PR166
`77250c708dbc5e74c2c4bc4745acc7ef217af87c`. Production PCS, the website, Cloudflare,
Aristotle modules, source gates, receipts and all predecessor files remain untouched.
No merge or deployment is part of this change.

## Play locally

From the repository root:

```sh
python -m http.server 8080 --bind 127.0.0.1 --directory research/flux_detective_v1
```

Open **http://127.0.0.1:8080/#seed=20261021**. There is no build step, runtime npm
dependency, API, account, analytics, storage, remote font or external script.
ES modules require HTTP rather than a `file:` URL. Keyboard buttons, screen-reader
table labels, live feedback and a narrow-screen layout are included. Three stars
per puzzle reward solving without a wrong choice or a hint. Scores are temporary;
there is no trusted competition or anti-cheating claim.

An unsigned 32-bit seed determines all six puzzles and candidate order. Share the
URL for the same campaign; zero and `4294967295` are supported. Different seeds
can produce the same models; this is not a claim of 2^32 distinct challenges.
The early cases use two and three cells, later cases include up to five cells and
three updates. Two decoys change only the last update, so inspecting only the
initial prefix fails on later cases.

## Replay an export with actual Lean

Use this checkout's usual pinned Lean4.28.0, Mathlib and Python dependencies:

```sh
source scripts/activate_lean_428.sh
lake exe cache get
python -m pip install --require-hashes -r requirements-build.lock -r requirements-dev.lock
python -m pip install --no-deps --no-build-isolation -e .
python -m research.flux_detective_v1.check /path/to/download.json /new/evidence-directory
python -m research.portable_transport_v2.replay verify /new/evidence-directory
```

Both commands use the unchanged PR165 fixed source-bound proof constructor and
Lean checker. Exit **0** means kernel support for the finite trace, **10** means
kernel refutation, **20** means refusal/unavailability. Argument errors have exit2.
Read the JSON status as well. Existing output directories are refused. Failed
checks can retain diagnostic evidence without establishing a verdict.

The browser exports a versioned JSON object containing the contract object and
the exact CSV text. There is deliberately no supplied proof or verification
verdict. The receiving bridge rejects oversized/non-UTF8/duplicate-key/nested
malformed JSON, extra authority/path/verifier fields, unsupported metadata and
invalid PCS contracts/CSV. It captures bytes, canonicalizes the contract through
existing PCS code and checks against the exact exported model. Seed/level/choice
are untrusted labels: editing a label cannot choose a verdict, and the bridge
does not authenticate a download as a genuine game-generated artifact.

The evidence directory contains the actual input bytes, regenerated Lean source,
fixed source copies, axiom inventories, process logs and hashes. A reviewer uses
a separately reviewed checkout and runs `verify` again. Self-consistent hashes
do not authenticate a producer; a stored `result.json` verdict is never accepted
as proof. Tests forge both its verdict fields and its inventory hash, then run
Lean again to check the original mathematical result.

## What is established, and where

| Boundary | Evidence and remaining trust |
| --- | --- |
| Browser arithmetic | Reduced BigInt rationals; canonical parser; exact comparisons; signed bounded arithmetic tests. No floating point is used for mathematical decisions. |
| Browser model vs Python | 1,224 exported cases from 68 fixed seeds, independently evaluated with Python Fraction and matrix products; 408 exact traces, 816 recurrence violations, all with conserved mass/bounds/decreasing energy. Bounded compatibility evidence, not a compiler or parser refinement theorem. |
| Exports vs Lean | The 18 default-campaign choices are independently replayed: six positive traces and twelve exact negative witnesses. Every result requires real Lean compilation and standard-axiom inventories. Missing tools fail the tests. |
| Replay convenience CLI | Positive and negative commands and exit codes tested with real Lean; fresh reviewer replay ignores deliberately forged stored verdicts. |
| Generic mathematical basis | PR165/166's existing theorems and assumptions are reused unchanged. This PR adds no generic Lean theorem. New game-instance proofs are kernel checked during tests/replay. |
| Scientific scope | Closed, synthetic, explicitly discrete rational diffusion only. No real-world data, continuum error guarantee, empirical validity, or recursive self-improvement result. |
| Security scope | Host/browser/JavaScript/Python/compiler/OS, reviewed checkout and pinned dependency objects remain trusted. Same-host Lean subprocesses do not establish an independent administrator or immutable root. Browser scores and generated data are untrusted. |

The generator uses small symmetric edge conductances and positive cell volumes.
The correct trace applies the declared update; decoys use twice or three times
the declared transfer in the final step. These small alternative steps remain
stable for the generated graphs, explaining why their aggregate summaries can
look good. The browser's `inspect` computes those summaries rather than assigning
them from a success label. The independent tests compare every energy, amount,
fault location, observed value, expected value and residual. No exhaustive claim
over all seeds is made.

## Tests and reproducibility

```sh
node --test research/flux_detective_v1/test_engine.mjs
npm ci --ignore-scripts --prefix research/flux_detective_v1
cd research/flux_detective_v1
npx --no-install playwright install --with-deps chromium
cd ../..
node --test research/flux_detective_v1/test_browser.mjs
python -m pytest -q research/flux_detective_v1/test_correspondence.py
python -m pytest -q research/portable_transport_v2/test_replay.py
python -m research.flux_detective_v1.preservation
python -m research.integration_v1.source_gate
```

Node24.19.0 and Python3.12.14 are used in the focused workflow. Playwright1.64.0
and its transitive package are lockfile pinned; only browser testing needs npm.
`PCS_CHROMIUM=/path/to/chromium` selects an existing test browser.
`PCS_FLUX_SCREENSHOTS=/new/path` retains screenshots.
`PCS_FLUX_EVIDENCE_DIR=/new/path` retains all 18 default-choice proof packages.

The new workflow runs eight engine tests, three real-browser tests, forty Python
tests and the inherited 24 hostile replay tests, plus source preservation and the
unchanged consolidated source gate. The mathematical compatibility test covers
68 preregistered seeds: 0, 1, 4294967295, 20261021, and 1000 through1063. These
1,224 exports are cases inside one test, not 1,224 independent pytest tests.
Actual run results and tested commit are reported in the PR, not inferred here.

## Next useful milestone

Before promoting this into a public research activity, evaluate whether people
learn the distinction on unseen models; engagement and learning have not been
measured. A later sandbox could let participants construct their own invariant-
preserving forgeries and submit exact witnesses for independent replay. A separate
formal milestone remains source-to-wire decoding correspondence; this interface
does not close that obligation or depend on unfinished Aristotle codec changes.
