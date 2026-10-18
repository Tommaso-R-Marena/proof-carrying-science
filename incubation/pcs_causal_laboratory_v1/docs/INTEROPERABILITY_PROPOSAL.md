# Future PCS interoperability proposal (read-only design)

**Status:** Proposal only. No production PCS Claim IR import. No verification-authority changes. No cross-repo automated merges.

## Exported objects (versioned)

Suggested bundle media type: `application/vnd.pcs-causal.export.v1+json`

| Object | Meaning | Authority |
|--------|---------|-----------|
| `causal_query` | Target estimand | Declaration |
| `assumed_model` | Graph / SCM class | Assumption |
| `identification_expression` | Functional of observational law | Mathematical (if checker accepts) |
| `derivation_certificate` | `pcs-causal-cert-v1` | This project's verifier |
| `nonidentifiability_witness` | Model pair + TV checks | This project's verifier |
| `statistical_estimate` | Point/interval estimate | Statistical, assumption-qualified |
| `uncertainty_analysis` | CIs, positivity, sensitivity | Statistical |
| `experiment_design_proposal` | Simulated intervention plan | Computational design |
| `explicit_assumptions` | Listed premises | Human / scientific |

## Authority separation

1. **Mathematical theorem** accepted by this project's trusted checker.
2. **Statistical evidence** from samples under estimation assumptions.
3. **Scientific model assumptions** (not validated by math certificates).
4. **Empirical interventions** (not produced by this laboratory).
5. **Human interpretation**.
6. **Unresolved causal validity**.

A mathematical certificate must never confer automatic scientific acceptance in PCS.

## Integration constraints

- Narrow, versioned export only.
- PCS remains fail-closed on unsupported kinds.
- This incubation package stays independently buildable without PCS production infrastructure.
