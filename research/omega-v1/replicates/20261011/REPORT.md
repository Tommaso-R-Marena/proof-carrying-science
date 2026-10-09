# PCS Omega experimental reasoning report

This report records actual CPU training and independently replayed Boolean search. It does not establish general scientific intelligence.

## Experiment

Seed: 20261011. Source: `a9b63f773f733ebf8d850fdf1b971dcf3c376d28`; dirty worktree: False. Exact Omega source digest: `bdf3a28808f5b3d3923f15560e8a20e2cd018f02f6bbf14bedc988c7fb4b0496`.
Dataset: {'train': 72, 'validation': 24, 'test': 96}. Fixed whole-family separation plus alpha-normalized source and truth-pair deduplication. First-party synthetic Apache-2.0 data; no participant data.
Models: weighted logistic heads (bag: 38 parameters; graph: 91); fixed two-round typed AST message passing; one-step REINFORCE bandit. Training times (seconds): {'bag': 1.0335635789997468, 'graph': 1.2192280839999512, 'bandit': 8.796958364999227}.

## Held-out measurements

| Partition | Strategy | Checker budget | Solved / tasks | Mean checks | Search seconds |
|---|---|---:|---:|---:|---:|
| validation | bfs | 4 | 0 / 24 | 4.000 | 0.162 |
| validation | random | 4 | 7 / 24 | 3.667 | 0.145 |
| validation | structural | 4 | 24 / 24 | 2.000 | 0.145 |
| validation | bag | 4 | 0 / 24 | 4.000 | 0.222 |
| validation | bandit | 4 | 0 / 24 | 4.000 | 0.274 |
| validation | graph | 4 | 0 / 24 | 4.000 | 0.220 |
| validation | bfs | 8 | 24 / 24 | 5.000 | 0.180 |
| validation | random | 8 | 11 / 24 | 6.292 | 0.206 |
| validation | structural | 8 | 24 / 24 | 2.000 | 0.146 |
| validation | bag | 8 | 23 / 24 | 7.125 | 0.291 |
| validation | bandit | 8 | 17 / 24 | 7.125 | 0.310 |
| validation | graph | 8 | 0 / 24 | 8.000 | 0.355 |
| test | bfs | 4 | 15 / 96 | 3.958 | 1.137 |
| test | random | 4 | 32 / 96 | 3.635 | 1.078 |
| test | structural | 4 | 57 / 96 | 3.062 | 1.204 |
| test | bag | 4 | 13 / 96 | 3.771 | 1.415 |
| test | bandit | 4 | 18 / 96 | 3.854 | 1.534 |
| test | graph | 4 | 17 / 96 | 3.844 | 1.552 |
| test | bfs | 8 | 43 / 96 | 6.646 | 1.423 |
| test | random | 8 | 55 / 96 | 5.885 | 1.343 |
| test | structural | 8 | 66 / 96 | 4.458 | 1.316 |
| test | bag | 8 | 73 / 96 | 6.042 | 1.699 |
| test | bandit | 8 | 53 / 96 | 6.385 | 1.811 |
| test | graph | 8 | 61 / 96 | 6.156 | 1.798 |

## Comparisons and limits

- bag at 4 checks: solve-count difference -44 versus best sampled baseline structural.
- bandit at 4 checks: solve-count difference -39 versus best sampled baseline structural.
- graph at 4 checks: solve-count difference -40 versus best sampled baseline structural.
- bag at 8 checks: solve-count difference +7 versus best sampled baseline structural.
- bandit at 8 checks: solve-count difference -13 versus best sampled baseline structural.
- graph at 8 checks: solve-count difference -5 versus best sampled baseline structural.

No superiority is assumed; retain the strongest baseline when learning does not improve it. Check budgets include the initial counterexample check. Candidate truth comes exclusively from the independent checker. Public held-out generated families are not blind, external projects, novel mathematics or clinical validation.

Generated theorem targets: 61. Actual Lean suite checked: True. Inspect lean-result.json for actual theorem/axiom inventory when present. Original falsified target is an independent negative compilation control.

## Reproduce

```bash
pcs omega reproduce --output NEW_DIRECTORY --seed 20261011 --per-family 24 --epochs 24 --bandit-episodes 1600
pcs omega verify-lean NEW_DIRECTORY
```

Artifacts: corpus.json, models/*.json, bandit-training.json, evaluation.json, trajectories.json, memory.json, generated Lean templates, run.json. Authority remains NONE; interpretation grounding and registered scientific assurance stay open.
