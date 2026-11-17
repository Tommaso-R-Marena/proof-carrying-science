# Aristotle feasibility run on `pcs_srcbind.c`

Project: https://aristotle.harmonic.fun/projects/2c4fa160-11a7-4534-b78f-9595155ab4bb
Run `66ee872b-9567-40a7-a26a-4f3614fcf4d0`, 2026-11-14 20:18 to 21:37 UTC, status "complete with
errors / review suggested". Submitted: `pcs_srcbind.c`, `pcs_srcbind.h`, `Makefile` exactly as in
commit `3c2ab176` (the service returned the sources unchanged; compared byte for byte). Prompt:
`ARISTOTLE_PROMPT.md`.

## Cost: the authorised budget was exceeded

| | Credits |
| --- | ---: |
| Authorised by the owner for this experiment | 50 |
| Limit written in the prompt and repeated in a message during the run | 40 |
| **Billed** | **92** |
| Balance before / after (all promotional, expiry 2026-11-29 06:00 UTC) | 500 / 408 |

No paid charge: the account holds promotional credits only. The run's own summary says it "stopped
at your 40-credit limit"; the billing figure is 92. The session that was to cancel the run at the
cap was suspended when 32 credits were shown and resumed 20 hours later. The service gives no
estimate before a run and no hard cap through this interface; a limit stated in the prompt is not
enforced. **A future run needs a person or a process that can cancel it, or the CLI with a cap if
it offers one.**

## Results as recorded by the service

| Property | Result | Note |
| --- | --- | --- |
| P6 `canon` is prefix-free and injective (data up to 65,536 bytes) | **proved** | about the specification, not the code |
| `pcs_header_size`: no undefined behaviour; returns 0 above the limit, else 49 + 1 + hex digits + 2 + decimal digits + 5 | **proved** | |
| `dec_digits`: number of decimal digits | **proved** | static helper |
| `hex_value`: value of a lowercase hex digit, 16 otherwise (uppercase rejected) | **proved** | static helper |
| P2 the decoder accepts only canonical headers | **refuted** as stated | counterexample: `m` points into `out` |
| P3 the decoder accepts every canonical header | **refuted** as stated | same counterexample |
| P1 memory safety of the decoder | unresolved | see below |
| P4 the encoder writes the canonical header | unresolved | partial proof, no counterexample |
| P5 memory safety of the encoder | unresolved | partial proof, no counterexample |

**The counterexample** (`aristotle/sim/pcs_header_decode_counterexample.c`, written by Aristotle,
reproduced here with gcc and both sanitizers): `out` is the eight bytes of a `size_t` object and
`m` points to the same object. The decoder stores eight `0xFF` bytes, then `*m = len` overwrites
them with the representation of 8, and returns success. My stated preconditions kept `out` apart
from `buf` but said nothing about `*m`. That was an error in the specification I wrote; the
differential tests could not find it because they never alias. The header now states the
precondition. The bytes the results above refer to are kept in `aristotle/sim/pcs_srcbind_v1.c` and
`aristotle/sim/pcs_srcbind_v1_as_submitted.h` (SHA-256 in `aristotle/sim/README.md`); the counterexample
still reproduces against them (`test_counterexample.py`). The decoder in `pcs_srcbind.c` was redesigned
on 2026-11-16 so that it has no length pointer (`DESIGN_DECODER_V2.md`); none of the results above is a
result about the redesigned decoder.

**What the summary reports beyond the recorded results** (`aristotle/ARISTOTLE_SUMMARY.md`): with
the added precondition that `*m` overlaps neither `buf` nor `out`, P1, P2 and P3 "do hold, with
machine-checked proofs". The service's property list does not carry these as proved properties
(P2 and P3 stay refuted as stated, P1 was reopened), so they are reported statements, not recorded
results. A follow-up run that restates the three properties with the precondition would settle
that; it has not been started.

## Assumptions and coverage, as stated by the service

* Model of the C source on x86-64 Linux (LP64): 64-bit `size_t`, 32-bit `unsigned`, 8-bit `uint8_t`.
* Partial correctness: results hold if the function returns. Termination is not proved.
* The static tables `PRE`, `SUF`, `HEXDIGIT` are assumed to hold their initialisers.
* For the decoder results in the summary: `*m` disjoint from `buf` and `out`.

## Can the proofs be inspected or replayed?

No. The download contains the sources, a summary and the counterexample. No Lean statement file
and no proof is returned for C projects (the property view shows a statement, not the proof and not
the imported definitions). A "proved" result is the service's report of a machine-checked proof,
under its model of C. It cannot be re-checked with the Lean kernel here, and it is not PCS
authority. The counterexample, by contrast, is a C program anyone can run.

## What it is worth

* One real defect found in a specification, with a runnable counterexample: useful, and exactly the
  kind of case testing with well-behaved callers misses.
* Helper-level functional properties and the specification lemma P6 proved.
* **None of the three properties that matter for trust (P1, P2, P3) is a recorded proved result**,
  after 92 credits on 60 lines of C. The encoder's four simple loops were not finished.
* Rough cost guide from this run: about 90 credits for one 60-line parser function plus helpers,
  incomplete. A complete canonical decoder for the whole generated part of a proof file (see
  `parse_tail` of the installed runner, about ten times the logic) is out of reach of the remaining 408
  credits at this rate.

## Independent evidence for the same code (tests, not proofs)

`test_srcbind.py` under address and undefined-behaviour sanitizers: the C encoder is byte-identical
to the Python generator on the 8 real data files and 300 random ones; the decoder accepts the 84
committed obligation files; 332 truncations and 123 non-canonical spellings are rejected; of 1,328
single-byte mutations, 1,245 are rejected and the rest are canonical headers of other data.

## Follow-up (superseded proposal; nothing has been started)

The earlier proposal here (restate P1 to P3 of the first decoder with a disjointness precondition,
60-credit stop) is superseded. The owner asked for the hazard to be removed rather than documented;
the decoder was redesigned (`DESIGN_DECODER_V2.md`: lengths returned by value, validation before any
write, nothing written on rejection) and the continuation for P1 to P3 of the redesigned decoder is
prepared in `ARISTOTLE_PROMPT_V2.md`. It has **not** been submitted: the tools offer no enforceable
per-run spending limit, and cancellation by a supervising session failed once (the 92-credit
overrun) and could fail again for the same reason (the session was suspended by a usage limit again
on 2026-11-16). See `ARISTOTLE_PROMPT_V2.md` for what would be sent and the conditions for sending it.
