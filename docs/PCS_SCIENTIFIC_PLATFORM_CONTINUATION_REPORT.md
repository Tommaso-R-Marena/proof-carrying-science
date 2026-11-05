# Scientific platform continuation: conservative finite-volume transport

PCS now accepts a reusable typed scientific workflow for conservative transport across an irregular cell network. It maps an explicit contract and finite trajectory into source-bound proof obligations, signs them through the **existing PCS v0.6 package authority**, and independently recomputes all numerical states and invariants in a fresh receiving process.

The example is an actual executed **CC0-authored synthetic numerical computation**, not field measurements, external empirical data or a scientific discovery. It adds spatial topology, heterogeneous cell volumes, conservative fluxes, a CFL stability condition and a bounded maximum principle beyond the existing mass-action and descriptive-regression adapters. Numerical, continuum and empirical PCS claims remain **OPEN**.

## Final executed evidence

The final frozen experiment is in [`research/scientific-workflow-v3/final`](../research/scientific-workflow-v3/final). [`PROTOCOL.json`](../research/scientific-workflow-v3/final/PROTOCOL.json) was written before execution and pins exact implementation, helper and producer/contract source hashes. Original source/license bytes are also signed in each package.

| Measured result | Final execution |
|---|---|
| Irregular-volume cells / undirected edges | 5 / 6 |
| Time steps / recorded states | 16 / 17 |
| Time step / final modeled time | 1/4 s / 4 s |
| Conserved amount at every state | Exactly `7/4 mol` |
| Initial weighted squared concentration | `73/64 mol²/m³` |
| Explicit bounded predicates | All 10 passed |
| Compiled PCS dimensional claims | All 3 `COMPUTATIONALLY_SUPPORTED` |
| Numerical / continuum / empirical claims | All `OPEN` |
| Fresh independent receiving processes | 5 |
| Deterministic archive reproduction | Byte-identical for the same key, input and fixed timestamp |
| NumPy 2.2.6 independent matrix-power baseline | All 17 states agree; max absolute error `2.220446049250313e-16`, predeclared tolerance `1e-12` |
| Focused tests | 40 passed in 11.25 s |
| Experiment wall time | 13.028 s |
| Self / child CPU time | 6.566 / 6.954 s |
| Largest child RSS, Linux | 31,812 KiB |
| Spend / training / human participants | Zero / none / zero |

The positive bundle SHA-256 is `e42cd03113e5f65b7eaa0399bb1dc05be50cf5689ed1980caa058cd252442681`. The final evidence-seal SHA-256 is `6426a87bc6f7567688ccb39c1720a3a11ff2e5f49556537580d5ae0c96f0e8c1`. This unsigned seal establishes byte consistency, not independent scientific review.

The producer PUBLIC key fingerprint for this experimental case is `641d1c28dbb6aeb20bd606cfbe406059d4782f339467d9b94485a8390e60d988`. It is an ephemeral experimental producer identity, not a production-root rotation or automatic model/scientific authorization. Private keys were temporary and are absent from retained evidence.

## Actual scientific mechanism

Each cell has a positive volume and nonnegative initial concentration. Each declared undirected edge has positive symmetric conductance. Units are explicit: volume `m³`, concentration `mol/m³`, conductance `m³/s`, and time `s`. No unit-scale guessing is performed.

For each edge, the independently authored producer moves the amount `dt × conductance × (left concentration − right concentration)`, with equal and opposite inventory changes. It then divides cell inventory changes by each cell's own volume. The receiver independently reconstructs a transition matrix and evolves matrix rows using exact rational arithmetic. It does not execute or import the submitted producer.

The CFL requirement is `dt × sum(incident conductance) / cell volume ≤ 1` for every cell. Unsupported or unstable contracts fail explicitly. Under this supported discrete contract the receiver checks:

- Exact declared time grid and agreement of every state with independently reconstructed evolution.
- Nonnegative concentrations and the initial minimum/maximum bound.
- Exact volume-weighted **amount** conservation at every recorded state.
- Nonincreasing volume-weighted squared-concentration functional.
- Finite transition-matrix nonnegativity, row sums of one, and volume-weighted column invariance.
- Three source-derived dimensional predicates through the existing compiled PCS checker.

The squared-concentration functional has units `mol²/m³`; it is **not thermodynamic energy**. The conserved quantity is amount in mol, not mass in kg. Continuum discretization accuracy, material geometry, boundary applicability and empirical behavior are not established.

Resources are bounded to 16 cells, 64 edges, 64 steps, 2 MiB per artifact and existing 4,096-bit rational limits. The existing rational text grammar also limits supplied individual scalar strings. These are limits of the executable fragment, not evidence of scientific adequacy or arbitrary problem scalability.

## Integrated intake and replay

New implementation: `pcs/scientific_workflow_v3.py`, `scripts/run_scientific_workflow_v3.py`, `tests/test_scientific_workflow_v3.py`, and [`examples/scientific_workflow_v3`](../examples/scientific_workflow_v3). Existing scientific v1 helpers, signed bundle format, Claim IR, proof-obligation propagation and compiled authority are reused; existing hash-bound v2 implementations and evidence are unchanged.

Run the authored experiment with a new output path:

```bash
source /workspace/.onboarding/activate.sh
python scripts/run_scientific_workflow_v3.py --output /tmp/pcs-transport-experiment-new
python -m pytest tests/test_scientific_workflow_v3.py -q
```

The bounded intake accepts a separately prepared eligible project with `contract.json` and its declared trajectory CSV, retaining all safe source artifacts while running **no submitted code**:

```bash
python scripts/run_scientific_workflow_v3.py \
  --project /path/to/eligible-project --work-directory /tmp/pcs-transport-work \
  --output /tmp/transport.pcs.zip --private-key /secure/producer.pem \
  --public-key /path/to/producer-public.pem --fingerprint PINNED_FINGERPRINT \
  --confirm-reviewed-draft
```

The confirmation flag records only the caller's explicit confirmation of the bounded generated draft. It is not authenticated independent review. The builder uses existing discovery, exact-source inventory, manifest confirmation, Ed25519 signing, compiled checking and verified ZIP creation. Every receiving run first verifies that PCS package, pins the exact local adapter/helper sources, and recomputes the report and dependency graph. Canonical sidecar bytes must match exactly, preventing bool/number equality from admitting a forged report.

Replay the retained final case in a fresh process, using a new receipt path:

```bash
python scripts/run_scientific_workflow_v3.py \
  --replay research/scientific-workflow-v3/final/positive.pcs.zip \
  --public-key research/scientific-workflow-v3/final/producer-public.pem \
  --fingerprint 641d1c28dbb6aeb20bd606cfbe406059d4782f339467d9b94485a8390e60d988 \
  --output /tmp/pcs-transport-fresh-receiver.json
```

`pcs_package_valid`, `independent_replay_consistent`, `bounded_contract_satisfied` and `scientific_acceptance` remain different fields. Bounded success requires actual compiled dimensional support **and** fresh numerical replay. Package validity alone cannot certify an incorrect or unsupported scientific claim. Scientific acceptance remains false. This is a functioning local platform intake/replay interface; no new remote execution backend, production database mutation or paid hosting is introduced.

## Preserved negative results

Five actual fresh receiver runs cover the positive case and four signed negative cases:

1. An actual amount leak changes the last cell state: the signed package is valid, but conservation, maximum-principle, functional and model-step checks fail with explicit row witnesses.
2. An incorrect final uniform state preserves total amount, positivity, initial min/max and the decreasing functional. It still fails exact model-step replay. Conservation alone cannot establish that a trajectory implements the intended discretization.
3. A false final-amount report is re-signed with the legitimate ephemeral producer key. Existing package integrity passes; the independent receiving algorithm rejects the report.
4. A legitimately signed dimension claim is `FALSIFIED_OR_CHECK_FAILED`; the workflow receiver cannot turn package validity into bounded success.

The experiment also rejects an actual CFL violation and records transitive invalidation after changing a modeling premise or trajectory bytes. Combining a plan with a report for different trajectory bytes is rejected. Tests cover malformed and ragged data, missing/extra states, negative/nonfinite values, wrong time grids, invalid units/topology, duplicate or reversed edges, zero volumes, an oscillatory case exactly at the CFL boundary, missing confirmation, wrong key pins, generic CLI intake/fresh replay and signed bool/number confusion.

An earlier mathematically correct execution used misleading `mass_mol` diagnostic names. It is retained unchanged under `preceding-amount-label-cleanup`, explicitly superseded by the current amount-based names and final source pins. It is not counted as a second scientific/generalization result. The amount terminology correction changes no underlying trajectory values.

## Remaining scientific and formal obligations

No source-bound Lean theorem currently refines this Python adapter or the producer's implementation. The finite matrix/invariant checks are executed arithmetic checks, not a claim of a general Lean proof for all discretizations. A valuable formal next step is a theorem for finite volume-weighted stochastic transition matrices establishing amount preservation, positivity, a maximum principle and weighted quadratic contraction, followed by source-bound extraction/refinement of the implemented parser and update loop.

There is no established continuum error bound, derived mesh geometry, empirical material validation, authenticated independent reviewer, learned scientific policy or autonomous discovery result. One bounded synthetic scientific algorithm is demonstrated; unfamiliar empirical workflows and general scientific competence remain OPEN. All historical evidence, current limitations and negative controls are preserved without promoting model or scientific authority.
