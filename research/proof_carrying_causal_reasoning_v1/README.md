# Proof-Carrying Causal Reasoning (PCCR) v1

Isolated research package: **AI causal claims are accepted only with a
machine-checkable identification certificate that agrees with exact interventions
on executable finite SCMs and real programs.**

| Item | Value |
|------|--------|
| Path | `research/proof_carrying_causal_reasoning_v1/` only |
| Branch | `feature/proof-carrying-causal-reasoning-v1-9178` |
| Status | draft research — do not merge into production authority |

## Why this is different

Existing LLM causal benchmarks (CausalBench, CLadder, CARL-GT) and symbolic
checkers (DoVerifier) mostly score string/expression agreement. PCCR closes a
stronger loop:

1. **Claim** — model emits a structured causal claim (JSON schema).
2. **Identify** — independent backdoor / front-door / IV / counterfactual check
   (auto-synthesizer available for simple patterns).
3. **Intervene / abduct** — exact rational `do(·)` or twin-network
   counterfactuals on a finite binary SCM; optional noise-bit enumeration on
   real Python programs whose dataflow *is* the graph.
4. **Certify or countermodel** — accept only under declared assumptions; otherwise
   fail closed with reasons (wrong adjustment, collider, non-identifiability,
   association≠effect, CF≠do trap, positivity failure, numeric mismatch).
5. **Epistemic ceiling** — a valid certificate never escalates to empirical
   causation or production PCS authority.

Breakthrough (v1.5): exact twin-network `P(Y_x | evidence)` with certificates
that reject confusing the counterfactual with the interventional law under
confounding (T11: `7/20 ≠ 3/8`).

This does **not** claim a new general theorem of causality, frontier-model SOTA,
or that Lean proves full backdoor soundness for arbitrary SCMs. Lean checks
concrete finite graph obligations used by the suite.

## Quick start

```bash
export PYTHONPATH=.
python -m research.proof_carrying_causal_reasoning_v1 list-tasks
python -m research.proof_carrying_causal_reasoning_v1 all \
  --out research/proof_carrying_causal_reasoning_v1/results/local-run
bash research/proof_carrying_causal_reasoning_v1/scripts/check_all.sh
```

Lean (optional, after `source scripts/activate_lean_428.sh`):

```bash
cd research/proof_carrying_causal_reasoning_v1/lean && lake build
```

Lean now includes inductive confounder/collider/mediation/front-door/IV proofs,
do-calculus Rule-2 context packs, an abstract non-identifiability theorem,
exact-rational SCMs with `backdoor = do` and `frontdoor = do`,
correlation≠causation, and twin-network counterfactual consistency / CF≠do
(see `RESULTS.md`). Certificates carry strategy-specific assumptions and
`formal_bindings` naming the concrete Lean theorems for the suite graphs.
Binary IV bounds are dual-checked (exact LP ≡ Balke–Pearl closed forms)
before certification.

## Live local models (GGUF)

Uses the same pinned Qwen3-0.6B/1.7B GGUF + llama.cpp contract as
`research/public_study_validation_v1` (CPU, loopback only):

```bash
python -m research.proof_carrying_causal_reasoning_v1 download-weights \
  --weights /tmp/pcs-pinned-weights
python -m research.proof_carrying_causal_reasoning_v1 model \
  --weights /tmp/pcs-pinned-weights \
  --out /tmp/pccr-qwen06 \
  --model Qwen/Qwen3-0.6B-GGUF
```

## Gemini API (rate-limited)

Requires `GEMINI_API_KEY` in the environment. The key is never written to
results or the repository. Defaults: `gemini-3.5-flash-lite`, ≥8–10s between
calls, capped request count.

```bash
export GEMINI_API_KEY=...   # shell only
python -m research.proof_carrying_causal_reasoning_v1 gemini \
  --out /tmp/pccr-gemini \
  --model gemini-3.5-flash-lite \
  --min-interval 10 \
  --max-requests 10
```

Results are local measurements, not an official leaderboard.

## Task battery

| ID | Domain | Point |
|----|--------|-------|
| T01 | epidemiology-toy | confounder; association ≠ ATE |
| T02 | mechanisms-toy | mediator must not be adjusted for total effect |
| T03 | selection-toy | collider trap |
| T04 | epidemiology-toy | M-bias |
| T05 | epidemiology-toy | two confounders |
| T06 | latent-confounding | unobserved U → not identifiable from {X,Y} |
| T07 | mechanisms-toy | fork into mediator + treatment |
| T08 | spurious-correlation | association without causation |
| T09 | frontdoor | latent confounder; identify via mediator M |
| T10 | instrument | IV Z→X; Balke–Pearl bounds (partial ID) |
| P01 | program-systems | request-routing feature flag → latency |
| P02 | program-systems | CI flaky → pass |

## Scientific honesty

- Identification under assumptions ≠ empirical validation of those assumptions.
- Exact finite SCM enumeration ≠ continuous real-world systems.
- Program ATE from noise-bit enumeration is exact for that program, not a field trial.
- Checked Lean lemmas are finite graph facts, not a replacement for Pearl’s theorems.
- Parallel agents (safety research, incremental revalidation, scientific reasoning)
  are not modified by this package.

## License

Apache-2.0, as the host repository.
