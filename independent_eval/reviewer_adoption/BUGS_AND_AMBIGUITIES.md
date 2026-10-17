# Bugs and ambiguities — Workstream D

1. **Certificate vs receipt status** — Workbench prefers receipt decisions when
   present and labels them *reported*. Neither is workbench-decided ACCEPT.
2. **Keyword tabletop scoring** — Simulator uses substring keywords; answers must
   include exact phrases from `acceptable_keywords`. Facilitators should treat
   heuristic pass/fail as a dry-run aid, not incident-grade grading.
3. **Blind label taxonomy** — Core judgments are
   `accept_as_valid` / `reject_as_invalid` / `accept_computational_only` /
   `abstain`. Finer distinction dimensions are encoded via ground-truth labels
   and `distinction_tags`, not separate scored axes in v1.
4. **Checklist filename** — Canonical file is `CHECKLIST.json` only. A previous
   dual `checklist.json` pair failed repository integrity (case-insensitive
   path collision) and was removed. Loader still requires
   `external_validation_complete_allowed=false` plus forbidden
   `EXTERNAL_VALIDATION_COMPLETE`.
5. **Duplicate case files** — Concurrent edits can leave duplicate `case_id`s;
   `load_cases` keeps the first sorted path. Prefer a single file per id.

## Open questions

- Whether receipt `valid: true` without Lean authority needs a stronger banner.
- Human multi-rater response-sheet schema (out of scope for synthetic fixtures).
