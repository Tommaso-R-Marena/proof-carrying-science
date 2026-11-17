# Soundness theorems (kernel-checked)

Toolchain: Lean 4.28.0. Package: `formal/` under this research directory.
Command: `cd formal && lake build`

No `sorry`, no `admit`, no custom axioms. Transitive axiom audit via `#print axioms`.

## Family A — Dependency correctness

| Theorem | File | Axioms |
|---|---|---|
| `deps_accounted` | Soundness | none |
| `unique_ids` | Soundness | none |
| `acyclic_rejects_self_loops` | Soundness | none |
| `acyclic_no_self_dep` | Dependency | none |
| `upwardClosed_contains_downstream` | Dependency | none |

## Family B–C — Invalidation

| Theorem | Notes | Axioms |
|---|---|---|
| `invalidation_soundness` | Downstream of a change is Affected | none |
| `invalidation_completeness` | Affected ⇒ exists seed path | none |
| `affected_step` | closure under one dependency edge | none |
| `affected_topology_only` | syntactic vs semantic sensitivity | none |
| `unaffected_not_changed` | | none |
| `new_edge_requires_new_graph_invalidation` | new edges need `g'` Affected | none |
| `affected_least` | inductive Affected is least upward-closed set | Classical.choice / propext / Quot.sound |

## Family D — Safe reuse

| Theorem | Axioms |
|---|---|
| `safe_reuse_preserves_obligation` | none |
| `reuse_entry_checks` | none |
| `reuse_requires_authority` / `eligibility` | none |

## Family E — Fresh correspondence (central)

| Theorem | Axioms |
|---|---|
| `incremental_implies_fresh` | propext, Classical.choice, Quot.sound |
| `incremental_accept_eq_fresh_accept` | same (via Nonempty unpack) |
| `fresh_implies_incremental_full_recheck` | definitional (full-seed path) |

**Substance:** `IncrementalAccept` no longer embeds `FreshValid`. The theorem
derives fresh validity from `FreshWitness`, `ChangesComplete`, new-graph
`Affected` rechecks, and authoritative eligible reuse.

**Gap:** Equivalence under *partial* reuse (not full recheck) as a bidirectional
equality of arbitrary executable traces remains outside the kernel; Python
establishes premises only differentially.

## Family F–G — Policy / version sensitivity

| Theorem | Axioms |
|---|---|
| `policy_sensitivity` | none |
| `version_sensitivity` | none |
| `op_change_breaks_eligibility` | none |

## Family H — Non-escalation

| Theorem | Axioms |
|---|---|
| `non_escalation` | propext |
| `mutation_safety_no_forgery` | propext |
| `demo_forged_rejected` | propext |
| `lookup_not_validity` | propext |

## Family I — Composition

| Theorem | Axioms |
|---|---|
| `compositional_fresh` | none |
| `compositional_from_local` | none |

## Family J — Mutation safety

| Theorem | Axioms |
|---|---|
| `mutation_breaks_dep_eligibility` | none |
| `mutation_breaks_evidence_eligibility` | none |
| `valid_state_outputs_agree` | (uses FreshWitness) |

## Correspondence

| Theorem | Axioms |
|---|---|
| `executableAcceptImpliesLeanFresh` | same as `incremental_implies_fresh` |

Documents that *if* an executable acceptance decodes to `IncrementalAccept`,
then Lean `FreshValid` holds. Decoding/algorithm refinement remain gaps.
Differential testing is **not** a refinement proof.
