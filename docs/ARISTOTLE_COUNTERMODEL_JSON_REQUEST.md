# Aristotle follow-up: bounded witness decoding, Lean 4.28.0

Upload the current `formal/` directory, `pcs/countermodel_v1.py`,
`pcs/schemas/countermodel_missions_v1.json`, `scripts/generate_countermodel_missions.py`,
and the website's `public/countermodel-core.mjs`. Use `leanprover/lean4:v4.28.0`.

The existing `PCSCountermodel` library proves general typed evaluator correctness,
named lowering correctness, enumeration coverage and search soundness/minimality.
`PCSCountermodel/Missions.lean` now binds all seven real game mission pairs.
Preserve those results and the independent `NHolds`/`Holds` semantics.

Close the next trust boundary: a strict, executable decoder from a documented
JSON witness representation into these fixed mission constants and a `World n`.
Do not attempt to prove real-world scientific intent or Python/JavaScript execution
inside Lean. Do not replace the actual game formulas with convenient alternatives.

1. Specify a JSON value representation that preserves duplicate object keys until
   validation. Decode exactly the outer fields `format`, `version`, `mission_id`,
   `world`, with values `pcs-countermodel-witness-v1`, `pcs-countermodel-lab-v1`,
   one of the seven fixed mission IDs, and exactly `n`, `P`, `Q`, `R` in the world.
   Reject unknown/duplicate fields, unknown missions, submitted verdicts or formulas,
   non-Booleans, incorrect vector/matrix lengths, and domains outside 1–3.
2. Prove decoder acceptance iff a precise independently defined schema predicate.
   Prove every decoded P/Q/R entry equals the corresponding validated JSON Boolean;
   no padding, truncation, rounding, defaults or alternate mission selection.
3. Define the witness checker using the decoded world and the fixed mission lookup.
   Prove acceptance implies disagreement of the corresponding original named
   formulas under `NHolds` for every valuation, by the existing generic theorem.
   Prove exact checker completeness relative to a successfully decoded witness.
   Keep unsuccessful bounded searches distinct from unbounded equivalence.
4. Provide encode/decode round-trip theorems for every valid world and all seven
   mission IDs, concrete positive fixtures, and fail-closed negative fixtures for
   all schema rejection cases, including variable/domain index confusion.
5. If adding a byte parser, explicitly specify its accepted grammar and resource
   bounds (16 KiB input maximum), prove its connection to the value decoder, and
   keep unproved Unicode, numeral or runtime details explicit. The existing Python
   input accepts ordinary JSON with whitespace; a canonical-only Lean parser would
   be a new protocol restriction, not a proof of that current parser's behavior.
   If byte parsing cannot be proved, finish items 1–4 and state that boundary.

Return the full source, exact build commands/output and `#print axioms` for every
principal theorem. Use ordinary kernel-checked proofs: no admissions, custom
axioms, `native_decide`, `Lean.ofReduceBool`, unsafe code, externs, or weakened
targets. Keep dependencies limited to the pinned Lean distribution and existing
repository dependencies. Include a separately excluded false-equivalence target
that Lean rejects because the proposition is false. Do not report compilation or
an axiom audit without executing it. This work does not authorize purchases or
paid services.
