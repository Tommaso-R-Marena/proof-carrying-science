# Restricted PK/PD Adapter v0.1

## Supported PK model

One-compartment IV bolus with first-order elimination:

\[
C(t)=\frac{D}{V}\exp\left(-\frac{CL}{V}t\right).
\]

## Supported PD model

Optional direct Emax response:

\[
E(C)=E_0+E_{\max}\frac{C}{EC_{50}+C}.
\]

The adapter verifies a **computational contract**, not biological truth.

### `pkpd_contract`

Checks finite/positive PK parameters, dimensional consistency for Dose, V, CL, time and concentration, and—when the direct Emax layer is present—compatibility of EC50 with concentration and E0/Emax with the declared effect unit.

### `pkpd_reference_match`

Replays both analytic equations independently from the JSON model artifact and compares every row of a prediction CSV against the reference under explicit relative/absolute tolerances.

### `pkpd_peak_concentration_threshold`

Checks that a non-empty committed prediction CSV contains the declared concentration column, that every value is a strict non-negative PCS decimal, that the threshold unit exactly equals the model artifact's declared concentration unit, and that every committed row is at or below the committed upper bound. This certifies the maximum **reported table value** only; it is not a theorem about the continuous-time analytic maximum or clinical safety.

This establishes: **the artifact is consistent with the declared restricted PK/PD model within tolerance**.

It does not establish one-compartment adequacy, direct-Emax adequacy, population validity, identifiability, goodness of fit, patient predictive validity, regulatory acceptability, or arbitrary ODE-solver correctness. Those remain separate empirical/statistical/formal obligations.

## Next increments

1. oral absorption;
2. two-compartment IV;
3. Hill Emax / indirect response;
4. parameter/covariate schemas;
5. observation/noise models;
6. restricted ODE IR;
7. equation-to-generated-code refinement;
8. numerical solver error certificates;
9. NONMEM/Monolix/R/Python import adapters.
