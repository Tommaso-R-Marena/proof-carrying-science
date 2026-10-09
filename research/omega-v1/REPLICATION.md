# Fixed-setting Omega replication

Three seeds use the same 24 tasks per family, 24 logistic epochs and 1,600 one-step bandit episodes. No parameters were changed after viewing holdout results. The website retains the original checkpoint. This is a generated-family robustness check, not independent external scientific validation.

| Seed | Budget | BFS | Random | Structural | Bag | Graph | Bandit |
|---|---:|---:|---:|---:|---:|---:|---:|
| 20261009 | 4 | 18 | 35 | 63 | 14 | 26 | 16 |
| 20261009 | 8 | 51 | 54 | 68 | 73 | 66 | 65 |
| 20261010 | 4 | 11 | 29 | 59 | 12 | 11 | 12 |
| 20261010 | 8 | 43 | 56 | 64 | 73 | 52 | 59 |
| 20261011 | 4 | 15 | 32 | 57 | 13 | 17 | 18 |
| 20261011 | 8 | 43 | 55 | 66 | 73 | 61 | 53 |

Every cell is solved / 96 test tasks. Bag solves 73/96 at eight calls on all three seeds, versus structural 68, 64 and 66. At four calls all learned models lose. Graph and bandit lose to structural at eight calls on every seed. This negative graph ablation does not support adding a larger graph model without better tasks or features.

Actual Lean targets compiled: 179 across runs (66, 52, 61); all have empty axiom inventories, and all three false-original controls were rejected.

Each run retains its source commit, source fingerprint, actual checkpoints, corpus, complete trajectories, reward trace, per-task results and theorem/axiom evidence. Repeated task families and possible cross-seed overlap prevent treating aggregate counts as independent samples. Source fingerprint portability was hardened after the original run; later runs correctly record the newer clean source commit.
