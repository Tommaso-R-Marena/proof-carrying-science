# Exact transfer regions and counterexample workshop

This extension to PR167 adds a constructive research activity: change the final
row of a synthetic transport trajectory by moving an exact amount between two
cells. It also proves the complete rational interval for preserving pair bounds
and energy no greater than the unmodified pair's energy.

The implementation is isolated on a stacked research branch. PCS authority,
canonical wire formats, receipt schemas, existing Lean statements, and Aristotle
proof-development modules are unchanged. The browser constructs data; the existing
fixed checker independently supports or refutes an exported trace.

## Mathematical result

For rational volumes **v,w > 0**, concentrations **x,y**, and an amount **t**, set
`x' = x − t/v`, `y' = y + t/w`. Let

```text
R = 2 v w (x − y) / (v + w)
L = max(min(0,R), v(x−hi), w(lo−y))
U = min(max(0,R), v(x−lo), w(hi−y))
```

The six new ordinary Lean theorems in namespace `PCSFluxForge` are:

| Theorem | Exact guarantee |
| --- | --- |
| `amount` | `v x' + w y' = v x + w y`, assuming only nonzero volumes. |
| `energy_delta` | Weighted pair energy change is `(v+w)/(vw) × t × (t−R)`. |
| `energy_interval` | Pair energy does not increase **iff** `min(0,R) ≤ t ≤ max(0,R)`. |
| `bounds_interval` | Both updated concentrations lie in `[lo,hi]` **iff** the four rational bounds on t hold. |
| `feasible_interval` | Bounds and nonincreasing pair energy hold together **iff** `L ≤ t ≤ U`. |
| `nonzero_changes` | Every nonzero transfer changes the first concentration, assuming its volume is nonzero. |

The energy, bounds and combined interval theorems assume positive volumes. Bounds
need not initially hold for the mathematical equivalences; an empty intersection
correctly expresses infeasibility. The browser supports the subset with an already
in-bounds baseline, so zero is always feasible. Reversing the cells reverses the
transfer sign. Equal concentrations give a zero-width energy interval. No square
roots, floating point, or sampling are used to construct the endpoints.

Other coordinates remain unchanged in the implementation. The generic theorem
concerns pair arithmetic. Its connection to whole-model browser updates is tested
with independent matrix calculations; no formal source-to-JavaScript refinement
theorem is claimed. Nonzero transfers from a correct final row violate the declared
recurrence even when all displayed invariants pass. Selected complete trace exports
are checked separately by actual Lean, using the unchanged PR165 certificates.

## Use the workshop

Serve `research/flux_detective_v1` using the existing local instructions. Below the
puzzle cards, choose two distinct cells and an amount, or explore the exact interval
with the slider and midpoint button. Manual values outside the interval expose
failed conditions; malformed rational inputs disable export. Restoring zero returns
the model trace. Editing the workshop does not change campaign stars.

Downloads retain the existing `pcs-flux-detective-export-v1` data-only envelope.
The choice label is zero and is untrusted metadata, not a claim that the case is an
original campaign choice. No extra proof, verdict, path or verifier command enters
the unchanged export parser. Use the existing `research.flux_detective_v1.check`
and reviewer `research.portable_transport_v2.replay verify` commands for actual Lean.

## Independent scientific falsification

`experiment.py` compares three policies on adversarially constructed synthetic
inputs: original mass/bounds/historical-energy summaries, the stricter energy limit
relative to the correct model output, and exact matrix correspondence.

The fixed final protocol has three seeds (0,20261021,4294967295), six models per
seed, every ordered cell pair, five points within the exact interval and four
outside probes: each endpoint plus/minus 1/8 and 1/1024 as appropriate. There are
**1,296 samples and 582 unique model/trajectory pairs**. Duplicate samples are
reported separately; these are not independent trials or population failure rates.

| Policy | Accepted samples | Invalid samples accepted | Unique pairs accepted | Invalid unique pairs accepted |
| --- | ---: | ---: | ---: | ---: |
| Original summaries | 796 | 628 | 332 | 314 |
| Stricter energy | 720 | 552 | 294 | 276 |
| Exact matrix correspondence | 168 | 0 | 18 | 0 |

The stricter policy eliminates 38 unique invalid cases but still accepts 276.
The exact criterion's zero false positives here is definitional: the independent
matrix oracle defines model correspondence. It is not an empirical false-positive
rate or evidence of source-code correctness in general.

An initial development protocol used only the coarse 1/8 outside probes (1,008
samples,438 unique pairs). Both summary policies accepted the same 276 invalid
unique pairs. That negative comparison is retained in the development evidence.
The final protocol adds the closer boundary probes, preserving the coarse cases;
it exposes the difference without hiding the remaining counterexamples. This is
exploratory analysis, not a preregistered empirical study.

## Reproduce

Use the existing pinned Lean4.28.0/Mathlib and Python setup, then run:

```sh
python -m research.flux_forge_v1.audit --out /new/formal-audit
python -m research.flux_forge_v1.experiment --out /new/policy-experiment
node --test research/flux_detective_v1/test_engine.mjs research/flux_detective_v1/test_forge.mjs research/flux_detective_v1/test_browser.mjs
python -m pytest -q research/flux_detective_v1/test_correspondence.py research/flux_forge_v1/test_forge.py research/portable_transport_v2/test_replay.py
python -m research.flux_forge_v1.preservation
```

The formal audit freshly compiles all six statements, checks their complete axiom
inventories, and uses the official `leanchecker --fresh` on the resulting object.
Only propext/Classical.choice/Quot.sound are permitted. The object checker is the
same Lean kernel, not an external proof verifier; imported Mathlib objects remain
trusted cache inputs. Compilation/checker refusal never establishes success.

Tests compare **13,200 exact pair transfers** with an independent Fraction oracle,
then all **1,296 full-model exports** with independent matrix evolution and exact
fault residuals. Eight selected workshop exports (two supported/six refuted) run
actual Lean; the other 1,288 are differential cases, not claimed Lean verdicts.
The original 40 export tests and 24 hostile replay tests continue to run. There
are 75 Python tests and 19 Node/browser tests in total, plus the formal audit.
The consolidated source gate is unchanged. The new preservation gate permits only
the six reviewed UI/documentation/workflow changes to PR167's existing files and
preserves all 6,311 pre-game predecessor blobs and modes.

Set `PCS_FORGE_EVIDENCE_DIR=/new/path` to retain the eight selected proof packages.
The experiment retains all input bytes, hashes, source copies, duplicate-aware
metrics and per-case results. Output directories are fresh-only. The workflow
uploads these artifacts, formal object replay logs, screenshots and test XML.

## Trust, science and readiness

This is a usable exact-model counterexample exercise, with a new mathematical
characterization and bounded independently replayable controls. Browser and Python
code, their runtime/compiler/OS, source-to-object correspondence and same-host
administration remain trusted/tested boundaries. No immutable root, independently
administered authority, production admission or new canonical receiver is added.
All models are synthetic rational discrete transport; no physical, continuum,
learning, engagement or recursive-self-improvement result is established.

Next: evaluate whether people can construct and diagnose counterexamples on unseen
models, and formally connect finite-vector updates and wire decoding to the
existing trace predicate. Future Aristotle codec changes remain a separate,
fully differential-tested integration.
