# Contradiction semantics research report

## Finding E restated

Classical `Entails` (Boolean assignments) makes every formula a consequence of an
unsatisfiable context. The ND fragment without ExFalso is non-explosive at the
**derivability** level (`no_ex_falso_unrelated_atom`).

Absence of an ExFalso *rule* is **not** by itself a complete paraconsistent semantics.

## Belnap FOUR fragment

`lean/ScientificReasoning/Belnap.lean` defines truth values
`none | onlyTrue | onlyFalse | both` with negation and conjunction, and designated
truth `onlyTrue|both`.

Witness: assignment with atom 0 = `both` designates both `atom 0` and `¬ atom 0`
while not designating unrelated `atom 99`.

## Status

| Layer | Non-explosion? |
|---|---|
| Derives (no ExFalso) | Yes (proved for atom-occurrence invariant) |
| Classical Entails | No (vacuous on inconsistent Γ) |
| Entails4 (Belnap) | Countermodel witness for demo assignment; full Derives⇒Entails4 deferred |

## Retraction (≠ ICR #217)

Support-set invalidation: withdrawing id `i` invalidates certificates with `i ∈ support`.
Multiple independent derivations of the same formula may have distinct supports; only
those containing `i` are invalidated. No DAG cache engine.
