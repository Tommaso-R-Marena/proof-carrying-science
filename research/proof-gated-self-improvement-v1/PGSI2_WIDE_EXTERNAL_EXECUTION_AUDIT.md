# PGSI2-WIDE external runtime correspondence: independently executed pilot

**Status:** experimental only; no production use, no merger into main.

**GitHub branch:** `research/pgsi2-runtime-correspondence-20261017`  
**Base:** isolated Aristotle V5 strong-gate integration PR #127.  
**Stacked draft PR:** #130.  
**Reproducible passing run:** https://github.com/Tommaso-R-Marena/proof-carrying-science/actions/runs/39071622887

## Question

Do independently written Python byte decoding and integer inference give the same observed output as the actual Lean V5 `ProofGatedNetArtifacts.decode` and `ProofGatedWide.predict` on exactly the same canonical artifacts, signed inputs, and architecture policy?

A related question is whether real Lean `ProofGatedStrongArtifacts.acceptStrongWire`, rather than a caller-provided mock, accepts and rejects the known interval-sensitive modifications.

## Files

- `pgsi2_wide_runtime.py`: independent strict byte parser, canonical encoder and exact integer network evaluation; `freeze_reference` returns a frozen local byte/model snapshot and checks an optionally supplied expected SHA-256 digest.
- `pgsi2_wide_lean_oracle.lean`: **research-only executable adapter** around the existing V5 Lean decoder, evaluator, and strong gate. It has no proof obligations and changes no formal Lean modules.
- `pgsi2_wide_differential.py`: actual cross-language invocation, deterministic fixtures, and strict observed-verdict comparison.
- `tests/test_pgsi2_wide_runtime.py`: independent Python golden, negative, seeded, byte-mutation, bounds and snapshot tests.
- `.github/workflows/pcs-pgsi2-wide-correspondence.yml`: Lean compile+axiom audit, Python tests, actual Lean runtime comparisons.

## Reproduced evidence (GitHub Actions)

- Lean 4.28.0 builds the strong-artifact/deep-certificate closure (**14 build jobs**) and its axiom audit passes.
- Independent Python tests **6/6** pass (including 300 seeded canonical model roundtrips with multiple signed inputs).
- Python and actual Lean agree on **760 model–integer-input predictions**: eight V5 golden wide networks plus 32 deterministic independently serialized networks, each across 19 inputs including \(\pm 10^{12}\).
- Lean and Python reject **15 malformed/missing-file cases**; test checks exact failures rather than interpreting any nonzero output as acceptance.
- Four actual Lean strong-gate / architecture-bound checks pass, including acceptance of `gen0→gen1` on \([-4,4]\), rejection on \([-50,50]\), and rejection under insufficient parameter bounds.
- The preexisting PCS PR #117 workflow also passed on this branch's earlier commits, preserving its original Lean-authorized PGSI1 CAS promotions and sealed inference.

These are tests of **specific cases**, not a proof of full semantic correspondence. In particular the 760 comparisons do not establish equivalence for all integer networks/inputs.

## Trust boundary and threat model

The mathematical V5 theorem applies to abstract canonical strings and Lean's mathematical `predict`. The host boundary remains deliberately outside this proof:

1. **Executable provenance:** an adversary with source or executable replacement rights can change the Python runtime and the Lean CLI. The CI runner is evidence of execution, not a protected third-party root of trust.
2. **Storage and symlinks:** Lean's `IO.FS.readFile` follows ordinary file paths and symlinks. The adapter has no sealed descriptor or symlink-rejection guarantee. A missing file exits unsuccessfully, but is an uncaught file exception, not a model theorem.
3. **Configuration authorization:** architecture limits, target bytes, corpus and robustness interval are CLI parameters. A malicious proposer who can choose those values could weaken a policy without changing either model. A real authority must independently pin and bind these settings and validate the whole certificate.
4. **Signatures/hash:** SHA-256 comparison within the same caller's privileges is integrity checking only; it does not authenticate an external authority or establish anti-rollback.
5. **IO/string boundary:** Lean `readFile` gives Unicode `String`; Python accepts a restricted ASCII byte grammar. These tests cover malformed UTF-8/Unicode examples but are not a formal byte-to-string refinement theorem.
6. **Lifetime and isolation:** the Python frozen snapshot avoids reopening mutable paths during inference but is not an OS-isolated process, cannot resist same-privilege memory mutation, and does not evidence protected atomic CAS.
7. **Model expressiveness:** exact scalar-input, finite-width integer ReLU networks, not arbitrary precision-floating hardware inference or multidimensional deep models. No general intelligence guarantee.

**Do not wire this standalone oracle directly to production promotions or describe its affirmative stdout as cryptographically authenticated.**

## Next necessary research milestone

After Aristotle V6 develops certificate/checker proofs, bind the entire strong policy (architecture, target, corpus, interval and expected incumbent generation) to an immutable or externally authenticated reference under a separate verifier process. Implement concrete byte- and runtime-refinement checks against this pinned reference and strengthen symlink/race/process-isolation tests. Verify production deployability separately.
