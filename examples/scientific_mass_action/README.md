# Authored synthetic biochemical workflow

This independent, standard-library example computes a three-species, two-reaction
finite rational Euler trajectory. Glucose cleavage and an authored isomerization
preserve elemental amounts. Rates are synthetic modeling assumptions rather than
validated biological kinetics. All source/model/example artifacts are CC0-1.0;
there is no private data and no human participant.

From this directory:

```bash
python run_workflow.py
```

This writes `observations.csv`. PCS discovery does not execute this source: the
experiment owner runs the explicitly authored script, then the PCS adapter checks
its resulting data against the independently implemented typed contract.

From the repository root, the complete frozen-protocol experiment can be rerun
into a **new** directory:

```bash
python scripts/run_scientific_assurance_v1.py --output /tmp/pcs-scientific-new-run
```

The experiment creates canonical signed packages, preserves an honest mass-leak
failure, rejects a producer-signed false numerical report in a fresh receiver
process, demonstrates prerequisite invalidation, and preserves a separate checked
repair proposal. Private signing keys stay in a temporary directory and are never
exported. The numerical certificate claim remains OPEN in PCS authority. See
[the workstream report](../../docs/PCS_SCIENTIFIC_WORKSTREAM_REPORT.md) for the exact
scope, commands, resource receipts and remaining scientific obligations.
