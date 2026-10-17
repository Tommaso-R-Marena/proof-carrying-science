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
| Issue PCS ACCEPT / PASS | **No** |
| Replace Lean / PCS authority | **No** |
| Certify scientific validity | **No** |

## Claim-strength lattice (`inspection_class`)

Workbench maps `reported_*` statuses into one of:
`cryptographic_validity`, `computationally_supported`,
`empirically_unsupported`, `scientific_adequacy_open`, `rejected_or_failed`,
`unknown_or_ambiguous`. Summary counts appear as `claim_strength_summary`.

## Usage

From repository root:

```bash
python3 -m independent_eval.reviewer_adoption.workbench.generate_report \
  --evidence independent_eval/reviewer_adoption/workbench/fixtures/sample_bundle \
  --out /tmp/pcs-reviewer-workbench-report.html \
  --format both
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
