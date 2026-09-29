# Final Aristotle acceptance checklist

This checklist is the acceptance contract for the PCS formal handoff.

## Toolchain

Start from the repository's pinned toolchain. If Aristotle itself migrates the
project to a different Lean version, preserve and report the exact resulting
`lean-toolchain` value. Do not silently move the project back afterward.

## Required proof closure

Aristotle must close every designated `sorry` in:

- `Aristotle/Normalization.lean`
- `Aristotle/DecisionExtraction.lean`
- `Aristotle/SerializedBridge.lean`

Do not add `axiom`, `admit`, `unsafe` proof shortcuts, or replacement
`sorry` declarations.

## Required clean-library checks

The following files must compile unchanged in meaning:

- `PCS/Core.lean`
- `PCS/Decision.lean`
- `PCS/Refinement.lean`
- `PCS/Normalized.lean`
- `PCS/DecisionVectors.lean`
- `PCS/AcceptanceTests.lean`
- `PCS/PKPD.lean`
- `PCS/Audit.lean`

The acceptance tests deliberately check:

- missing required evidence -> OPEN;
- required FAIL -> FAILED;
- required UNVERIFIED -> OPEN;
- unrelated evidence cannot poison a claim;
- empty required evidence cannot support a claim;
- formal claims do not accept computational-test substitution;
- empirical claims do not accept formal-proof substitution;
- mixed assurance requires both formal and empirical/statistical roles;
- formal proof may act as stronger evidence for a computational claim;
- empirical/statistical evidence alone cannot support a computational claim.

## Required build

Run from `formal/`:

```bash
lake build
```

The final build must exit successfully.

## Required placeholder audit

After Aristotle has solved the staged files:

```bash
grep -R --line-number -E '\\b(sorry|admit)\\b' PCS.lean PCS Aristotle
```

Expected result: no proof placeholders.

Comments/documentation that merely mention the words should be reviewed manually;
the final Lean declarations must contain no unresolved placeholder.

## Required axiom audit

`PCS/Audit.lean` contains `#print axioms` commands for the current clean kernel.
After the direct decision/normalized bridge theorems are solved and promoted,
add their theorem names to the audit and capture the output.

Expected target: no unexpected project-specific axioms and no `sorryAx`.

## Semantic invariants that must not be weakened

1. `Assures.computational` permits either `computationalTest` or stronger
   `formalProof` evidence.
2. Formal assurance requires formal-proof evidence.
3. Empirical assurance requires empirical/statistical validation evidence.
4. Mixed assurance requires both formal correctness and empirical/statistical evidence.
5. Every assurance constructor requires PASS evidence.
6. Evidence must be explicitly required by the claim and predicate-bound.
7. Assumption context remains explicit via `ContextCovers`.
8. Raw JSON/schema/replay soundness is NOT silently collapsed into the pure
   decision theorem; the normalized bridge starts after that executable boundary.

## Return artifacts

Please preserve and return:

1. all modified Lean files;
2. exact `lean-toolchain`;
3. exact Aristotle/aristotlelib version if reported;
4. complete `lake build` result;
5. placeholder-audit result;
6. `#print axioms` output;
7. any theorem Aristotle believes is false, missing a precondition, or materially
   changed to compile.

A theorem that turns out to be false should be reported, not weakened silently.
