# Lean kernel status

## Current verdict

**V0.5 SOURCE ACTIVE; MACHINE-CHECKED STATUS NOT YET ESTABLISHED.**

Target toolchain: `leanprover/lean4:v4.16.0`.

PCS now contains:

- the indexed assurance judgment `Assures Γ L C E`, representing `Γ ; E ⊢ C @ L`;
- typed claims, assumptions, evidence classes, outcomes, and machine-readable predicates;
- explicit claim/evidence binding;
- single-evidence computational/formal admission functions with source-level soundness proofs;
- an executable whole-claim `decideClaim` function mirroring the pure Python decision kernel after evidence replay;
- restricted PK/PD dimensional contracts.

The Python side now freezes cross-language decision cases in `tests/decision_vectors.json`. See `PYTHON_LEAN_REFINEMENT.md`.

## Already encoded theorem/source targets

The source currently states or targets:

- explicit assumption-context coverage;
- formal assurance contains passing formal-proof evidence;
- computational assurance is predicate-bound;
- unverified evidence cannot establish computational assurance;
- empirical assurance requires empirical/statistical evidence;
- mixed assurance requires formal plus empirical/statistical evidence;
- canonical one-compartment IV PK units are dimensionally valid;
- canonical direct-Emax PD units are dimensionally valid;
- Boolean single-evidence admission refines to the logical `Assures` judgment.

The next main theorem is whole-claim one-way soundness:

```text
decideClaim c es = accepted(L)
∧ NormalizedEvidence es
∧ ContextCovers Γ c
---------------------------------
Γ ; es ⊢ c @ L
```

This is intentionally a soundness target, not completeness.

## What is still not proved

The current source does **not** yet establish:

- a machine-checked successful Lean build;
- whole-claim decision soundness for all accepted classes;
- serialization/decoding refinement from PCS JSON into Lean datatypes;
- Python implementation refinement to the Lean decision function;
- formal real-analysis semantics of the PK exponential/Emax equations;
- empirical adequacy of any PK/PD model.

## Standalone CI status

The standalone repository now contains a dedicated Lean CI job using `leanprover/lean-action@v1`, plus a no-`sorry` source gate.

As of September 28, 2026, GitHub Actions jobs for this repository are completing with no exposed execution steps; the latest inspected job had an empty step list. The same symptom affected a trivial smoke workflow. This is consistent with runner/provisioning failure before repository commands execute, so it provides neither positive nor negative evidence about the Lean source or Python tests.

Separately, the Python v0.5 candidate was executed in the working environment before repository migration: 44/44 tests passed, and the frozen v0.5 targeted adversarial campaign rejected 16/16 attacks with 0 false accepts in that finite campaign. A finite campaign is not a security proof.

## Reproduction command

Once Lean 4.16.0 is available:

```bash
./scripts/verify_lean.sh
```

The command must succeed and the source audit must find no `sorry` before PCS is described as machine checked.

## Publication boundary

The Lean kernel is an independent synthesis artifact. It contains no CertiForge optimizer semantics, CASMI/QFD algorithms, unpublished biological results, or proof-carrying-agent implementation details. See `PUBLICATION_FIREWALL.md`.

Historical compilation experiments in other private repositories are no longer part of the PCS development path. All current and future PCS formal work belongs in `Tommaso-R-Marena/proof-carrying-science`.
