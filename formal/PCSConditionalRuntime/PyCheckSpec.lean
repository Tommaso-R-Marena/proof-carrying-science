import PCSConditionalRuntime.PyJson

/-!
# Statement of the Python conditional refinement theorem

* `tlook`, `FDen`, `TaskDen` — when a JSON tree denotes a typed formula / conditional task (key
  order and extra keys are irrelevant to the checker, which reads fields by key);
* `receiptT` — the JSON receipt the current `check` returns for a reference receipt
  `PCSDD.check t lim`, with the two digests supplied by the (unextracted) `digest` function;
* `ValidateAccepts`, `DigestOK` — the contracts assumed of the two unextracted callees
  `validate` and `digest` (the only behaviour of theirs that the proof uses).
-/

namespace PCSCR.Py

open PCSCR PCSDD PCSOmega

/-- First value of a key in a JSON object. -/
def tlook : List (String × T) → String → Option T
  | [], _ => none
  | (k, v) :: rest, x => if k = x then some v else tlook rest x

/-- A JSON tree denotes a typed formula over `names` (fields are read by key). -/
def FDen (names : List String) {n : Nat} : T → BForm n → Prop
  | .obj kvs, .atom i => tlook kvs "op" = some (.str "atom") ∧
      tlook kvs "symbol" = some (.str (names.getD i.val ""))
  | .obj kvs, .tt => tlook kvs "op" = some (.str "true")
  | .obj kvs, .ff => tlook kvs "op" = some (.str "false")
  | .obj kvs, .not f => tlook kvs "op" = some (.str "not") ∧
      ∃ b, tlook kvs "body" = some b ∧ FDen names b f
  | .obj kvs, .and f g => tlook kvs "op" = some (.str "and") ∧
      ∃ l r, tlook kvs "left" = some l ∧ tlook kvs "right" = some r ∧ FDen names l f ∧ FDen names r g
  | .obj kvs, .or f g => tlook kvs "op" = some (.str "or") ∧
      ∃ l r, tlook kvs "left" = some l ∧ tlook kvs "right" = some r ∧ FDen names l f ∧ FDen names r g
  | .obj kvs, .imp f g => tlook kvs "op" = some (.str "implies") ∧
      ∃ l r, tlook kvs "left" = some l ∧ tlook kvs "right" = some r ∧ FDen names l f ∧ FDen names r g
  | _, _ => False

/-- A JSON tree denotes the typed conditional task `t` over the declared `names`. -/
def TaskDen (names : List String) (tj : T) (t : CTask names.length) : Prop :=
  ∃ kvs s c as, tj = .obj kvs ∧ tlook kvs "variables" = some (.arr (names.map T.str)) ∧
    tlook kvs "source" = some s ∧ FDen names s t.source ∧
    tlook kvs "candidate" = some c ∧ FDen names c t.candidate ∧
    tlook kvs "assumptions" = some (.arr as) ∧ as.length = t.assumptions.length ∧
    ∀ p ∈ as.zip t.assumptions, FDen names p.1 p.2

/-! ## The receipt as a JSON tree -/

/-- An assignment as the dictionary `{name: bool}` built by `Diagram.world`. -/
def asgT (names : List String) (w : List Bool) : T :=
  .obj ((names.zip w).map fun p => (p.1, .bool p.2))

def optT {α : Type} (f : α → T) : Option α → T
  | none => .null
  | some a => f a

def natT (x : Nat) : T := .int (x : Int)

def decisionT : Decision → T
  | .equivalentUnderAssumptions => .str "equivalent_under_assumptions"
  | .counterexample => .str "counterexample"
  | .inconsistentAssumptions => .str "inconsistent_assumptions"
  | .resourceLimit => .str "resource_limit"

def cexT (names : List String) (c : CexRec) : T :=
  .obj [("assignment", asgT names c.assignment), ("source_true", .bool c.sourceTrue),
        ("candidate_true", .bool c.candidateTrue),
        ("assumptions_true", .arr (c.assumptionsTrue.map T.bool))]

def witsT (names : List String) (ws : List (Nat × List Bool)) : T :=
  .arr (ws.map fun p => .obj [("removed_assumption", natT p.1), ("assignment", asgT names p.2)])

def nodeT (nd : Node) : T := .arr [natT nd.var, natT nd.low, natT nd.high]

def diagramT (d : DiagramRec) : T :=
  .obj [("nodes", .arr (d.nodes.toList.map nodeT)), ("source", optT natT d.source),
        ("candidate", optT natT d.candidate), ("context", natT d.context),
        ("difference", optT natT d.difference)]

def workT (w : Work) : T :=
  .obj [("bdd_nodes", natT w.bddNodes), ("apply_calls", natT w.applyCalls),
        ("ast_visits", natT w.astVisits), ("witness_steps", natT w.witnessSteps)]

/-- Receipt fields (in the insertion order of the Python dictionary), before `receipt_sha256`. -/
def receiptFields (names : List String) (tj : T) (taskDigest : String) (r : CReceipt names.length) :
    List (String × T) :=
  [("format", .str "pcs-conditional-boolean-receipt-v1"), ("checker", .str "pcs-conditional-bdd/1"),
   ("original_task", tj), ("task_sha256", .str taskDigest), ("limits", limT r.limits),
   ("decision", decisionT r.decision), ("context_example", optT (asgT names) r.contextExample),
   ("counterexample", optT (cexT names) r.counterexample),
   ("unsat_core", optT (fun c => .arr (c.map natT)) r.unsatCore),
   ("core_necessity_witnesses", optT (witsT names) r.coreWitnesses),
   ("diagram", optT diagramT r.diagram), ("limit_reached", optT (fun e => .str e.name) r.limitReached),
   ("scope", .str "Declared Boolean interpretations and explicit assumptions only"),
   ("pcs_authority", .bool r.pcsAuthority), ("lean_kernel_checked", .bool r.leanKernelChecked),
   ("work", workT r.work)]

/-- The complete receipt returned by `check`, given the digest function `dg`. -/
def receiptT (names : List String) (tj : T) (dg : T → String) (r : CReceipt names.length) : T :=
  .obj (receiptFields names tj (dg tj) r ++
    [("receipt_sha256", .str (dg (.obj (receiptFields names tj (dg tj) r))))])

/-! ## Contracts of the unextracted callees -/

/-- `validate` accepts (every heap copy of) the task `tj` and returns its argument unchanged. -/
def ValidateAccepts (ext : Ext) (tj : T) : Prop :=
  ∀ (h : Heap) (v : V) (fu : Nat), readback fu h v = some tj → ext "validate" [v] h = .ok v h

/-- `digest` returns the digest `dg` of the JSON value of its argument, without heap effects. -/
def DigestOK (ext : Ext) (dg : T → String) : Prop :=
  ∀ (h : Heap) (v : V) (fu : Nat) (t : T), readback fu h v = some t → ext "digest" [v] h = .ok (.str (dg t)) h

end PCSCR.Py
