# HECK architecture

## Trust boundary

```text
Untrusted producer
  → proposes atoms, composite claims, theory objects, predictions
Independent HECK receiver
  → re-evaluates leave support flags (caller-supplied for v1),
     recomputes meet, checks required ≤ achieved,
     discharges predictive obligations against observations,
     emits deterministic receipts
Lean reference model
  → proves the composition/predictive laws on the typed IR
```

v1 leaf `supported` bits are inputs from upstream independent checkers
(transport kernel, calibration kernel, computational replay, …). HECK does
not re-prove those leaves; it forbids conflating their assurance classes.

## Objects

| Object | Role |
| --- | --- |
| `Level` | Ordered assurance class |
| `EvidenceAtom` | Leaf evidence with level + support + content digest |
| `CompositeClaim` | Required level + leaf id set |
| `PredictiveObligation` | Theory-bound prediction with status |
| `TheoryObject` | Assumptions + formal leaves + predictive obligations |
| Receipts | Canonical JSON evaluation records |

## CLI surface

- `heck meet` — compute meets
- `heck compose` — evaluate a composite
- `heck verify` — package directory verification
- `heck predict` — discharge one obligation
- `heck theory` — theory closure evaluation
- `heck attacks` — conflation campaign

## Noninterference

Only `incubation/pcs_heterogeneous_compose_v1/` is owned. No edits to
`pcs/`, `formal/PCS*`, website, CertNum, PCS Next, or PGSI trees.
