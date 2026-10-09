# Counterexample-guided repair and a nonlinear model

This release changes the search architecture: a best-first frontier explores up to three constrained AST edits, keeps the original source interpretation immutable, and retains counterexamples from actual exhaustive Boolean checks. Previously checked assignments screen subsequent proposals. A failed witness rejects a proposal but cannot establish equivalence; every accepted repair receives a fresh exhaustive check.

A deterministic CPU trainer fits a 95 → 12 → 1 tanh MLP, including both layers and biases (1,165 parameters), with weighted logistic SGD over actual one-edit equivalence labels from training tasks only. The 91 graph features use the original fixed encoder; four additional syntax features express structural distance and exact syntactic repair. This is not an end-to-end GNN or a language model. The model changes proposal priority, never the checking decision.

## Fixed-setting evaluation

Each seed generates 72 training, 24 validation and 96 test tasks. Training uses only connective-confusion, negation-loss and swapped-implication. Validation uses nested-connective; test uses de-morgan, implication-expansion, distribution and absorption. Source alpha-normalization and semantic truth-pair fingerprints prevent duplicate tasks across splits within each seed. The full corpus is first-party synthetic Apache-2.0 data, with no participant records.

Settings fixed for all three seeds: 24 training epochs; checker budgets 4 and 8 (including initial check); depth 3; at most 128 examined repairs. Search may score up to 128 outgoing edits per expanded state: the examined-proposal cap is not a cap on all generated/ranked candidates. Both full calls and partial witness evaluations are counted. Wall times below include actual search and independent Python replay; model training is separately recorded. Reproduction did not select or tune on test outcomes.

| Seed | Full-check budget | BFS | Random | Structural | Bag | Fixed graph | Adaptive | Adaptive + nonlinear |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 20261009 | 4 | 18/96 | 35/96 | 63/96 | 14/96 | 26/96 | 78/96 | 84/96 |
| 20261009 | 8 | 51/96 | 54/96 | 68/96 | 73/96 | 66/96 | 91/96 | 86/96 |
| 20261010 | 4 | 11/96 | 29/96 | 59/96 | 12/96 | 11/96 | 80/96 | 90/96 |
| 20261010 | 8 | 43/96 | 56/96 | 64/96 | 73/96 | 52/96 | 84/96 | 95/96 |
| 20261011 | 4 | 15/96 | 32/96 | 57/96 | 13/96 | 17/96 | 79/96 | 89/96 |
| 20261011 | 8 | 43/96 | 55/96 | 66/96 | 73/96 | 61/96 | 83/96 | 94/96 |

The adaptive architecture improves solve counts over the strongest previous strategy on these particular task sets at both budgets. The nonlinear model improves the adaptive four-call result on all three seeds and the eight-call result on two seeds; it loses to adaptive alone on the first eight-call seed. The default uses adaptive symbolic search; the trained model remains an explicitly selectable, experimental option.

Extra computation matters: these strategies screen and rank more proposals than the previous breadth-first implementation. Equal full-check budgets are not equal total evaluations, energy or wall time. `evaluation.json` retains per-task solve outcomes, full checks, examined proposals, partial witness tests and measured wall time. The website publishes its complete row summaries. Training provenance binds actual task IDs, task digests, corpus and Omega Python source. Hashes identify artifacts, not authenticated scientific authority.

## Reproduction and trust limits

```sh
pcs omega adaptive-reproduce --output NEW_DIRECTORY
pcs omega adaptive-train corpus.json --output model.json
pcs omega adaptive-search task.json --model model.json --output episode.json
pcs omega adaptive-replay episode.json
```

The retained `Repairs.lean` contains independently compilable Boolean equalities from the adaptive eight-call test solutions. Lean 4.28.0 compiled all 258 targets with empty axiom inventories and rejected the false original. Compilation and the exact axiom inventory are reported in `lean-result.json`; no browser kernel execution is claimed. These generated statements establish only the selected Boolean equalities. The experiment does not prove a refinement theorem from Python or JavaScript implementation to Lean, validate scientific interpretations, certify a deployed AI, or establish external scientific transfer. Public correlated families and possible overlap across seeds do not constitute independent blind problems. No new theorem about science or general intelligence is claimed.

Validation is a fixed family evaluation, not a model-selection set in this reproduction. Retained v1 checkpoints/results are unchanged. No paid services, participant fabrication or financial information are involved.
