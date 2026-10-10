# Aristotle Omega/decision-diagram integration

Returned run: `b9577162-8244-44ff-83ca-dc7efe9d95a4`.
Archive SHA256: `5bbe5fdcae4acad3d7bbe48de26559e89bc2eae2c0681a23526e2cedf4ea95a6`.
Base: core `e0c4f7b3af37f1ae42eb5f4cbee8937f9dc93604`, site `711acdcb088654904e42d7cb94cbdd400df6eb7d`.
Lean: exact 4.28.0 release, commit `7e01a1bf5c70fc6167d49c345d3bf80596e9a79b`.

## Evidence boundaries

The new `PCSOmega` and `PCSDecisionDiagram` libraries are executable typed reference models.
They prove general evaluator, checker, replay, named-lowering, BDD apply/compile/canonicity,
conditional-conflict/witness and strictly-positive-cost Bellman contracts. They do not prove
that the Python or JavaScript engines refine those models. The existing authority libraries,
import graph, toolchain and dependency lock are byte-identical to the supplied baseline.
Models remain untrusted proposal policies. All browser/Python and new reference receipts
retain false scientific-authority and per-result Lean-kernel flags.

`formal/PCS_OMEGA_DECISION_DIAGRAM_REPORT.md` preserves Aristotle's returned report.
`returned-logs/` contains its submitted logs, not our independent build evidence.
`source-manifest.json` binds returned source and archive identity. The integration gate
checks source identity, active admissions, complete declared axiom inventories and the
precise mathematical rejection of deliberately false equivalence/minimum/mandatory claims.

## Executed finite runtime comparisons

`parity/result.json`, `parity/tasks.json`, `parity/Parity.lean` and both native implementation
receipt files retain 91 actual Lean/Python/JavaScript comparisons: 54 optimal plans,
12 infeasible goals, 10 contradictory contexts and 15 resource limits. There are zero
output disagreements, including complete diagram tables, exact work counters, witnesses,
Bellman cells, lexicographic assignments, counts and necessity/possibility masks.
Seventy-four resolved cases through six variables additionally match an independent
exhaustive truth-table optimization oracle. Larger cases are explicitly finite controls,
not an exhaustive evaluation of the 24-variable input domain or an implementation theorem.
The JavaScript receipts also match the Python receipts including canonical content hashes.

The 457 targeted Omega, conditional, intervention and integration tests pass locally.
Seven gate integrity tests reject missing/duplicate/substituted axiom inventories, custom
axioms, non-semantic negative failures, extra compiler errors and false success statuses.

## Reproduction

```sh
source scripts/activate_lean_428.sh
bash scripts/verify_lean.sh
python scripts/verify_omega_dd_formal.py --output NEW_AUDIT_DIRECTORY
python scripts/verify_omega_dd_parity.py --site ../proof-carrying-science-site --output NEW_PARITY_DIRECTORY
python -m pytest -q tests/test_omega_dd_integration.py tests/test_conditional_reasoning.py tests/test_intervention.py
```

The parity program emits actual reference results from generated typed tasks; it does not
accept arbitrary user Lean or shell code. Its output codec and Python lowering remain
unproved integration software. PR CI uses pinned public browser modules with no credentials
and independently executes these gates. No new artifact upload is introduced.

## Open obligations

Python/JavaScript refinement, JSON/text decoding, hash/serialization/authentication/browser
assumptions, search-to-replay completeness, scientific grounding and authority correspondence
remain open. Zero-cost change weights remain rejected; a feasible baseline can legitimately have optimal objective zero. This package establishes no learned
accuracy gain, new model checkpoint, RL improvement or novel mathematical discovery.
No financial service, paid runner/GPU, billing information or production D1 mutation is used.

Independent build, complete axiom/negative logs and protected release identities are recorded
separately once their checks complete; submitted build success is not substituted for them.

## Independent build resource diagnosis

The first fresh unrestricted parallel `lake build` ran all 291 jobs but exited 1: the
large control module was killed by the 32 GiB environment limit (exit 137). General
proof modules and existing authorities completed. `independent-build.json` records
585.1 wall seconds and 24,317,528 KiB peak child RSS; this is a failed build, not success.
`general-audit.json` independently records 214 checked general theorem inventories
and all three intended false-claim rejections.

Integration preserves every returned Lean source byte. The Lake configuration builds
reference libraries with the authorities and runs `PCSControls` afterward through the
required `verify_lean.sh` gate. New library compilation uses one Lean thread and a
6000 MB limit. This is a resource profile change, not a reduced assertion, admitted
proof or weakened theorem. The original returned configuration hash is retained
separately from the integration configuration hash. Heavy control verification and
protected CI remain release prerequisites.
