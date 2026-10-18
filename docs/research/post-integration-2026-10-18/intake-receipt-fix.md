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

## Explicit source-profile successor

The original `docs/integration/2026-10-18/SOURCE_PROFILE.json` is preserved
byte-for-byte, SHA-256
`0610914446b24a6b2e7fb70cd385155531c42d65a95ec04b896d37c29f9d7297`.
The raw expected pre-successor two-file mismatch is retained in
`intake-receipt-source-gate-before.json` alongside this report.

A fixed-path, versioned `receipt-source-profile-successor.json` records exact
predecessor commit/profile identity, old/new source hashes, mode and reason.
Only three predecessor entries can progress: the intake implementation, its
tests, and the identity gate itself. The existing receipt contract is one
additional pinned source file; it was not in the predecessor profile. All 1,992
original checks, all 38 V7 modules, and all baseline formal protections remain
mandatory.

The gate code pins both old and permitted new identities for the three repair
files. Editing a source file and its manifest hash together cannot authorize
another replacement. Duplicate/unknown manifest keys, extra paths, wrong hashes,
mode changes, symlinks, and unrelated source mutations reject. No environment
variable or caller-selected profile participates. The gate's own exact new SHA
is recorded and checked by the successor, with its predecessor SHA fixed by
code; reviewing a change to gate code remains essential. The repository, Git,
reviewed gate code and reviewed manifest remain trusted configuration, not an
immutable root. `pending_independent_review` is metadata, not approval.

The independent reviewer separately validated code commit `8c1aa88`: all 28
actual-Lean decisions matched its prior observations, all 20 previously blocked
negative receipts became writable, and 176 fresh contradictory receipt mutations
rejected. This validates bounded behavior and receipt consistency; it does not
constitute a general theorem about receiving acceptance sets.

Combined final local run: **120 passed, zero skips**, 36.38 s, including all 105
affected behavioral tests plus 15 source-successor checks (one positive and 14
negative controls). The identity gate passes all 1,992 predecessor entries plus
one additional receipt-contract pin. JUnit evidence for this session is
`/workspace/.onboarding/intake-receipt-combined.xml`; pre-successor and initial
partial-provisioning results are retained separately, not overwritten.

## Independent successor falsification and repair

Independent source review of `08f0a751` found one unsupported boundary claim:
changing the gate file and its self-hash manifest together could pass while the
previous gate code remained loaded. Eleven other independent identity controls
behaved as expected. The review's raw negative evidence is preserved in its
`SOURCE_SUCCESSOR_REVIEW_08f0a75.json`; the earlier 120-test result above predates
this additional attack and does not claim to cover it.

Commit `a7e2b50` requires the fixed successor file's bytes to equal the exact
object at `git show HEAD:<fixed successor path>`. The temporary test repositories
now commit their initial fixtures. Invalid hash/path/source-plus-manifest
controls are also committed before checking, so they still exercise the
hard-pinned identities independently of the working-tree boundary. Two new
controls reject uncommitted gate-plus-manifest substitutions and review-status
changes.

This is a Git-commit identity boundary with explicitly trusted gate code, Git
and reviewed HEAD. An actor able to replace the trusted commit and its verifier
code is outside that boundary. It is not an external immutable execution root.
No artifact receiving acceptance or actual Lean verdict changed in this repair.

Final local committed-source candidate `a7e2b50`: **122 passed, zero skips**, in
38.13 s (105 behavioral and 17 identity checks). The intentional duplicate-ZIP
warning remains. JUnit: `/workspace/.onboarding/intake-receipt-final-committed-successor.xml`.
Independent final successor review is tracked separately; this document does not
self-approve it or PR #153.
