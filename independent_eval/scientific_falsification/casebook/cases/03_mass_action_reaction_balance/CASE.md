# Mass-action stoichiometry via reaction_balance

**Case ID:** `03_mass_action_reaction_balance`
**PCS checks:** `reaction_balance`
**License:** CC0-1.0

## Assumptions

- Element balance of authored synthetic cleavage only; no kinetic validation.

## Expected results

- Certify/verify PASS for balanced C6H12O6 -> 2 C3H6O3.

## Negative controls

- Unbalanced 1:1 cleavage fails reaction_balance.

## Reproduction instructions

```bash
pcs certify independent_eval/scientific_falsification/casebook/cases/03_mass_action_reaction_balance/manifest.json -o /tmp/pcs-sf-03_mass_action_reaction_balance
pcs verify /tmp/pcs-sf-03_mass_action_reaction_balance/certificate.json
```

## License metadata

```json
{
  "spdx": "CC0-1.0",
  "statement": "All authored fixtures under independent_eval/scientific_falsification are dedicated to the public domain under CC0-1.0. No human participants; no private data."
}
```
