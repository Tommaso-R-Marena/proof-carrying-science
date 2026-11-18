# Security-review package: the ClaimCheck kernel runner and local receipts (C3/D4)

**Status:** prepared for the owner's final security review. The corrected runner is implemented and
tested on the draft branches; nothing is merged or deployed, and no protected file is changed by
this package. "Proved" below means a Lean theorem checked by the kernel; "tested" means the named
tests pass; "reviewed" means read and probed by an independent reviewer (an AI subagent working
from fresh read-only copies, not a person).

## 1. What a runner receipt is, and what it is not

The ClaimCheck page writes a Lean proof file for the user's data and claim. The stand-alone runner
`claimcheck_kernel_runner.py` runs the real Lean 4.28.0 kernel on that file on the user's own machine
and writes a receipt (`pcs-claimcheck-kernel-run-v2`). A receipt is **self-reported**: anyone can
write one by hand. It carries no signature and no authority. The page shows a loaded receipt only
under the label "REPORTED BY YOUR LOCAL RUN · NOT VERIFIED BY THIS PAGE", only when it is about the
exact file the page generated, and never as a statement that a paper or a sentence is correct. A
receipt, even a genuine one, establishes at most that the stated mathematical obligation about the
embedded bytes holds; not that the sentence means it, that its settings are the right ones, or that
the bytes are the authors' data.

## 2. Digests

| What | SHA-256 | Where |
| --- | --- | --- |
| withdrawn runner (schema v1) | `8d9e07b4ac4b0abed13c9e750cbca113f1db26d82f3709579a7aafa7401f713f` | core history at `37915a9e`; kept byte for byte as evidence on the research branch (`findings/record/claimcheck_kernel_runner_v1.withdrawn`) |
| corrected runner of 2026-11-16 (superseded) | `459155f30329462ee598e7327c676b5826c4954384064084506323a874f1f158` | core `39ce953c` |
| **current runner** | `831bbababd2f48e5b9f62fa33433fe7edfbc8ee1f2271e3e7700b883745f75e9` | core `research/claimcheck_v1_1/claimcheck_kernel_runner.py` (commit `52b5e182`); the site serves the byte-identical copy `public/claim-check/claimcheck_kernel_runner.py` (site commit `10b5b2a`), and its catalog pins this digest |
| reviewed checker `ClaimCheck.lean` | `35c83b283b18f50c3fa9d1bb3f42ec0beca1d6a7458d14ebf7180d9927b9edf9` | compiled into the runner; pinned by the catalog and the page |

The exact source changes are in [`security/runner-v1-to-v2-2026-11-16.diff`](security/runner-v1-to-v2-2026-11-16.diff)
(the correction, 212 lines) and [`security/runner-v2-hardening-2026-11-17.diff`](security/runner-v2-hardening-2026-11-17.diff)
(the hardening, 395 lines).

## 3. The original forgery and its correction (2026-11-15/16)

**Defect.** The withdrawn runner checked the generated part of a proof file only for a few forbidden
words. A hand-written file that defined its own `run` on a decoy type and proved the expected
equation by `rfl` passed the Lean kernel, and the runner reported "MATCHES", although the theorem
said nothing about the reviewed checker. Plain Lean accepts that file too; the defect was in what
the runner concluded from Lean's acceptance.

**Correction.** The generated part must be in the canonical form of the generator's grammar: one
data numeral, claim records built from literals only, one batch theorem, one fixed-form theorem per
claim proved from the batch theorem, one spelling per value. Anything else (another definition, a
macro, a comment, an option, another proof term, another outcome, trailing text) is refused before
Lean is started.

**Evidence.**

| Claim | Kind | Where |
| --- | --- | --- |
| the forgery reproduces: plain Lean accepts it, the withdrawn runner reports a match | tested with the real kernel | research branch `runner/test_strict_tail.py`; records `findings/record/forgery_reproduction.json` (runner of 2026-11-16) and `forgery_reproduction_runner_831bbaba.json` (current runner) |
| the current runner refuses the forgery before Lean is asked anything | tested (stand-in `lean` records that it was never started) and with the real kernel | `tests/test_runner_strict.py`, `check_live_v11.py` |
| every genuine proof file is accepted: all 84 committed obligation files parse; a genuine file passes with the real kernel | tested | `tests/test_runner_strict.py`, `check_live_v11.py`, `forgery_reproduction_runner_831bbaba.json` |
| 16 forgery classes and the 14 negative controls are refused; 1,551 of 1,569 single-character edits of a genuine file are refused (the rest are canonical files about other values) | tested | `runner_negative_controls.py`, `test_strict_tail.py` |
| the canonical language is exactly the set of renderings of valid values; a text is determined by its meaning in the checker; the claim theorems say exactly what the batch theorem says | **proved** in Lean (`Claims.lean`: `parseTail_renderTail`, `parseTail_sound`, `parseTail_iff`, `renderTail_injective`, `same_meaning_same_text`, `batch_iff_claims`), axioms `propext`, `Classical.choice`, `Quot.sound` only | research branch `formal/` |
| the runner's Python parser computes the proved Lean parser | **tested, not proved**: 10,720 vectors, 0 disagreements (after the hardening) | research branch `conformance/test_claims_refinement.py` |

## 4. Independent security review (2026-11-17) and what was done

Method: fresh read-only clones of the three branches, the real Lean 4.28.0, attempts to make the
runner accept a theorem not about the reviewed `run`, to make it report other data than Lean
checked, and to make the page show a misleading report. Reproduction scripts and outputs were kept
in the session's scratch space; every finding below was reproduced again before it was fixed.

**Held (no bypass found):** shadowed `run`, decoy types, macros, namespaces, options, comments,
extra definitions and imports are refused before Lean; Lean syntax inside strings is inert; 30
encoding tricks (BOM, CRLF, zero-width and look-alike characters, non-ASCII digits, uppercase hex,
invalid UTF-8, a repeated marker, ...) are refused; parsing is linear up to 35 MB; axiom-report
spoofing, data other than reported, batch/claim mismatches, more than 256 claims or 65,536 data
bytes, and killed or timed-out Lean are all refused; the page refuses receipts about another file,
other data, another checker, v1 receipts and reordered theorems.

| # | Finding | Severity | Status |
| --- | --- | --- | --- |
| 1 | An accepted receipt did not say what was proved, and the grammar admits claim settings the page never writes (other missing-value tokens, any positive scale, a vacuous reported value such as `0e400`). Reproduced: the same data and printed number gave a kernel-checked "MATCHES" or "DOES NOT MATCH" depending on such settings. The theorems were still about the reviewed `run` | medium | **fixed in the runner** (`52b5e182`): each theorem in the receipt carries its `statement` (column, filter, statistic, missing-value tokens, scale, reported value) and `settings_the_page_never_writes`; `all_settings_as_the_page_writes` summarises; the KERNEL-CHECKED line names the settings and flags them. The grammar is unchanged (it remains the proved language); settings are flagged, not refused, because the core pipeline may legitimately take missing-value tokens from a dataset manifest. Wording corrected in the runner, README, REPORT and the site catalog. Live: with a scale the page never writes, the kernel accepts exactly one of the two verdicts and the receipt flags the scale |
| 2 | How `lean` was found: `shutil.which` searches the current directory first on Windows, and an empty PATH entry does so on POSIX; a `lean` planted beside a download ran for the version check and its banner reached an accepted receipt (reproduced on POSIX). A relative `--lean` crashed | medium | **fixed** (`52b5e182`): `--lean` is made absolute once; otherwise only absolute PATH entries are searched (`lean.exe` on Windows); a `lean` in the current directory or next to the proof file is refused unless given explicitly; one absolute path and one reduced environment for both calls; the receipt records the executable and its SHA-256. Tests: planted `lean` never runs; `lean` next to the proof refused; relative `--lean` used for both calls. The Windows path is reasoned from documented behaviour, not run here |
| 3 | The page kept showing a previous local report, preview and outcome after another data file was opened; a download could mix new data with old outcomes | medium | site page: see section 6 |
| 4 | Text from a receipt (Lean banner, time, refusal reason) was shown inside the page's own sentences; direction-changing characters rendered | low | site page: see section 6. The runner now prints its receipt as ASCII and neutralises control and format characters in the file name |
| 5 | The page's receipt gate ignored fields a genuine receipt always gets right (per-theorem `kernel_accepted`, axioms, `authority`, exact outcome, checker digest present) and did not check the fetched checker against its pin | low | site page: see section 6 |
| 6 | A numeral over 4,300 digits crashed the runner (Python's `int()` limit): no report, stale `--out` left; a non-UTF-8 file name crashed with `--out` | low | **fixed** (`52b5e182`): any runner error is a refusal with a report; number literals over 1,000 digits are refused as a resource limit (a Python-only cap, like the existing caps; no disagreement with the proved parser on the 10,720 vectors); `--out` is replaced atomically; file names neutralised |
| 7 | Lean runs with no memory limit: a file at the size cap peaked at 7.4 GB; a genuine 33 KB file needs 3.2 GB | low | **mitigated**: `--max-memory-mb` (POSIX, `RLIMIT_AS`; live: 256 MiB refused, 2 and 8 GiB accept a genuine file); memory needs documented. Not a default, because a default low enough to matter would refuse genuine large files |
| I1 | `--checker-sha256` accepted any digest and the receipt still spoke of "the reviewed checker" | info | **fixed**: `checker_pin_overridden` recorded, and the meaning text says the checker was not reviewed; the page refuses such a receipt |
| I2 | The grammar accepts more than the generator writes (non-UTF-8 byte lists, square-root sign 0 with a non-zero radicand, non-positive scale, non-decimal reported values, the outcome `sourceNotWellFormed`) | info | documented; the settings that can force a verdict are flagged (finding 1). Narrowing the grammar would also need the Lean model changed, so it is not done now |
| I3 | The page did not show the runner's digest | info | site page: see section 6 |
| I4 | The receipt was printed with non-ASCII characters raw | info | **fixed**: ASCII output |

## 5. A second gap, found by the conformance work: binding the claim to the sentence

The independent replayers re-derive each proof obligation from the receipt's claim, and the v1
replay binds the printed literal to the source text, but nothing tied the claim to that literal or
its variants to the claim's statistic. Three resealed forgeries replayed successfully, with the real
kernel re-checking both obligation files: a claim whose reported value was changed to the file's
mean; a variant that checks the median for a claim about the mean; a dropped standard-deviation
convention. The kernel cannot catch these: the remaining theorem is true, about another statement.

**Fixed in the v1.1 replayer** (`1d2f80ef`): the claim's reported value must equal the printed
literal whenever the quote check found it, and the checked variants must be exactly those the claim's
statistic requires (both standard-deviation conventions unless the manifest declares one). All 302
committed receipts satisfy both rules (0 violations); the live check still replays genuine bundles.
The three tests now assert refusal (`tests/test_binding_offline.py`, 15 tests). **Not fixed in the
frozen v1 replayer** (`FREEZE.json` pins it): on its own it still accepts these bundles, and it must
not be used alone to establish the integrity of a bundle from an untrusted source
(`research/claimcheck_v1/LEGACY_REPLAY_WARNING.md`, a new file; no frozen file changed). Safe paths:
the v1.1 replayer for v1.1 bundles, and `research/claimcheck_v1_1/replay_v1_bundle_checked.py` for v1
bundles, which runs the frozen replayer unchanged and adds the binding and result-consistency checks.
The six committed held-out bundles pass it (302 receipts, no problem; bundle 08 also with the real
kernel, now in CI); the three forgeries are refused by it while the frozen replayer alone accepts them.

## 5a. The outward verdict followed a mutable field (closed 2026-11-17)

`policy._decide` chose the match or mismatch rules by the receipt's `result` field and checked a
decided verdict only against that field (with `assert`, which `python -O` removes). A receipt whose
`result` contradicted its kernel-checked variants could therefore be confirmed or flagged, and could
corroborate another number. **Fixed** (`5a18afd7`): `policy.established_status` recomputes the status
from the variants as the pipeline builds it and requires `result`, `q1.status`, `q1.conditional` and
`reason` to agree; `policy.binding_problem` applies the replay's binding checks; an inconsistent receipt
decides nothing and corroborates nothing; the decided-verdict check is no longer an `assert`. All 1,590
committed receipts are consistent and the site catalog re-exports byte-identical. Tests:
`tests/test_decide_guard.py`, including all 240 combinations of the summary fields. On the research
branch the conformance check now asserts, with the real guard, that a receipt whose result contradicts
its status decides nothing (it was recorded, not asserted, before), and that the guard accepts every
receipt the pipeline can write (all 84 status patterns). Out of scope by design: a consistent lie in
the kernel record itself, which only re-running the kernel detects (the replay does).

## 6. The website's receipt rule

What the page must enforce (requirements for decision D4): accept only schema
`pcs-claimcheck-kernel-run-v2` and refuse the withdrawn v1 schema; show a report only if it is about
the exact proof file, data bytes and pinned checker of the current check, with every theorem
kernel-accepted, standard axioms only, outcomes exactly the page's, the research authority value, no
checker override and only page settings; clear any report when the inputs change; never display
free text from a receipt; label every shown report as reported by the user's local run and not
verified by the page; never present it as scientific correctness.

Implementation and evidence: see the site's `docs/governance/CLAIMCHECK_PROPOSALS.md`, section 4.

## 7. Assumptions and implementation-level limitations that remain

* **Trusted:** the Lean 4.28.0 binary and its elaborator's reading of numerals and literals; the
  runner records which executable ran and its digest but cannot verify that it is a genuine Lean
  (with elan, the digest is that of elan's shim); the user's Python 3.9+ and operating system.
* **Tested, not proved:** that the runner's Python parser is the proved Lean parser; that the
  Python verdict policy is the Lean model (exhaustive on the model's finite domain, see the research
  branch `conformance/CORRESPONDENCE.md`).
* Settings the page never writes are flagged, not refused. A receipt with flags is still a true
  statement about its settings; it is the reader's job to read them, and the page refuses them.
* `--max-memory-mb` is opt-in and POSIX-only; on Windows Lean runs without a memory limit.
* The Windows lookup rule (only `lean.exe` in absolute PATH entries, never the current or proof
  directory) is reasoned from documented behaviour and was not executed on Windows.
* A receipt is not a signature: the page can check that a receipt is consistent with its own file,
  not that a kernel actually ran. Only running the runner (or `lean`) yourself establishes that.
* The frozen v1 replayer keeps the claim-binding gap of section 5; use it only through
  `replay_v1_bundle_checked.py` for bundles from untrusted sources.
* The policy layer checks the internal consistency of a receipt, not the truth of its kernel record;
  that is the replay's job (it re-runs the kernel).
