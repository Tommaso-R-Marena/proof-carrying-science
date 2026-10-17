# Workstream F — Offline Proof-Carrying Assurance Card

One command produces a reviewer-facing **Assurance Card** (JSON + static HTML)
for an evidence directory or certificate path. Offline, single-process, no
network, verify-only (no Mathlib / Lean rebuild).

```bash
PYTHONPATH=independent_eval/assurance_card python3 -m python_harness.card \
  --evidence PATH_OR_CERTIFICATE --out /tmp/pcs-assurance-card --format both

PYTHONPATH=independent_eval/assurance_card python3 -m pytest -q \
  independent_eval/assurance_card/tests
```

| Doc | Purpose |
| --- | --- |
| `NONOVERLAP.md` | Writable scope vs forbidden trees / sibling PRs |
| `TEST_INVENTORY.md` | Collected pytest node ids |
| `TECHNICAL_REPORT.md` | Method, lanes, efficiency |
| `BUGS_AND_AMBIGUITIES.md` | Ambiguities and observed hazards |

## Card contents (separation of concerns)

1. **Authority lane (CLI)** — black-box `pcs verify` (or `python -m pcs.cli verify`).
   Records argv, return code, ok, stdout/stderr tails, duration. Authoritative for
   computational / cryptographic validity of the package.
2. **Inspection lane (non-authority)** — parse certificate / receipt / LIMITATIONS;
   classify each claim into the inspection_class lattice:
   `cryptographic_validity | computationally_supported | scientific_adequacy_open | rejected_or_failed | unknown_or_ambiguous`.
   Explicit: `card_issues_accept: false`, `inspection_is_not_authority: true`.
3. **Provenance** — git HEAD (if repo), file sha256s of inspected inputs, UTC
   timestamps, cheap tool versions.
4. **Limitations banner** — always visible: computational PASS ≠ empirical
   adequacy; the card never certifies science.

## Layout

- `python_harness/` — card builder, pcs_cli wrapper, claim_lattice, hashing, paths, HTML
- `fixtures/sample_bundle/` — minimal synthetic CC0 evidence (fresh; not copied from sibling trees)
- `tests/` — pytest (≥10): lattice, hashing, schema, HTML a11y, CLI agree/disagree/inconclusive, optional pkpd real path

## Non-claims

No clinical validity, no external lab completion, no security proof, no merge
recommendation. Inspection never issues ACCEPT/PASS.
