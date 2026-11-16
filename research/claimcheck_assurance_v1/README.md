# ClaimCheck assurance research: binding, authority, selection

Research only. **No PCS v0.6 authority.** Nothing here changes ClaimCheck v1 or v1.1, the reviewed
checker, a benchmark, a protected file or any production path. Kernel-checked with Lean 4.28.0
(core only, no Mathlib): `formal/build.sh` builds everything in well under a minute.

## What a ClaimCheck verdict rests on, and what this directory adds

| Step of the chain | Status before | Added here | Kind of evidence |
| --- | --- | --- | --- |
| proof-file text → data bytes | regular expressions in the runner | `Header.lean`: the strict decoder accepts exactly the canonical headers and returns their data; canonical headers are prefix-free | **proved** (Lean kernel) |
| | | the C decoder and the installed Python runner compute that same function on 5,755 inputs | **tested** (`conformance/test_header_refinement.py`) |
| numeral → bytes the checker computes on | unstated | `SourceBinding.lean`: `Source.bytes` of the numeral is exactly the data; a well-formed source is the dump of its own bytes | **proved** |
| text `0x…` → the number Lean uses | — | — | **trusted**: standard meaning of numeric literals in Lean's elaborator |
| the rest of the generated part (claims, theorem statements) | eight forbidden words | the installed runner's `parse_tail` (core `research/claimcheck_v1_1/claimcheck_kernel_runner.py`, since 2026-11-16): exactly the generator's language, checked before Lean starts | **tested** (84 real files accepted; 16 forgeries here and 13 alterations in the core suite rejected) |
| kernel result → outward verdict | `assert` in the Python policy | `Authority.lean`: a decided verdict implies the statement about the real `run`; unknown and conditional results never become decided; withdrawing evidence never raises a verdict; a discrepancy needs a kernel-confirmed sibling | **proved** about a Lean model |
| | | the Python policy computes the model's decision function on 302 real receipts and every one of 160 + 448 table states | **tested** (`conformance/check_conformance.py`) |
| the decoy rule against a chooser who saw the data | "2 %" | `Selection.lean`: in any 51 consecutive comparable numbers at most 2 are confirmable by the direct route and one supporting sibling together (`max(1, s) × 2` with `s` supporting reading sets), and 2/52 is reached; two rules that do give 2 % | **proved** about a model of the rule (finding) |
| | | every confirmation the implemented rule makes is confirmable in the model (785 checked); the real rule confirms 3.6 % in the worst pattern | **tested** (`conformance/test_decoy_rule.py`) |
| the kernel itself, the Lean binary, SHA-256, the process boundary | trusted | — | **trusted**, unchanged |

## Findings

* [`findings/RUNNER_TAIL_FORGERY.md`](findings/RUNNER_TAIL_FORGERY.md): the v1.1 stand-alone kernel
  runner, also served by the website draft, accepted a hand-written proof file that defines its own
  `run` and reported "MATCHES". Reproduced with the real kernel. **Corrected on the draft branches
  on 2026-11-16** (owner decisions C3/D4, authorised for preparation and testing): the strict runner
  is installed and served; the withdrawn runner is kept byte for byte as evidence in
  [`findings/evidence/`](findings/evidence/README.md), not as a verification path.
* `Selection.lean`: the documented "2 %" decoy limit is a local density, not a bound on coincidental
  confirmation. Owner decision A6 (2026-11-16): the rule is retained and its descriptions in the
  ClaimCheck branch were corrected to state the proved bound, its model and its assumptions.
* [`c/ARISTOTLE_RESULTS.md`](c/ARISTOTLE_RESULTS.md): Aristotle refuted two decoder properties as I
  had stated them (missing non-aliasing precondition, runnable counterexample) and proved four
  smaller ones; 92 credits were billed against an authorised 50.

## Main theorems (all in namespace `PCS.ClaimCheck.Assurance`)

Axioms used: only `propext`, `Classical.choice`, `Quot.sound`; several use none
([`formal/AXIOMS.expected`](formal/AXIOMS.expected), checked by CI).

**Header** (`formal/ClaimCheckAssurance/Header.lean`)

```lean
theorem decode_canon (d rest : List Nat) (cap : Nat) (hb : ∀ x ∈ d, x < 256)
    (hm : d.length ≤ MAXD) (hc : d.length ≤ cap) :
    decode (canon d ++ rest) cap = some (d, (canon d).length)

theorem decode_sound (h : decode buf cap = some (d, L)) :
    buf.take L = canon d ∧ L = (canon d).length ∧ L ≤ buf.length ∧
      d.length ≤ cap ∧ d.length ≤ MAXD ∧ ∀ x ∈ d, x < 256

theorem canon_prefix_free (h₁ : ∀ x ∈ d₁, x < 256) (h₂ : ∀ x ∈ d₂, x < 256)
    (m₁ : d₁.length ≤ MAXD) (m₂ : d₂.length ≤ MAXD) (h : canon d₁ ++ r = canon d₂) : d₁ = d₂

theorem accepted_header_denotes_data (h : decode buf cap = some (d, L)) :
    buf.take L = PRE ++ 120 :: (hexOf d ++ 44 :: 32 :: (decStr d.length ++ SUF)) ∧
      hexValue (hexOf d) = ofBytes d ∧ decVal (decStr d.length) = d.length ∧
      (Source.mk (hexValue (hexOf d)) (decVal (decStr d.length))).wellFormed = true ∧
      (Source.mk (hexValue (hexOf d)) (decVal (decStr d.length))).bytes = d

theorem accepted_header_run (h : decode buf cap = some (d, L)) (c : Claim) (t : Table)
    (ht : parseTable d = some t) :
    run (Source.mk (hexValue (hexOf d)) (decVal (decStr d.length))) c = runTable t c
```

`PRE_text` and `SUF_text` prove that the fixed bytes are the UTF-8 of the intended text.
`decStr_decVal` (a digit string without a leading zero is the decimal representation of its value)
and `hexBytes_unhex` (lowercase hexadecimal pairs re-encode to themselves) are what make the
decoder strict.

**Source binding** (`SourceBinding.lean`): `Source.bytes_eq`, `Source.bytes_ofBytes`,
`Source.ofBytes_bytes`, `Source.eq_of_bytes_eq`, `run_ofBytes_some`, `run_ofBytes_none`,
`run_not_wellFormed`, all about the definitions in `claimcheck_v1/formal/ClaimCheck.lean`.

**Authority** (`Authority.lean`): `confirmation_sound`, `discrepancy_sound`,
`discrepancy_corroborated`, `verdict_unknown_of_unaccepted`, `conditional_never_decided`,
`conditional_sound`, `verdict_mono`, `decided_of_withdrawn`, `no_conflict`, `verdict_ignores_notes`,
`evidence_does_not_transfer`, `faithfulness_not_decidable_from_observables`. The single assumption
about the world is `KernelSound src vs` (an accepted equation is true); it is a hypothesis, never an
axiom. Every other input (findings, sibling links, notes, claims) is arbitrary.

**Selection** (`Selection.lean`): `confirmable_block_le`, `confirmable_count_le`,
`confirmable_count_le_general`, `sliding_window_exceeds_nominal_rate`,
`strict_rule_within_two_percent`, `blockConfirmable_count_le`, and for both confirmation routes
together `routes_block_le` and `routes_count_le`:

```lean
theorem routes_block_le (R : Nat → Bool) (Rs : List (Nat → Bool))
    (hsub : ∀ R' ∈ Rs, ∀ n, R' n = true → R n = true) (r k a : Nat) :
    (List.range' a (r + 1)).countP (confirmableByRoutes R Rs r k) ≤ max 1 Rs.length * k
```

With one supporting sibling the bound is the same as for the direct route; with `s` different
supporting reading sets it is `s · k`, and an example shows it can exceed `k`.

Negative controls sit at the end of each module: every hypothesis is shown to be needed by a
concrete case, and `coreFlawed` shows that the monotonicity theorem fails for a plausible wrong policy.

## What is not established

* That the Python policy *is* the Lean model: tested on real receipts and on every table state, not
  proved. The functions that compute findings from text and data are outside the model.
* That the C decoder is memory safe for every input: sanitizer tests pass; Aristotle's memory-safety
  property for the decoder is unresolved.
* The claims part of the proof file: strict grammar, tested, not proved (next formal target,
  `HANDOFF.md`).
* The decoy bound with `s` different supporting reading sets is `max(1, s) · k` per `r + 1`
  numbers, that is `max(1, s) × 2` per 51 for the implemented rule (proved, `routes_block_le`,
  under the hypothesis that every supporting set is a subset of the direct one, which is how the
  policy builds them and is tested, not proved). How many such sets a chooser can obtain in one
  sentence is not bounded here; it is limited by the numbers that are themselves strongly confirmed.
  The bound is about printed numbers unrelated to the table and placed uniformly among comparable
  numbers; it says nothing about related numbers and is not a false-confirmation rate.
* Anything about meaning: `faithfulness_not_decidable_from_observables` states why no verdict claims
  that a reading is what the authors meant.

## Run

```bash
source scripts/activate_lean_428.sh
research/claimcheck_assurance_v1/formal/build.sh
python3 research/claimcheck_assurance_v1/conformance/test_header_refinement.py
python3 research/claimcheck_assurance_v1/conformance/check_conformance.py
python3 research/claimcheck_assurance_v1/conformance/test_decoy_rule.py
python3 research/claimcheck_assurance_v1/c/test_srcbind.py
PCS_LEAN="$(command -v lean)" python3 research/claimcheck_assurance_v1/runner/test_strict_tail.py
```
