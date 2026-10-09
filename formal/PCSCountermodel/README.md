# PCSCountermodel — finite first-order checker soundness (Lean 4.28.0)

Toolchain: `leanprover/lean4:v4.28.0` (`lean-toolchain`). Dependencies: none (`import Std`
only; `lake-manifest.json` has an empty package list). Library target `PCSCountermodel` in
`lakefile.toml`.

## Files

| File | Content |
| --- | --- |
| `PCSCountermodel/Core.lean` | Items 1–5: `Formula k`, `World n`, `Env`, `extend`, `evalBool`, `Holds`, `evalBool_iff_holds`, `checker`, `checker_iff` |
| `PCSCountermodel/Enumeration.lean` | Item 6: flat bit layout, `allWorlds`, `allWorlds_complete`, `enumeration_covers`, `search`, `search_sound`, `search_minimal`, `search_none`, `search_none_not_unbounded` |
| `PCSCountermodel/Named.lean` | Named AST `NFormula`, `lower`, `NHolds`, `lower_sound`, `lower_closed_sound`, `lower_isSome_iff`, `namedChecker_sound`, `namedChecker_isSome_iff` |
| `PCSCountermodel/Fixtures.lean` | `implication-flip` reference counterexample, shadowing/capture/unbound examples |
| `PCSCountermodel/Audit.lean` | `#print axioms` for all principal theorems |
| `PCSCountermodel/Negative/WrongEquivalence.lean` | Intentionally false target (not in the library; must fail) |
| `PCSCountermodel/Missions.lean` | All seven shipped mission pairs, exact lowering, concrete disagreements and minimum search sizes |
| `PCSCountermodelReplay.lean` | Compiled exhaustive differential-test runner |

## Reproduce

```
lake build PCSCountermodel
lake env lean PCSCountermodel/Negative/WrongEquivalence.lean   # expected: exit 1
lake build pcs-countermodel-replay
cd ..
python scripts/verify_countermodel_formal.py
```

The negative file fails with
`Tactic 'decide' proved that the proposition ... is false` — the proposition is false; it is
not a syntax/import/`sorry` failure.

## Axiom inventory (actual `#print axioms` output)

| Theorem | Axioms |
| --- | --- |
| `evalBool_iff_holds` | propext, Quot.sound |
| `checker_iff` | propext, Quot.sound |
| `allWorlds_complete`, `enumeration_covers` | propext, Quot.sound |
| `searchAt_none_iff`, `search_sound`, `search_minimal`, `search_none` | propext, Quot.sound |
| `search_none_not_unbounded` | propext, Quot.sound |
| `lower_sound`, `lower_closed_sound`, `lower_isSome_iff`, `namedChecker_isSome_iff` | propext |
| `namedChecker_sound` | propext, Quot.sound |
| `implicationFlip_lowering`, `implicationFlip_checker_accepts`, `implicationFlip_search_size`, `capture_search_size` | propext |
| `implicationFlip_counterexample`, `implicationFlip_named_counterexample` | propext, Quot.sound |

No `Classical.choice`, no `Lean.ofReduceBool`, no `native_decide`, no custom axioms.

## Scope

* Established: for every `n`, world, environment and well-scoped typed formula, `evalBool`
  agrees with `Holds`; the checker accepts a world iff the closed formulas disagree there;
  every world of size `n` is enumerated; `search` (sizes 1, 2, 3) returns only genuine
  disagreements, a returned size is minimal among nonempty sizes, and `none` means agreement
  on all worlds of sizes 1–3 **only**. `search_none_not_unbounded` exhibits two closed
  formulas with `search = none` that disagree on a 4-element world, so a `none` result does
  not establish unbounded equivalence.
* Named bridge: `lower` resolves each name to its innermost binder, rejects unbound variables
  and unknown predicate names exactly (`lower_isSome_iff`), and preserves semantics with
  respect to the independent Tarskian semantics `NHolds`.
* Repository integration: `Missions.lean` binds all seven real game AST pairs to the pinned
  `pcs/schemas/countermodel_missions_v1.json`. The generator rejects unknown fields,
  predicates, operators and unbound variables. Each named-to-typed lowering is proved
  by `rfl`; each mission has a kernel-checked concrete disagreement and search size.
  The required release gate checks generation drift, the 48 principal/mission axiom
  inventories, a genuinely false equivalence, and all 231,224 P/Q/R interpretations
  on domains 1–3 against the independent Python evaluator. Website CI additionally
  compares these compiled Lean verdicts with the real JavaScript game evaluator.
  These exhaustive finite comparisons are tests, not general implementation-refinement proofs.
* Outside scope: byte/JSON parsing, schema validation, general correspondence between
  arbitrary JSON objects and `NFormula` values, Python/JavaScript refinement, and
  cryptographic hash correctness. The generator and compiled executable use trusted
  host runtimes. Runtime output is not a serialized kernel proof or PCS certificate.
  Nothing here establishes natural-language intent, participant authenticity, consent, model optimality,
  scientific authority or real-world AI safety.

## Provenance

The reviewed proof sources came from `241372da-f67c-441a-bc49-b30ef8de2864-aristotle.tar.gz`
(SHA-256 `9815ba0c844c4978882b6a317f24f8f950cd0014e4dd5bdd2e7d65489699797b`),
run `d1f2ca07-5e0e-4389-8ad4-7c37a7ad87fe`. Existing PCS source bytes were unchanged
in that archive. Its supplied build transcript was independently reproduced rather
than used as verification evidence. `Missions.lean`, the runtime runner and release
gate are repository integration additions.
