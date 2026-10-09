# PCS Omega experimental reasoning report

This report records actual CPU training and independently replayed Boolean search. It does not establish general scientific intelligence.

## Experiment

Seed: 20261010. Source: `a9b63f773f733ebf8d850fdf1b971dcf3c376d28`; dirty worktree: False. Exact Omega source digest: `bdf3a28808f5b3d3923f15560e8a20e2cd018f02f6bbf14bedc988c7fb4b0496`.
Dataset: {'train': 72, 'validation': 24, 'test': 96}. Fixed whole-family separation plus alpha-normalized source and truth-pair deduplication. First-party synthetic Apache-2.0 data; no participant data.
Models: weighted logistic heads (bag: 38 parameters; graph: 91); fixed two-round typed AST message passing; one-step REINFORCE bandit. Training times (seconds): {'bag': 0.9540293770005519, 'graph': 1.1575339559994973, 'bandit': 7.6952697930000795}.

## Held-out measurements

| Partition | Strategy | Checker budget | Solved / tasks | Mean checks | Search seconds |
|---|---|---:|---:|---:|---:|
| validation | bfs | 4 | 1 / 24 | 3.917 | 0.189 |
| validation | random | 4 | 6 / 24 | 3.833 | 0.190 |
| validation | structural | 4 | 24 / 24 | 2.000 | 0.159 |
| validation | bag | 4 | 1 / 24 | 3.917 | 0.271 |
| validation | bandit | 4 | 1 / 24 | 3.917 | 0.283 |
| validation | graph | 4 | 1 / 24 | 3.917 | 0.266 |
| validation | bfs | 8 | 24 / 24 | 4.875 | 0.204 |
| validation | random | 8 | 10 / 24 | 6.500 | 0.220 |
| validation | structural | 8 | 24 / 24 | 2.000 | 0.168 |
| validation | bag | 8 | 13 / 24 | 7.500 | 0.374 |
| validation | bandit | 8 | 14 / 24 | 7.375 | 0.316 |
| validation | graph | 8 | 2 / 24 | 7.750 | 0.332 |
| test | bfs | 4 | 11 / 96 | 4.000 | 1.148 |
| test | random | 4 | 29 / 96 | 3.688 | 1.074 |
| test | structural | 4 | 59 / 96 | 3.042 | 1.209 |
| test | bag | 4 | 12 / 96 | 3.917 | 1.555 |
| test | bandit | 4 | 12 / 96 | 3.812 | 1.626 |
| test | graph | 4 | 11 / 96 | 3.833 | 1.469 |
| test | bfs | 8 | 43 / 96 | 6.823 | 1.373 |
| test | random | 8 | 56 / 96 | 5.948 | 1.238 |
| test | structural | 8 | 64 / 96 | 4.469 | 1.272 |
| test | bag | 8 | 73 / 96 | 6.177 | 1.622 |
| test | bandit | 8 | 59 / 96 | 6.240 | 1.735 |
| test | graph | 8 | 52 / 96 | 6.729 | 1.753 |

## Comparisons and limits

- bag at 4 checks: solve-count difference -47 versus best sampled baseline structural.
- bandit at 4 checks: solve-count difference -47 versus best sampled baseline structural.
- graph at 4 checks: solve-count difference -48 versus best sampled baseline structural.
- bag at 8 checks: solve-count difference +9 versus best sampled baseline structural.
- bandit at 8 checks: solve-count difference -5 versus best sampled baseline structural.
- graph at 8 checks: solve-count difference -12 versus best sampled baseline structural.

No superiority is assumed; retain the strongest baseline when learning does not improve it. Check budgets include the initial counterexample check. Candidate truth comes exclusively from the independent checker. Public held-out generated families are not blind, external projects, novel mathematics or clinical validation.

Generated theorem targets: 52. Actual Lean suite checked: True. Inspect lean-result.json for actual theorem/axiom inventory when present. Original falsified target is an independent negative compilation control.

## Reproduce

```bash
pcs omega reproduce --output NEW_DIRECTORY --seed 20261010 --per-family 24 --epochs 24 --bandit-episodes 1600
pcs omega verify-lean NEW_DIRECTORY
```

Artifacts: corpus.json, models/*.json, bandit-training.json, evaluation.json, trajectories.json, memory.json, generated Lean templates, run.json. Authority remains NONE; interpretation grounding and registered scientific assurance stay open.
