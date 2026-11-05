# Reproducibility

## Pinned versions

| Component | Version |
|---|---|
| Lean | `leanprover/lean4:v4.28.0` (`lean-toolchain`) |
| Mathlib | tag `v4.28.0`; exact commit in `lake-manifest.json` |
| Python | 3.11 (tested with 3.11.14); **standard library only**: no numpy, pytest, matplotlib or solver dependencies |
| Build | `lake` (bundled with the Lean toolchain) |

No external solvers are used. All arithmetic is exact (`fractions.Fraction` in
Python, `ℚ` / `ℚ≥0` in Lean).

## One command

```bash
python3 scripts/run_all.py            # full run, about 25–40 min on 8 cores (the benchmarks dominate)
python3 scripts/run_all.py --quick    # reduced benchmarks and Lean-agreement cases
python3 scripts/run_all.py --no-lean  # Python-only parts (no lake needed)
```

`run_all.py` performs, in order, stopping at the first failure:

1. `lake build PRISM`, which builds every Lean file, including the generated
   example certificates, which are re-checked by the kernel.
2. A source scan of `PRISM/` for `sorry`, `admit`, `axiom`, `native_decide` and
   `implemented_by`, ignoring comments.
3. The axiom audit, `lake env lean PRISM/AxiomAudit.lean` → `results/axiom_audit.txt`.
   The run fails if any axiom outside {`propext`, `Classical.choice`,
   `Quot.sound`} appears.
4. The tests: `tests/test_differential.py`, `tests/test_serialization.py` and
   `tests/test_lean_agreement.py`.
5. The demonstrations: `examples/biochemical/build.py`,
   `examples/biochemical/noisy.py`, `examples/causal/build.py` and
   `examples/scalable/run.py` → `results/demo_*.txt`. The first and third also
   regenerate `PRISM/Examples/Generated/*.lean`.
6. `lake build PRISM` again, so the regenerated Lean files are re-checked.
7. The benchmarks → `results/benchmarks.json`, `results/benchmarks.csv`. The
   report → `results/report.html` (inline SVG plots, every record shown).

Logs for every step go to `results/logs/<step>.log`.

## Determinism

All generators are seeded (`python/prism/generators.py`). Random benchmark seeds
1000–1009 are held out: they were not used while developing the algorithms, which
used seeds 0–399 in the tests. Timings depend on the machine. The one recorded is
in `results/benchmarks.json` → `machine` (8 vCPUs, Linux under gVisor, CPython
3.11.14, single-threaded). Values, certificates and accept/reject outcomes are
deterministic.

## Verifying a certificate by hand

```bash
python3 python/verify.py examples/biochemical/problem.json examples/biochemical/certificate_initial.json --lean
```

This parses and validates both files, recomputes the version space, runs the
independent Python checker, emits a Lean module and has the Lean kernel re-check
it.

## Archive

`PRISM_artifact.tar.gz`, at the repository root and created by `git archive`,
contains the source tree, the docs and the results (the build outputs in `.lake/`
are excluded). Rebuilding requires downloading Mathlib (`lake exe cache get`
fetches prebuilt Mathlib artefacts).
