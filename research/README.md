# PCS research guide

Use the [root README](../README.md) for installation and production verification.
Research results below retain explicit finite models, assumptions and host trust
boundaries. A checked theorem, implementation correspondence, empirical utility
and independent external validation are separate claims.

| Start here | Capability and evidence |
|---|---|
| [Public-study actual-weight evaluation](public_study_validation_v1_results/README.md) | 72 fresh Qwen responses, five published attack templates, failures retained, 72 guarded episodes and 72 fresh receiving replays; current hardened receiving command |
| [Canonical action laboratory](structured_action_lab_v4/README.md) | Recorded/fresh model modes, exact token/byte parsing, corrected proposals and visual reports |
| [Token policy gate](token_policy_gate_v5/README.md) | Kernel-checked token/byte/selection binding and controller-version budget proofs; recorded-response replay |
| [Progress supervisor](progress_supervisor_v1/README.md) | Fixed native Lean/SQLite safe-progress, row refinement, receipts and replay |
| [Scientific authority](scientific_authority_v2/README.md) | Typed scientific-history receiving and explicit authority boundaries |
| [Scientific engines](scientific_engines_v1/README.md) | Independently checked bounded engines with source provenance |
| [Transport counterexamples](transport_invariant_counterexamples_v1/README.md) | Exact counterexamples to insufficient transport summaries |
| [Flux Detective](flux_detective_v1/README.md) and [Flux Forge](flux_forge_v1/README.md) | Replayable visual scientific puzzles and exact finite transport claims |
| [Trace lab](trace_lab_v1/README.md) | Offline full-trace inspection and source-bound evidence |
| [Combined source qualification](integration_v2/README.md) | Exact PR/path/file/mode census; reviewed successor contract |
| [Independent evaluations](../independent_eval/README.md) | Separate reviewer, falsification, protocol and reproducibility projects |

## Reproduce the latest public-study receiving result

From a clean committed repository with the frozen Python requirements and pinned
Lean 4.28.0 available:

```sh
source scripts/activate_lean_428.sh
python -m research.integration_v2.reconcile --require-committed
python -m pytest -q research/public_study_validation_v1/test_study.py
PYTHONPATH=. python research/public_study_validation_v1_results/receiving.py \
  research/public_study_validation_v1_results/recorded/producer /tmp/new-study-receiver
PCS_PUBLIC_STUDY_EVIDENCE=research/public_study_validation_v1_results/recorded/producer \
  python -m pytest -q research/public_study_validation_v1_results/test_recorded_evidence.py
```

Existing output paths refuse. Receiving performs actual native Lean/SQL replay;
it does not load model weights, re-run generation or independently attest that
recorded neural computation occurred. The report separately documents pinned
weight downloads and fresh generation. Use `public_study_validation_v1_results/receiving.py`,
which freezes metadata from the exact bytes it hashes, in place of the historical
v1 receiving command in the frozen generation package's README.

## Versioned and historical instructions

Source-bound READMEs, upstream model cards/licenses, vendor files and earlier
qualification reports retain their original bytes. Their original branch-specific
preservation commands intentionally refuse a different combined tree. The current
combined workflow selects `research.integration_v2.boundary` and the pinned whole
source contract; it never changes an old guard to assert a false predicate.
Historical assertion tests run unchanged in their exact original Git context with
separate before/after qualification of the current combined checkout.

The [README audit](../docs/integration/2026-10-29/README_AUDIT.json) records every
README and its current-entry-point or preserved-versioned status. Source snapshots
are evidence, not a claim that an old experiment is the latest result. The current
[publication status](../docs/integration/2026-10-29/README.md) records hosted CI and
protected integration separately from historical local qualification.

PR #117 remains held. Isolated PGSI1/PGSC research is not a production self-modifying
system; its formal modules and current trust assumptions remain intact. Final
Aristotle V8 outputs require their own exact-source intake and independent check.
No untrusted generation trace is training data. Same-host process separation,
hashes and sealed snapshots do not create an independently administered root.
