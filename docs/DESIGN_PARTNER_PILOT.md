# Design-Partner Pilot

## Product sentence

PCS produces independently replayable evidence that a computational scientific workflow satisfies a declared set of scoped assurance claims under explicit assumptions.

## Ideal first design partner

A small or medium biopharma, CRO, pharmacometrics group, quantitative systems pharmacology team, or computational-biology team with:
- custom modeling code;
- expensive review/reproduction burden;
- a concrete internal workflow rather than a request to verify "all science";
- willingness to start with non-sensitive, synthetic, or de-identified artifacts.

## Pilot input

The partner provides one bounded computational workflow and states 3–10 claims they care about, such as:
- specified datasets are disjoint;
- units are dimensionally coherent;
- a declared PK/PD representation satisfies its structural contract;
- exported predictions match the declared equations within a stated tolerance;
- provenance artifacts correspond to the reviewed run.

## PCS work

1. Convert the requested claims into machine-readable predicates where possible.
2. Record assumptions explicitly.
3. Package inputs by cryptographic hash.
4. Run/replay the supported checks.
5. Red-team the certificate and workflow bindings.
6. Deliver an HTML report, JSON certificate, signed signature record, reproducible evidence ZIP, and limitation statement.\n7. Ask the independent reviewer to persist a PCS verification receipt that binds the exact bundle and reviewer policy used.

## Explicit non-goals

The pilot does not establish:
- clinical validity;
- model adequacy for a drug or population;
- regulatory acceptability;
- correctness of arbitrary unsupported code;
- security of systems outside the defined assurance boundary.

## Success criterion

A partner scientist who did not produce the original run can independently answer:
- what was claimed;
- what assumptions were required;
- what exact artifacts were used;
- which checks ran;
- whether those checks can be replayed;
- which claims remain open;
- what changed between two runs.
