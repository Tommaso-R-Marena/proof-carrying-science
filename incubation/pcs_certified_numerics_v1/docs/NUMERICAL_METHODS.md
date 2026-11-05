# Numerical methods notes

- Prefer exact `fractions.Fraction` endpoints.
- Subdivision always bisects at exact rational midpoints.
- Exp enclosure order defaults to 16; increases if `z ≥ n`.
- Optimization pruning uses leaf lower enclosures vs incumbent upper bound.
