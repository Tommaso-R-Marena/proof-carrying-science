# The decoder the 2026-11-14 Aristotle run examined (kept as a record)

Aristotle run `66ee872b-9567-40a7-a26a-4f3614fcf4d0` on project
`2c4fa160-11a7-4534-b78f-9595155ab4bb` (see `../../ARISTOTLE_RESULTS.md`) examined the first version
of the header codec, whose decoder reports the data length through a pointer `size_t *m`.
`pcs_header_decode_counterexample.c`, written by Aristotle, shows that when `m` points into `out`
the final store `*m = len` overwrites decoded bytes while the call still succeeds. The decoder in
`../../pcs_srcbind.c` has since been redesigned so that it has no length pointer at all
(`../../DESIGN_DECODER_V2.md`); the files here keep the examined version runnable.

| File | SHA-256 | What it is |
| --- | --- | --- |
| `pcs_srcbind_v1.c` | `7a3a661acc8480c51c1fec5b5c7f883c902baee7494453e396f1c47872878ce5` | the decoder source, byte-identical to what was submitted (commit `3c2ab176`) |
| `pcs_srcbind_v1_as_submitted.h` | `96e44293fc81eb7e58e437451bfabb4c3deea57a168a127f40b804476a4e9a8c` | the header exactly as submitted (commit `3c2ab176`) |
| `pcs_srcbind_v1.h` | `c68b9df8c10611f3b9a6fd923a70d82af152302f478e6a9eecb7479f3cd8b3a7` | the same header with the comment added after the run (commit `8c7b4abc`) that states the `*m` disjointness precondition; the declarations are identical |
| `pcs_header_decode_counterexample.c` | `225d5c71adfa7839a999c89ef476dd9d34f99d6606b73d84f56371a6c20cb07f` | Aristotle's counterexample, unchanged |

`../../test_counterexample.py` lays these files out in a temporary directory so that the
counterexample's `#include "../../pcs_srcbind.h"` resolves to the v1 header, builds it with the
address and undefined-behaviour sanitizers, and checks that it still reports the violation (exit
status 1, `out[0..8) = 08 00 00 00 00 00 00 00`). It also checks that the same program no longer
compiles against the current decoder, whose interface has no pointer that could alias `out`.
