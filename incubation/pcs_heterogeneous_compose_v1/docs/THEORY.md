# HECK theory: heterogeneous composition and predictive closure

## Judgment

Leaf evidence atoms are independently checkable. A composite claim is accepted when:

```text
leaves nonempty
∧ ∀ leaf ∈ leaves. supported(leaf) ∧ required ≤ level(leaf)
∧ required ≤ meet({ level(leaf) | leaf ∈ leaves })
```

The achieved level is exactly the meet of leaf levels.

## Laws (Lean-proved)

| Law | Content |
| --- | --- |
| Meet lattice | `meet` is commutative, associative, idempotent; `meet ≤` each argument |
| Empirical≠Formal | `empirical.meet formal = empirical` |
| No promotion | Nonempty at-most-empirical lists cannot meet to Formal |
| Empty rejects | Empty composites never accept |
| Heterogeneous pair | Formal+Empirical achieves Empirical; Formal requirement rejects |
| Predictive match | Match ⇒ `empiricallySupported` at Empirical level, never Formal |
| Predictive falsify | Contradiction ⇒ `falsified`; sticky under rematch |
| Unsupported/underleveled | Concrete controls reject bad leaves |

## Predictive obligations

A theory `T` may emit prediction `π`. Until an observation is checked:

- status = `OPEN` (blocks scientific closure)
- matching observation → Empirical support (still not Formal)
- contradicting observation → `FALSIFIED` (sticky)

Scientific closure requires: composite acceptance ∧ no falsified obligations ∧ no open obligations.
Closure is **not** formal truth and **not** production PCS `ACCEPT`.

## Relation to PCS Research Agenda

Addresses Program A compositionality, evidence heterogeneity, and uncertainty without converting confidence into proof. Complements existing leaf kernels without replacing them.
