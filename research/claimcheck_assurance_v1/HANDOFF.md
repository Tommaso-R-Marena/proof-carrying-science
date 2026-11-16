# Handoff: ClaimCheck assurance and qualification work, state on 2026-11-15

For the next implementer. Everything below was checked in this repository on the date above;
anything marked *reported* comes from an external service and was not reproduced.

## 1. Where things are

| Repository / branch | Draft PR | Contains |
| --- | --- | --- |
| core `tommaso-r-marena/festive-galileo-4a5m5k` | Tommaso-R-Marena/proof-carrying-science#212 | ClaimCheck v1 (frozen) and v1.1; prospective protocol draft 2; owner-decision register; adjudication plan; usability ethics note; admission proposal, census, dry run and audit |
| core `tommaso-r-marena/claimcheck-assurance-research` (stacked on the branch above) | Tommaso-R-Marena/proof-carrying-science#216 | this directory: Lean proofs, conformance tests, the runner finding and fix, the C codec and Aristotle record |
| site `tommaso-r-marena/festive-galileo-4a5m5k` | Tommaso-R-Marena/proof-carrying-science-site#149 | ClaimCheck page, its tests and evidence, governance proposals for three protected files |

Read first: `README.md` (this directory), `../claimcheck_v1_1/OWNER_DECISIONS.md`,
`../claimcheck_v1_1/prospective/AMENDMENTS_DRAFT_2.md`, `findings/RUNNER_TAIL_FORGERY.md`,
`c/ARISTOTLE_RESULTS.md`.

## 2. What is finished (kernel-checked, or run and passing)

* `formal/`: modules `SourceBinding`, `Authority`, `Selection`, `Header`, `Audit`. Build:
  `source scripts/activate_lean_428.sh && research/claimcheck_assurance_v1/formal/build.sh`. The
  axiom report (46 theorems) must equal `formal/AXIOMS.expected`.
* `conformance/`: `test_header_refinement.py` (proved decoder = C = Python on 5,755 inputs),
  `check_conformance.py` (Lean policy model = Python policy), `test_decoy_rule.py` (implemented decoy
  rule within the model), `ExportTables.lean` + `lean_tables.json`.
* `runner/`: `test_strict_tail.py` (the strict grammar of the installed runner; the forgery on the
  withdrawn runner kept in `findings/evidence/`). Since 2026-11-16 the grammar lives in one place,
  `parse_tail` of the installed runner `../claimcheck_v1_1/claimcheck_kernel_runner.py`; the
  prototype that was here was removed once installed.
* `c/`: `pcs_srcbind.c`, `test_srcbind.py`, Aristotle prompt, results and counterexample.
* `.github/workflows/pcs-claimcheck-assurance.yml` runs all of the above.

## 3. Open proof obligations (precise)

1. **Canonical grammar for the claims part.** The installed runner's `parse_tail` accepts only the generator's
   language, so no foreign definition can enter a proof file, but it is not canonical: a byte string
   of safe characters may be written `b "abc"` or `[97, 98, 99]`; a rational may be unreduced
   (`((2 : Rat) / 2)`) or `-0`. Both spellings denote the same claim, so this is not a soundness
   defect, but the replayer (byte-identical rebuild) and the runner then disagree on what is
   acceptable. Task: tighten the grammar to the generator's choices (`b "…"` exactly when the content
   matches `_SAFE_STRING` in `claimcheck_v1/lean.py`; reduced fractions with positive denominator;
   no `-0`), then in Lean: `renderTail : List Nat → List Claim → List Outcome → List Nat` following
   `lean.py::batch_tail`, `parseTail` following the tightened grammar, and prove
   `parseTail (renderTail d cs os) = some (d, cs, os)` (under the generator's preconditions) and
   `parseTail t = some (d, cs, os) → t = renderTail d cs os`. `Header.lean` is the template: its
   `decode_canon` / `decode_sound` pair is exactly this shape for the header.
2. **C decoder, memory safety and functional correctness with the non-aliasing precondition.**
   *Reported* by Aristotle as proved under that precondition but not recorded as a result; P1, P4, P5
   unresolved. Needs the owner's approval of more credits (decision E2), or the alternative of
   returning `1 + length` instead of writing through `m`, which removes the aliasing hazard.
3. **The verdict policy as verified code.** Today the Lean model and the Python policy agree by
   test. To make the decision logic itself verified: compile `Authority.core`/`outward` from Lean and
   have `policy._decide` call it with the findings Python computes; the conformance test then checks
   the bridge, not two implementations. Changes v1.1's code path: needs the owner's approval before
   the software freeze.
4. **Multiple supporting siblings.** `routes_block_le` bounds the decoy coincidence by
   `max 1 s · k` for `s` supporting reading sets. Bounding `s` (it is limited by strongly confirmed
   numbers in one sentence) would close the last gap of the selection analysis.

## 4. Engineering tasks that can run in parallel

| Task | Isolated in | Acceptance |
| --- | --- | --- |
| A. tighten the installed runner's `parse_tail` to canonical forms | core `../claimcheck_v1_1/claimcheck_kernel_runner.py` (and the site's copy) | the 84 committed obligation files accepted; non-canonical spellings of byte strings and rationals rejected; `test_strict_tail.py` and `test_header_refinement.py` pass |
| B. Lean renderer and parser for the claims part (obligation 1) | new `formal/ClaimCheckAssurance/Claims.lean` | kernel build passes; axiom report extended and still standard; a refinement test like `test_header_refinement.py` comparing the Lean parser with the installed runner's `parse_tail` on all committed files and mutations |
| C. prospective-evaluation plumbing on synthetic data only: screening record, adjudication form intake with sealing (SHA-256 and time before comparison), Cohen's κ, the D1 report | `../claimcheck_v1_1/prospective/` | tests on synthetic fixtures only; nothing reads a prospective paper; `test_score_draft2.py` still passes |
| D. **done 2026-11-16** (C3/D4 authorised for preparation and testing): the v1.1 runner and the site's copy replaced by the strict runner | core `d5a36975`, `2de4f872`; site `a6e8c9c` | the forgery is a must-reject case in the core offline and live suites and in the site's tests and browser journey; the site pins the new digest |
| E. ~~change the decoy rule~~: the owner decided A6 on 2026-11-16 to **retain** the rule and correct its wording (done in the ClaimCheck branch). Alternatives may be compared on development data only; the software to be frozen does not change without approval | `../claimcheck_v1_1/dev/` | any comparison is labelled exploratory and leaves `policy.py` unchanged |

## 5. Known failure modes

* The Lean interpreter overflows its stack on long lists: run `lean --run` with an unlimited stack
  (`test_header_refinement.py` does).
* Well-founded recursion does not reduce in the kernel; definitions that `decide` must evaluate need
  structural recursion (see `decStr`, which uses fuel and proves its equation once).
* ClaimCheck obligations on large tables exhaust memory or hit a recursion limit (medians, minima,
  maxima above about 400 rows): a failed kernel run is `UNKNOWN`, never a result.
* Aristotle accepts no hard credit cap through this interface; a limit written in the prompt was not
  respected (92 billed against 40 asked). A run must be watched by someone able to cancel it.
* `source-policy`, `verified-public-integration` (core) and four site checks are red by design of
  the protected gates until the owner decides C1, D1 and D2. Do not try to turn them green.

## 6. Do not

* merge or deploy any of the three PRs; push any branch other than the two named above; create or
  push a tag (in particular the retained-source tags the admission needs);
* edit a protected file (`research/integration_v2/**`, `scripts/check_reconciled_prs.py`,
  `docs/integration/2026-11-05/**`, the site's `scripts/verify_browser_ui_sources.mjs`,
  `scripts/check_reconciled_prs.py`, `package.json`), a frozen v1 file (`freeze check` must pass), a
  benchmark, a bundle, or a recorded result;
* sample, fetch, read, label or score any prospective paper before the owner approves the protocol;
* contact adjudicators or participants; make a paid model call; start an Aristotle run;
* send unpublished material or credentials to any external service;
* describe a theorem about a Lean model as a property of the Python, JavaScript or C code. Say what
  the test shows and that it is a test.

## 7. Keeping the kernel's authority

Every claimed theorem is checked by the Lean 4.28.0 kernel through `build.sh`; `#print axioms` for it
is in `Audit.lean`; the report may contain only `propext`, `Classical.choice`, `Quot.sound`. No
`sorry`, `native_decide`, new `axiom`, `implemented_by` or `extern` in proof modules. The assumption
that an accepted kernel equation is true (`KernelSound`) stays a hypothesis of the theorems that need
it. Each new theorem needs a negative control showing its hypotheses are needed, and a statement of
what it does not cover.
