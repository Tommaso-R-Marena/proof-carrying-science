Verify the C functions in pcs_srcbind.c (header pcs_srcbind.h, build with the Makefile). The code is a small,
security-critical codec: it binds the bytes of a data file into the text of a machine-checked proof file.
A wrong acceptance would let a proof about one file be presented as a proof about another.

Context and intent (decisions of the project owner):
- This is a bounded feasibility experiment. Budget: use at most 40 credits in total. If the budget is not
  enough for everything, prove the properties in the order given below and stop; do not start extra
  properties that are not listed.
- Functional correctness matters more than memory safety alone: a decoder that is memory safe but accepts a
  non-canonical or wrong header is a failure.
- Do not change the C code. If a property is false, report the counterexample.

Definitions. For a byte sequence d of length m with m <= PCS_MAX_DATA (65536), the canonical header canon(d)
is the byte string
    PREAMBLE || "0x" || HEX(d) || ", " || DEC(m) || SUFFIX
where PREAMBLE is the 48 bytes "open PCS.ClaimCheck\n\ndef pcs_src : Source := " followed by E2 9F A8,
HEX(d) is two lowercase hexadecimal digits per byte (first byte first) or the single digit "0" when m = 0,
DEC(m) is the decimal representation of m without leading zeros ("0" when m = 0),
and SUFFIX is the 5 bytes E2 9F A9 0A 0A.

Preconditions for every call: `buf` is readable for `n` bytes, `d` is readable for `m` bytes, `out` is
writable for `cap` bytes, `m` (the out-parameter of the decoder) points to a valid size_t, and the output
buffer does not overlap the input buffers. Nothing else is assumed: n, m and cap are arbitrary size_t values
and the buffer contents are arbitrary.

Properties, in priority order:

P1 (memory safety of pcs_header_decode). Under the preconditions, pcs_header_decode(buf, n, out, cap, m)
   reads only buf[0..n), writes only out[0..cap) and *m, and has no undefined behaviour (no out-of-bounds
   access, no signed overflow, no invalid shift).

P2 (the decoder accepts only canonical headers). If pcs_header_decode(buf, n, out, cap, m) returns L > 0,
   then L <= n, *m <= cap, *m <= 65536, and buf[0..L) is exactly canon(out[0..*m)), the canonical header of
   the bytes it stored.

P3 (the decoder accepts every canonical header). If m0 <= 65536, m0 <= cap, and buf[0..n) begins with
   canon(d) for a byte sequence d of length m0, then pcs_header_decode returns the length of canon(d), sets
   *m = m0 and stores d in out[0..m0).

P4 (the encoder writes the canonical header). If m <= 65536 and pcs_header_size(m) <= cap, then
   pcs_header_encode(out, cap, d, m) returns pcs_header_size(m), which is the length of canon(d[0..m)), and
   out[0..that length) = canon(d[0..m)); bytes of out beyond it are unchanged. If m > 65536 or the size
   exceeds cap, it returns 0 and writes nothing.

P5 (memory safety of pcs_header_encode and pcs_header_size), as in P1.

P6 (consequence, only if cheap): canon is injective and prefix-free: if canon(d1) is a prefix of canon(d2)
   then d1 = d2.

Please state each property about the functions as they are, list every assumption you add, and say which
parts of the C semantics your model covers (for example integer widths and that termination is not proved).
