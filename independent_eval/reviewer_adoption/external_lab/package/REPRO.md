# External lab — REPRO

Attempt reconstruction of a documented workflow on lab hardware and **record**
what matches or diverges.

## Steps

1. Choose a read-only example under `examples/` (do not vendor large trees here).
2. Record OS, Python version, CPU/GPU, and dependency pins used.
3. Attempt the documented command sequence offline where possible.
4. Compare outputs / hashes against any published digests.
5. If dependency hashes diverge, stop and document (see tabletop scenario
   `dependency_substitution.json` for response structure).

## Logging

```bash
python3 -m independent_eval.reviewer_adoption.external_lab.burden_tracker \
  --package independent_eval/reviewer_adoption/external_lab/package \
  --log independent_eval/reviewer_adoption/external_lab/burden_logs/lab.jsonl \
  --step attempt_repro --minutes 30 --notes "record divergence here"
```

## Non-claims

A successful local rebuild is **not** a completed external-lab validation claim
for the PCS project unless separately stewarded and published.
