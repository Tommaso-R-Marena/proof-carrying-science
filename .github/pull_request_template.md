## Purpose

Describe the change and the user/scientific/verification problem it addresses.

## Scope and trust boundary

- What changes?
- What explicitly does **not** change?
- Does this alter a formal theorem, trust assumption, checker semantics, cryptographic boundary, CI gate, packaging contract, or public assurance claim?

## Branch / history reconciliation

- Base commit / current `main` considered:
- Supersedes or continues PR/branch:
- Any historical branch content intentionally ported:
- Any post-merge branch commits reviewed separately:

> Do not use ahead/behind counts alone as evidence that work is missing. PCS uses squash merges.

## Validation

- [ ] `python scripts/check_repository_integrity.py`
- [ ] Inspected `git diff --summary origin/main...HEAD` for unexpected mode/rename changes
- [ ] Focused Python tests / executable checks pass
- [ ] `./scripts/verify_lean.sh` passes if production Lean/authority paths are affected
- [ ] `./scripts/verify_lean_real.sh` passes if the Mathlib real-analysis bridge is affected
- [ ] Documentation/public claims match the exact tested state
- [ ] Temporary diagnostic CI has been removed or explicitly promoted to permanent policy

## Git metadata

List every intentional executable-bit, rename, line-ending, generated-manifest, or path-layout change. Write "none" if there are none.

## Remaining boundaries / follow-up

State what remains open. Do not turn a conditional or scoped result into an unconditional claim.
