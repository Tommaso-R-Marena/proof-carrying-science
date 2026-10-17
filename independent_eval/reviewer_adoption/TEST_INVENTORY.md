# Test inventory — Workstream D

| Suite | Scope |
| --- | --- |
| `tests/test_workbench.py` | Evidence inspection + HTML generation; asserts non-authority |
| `tests/test_blind_challenge.py` | Blind packet strips labels; scorer matches synthetic fixture only |
| `tests/test_tabletop.py` | Simulator offline constraints + field coverage on fixtures |
| `tests/test_burden_tracker.py` | `--list-steps` checklist + JSONL append |

```bash
python3 -m pytest -q independent_eval/reviewer_adoption/tests
```

## Smoke commands (not human performance)

```bash
python3 -m independent_eval.reviewer_adoption.workbench.generate_report \
  --evidence independent_eval/reviewer_adoption/workbench/fixtures/sample_bundle \
  --out /tmp/pcs-reviewer-workbench-report.html

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
- No live credential rotation tests
- No completed external-lab validation assertions
