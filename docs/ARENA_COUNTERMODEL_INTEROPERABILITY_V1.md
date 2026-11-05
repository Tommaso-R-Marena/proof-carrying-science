# Independent Arena countermodel checks in PCS

Countermodel Lab emits `pcs-countermodel-witness-v1` JSON with exactly `format`, `version`, `mission_id`, and `world`. Run `pcs countermodel-check-v1 witness.json` to re-evaluate that world using an independent Python implementation. Exit 0 means the two pinned formulas disagree, 1 means they agree in that world, and 2 means unsupported/malformed input.

The checker registers only the seven exact v1 mission formulas, pinned to ruleset SHA-256 `d3b02eb4eb39976fd3179a44ef1b6bffd17a8f4a271b1bd7cddb97eb71276df2`. Worlds contain 1–3 agents and explicit Boolean P/Q/R interpretations. It recomputes truth and exhaustive minimum-domain size; submitted labels/scores/extra fields, duplicate JSON keys, unsupported versions, and oversized files are rejected. No client AST or executable code is accepted.

This CLI is a diagnostic **finite first-order model checker**, not a registered PCS assurance check, scientific certificate, Lean receipt, or proof of unbounded equivalence. A disagreement is a concrete witness to differing meanings under the supplied interpretation. The website separately exports Lean source whose actual compilation is checked in website CI. Neither game score nor trained model can grant verification authority.

The website dataset preparation script replays consented trajectories before creating model transitions; the independent checker adds an optional cross-language verification of final witnesses. It does not authenticate human provenance, certify consent, or replace trajectory replay. Training should isolate evaluation families and exclude hint-assisted examples unless explicitly studying assistance. Private research exports remain owner-only.

## Maintenance PR review

Dependency PRs #83–#87 are consolidated here with their exact immutable action pins: upload-artifact v7.0.1, download-artifact v8.0.1, checkout v7.0.1, setup-node v7.0.0, setup-python v7.0.0. Standard public ubuntu-24.04 runners must execute the full required gate before merging. The optional legacy self-hosted workflows also require a sufficiently current runner for these action releases; their skipped jobs are not execution evidence.
