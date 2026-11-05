# Capability inventory (live main @ fabc704)

| Capability | Existing location | Status on main | Class | Limitations / trust | Relevant PRs | PCS Next action |
|---|---|---|---|---|---|---|
| Lean-authoritative verifier | `formal/`, `pcs/lean_authority_v06.py` | Present | Authoritative | Kernel/toolchain assumed | — | Bridge read-only; isolated `formal/` under owned ns |
| Canonical artifact protocol | `pcs/canonical_json.py`, v06 zip | Present | Authoritative | JCS profile | — | Independent canonicalizer + differential tests |
| Claim IR / semantic translation | `pcs/semantic_translation_v1.py` | Present | Experimental/partial | Fragment limits | — | Complementary typed Claim IR in owned ns |
| Proof-obligation graph | `pcs/scientific_obligations_v1.py` | Partial | Experimental | — | — | Full POG with invalidation |
| Scientific validators | `pcs/scientific_*`, adapters | Present | Mixed | Domain scopes | — | Adapters + falsification engine |
| Independent scientific pilot | not on main (`pcs/independent_pilot_v1.py` on PR #120) | Draft on PR | Experimental | Overlaps | #120 | Complementary integrated pilot under incubation |
| Independent eval suites | `independent_eval/*` on PRs #121–#128 | Draft on PRs | Experimental | — | #121–#128 | Interop/benchmark layer; no overwrite |
| Proof-gated self-improvement | `research/` + formal V2 on PRs | Draft | Research | Finite domains | #117, #129–#135 | Isolated research models + Lean ScalarGuard |
| Website | separate repo | Active | Product | — | site repo | Proposal only (`proposals/website_integration.md`) |
| Signing / release gates | `pcs/signing*.py`, docs gates | Present | Authoritative | Founder key custody | — | No key changes; receiver pin model only |

Evidence: open PR inventory via `gh pr list` on 2026-10-17; main tree listing under `pcs/`, `formal/`, `research/`.
