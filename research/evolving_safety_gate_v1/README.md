# Evolving Safety Gate v1

**Question.** Can a Lean-checked admission lattice steer automated search toward
safety mechanisms that actually detect real-model mirages — and permanently
reject channel-1-only “perfect completion” theater?

**Answer in this package.** Yes, within a finite reviewed mutation set scored on
attested Assurance Mirage evidence. The gate is fail-closed: channel-1-only and
correcting-guard-only mechanisms are never admissible champions.

## What “self-evolving” means here

1. **Formal kernel** (`formal/EvolvingSafetyGate.lean`): mechanisms form a lattice;
   only classes that detect the constructive mirage are `Admissible`; evolution
   may `Retain` a successor only if it `Dominates` its parent on detectability.
2. **Empirical fitness**: candidates are scored on pinned Qwen/Gemini/transfer
   captures (mirage recall, benign FPR, Gemini cleanliness).
3. **Attested loop** (`evolve`): generations propose reviewed mutations, discard
   losers, keep a champion lineage with SHA-256.
4. **Optional live stress**: re-test the champion on Gemini free-tier waves.

This is **not** recursive self-improvement of production PCS authority, not an
open-ended self-modifying kernel, and not a claim of absolute/global safety.

## Run

```sh
source scripts/activate_lean_428.sh
PYTHONPATH=. python3 -m research.evolving_safety_gate_v1 formal /tmp/esg-formal
PYTHONPATH=. python3 -m research.evolving_safety_gate_v1 evolve /tmp/esg-evolve --generations 4
# Optional live Gemini stress (needs GEMINI_API_KEY; never committed):
PYTHONPATH=. python3 -m research.evolving_safety_gate_v1 evolve /tmp/esg-live \
  --generations 3 --live-gemini --max-requests 12
PYTHONPATH=. python3 -m unittest research.evolving_safety_gate_v1.test_evolve
```

## Relation to Assurance Mirage

Uses the sharp result that channel-1-factorable scores are mirage-blind. The
evolving gate’s job is to **keep discovering and retaining** joint-channel
mechanisms that dominate that blindness on real attested runs.
