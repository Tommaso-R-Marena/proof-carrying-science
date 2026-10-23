# Trust boundaries

## What is proved and what is trusted

```
JSON problem + certificate  ──(1) strict parser (Python, tested, NOT verified)──▶ Problem data
        │                                                                          │
        │ sha256 of canonical encoding                                             │
        ▼                                                                          ▼
(2) Python checker (independent mirror, tested)        (3) Lean emitter (Python, NOT verified)
                                                                   │  Lean literals + hash comment
                                                                   ▼
                                     (4) Lean kernel: decide +kernel on checkOptimal / checkImpossible / ...
                                                                   │
                                                                   ▼
                       (5) Lean soundness theorems (proved): checker = true ⇒ mathematical claim
```

| Component | Status | What you must trust |
|---|---|---|
| (5) Soundness theorems in `PRISM/Certificates/Checker.lean` and below | **Proved in Lean** | Lean kernel, Mathlib, and the axioms `propext`, `Classical.choice`, `Quot.sound` |
| (4) Kernel evaluation of the checker on concrete data | **Kernel-checked** (`decide +kernel`, no `native_decide`, no compiled code) | Lean kernel |
| (3) `python/prism/lean_export.py` (JSON → Lean literals) | **Trusted, unverified** | That the emitted `Problem` literal is the one described by the JSON file. Mitigations: the emitted file lists every index ↔ identifier mapping and records the SHA-256 of the canonical JSON; it is short and human-auditable. |
| (1) `python/prism/serialize.py` | **Tested, unverified** | Correct rejection of malformed input (see `tests/test_serialization.py`) |
| (2) `python/prism/reference/checker.py` | **Tested, unverified** | Used for large-scale differential testing and benchmarks. Its agreement with the Lean checker is tested by `tests/test_lean_agreement.py` (honest certificates accepted, tampered ones rejected by both). |
| Search engine (`python/prism/search/*`, `engine.py`) | **Untrusted** | Nothing. Every positive claim it makes is re-checked. |
| Python runtime, OS, hardware | Trusted | As usual |

**There is no verified byte-to-model correspondence theorem.** We did not formalize
a parser in Lean. The precise residual risk: a bug in the emitter could produce a
Lean problem that differs from the JSON. The Lean theorems would then be true
statements about a different problem. The Lean file is self-describing (it contains
the full observation table, the query values and the costs), so a reviewer can
compare it with the JSON directly.

## Model-level trust: formal conclusion ≠ empirical truth

Every Lean conclusion is relative to the declared model class `M₀`, the declared
assumptions `A` and the recorded data `D`. `certified_transfers_to_truth` makes
the bridge explicit: a certified claim holds for the real mechanism **only if** the
real mechanism belongs to `M₀`, satisfies `A` and reproduces `D`.
`certified_does_not_imply_truth` shows that this premise cannot be dropped. All
demonstrations use **synthetic** mechanisms. None of them is laboratory
validation.

## Schemas (`prism-problem/1`, `prism-certificate/1`)

* Encoding: UTF-8 JSON. Duplicate keys, `NaN` and `Infinity` are rejected.
  Inputs are capped at 64 MiB, 2^20 models, 4096 experiments, 4096 outcomes per
  experiment and 2^22 policy nodes.
* Rationals: strings matching `-?(0|[1-9][0-9]*)(/[1-9][0-9]*)?`, in lowest terms,
  with no `/1` and no `-0`, and at most 4096 characters.
* Problem: `schema`, `name`, `description`, `models[{id, obs{experiment→outcome},
  q}]`, `experiments[{id, cost, outcomes[]}]`, `query{id, description}`,
  `assumptions[{id, description, holds[model ids]}]`, `data[{experiment,
  outcome}]` and `tolerance`. Identifiers must be unique and match a restricted
  character class. Each model must give an observation for every experiment, drawn
  from that experiment's declared outcome list. Costs and the tolerance must be
  `≥ 0`.
* Certificate: `schema`, `problem_sha256` (SHA-256 of the canonical encoding of the
  problem: sorted keys and compact separators), `kind = "optimal"`, `bound`,
  `core[model ids]`, `policy` (`"stop"` or `{experiment, next{outcome→policy}}`) and
  `adversary[{models[ids], lb}]`. Unknown or missing fields are rejected. An outcome
  missing from `next` means `stop`.
* Rejection: `SchemaError` with a reason, or `Reject` from the checker. The CLI
  `python/verify.py` exits with code 2 for malformed input and 1 for a rejected
  certificate.

Reordering models, experiments or JSON keys changes neither the canonical hash
(keys are sorted) nor the semantics (lookups are by identifier). Reordering
*list* elements does change the hash, because canonical encoding preserves list
order. This is deliberate: certificates bind to an exact model indexing.

## Probabilistic layer

The noisy guarantees (`PRISM/Probabilistic/AnytimeValid.lean`) assume that the
true outcome distribution is exactly one of the declared rational likelihood
tables, and that outcomes are conditionally independent given the model and the
chosen experiment. They are kept strictly separate from the deterministic
certificates. A deterministic certificate never implies a probabilistic one, and
vice versa.
