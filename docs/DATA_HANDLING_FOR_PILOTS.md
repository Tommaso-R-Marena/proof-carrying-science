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

## Retention

The pilot agreement should state a retention period and deletion process. Default operational preference: retain the final signed certificate and permitted evidence package; delete unnecessary raw partner data after the agreed closeout window.

## Research separation

Commercial partner data must not be used to support academic claims, publications, benchmarks, or model training unless the partner has explicitly granted that use and any required institutional approvals have been obtained.
