/-!
# Heterogeneous proof-obligation graphs (Claim IR) and root-assurance soundness

A PCS claim is discharged by a *proof-obligation graph*: every node carries a typed claim
(an element of an arbitrary claim-IR type `C`) and is either

* a **leaf** carrying an obligation `ob : L` (formal proof, computational replay, empirical
  validation, external receipt, … — `L` is arbitrary, and `Checker.sumLeaf` combines
  validators for heterogeneous leaf kinds), or
* a **derivation** node naming a decomposition rule and the ids of its children, or
* an explicitly **unsupported** node (always rejected).

The graph is *untrusted data*: it may be produced by the package author, by the domain
adapter, or by an external proposer (see `PCS.V2.Proposer`).  Only the `Checker` is
trusted, and only through the two local soundness obligations of `CheckerSound`:

* `leaf`  — a leaf obligation that the validator accepts for a claim denotes that claim;
* `rule`  — a decomposition rule accepted by the rule checker is semantics-preserving
  (all child claims true ⇒ parent claim true).

`checkGraph V g goal` is the deterministic graph checker.  It **rejects**

* duplicate node ids (`Nodup` check),
* a missing root, or a root whose claim is not the expected `goal` (wrong claim binding),
* a reference to a missing child (unresolved obligation),
* an `unsupported` node,
* a leaf whose validator does not accept the leaf's *own* claim
  (so an accepted leaf can never stand for a different proposition than the one its
  parent's rule check consumed),
* any cycle reachable from the root (a node met again on the current path),
* any graph deeper than its number of nodes (fuel).

Main results:

* `root_assurance_sound` — acceptance + `CheckerSound` ⇒ the root claim's semantics.
* `accepted_graph_facts` — acceptance alone ⇒ duplicate-free ids, root bound to `goal`,
  every reachable node present and supported, every reachable derivation's children
  present and its rule check passing, every reachable leaf discharged, and **no cycle
  through any reachable node**.

The file depends only on Lean core.
-/

set_option autoImplicit false

namespace PCS.VM�mt�G!j�