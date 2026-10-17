# Workstream D — Reviewer & Adoption

Independent evaluation materials for PCS reviewer adoption. This tree is
**additive evaluation infrastructure**. It does not modify `pcs/`, `formal/`,
`research/`, `site/`, or `.github/`, and it does **not** replace Lean/PCS
authority with local accept decisions.

| Task | Path | Purpose |
| --- | --- | --- |
| 15 | `workbench/` | Offline static HTML/report generator that inspects existing evidence |
| 16 | `blind_challenge/` | Synthetic blinded challenge cases + scoring protocol software |
| 17 | `tabletop/` | Offline incident / key-compromise tabletop simulator |
| 18 | `external_lab/` | External-laboratory deployment challenge package |

## Non-claims

- Does not issue PCS `ACCEPT` / `PASS` authority.
- Does not invent human blind-review results.
- Does not perform live credential rotation or key changes.
- Does not claim completed external laboratory validation.

## Quick start

```bash
# Task 15 — generate an offline reviewer report from fixture evidence
python -m independent_eval.reviewer_adoption.workbench.generate_report \
  --evidence independent_eval/reviewer_adoption/workbench/fixtures/sample_bundle \
  --out /tmp/pcs-reviewer-workbench-report.html

# Task 16 — blind a case packet and score a synthetic response sheet
python -m independent_eval.reviewer_adoption.blind_challenge.blind \
  --cases-dir independent_eval/reviewer_adoption/blind_challenge/cases \
  --out /tmp/pcs-blind-packet
python -m independent_eval.reviewer_adoption.blind_challenge.score \
  --ground-truth independent_eval/reviewer_adoption/blind_challenge/keys/ground_truth.json \
  --responses independent_eval/reviewer_adoption/blind_challenge/fixtures/sample_responses.json

# Task 17 — run an offline tabletop scenario (no live credentials)
python -m independent_eval.reviewer_adoption.tabletop.simulator \
  --scenario independent_eval/reviewer_adoption/tabletop/scenarios/compromised_signing_key.json \
  --responses independent_eval/reviewer_adoption/tabletop/fixtures/sample_responses_compromised_key.json

# Task 18 — print external-lab checklist and record config burden
python -m independent_eval.reviewer_adoption.external_lab.burden_tracker \
  --package independent_eval/reviewer_adoption/external_lab/package \
  --log /tmp/pcs-external-lab-burden.jsonl --list-steps

# Tests for this workstream only
python -m pytest -q independent_eval/reviewer_adoption/tests
```

See `NONOVERLAP.md`, `TEST_INVENTORY.md`, and `TECHNICAL_REPORT.md`.
