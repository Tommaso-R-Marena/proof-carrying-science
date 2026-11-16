<!--
NOT A SPENDING CONTROL. This file contains no credit budget, on purpose. A budget written in a
prompt does not bound what a run costs: the 2026-11-14 run's summary says it "stopped at your
40-credit limit", and 92 credits were billed (ARISTOTLE_RESULTS.md). The owner requires an external,
enforceable limit (a cap the service enforces, or a person or process that follows the run and
cancels it in time). Whoever starts a run establishes that limit and records it outside this file
first. Preparing this file started nothing and spent nothing.

What would be sent: the text between PROMPT START and PROMPT END, as the prompt of a continuation of
the existing project, together with exactly the three files listed under "Files to upload".
-->

# Aristotle continuation: the redesigned header decoder (P1 to P3)

Project `2c4fa160-11a7-4534-b78f-9595155ab4bb`,
https://aristotle.harmonic.fun/projects/2c4fa160-11a7-4534-b78f-9595155ab4bb (first run:
`ARISTOTLE_RESULTS.md`). Design: `DESIGN_DECODER_V2.md`.

<!-- PROMPT START -->
Please continue this project with the redesigned header decoder in pcs_srcbind.c (header pcs_srcbind.h, build with the Makefile). Verify only the three decoder properties P1, P2 and P3 stated below.

What the previous run on this project established (run 66ee872b-9567-40a7-a26a-4f3614fcf4d0, 2026-11-14), as your property list and summary recorded it:
- Proved: P6 (canon is prefix-free, hence injective, for data of at most 65536 bytes); pcs_header_size (no undefined behaviour; returns 0 when m > 65536, otherwise 49 + 1 + (1 if m = 0, else 2m) + 2 + the number of decimal digits of m + 5); the static helpers dec_digits and hex_value.
- Refuted as stated: P2 and P3 of the old decoder, which returned the header size and reported the data length through a pointer m. When m pointed into out, the final store *m = len overwrote the decoded bytes while the call still succeeded. Your counterexample sim/pcs_header_decode_counterexample.c is kept in our repository as a record. It uses the old five-argument interface, so it does not compile against the new header; that is intended.
- Unresolved: P1 of the old decoder, and P4 and P5 (the encoder). Your summary also reported that P1, P2 and P3 of the old decoder hold if *m overlaps neither buf nor out, an assumption you added; the property list did not record them as proved, so we treat them as reported, not established.
- Your stated model and assumptions: x86-64 LP64 (64-bit size_t, 32-bit unsigned, 8-bit uint8_t); partial correctness only (termination not proved); the static tables PRE, SUF and HEXDIGIT hold their initializers.

In the new pcs_srcbind.c, pcs_header_size, dec_digits, hex_value, the encoder and the tables PRE, SUF and HEXDIGIT are byte-identical to the previous run's file; only pcs_header_decode and its declaration changed. Please reuse what was proved about them.

The redesign. The project owner asked for the length-pointer hazard to be removed from the interface rather than documented as a caller obligation, and for the possible designs to be compared. This design is our proposal for that, chosen after comparing it with keeping the pointer under an extra precondition and with returning 1 + data length; the owner reviews the choice.
- There is no length pointer:
      typedef struct { size_t header; size_t data; } pcs_decoded;
      pcs_decoded pcs_header_decode(const uint8_t *buf, size_t n, uint8_t *out, size_t cap);
  Both lengths come back by value. header == 0 means the input was rejected, and then data == 0. The only pointer the decoder writes through is out.
- Two passes. Pass 1 validates the whole header and writes nothing. Only if the header is canonical and its data fits in cap does pass 2 store the data in out[0..data). A rejected input leaves out untouched.
- The checks of pass 1 and their order are those of the old decoder; the copy loop moved after the last check.

The owner's requirements for this run:
- Do not change the C code. If a property is false, give a concrete counterexample as a runnable C program against the uploaded files, as you did for the old decoder.
- Do not add assumptions merely to make a proof go through. If a property cannot be proved under the preconditions below, say so and why, rather than strengthening them. List any assumption you do add, with its reason.
- Memory safety alone is not enough: a decoder that is memory safe but accepts a non-canonical header, or returns the wrong data, fails P2 or P3.
- Out of scope: the encoder pcs_header_encode (P4 and P5) and any property not listed below. Please do not start other work. Work on P1, then P2, then P3.

Definitions. For a byte sequence d of length m with m <= 65536, the canonical header canon(d) is the byte string
    PREAMBLE || "0x" || HEX(d) || ", " || DEC(m) || SUFFIX
where PREAMBLE is the 48 bytes "open PCS.ClaimCheck\n\ndef pcs_src : Source := " followed by E2 9F A8, HEX(d) is two lowercase hexadecimal digits per byte (first byte first) or the single digit "0" when m = 0, DEC(m) is the decimal representation of m without leading zeros ("0" when m = 0), and SUFFIX is the 5 bytes E2 9F A9 0A 0A. This is the definition in pcs_srcbind.h.

Preconditions of a call pcs_header_decode(buf, n, out, cap). These are the only assumptions about the caller, each with its reason:
- buf points to n readable, initialised bytes with arbitrary values; when n == 0 it is never dereferenced and may be NULL. Reason: the decoder can read only what the caller provides.
- out points to cap writable bytes whose initial contents do not matter; when cap == 0 it may be NULL. Reason: cap is the output capacity the caller provides, and data longer than cap is rejected.
- buf[0..n) and out[0..cap) do not overlap. Reason: this is the usual input/output condition of a decoder, the same as memcpy's. Pass 2 reads two hex digits for each byte it writes, so an out that overlapped hex digits not yet read would overwrite input before it is decoded, and an out that overlapped the rest of the header would change the bytes compared with canon(d) afterwards. In-place decoding is not supported.
- Both regions stay allocated for the whole call, and nothing else (another thread, a signal handler) accesses them during it. Reason: pass 2 relies on reading the bytes pass 1 checked; the decoder keeps no pointer after it returns.
n and cap are otherwise arbitrary size_t values.

Properties, in priority order. r is the returned pcs_decoded; "after the call" means the memory state when the call returns.

P1 (memory safety and side effects). Under the preconditions, the call has no undefined behaviour (no out-of-bounds access, no signed overflow, no invalid shift, no read of an uninitialised object). It reads no memory other than buf[0..n), its local variables and the static tables PRE and SUF. It writes no memory other than out[0..r.data) and its local variables. r.data <= min(cap, 65536). If r.header == 0 then r.data == 0 and out is not written at all.

P2 (soundness: only canonical headers are accepted). If r.header > 0, then r.header <= n, r.data <= cap, r.data <= 65536, and buf[0..r.header) is exactly canon(out[0..r.data)), with out read after the call (the call does not modify buf). In words: whatever the decoder accepts is the canonical header of exactly the bytes it returns.

P3 (completeness: every canonical header is accepted). If d is a byte sequence with |d| <= 65536 and |d| <= cap, and buf[0..n) begins with canon(d) (so n >= |canon(d)|), then r.header = |canon(d)|, r.data = |d|, and out[0..|d|) = d after the call, whatever bytes follow canon(d) in buf.

Please state each property about the function exactly as it is, and report for each whether it is proved, refuted (with the counterexample program) or unresolved. List every assumption you add, with its reason, and say what your model of C covers: integer widths, termination, the initial values of the static tables, and anything else a reader needs to judge the results.
<!-- PROMPT END -->

## Files to upload

The same three paths as in the first run, nothing else (no Lean, no tests, no data, no credentials):

| Path | SHA-256 | Note |
| --- | --- | --- |
| `pcs_srcbind.c` | `312314d436d3f52e191555f32bcd79e721ea8d699047dcf45ffd1ce07f0968b5` | the redesigned decoder; `pcs_header_size`, the helpers, the tables and the encoder unchanged |
| `pcs_srcbind.h` | `4fd71165f7861a6847dffde6b9529f191a893b9ec3498df1d940bdba276b0cfb` | the `pcs_decoded` type and the decoder's contract |
| `Makefile` | `881bdd6fe90ce86d1470eeac1bc947d144a9537ae2df838c9d7acec66d46291e` | unchanged since the first run (commit `3c2ab176`) |

Check before sending:

```bash
sha256sum research/claimcheck_assurance_v1/c/pcs_srcbind.c research/claimcheck_assurance_v1/c/pcs_srcbind.h research/claimcheck_assurance_v1/c/Makefile
```

The first run's sources are kept as `aristotle/sim/pcs_srcbind_v1.c` and
`aristotle/sim/pcs_srcbind_v1_as_submitted.h`, its counterexample beside them.

## How the results will be recorded

As for the first run (`ARISTOTLE_RESULTS.md`): each property's result as the service records it
(proved, refuted with its counterexample, unresolved), the statement it proved, the assumptions it
states, and the credits billed. No C proof artifact is returned, so a "proved" result is the
service's report of a machine-checked proof under its model of C on x86-64, not a proof replayed
here with the Lean kernel, and it says nothing about the Python runner. A counterexample is
reproduced locally before it is reported.
