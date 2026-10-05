# Pilot Data-Handling Principles

This is an engineering policy draft, not legal advice or a substitute for a negotiated data-processing agreement.

## Default posture

PCS should request the minimum data necessary to evaluate the agreed computational claims. Prefer synthetic, de-identified, or non-sensitive examples for early design-partner work whenever they are sufficient.

## Prohibited by default

Do not request or accept, without an explicit reviewed agreement and appropriate infrastructure:

- direct patient identifiers;
- protected health information;
- production credentials or secrets;
- unrelated proprietary datasets;
- export-controlled or otherwise restricted data;
- data that the partner is not authorized to provide.

## Isolation

Each partner engagement should use a separate private workspace. Access should be limited to personnel necessary for the engagement. Partner artifacts must not be copied into public examples or unrelated research repositories.

## Provenance

Record cryptographic hashes of source artifacts at intake. Transformations made for PCS analysis should be separately identified rather than silently replacing the originals.

## Retention and deletion

The pilot agreement should state a retention period, closeout trigger, and deletion process. Default operational preference: retain only the final signed assurance records and other expressly permitted evidence; delete unnecessary raw partner data and temporary working copies after the agreed closeout window.

PCS now has a fail-closed local closeout mechanism in `scripts/pilot_closeout.py`:

- the plan must classify every regular workspace file as RETAIN or DELETE;
- it binds exact size/SHA-256 for each file;
- apply requires the exact plan hash;
- any added, removed, modified, or symlinked file aborts the operation;
- only planned DELETE files are unlinked;
- a hash-bound receipt records what was deleted and what remained.

Use `docs/PILOT_CLOSEOUT.md` for the operational procedure.

The receipt is evidence of the local closeout execution only. It is **not** proof of secure media erasure or deletion from cloud snapshots, backups, transfer services, or third-party systems.

## Research separation

Commercial partner data must not be used to support academic claims, publications, benchmarks, or model training unless the partner has explicitly granted that use and any required institutional approvals have been obtained.
