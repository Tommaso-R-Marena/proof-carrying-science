# Technical report — Workstream F Assurance Card

## Goal

Produce a single offline artifact a human reviewer can open without running a
rebuild: an Assurance Card that cleanly separates **authority** (black-box
`pcs verify`) from **inspection** (heuristic claim classification) and always
surfaces the limitations banner that computational PASS ≠ empirical adequacy.

## Method

### Authority lane

`python_harness/pcs_cli.py` resolves `pcs verify <certificate>` when the `pcs`
binary is on `PATH`, else `python -m pcs.cli verify`. The invocation is
subprocess-only (black-box). Recorded fields: argv, returncode, ok
(prefer structured `valid` ∧ rc==0), stdout/stderr tails (4k), duration_seconds.
Timeouts and missing CLI map to skipped / inconclusive — never to invented PASS.

No Mathlib rebuild, no Lean rebuild, no network. Verify only.

### Inspection lane

`python_harness/inspect_lane.py` parses certificate / verification-receipt /
LIMITATIONS under the evidence root. Each claim is classified by
`claim_lattice.classify_claim` into:

| inspection_class | Meaning (heuristic) |
| --- | --- |
| `cryptographic_validity` | integrity / signature style reported status |
| `computationally_supported` | computational support reported for non-science kinds |
| `scientific_adequacy_open` | scientific / adequacy claims remain open even if computationally labeled |
| `rejected_or_failed` | reject / fail / hash-mismatch style status |
| `unknown_or_ambiguous` | missing or unrecognized status |

Invariants forced in JSON: `card_issues_accept: false`,
`inspection_is_not_authority: true`. Inspection classes are never mutated by
authority-lane outcomes; `lane_consistency` is observational only
(agreement / disagreement / inconclusive).

### Provenance

UTC timestamp, optional `git rev-parse HEAD`, sha256 of inspected inputs,
Python / platform / cheap `pcs` version probe, and an efficiency block
declaring single-process / no-network / verify-only.

### HTML

Static, self-contained HTML with skip-link, `lang="en"`, focus-visible styles,
limitations banner (`role="status"`), and labeled authority / inspection
sections. No external assets.

## Fixtures and real-path demo

- `fixtures/sample_bundle/` — fresh CC0 synthetic package (computational +
  integrity + open scientific claim). Format markers identify it as a fixture
  so it is not mistaken for a real attest package.
- `tests/test_pkpd_real_path.py` — when `pcs` and
  `examples/pkpd_one_compartment` are available: certify → verify → card in a
  temp directory.

## Non-claims

No clinical validity, no external lab completion, no security proof, no merge
recommendation. The card does not certify science.
