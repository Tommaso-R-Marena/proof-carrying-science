# PCS Omega experimental reasoning report

This report records actual CPU training and independently replayed Boolean search. It does not establish general scientific intelligence.

## Experiment

Seed: 20261009. Source: `71601011781d833886c207a1d9a1593acf67ad24`; dirty worktree: False. Exact Omega source digest: `b84d3a7dcb668ec0f8ff58584a7281bd8d1550ee0463c92b02e03ea01224dff5`.
Dataset: {'train': 72, 'validation': 24, 'test': 96}. Fixed whole-family separation plus alpha-normalized source and truth-pair deduplication. First-party synthetic Apache-2.0 data; no participant data.
Models: weighted logistic heads (bag: 38 parameters; graph: 91); fixed two-round typed AST message passing; one-step REINFORCE bandit. Training times (seconds): {'bag': 1.0135602520003886, 'graph': 1.0808293449999837, 'bandit': 7.401160438999796}.

## Held-out measurements

| Partition | Strategy | Checker budget | Solved / tasks | Mean checks | Search seconds |
|---|---|---:|---:|---:|---:|
| validation | bfs | 4 | 0 / 24 | 4.000 | 0.159 |
| validation | random | 4 | 4 / 24 | 3.875 | 0.155 |
| validation | structural | 4 | 24 / 24 | 2.000 | 0.140 |
| validation | bag | 4 | 0 / 24 | 4.000 | 0.210 |
| validation | bandit | 4 | 0 / 24 | 4.000 | 0.226 |
| validation | graph | 4 | 0 / 24 | 4.000 | 0.225 |
| validation | bfs | 8 | 24 / 24 | 5.000 | 0.176 |
| validation | random | 8 | 10 / 24 | 6.667 | 0.210 |
| validation | structural | 8 | 24 / 24 | 2.000 | 0.146 |
| validation | bag | 8 | 1 / 24 | 8.000 | 0.312 |
| validation | bandit | 8 | 17 / 24 | 7.375 | 0.296 |
| validation | graph | 8 | 1 / 24 | 8.000 | 0.303 |
| test | bfs | 4 | 18 / 96 | 3.979 | 1.049 |
| test | random | 4 | 35 / 96 | 3.708 | 1.000 |
| test | structural | 4 | 63 / 96 | 2.969 | 1.103 |
| test | bag | 4 | 14 / 96 | 3.719 | 1.306 |
| test | bandit | 4 | 16 / 96 | 3.688 | 1.383 |
| test | graph | 4 | 26 / 96 | 3.552 | 1.386 |
| test | bfs | 8 | 51 / 96 | 6.479 | 1.264 |
| test | random | 8 | 54 / 96 | 5.865 | 1.186 |
| test | structural | 8 | 68 / 96 | 4.260 | 1.200 |
| test | bag | 8 | 73 / 96 | 6.167 | 1.606 |
| test | bandit | 8 | 65 / 96 | 5.906 | 1.768 |
| test | graph | 8 | 66 / 96 | 5.500 | 1.560 |

## Comparisons and limits

- bag at 4 checks: solve-count difference -49 versus best sampled baseline structural.
- bandit at 4 checks: solve-count difference -47 versus best sampled baseline structural.
- graph at 4 checks: solve-count difference -37 versus best sampled baseline structural.
- bag at 8 checks: solve-count difference +5 versus best sampled baseline structural.
- bandit at 8 checks: solve-count difference -3 versus best sampled baseline structural.
- graph at 8 checks: solve-count difference -2 versus best sampled baseline structural.

No superiority is assumed; retain the strongest baseline when learning does not improve it. Check budgets include the initial counterexample check. Candidate truth comes exclusively from the independent checker. Public held-out generated families are not blind, external projects, novel mathematics or clinical validation.

Generated theorem targets: 66. Actual Lean suite checked: True. Inspect lean-result.json for actual theorem/axiom inventory when present. Original falsified target is an independent negative compilation control.

## Reproduce

```bash
pcs omega reproduce --output NEW_DIRECTORY --seed 20261009 --per-family 24 --epochs 24 --bandit-episodes 1600
pcs omega verify-lean NEW_DIRECTORY
```

Artifacts: corpus.json, models/*.json, bandit-training.json, evaluation.json, trajectories.json, memory.json, generated Lean templates, run.json. Authority remains NONE; interpretation grounding and registered scientific assurance stay open.
