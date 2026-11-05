import PCS.V2.TranslationChecker
import PCS.V2.Canonical
import PCS.V2.JsonRoundtrip
import PCS.V2.Ed25519
import PCS.V2.Base64

/-!
# Wire format and executable front end of the semantic translation checker

`pcs-semantic-check` (`PCSSemanticCheck.lean`) reads two files — an authority
configuration and a translation request, both canonical JSON (RFC 8785 fragment of
`PCS.V2.Json`, keys sorted, no whitespace) — and prints the decision computed by
`semanticCheck`.

* **Strict, fail-closed decoding.**  Every object is matched against its exact canonical
  member list: a missing, extra, misspelled or mistyped field, a wrong schema tag, or a
  non-canonical byte string makes decoding fail, and the decision is `REJECTED` with
  `MALFORMED_INPUT`.  Constructs outside the fragment must be sent explicitly as
  `{"construct":…,"op":"unsupported"}` and are then rejected with `UNSUPPORTED_CONSTRUCT`.
* **Receipts are verified with Ed25519** (`PCS.V2.Ed25519.verify`, the project's verified
  RFC 8032 verifier) under role-separated authorized key lists, over domain-separated
  messages that bind the exact interpretation / Lean source / declaration / axioms.

Proved here:

* `decRequest_encRequest` — the request decoder inverts the canonical encoder (so the
  wire format loses no structure).
* `semanticCheck_decision` — whenever the input bytes decode, the decision is *exactly*
  `checkTranslation` of the decoded authority and request.
* `semanticCheck_accepted_iff` — the front end returns `ACCEPTED` iff the bytes decode to
  an authority/request pair satisfying the certified `TranslationContract`.
* `semanticCheck_encRequest` — **serialization refinement**: on the canonical bytes of any
  request `r` whose encoding is canonical, the front end's decision is the certified
  checker's decision on `r`.

Not proved (explicit runtime bridge): that the compiled binary computes `semanticCheck`
(compiler/runtime), file IO, and that the Python pipeline serializes the intended object.
-/

set_option autoImplicit false

namespace PCS.V2.Semantic

open PCS.V2.Json PCS.V2.Canonical

/-! ## Generic helpers -/

def decList {α : Type} (f : JVal → Option α) : List JVal → Option (List α)
  | [] => some []
  | v :: vs =>
    match f v, decList f vs with
    | some a, some as => some (a :: as)
    | _, _ => none

theorem decList_map {α : Type} (f : JVal → Option α) (enc : α → JVal) :
    ∀ (l : List α), (∀ a ∈ l, f (enc a) = some a) → decList f (l.map enc) = some l
  | [], _ => rfl
  | a :: as, h => by
    simp only [List.map, decList, h a List.mem_cons_self,
      decList_map f enc as (fun x hx => h x (List.mem_cons_of_mem _ hx))]

def decStr : JVal → Option String
  | .str s => some s
  | _ => none

def decOpt {α : Type} (f : JVal → Option α) : JVal → Option (Option α)
  | .null => some none
  | v => (f v).map some

def encOpt {α : Type} (enc : α → JVal) : Option α → JVal
  | none => .null
  | some a => enc a

theorem decOpt_encOpt {α : Type} (f : JVal → Option α) (enc : α → JVal)
    (hnull : ∀ a, enc a ≠ .null) (h : ∀ a, f (enc a) = some a) :
    ∀ o, decOpt f (encOpt enc o) = some o
  | none => rfl
  | some a => by
    simp only [encOpt]
    unfold decOpt
    split
    · rename_i he; exact absurd he (hnull a)
    · simp [h a]

def encStrs (l : List String) : JVal := .arr (l.map JVal.str)

def decStrs : JVal → Option (List String)
  | .arr vs => decList decStr vs
  | _ => none

theorem decStrs_encStrs (l : List String) : decStrs (encStrs l) = some l :=
  decList_map decStr JVal.str l (fun _ _ => rfl)

/-! ## Terms and formulas -/

mutual
def encTerm : Term → JVal
  | .var x => .obj [("var", .str x)]
  | .app f args => .obj [("args", .arr (encTerms args)), ("fn", .str f)]
def encTerms : List Term → List JVal
  | [] => []
  | t :: ts => encTerm t :: encTerms ts
end

mutual
def decTerm : JVal → Option Term
  | .obj [("var", .str x)] => some (.var x)
  | .obj [("args", .arr as), ("fn", .str f)] => (decTerms as).map (.app f)
  | _ => none
def decTerms : List JVal → Option (List Term)
  | [] => some []
  | a :: as =>
    match decTerm a, decTerms as with
    | some t, some ts => some (t :: ts)
    | _, _ => none
end

mutual
theorem decTerm_encTerm : ∀ t : Term, decTerm (encTerm t) = some t
  | .var x => by simp [encTerm, decTerm]
  | .app f args => by simp [encTerm, decTerm, decTerms_encTerms args]
theorem decTerms_encTerms : ∀ ts : List Term, decTerms (encTerms ts) = some ts
  | [] => by simp [encTerms, decTerms]
  | t :: ts => by simp [encTerms, decTerms, decTerm_encTerm t, decTerms_encTerms ts]
end

def encFormula : Formula → JVal
  | .tt => .obj [("op", .str "true")]
  | .ff => .obj [("op", .str "false")]
  | .pred p args => .obj [("args", .arr (encTerms args)), ("op", .str "pred"), ("symbol", .str p)]
  | .eq a b => .obj [("lhs", encTerm a), ("op", .str "eq"), ("rhs", encTerm b)]
  | .ne a b => .obj [("lhs", encTerm a), ("op", .str "ne"), ("rhs", encTerm b)]
  | .not φ => .obj [("arg", encFormula φ), ("op", .str "not")]
  | .and φ ψ => .obj [("lhs", encFormula φ), ("op", .str "and"), ("rhs", encFormula ψ)]
  | .or φ ψ => .obj [("lhs", encFormula φ), ("op", .str "or"), ("rhs", encFormula ψ)]
  | .imp φ ψ => .obj [("lhs", encFormula φ), ("op", .str "implies"), ("rhs", encFormula ψ)]
  | .quant .all x s φ =>
    .obj [("body", encFormula φ), ("op", .str "forall"), ("sort", .str s), ("var", .str x)]
  | .quant .ex x s φ =>
    .obj [("body", encFormula φ), ("op", .str "exists"), ("sort", .str s), ("var", .str x)]
  | .unsupported t => .obj [("construct", .str t), ("op", .str "unsupported")]

def bin {α β γ : Type} (k : α → β → γ) (a : Option α) (b : Option β) : Option γ :=
  match a, b with
  | some x, some y => some (k x y)
  | _, _ => none

def decFormula : JVal → Option Formula
  | .obj [("op", .str "true")] => some .tt
  | .obj [("op", .str "false")] => some .ff
  | .obj [("args", .arr as), ("op", .str "pred"), ("symbol", .str p)] => (decTerms as).map (.pred p)
  | .obj [("lhs", a), ("op", .str "eq"), ("rhs", b)] => bin Formula.eq (decTerm a) (decTerm b)
  | .obj [("lhs", a), ("op", .str "ne"), ("rhs", b)] => bin Formula.ne (decTerm a) (decTerm b)
  | .obj [("arg", a), ("op", .str "not")] => (decFormula a).map .not
  | .obj [("lhs", a), ("op", .str "and"), ("rhs", b)] => bin Formula.and (decFormula a) (decFormula b)
  | .obj [("lhs", a), ("op", .str "or"), ("rhs", b)] => bin Formula.or (decFormula a) (decFormula b)
  | .obj [("lhs", a), ("op", .str "implies"), ("rhs", b)] =>
    bin Formula.imp (decFormula a) (decFormula b)
  | .obj [("body", b), ("op", .str "forall"), ("sort", .str s), ("var", .str x)] =>
    (decFormula b).map (.quant .all x s)
  | .obj [("body", b), ("op", .str "exists"), ("sort", .str s), ("var", .str x)] =>
    (decFormula b).map (.quant .ex x s)
  | .obj [("construct", .str t), ("op", .str "unsupported")] => some (.unsupported t)
  | _ => none

theorem decFormula_encFormula : ∀ φ : Formula, decFormula (encFormula φ) = some φ
  | .tt | .ff | .unsupported _ => by simp [encFormula, decFormula]
  | .pred p args => by simp [encFormula, decFormula, decTerms_encTerms]
  | .eq a b | .ne a b => by simp [encFormula, decFormula, decTerm_encTerm, bin]
  | .not φ => by simp [encFormula, decFormula, decFormula_encFormula φ]
  | .and φ ψ | .or φ ψ | .imp φ ψ => by
    simp [encFormula, decFormula, decFormula_encFormula φ, decFormula_encFormula ψ, bin]
  | .quant .all x s φ | .quant .ex x s φ => by
    simp [encFormula, decFormula, decFormula_encFormula φ]

/-! ## Claims, interpretations, candidates -/

def encBinder (b : Binder) : JVal := .obj [("name", .str b.name), ("sort", .str b.sort)]

def decBinder : JVal → Option Binder
  | .obj [("name", .str x), ("sort", .str s)] => some ⟨x, s⟩
  | _ => none

def encClaim (c : SemanticClaim) : JVal :=
  .obj [("assumptions", .arr (c.assumptions.map encFormula)), ("conclusion", encFormula c.conclusion),
    ("params", .arr (c.params.map encBinder))]

def decClaim : JVal → Option SemanticClaim
  | .obj [("assumptions", .arr as), ("conclusion", c), ("params", .arr ps)] =>
    match decList decFormula as, decFormula c, decList decBinder ps with
    | some as', some c', some ps' => some ⟨ps', as', c'⟩
    | _, _, _ => none
  | _ => none

theorem decClaim_encClaim (c : SemanticClaim) : decClaim (encClaim c) = some c := by
  cases c with
  | mk ps as cl =>
    simp only [encClaim, decClaim,
      decList_map decFormula encFormula as (fun a _ => decFormula_encFormula a),
      decFormula_encFormula,
      decList_map decBinder encBinder ps (fun b _ => by cases b; rfl)]

def AmbiguityKind.name : AmbiguityKind → String
  | .scope => "scope" | .lexical => "lexical" | .symbol => "symbol"
  | .temporal => "temporal" | .referent => "referent" | .other => "other"

def decAmbiguityKind : String → Option AmbiguityKind
  | "scope" => some .scope | "lexical" => some .lexical | "symbol" => some .symbol
  | "temporal" => some .temporal | "referent" => some .referent | "other" => some .other
  | _ => none

theorem decAmbiguityKind_name (k : AmbiguityKind) : decAmbiguityKind k.name = some k := by
  cases k <;> rfl

def encAmbiguity (a : Ambiguity) : JVal :=
  .obj [("id", .str a.id), ("kind", .str a.kind.name), ("question", .str a.question),
    ("resolution", encOpt JVal.str a.resolution)]

def decAmbiguity : JVal → Option Ambiguity
  | .obj [("id", .str i), ("kind", .str k), ("question", .str q), ("resolution", r)] =>
    match decAmbiguityKind k, decOpt decStr r with
    | some k', some r' => some ⟨i, k', q, r'⟩
    | _, _ => none
  | _ => none

theorem decAmbiguity_encAmbiguity (a : Ambiguity) : decAmbiguity (encAmbiguity a) = some a := by
  cases a with
  | mk i k q r =>
    simp only [encAmbiguity, decAmbiguity, decAmbiguityKind_name,
      decOpt_encOpt decStr JVal.str (fun _ h => by cases h) (fun _ => rfl)]

def encAmbiguities (l : List Ambiguity) : JVal := .arr (l.map encAmbiguity)

def decAmbiguities : JVal → Option (List Ambiguity)
  | .arr vs => decList decAmbiguity vs
  | _ => none

theorem decAmbiguities_enc (l : List Ambiguity) : decAmbiguities (encAmbiguities l) = some l :=
  decList_map _ _ l (fun a _ => decAmbiguity_encAmbiguity a)

def encInterpretation (I : Interpretation) : JVal :=
  .obj [("ambiguities", encAmbiguities I.ambiguities),
    ("model_asserts_confirmed", .bool I.modelAssertsConfirmed), ("proposer", .str I.proposer),
    ("selected", encClaim I.selected), ("source_text", .str I.sourceText)]

def decInterpretation : JVal → Option Interpretation
  | .obj [("ambiguities", as), ("model_asserts_confirmed", .bool b), ("proposer", .str p),
      ("selected", c), ("source_text", .str s)] =>
    match decAmbiguities as, decClaim c with
    | some as', some c' => some ⟨s, p, b, c', as'⟩
    | _, _ => none
  | _ => none

theorem decInterpretation_enc (I : Interpretation) :
    decInterpretation (encInterpretation I) = some I := by
  cases I
  simp only [encInterpretation, decInterpretation, decAmbiguities_enc, decClaim_encClaim]

def encSymbolRef (g : SymbolRef) : JVal :=
  .obj [("lean_name", .str g.leanName), ("provenance", .str g.provenance), ("symbol", .str g.symbol)]

def decSymbolRef : JVal → Option SymbolRef
  | .obj [("lean_name", .str l), ("provenance", .str p), ("symbol", .str s)] => some ⟨s, l, p⟩
  | _ => none

/-! ## Registry entries and Explanation IR -/

def encSymbolEntry (e : SymbolEntry) : JVal :=
  match e.kind with
  | .pred ss => .obj [("args", encStrs ss), ("id", .str e.id), ("kind", .str "pred"),
      ("lean_name", .str e.leanName), ("provenance", .str e.provenance), ("result", .null)]
  | .fn ss r => .obj [("args", encStrs ss), ("id", .str e.id), ("kind", .str "fn"),
      ("lean_name", .str e.leanName), ("provenance", .str e.provenance), ("result", .str r)]

def decSymbolEntry : JVal → Option SymbolEntry
  | .obj [("args", ss), ("id", .str i), ("kind", .str "pred"), ("lean_name", .str l),
      ("provenance", .str p), ("result", .null)] => (decStrs ss).map (fun ss' => ⟨i, l, .pred ss', p⟩)
  | .obj [("args", ss), ("id", .str i), ("kind", .str "fn"), ("lean_name", .str l),
      ("provenance", .str p), ("result", .str r)] => (decStrs ss).map (fun ss' => ⟨i, l, .fn ss' r, p⟩)
  | _ => none

theorem decSymbolEntry_enc (e : SymbolEntry) : decSymbolEntry (encSymbolEntry e) = some e := by
  cases e with
  | mk i l k p => cases k <;> simp [encSymbolEntry, decSymbolEntry, decStrs_encStrs]

def encSortEntry (e : SortEntry) : JVal :=
  .obj [("id", .str e.id), ("lean_type", .str e.leanType), ("provenance", .str e.provenance)]

def decSortEntry : JVal → Option SortEntry
  | .obj [("id", .str i), ("lean_type", .str t), ("provenance", .str p)] => some ⟨i, t, p⟩
  | _ => none

def encExplNode : ExplNode → JVal
  | .always => .obj [("role", .str "always")]
  | .never => .obj [("role", .str "never")]
  | .atom p l args => .obj [("args", .arr (encTerms args)), ("lean_name", .str l),
      ("role", .str "atom"), ("symbol", .str p)]
  | .equal a b => .obj [("lhs", encTerm a), ("rhs", encTerm b), ("role", .str "equal")]
  | .notEqual a b => .obj [("lhs", encTerm a), ("rhs", encTerm b), ("role", .str "not_equal")]
  | .negation n => .obj [("arg", encExplNode n), ("role", .str "negation")]
  | .allOf a b => .obj [("lhs", encExplNode a), ("rhs", encExplNode b), ("role", .str "all_of")]
  | .anyOf a b => .obj [("lhs", encExplNode a), ("rhs", encExplNode b), ("role", .str "any_of")]
  | .ifThen a b => .obj [("conclusion", encExplNode b), ("premise", encExplNode a),
      ("role", .str "if_then")]
  | .forEvery x s n => .obj [("body", encExplNode n), ("role", .str "for_every"),
      ("sort", .str s), ("var", .str x)]
  | .thereExists x s n => .obj [("body", encExplNode n), ("role", .str "there_exists"),
      ("sort", .str s), ("var", .str x)]
  | .unsupported t => .obj [("construct", .str t), ("role", .str "unsupported")]

def decExplNode : JVal → Option ExplNode
  | .obj [("role", .str "always")] => some .always
  | .obj [("role", .str "never")] => some .never
  | .obj [("args", .arr as), ("lean_name", .str l), ("role", .str "atom"), ("symbol", .str p)] =>
    (decTerms as).map (.atom p l)
  | .obj [("lhs", a), ("rhs", b), ("role", .str "equal")] => bin ExplNode.equal (decTerm a) (decTerm b)
  | .obj [("lhs", a), ("rhs", b), ("role", .str "not_equal")] =>
    bin ExplNode.notEqual (decTerm a) (decTerm b)
  | .obj [("arg", a), ("role", .str "negation")] => (decExplNode a).map .negation
  | .obj [("lhs", a), ("rhs", b), ("role", .str "all_of")] =>
    bin ExplNode.allOf (decExplNode a) (decExplNode b)
  | .obj [("lhs", a), ("rhs", b), ("role", .str "any_of")] =>
    bin ExplNode.anyOf (decExplNode a) (decExplNode b)
  | .obj [("conclusion", b), ("premise", a), ("role", .str "if_then")] =>
    bin ExplNode.ifThen (decExplNode a) (decExplNode b)
  | .obj [("body", b), ("role", .str "for_every"), ("sort", .str s), ("var", .str x)] =>
    (decExplNode b).map (.forEvery x s)
  | .obj [("body", b), ("role", .str "there_exists"), ("sort", .str s), ("var", .str x)] =>
    (decExplNode b).map (.thereExists x s)
  | .obj [("construct", .str t), ("role", .str "unsupported")] => some (.unsupported t)
  | _ => none

theorem decExplNode_enc : ∀ n : ExplNode, decExplNode (encExplNode n) = some n
  | .always | .never | .unsupported _ => by simp [encExplNode, decExplNode]
  | .atom p l args => by simp [encExplNode, decExplNode, decTerms_encTerms]
  | .equal a b | .notEqual a b => by simp [encExplNode, decExplNode, decTerm_encTerm, bin]
  | .negation n => by simp [encExplNode, decExplNode, decExplNode_enc n]
  | .allOf a b | .anyOf a b | .ifThen a b => by
    simp [encExplNode, decExplNode, decExplNode_enc a, decExplNode_enc b, bin]
  | .forEvery x s n | .thereExists x s n => by
    simp [encExplNode, decExplNode, decExplNode_enc n]

def Quant.name : Quant → String
  | .all => "forall"
  | .ex => "exists"

def decQuant : String → Option Quant
  | "forall" => some .all
  | "exists" => some .ex
  | _ => none

def encQuantEntry (q : Quant × String × SortId) : JVal :=
  .obj [("quantifier", .str q.1.name), ("sort", .str q.2.2), ("var", .str q.2.1)]

def decQuantEntry : JVal → Option (Quant × String × SortId)
  | .obj [("quantifier", .str q), ("sort", .str s), ("var", .str x)] =>
    (decQuant q).map (fun q' => (q', x, s))
  | _ => none

def decNat : JVal → Option Nat
  | .num (.ofNat n) => some n
  | _ => none

def encExplanation (e : ExplanationIR) : JVal :=
  .obj [("assumptions", .arr (e.assumptions.map encExplNode)), ("conclusion", encExplNode e.conclusion),
    ("negations", .num e.negations), ("not_established", encStrs e.notEstablished),
    ("quantifiers", .arr (e.quantifiers.map encQuantEntry)),
    ("references", .arr (e.references.map encSymbolEntry)),
    ("sort_references", .arr (e.sortReferences.map encSortEntry)),
    ("trust_boundary", encStrs e.trustBoundary), ("variables", .arr (e.variables.map encBinder))]

def decExplanation : JVal → Option ExplanationIR
  | .obj [("assumptions", .arr as), ("conclusion", c), ("negations", n), ("not_established", ne),
      ("quantifiers", .arr qs), ("references", .arr rs), ("sort_references", .arr srs),
      ("trust_boundary", tb), ("variables", .arr vs)] =>
    match decList decExplNode as, decExplNode c, decNat n, decStrs ne, decList decQuantEntry qs,
      decList decSymbolEntry rs, decList decSortEntry srs, decStrs tb, decList decBinder vs with
    | some as', some c', some n', some ne', some qs', some rs', some srs', some tb', some vs' =>
      some ⟨vs', as', c', qs', n', rs', srs', tb', ne'⟩
    | _, _, _, _, _, _, _, _, _ => none
  | _ => none

theorem decExplanation_enc (e : ExplanationIR) : decExplanation (encExplanation e) = some e := by
  cases e with
  | mk vs as c qs n rs srs tb ne =>
    simp only [encExplanation, decExplanation,
      decList_map decExplNode encExplNode as (fun a _ => decExplNode_enc a), decExplNode_enc,
      decStrs_encStrs,
      decList_map decQuantEntry encQuantEntry qs (fun q _ => by
        obtain ⟨q, x, s⟩ := q; cases q <;> rfl),
      decList_map decSymbolEntry encSymbolEntry rs (fun e _ => decSymbolEntry_enc e),
      decList_map decSortEntry encSortEntry srs (fun e _ => by cases e; rfl),
      decList_map decBinder encBinder vs (fun b _ => by cases b; rfl)]
    rfl

def encCandidate (c : Candidate) : JVal :=
  .obj [("claim", encClaim c.claim), ("decl_name", .str c.declName),
    ("explanation", encOpt encExplanation c.explanation),
    ("groundings", .arr (c.groundings.map encSymbolRef)), ("lean_source", .str c.leanSource),
    ("model_confidence", .num c.modelConfidence), ("proposer", .str c.proposer)]

def decCandidate : JVal → Option Candidate
  | .obj [("claim", cl), ("decl_name", .str d), ("explanation", e), ("groundings", .arr gs),
      ("lean_source", .str src), ("model_confidence", conf), ("proposer", .str p)] =>
    match decClaim cl, decOpt decExplanation e, decList decSymbolRef gs, decNat conf with
    | some cl', some e', some gs', some conf' => some ⟨cl', gs', src, d, e', p, conf'⟩
    | _, _, _, _ => none
  | _ => none

theorem decCandidate_enc (c : Candidate) : decCandidate (encCandidate c) = some c := by
  cases c with
  | mk cl gs src d e p conf =>
    simp only [encCandidate, decCandidate, decClaim_encClaim,
      decOpt_encOpt decExplanation encExplanation (fun _ h => by cases h) decExplanation_enc,
      decList_map decSymbolRef encSymbolRef gs (fun g _ => by cases g; rfl)]
    rfl

/-! ## Receipts and requests -/

def encConfirmation (r : ConfirmationReceipt) : JVal :=
  .obj [("ambiguities", encAmbiguities r.ambiguities), ("authority", .str r.authority),
    ("selected", encClaim r.selected), ("signature", .str r.signature),
    ("source_text", .str r.sourceText)]

def decConfirmation : JVal → Option ConfirmationReceipt
  | .obj [("ambiguities", as), ("authority", .str a), ("selected", c), ("signature", .str sg),
      ("source_text", .str s)] =>
    match decAmbiguities as, decClaim c with
    | some as', some c' => some ⟨s, c', as', a, sg⟩
    | _, _ => none
  | _ => none

theorem decConfirmation_enc (r : ConfirmationReceipt) :
    decConfirmation (encConfirmation r) = some r := by
  cases r
  simp only [encConfirmation, decConfirmation, decAmbiguities_enc, decClaim_encClaim]

def encElaboration (r : ElaborationReceipt) : JVal :=
  .obj [("authority", .str r.authority), ("decl_name", .str r.declName),
    ("lean_source", .str r.leanSource), ("signature", .str r.signature)]

def decElaboration : JVal → Option ElaborationReceipt
  | .obj [("authority", .str a), ("decl_name", .str d), ("lean_source", .str s),
      ("signature", .str sg)] => some ⟨s, d, a, sg⟩
  | _ => none

def encProof (r : ProofReceipt) : JVal :=
  .obj [("authority", .str r.authority), ("axioms", encStrs r.axioms),
    ("decl_name", .str r.declName), ("lean_source", .str r.leanSource),
    ("signature", .str r.signature)]

def decProof : JVal → Option ProofReceipt
  | .obj [("authority", .str a), ("axioms", axs), ("decl_name", .str d), ("lean_source", .str s),
      ("signature", .str sg)] => (decStrs axs).map (fun axs' => ⟨s, d, axs', a, sg⟩)
  | _ => none

theorem decProof_enc (r : ProofReceipt) : decProof (encProof r) = some r := by
  cases r; simp [encProof, decProof, decStrs_encStrs]

/-- Wire schema tag of requests. -/
def requestSchema : String := "pcs-semantic-translation-v1"

def encRequest (r : Request) : JVal :=
  .obj [("candidate", encCandidate r.candidate),
    ("confirmation", encOpt encConfirmation r.confirmation),
    ("elaboration", encOpt encElaboration r.elaboration),
    ("interpretation", encInterpretation r.interpretation),
    ("proof", encOpt encProof r.proof), ("schema", .str requestSchema)]

def decRequest : JVal → Option Request
  | .obj [("candidate", c), ("confirmation", cf), ("elaboration", el), ("interpretation", i),
      ("proof", p), ("schema", .str "pcs-semantic-translation-v1")] =>
    match decCandidate c, decOpt decConfirmation cf, decOpt decElaboration el,
      decInterpretation i, decOpt decProof p with
    | some c', some cf', some el', some i', some p' => some ⟨i', cf', c', el', p'⟩
    | _, _, _, _, _ => none
  | _ => none

/-- **The request decoder inverts the canonical encoder.** -/
theorem decRequest_encRequest (r : Request) : decRequest (encRequest r) = some r := by
  cases r with
  | mk i cf c el p =>
    simp only [encRequest, requestSchema, decRequest, decCandidate_enc, decInterpretation_enc,
      decOpt_encOpt decConfirmation encConfirmation (fun _ h => by cases h) decConfirmation_enc,
      decOpt_encOpt decElaboration encElaboration (fun _ h => by cases h) (fun r => by cases r; rfl),
      decOpt_encOpt decProof encProof (fun _ h => by cases h) decProof_enc]

/-! ## Authority configuration and Ed25519 receipt verification -/

/-- Trusted authority configuration as it appears on the wire. -/
structure AuthorityConfig where
  registry : Registry
  requireElaboration : Bool
  requireProof : Bool
  allowedAxioms : List String
  confirmationKeys : List String
  elaborationKeys : List String
  proofKeys : List String
  deriving Repr, Inhabited

def decRegistry : JVal → Option Registry
  | .obj [("sorts", .arr ss), ("symbols", .arr ys)] =>
    match decList decSortEntry ss, decList decSymbolEntry ys with
    | some ss', some ys' => some ⟨ss', ys'⟩
    | _, _ => none
  | _ => none

def encRegistry (R : Registry) : JVal :=
  .obj [("sorts", .arr (R.sorts.map encSortEntry)), ("symbols", .arr (R.symbols.map encSymbolEntry))]

def authoritySchema : String := "pcs-semantic-authority-v1"

def decAuthorityConfig : JVal → Option AuthorityConfig
  | .obj [("allowed_axioms", ax), ("confirmation_keys", ck), ("elaboration_keys", ek),
      ("proof_keys", pk), ("registry", r), ("require_elaboration", .bool re),
      ("require_proof", .bool rp), ("schema", .str "pcs-semantic-authority-v1")] =>
    match decStrs ax, decStrs ck, decStrs ek, decStrs pk, decRegistry r with
    | some ax', some ck', some ek', some pk', some r' => some ⟨r', re, rp, ax', ck', ek', pk'⟩
    | _, _, _, _, _ => none
  | _ => none

def encAuthorityConfig (a : AuthorityConfig) : JVal :=
  .obj [("allowed_axioms", encStrs a.allowedAxioms), ("confirmation_keys", encStrs a.confirmationKeys),
    ("elaboration_keys", encStrs a.elaborationKeys), ("proof_keys", encStrs a.proofKeys),
    ("registry", encRegistry a.registry), ("require_elaboration", .bool a.requireElaboration),
    ("require_proof", .bool a.requireProof), ("schema", .str authoritySchema)]

/-- UTF-8 bytes of a domain-separated message. -/
def message (tag : String) (payload : JVal) : List UInt8 :=
  ((tag ++ "\n").toList ++ ser payload).utf8Encode.toList

/-- Signed payload of a confirmation receipt: the exact interpretation it confirms. -/
def confirmationMessage (r : ConfirmationReceipt) : List UInt8 :=
  message "pcs-semantic-confirmation-v1" (.obj [("ambiguities", encAmbiguities r.ambiguities),
    ("selected", encClaim r.selected), ("source_text", .str r.sourceText)])

def elaborationMessage (r : ElaborationReceipt) : List UInt8 :=
  message "pcs-semantic-elaboration-v1" (.obj [("decl_name", .str r.declName),
    ("lean_source", .str r.leanSource)])

def proofMessage (r : ProofReceipt) : List UInt8 :=
  message "pcs-semantic-proof-v1" (.obj [("axioms", encStrs r.axioms),
    ("decl_name", .str r.declName), ("lean_source", .str r.leanSource)])

/-- Ed25519 check: `authority` (base64 public key) is an authorized key for the role and
    `signature` (base64) verifies over `msg`. -/
def sigOK (keys : List String) (authority : String) (msg : List UInt8) (sig : String) : Bool :=
  keys.contains authority &&
    match PCS.V2.Base64.decode authority.toList, PCS.V2.Base64.decode sig.toList with
    | some pk, some s => PCS.V2.Ed25519.verify pk msg s
    | _, _ => false

/-- The executable authority induced by a configuration. -/
def AuthorityConfig.toAuthority (a : AuthorityConfig) : Authority :=
  { registry := a.registry,
    requireElaboration := a.requireElaboration,
    requireProof := a.requireProof,
    allowedAxioms := a.allowedAxioms,
    verifyConfirmation := fun r => sigOK a.confirmationKeys r.authority (confirmationMessage r) r.signature,
    verifyElaboration := fun r => sigOK a.elaborationKeys r.authority (elaborationMessage r) r.signature,
    verifyProof := fun r => sigOK a.proofKeys r.authority (proofMessage r) r.signature }

/-- A verified receipt names an authorized key of its role. -/
theorem sigOK_authorized {keys : List String} {a : String} {m : List UInt8} {s : String}
    (h : sigOK keys a m s = true) : a ∈ keys := by
  unfold sigOK at h
  simp only [Bool.and_eq_true] at h
  exact List.contains_iff_mem.mp h.1

/-! ## The executable front end -/

/-- Size limit on each input (bytes). -/
def maxInputBytes : Nat := 16777216

/-- What the front end computes. -/
structure CliResult where
  decision : Decision
  expectedLeanSource : String
  explanation : Option ExplanationIR
  deriving Repr, Inhabited

def malformed (component : String) : CliResult :=
  ⟨⟨.rejected, [⟨.malformedInput, component, "input is not canonical JSON of the expected schema"⟩]⟩,
    "", none⟩

/-- **The pure semantic-check front end** run by `pcs-semantic-check`. -/
def semanticCheck (authorityRaw requestRaw : ByteArray) : CliResult :=
  match (parseCanonicalBytes maxInputBytes authorityRaw).bind decAuthorityConfig with
  | none => malformed "authority"
  | some cfg =>
    match (parseCanonicalBytes maxInputBytes requestRaw).bind decRequest with
    | none => malformed "request"
    | some req =>
      let A := cfg.toAuthority
      let d := checkTranslation A req
      { decision := d,
        expectedLeanSource := renderClaimLean A.registry req.candidate.claim,
        explanation := if d.verdict = .accepted then some (toExplanation A.registry req.candidate.claim)
          else none }

def encDiagnostic (d : Diagnostic) : JVal :=
  .obj [("code", .str d.code.name), ("component", .str d.component), ("detail", .str d.detail)]

/-- Canonical JSON output of the front end. -/
def encCliResult (r : CliResult) : JVal :=
  .obj [("diagnostics", .arr (r.decision.diagnostics.map encDiagnostic)),
    ("expected_lean_source", .str r.expectedLeanSource),
    ("explanation", encOpt encExplanation r.explanation),
    ("explanation_literal", match r.explanation with
      | some e => .str e.renderLiteral
      | none => .null),
    ("schema", .str "pcs-semantic-decision-v1"),
    ("verdict", .str r.decision.verdict.name)]

def renderCliResult (r : CliResult) : String := String.ofList (ser (encCliResult r))

/-- When both inputs decode, the decision is exactly the certified checker's decision. -/
theorem semanticCheck_decision {aRaw rRaw : ByteArray} {cfg : AuthorityConfig} {req : Request}
    (ha : (parseCanonicalBytes maxInputBytes aRaw).bind decAuthorityConfig = some cfg)
    (hr : (parseCanonicalBytes maxInputBytes rRaw).bind decRequest = some req) :
    (semanticCheck aRaw rRaw).decision = checkTranslation cfg.toAuthority req := by
  unfold semanticCheck; rw [ha, hr]

/-- **The front end accepts iff the inputs decode to a pair satisfying the certified
    contract.** -/
theorem semanticCheck_accepted_iff (aRaw rRaw : ByteArray) :
    (semanticCheck aRaw rRaw).decision.verdict = .accepted ↔
      ∃ cfg req, (parseCanonicalBytes maxInputBytes aRaw).bind decAuthorityConfig = some cfg ∧
        (parseCanonicalBytes maxInputBytes rRaw).bind decRequest = some req ∧
        TranslationContract cfg.toAuthority req := by
  unfold semanticCheck
  constructor
  · intro h
    split at h
    · simp [malformed] at h
    · rename_i cfg hcfg
      split at h
      · simp [malformed] at h
      · rename_i req hreq
        exact ⟨cfg, req, hcfg, hreq,
          (translationAccepts_iff _ _).mp ((verdict_accepted_iff _ _).mp h)⟩
  · rintro ⟨cfg, req, hcfg, hreq, hc⟩
    rw [hcfg, hreq]
    exact (verdict_accepted_iff _ _).mpr ((translationAccepts_iff _ _).mpr hc)

/-- Malformed inputs are rejected. -/
theorem semanticCheck_malformed_request_rejected {aRaw rRaw : ByteArray}
    (h : (parseCanonicalBytes maxInputBytes rRaw).bind decRequest = none) :
    (semanticCheck aRaw rRaw).decision.verdict = .rejected := by
  unfold semanticCheck
  split
  · rfl
  · rw [h]; rfl

/-- **Serialization refinement**: on the canonical bytes of any request whose encoding is
    canonical (and within the size limit), the executable front end computes exactly the
    certified checker's decision on that request. -/
theorem semanticCheck_encRequest {aRaw : ByteArray} {cfg : AuthorityConfig} (r : Request)
    (ha : (parseCanonicalBytes maxInputBytes aRaw).bind decAuthorityConfig = some cfg)
    (hc : canonical (encRequest r) = true) (hs : (jcsBytes (encRequest r)).size ≤ maxInputBytes) :
    (semanticCheck aRaw (jcsBytes (encRequest r))).decision = checkTranslation cfg.toAuthority r := by
  apply semanticCheck_decision ha
  rw [parseCanonicalBytes_complete hc hs]
  exact decRequest_encRequest r

end PCS.V2.Semantic
