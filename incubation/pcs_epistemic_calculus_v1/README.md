# PCS Epistemic Calculus v1 (incubation)

Groundbreaking research kernel for **graded evidence composition**, **sound
invalidation under dependency completeness**, and **proof-carrying scientific
dialectic** over rival model ensembles.

> **Isolation.** Everything lives under `incubation/pcs_epistemic_calculus_v1/`.
> Production `pcs/`, `formal/PCS*`, website, CI, and peer incubation trees are
> untouched. Not production authority.

## Why this exists

PCS founding semantics asked for composition and invalidation theorems that were
still open as a self-contained executable kernel. Concurrent workstreams cover
certified numerics, PGSI/PGSC, and PCS Next — this thrust deliberately does not
overlap them. It instead treats **scientific disagreement** as an assurance
object: agreement cores, dispute frontiers, and distinguishing experiments.

## Delivered

| Layer | Contents |
| --- | --- |
| Theory | `docs/THEORY.md` — lattice, Assures, compose, invalidate, dialectic |
| Lean 4.28 | `PcsEpistemic/` — proofs with `propext` / `Quot.sound` only |
| Python | `python/pcs_epistemic/` — checker, composition, invalidation, dialectic CLI |
| Experiments | PK dialectic example + deterministic adversarial campaign |
| Engineering | `pyproject.toml`, pytest suite, noninterference script |

## Quick start

```bash
cd incubation/pcs_epistemic_calculus_v1

# Python
python3 -m pip install -e ".[dev]"
python3 -m pytest -q
python3 scripts/run_campaign.py
python3 -m pcs_epistemic dialectic examples/pk_dialectic/ensemble.json
python3 -m pcs_epistemic verify examples/pk_dialectic/dialectic_certificate.json

# Lean (Lean 4.28.0 on PATH)
lake build
bash scripts/axiom_audit.sh
```

## Non-claims

- No production PCS verifier integration
- No clinical / empirical scientific acceptance
- No forced consensus across rival models
- Declared non-impact ≠ world non-impact without completeness

## Reproduce noninterference

```bash
bash scripts/noninterference_check.sh
```
