# Independent numerical review

This internal, AI-assisted review used independently authored arithmetic and SBML counterexamples and the admitted development Fiedler 2016 PEtab project only. It is not external expert validation. No new final source or reference annotation was consulted. Earlier layers remain unchanged.

The retained run in [evidence/numeric-review.json](evidence/numeric-review.json) contains source and implementation hashes, environment versions, exact supplied-prediction residual arithmetic, and the actual 72 reconstructed observable predictions for each of Radau and BDF across three conditions. Prediction rows retain all measurement identity metadata; comparisons join these identities rather than row positions. The supplied decimal predictions give exact RSS

`40814069238626533672588417454406577989 / 4000000000000000000000000000000000000`

(approximately `10.203517309656634`). This calculation alone does not reexecute a model. Separately, reconstruction interprets the original closed SBML reactions, assignments, PEtab nominal parameters, conditions and observable formulas. Radau/BDF maximum observable difference is `5.690257305e-7`; the Radau/supplied-prediction maximum difference is `5.31543728e-7`. The reconstructed Radau decimal outputs have RSS approximately `10.203517528995794`. These are observed finite numerical comparisons, not certified error bounds.

Review repaired the following defects before final evaluation:

- Initial assignments to parameters now reach reaction environments. Initial assignments and assignment rules resolve together, with every pending target excluded from seed values, so stale declarations cannot satisfy an unresolved dependency. Decimal initialization uses exact source fractions directly at precision 80 instead of passing species or compartment values through binary64 first.
- MathML constants admit a closed base-10 fragment: decimal real literals, integer digit literals, or rational/e-notation literals with exactly one separator. Unsupported types, bases, units, malformed separators and mixed content abstain. SBML time uses an internal object key, so a source parameter named `__time__` cannot replace it.
- Original assignment-rule target mutability is checked before projection. Original core namespaces, one-model counts, direct declaration containers, duplicate containers/identifiers, local parameter identifiers, three-dimensional fixed compartments, nonnegative stoichiometry and referenced species are validated. Foreign or nested semantic activation and unknown active features abstain. Core notes/annotation are stripped as inert metadata, including any embedded core-looking assignments.
- Reconstructed parameter, condition and observable IDs must be unique before dictionaries are built. Unknown or compartment condition columns and compartment parameter overrides abstain. Extra PEtab noise/calibration parameters remain available for declared placeholders and are excluded from model overrides.
- Log/log10 parameter bounds and nominal values must all be positive in their declared, untransformed domain. Exact rational RSS survives binary64 overflow with `rss_float: null` and an explicit `OUT_OF_RANGE` projection. Full observation metadata distinguish measurements, and distinct predictions at one complete identity return `UNKNOWN`.

The structural projection is disclosed for each condition by its original model SHA-256, projection SHA-256, applied overrides and change list. It removes independently interpreted assignment containers and inert metadata, fixes parameter declarations for the unchanged older structural parser, and excludes rule-defined species from its dynamic-state list. It is a separately checked projection rather than a claim that the older parser directly accepted the original assignment-bearing model. Uploaded scripts and source expressions never execute as Python; the executable-formula regression returns `UNKNOWN` and leaves its filesystem marker absent.

The 60 focused tests pass. Reproduce from the repository root with the session's numerical dependencies:

```sh
PYTHONPATH=/dev/shm/pcs-science-numeric-deps:. /workspace/proof-carrying-science/.venv/bin/python -m pytest -q research/scientific_review_v4/tests/test_independent_numerics.py
```

The run used Python 3.12.14, SciPy 1.15.3 and NumPy 2.2.6 with `rtol=1e-9`, `atol=1e-12`. The dependency directory is session-local, not vendored. Decimal 80-digit initialization and two agreeing adaptive solvers do not establish rigorous rounding or global ODE error bounds, Python/SBML refinement, a fitted optimum, biological meaning, uncertainty calibration or empirical validity. Those obligations remain open; all records retain `authority: false` and `empirical_validity: NOT_ESTABLISHED`. Unsupported mathematics or source features return `UNKNOWN`.
