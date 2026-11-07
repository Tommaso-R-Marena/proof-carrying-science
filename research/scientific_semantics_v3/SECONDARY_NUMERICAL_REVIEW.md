# Independent review of the secondary numerical evaluation

The separately frozen **Chwirut2** project passed the narrow numerical reproduction test. The predetermined altered-table probe was **REFUTED**. This does not replace the primary scientific-semantics result of **14/22**, establish broad scientific understanding or validate the physical model.

This is an internal, AI-assisted independent source review. The source curator prepared annotations and the counterprobe from original source bytes without reading the repaired numerical checker or its output. No external domain expert participated.

## Freeze and provenance

The original NIST-format dataset was obtained from `lmfit/lmfit-py` commit `3a2439c2061ddeaf4cca8f99eb70a069e6a51a41`, path `NIST_STRD/Chwirut2.dat`. The direct NIST collection endpoint had returned HTTP 403 during source collection; mirror bytes were not independently compared with an accessible direct NIST download. The full original dataset and unchanged mirror BSD-3-Clause license are retained in `fixtures/secondary_numeric/`, alongside provenance, the predeclared reference protocol and the predetermined altered derivative.

- Original source SHA256: `968142c6f5427d87b1fed1e1bfc8cfce1f7ae8c6b89d3fbfb4960d7ced3c1e11`.
- Reference protocol SHA256: `38b2d73a2069098c7925dc3d1808d140d5ff3b0a3241e04c3fb2e0283101b2bd`.
- Source/reference manifest SHA256: `8db918d5255b417db7490caf7a7bb4a12eb7fa06b92279bc1281bab02537c8e3`.
- Runtime implementation commit: `04582fd89146a8aa31302c6e2c8aec00f6fcec4b`; committed pre-unlock freeze: `75310b56d9c6e4ea1ab47d50345aea7dc592744c`.

The coordinating run opened this source after that software freeze. The reviewer waited for its clean first output before running the already frozen corruption probe through the unchanged `numerical.reproduce` function. No runtime repair or retraining followed this secondary evaluation.

The pre-unlock context hash initially appeared inconsistent with the result. Independent comparison established that their **parsed context objects are exactly equal**. `51ba46234a7c8bfd1008568edcc8454d57a25d4a9d09dffbb4c90f5a4195d9ae` hashes the canonical JSON file **with a terminal newline**; `baf95e3f2f02781ce8e529c535e185a4b1cab7561d60065ff0a668103042128c` hashes canonical JSON **without** that newline. This is an encoding-label distinction, not a runtime, source, environment or trust-binding change. The original freeze event is retained.

## Actual numerical findings

| Field or check | Frozen source expectation | Observed outcome |
| --- | --- | --- |
| Observation count | 54 | 54 |
| Fitted parameter count | 3 | 3 |
| Residual degrees of freedom | 51 = 54 − 3 | 51 |
| Declared conditional mean | `exp(-b1*x)/(b2+b3*x)` | Exact expression retained; additive `e` excluded for fitted-mean prediction only |
| Fitted coefficients | Source-certified `b1`, `b2`, `b3` decimals | All three matched their separate typed parameter records |
| Reported RSS | `5.1304802941E+02` | Recomputed binary float `513.0480294068652` |
| Reported residual standard deviation | `3.1717133040E+00` | Recomputed `3.17171330395538` |
| Fresh checker replay | Same checker-owned numerical fields | Exact equality, excluding elapsed time and orchestration metadata |
| Predetermined corrupted first response | `92.9000E0` replaced by `192.9000E0`; reported statistics unchanged | **REFUTED**; recomputed RSS `12721.898800496814` |

The reported RSS relative discrepancy was approximately `6.11e-12`. Both reported statistics pass the independently frozen review tolerance `1e-8 + 1e-6 × abs(reported)`. They also pass the runtime's stricter relative tolerance `1e-7`; no gate was weakened.

The reviewer independently implemented the explicit source formula using 80-digit Python `Decimal` arithmetic, without using PCS's parser, evaluator or IR. The resulting RSS was:

```text
513.04802940686547049876301631532014235038678334188182253516597379101400805795313
```

It exactly matches the numerical receipt's 80-digit result. The independently computed residual standard deviation was:

```text
3.1717133039553808708732827144186455779579986827105155047226089794438333343462096
```

The independent formula implementation and PCS share the Python `Decimal` numerical library. This is independent expression reconstruction, not an independent transcendental library or certified error bound. Binary-float and Decimal RSS differed by approximately `2.27e-13`.

Sixteen source/computation/replay/counterprobe adjudication checks passed, with zero failed checks. Several are nested and correlated; they are not sixteen independent scientific claims or experiments. Detailed expected/observed values and raw clean/replay/corrupted results are retained in [evidence/secondary-numeric-independent-review.json](evidence/secondary-numeric-independent-review.json).

The review's initial draft compared the packet-wrapped result and direct function result as identical dictionaries. The packet adds a `source_sha256` field. That metadata distinction was isolated, documented and checked separately; the checker-owned numerical fields were already identical. No scientific protocol or result was changed to resolve this reviewer schema issue.

## What remains unestablished

The checker reports **UNSUPPORTED** for a rigorous transcendental interval enclosure. This negative result is retained. The two arithmetic implementations do not certify an error interval for `exp` or prove Python arithmetic refinement in Lean.

All tabulated predictors are positive, and the source-reported `b2` and `b3` are positive, so `b2+b3*x` is nonzero for these finite observations. No arbitrary-input domain theorem or physical domain inference is supplied. The source calls the predictor *metal distance* but specifies no length unit; millimetres were not inferred.

The dataset's additive error term does not establish independent, Gaussian or equal-variance errors. Parameter standard deviations, confidence intervals, uncertainty propagation, measurement calibration and statistical assumptions were not independently validated. Printed fitted coefficients are not proved globally or locally optimal. Agreement with residual statistics is finite computational reproduction, not physical adequacy or empirical confirmation of the underlying ultrasonic model.

The original 14/22 semantic result, its errors, all prior reference files and both original source freezes remain unchanged. No source was admitted for training, no model was promoted and no production authority was modified.

## Reproduction

From the repository root after installing the documented Python environment:

```python
from pathlib import Path
from research.scientific_semantics_v3.numerical import reproduce

root = Path("research/scientific_semantics_v3/fixtures/secondary_numeric")
clean = reproduce((root / "Chwirut2.dat").read_bytes())
corrupted = reproduce((root / "Chwirut2-corrupt-first-response.dat").read_bytes())
assert clean["status"] == "REPRODUCED_ROUNDED_COMPUTATION"
assert corrupted["status"] == "REFUTED"
```

Reproduction evaluates only the fixed supported mathematical fragment; it does not execute uploaded code or refit the scientific model.
