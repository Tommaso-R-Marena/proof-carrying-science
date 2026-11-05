# Bugs and ambiguities — Workstream E

## Motivating hazard (sibling)

1. **Case-insensitive path collision** — Workstream D CI failed when both
   `CHECKLIST.json` and `checklist.json` existed under the same directory.
   Repository integrity policies (and macOS/Windows default filesystems) treat
   those as one path. The collision scanner exists to catch this class of bug
   before merge.

## Ambiguities

1. **Inventory without sibling checkouts** — On this branch alone, A–D prefixes
   are typically `MISSING`. That is expected: the aggregator must not invent
   test counts or findings from absent trees. Merge/CI overlays that materialize
   siblings will flip status to `PRESENT`.
2. **Nonoverlap vs remote freshness** — The auditor uses
   `git diff --name-only origin/main...<branch>`. Stale local `origin/*` refs
   produce stale overlap reports; fetch before trusting results.
3. **Missing branches** — If a sibling branch ref is absent, it is listed under
   `missing_branches` rather than treated as an empty change set.
4. **Proposals are not results** — `proposals/PROPOSALS.json` entries are future
   work suggestions. Presence in the catalog is not evidence of completed
   evaluation or formal proof work.

## Non-findings

- No production `pcs/`, `formal/`, `.github/`, or `independent_eval/README.md`
  files were modified by this workstream.
- This package does not re-execute A–D harness campaigns.
