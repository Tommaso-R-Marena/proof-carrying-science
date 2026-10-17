# Bugs and ambiguities — Workstream D

Findings from building the reviewer-adoption evaluation kit. None of these
authorize inventing human results or live credential changes.

## Ambiguities in upstream evidence shapes

1. **Certificate vs receipt status precedence** — When both carry claim
   decisions, the workbench prefers the receipt for `reported_status` and
   records the source. Reviewers must not treat either as workbench-decided
   ACCEPT.
2. **`lean_authority: null` in fixtures** — Synthetic receipts may omit Lean
   authority. The workbench copies `null` rather than inventing PASS/FAIL.
3. **Interpretation vs claim objects** — Author narratives (abstracts) are not
   always structured claims. Blind cases surface unsupported interpretations
   via `interpretation_claims` / narrative fields; scorers must use the
   dedicated boolean dimension.

## Tooling constraints (by design)

4. **Workbench non-authority** — Any UI that looks like a “status badge” is
   *reported* status only. Automation tests assert `workbench_issues_accept` is
   false.
5. **Blind keys separation** — `keys/ground_truth.json` must not ship inside
   blinded packets. `blind.py` rebuilds the output directory and strips label
   keys; distribution checklists should exclude `keys/`.
6. **Tabletop forbidden markers** — The simulator uses string markers
   (`rotate_production_key`, etc.) as a coarse guard. Sophisticated live
   actions phrased differently could evade detection; labs must still follow
   policy. The simulator never performs credential operations.
7. **External-lab success** — Finishing `CHECKLIST.json` is dry-run success,
   not project-level external validation.

## Open questions for stewards

- Should receipt `valid: true` without Lean authority be displayed with a
  stronger warning banner? (Currently a general disclaimer + warnings list.)
- Preferred response-sheet schema for multi-rater human studies (out of scope
  for this synthetic fixture kit).
