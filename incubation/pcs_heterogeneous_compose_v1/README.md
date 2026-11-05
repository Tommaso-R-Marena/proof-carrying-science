# HECK v1 — Heterogeneous Evidence Composition Kernel

**Incubation only.** Owned path: `incubation/pcs_heterogeneous_compose_v1/`.
Does not modify production PCS authority, signing roots, website, CertNum, PCS Next, or PGSI/PGSC6 workstreams.

## Thesis

PCS already has strong leaf kernels (transport, calibration, PK/PD, Omega). The open Research Agenda question remains:

> *When can certificates for subworkflows be composed?*
> *How should formal, computational, statistical, and empirical evidence coexist without conflation?*

**HECK** answers with a typed composition algebra:

1. Assurance levels form a chain: `Formal > Computational > Empirical > Provenance > Open`.
2. Composite assurance is the **meet** (weakest link) — never a promotion.
3. **Predictive obligations** stay `OPEN` until observationally discharged; a match yields **Empirical** support only; contradiction **falsifies** and is sticky.
4. Untrusted producers propose composites; a small independent checker accepts or rejects.

This is Proof-Carrying Predictive Closure: scientific theories become first-class objects whose formal leaves and predictive obligations compose under an explicit non-conflation law.

## Layout

```text
heck/           Python reference receiver + Theory IR + attack suite
formal/         Lean 4.28 Mathlib-free composition calculus + controls
experiments/    End-to-end composition campaign
fixtures/       Positive and adversarial packages
tests/          Pytest suite
scripts/        Noninterference + Lean axiom audit
docs/           Theory and architecture notes
results/        Generated campaign reports
```

## Quick start

```bash
cd incubation/pcs_heterogeneous_compose_v1
pip install -e ".[dev]"
pytest -q
python -m heck.cli attacks
python experiments/compose_campaign/run_campaign.py

# Lean (pinned 4.28.0, no Mathlib)
export PATH="$HOME/.elan/bin:$PATH"   # or activate_lean_428.sh
cd formal && lake build
bash ../scripts/axiom_audit.sh
bash ../scripts/noninterference_check.sh
```

## Non-claims

- Not production PCS package authority.
- Empirical support is not formal proof.
- Catch rate is suite-specific, not a security proof.
- No new physical measurements or clinical validity.
- Do not merge without independent review.
