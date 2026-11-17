# Adversarial findings

Suite: `adversarial/attacks.py` → `results/adversarial_report.json`.

All listed attacks **failed to obtain false acceptance** after defense-in-depth
local checks on reuse (`recheck_on_reuse=True` by default).

| Attack | Goal | Result |
|---|---|---|
| input_substitution | Keep stale const after evidence change | Resisted |
| dependency_manipulation | Keep stale output after dep rewiring | Resisted |
| op_substitution | Reuse add cert under mul | Resisted |
| policy_substitution | Escalate untrusted cache under new policy | Resisted |
| version_mismatch | Accept incompatible checker version | Resisted |
| cache_forgery | `prior_accepted=False` wrong payload | Resisted (recheck) |
| serialization_duplicate_keys | Ambiguous JSON keys | Resisted (`reject_duplicate_keys`) |
| rollback | Reuse stale value on affected node | Resisted |
| proof_context_misuse | Apply foreign node certificate | Resisted |

## Design notes

1. **Lookup ≠ eligibility ≠ authority** enforced in `cache/store.py`.
2. Forged `prior_accepted=True` inside the process is outside the ValidState trust
   model; default `recheck_on_reuse=True` still rejects mismatched payloads.
3. **Rollback without external epoch**: presenting an old graph with its matching
   ValidState is mathematically consistent for that graph. Binding reports to graph
   bytes / epochs remains an external obligation (documented gap).
4. Concurrency/crash atomicity of cache persistence is not implemented (in-memory
   research model only).

## Assumption-removal counterexamples (independent of attack suite)

`tests/test_assumption_counterexamples.py` demonstrates that removing essential
`IncrementalAccept` premises breaks the guarantee:

| Removed premise | Observable failure |
|---|---|
| `ChangesComplete` (incomplete seeds) | Fail-closed reject under default; with forgery + no reuse-recheck → stale accept |
| New-graph invalidation (use prior Affected) | Set incompleteness for new edges; with forgery → stale accept |
| Authority (`prior_accepted=False`) | Reuse denied; falls back to recheck |
| Sound path (complete + new-graph) | Agrees with fresh |

These are intentional negative results showing necessity of the formal premises,
not product defects under default defenses.

## Regression

`tests/test_adversarial.py` fails the build if any attack succeeds.
`tests/test_assumption_counterexamples.py` encodes the negative findings above.
