# Technical report — Workstream D (reviewer & adoption)

## Scope

Tasks 15–18 under `independent_eval/reviewer_adoption/` only. Additive
evaluation infrastructure. Does not modify `pcs/`, `formal/`, `research/`,
`site/`, or `.github/`.

## Task 15 — Offline reviewer workbench

`workbench/inspect_evidence.py` walks a directory for certificates, receipts,
intake locks, and `LIMITATIONS.md`. It extracts claims, assumptions, artifact
identities (including on-disk SHA-256 when missing), and **reported** outcomes.

`workbench/generate_report.py` emits accessibility-minded static HTML (skip
link, focus outlines, reduced-motion, responsive tables) plus a companion
`.inspection.json`. The payload always includes `workbench_issues_accept: false`.

**Non-authority:** the workbench never sets ACCEPT/PASS; badges are labeled as
source-reported.

## Task 16 — Blind challenge

Seven synthetic cases under `blind_challenge/cases/` cover:

| Case | Category |
| --- | --- |
| BC-01 | Valid computational |
| BC-02 | Invalid / rejected (bad signature) |
| BC-03 | Computationally valid, scientifically unsupported interpretation |
| BC-04 | Crypto-valid without formal justification |
| BC-05 | Formal computational + declared empirical validation |
| BC-06 | Unsupported interpretation only |
| BC-07 | Rejected (hash mismatch despite outer signature) |

`keys/ground_truth.json` holds blinded labels separately. `blind.py` strips
label keys and writes a packet + response template. `score.py` compares a
response sheet to ground truth and sets
`human_review_results_invented: false`. The sample response sheet is explicitly
a **synthetic automated scorer fixture**, not human performance.

Distinction dimensions scored: cryptographic validity, formally justified
computational claims, empirically validated claims, unsupported interpretation,
outright rejected evidence, plus overall category.

## Task 17 — Tabletop

Seven offline scenarios: compromised signing key, stale verifier, corrupted
archive, lost commitment, dependency substitution, disclosure, conflicting
receipts. `simulator.py` merges a scenario with a response sheet into an
after-action JSON, refuses live credential/infra flags, and scans for forbidden
action markers. Fixture response sheets are synthetic and labeled as such.

## Task 18 — External lab kit

`external_lab/package/` provides SETUP, WORKFLOW, VERIFY, REPRO, LIMITATIONS,
TROUBLESHOOTING, SUCCESS_FAILURE, plus `CHECKLIST.json`. WORKFLOW points
read-only at repo `examples/` and local fixtures without copying large trees.
`burden_tracker.py` prints the checklist (`--list-steps`) and appends JSONL
entries that explicitly **do not** claim completed external-lab validation.

## Results policy

No human blind-review accuracy numbers are reported. No completed external
laboratory validation is claimed. Smoke outputs under `/tmp` or
`results/work/` are ephemeral.

## How to run

See `README.md` and `TEST_INVENTORY.md`.
