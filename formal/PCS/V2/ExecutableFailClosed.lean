import PCS.V2.ExecutableGeneral

/-!
# Fail-closed behaviour of `pcs-lean-authority`, for every input

Kernel-checked theorems about the exact pure decision functions run by
`pcs-lean-authority` (`executableAuthority` for `--zip`, `executableAuthorityEntries` for
directory mode, and the command-line wrappers `zipModeOutput` / `dirModeOutput`), for **all**
archive bytes, transcripts, keys and fingerprint pins.

## Rejection

* `executableAuthority_rejects_unregistered_type` (and the directory-mode and command-line
  forms): if the delivered certificate contains an evidence item whose `check_spec.type` is
  missing or is not one of the registered types (the six verified built-ins and the three
  registered domain checkers), the verdict is not `ACCEPT` â€” whatever the item's recorded
  outcome, whether or not any claim requires it, whatever the transcript reports, and
  whoever signed the archive.  The hypotheses only concern pre-acceptance parsing of the
  input bytes.
* `executableAuthority_rejects_false_supported_ai_claim`: a certificate claim recorded at an
  assurance level whose AI-safety predicate is false of the delivered trace bytes is rejected
  â€” for every transcript and trust anchor.

## Acceptance

* `executableAuthority_evidence_certified`: on `ACCEPT`, every evidence item has a registered
  check type, and its replay outcome is computed by a certified Lean checker *inside the
  executable's own executor* (whose fallback is the constant `FAIL`); a recorded `PASS` carries
  that checker's soundness proposition.
* `executableAuthority_supported_claims_sound`: on `ACCEPT`, every AI-safety or biology claim
  recorded at an assurance level holds of the committed artifacts â€” **with no obligation
  graph supplied by anyone, no `NoForgery`, and no assumption on the transcript**.  This is
  the claim-level bridge that was previously refuted for the transcript-fallbacdÑPÐ€L@öÛM¸r«