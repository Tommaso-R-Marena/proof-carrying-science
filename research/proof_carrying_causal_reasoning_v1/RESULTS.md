# PCCR v1 results

Draft research measurements. Not production PCS authority, not a frontier SOTA
claim, and not empirical proof of real-world causation.

## Exact finite oracle (no model)

Command:

```bash
PYTHONPATH=. python -m research.proof_carrying_causal_reasoning_v1 all \
  --out research/proof_carrying_causal_reasoning_v1/results/qualified-v1
```

| Check | Result |
|-------|--------|
| Authored control suite | pass (first control accepted; negative probes rejected) |
| Backdoor estimate = interventional truth | pass on all identifiable tasks |
| Unit tests | 13/13 pass |
| Lean `lake build` (PcsPccr) | success, no Mathlib |

Notable executable finding on T01 (confounder SCM): observational association
differs from ATE under exact rational enumeration — correlation ≠ causation is
witnessed by the program, not asserted rhetorically.

## Live local model: Qwen3-0.6B-Q8_0

Pinned artifact `Qwen/Qwen3-0.6B-GGUF` revision
`23749fefcc72300e3a2ad315e1317431b06b590a`, SHA-256
`9465e63a22add5354d9bb4b99e90117043c7124007664907259bd16d043bb031`,
runtime llama.cpp `b11827` / `970b51ce7c9ba5fff0726c5e9994f1c2f0e4eedc`.
CPU, temperature 0, seed 42, thinking off, JSON object mode.

Evidence directory: `evidence/qwen3-0.6b-q8/`.

| Metric | Value |
|--------|------:|
| Tasks | 10 |
| Accepted certificates | 6 |
| Accuracy | 0.6 |

| Task | Accepted | Failure mode (if any) |
|------|----------|------------------------|
| T01 | yes | — |
| T02 | no | Adjusted for mediator `M` (descendant of treatment) |
| T03 | yes | — |
| T04 | yes | Used `{U1,U2}` (valid; larger than empty) |
| T05 | yes | — |
| T06 | no | Claimed identifiable under unobserved confounding |
| T07 | yes | — |
| T08 | yes | — |
| P01 | no | Invented adjustment vars `Z1,Z2` absent from program graph |
| P02 | no | Invented adjustment var `Z1` absent from program graph |

### Interpretation

The small model handles several textbook DAG prompts, including collider-empty
adjustment and two-confounder adjustment, but fails in ways the certificate
layer is designed to catch:

1. **Mediator mistreatment** on total-effect queries (T02).
2. **Overconfident identification** when the latent confounder is unobserved (T06).
3. **Variable invention** on program-grounded systems (P01/P02) — proposing
   covariates that do not exist in the executable system.

These are local measurements on a 0.6B Q8 GGUF model. They do not rank frontier
systems and do not validate the scientific assumptions of any external domain.

## Lean scope

Proved concrete facts for confounder / mediation / collider fragments
(`noDescendantsOfTreatment`, descendant checks, edge presence). General
backdoor soundness for arbitrary SCMs remains an explicit non-claim (same
blocker class as the incubation causal laboratory).
