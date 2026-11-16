# Finding: the stand-alone kernel runner accepts a forged proof file

**Severity: integrity of one research tool. Found 2026-11-14 while specifying binding theorems.
Affected `research/claimcheck_v1_1/claimcheck_kernel_runner.py` (receipt schema v1, SHA-256
`8d9e07b4…`) and its copy served by the website draft (`public/claim-check/claimcheck_kernel_runner.py`).
Neither was deployed or admitted.**

**Status: corrected on the draft branches, 2026-11-16** (owner decisions C3 and D4, authorised for
preparation and testing; not merged, not deployed). Core: commits `d5a36975` and `2de4f872` on
`tommaso-r-marena/festive-galileo-4a5m5k` install the strict runner (receipt schema v2, SHA-256
`fe974a9f…`). Site: commit `a6e8c9c` on the site branch serves it, pins its digest, and refuses v1
receipts. The withdrawn runner is kept byte for byte as evidence in
[`evidence/`](evidence/README.md); it is not a verification path.

## What is wrong

A ClaimCheck proof file is `CHECKER + MARKER + TAIL`. The runner checks that `CHECKER` has the
reviewed digest, that `TAIL` contains none of eight forbidden words, extracts the data numeral and
the theorem statements from `TAIL` with regular expressions, runs Lean, and reports what the
*text* of each theorem says.

`TAIL` is Lean source. Nothing requires it to be what the generator writes. A hand-written tail can
declare its own function called `run` on its own type, state `theorem pcs_claim_0 : run pcs_src
pcs_c0 = .checked .consistent …`, and prove it by `rfl`. Lean resolves the overloaded name `run` to
the only candidate that type-checks, the forged one. The kernel accepts the file, no forbidden word
occurs, the regular expressions match, and the runner prints

    KERNEL-CHECKED  pcs_claim_0: the printed number MATCHES the file under this statement

with `accepted: true` and the digest of the real data. The theorem is true and says nothing about
the checker.

## Reproduce

    PCS_LEAN=/path/to/lean-4.28.0/bin/lean python3 research/claimcheck_assurance_v1/runner/test_strict_tail.py

On the preserved withdrawn runner, `with_lean.withdrawn_runner_accepts_the_forged_file` is `true`;
plain Lean accepts the forged file too. The forged tail is
[`evidence/forged_tail.lean.txt`](evidence/forged_tail.lean.txt); the recorded output is
[`evidence/forgery_reproduction.json`](evidence/forgery_reproduction.json).

## Who is affected

| Path | Affected | Why |
| --- | --- | --- |
| v1 pipeline, v1.1 `verify` | no | they write the tail themselves and never read one |
| independent replayers (v1 and v1.1) | no | they rebuild the proof file from the receipt and compare byte for byte |
| web page, "open kernel-run.json" | no for display | it shows a report only if `proof_file_sha256` equals the file it built itself |
| **runner on a proof file from someone else** | **yes** | the report describes a theorem that is not about the checker |
| a person who only runs `lean file.lean` and reads the exit status | yes | same reason |

All results recorded so far came from files the pipeline generated; none is in doubt. The exposure
is the documented use "anyone can run the runner on the proof file".

## Why the existing tests missed it

`check_live_v11` tested a forged *outcome* in an otherwise generated tail. Lean rejects that. It did
not test a tail that is not of the generated form. The blacklist of words was the wrong kind of
check: the property needed is "the tail is exactly a generated tail", which is a whitelist.

## Correction (installed 2026-11-16)

`parse_tail` in the installed runner accepts exactly the language of the generator
(`claimcheck_v1/lean.py::batch_tail`): the fixed preamble, one canonical data numeral of at most
65,536 bytes, claim records made of literals only, the batch theorem, one fixed-form theorem per
claim, and nothing after it. Anything else is refused before Lean is started. Receipts (schema v2)
say what a pass establishes (the supplied mathematical obligation) and what it does not (that the
obligation represents a paper, or that the bytes are the authors' data). The prototype prepared here
(`runner/strict_tail.py`, `runner/claimcheck_kernel_runner_v2.py`, `runner/build_runner_v2.py`) was
removed once installed, so that only one copy of the grammar exists; it remains in the history at
`a09d9ab9`.

Evidence, all in the suites CI runs:

* `runner/test_strict_tail.py` (this branch): all 84 committed obligation files are accepted; 16
  hand-crafted tails are rejected, including the shadowed `run`, a namespace wrapper, a macro, an
  altered proof term, text after the last theorem and non-canonical numerals; 1,551 of 1,569
  single-character edits of a canonical tail are rejected and the other 18 are still canonical
  tails with a different literal; with the real kernel, plain Lean and the withdrawn runner accept
  the forged file, the installed runner refuses it without asking Lean anything, and accepts a
  genuine file.
* `research/claimcheck_v1_1/tests/test_runner_strict.py` (core offline suite): the reported forgery
  and 13 alterations of genuine files are refused before a stand-in `lean` is started.
* `research/claimcheck_v1_1/check_live_v11.py` (core live suite, real kernel): the forgery is refused
  and Lean is not started for it.
* Site: `tests/claim-check-page.test.mjs` runs the served runner on a page-built file (reaches
  Lean) and on the forgery (refused, Lean never started); `scripts/browser_claim_check.cjs` repeats
  it with the real kernel and shows a v1 receipt refused by the page.

Since core `39ce953c` the grammar is canonical: one spelling per value, the generator's. The
language it should accept is proved in Lean to be exactly the renderings of valid values
(`../formal/ClaimCheckAssurance/Claims.lean`, `parseTail_iff`); the Python grammar agrees with the
proved Lean parser on 7,248 inputs (`../conformance/test_claims_refinement.py`) and its header part
with the proved header decoder and the C decoder on 5,755 (`../conformance/test_header_refinement.py`).
These agreements are tests, not proofs.

## What remains for the owner

1. Review the corrected runner and its tests (core and site PRs, both drafts).
2. Results recorded before the correction stand: they came from files the pipeline generated.
