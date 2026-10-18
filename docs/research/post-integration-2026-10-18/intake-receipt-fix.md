# Receiving intake veto and negative receipt repair

Base: `b916eec1b9d0d5c02c9cc19b070f7a47df5e5d87` (PR #153).
Branch: `fix/pcs-intake-veto-receipts-v1-20261018`.

## Independently reproduced defect

The independent post-PR #153 review found a receiving-contract regression:
real Lean accepted an internally valid signed package, then receiving intake
binding correctly rejected it. The result retained the true Lean verdict,
Lean stage, and exact-package mathematical coverage, but set overall `valid`,
`authoritative`, and `accepted` false. The receipt contract incorrectly required
all these different observations to agree, preventing negative receipt writing,
signing, and the CLI's normal rejection exit status.

The independent review's 28 same-byte ZIP/directory cases found 28 baseline
accepts, eight post-integration accepts, and 20 correct intake rejections which
could not be written as receipts. This is external review evidence, not a claim
that this repair's author independently repeated that entire corpus. Independent
revalidation of this repair is tracked separately by the reviewer.

## Minimal repair

- Keep the actual Lean `ACCEPT`, its stage, executable/transcript identity,
  certificate binding, and mathematical replay coverage unchanged.
- Keep the overall receiving rejection and existing acceptance gate unchanged.
- Admit the distinct negative receipt only for a structured, internally
  consistent intake veto: failed intake stage, exact failed-stage designation,
  invalid intake, appropriate required/present state, coherent detailed stages,
  recorded member identity when present, and nonempty propagated errors.
- Record the exact receiver-supplied expected intake semantic hash as structured
  metadata. When the lock parsed successfully, its actual/expected hash relation
  must agree with the recorded stage.
- Audit Lean stage/coverage against the actual Lean verdict. Neither field is an
  assertion of final receiving acceptance.
- Reject an accepting receipt that also records an invalid intake.

This changes no Lean source, theorem, production package verifier, authority
executable, acceptance policy, certificate schema, historical evidence, or
contributor branch. It does not turn a Python rejection into a Lean rejection.

## Tests and execution assumptions

The focused receipt/signature/intake suite passed **38 tests, zero skips**.
The full selected affected suite passed **105 tests, zero skips**, in 19.65 s:

```
PATH=/workspace/.onboarding/tools/lean-4.28.0-linux/bin:$PATH \
PCS_REQUIRE_LEAN_AUTHORITY=1 \
/workspace/.onboarding/pcs-integration-env/bin/python -m pytest -q \
  tests/test_verifier_v06.py tests/test_zip_verify_v06.py \
  tests/test_cli_verify_v06.py tests/test_lean_authority_v06.py \
  tests/test_receipt_contract_v06.py tests/test_receipt_signature_v06.py \
  tests/test_intake_verify_v06.py tests/test_attest_v06.py \
  tests/test_attest_v06_intake_lock.py tests/test_policy_v06.py \
  tests/test_formal_coverage_v06.py tests/test_external_validator_attestation_v06.py \
  tests/test_provenance_v06.py tests/test_quorum_v06.py \
  tests/test_local_verify_v06.py tests/test_adversarial_v06_hardening.py
```

The one warning is the existing intentional duplicate-ZIP-member fixture. An
initial run without Lean/Lake on PATH produced 103 passes and two explicit
skips; it was corrected and rerun, without altering tests.

Nineteen new regression cases cover eight real-Lean ZIP/directory negative
receipts (expected-hash mismatch, required missing lock, invalid lock, and
certificate/lock mismatch), two actual CLI signed-negative-receipt paths, and
nine contradictory-veto mutations. Exact-byte signatures and external bundle,
producer-key, and authority hashes replay successfully; post-signature mutations
reject. These authorization tests do not substitute a mock positive verifier.
Inherited unit tests may use diagnostic mocks and are not presented as native
authorization evidence.

For resource isolation, this worktree uses a copied previously built authority
from the PR #153 integration checkout. All 822 tracked formal paths were
compared between worktrees; regular-file contents were identical. The copied
executable SHA-256 is
`3fd286e68299ad399b59078618045cdaedac3bd0d55305d074005ade16317b49`.
This is actual native execution with exact preserved source, not a fresh compiler
rebuild or independent executable attestation. Host, toolchain, compiler, and
storage assumptions remain explicit.

## Boundaries and remaining review

A coherent receipt is a signer's attestation of observations. This contract
neither proves that the recorded execution historically occurred nor independently
replays its scientific package. A reviewer signature authenticates exact receipt
bytes, including a rejection; it does not make that rejected package valid.
A fabricated but internally coherent veto signed by a compromised reviewer is
outside what structural auditing can prevent.

The inherited integration source profile pins the imported intake module and
its tests. Any published successor must explicitly record their reviewed source
identity progression; silently weakening that gate is prohibited. Historical
PR #153 evidence and original source identities remain retained.

No merge, deployment, source PR modification, or approval of PR #153 is performed
by this repair branch.
