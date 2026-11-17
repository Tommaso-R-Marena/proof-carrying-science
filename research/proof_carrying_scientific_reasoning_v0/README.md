# Proof-Carrying Scientific Reasoning v0

Research-only PCS subsystem: a typed scientific argument calculus with
machine-checkable certificates that expose premises, inference steps, authority
levels, contradictions, and retraction effects — **without** promoting empirical
assertions into mathematical verification.

**Exclusive path.** Not production authority. Draft PR only.

## Reproduce

```bash
export PATH="$HOME/.local/lean-4.28.0/bin:$PATH"
cd research/proof_carrying_scientific_reasoning_v0
bash scripts/check_all.sh
```

Pinned Lean: **4.28.0**.

## Layout

See `SCOPE.md`, `docs/ARCHITECTURE_RECONNAISSANCE.md`, `HANDOFF.md`.
