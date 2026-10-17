# Technical report — Workstream B (scientific falsification)

## Scope

Independent black-box evaluation under `independent_eval/scientific_falsification/**` only. PCS is exercised via CLI (`pcs certify`, `pcs verify`, `pcs discover-v06`). Production and formal trees are untouched.

## What was built

1. **Casebook (Task 7)** — seven frozen workflows covering PK/PD contract+replay, mass-action balance, unit compatibility, CSV disjointness, composite multi-check workflows, and alternate PK parameters. Each case ships `CASE.md`, `license.json`, positive manifests, and negative-control artifacts where applicable.
2. **Inadequacy (Task 8)** — three synthetic examples where computational verification PASSes while empirical adequacy is explicitly not established.
3. **Metamorphic testing (Task 9)** — valid transforms (subject rename, claim reorder) and invalid transforms (dose break, post-certify tamper) compared against CLI oracles.
4. **Discovery benchmark (Task 10)** — synthetic projects with ground-truth labels; read-only `discover-v06` metrics.
5. **External validity (Task 11)** — blank protocol templates, completeness rubric, and scorer that refuses to invent participants/results and never equates PCS verify with empirical adequacy.

## Method notes

- Fixture generation may import PCS adapters once to freeze Decimal-faithful PK/PD tables; tests assert via CLI.
- Fixture hashes recorded in `fixtures/FIXTURE_HASHES.json`.
- Exact rebuild command: `PYTHONPATH=. python3 independent_eval/scientific_falsification/python_harness/build_fixtures.py`

## Remaining weaknesses

- External validity remains a protocol kit only until real laboratories enroll.
- Discovery metrics depend on synthetic ground truth.
- Classic certify path does not exercise every v0.6 check type; peak-threshold is documented, not classically executed.
- Metamorphic suite currently anchors on the PK/PD casebook project; extending to every case is planned follow-up.

## Prioritized proposals (for future Codex/Aristotle work — not implemented here)

1. Document per-check which CLI path (`certify` classic vs v0.6) actually executes it.
2. Add a reviewer-facing “computational PASS ≠ empirical adequacy” banner in evidence packages.
3. Expand metamorphic coverage to reaction_balance and unit_compatible cases.
