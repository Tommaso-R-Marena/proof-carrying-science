# Summary of changes for run a40a2f40-cf3f-455e-b5aa-e1ef09d15a1e
AION is built: a Lean 4/Mathlib library, an exact certificate checker, a synthesiser, experiments, documentation and an archive (`aion.tar.gz`). It produces exact rational bounds \(L \le P(\text{event}) \le U\) for rare hitting events in mass-action reaction networks on the infinite state space \(\mathbb N^d\), and Lean checks those bounds. The full `lake build` succeeds with no `sorry`, `admit`, new axioms or `@[implemented_by]`. The individual mathematical ingredients are classical, so this is not a breakthrough; my assessment is Tier 1 achieved, Tier 2 only partly.

**1. Strongest result.** The main result is a certificate format with a checker proved correct in Lean (`checkUpper_sound`, `checkLower_sound` in `RequestProject/AION/Checker.lean`).
- **Upper certificate:** an exact rational table on a finite box, a tail \(C\prod_i\rho_i^{x_i}\) outside it, and 1 on the target.
  - The generator acting on the tail factorises exactly (`genQ_expBar`).
  - A finite falling-factorial sign test then proves the needed inequality on whole infinite regions \(\{x \ge m\}\) (`cellCheck_sound`).
- **Lower certificate:** a subsolution table plus an "escape" (Foster–Lyapunov) table.
- **Supporting theorems:**
  - the barrier upper bound, which needs no boundedness or non-explosion assumption;
  - the lower bound, which requires the escape table;
  - a relative-error transfer theorem: the relative error of a core/tail sandwich is no worse than that of its tail data at the interface, however small \(P\) is;
  - a compositional union bound for modules whose coupling rates are known only within intervals;
  - a single-function robust bound for rates that depend affinely on uncertain parameters;
  - a symbolic birth–death closed form (`bd_exact`);
  - `hitN_eq_path_sum`, showing the discrete quantity is an explicit path probability.
- **Headline example:** for a two-species network where both species are unbounded, Lean proves \(3.9069877\times10^{-8} \le P \le 3.906989\times10^{-8}\) (`Examples/XYmain.lean`).

**2. Proof status.** All 13 key theorems are proved and listed in the Properties table, along with the definitions `hitProb` and `MACRN`.
- The abstract theorems use only `propext`, `Classical.choice` and `Quot.sound` (`results/axiom_audit.txt`).
- The four concrete certificate theorems use `native_decide`, so they also trust the Lean compiler.
- **Gaps you should know about:**
  - No continuous-time path measure is formalised. The results are about the embedded jump chain; linking that to the continuous-time process is standard but done on paper only.
  - Finite-horizon bounds \(P(\tau \le T)\) are not done.
  - The robust (interval-rate) checker runs but is not verified.

**3. Verification engine.** The Python code is in `python/aion/`:
- `checker.py`, an exact-rational mirror of the Lean checker;
- `synth.py`, the untrusted synthesiser, whose output is always re-checked;
- `robust.py`, `reference.py` and `emit_lean.py`.

There are 18 unit and adversarial tests in `tests/`, and `scripts/run_all.py` reproduces everything in one command.

**4–5. Demonstrations and benchmarks** (`results/`, `docs/PERFORMANCE.md`). All bounds hold for the infinite chain.

| Example | \(P\) | certified \(U/L-1\) |
|---|---|---|
| A: birth–death | down to \(8.3\times10^{-25}\) | at most \(4.6\times10^{-7}\); exact value always inside |
| B: gene expression | down to \(2.3\times10^{-13}\) | at most \(1.4\times10^{-5}\) |
| C: modulated growth, \(N\) up to 60 | down to \(2.8\times10^{-13}\) | at most \(5.7\times10^{-7}\) |

- Python checking takes at most 0.3 s; Lean re-checks take 8–13 s per certificate.
- **Versus finite-state projection on the same box:** its upper bound overestimates by 84% at \(N=60\), and gives \(7\times10^{-4}\) for a \(3.9\times10^{-8}\) event on a small box.
- **Versus simulation:** 20,000 runs saw no events for any \(P \le 10^{-6}\).
- **Robust ±1% and ±5% on all rates:** the robust bounds match the extreme constant-parameter certificates.

**6. Novelty** (`docs/NOVELTY_AUDIT.md`). I had no internet access, so I could not read any of the 2026 sources you listed, including the Ripple and CRNT-Lean repositories. Any novelty claim is provisional. The weighted-interface idea in particular may overlap with the 2026 partition and augmented-truncation papers.

**7. Negative findings** (`docs/NEGATIVE_RESULTS.md`), three of them proved in Lean:
- the lower bound fails without the escape certificate;
- the product rule picks up a cross term, so multiplicative module barriers cannot be checked locally;
- in a stable queue, a level with tiny stationary probability is still reached with probability 1, so rarity over an infinite horizon is not safety.

Also documented: the checker caught a synthesiser bug, there is no proved complexity separation, there is no toggle switch or Hill-type model, and the tail must be geometric.

**8–9. Archive and paper.** The archive is `aion.tar.gz` (the git tree). The manuscript is `docs/RESEARCH_PAPER.md`; the other documents are `docs/MAIN_THEOREMS.md`, `docs/TRUST_BOUNDARIES.md` and `docs/REPRODUCIBILITY.md`, plus `README.md`.

**10. Assessment (1–10):**

| Criterion | Score |
|---|---|
| Mathematical novelty | 3 |
| Formal rigour | 7 |
| Computational advantage | 4 |
| Scientific applicability | 4 |
| Demonstrated impact | 2 |