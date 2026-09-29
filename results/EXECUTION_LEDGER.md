# Execution Evidence Ledger

This file is the authoritative distinction between **repository inventory** and **executed evidence**.

## Current inventory on `main`

Draft PR #17 inventory as of 2026-09-29 after serialized-refinement hardening:

- 112 Python test functions are present under `tests/` (inventory count; not yet executed together).
- 28 adversarial attacks are encoded in `scripts/adversarial_campaign.py` (inventory count; not yet executed together).
- The production `formal/PCS*` sources are pinned to Lean 4.28.0 and the decision/normalized-state layer has a retained successful machine-check. New unfinished PR #17 obligations are isolated under `formal/ProofTasks/` and are not imported into the production root.

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

Those focused checks passed, but they do not substitute for a full current 112-test / 28-attack execution.

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

### Added since the last full retained execution

PR #17 additionally adds claim-scoped normalized decision export/verification, exact source-certificate reproduction, full required-evidence predicate binding, normalized-state package integration, valid-re-signing substitution attacks, wire/codec formal layers, version-consistency tests, and normalized-refinement release gating.

The current inventory additionally covers executable JSON Schema drift, duplicate-JSON parser differentials, pre-result pilot claim/assumption freezing, final delivered-bundle self-verification, signing-key overwrite/path safety, and additional cross-platform ZIP namespace attacks. These remain inventory until executed together from one commit.
