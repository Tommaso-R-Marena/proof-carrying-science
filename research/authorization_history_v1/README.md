# Signed authorization-history research v1

See the [protocol, threat model, results and limits](../../docs/research/post-integration-2026-10-18/authorization-history.md).
This isolated experiment authenticates exact authorization envelopes with real
Ed25519 and commits event/head together in SQLite. It does not execute a
scientific checker or provide a protected witness/root service.

From the repository root:

```sh
python -m pip install -r research/authorization_history_v1/requirements.txt
python -m unittest research.authorization_history_v1.test_history -v
python research/authorization_history_v1/check_formal.py \
  --lean /path/to/lean-4.28.0/bin/lean \
  --cache-root /path/to/repository-with-compatible-mathlib-cache
```

`formal/` is an independent Lean/Mathlib v4.28.0 Lake project. The proof is pure;
the runtime correspondence is analyzed but not proved. Runtime reports include
actual process-crash/concurrent-writer tests and deliberate undetectable
database-plus-trusted-root/checkpoint substitution.
