# AION — certified rare-event sandwiches for infinite-state reaction networks

AION is a Lean 4 / Mathlib and Python research prototype. For a mass-action stochastic
reaction network on the infinite state space \(\mathbb N^d\), it produces **exact rational lower and upper bounds**
\[ L \le P_{x_0}(\text{reach } B \text{ before } A) \le U \]
for rare hitting events. Each bound comes with a certificate that a small checker can
verify. The checker was **proved sound in Lean**. A Python mirror of it also exists.

Headline demonstration (`RequestProject/AION/Examples/XYmain.lean`): a two-species network
(self-replicating `X`, with its degradation catalysed by a fluctuating enzyme `Y`) where **both species are
unbounded**. Lean certifies
`3.90698e-8 ≤ P_(1,10)(X reaches 30 before extinction) ≤ 3.90699e-8`
(a relative gap of about \(3\times10^{-7}\)). The bound holds for the *infinite* chain, not for a truncation.
The proof uses `native_decide` (it trusts the Lean compiler; see `docs/TRUST_BOUNDARIES.md`).

## What is where

| Path | Content |
|---|---|
| `RequestProject/AION/Core.lean` | jump models, generator, hitting probabilities (`hitProb` as a least fixed point) |
| `RequestProject/AION/Barrier.lean` | barrier upper bound, Lyapunov-certified lower bound, mean exit-time bounds, sandwich |
| `RequestProject/AION/Composition.lean` | gluing, maximum principle, relative-error transfer, compositional union bound, robust affine families |
| `RequestProject/AION/MassAction.lean` | mass-action CRNs, exact exponential factorisation, falling-factorial orthant check |
| `RequestProject/AION/Checker.lean` | executable certificate checkers `checkUpper`/`checkLower` with soundness proofs |
| `RequestProject/AION/PathSemantics.lean` | `hitN` equals an explicit path-sum probability |
| `RequestProject/AION/NegativeResults.lean` | formal counterexamples (missing escape condition, failure of the Leibniz rule, recurrence) |
| `RequestProject/AION/Examples/` | symbolic birth–death formula; four concrete certificates checked in Lean |
| `RequestProject/AION/AxiomAudit.lean` | `#print axioms` for all headline theorems (output in `results/axiom_audit.txt`) |
| `python/aion/` | CRN model, exact checker, untrusted synthesiser, robust (interval) mode, references (exact, FSP, SSA), Lean exporter |
| `tests/test_checker.py` | 18 unit and adversarial tests |
| `scripts/run_all.py` | one-command reproduction |
| `certificates/` | JSON certificates (exact rationals) |
| `results/` | raw benchmark output, summary table, axiom audit |
| `docs/` | `MAIN_THEOREMS`, `NOVELTY_AUDIT`, `RESEARCH_PAPER`, `TRUST_BOUNDARIES`, `NEGATIVE_RESULTS`, `PERFORMANCE`, `REPRODUCIBILITY` |

## Quick start

```bash
lake build                                   # Lean library, certificates, axiom audit (about 25 s with Mathlib cache)
PYTHONPATH=python python3 -m unittest discover -s tests
python3 scripts/run_all.py --quick           # small benchmark run
python3 scripts/run_all.py --lean            # full run, plus Lean re-validation of exported certificates
```

Python needs only the standard library (3.11). See `docs/REPRODUCIBILITY.md`.

## Honest status

All Lean theorems compile with no `sorry`. The discrete-time quantities (`hitN`, `hitProb`) are
proved equal to explicit path-sum probabilities of the embedded jump chain. However, the measure-theoretic
continuous-time process is **not** constructed in Lean. The robust interval checker and the
finite-horizon questions are not Lean-verified. The individual mathematical ingredients are classical. The
contribution is in combining them into a verified certificate format. See `docs/NOVELTY_AUDIT.md` for the
self-assessment.
