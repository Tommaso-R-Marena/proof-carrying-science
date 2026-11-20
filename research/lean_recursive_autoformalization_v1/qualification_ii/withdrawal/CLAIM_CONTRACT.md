# Qualified verdicts for interpreted claims

`ClaimContract.receive` joins a reviewer-approved source interpretation and a finite evidence table at an exact subject and withdrawal budget. A causal subject identifies a model, assumptions and estimand. A policy subject identifies a policy, trace and criterion. A mathematical subject identifies a formal reference and candidate statement. All three include a source ID. The receipt and its display carry the entire requested scope. Changing an identifier or presenting evidence from another budget fails the binding check.

Unparsed and ambiguous interpretations have distinct decisions. An absent table gives insufficient evidence. Duplicate world or group IDs and a budget larger than the group count are invalid. If no world fits all groups, the evidence is inconsistent. On a grounded table, the receiver applies `Withdrawal.check` to both polarities. A mixed set of possible surviving interpretations yields insufficient evidence. A robust negative decision requires every surviving interpretation to refute the claim.

`PCSResearch.ClaimContract.decided_sound` proves that every decided receipt preserves the request, the interpretation equals its reviewed subject, the evidence scope exactly matches, and some listed world fits the complete evidence. For every withdrawal mask costing at most the requested budget, every listed surviving world has the asserted polarity. This applies to arbitrary world and group types with decidable equality. Its axiom audit reports `propext` and `Quot.sound`.

The caller authenticates the interpretation, identifiers and association of a table with its predicate. Completeness of the listed worlds and correct grouping of evidence with shared provenance remain application assumptions. The synthetic mathematical verdict concerns agreement with a supplied reference on the specified interpretations. A kernel proof of an arbitrary mathematical statement requires its own evidence. The numerical contrast and policy examples likewise depend on their supplied models and policy meanings.

The fixtures compare a hypothetical treatment risk with a fixed control risk, check required approval for a write, and evaluate double negation against a Boolean reference. An independent direct enumeration covers all 64 assignments of four agreement bits and two target bits over two worlds and two groups, at each of three budgets. All 192 decisions agreed. Separate negative fixtures cover ambiguous and unparsed inputs, absence, inconsistent evidence, mixed evidence, repeated groups, invalid budgets, and substitutions of domain, source and budget.

With the repository-pinned Lean 4.28.0 on PATH, run from this directory.

```sh
out=$(mktemp -d)
cp Withdrawal.lean ClaimContract.lean ClaimContractCases.lean "$out"
(
  cd "$out" || exit 1
  export LEAN_PATH=.
  set -e
  for mod in Withdrawal ClaimContract ClaimContractCases; do
    lean -DwarningAsError=true -o "$mod.olean" "$mod.lean"
    leanchecker "$mod"
  done
)
```
