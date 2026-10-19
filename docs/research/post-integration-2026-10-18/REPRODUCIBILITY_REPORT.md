# Executed qualification and evidence

Source snapshot and branch roles are in `CURRENT_SOURCE_BASELINE.json`; live
final-head CI belongs to the corresponding draft PR descriptions. This document
records the local pre-publication qualification, rather than predicting a CI run.

| Check | Observed result | Evidence |
|---|---|---|
| Fresh new Lean modules and complete namespace audit | 54 authored theorems;190 namespace theorem declarations including generated; standard three axioms only | `research/scientific_receiver_v1/reports/qualification-20261019/` and `RECEIVER_THEOREM_INVENTORY.json` |
| Receiver/producer/reference/host/assurance/framing tests | 160 passed,0 failed,0 skipped;56.53s | `reports/receiver-tests-20261019.log` and `.xml` |
| Fixed seeded actual Lean differential campaign | 10,774 cases;778 accepts;9,996 rejects;0 disagreements;801.09s | `reports/differential-20261018/` and `reports/EVALUATION.md` |
| Extreme rational intermediate probe | 13 actual launches;11 accepts;2 expected rejects;0 issues;576-digit intermediate denominator | `reports/resource-stress-20261019/` |
| Full inventoried module-pin receiving | Actual positive and negative cases pass pre/post pin checks, response comparison and receipt signature replay | `reports/full-profile-20261019/` |
| Independently reproduced host faults and retest | Both old defects reproduced; fixed sources return signed rejection/terminate child | `reports/independent-host-review/` |
| Scientific pilot | Three synthetic cases preserve exact/computational/negative categories | `reports/pilot-20261019/` |
| Existing imported source gate | All1,992 predecessor entries and38V7 modules unchanged on receiver branch | `python -m research.integration_v1.source_gate` |
| Receipt repair, separate #154 | 124 affected tests,0 skips;40 CI-selection tests;1 fresh clean-room rebuild;original28case decisions preserved | Separate repair report and raw logs under `/workspace/.onboarding/` |
| History, separate #157 | 32 tests;fresh Lean library and28 authored theorem axiom closures;hosted standalone Lake build passes | Separate history reports and run39191133912 |

The full-profile experiment pins 4,983 declared Lean modules and19,878 distinct
dependency artifact paths. Object inventories also contain duplicate resolved
paths; the host deduplicates those paths. The actual object inventory is not an
OS loader measurement or an independent source-to-object attestation.

Local Lean4.28.0 comes from executable SHA256
`3e0d0d3d801675359f2d4cf9815bfdb417b20b92fdd9d48b3b14c95bbae28bbf`;
Main source SHA256 is
`427f046da8101b3e1b29c28caaf40c72ddb3da49c2ba5d5012dacb02c579ca99`.
Execution is `lean --run` over compiled IR, not a standalone native binary. New
proof modules were freshly checked against validated, read-only, source-identical
cached imports. The checker compares954 tracked dependency-project files and
validates nine Git dependency revisions/clean sources. Cached object trust remains
explicit. Hosted Lake builds separately exercise normal pinned project setup.

The original campaign completed before an interruption. Its full source/response
records were recovered and independently revalidated, not rerun or fabricated.
The original same-source recompilation overlap is retained as a limitation in
`reports/EVALUATION.md`. Later final qualification writes fresh outputs to a
separate directory and performs actual receiving with those stable outputs.

Original dataset/report bytes remain indexed separately. New large module/import
inventories are losslessly compressed; `QUALIFICATION_EVIDENCE_INDEX.json` gives
compressed and uncompressed hashes. Decompress with standard gzip before direct
inspection. All source, algorithm and platform trust assumptions survive a hash
match.

The first receipt full-CI run39154782008 failed the clean-room job. Two new tests
forced an absent checkout binary despite a real isolated binary being supplied.
The failure was reproduced locally before fixing receiver-path resolution; no
mock positive or skip was substituted. Final receipt run39190686652 rechecks the
repair. Artifact/log blob downloads from GitHub were blocked by this environment's
proxy with403; GitHub status/annotation APIs and local complete reproductions were
available. Unread hosted log contents are not presented as inspected evidence.
