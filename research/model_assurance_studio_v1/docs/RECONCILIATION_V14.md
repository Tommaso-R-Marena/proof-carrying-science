# Current studio reconciliation

This integrates the actual v0.13 head of draft PR #196, preserving its model samples, evidence and restricted semantics. It also includes the core Lean-action update from #197. It changes no production PCS authority, signing root, existing formal theorem or model weights.

## What works

The local studio accepts supported model/scientific files and reports scoped PASS, FAIL or OPEN findings. The exact-rational and binary32 certificate routes, independent protobuf comparison and reviewer-pinned operating regions remain separate from production PCS certificates. An unknown or unsupported case abstains.

The current local suite passed **329 tests and 397 nested subtests, with zero skips**, using NumPy 2.2.6, CPU PyTorch 2.7.1, protobuf 6.33.6, cryptography 47.0.0 and genuine official ONNX Runtime 1.31.1. The exact validation packages are recorded in `requirements-validation.lock`; CPU dependencies reuse the protected repository's `requirements-prover.lock`.

## Confirmed defects and repairs

- The original generated Lean files put module documentation before `import Mathlib`. Lean 4.28.0 rejects that order. `checked_export_v14` moves the single import first, leaving all mathematical hypotheses, statements and proof bodies unchanged. Original v0.6/v0.7 source artifacts and deterministic legacy generation remain unchanged.
- `lean_status_v07` now requires the qualified Lean/Lake binary digests and locked Mathlib revision, compiles the exact generated source and independently audits every named theorem. Admissions, custom axioms, unsafe shortcuts, wrong imports, unexpected theorem sets and changed source/tool bytes cannot return a positive result. This is not a hostile-source sandbox.
- ULP distance incorrectly ordered negative numbers across zero. The monotone encoding now treats signed zeros as the same value and measures the two adjacent subnormal values across zero at distance two. Actual regression tests cover both directions.
- A missing-dependency test assumed `python -S` removes explicit `PYTHONPATH`. It now explicitly clears that path in the real negative subprocess. No positive verifier result is mocked.

## Genuine new validation

Both import-first proof successors compile under qualified Lean 4.28.0 with Mathlib revision `8f9d9cff6bd728b17a24e163c9402775d9e6a365`. The named checks are `certified_relation`, `certified_update_drift` and `bounded_update_composition` (the last appears in both files). Dependencies are standard `propext`, `Classical.choice`, `Quot.sound`; no custom axiom or admission is accepted.

These proofs say that the exported **abstract linear hypotheses imply the output inequality**. The kernel does not establish that the ONNX parser, abstract interpreter, source model or physical runtime supplies those hypotheses. The model/certificate/policy hashes remain implementation/provenance bindings.

Four actual ONNX Runtime CPU sessions ran 64 vectors each, with optimizations disabled and one sequential CPU thread. Across 640 scalar outputs:

| Model | Nonidentical results | Maximum ULP difference |
| --- | ---: | ---: |
| Dense violation fixture | 0/128 | 0 |
| Trained Iris baseline | 83/192 | 44 |
| Trained Iris update | 84/192 | 44 |
| Correlated-output fixture | 0/128 | 0 |

**167 outputs differed from the specified sequential nonfused reference.** These finite observations refute equality on those sampled computations; they do not alone show a violation of a reviewer-approved property. The probe domain is not restricted to the approved Iris regions. Do not transfer Python rounding proofs into an official-runtime guarantee. Graph-optimization settings do not prove kernel-level arithmetic equivalence.

`validation/reconciliation_v14/report.json` contains exact source/model/tool hashes, named audits, dependency versions and numerical counterexamples. Historical reports claiming NOT_RUN or NOT_ESTABLISHED remain historical; they were not overwritten.

## Reproduce

From repository root, use Python 3.12 on Linux x86-64:

```sh
python -m pip install --require-hashes -r requirements-prover.lock -r research/model_assurance_studio_v1/requirements-validation.lock
cd research/model_assurance_studio_v1
python -m pytest -q tests
python -S scripts/verify_v07_release.py
cd ../..
source scripts/activate_lean_428.sh
lake exe cache get
python research/model_assurance_studio_v1/scripts/reproduce_reconciliation_v14.py --output /tmp/new-studio-validation --require-kernel --require-ort
```

The output directory must be new. The dedicated research CI repeats these actual checks; a missing kernel or official runtime fails the required validation command rather than counting as a pass. Compiler/library and host trust remain explicit. No independent key custody, immutable execution root, universal runtime equivalence, blind generalization, biological validity or general AI-safety guarantee is established.


For a new independently checked certificate, use the corrected exporter from the studio directory. It verifies the supplied Python certificate first, writes exclusively to a new file, and only reports a kernel verdict when the real qualified tool succeeds:

```sh
python -m studio.checked_export_v14 relation samples/demo_trained_iris_mlp.onnx validation/v06_iris_property_1_certificate.json validation/v06_iris_property_1_reviewer_policy.json /tmp/new-reviewed-proof.lean --check --project-dir ../..
```

Without `--check`, the result explicitly remains `SOURCE_EXPORTED_NOT_KERNEL_CHECKED`. Invalid certificates cannot generate source, and existing source files cannot be overwritten.
