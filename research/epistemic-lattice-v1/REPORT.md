# Epistemic Obligation Lattice v1 — research report

**Branch intent:** groundbreaking theory + architecture + experimentation + engineering,
isolated from concurrent PCS development.

**Authority:** none. Experimental only.

## 1. Problem

PCS has a mature production verifier, claim IR, transport/calibration kernels, Omega
reasoning, and semantic authority. The founding architecture insists that formal,
computational, empirical, and provenance evidence must not be conflated — yet the
repository lacked a **machine-checkable falsifiability calculus**:

- empirical claims could be discussed without stating what would refute them;
- class promotion attacks were handled in specific adapters, not as a general lattice law;
- defeasibility under new observations was not an explicit receiving judgment.

## 2. Theoretical contribution

We define a finite **Epistemic Obligation Lattice** over statuses

```text
unsound | open | supported | refuted
```

with laws:

1. **Falsifier barrier.** Empirical/computational claims without falsifiers are ill-formed.
2. **Class barrier.** Evidence class must equal claim class; no promotion.
3. **Falsifier dominance.** A matched falsifier yields `refuted` even if evidence passes.
4. **Composition reopen.** A refuted dependency forces dependents to `open`, never `supported`.
5. **Defeasibility.** New matching falsifying observations can turn `supported` into `refuted`.

These are not slogans: they are executable in Python and partially formalized in Lean
(`PCSEpistemic`).

## 3. Architecture

```text
pcs/epistemic_lattice_v1.py     receiving kernel + CLI
formal/PCSEpistemic/            Lean lattice + controls + axiom audit
tests/test_epistemic_lattice_v1.py
research/epistemic-lattice-v1/  fixtures, protocol, campaign
docs/PCS_EPISTEMIC_OBLIGATION_LATTICE_V1.md
```

No changes to `verifier_v06`, Lean authority, signing roots, or existing research
receipts. CLI registration is additive.

## 4. Experiments

Six frozen controls (see `PROTOCOL.json`):

| Control | Result |
| --- | --- |
| Good empirical support | `supported` |
| Falsifier vs passing evidence | `refuted` |
| Formal→empirical promotion | stays `open` |
| Unfalsifiable empirical | rejected at parse |
| Three-layer composition | all `supported` |
| Upstream integrity fail | `refuted` + dependents `open` |

Additional unit tests cover self-dependency rejection, duplicate ids, cyclic graphs
(`unsound`), and defeasibility under observation update.

## 5. Engineering surface

```bash
pcs epistemic-lattice-v1 --package examples/epistemic-lattice-v1/package.json \
  --output /tmp/eol-receipt.json
```

Receipts bind `package_sha256` / `input_sha256` / `canonical_sha256`, always set
`scientific_acceptance: false` and `pcs_authority: false`, and list explicit limitations.

## 6. Limits (intentional)

- Observation atoms are Boolean labels, not instruments.
- Formal lattice `supported` is not a substitute for Lean kernel checking of mathematics.
- No claim of general scientific intelligence, causal identification, or regulatory acceptance.
- Lean theorems cover the abstract barriers and concrete controls; they do not refine the
  Python implementation byte-for-byte (that remains a future refinement obligation).

## 7. Why this is a hard push

Prior PCS research advanced checkers, kernels, search, and calibration inside existing
assurance categories. EOL introduces a **new category of obligation**: claims must carry
their own falsifiers, and the receiver independently enforces Popperian structure as law.
That is the missing bridge between PCS's philosophical non-conflation thesis and an
executable scientific epistemology.
