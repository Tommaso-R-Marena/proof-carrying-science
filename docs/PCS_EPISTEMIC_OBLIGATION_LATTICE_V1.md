# Epistemic Obligation Lattice v1

**Status:** experimental research line. Grants **no** package authority, Lean-authority
acceptance, biological adequacy, clinical validity, or scientific truth.

## Thesis

PCS already separates formal, computational, empirical, and provenance evidence.
What it has not yet made *machine-obligatory* is the Popperian asymmetry:

> Empirical and computational claims must say what would refute them.
> Support is defeasible under new observations.
> Evidence classes cannot silently promote.
> Composition cannot hide a refuted premise.

The Epistemic Obligation Lattice (EOL) makes that asymmetry an independently
replayable receiving judgment.

## Judgment

A finite package `P = (Claims, Evidence, Observations)` is evaluated by the
receiver to a status table:

```text
evaluate(P) : ClaimId → {unsound, open, supported, refuted}
```

Producer-declared statuses are ignored. The receiver recomputes everything from
canonical package bytes.

## Well-formedness barriers

| Rule | Meaning |
| --- | --- |
| Falsifier barrier | `empirical` and `computational` claims require ≥1 falsifier literal |
| Self-dependency barrier | A claim may not depend on itself |
| Unique ids / resolved deps | Duplicate or dangling identifiers are rejected |
| Exact class match | Evidence of class `K` discharges only claims of class `K` |

Formal and provenance claims may omit falsifiers: formal failure belongs to an
independent checker; provenance is integrity metadata, not an empirical world-claim.

## Evaluation

Bottom-up over the claim DAG:

1. Join dependency statuses (`unsound` absorbs; else `refuted`; else `open`; else `supported`).
2. If any falsifier literal matches a known observation atom → `refuted`.
3. If a dependency is `refuted` → dependent becomes `open` (reopened, not silently supported).
4. Else if all dependencies are `supported`, exact-class evidence passes, and all
   support literals match → `supported`.
5. Otherwise → `open`.
6. Cycles / fuel exhaustion → `unsound`.

## Defeasibility

Unlike a Lean proof, empirical support is not monotonic in observations.
Adding a matching falsifying observation turns `supported` into `refuted`.
That is the intended scientific asymmetry, not a bug.

## Architecture placement

```text
L0 production verifier / Lean authority     ← unchanged
L1 Claim IR / packages / receipts           ← unchanged
EOL v1 (this line)                          ← experimental sibling receiver
Lean PCSEpistemic                           ← abstract lattice theorems + controls
```

EOL does **not** replace `verify-v06`, transport, calibration, Omega, or semantic
authority. It proposes a new obligation surface that those systems can later bind.

## CLI

```bash
pcs epistemic-lattice-v1 --package package.json --output receipt.json
pcs epistemic-lattice-v1 --campaign research/epistemic-lattice-v1/fixtures \
  --output research/epistemic-lattice-v1/campaign/report.json
```

Exit `0` only when every claim is `supported` and none are `unsound` (package mode),
or when every campaign fixture meets its expectation (campaign mode).
Operational errors return `2`. Scientific acceptance is always reported `false`.

## Formal layer

`formal/PCSEpistemic/` proves:

- empirical/computational claims without falsifiers are ill-formed;
- class compatibility is exact equality;
- falsifier match forces `refuted` under sound non-unsound dependencies;
- empty empirical packages are structurally unsound;
- concrete positive/negative controls via `decide`.

Axiom audits allow at most `propext`, `Classical.choice`, `Quot.sound`.

## Non-claims

- EOL does not sense the physical world; observation atoms are declared Booleans.
- EOL does not replace statistical estimation, causal identification, or clinical validation.
- Passing EOL does not imply package `ACCEPT` or Lean-authority `valid: true`.
- Formal claim `supported` here only means lattice discharge under exact-class evidence;
  the actual mathematical checker remains separate.
