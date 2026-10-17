# Test inventory — Workstream D

| Suite | Scope |
| --- | --- |
| `tests/test_workbench.py` | Evidence inspection + claim-strength lattice + HTML/JSON export + CLI cross-check (agree/disagree/skip/fixture-inconclusive); asserts non-authority |
| `tests/test_export_assurance_card.py` | Discover/subprocess bridge to Workstream F; ABSENT exit 3 ≠ PASS; PRESENT monkeypatched export |
| `tests/test_blind_challenge.py` | Blind packet strips labels; scorer on synthetic fixture; refuses unattested human study |
| `tests/test_tabletop.py` | Scenario catalog; compromised-key fixture passes offline; live-cred flag rejected |
| `tests/test_external_lab.py` | Checklist forbids EXTERNAL_VALIDATION_COMPLETE; burden log never claims validation |

```bash
python3 -m pytest -q independent_eval/reviewer_adoption/tests
```

Latest local run: **22 passed** (workbench + F export bridge ABSENT/PRESENT + blind/tabletop/lab).

## Smoke commands

```bash
python3 -m independent_eval.reviewer_adoption.workbench.generate_report \
  --evidence independent_eval/reviewer_adoption/workbench/fixtures/sample_bundle \
  --out /tmp/pcs-reviewer-workbench-report.html \
  --format both --cli-crosscheck

python3 -m independent_eval.reviewer_adoption.blind_challenge.blind \
  --cases-dir independent_eval/reviewer_adoption/blind_challenge/cases \
  --out /tmp/pcs-blind-packet

python3 -m independent_eval.reviewer_adoption.blind_challenge.score \
  --ground-truth independent_eval/reviewer_adoption/blind_challenge/keys/ground_truth.json \
  --responses independent_eval/reviewer_adoption/blind_challenge/fixtures/sample_responses.json

python3 -m independent_eval.reviewer_adoption.tabletop.simulator \
  --scenario independent_eval/reviewer_adoption/tabletop/scenarios/compromised_signing_key.json \
  --responses independent_eval/reviewer_adoption/tabletop/fixtures/sample_responses_compromised_key.json

python3 -m independent_eval.reviewer_adoption.external_lab.burden_tracker \
  --package independent_eval/reviewer_adoption/external_lab/package \
  --log /tmp/pcs-external-lab-burden.jsonl --list-steps
```

## Explicit non-tests

- No human blind-review accuracy claims
- No live credential rotation
- No completed external-lab validation assertions
