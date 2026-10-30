# Technical report — Independent eval Workstream C

**Branch:** `feature/independent-eval-repro-tcb-c8bb`  
**Scope:** `independent_eval/repro_tcb/**` only (read-only toward `formal/` and `pcs/`)  
**Tasks:** 12–14

## Summary

Workstream C adds an independent reproducibility and TCB audit package that treats
PCS as a system under test. It does not modify production Lean or Python, does not
touch PRs #117/#120, and does not alter CI.

## Task 12 — Cross-environment reconstruction harness

Module: `python_harness/reconstruction.py`

- Builds deterministic synthetic evidence members and a canonical `ZIP_STORED` archive.
- Modes:
  - `identical_archive_replay` — same archive bytes verified in fresh directories
  - `regenerated_archive` — members re-packed with canonical rules (byte-identical)
  - `regenerated_noncanonical` — same members, different DOS timestamp (byte-different, digest-stable members)
- Records git commit/describe, platform, Lean toolchain pin, cryptography version,
  interpreter paths + SHA-256, and per-interpreter archive digests.
- Campaign summary: `results/reconstruction_campaign.json`

**Finding:** Identical-archive replay preserves ZIP SHA-256. Regenerating with
noncanonical ZIP metadata preserves member digests but **not** archive identity.
Callers must not conflate “same evidence members” with “same handoff object.”

## Task 13 — Trusted computing base dependency atlas

Module: `python_harness/tcb_atlas.py`

Machine-readable graph (`results/tcb_atlas.json`) for the chain:

`source_bytes → os_io → zip_archive → crypto → python → transcripts → lean_authority → reviewer_policy → verification_output`

Each node carries a trust class:

| Class | Examples |
| --- | --- |
| `kernel-proved` | Lean authority / proved parser-codec obligations |
| `executable-tested` | SHA-256/Ed25519 Lean specs + KATs; transcripts |
| `cryptographically-assumed` | collision resistance, unforgeability, `ProductionRefinesLean`, ZIP faithfulness |
| `externally-trusted` | OS I/O, Lean foundation axioms, Python runtime, reviewer policy, scientific predicates |
| `unresolved` | environment reconstruction fidelity (Lean `notApplicable`) |

The atlas **reads** `formal/PCS/V2/TCB.lean` and probes hashes of key formal/pcs
files. It never writes Lean.

## Task 14 — Independent evidence traceability auditor

Module: `python_harness/traceability.py`

Parses claims of the form `**Claim ID**: text` with typed links
(`commit` / `theorem` / `test` / `hash` / `assumption`) and classifies each claim:

- **supported** — all links resolve to catalog evidence
- **unsupported** — no links or none resolve
- **stale** — `expected_commit` disagrees with current HEAD
- **ambiguous** — mixed resolve status, assumption-only anchors, or universal language without a theorem

Fixture `fixtures/claims/sample_claims_report.md` deliberately includes one of each
flag class for regression.

## How to run

```bash
PYTHONPATH=independent_eval/repro_tcb python -m python_harness run-all
python -m pytest independent_eval/repro_tcb/tests -q
```

## Non-claims

This package does not assert production readiness, clinical validity, or absence of
residual TCB. See `OPEN_TRUST_ASSUMPTIONS.md` and `NONOVERLAP.md`.
