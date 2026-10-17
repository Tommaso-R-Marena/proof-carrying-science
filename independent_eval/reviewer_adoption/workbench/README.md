# Offline reviewer workbench (Task 15)

Static HTML report generator that **inspects** existing PCS-style evidence for
human review. It copies reported statuses from certificates and receipts; it
never issues `ACCEPT` / `PASS` authority.

## Non-authority

| Capability | Supported? |
| --- | --- |
| Extract claims, assumptions, artifact hashes | Yes |
| Display reported claim statuses from evidence | Yes (labeled *reported*) |
| Assign `inspection_class` claim-strength labels | Yes (heuristic; not authority) |
| Optional observational `pcs verify` cross-check | Yes (`--cli-crosscheck`) |
| Issue PCS ACCEPT / PASS | **No** |
| Replace Lean / PCS authority | **No** |
| Certify scientific validity | **No** |

## Claim-strength lattice (`inspection_class`)

Workbench maps `reported_*` statuses into one of:
`cryptographic_validity`, `computationally_supported`,
`empirically_unsupported`, `scientific_adequacy_open`, `rejected_or_failed`,
`unknown_or_ambiguous`. Summary counts appear as `claim_strength_summary`.

## CLI cross-check (observational)

`workbench/cli_crosscheck.py` black-box runs `pcs verify <certificate>` (or
`python -m pcs.cli verify`) and compares the CLI outcome with workbench
inspection. Explicit fields: `cli_is_authority: true`,
`workbench_issues_accept: false`. Classifications are `agreement` /
`disagreement` / `inconclusive` with reasons; `inspection_class` is never
mutated. Enable via `--cli-crosscheck` on the report generator (embeds JSON +
an HTML section labeled observational). Demo fixtures that are not real attest
packages are marked inconclusive when CLI fails schema checks.

## Usage

From repository root:

```bash
python3 -m independent_eval.reviewer_adoption.workbench.generate_report \
  --evidence independent_eval/reviewer_adoption/workbench/fixtures/sample_bundle \
  --out /tmp/pcs-reviewer-workbench-report.html \
  --format both
```

Optional observational CLI cross-check:

```bash
python3 -m independent_eval.reviewer_adoption.workbench.generate_report \
  --evidence independent_eval/reviewer_adoption/workbench/fixtures/sample_bundle \
  --out /tmp/pcs-reviewer-workbench-report.html \
  --format both --cli-crosscheck
```

Or:

```bash
python3 -m independent_eval.reviewer_adoption.workbench \
  --evidence independent_eval/reviewer_adoption/workbench/fixtures/sample_bundle \
  --out /tmp/pcs-reviewer-workbench-report.html
```

`--format` accepts `html`, `json`, or `both` (default). Output: standalone HTML
(accessibility-minded: skip link, focus styles, reduced motion, captioned
tables, strength definition list) and/or `.inspection.json` for tooling.

## Fixture

`fixtures/sample_bundle/` is synthetic demo evidence only. Reported statuses in
the fixture are not live PCS authority decisions.
