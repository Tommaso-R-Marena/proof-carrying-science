# Post-evaluation Smith availability diagnosis

**POST-HOC / EXPOSED FINAL CASE — availability diagnosis only.** This investigation occurred after the original final evaluation exposed the Smith2013 worker failures. It is not prospective evaluation, a corrected final score, new scientific validation or evidence of generalization. The original frozen software, results, failed packages, elapsed times and zero scoring credit remain immutable. No reference annotations were consulted for profiling. No uploaded program was imported or executed, and no source/checker module or original evidence package was edited by this investigation.

The coordinator reported that the original v3 and v4 Smith workers failed within their original bounded execution contracts (approximately 52 and 100 seconds including surrounding work). The original Schwen/Bertozzi replays passed. The measurements below diagnose repeated independent XML checking; they do not turn an unperformed original check into a successful result.

## Exact hotspot

The expensive operation is `research.scientific_semantics_v3.checks._xml_claim`, called once per interpreted claim by both the original v3 execution path and additive v4 dispatch. On **every** call it runs `safe_xml(raw)` and rebuilds independent original-byte spans with `_source_spans(raw, root)` before checking the requested declaration/equation. `_source_spans` uses Expat callbacks, including a Python byte scan of every opening tag. The same approximately 350 KB SBML artifact is therefore parsed hundreds of times. This is repeated full-source work, not execution of a supplied model script.

Smith has three comparably expensive artifacts rather than one unique outlier:

| Original source | Raw bytes | SHA-256 | V4 claims | Cumulative raw input if all claims are checked |
| --- | ---: | --- | ---: | ---: |
| `petab/v1/model.xml` | 350,061 | `a21f1453e81ceb8595a072cccb57ccb3c5ae1437074044640fdce1b45bced069` | 929 | 325,206,669 B |
| `supplements/1752-0509-7-41-S11.xml` | 351,484 | `01d711f2a72f5fbeef1c7b8f5f0b4e0a1aa7108623e0e72dc748c64e89ed520c` | 926 | 325,474,184 B |
| `supplements/1752-0509-7-41-S12.xml` | 351,611 | `9251057a4e78bb323bf7b8839f95c7fd1a60cac04a972bff7d76b46fb068544c` | 926 | 325,591,786 B |

These sources contain approximately 6,200 XML elements each; the PEtab model has 6,251. The three sources contribute **2,781 claims and 976,272,639 bytes (about 931 MiB) of repeated checker input** despite only 1,053,156 distinct original bytes. Each checked claim performs both ElementTree and Expat parsing, corresponding to roughly 1.95 GB of parser input before accounting for source hashing, symbol scans or other work. Two additional claims come from `paper.xml` (276,157 bytes, SHA-256 `8eea6c2a23a60ef69dae462637b59f2343f90cf101fcde2cd6bab5203a219cfa`).

## Bounded measurements

The source directory was `/dev/shm/pcs-v4-final-evaluation/projects/smith2013`. Fixed trusted v4 interpretation processed all **23 artifacts / 2,748,458 bytes** in **2.819 seconds**, producing 2,783 claims, 1,590 symbols, 4,270 dependencies, 2,807 obligations and 25 unresolved records. A separate instrumented pass measured interpretation at 2.846 seconds, with the individual XML interpretation calls at 0.654, 0.645 and 0.639 seconds for the three model sources. Supplied `.py` files were parsed only as data through the existing bounded AST parser; they were never imported or executed. The interpretation measurements rule out source decoding/static interpretation as the observed long stall, while not measuring every later v4 stage.

For each claim-bearing artifact, the checker sample selected `min(40, claim_count)` indices deterministically as `floor(i * claim_count / sample_count)`. No annotations, correctness labels or model scores entered selection. The sample contains 122 claims: 40 per SBML source plus the two paper claims. Each subprocess had a 2 GiB address-space bound, a 25- or 30-second CPU bound, an outer 30- or 35-second timeout with a 2-second kill grace, and periodic `faulthandler` traces. Each bounded process completed; no full unmodified 2,783-claim checker run was allowed to exceed the original timeout.

Unprofiled elapsed measurements, which avoid the substantial Python callback overhead added by `cProfile`, were:

| Source | Claims sampled | Raw bytes charged once per sampled claim | Two XML parser passes, input bytes | Elapsed |
| --- | ---: | ---: | ---: | ---: |
| `paper.xml` | 2 | 552,314 | Expat model pass not reached | 0.00798 s |
| `petab/v1/model.xml` | 40 | 14,002,440 | 28,004,880 | 1.66643 s |
| `S11.xml` | 40 | 14,059,360 | 28,118,720 | 1.80322 s |
| `S12.xml` | 40 | 14,064,440 | 28,128,880 | 1.83435 s |

The 122-claim sample took **5.312 seconds**. Multiplying each artifact’s observed per-claim sample cost by its total claim count gives a **122.92-second projection** for original claim checking alone. This is a linear estimate, not a measured full-run duration, rigorous upper bound or solver benchmark. It is already larger than the original v4 worker’s 75-second CPU / 100-second parent-wall contracts and the v3 worker’s 30-second CPU / 45-second parent-wall contracts. Parent pipeline costs are additional.

A separate `cProfile` run of the same sample took 10.281 seconds and recorded:

| Trusted function | Calls | Cumulative seconds |
| --- | ---: | ---: |
| `checks.check_claim` | 122 | 10.280 |
| `checks._xml_claim` | 122 | 10.022 |
| `checks._source_spans` | 120 | 8.894 |
| Expat `Parse` | 120 | 7.661 |
| `_source_spans.start` callback | 745,880 | 6.393 |
| `model_checks.safe_xml` | 122 | 0.933 |

The profile counted **40 `safe_xml` calls and 40 `_source_spans` calls per 40-model-claim sample**, rather than one independent source preparation. The seven-second `faulthandler` trace captured `ElementTree.XML -> model_checks.safe_xml -> checks._xml_claim -> checks.check_claim`. Profiled maximum RSS was 88,064 KiB; the later unprofiled diagnostic process reached 88,004 KiB. These are process high-water values, not isolated allocation measurements. The timing ratio between profiled and unprofiled runs is why the 238-second profiled extrapolation is not used as the runtime estimate.

An additional **diagnostic-only** subprocess temporarily memoized the outputs of the original independent `safe_xml` / Expat preparation functions by actual immutable raw bytes within that one process. It did not reuse interpreter trees/spans, edit modules, persist a cache, write a package, run replay or compute a grade. All 122 sampled records matched the unmodified checker **exactly after removing only their top-level `seconds` field**. Reusing those preparations then let the unchanged individual `check_claim` function process all 2,783 claims in 1.654 seconds: 1,587 source-declaration statuses, 1,182 scoped-equation statuses and 14 unknowns; authority remained false and scientific meaning open for every record. Four ElementTree preparations (three models and one non-model paper) and three Expat preparations were built. The diagnostic stable-record SHA-256 was `fa3950813d331eddf4c2c30ea3e8ca90a30ba53637bf7d69295b066cd148fb89`.

That ablation confirms that repeated source preparation dominates the sample. It is **not** an accepted implementation, proof of full-record equivalence, replacement final result or proposal to activate monkeypatching/memoization. The complete unmodified checker was not run to completion for comparison, and later numerical/formal stages were not measured by this ablation.

## Minimal proposed availability successor

The smaller additive repair is a **fixed cumulative original-source checker input-byte budget in v4 dispatch**, retaining the entire interpretation and the unchanged independent v3 checker. Do not raise the global worker timeout, change old v3 files or cache verdicts. Before dispatching each potentially repeated source check, charge its complete original raw length to a deterministic per-project budget. Every valid claim beyond that budget receives its own source-bound `UNKNOWN` record with an explicit budget reason, source identity and accounting. Grounding failure remains a grounding failure; reaching a budget cannot make malformed evidence valid. No skipped check receives declaration/equation/numerical success or scientific authority.

A generic **32 MiB (33,554,432-byte) cumulative raw-input budget**, charged once per dispatched claim, has an evidence-based availability margin. The coordinator supplied the existing successful source-check counts of 48 development, 58 Schwen and 16 Bertozzi checks. Using only their public frozen source-size metadata, even charging every one of those checks the largest XML in its project gives these conservative upper bounds:

| Existing case | Checks | Largest XML bytes | Maximum raw-input charge |
| --- | ---: | ---: | ---: |
| Development Fiedler | 48 | 252,545 | 12,122,160 B |
| Schwen | 58 | 363,978 | 21,110,724 B |
| Bertozzi | 16 | 133,049 | 2,128,784 B |

All are below 32 MiB; this argument does not need final reference content. Smith’s two paper checks plus approximately 94 model checks fit this budget, with the remainder explicitly unknown. The measured model sample suggests a few seconds of independent XML checking at that budget; this is not a hard wall-time guarantee for every admissible XML. The existing worker CPU/memory/wall contracts remain the outer bound. Deterministic iteration order creates a visible coverage preference for earlier source paths, which must be disclosed rather than represented as whole-project check completeness.

Independently test the successor with (1) small genuine checks whose complete original records/statuses remain unchanged; (2) an injected counting checker and synthetic byte sizes demonstrating exact budget-boundary accounting, no later dispatch after exhaustion, one output per claim and no lost neighbors; (3) exact source/hash/span/namespace/scope substitutions refused even after budget exhaustion; (4) transformed PDF/DOCX quotes retaining their own unknown status; (5) a larger legitimate synthetic SBML case returning a complete interpretation and bounded partial check coverage; and (6) actual original development/Schwen/Bertozzi check counts retained. Verify skipped records are `UNKNOWN`, authority false, scientific meaning open, and report their count and byte budget separately. Preserve original frozen runs, mark any Smith repair run explicitly post-hoc, and give a successor its own software/context identity. This proposal grants availability and partial coverage only.

## Source and scope record

Measured trusted source identities:

- `scientific_semantics_v3/checks.py`: SHA-256 `2c91c029d6c5fda43ecf9c99823d90b1dfd594b17d3d73a637df1693147e704d`.
- `scientific_review_v4/semantics.py`: SHA-256 `d94a1a62db26302bdd9a4af742a02e1cf591b2561b95a19fa6c06787c8a9bba8`.
- Original `scientific_semantics_v3/worker.py`: SHA-256 `0cbaf0764f736b92321f6f6b0c37f31a1dbe54a602da5d0e4fa00e3fcb1a5fe9`.

The Git snapshot observed while compiling this diagnosis was `f8d9802587e0a2fe9a254ca3b8b8bc41d7f0bf48`; exact original evaluation software identities remain those in the immutable final benchmark evidence. Investigation date: 2026-11-09 UTC. The sole saved artifact from this review is this diagnosis document. No production authority, protected source gate, theorem, original result or upstream program was modified.
