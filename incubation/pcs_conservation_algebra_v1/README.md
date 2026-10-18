# PCCA — Proof-Carrying Conservation Algebra (v1 incubation)

Standalone research engine for **stoichiometric conservation certificates**:
exact left-nullspace / elemental pool laws, trajectory preservation under
arbitrary firings, independent receiving verification, and Lean 4 theorems.

**Independence:** lives only under `incubation/pcs_conservation_algebra_v1/`.
It does **not** modify PCS production (`pcs/`, `formal/PCS`, `formal/real`),
the website, CertNum (`incubation/pcs_certified_numerics_v1/`), PCS Next,
PGSC/PGSI, or Aristotle workstreams.

## Why this is a hard push

PCS already kernel-checks discrete transport amount conservation and static
reaction balance. What remained open was a **general conservation algebra**
that:

1. treats stoichiometric matrices as first-class scientific objects;
2. proves that every left-nullspace vector is dynamically invariant under
   *arbitrary* firing sequences (not only mass-action Euler);
3. derives elemental C/H/O/… pools from formulas and proves they are
   conservation laws when reactions balance;
4. packages the result as an independently checkable certificate that a
   receiving process can verify without trusting the producer;
5. reduces transport amount conservation to the same stoichiometric theorem;
6. explicitly keeps continuum accuracy, biology, and PCS authority **OPEN**.

This is the missing bridge between Chemistry's static atom balance and
Transport's dynamical invariants — expressed as proof-carrying scientific
assurance, not merely as a CRN library.

## Quick start

```bash
python3 -m venv ~/.venvs/pcs-pcca
source ~/.venvs/pcs-pcca/bin/activate
cd incubation/pcs_conservation_algebra_v1
pip install -e ".[dev]"
pytest -q

# Independent receive of the synthetic glucose network
pcca receive examples/mass_action/glucose_cleavage.json -o /tmp/pcca-glucose
pcca verify /tmp/pcca-glucose/conservation_law-C.json
pcca explain /tmp/pcca-glucose/trajectory_conservation-C.json

# Adversarial mass-leak must fail closed
pcca receive examples/adversarial/mass_leak.json   # exit 1

# Lean 4.28 + Mathlib (own lake cache)
export PATH="$HOME/.elan/bin:$PATH"   # or source ../../scripts/activate_lean_428.sh
export LAKE_CACHE_DIR="$HOME/.cache/pcca-lake"
lake exe cache get
lake build
```

## Lean theorems (namespace `PCCA.Stoich` / `PCCA.Elemental`)

| Result | Content |
| --- | --- |
| `conserved_step` | `γ · S = 0 ⇒ γ · (x + Sξ) = γ · x` for any firing ξ |
| `conserved_all_times` | Same for every finite firing sequence |
| `conservation_add` / `conservation_smul` | Conservation laws form a vector space |
| `check_sound` | Exact rational Boolean check ⇒ real conservation law |
| `rational_certificate_real` | Rational certificates embed into ℝ |
| `trajectory_preserves_pool` | Declared stoichiometric trajectories keep the pool |
| `elemental_is_conservation` | Atom-balanced reactions ⇒ elemental conservation law |
| Controls | Glucose C/H/O accept; mass-leak reject; exchange amount |

Axiom audits target only `propext`, `Classical.choice`, `Quot.sound` (or fewer).
No `sorry`, `admit`, project `axiom`, or `native_decide`.

## Trust boundary

| Layer | Status |
| --- | --- |
| Lean stoichiometric theorems | Mathematical authority for proved claims |
| Python independent checker | Recomputes obligations; never trusts producer verdicts |
| Continuum ODE accuracy | **OPEN** |
| Empirical / biological validity | **OPEN** |
| PCS package / scientific acceptance | **false** (explicitly) |

## Non-goals

- No production Claim-IR coupling or signing-root changes
- No merge into protected `main` without owner review
- No claim of general CRNT deficiency / persistence theory (see DefectCRN for that line)
- No floating-point proofs
