# The header decoder, second version: no length pointer, validate before writing

Research code, no PCS v0.6 authority. Nothing in the ClaimCheck runner calls this C code; the
runner's Python grammar is the gate (its header rule agrees with this decoder and with the proved
Lean decoder `formal/ClaimCheckAssurance/Header.lean`, by test: `conformance/test_header_refinement.py`).
The C decoder exists to be verified on its own, as a second implementation of the proved function;
a result about it, from tests or from Aristotle, is not a result about the Python runner.

## What went wrong in the first version

```c
size_t pcs_header_decode(const uint8_t *buf, size_t n, uint8_t *out, size_t cap, size_t *m);
```

It reported the data length through `m` and wrote `out` while still validating. Aristotle refuted
P2 and P3 as they had been stated: when `m` points into `out`, the final store `*m = len` overwrites
decoded bytes and the call still succeeds (`aristotle/sim/pcs_header_decode_counterexample.c`, kept
runnable by `test_counterexample.py`). The stated preconditions separated `out` from `buf` but not
`*m` from `out`. A second weakness, not a refutation: on rejection, `out` could already hold part of a
decoding.

## Options

| | (a) v1 + precondition | (b) v2: lengths by value, two passes | (c) return `1 + length` |
| --- | --- | --- | --- |
| Interface | as v1; the caller must keep `*m` disjoint from `buf` and `out` | `pcs_decoded pcs_header_decode(buf, n, out, cap)` with `{header, data}`; `header == 0` is a rejection | `size_t pcs_header_decode(buf, n, out, cap)`: 0 is a rejection, otherwise `1 + data length`; the header size is `pcs_header_size(data length)` |
| Pointers written | `out` and `*m` | `out` only | `out` only |
| Caller's obligations | readable `buf`, writable `out`, `*m` valid, **three regions pairwise disjoint** | readable `buf`, writable `out`, `buf` and `out` disjoint | as (b) |
| Can the obligation be checked by a compiler or a reviewer? | no: `restrict` on the prototype documents it but violating it is undefined behaviour, not a diagnostic; the overlap that broke v1 (a length field inside the output object) is easy to write by accident | the input/output non-overlap is the familiar `memcpy` condition; the aliasing of a length with the output cannot be expressed at all | as (b), plus an off-by-one convention every caller must remember |
| Writes on rejection | possible (partial decoding) | none | none, if also two-pass |
| P1 (memory safety) must state | reads within `buf[0..n)`, writes within `out[0..len)` and `*m`, under three-way disjointness | reads within `buf[0..n)`; writes only `out[0..data)` and only on acceptance | as (b) |
| P2/P3 must state | the result about `out` and `*m`, both read after the call, under the three-way disjointness | the result about `out` read after the call and the returned pair; the validation pass writes nothing, so it is a pure function of `buf[0..n)` and `cap`, and the copy pass writes a region the validation never reads again | as (b), with the length recovered from the encoded return value |
| Cost | none | a second pass over at most 131,072 hex digits | as (b) |

Rejected alternatives:

* Storing `*m` before `out` instead of after: with aliasing, the decoded bytes then overwrite the
  length. Either order breaks when the regions overlap.
* Decoding into a local buffer and copying: needs 64 KiB of stack or dynamic memory, and the final
  store to `*m` can still alias `out`.
* Adding `restrict` to the v1 prototype: it states the precondition in the type, but a violating
  caller compiles without warning and the behaviour becomes undefined; it does not remove the hazard.

## Recommendation: (b), for the owner's review

(b) removes the hazard by construction instead of documenting it, leaves only the conventional
input/output non-overlap, and adds a property callers can rely on: a rejected header leaves `out`
untouched. It is also easier to verify: the validation pass is a pure function of the input, which
is how `Header.lean`'s proved `decode` is written (same checks, same order), and the copy pass is a
loop over a region the validation never reads again. (c) has the same safety but encodes two results
in one number with a `+1` convention, which moves a source of off-by-one errors to every caller.

Why the remaining non-overlap condition is needed: pass 2 reads two hex digits for each byte it
writes. An `out` that overlaps hex digits not yet read would overwrite input before it is decoded,
and an `out` that overlaps the rest of the header would change the bytes the caller later compares
with `canon(d)`. In-place decoding is therefore not supported; it would need its own, weaker
statement.

## What changed, and the evidence

* `pcs_srcbind.h`, `pcs_srcbind.c`: the decoder as in (b). The encoder and `pcs_header_size` are
  unchanged. Builds with `-std=c99 -O2 -Wall -Wextra -Wpedantic -Wconversion -Werror`.
* `aristotle/sim/`: the examined first version kept byte for byte (`pcs_srcbind_v1.c`, the header as
  submitted and with the later precondition comment), with digests in `aristotle/sim/README.md`.
* `test_counterexample.py`: Aristotle's counterexample, unchanged, still reproduces against the
  first version (both headers; exit status 1; the documented output; no sanitizer report), and does
  not compile against the second version.
* `test_srcbind.py` (address and undefined-behaviour sanitizers): as before (encoder equal to the
  Python generator on 8 real and 300 random files; 84 committed obligation files decoded; 332
  truncations and 123 non-canonical spellings rejected; 1,245 of 1,328 single-byte mutations
  rejected, the rest canonical headers of other data), plus: every one of 2,134 rejections leaves a
  pattern-filled `out` unchanged, and every acceptance leaves `out[data..cap)` unchanged. Two
  deliberately broken decoders (writing before validation is complete; writing one byte past the
  data) were each caught by these checks.
* `conformance/test_header_refinement.py`: the C decoder, the proved Lean decoder (executed with
  `lean --run`) and the runner's Python header rule agree on all 5,755 vectors, and the C decoder
  writes nothing on each of the 5,535 rejections and nothing beyond `out[0..data)` on the 220
  acceptances.

These are tests. Whether the C code meets P1 to P3 for every input is what the Aristotle submission
`ARISTOTLE_PROMPT_V2.md` asks; a result from the service is a report of a proof under its model of C
on x86-64, not a proof replayed here.
