# Causal counterexample library

Each entry has exact mathematical ground truth where feasible. These are pedagogical / adversarial fixtures, not empirical discoveries.

| ID | Mistake | Graph sketch | Expected |
|----|---------|--------------|----------|
| C1 | Confounding | Z→X, Z→Y, X→Y | Empty adjustment invalid; {Z} valid |
| C2 | Collider bias | X→C←Y | Empty valid for X–Y causal effect (none); {C} invalid |
| C3 | Mediator adjustment | X→M→Y | Empty valid backdoor; {M} invalid |
| C4 | M-bias | U1→X,U1→C,U2→Y,U2→C | Empty valid; {C} invalid |
| C5 | Reverse causation | Y→X | Interpreting assoc as X→Y effect unsupported |
| C6 | Positivity failure | Supported in estimation diagnostics | Formula undefined / unstable |
| C7 | Selection | S←Y, treat on selected | Observational law ≠ population |
| C8 | Non-identifiability witness | Latent U confounding | Two models, same P(X,Y), different P(Y\|do(X)) |

Executable checks: `pcs_causal.benchmarks.adversarial.run_adversarial_suite` and `tests/`.
