# PCS generic-domain soundness report

This covers the domain-independent layer added to the production V2 formalization
(`PCS/V2/…`). It builds on `PCS.V2.Frontier.pcs_frontier_archive_acceptance_sound` and leaves
that theorem and every existing definition unchanged.

New files (2360 lines, all part of the default `PCS` library target):

| file | content |
|---|---|
| `PCS/V2/ClaimGraph.lean` | Theorem 2: heterogeneous proof-obligation graphs (Lean core only) |
| `PCS/V2/DomainAdapter.lean` | Theorem 1: generic domain adapters |
| `PCS/V2/DomainAuthority.lean` | Theorem 5: flagship for the production authority and for the authority extended with domain checkers |
| `PCS/V2/Proposer.lean` | Theorem 3: untrusted proposer non-authority |
| `PCS/V2/WorkflowRefinement.lean` | Theorem 4: compositional workflow refinement (Lean core only) |
| `PCS/V2/Witnesses/Registry.lean` | how domain checkers are registered (`registry_valid`) |
| `PCS/V2/Witnesses/Biology.lean` | witness 1: computational biology |
| `PCS/V2/Witnesses/AISafety.lean` | witness 2: AI-safety trace invariant |
| `PCS/V2/Witnesses/MLEval.lean` | witness 3: ML-evaluation split hygiene, run on the **unchanged production authority** |
| `PCS/V2/Witnesses/Instances.lean` | one shared registry for the witnesses, plus non-vacuity runs |
| `PCS/V2/Witnesses/WorkflowWitness.lean` | a small instance of Theorem 4 |
| `PCS/V2/GenericCounterexamples.lean` | falsification attempts (each proved) |
| `PCS/V2/GenericAudit.lean` | `#print axioms` for all 56 new results |

`PCS.lean` imports all of them. No existing file was modified apart from that import list.

---

## 1. Theorem statements and what they establish

### Theorem 2: obligation-graph root assurance (`PCS.V2.ClaimGraph`)

Data. A graph `Graph L C` is a list of nodes `⟨id, claim : C, kind⟩` plus a root id. A node's
`kind` is one of:

* `leaf (ob : L)`,
* `derive (rule : String) (children : List String)`,
* `unsupported tag`.

`L` (the obligation type) and `C` (the claim IR) can be any types. The only trusted component
is a `Checker L C`, made of `leaf : L → C → Bool` and `rule : String → C → List C → Bool`.

```lean
structure CheckerSound (V : Checker L C) (Sem : C → Prop) : Prop where
  leaf : ∀ ob c, V.leaf ob c = true → Sem c
  rule : ∀ r p cs, V.rule r p cs = true → (∀ c ∈ cs, Sem c) → Sem p

theorem root_assurance_sound [DecidableEq C] {V : Checker L C} {Sem : C → Prop}
    (hV : CheckerSound V Sem) {g : Graph L C} {goal : C}
    (h : checkGraph V g goal = true) : Sem goal

theorem accepted_graph_facts [DecidableEq C] {V : Checker L C} {g : Graph L C} {goal : C}
    (h : checkGraph V g goal = true) : AcceptedGraph V g goal
```

`AcceptedGraph` holds with **no** soundness assumption. It says:

* node ids are duplicate-free;
* the root exists and its claim is exactly `goal`;
* every node reachable from the root exists and passes its local check. So it is not
  `unsupported`, all of its children exist, its rule check passes, and if it is a leaf its
  validator accepts the leaf's *own* claim;
* no cycle passes through any reachable node.

Rejection corollaries: `cycle_rejected`, `missing_child_rejected`, `duplicate_ids_rejected`,
`unsupported_rejected`.

Heterogeneous evidence: `Checker.sumLeaf` and `sumLeaf_sound` combine validators over different
obligation types `L₁ ⊕ L₂` (formal, computational, empirical, external, …). The combined
validator is sound if each part is.

Scope. The theorem applies to any finite graph, including DAGs with shared children.
Termination is ensured by a fuel bound equal to the number of nodes. Cycles are caught by the
ancestor-path check (and in any case cannot pass, because of the fuel bound). Soundness does not
depend on the duplicate-id check, but acceptance guarantees it anyway.

### Theorem 1: generic domain-adapter soundness (`PCS.V2.DomainAdapter`)

```lean
structure Domain where
  World : Type
  Claim : Type
  [decEq : DecidableEq Claim]
  Holds : World → Claim → Prop

structure DomainAdapter (D : Domain) where
  IR : Type
  [decEqIR : DecidableEq IR]
  decode : JVal → Option D.Claim          -- typed decoding of the signed claim predicate
  compile : D.Claim → Option IR           -- typed compilation to the root obligation
  world : ArtifactTable → D.World          -- world given by the committed artifact bytes
  sem : D.World → IR → PropECB1�Mw��Z�