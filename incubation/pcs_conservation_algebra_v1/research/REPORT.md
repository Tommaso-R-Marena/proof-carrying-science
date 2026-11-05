# PCCA v1 research report

## Thesis

Scientific assurance needs a **proof-carrying conservation algebra**: not only
static reaction balance and not only one transport matrix theorem, but a general
stoichiometric invariant that receiving processes can check independently while
keeping continuum and empirical obligations OPEN.

## Delivered

- Lean 4.28 theorems: conservation under arbitrary firings; elemental bridge;
  rational checks; glucose / leak / exchange controls.
- Python engine: nullspace discovery, elemental derivation, Euler-as-fire replay,
  `pcca-cert-v1` certificates, adversarial rejection.
- Isolation: incubation-only tree with noninterference script.

## Experiments

| Fixture | Expected | Result |
| --- | --- | --- |
| Glucose cleavage | Accept C/H/O + trajectory | Accept |
| Mass leak | Reject elemental | Reject |
| Two-cell exchange | Accept moiety X, pool 7/4 | Accept |
| Producer verdict field | Reject | Reject |
| Non-stoichiometric trajectory | Reject | Reject |

## Relation to parallel work

Complements CertNum (intervals/ODE enclosures) and PCS Transport (matrix
invariants). Does not modify PGSC/PGSI, Aristotle integrations, or production
authority.

## Limits

Continuum accuracy, biology, and PCS scientific acceptance remain OPEN by design.
