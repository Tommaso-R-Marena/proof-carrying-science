import PCS.V2.ClaimGraph

/-!
# Obligation-graph checking: exact characterisation and a memoised evaluator

1. **Completeness of the specification checker.**  `checkGraph_complete` proves the converse
   of `accepted_graph_facts`: every graph with duplicate-free ids, root bound to the goal,
   every reachable node present and locally valid, and no cycle through a reachable node is
   accepted.  Hence `checkGraph_iff`: `checkGraph V g goal = true ↔ AcceptedGraph V g goal`
   — the simple checker is an exact decision procedure for the structural specification.

2. **Memoised evaluator.**  `checkGraphMemo` runs a depth-first search that records every
   fully verified node id in a `done` list and never re-expands it (`visit_done`), so a shared
   sub-graph is evaluated once (polynomially many steps instead of one per root-to-node path).
   The current DFS stack still detects cycles, duplicate ids and missing nodes are still
   rejected, and the leaf / rule checks are unchanged.
   `checkGraphMemo_eq : checkGraphMemo V g goal = checkGraph V g goal` — the optimisation does
   not change any verdict, so every soundness theorem of the simple checker
   (`root_assurance_sound`, `accepted_graph_facts`, `domain_adapter_sound`, …) applies
   verbatim (`root_assurance_sound_memo`).
-/

set_option autoImplicit false

namespace PCS.V2.ClaimGraph

variable {L C : Type}

/-! ## Counting lemma -/

theorem nodup_length_le {α : Type} [DecidableEq α] :
    ∀ {l m : List α}, l.Nodup → (∀ a ∈ l, a ∈ m) → l.length ≤ m.length
  | [], _, _, _ => Nat.zero_le _
  | a :: l, m, hnd, hsub => by
    have ha : a ∈ m := hsub a List.mem_cons_self
    have hnd' := List.nodup_cons.mp hnd
    have : l.length ≤ (m.erase a).length :=
      nodup_length_le hnd'.2 (fun b hb => by
        have hba : b ≠ a := fun e => hnd'.1 (e ▸ hb)
        exact (List.mem_erase_of_ne hba).mpr (hsub b (List.mem_cons_of_mem _ hb)))
    rw [List.length_erase_of_mem ha] at this
    have hpos : 0 < m.length := List.length_pos_of_mem ha
    simp only [List.length_cons]
    omega

/-! ## Completeness of the specification checker -/

theorem reach_trans_edge {g : M�n��G!j�