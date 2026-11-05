# Existing Project Integration Map

## CertiForge

Reuse conceptually:

- proof-carrying artifact architecture;
- independent checking over trusted generation;
- explicit TCB accounting;
- semantics/refinement methods;
- adversarial false-accept testing.

Do not copy source until IP/provenance is cleared. Prefer an adapter that can ingest an accepted CertiForge package as one evidence node.

## CASMI/QFD

Reuse conceptually:

- benchmark falsification lessons;
- split/self-match/collision-energy/replicate checks;
- reproducible scientific benchmark packages.

Near-term adapter: CASMI-style `evaluation_integrity` pack with structure-aware split audits and leakage checks.

## Proof-carrying AI safety work

Reuse conceptually:

- policy/authority traces;
- refinement from abstract policy semantics to executable events;
- explicit TCB and crash/recovery behavior;
- negative/impossibility results.

Near-term adapter: `trace_policy` evidence node; longer-term domain pack for AI agents.

## Carnot / pure mathematics

Keep primarily as independent fundamental research. It may inform validated numerics or geometry later but should not be forced into a product narrative.
