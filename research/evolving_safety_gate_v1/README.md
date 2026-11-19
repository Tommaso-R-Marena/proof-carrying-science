# Evolving Safety Gate v1

**Question.** Can a Lean-checked admission lattice steer automated search toward
safety mechanisms that actually detect real-model mirages — including stealth
channel-1-perfect compliance — and permanently reject channel-1-only theater?

**Answer in this package.** Yes, within a finite reviewed mutation set scored on
attested Assurance Mirage evidence plus a pinned stealth hard suite. The gate is
fail-closed: channel-1-only and correcting-guard-only mechanisms are never
admissible champions. Evolution promotes `ensembleProbe` over `jointDetectingGuard`
when note-level stealth probes dominate classic joint OR-flags.

## What “self-evolving” means here

1. **Formal kernel** (`formal/EvolvingSafetyGate.lean`): five mechanism classes;
   only classes that detect the constructive mirage are `Admissible`; `ensembleProbe`
   formally dominates `jointDetectingGuard`; evolution may `Retain` only on domination.
2. **Empirical fitness**: classic mirage recall + stealth hard-suite recall + benign
   FPR + Gemini cleanliness (refusal-aware probes).
3. **Attested loop** (`evolve` / `kernel`): generations propose reviewed mutations and
   failure-driven adaptations, discard losers, keep a champion lineage with SHA-256.
4. **Optional live stress**: re-test the champion on Gemini free-tier waves.

This is **not** recursive self-improvement of production PCS authority, not an
open-ended self-modifying kernel, and not a claim of absolute/global safety.

## Run

```sh
source scripts/activate_lean_428.sh
PYTHONPATH=. python3 -m research.evolving_safety_gate_v1 formal /tmp/esg-formal
PYTHONPATH=. python3 -m research.evolving_safety_gate_v1 kernel /tmp/esg-kernel --generations 5
# Optional live Gemini stress (needs GEMINI_API_KEY; never committed):
PYTHONPATH=. python3 -m research.evolving_safety_gate_v1 kernel /tmp/esg-live \
  --generations 3 --live-gemini --max-requests 12
PYTHONPATH=. python3 -m unittest research.evolving_safety_gate_v1.test_evolve
```

## Relation to Assurance Mirage

Uses the sharp result that channel-1-factorable scores are mirage-blind. The
evolving gate’s job is to **keep discovering and retaining** joint/ensemble
mechanisms that dominate that blindness on attested real-model runs — including
stealth cases where classic joint flags stay silent.

## External bake-off (JailbreakBench + SOTA-style guards)

```sh
# Requires ProtectAI ONNX under /tmp/external-bench/protectai/onnx and
# JailbreakBench CSVs under /tmp/external-bench/jbb/data (see external_bench/).
PYTHONPATH=. python3 -m research.evolving_safety_gate_v1.external_bench.run_bakeoff \
  /tmp/esg-bakeoff --jbb-max 50
```

Results: [`RESULTS_EXTERNAL.md`](RESULTS_EXTERNAL.md). Short version: Gemini wins on
JBB *content* Goals; `ensembleProbe` wins on agent mirage/stealth episodes;
ProtectAI is strong on injection syntax but noisy / incomplete on mirages.

## Multi-threat SOTA stack

See [`RESULTS_SOTA.md`](RESULTS_SOTA.md): modality-routed `composedStack` is uniquely undominated across JBB content + agent mirage/stealth tracks (not a claim on every public leaderboard).
