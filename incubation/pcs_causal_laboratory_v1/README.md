# PCS Causal Laboratory (Independent Incubation)

**Proof-carrying causal inference laboratory** — finite structural causal models, exact rational probability, graphical identification, non-identifiability witnesses, statistical estimation, discovery, sensitivity, and simulated experiment design.

## Isolation

| Item | Value |
|------|--------|
| Preferred separate repo | `Tommaso-R-Marena/proof-carrying-causality` (**create blocked** by token scopes; see `NONINTERFERENCE_BASELINE.md`) |
| Fallback namespace | `incubation/pcs_causal_laboratory_v1/` **only** |
| Branch | `feature/pcs-causal-laboratory-v1-4972` |
| Host repo (fallback) | `tommaso-r-marena/proof-carrying-science` |

This package does **not** modify PCS production verification, the website, Aristotle, FoldBounds, CertiForge, or other agents' branches.

## Scientific honesty (non-negotiable)

- Identification under assumptions ≠ empirical validation of those assumptions.
- Statistical significance ≠ causation.
- Formal / computational verification ≠ scientific model truth.
- Simulated experiments ≠ laboratory interventions.
- Observational discovery output ≠ established causal mechanism.

## Quick start

```bash
cd incubation/pcs_causal_laboratory_v1
source .venv/bin/activate   # or: uv venv && source .venv/bin/activate
uv pip install -e ".[dev,ui]"
./scripts/run_tests.sh
pcs-causal backdoor-demo
pcs-causal witness
pcs-causal demo-drug
pcs-causal adversarial
```

Local UI (not mathematical authority):

```bash
pcs-causal ui --port 8765
```

## Lean

```bash
cd lean
lake build
```

See `docs/FORMAL_STATUS.md` for theorem inventory, axiom policy, and open blockers.

## Architecture split

1. **Identification** — is the causal quantity determined by the observational law under a declared model class?
2. **Estimation** — estimate an identified (or assumed-identified) quantity from finite samples.
3. **Certificates** — machine-checkable mathematical claims; `producer_pass` is ignored.
4. **Non-identifiability witnesses** — two models, same observations, different interventions.

## License

Apache-2.0 (incubation package). Independent of PCS production release process.
