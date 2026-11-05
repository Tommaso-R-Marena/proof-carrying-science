# ProofLab: 40 pinned real Lean theorem targets

This first benchmark indexes **40 existing Lean theorem declarations** from the private PCS core at commit `cff0b67595abd4862ab0c156b157f262b169eca5`. All source byte blobs and lines are pinned. It does **not** compile a new theorem, guarantee arbitrary scientific assertions, or verify the current runtime's assumptions. The historical Lean build and authority status must be checked independently. The separate unknown-checker fail-open P0 remains open until its PR receives signed negative-test evidence and is merged.

- **22 train**: Binding, Workflow, PKPDCheck.
- **8 development/validation**: Checkers.
- **10 held-out evaluation**: PackageProofs, Frontier.

These are **entire source modules**, not row-random splits. All 40 come from **one project (PCS Lean v2)**. A real project-held-out evaluation must wait for independently permission-cleared outside projects; do not claim cross-project generalization yet.

`pcs_lean_v2_40.json` includes genuine theorem statements and source cited prior target lemma mentions; it is private repo material. `prooflab_public_view.json` publishes **only the 22 training mission summaries**, never the 18 validation/evaluation cases; it contains task boards and citation references but **no private Lean proof bodies or statements**. The private benchmark is the only file carrying held-out target identifiers and theorem statements. Public educational graph edges describe a prudent review workflow and are not a Lean theorem's exact minimal prerequisites. Actual cited lemma edges are labeled separately and checked lexically against source.

The validator checks Git blob SHA-1, line, exact normalized statement, prior cited theorem names, 40 IDs, graph acyclicity and source-module split integrity. It does not prove those lexical references logically necessary. It does not run Lean.

To validate when the private core repo is checked out:

```sh
python -m pytest -q tests/test_prooflab_benchmark_v1.py
python -c 'from pathlib import Path; from pcs.prooflab_benchmark_v1 import validate_checked_in; print(validate_checked_in(Path(".")))'
bash scripts/verify_lean.sh
```

When adding third-party projects, require explicit usage/publication permission and a separate project-level holdout; do not mix inaccessible or patient-identifying data into the public Arena.

The game may train **planning and critique heuristics**, never automatic promotion to Lean authority. The web client performs no Lean kernel check. Its replayed D1 training records are participant gameplay traces with an educational partial-order checker, not new mathematical theorems.
