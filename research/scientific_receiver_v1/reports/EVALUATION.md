# Scientific receiver v1: preserved actual evaluation

The preregistered 10,774-case campaign completed on 2026-10-18 against the actual pinned Lean executable running `--run Main.lean`. It observed 778 accepts, 9,996 rejects, and zero acceptance, result, byte-echo, metadata, or independently labeled expectation disagreements across 44 families. This is Lean compiled-IR execution through the interpreter, not a standalone native executable.

| Measurement | Observed value |
|---|---|
| Campaign interval UTC | 2026-10-18 18:29:26.829972–18:42:47.921205 |
| Campaign wall time | 801.0912107549957 seconds |
| Seed | 20261018 |
| Random positive contracts | 256, with fixed-family mutations and positive controls |
| Actual evaluated bytestrings | 10,774 |
| Independent reference / actual Lean accepts | 778 / 778 |
| Cases with any issue | 0 |
| Corpus SHA256 | `04658b54ac7ded872719176800e18d7339a030755c759a902e14666e15fca950` |
| Frozen preregistration SHA256 | `a8abe16db96298383c118fb9196764886b9bf632bb0614bcc10aeea3d96a23ef` |
| Actual Main source SHA256 | `427f046da8101b3e1b29c28caaf40c72ddb3da49c2ba5d5012dacb02c579ca99` |
| Actual Lean executable SHA256 | `3e0d0d3d801675359f2d4cf9815bfdb417b20b92fdd9d48b3b14c95bbae28bbf` |

The environment interrupted the supervising chat after the campaign finished. On resumption on 2026-10-19, the original complete summary, 10,774 actual response records, and 10,774 full input records were present. They were verified against the unchanged seeded corpus, exact byte echoes, all accepted rational results, and the independent reference. The actual Main source and Lean executable hashes still matched. The full campaign was preserved without a redundant rerun. The two large evidence files are losslessly gzip-compressed with deterministic headers; `EVIDENCE_INDEX.json` records both compressed and original hashes, sizes, and original modification times.

The missing three-case pilot then ran against the same actual Lean command and reconstructed recorded `LEAN_PATH` on 2026-10-19 02:29:23.960374–02:29:26.407239 UTC (2.446861443 seconds).

| Synthetic case | Actual observation | Evidence category |
|---|---|---|
| Exact discrete A→B | Lean receiving accepted; reference agreed: final A=13/2, B=7/2, total=10, derived B enclosure [2,5] | Actual compiled-IR receiving, linked to the separately checked Lean theorem |
| Four sampled IV-bolus PK values | Original PK adapter replayed all four values; maximum absolute concentration difference 2e-15 mg/L; a 10% final-row tamper rejected | Computational sampled-model replay; empirical and Lean validity unverified |
| Finite SCM witness | Original verifier observed observational TV=0 and intervention TV=1/2; identical-model negative control rejected | Computational finite nonidentifiability witness; no causal-effect support |

The reused finite-SCM witness has P(X=1)=0 in its observational table; missing treatment support is part of this example. It does not establish nonidentifiability under an added positivity assumption.

All 90 Python tests passed on resumption (0.90 seconds). The existing PK and SCM components were imported at their original paths; their source identities and the actual pilot responses are retained in the pilot report. No receiver output was used for training, and no source was generated from submitted inputs.

During the original campaign, the coordinating process reported a fresh compilation of the same source modules into the receiver's `.olean` directory, then stopped further overwrites. No loading error or nonzero CLI exit occurred in the completed campaign. This overlap is a local execution limitation: the report does not claim that the filesystem was held immutable throughout evaluation, or establish compiler/IO/OS correspondence or an independently protected execution root. The later pilot used the preserved, source-matching receiver artifacts. The index records the source and compiled-artifact identities observed after resumption, without presenting them as an independently protected authority.

Zero observed disagreements is agreement on this finite, deliberately constructed corpus. It is not a general Python-to-Lean refinement theorem, exhaustive parser coverage, statistical population guarantee, empirical chemistry or physiology, clinical safety, cryptographic provenance, broad scientific acceptance, or production authority. PK and SCM observations retain their computational categories; empirical validity remains unverified.
