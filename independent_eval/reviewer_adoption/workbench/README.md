# Offline reviewer workbench (Task 15)

Static HTML report generator that **inspects** existing PCS-style evidence for
human review. It copies reported statuses from certificates and receipts; it
never issues `ACCEPT` / `PASS` authority.

## Non-authority

| Capability | Supported? |
| --- | --- |
| Extract claims, assumptions, artifact hashes | Yes |
| Display reported claim statuses from evidence | Yes (labeled *reported*) |
| Issue PCS ACCEPT / PASS | **No** |
| Replace Lean / PCS authority | **No** |
| Certify scientific validity | **No** |

## Usage

From repository root:

```bash
python3 -m independent_eval.reviewer_adoption.workbench.generate_report \
  --evidence independent_eval/reviewer_adoption/workbench/fixtures/sample_bundle \
  --out /tmp/pcs-reviewer-workbench-report.html
```

Or:

```bash
python3 -m independent_eval.reviewer_adoption.workbench \
  --evidence independent_eval/reviewer_adoption/workbench/fixtures/sample_bundle \
  --out /tmp/pcs-reviewer-workbench-report.html
```

Output: standalone HTML (accessibility-minded: skip link, focus styles, reduced
motion, responsive tables) plus a companion `.inspection.json` for tooling.

## Fixture

`fixtures/sample_bundle/` is synthetic demo evidence only. Reported statuses in
the fixture are not live PCS authority decisions.
