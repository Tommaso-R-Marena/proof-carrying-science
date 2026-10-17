# Technical report — Workstream D (reviewer & adoption)

## Scope

Tasks 15–18 under `independent_eval/reviewer_adoption/` only. Additive
evaluation infrastructure. Does not modify `pcs/`, `formal/`, `research/`,
`site/`, or `.github/`. No top-level `independent_eval/__init__.py` (avoid
cross-PR overlap); imports use the namespace package from the repo root.

## Task 15 — Offline reviewer workbench

`workbench/inspect_evidence.py` extracts claims, assumptions, artifact
identities, and **reported** outcomes from certificates/receipts. Each claim
also receives an `inspection_class` from a claim-strength lattice
(`cryptographic_validity`, `computationally_supported`,
`empirically_unsupported`, `scientific_adequacy_open`, `rejected_or_failed`,
`unknown_or_ambiguous`). These labels are workbench heuristics over
`reported_*` fields only — never PCS authority. Payload includes
`claim_strength_summary` counts and always `workbench_issues_accept: false`.

`workbench/generate_report.py` accepts `--format html|json|both` (default
`both`). HTML shows strength class per claim (captioned table + definition-list
summary) with skip-link and focus-visible styles; JSON export is the inspection
dict plus `generated_at`. Workbench never issues ACCEPT/PASS.

## Task 16 — Blind challenge

Seven synthetic labeled cases under `blind_challenge/cases/` cover valid
computational, invalid/rejected, computationally valid but scientifically
unsupported, crypto-valid without formal justification, empirical+computational,
unsupported interpretation, and hash-mismatch rejection.

`keys/ground_truth.json` holds sealed labels. `blind.py` strips
`ground_truth_label` / `expected_*` fields and writes a reviewer packet
(facilitator map kept separate). `score.py` scores supplied response sheets
only; refuses unattested `human_study=true`. Fixture
`fixtures/sample_responses.json` is synthetic and intentionally includes one
incorrect judgment — not human performance.

Distinction dimensions (via labels / `distinction_tags`): cryptographic
validity, formally justified computational claims, empirically validated
claims, unsupported interpretations, outright rejected evidence.

## Task 17 — Tabletop

Seven offline scenarios (compromised key, stale verifier, corrupted archive,
lost commitment, dependency substitution, disclosure, conflicting receipts).
`simulator.py` scores response sheets with keyword heuristics, forbids
`live_credential_changes_performed=true`, and never mutates credentials.

## Task 18 — External lab kit

`external_lab/package/` documents SETUP/WORKFLOW/VERIFY/REPRO/LIMITATIONS/
TROUBLESHOOTING/SUCCESS_FAILURE plus checklist JSON forbidding
`EXTERNAL_VALIDATION_COMPLETE`. `burden_tracker.py` lists steps and appends
JSONL entries with `completed_external_lab_validation: false`.

## Non-claims

- No invented human blind-review results
- No completed external-lab validation claim
- No live credential or infrastructure changes
- No workbench ACCEPT/PASS authority
