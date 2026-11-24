# Summary of changes for run 66ee872b-9567-40a7-a26a-4f3614fcf4d0
I stopped at your 40-credit limit. P2 and P3 are false under your stated preconditions; there is a confirmed counterexample. P6 is proved. P1, P4 and the encoder half of P5 are unresolved. All results are about `pcs_srcbind.c` exactly as submitted.

**Refuted: P2 and P3, when `m` points into `out`.** Your preconditions keep `out` away from `buf`, but nothing stops `m` pointing into `out`. The reproducer is `sim/pcs_header_decode_counterexample.c`:
- `out` is the 8 bytes of a `size_t` object, `cap = 8`, and `m` points to that same object.
- `buf` holds `canon` of eight 0xFF bytes.
- The call returns 74 with `*m = 8`, but the final `*m = len;` overwrites the decoded bytes. `out[0..8)` ends up as `08 00 00 00 00 00 00 00` instead of eight 0xFF bytes.
- So `buf[0..74)` is not `canon(out[0..*m))` (P2 fails), and `d` is not stored in `out` (P3 fails).
- The run was observed with address and undefined-behaviour sanitizers and produced no sanitizer reports. It uses no undefined behaviour, since C allows reading and writing a `size_t` object through `uint8_t`.

**Proved for the non-aliasing case.** If `*m` is also kept apart from `buf` and `out`, P2 and P3 do hold, with machine-checked proofs. In that case:
- `pcs_header_decode` has no undefined behaviour for any `n`, `cap` and buffer contents.
- A return of `L > 0` means `L <= n`, `*m <= cap`, `*m <= 65536`, `buf[0..L)` = `canon(out[0..*m))`, and the rest of `out` is unchanged.
- Every canonical prefix `canon(d)` with `|d| <= min(cap, 65536)` is accepted: it returns `|canon(d)|`, sets `*m = |d|` and stores `d`.

**Other proved results**
- **P6.** `canon` is prefix-free, and therefore injective, on byte sequences of length at most 65536.
- **`pcs_header_size`.** No undefined behaviour for any `m`. It returns 0 when `m > 65536`, otherwise 49 + 1 + (1 if `m` is 0, else 2·`m`) + 2 + (number of decimal digits of `m`) + 5.
- **Static helpers.** `dec_digits` returns the number of decimal digits of `m`. `hex_value` returns the value of a lowercase hex digit and 16 for anything else, so uppercase is rejected. Neither has undefined behaviour.

**Unresolved**
- **P1** is proved only when `*m` does not overlap `buf` or `out`. The aliasing case is not proved; the reproducer's clean sanitizer run is suggestive, not a proof.
- **P4 and P5 for `pcs_header_encode`.** The proof covers the call to `pcs_header_size`, part of the early `return 0` branches and part of the loop that copies `PRE`. The rest of that loop, the hex, decimal and `SUF` loops, and the final postcondition are still open. No counterexample was found for P4 or P5.
- **Size equality.** It is not proved that `pcs_header_size(m)` equals `|canon(d)|`; that is part of P4.

**Assumptions I added**
- **Static tables.** `PRE`, `SUF` and `HEXDIGIT` are assumed to hold their initializers; I did not prove the program start-up step separately.
- **Separate `*m`.** For the proved decoder results only, `*m` must not overlap `buf` or `out`.

**What the model covers**
- **Target.** x86-64 LP64: 64-bit `size_t`, 32-bit `unsigned`, 8-bit `uint8_t`, with unsigned wrap-around checked wherever it can occur.
- **Partial correctness only.** Every result holds if the function returns; termination is not proved.

## Suggested follow-up

Possible bug: `pcs_header_decode` writes `*m = len` after filling `out`, so a caller whose `m` points into `out` gets its decoded bytes overwritten while the call still succeeds. You can either document that `m` must not overlap `out` or `buf`, or decode into a local first. I can help with either change, or rerun the proofs under the stricter precondition.