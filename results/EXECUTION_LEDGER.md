# Execution Evidence Ledger

This file is the authoritative distinction between **repository inventory** and **executed evidence**.

## Current inventory on `main`

As of 2026-09-28 after ZIP namespace hardening:

- 64 Python test functions are present under `tests/`.
- 22 adversarial attacks are encoded in `scripts/adversarial_campaign.py`.
- Lean sources target Lean 4.16.0 and contain no intentionally admitted `sorry` proofs.

Inventory counts are not execution results.

## Last retained full execution evidence

The last retained full local/reference execution before later provenance/refinement/security additions established:

- 44/44 Python tests passing;
- 16/16 targeted adversarial attacks rejected;
- 0 false accepts in that finite campaign.

Those results are implementation evidence only; the finite campaign is not a security proof.

An older `FOUNDING_VERDICT.md` revision stated 49/49 tests passing, but the repository does not retain a machine-readable execution log that distinguishes that run from later inventory edits. PCS therefore does **not** use 49/49 as an authoritative current execution claim.

## Directly exercised after the last full campaign

The ZIP namespace validator added after the last full campaign was directly exercised in the development environment against:

- duplicate member names;
- a regular file used as a parent of another ZIP member;
- `./` path aliases;
- doubled-separator aliases;
- `..` traversal;
- backslash paths.

Those focused checks passed, but they do not substitute for a full 64-test / 22-attack execution.

## Hosted CI blocker

GitHub Actions jobs in this repository have repeatedly completed with:

- `runner_id = 0`;
- empty runner name;
- `steps = []`.

Therefore no checkout, Python test, adversarial campaign, or Lean build is known to have executed in those failed hosted jobs. See `results/CI_RUNNER_STATUS.md`.

## Promotion rule

Do not promote the inventory counts into PASS claims until one environment executes, from the same commit:

1. `pytest -q`;
2. `python scripts/adversarial_campaign.py`;
3. the reference certificate round trip;
4. the no-`sorry` audit;
5. `lake build` for the Lean kernel.

When that happens, record the commit SHA, environment identity, commands, exit codes, and resulting counts here.
