import PCS.V2.CertificateModel

/-!
# Semantic meaning of the static workflow-replay stage (`verify_static_workflow_replay_v06`)

Before this module the authority's workflow oracle was a naked Boolean copied from the
Python transcript (`workflow_ok`).  Here the Lean authority **itself** checks every signed
static-workflow claim of the certificate against a *normalized static analysis*
(`FreshSource`) of the committed source artifacts:

* the signed proposition (a JSON string inside the signed certificate) is parsed by Lean;
* `static_only = true`, `user_code_executed = false`, `human_confirmed = true`;
* inference identity, source path and source kind agree with the analysis;
* the analysed source is a committed certificate artifact with that `source_path`;
* the node lists its source artifact as an input;
* `exact_resolved_set`: claimed inputs/outputs are exactly the rediscovered sets;
  `claimed_subset`: claimed inputs/outputs are among the rediscovered sets;
* every signed resolved reference `(kind, path, artifact_id)` was rediscovered;
* `operation = "static_<source_kind>_workflow"`.

`workflowCheckB_sound` proves that the executable check implies the declarative
`WorkflowDescribes` relation.  The *only* remaining workflow assumption is the narrow
front-end contract that each `FreshSource` is the static analyser's normalized result on
the exact committed source bytes (see `PCS.V2.HighAssurance.WorkflowFrontEnd`); the
claim-comparison logic is no longer trusted.

The signed proposition may contain non-integral JSON numbers (`confidence`), which lie
outside the verified canonical-JSON fragment `JVal`; `PVal` keeps such numbers as raw
text.  The Lean check never interprets numbers; comparison of `confidence` and
`analysis_mode` in `exact_resolved_set` mode remains part of the production Boolean, which
is still required (conjunctively) by the authority.
-/

namespace PCS.V2.Workflow

open PCS.V2.Json PCS.V2.Package PCS.V2.CertificateModel PCS.V2.Common

/-- JSON values of a signed workflow proposition; numbers are kept as raw text. -/
inductive PVal where
  | null
  | bool (b : Bool)
  | num (raw : String)
  | str (s : String)
  | arr (xs : List PVal)
  | obj (ms : List (String × PVal))
  deriving Inhabited

def pfield (ms : List (String × PVal)) (k : String) : Option PVal :=
  (ms.find? (fun kv => kv.1 == k)).map (·.2)

def pstr : Option PVal → Option String
  | some (.str s) => some s
  | _ => none

def pbool : Option PVal → Option Bool
  | some (.bool b) => some b
  | _ => none

def parr : Option PVal → Option (List PVal)
  | some (.arr xs) => some xs
  | _ => none

/-! ## Proposition parser (fail-closed: duplicate keys and trailing input are rejected) -/

def isDigitC (c : Char) : Bool := '0' ≤ c && c ≤ '9'

def spanD : List Char → List Char × List Char
  | [] => ([], [])
  | c :: r => if isDigitC c then let p := spanD r; (c :: p.1, p.2) else ([], c :: r)

/-- `-? digits ('.' digits)? ([eE] [+-]? digits)?`, returned as raw text. -/
def parseNumber (cs : List Char) : Option (List Char × List Char) :=
  let (sign, r0) := match cs with
    | '-' :: r => (['-'], r)
    | r => ([], r)
  match spanD r0 with
  | ([], _) => none
  | (int, r1) =>
    let frac : Option (List Char × List Char) := match r1 with
      | '.' :: r => match spanD r with
        | ([], _) => none
        | (ds, r') => some ('.' :: ds, r')
      | r => some ([], r)
    match frac with
    | none => none
    | some (fr, r2) =>
      let ex : Option (List Char × List Char) := match r2 with
        | e :: r => if e = 'e' ∨ e = 'E' then
            let (sg, r') := match r with
              | '+' :: q => (['+'], q)
              | '-' :: q => (['-'], q)
              | q => ([], q)
            match spanD r' with
            | ([], _) => none
            | (ds, r'') => some (e :: sg ++ ds, r'')
          else some ([], e :: r)
        | [] => some ([], [])
      match ex with
      | none => none
      | some (exs, r3) => some (sign ++ int ++ fr ++ exs, r3)

mutual
def pVal : Nat → List Char → Option (PVal × List Char)
  | 0, _ => none
  | _ + 1, [] => none
  | n + 1, c :: r =>
    if c = 'n' then
      match r with
      | 'u' :: 'l' :: 'l' :: r' => some (.null, r')
      | _ => none
    else if c = 't' then
      match r with
      | 'r' :: 'u' :: 'e' :: r' => some (.bool true, r')
      | _ => none
    else if c = 'f' then
      match r with
      | 'a' :: 'l' :: 's' :: 'e' :: r' => some (.bool false, r')
      | _ => none
    else if c = '"' then
      (parseStrBody r).map fun p => (.str (String.ofList p.1), p.2)
    else if c = '[' then
      match r with
      | ']' :: r' => some (.arr [], r')
      | _ =>
        match pVal n r with
        | some (x, r') =>
          match pElems n r' with
          | some (xs, r'') => some (.arr (x :: xs), r'')
          | none => none
        | none => none
    else if c = '{' then
      match r with
      | '}' :: r' => some (.obj [], r')
      | '"' :: r1 =>
        match parseStrBody r1 with
        | some (k, ':' :: r2) =>
          match pVal n r2 with
          | some (v, r3) =>
            match pMembers n r3 with
            | some (ms, r4) =>
              let all := (String.ofList k, v) :: ms
              if (all.map (·.1)).Nodup then some (.obj all, r4) else none
            | none => none
          | none => none
        | _ => none
      | _ => none
    else if c = '-' ∨ isDigitC c then
      (parseNumber (c :: r)).map fun p => (.num (String.ofList p.1), p.2)
    else none

def pElems : Nat → List Char → Option (List PVal × List Char)
  | 0, _ => none
  | _ + 1, ']' :: r => some ([], r)
  | n + 1, ',' :: r =>
    match pVal n r with
    | some (x, r') =>
      match pElems n r' with
      | some (xs, r'') => some (x :: xs, r'')
      | none => none
    | none => none
  | _ + 1, _ => none

def pMembers : Nat → List Char → Option (List (String × PVal) × List Char)
  | 0, _ => none
  | _ + 1, '}' :: r => some ([], r)
  | n + 1, ',' :: '"' :: r1 =>
    match parseStrBody r1 with
    | some (k, ':' :: r2) =>
      match pVal n r2 with
      | some (v, r3) =>
        match pMembers n r3 with
        | some (ms, r4) => some ((String.ofList k, v) :: ms, r4)
        | none => none
      | none => none
    | _ => none
  | _ + 1, _ => none
end

/-- Parse a complete signed proposition string. -/
def parseProp (s : String) : Option PVal :=
  match pVal (s.length + 1) s.toList with
  | some (v, []) => some v
  | _ => none

/-! ## Normalized static analysis (the front-end output) -/

/-- Normalized result of statically analysing one committed source artifact. -/
structure FreshSource where
  inferenceId : String
  sourceArtifactId : String
  sourcePath : String
  sourceKind : String
  inputs : List String
  outputs : List String
  /-- rediscovered resolved references `(kind, path, artifact_id)` -/
  refs : List (String × String × String)
  deriving Repr, DecidableEq

def decodeRef (v : JVal) : Option (String × String × String) := do
  let ms ← objOf v
  let k ← strField ms "kind"
  let p ← strField ms "path"
  let a ← strField ms "artifact_id"
  pure (k, p, a)

def decodeFreshSource (v : JVal) : Option FreshSource := do
  let ms ← objOf v
  let inferenceId ← strField ms "inference_id"
  let sourceArtifactId ← strField ms "source_artifact_id"
  let sourcePath ← strField ms "source_path"
  let sourceKind ← strField ms "source_kind"
  let inputs ← (field ms "inputs").bind strArray
  let outputs ← (field ms "outputs").bind strArray
  let refs ← (field ms "references").bind arrOf >>= mapOpt decodeRef
  pure { inferenceId, sourceArtifactId, sourcePath, sourceKind, inputs, outputs, refs }

/-! ## Declarative semantics -/

def workflowNamespace : String := "pcs-manifest-workflow-contract-v1"
def workflowInferenceFormat : String := "pcs-static-workflow-map-v1"

/-- The certificate workflow node `nm` carries the signed static-workflow proposition `sg`. -/
def StaticContract (nm : List (String × JVal)) (sg : List (String × PVal)) : Prop :=
  ∃ c p, field nm "contract" = some (.obj c) ∧ strField c "type" = some "external" ∧
    strField c "namespace" = some workflowNamespace ∧ field c "proposition" = some (.str p) ∧
    parseProp p = some (.obj sg) ∧ pstr (pfield sg "inference_format") = some workflowInferenceFormat

/-- A signed resolved reference `(kind, path, artifact_id)`; all three must be strings. -/
def refKey : PVal → Option (String × String × String)
  | .obj ms =>
    match pstr (pfield ms "kind"), pstr (pfield ms "path"), pstr (pfield ms "artifact_id") with
    | some k, some p, some a => some (k, p, a)
    | _, _, _ => none
  | _ => none

def SubsetL (xs ys : List String) : Prop := ∀ x ∈ xs, x ∈ ys

/-- **Signed-claim semantics**: the signed claim `(nm, sg)` is described by the analysis `f`. -/
def ClaimMatches (f : FreshSource) (nm : List (String × JVal)) (sg : List (String × PVal)) : Prop :=
  pstr (pfield sg "inference_id") = some f.inferenceId ∧
  pbool (pfield sg "static_only") = some true ∧
  pbool (pfield sg "user_code_executed") = some false ∧
  pbool (pfield sg "human_confirmed") = some true ∧
  pstr (pfield sg "source_path") = some f.sourcePath ∧
  pstr (pfield sg "source_kind") = some f.sourceKind ∧
  strField nm "operation" = some ("static_" ++ f.sourceKind ++ "_workflow") ∧
  ∃ ins outs refs, (field nm "inputs").bind strArray = some ins ∧
    (field nm "outputs").bind strArray = some outs ∧
    parr (pfield sg "resolved_references") = some refs ∧
    f.sourceArtifactId ∈ ins ∧
    ((pstr (pfield sg "dependency_claim_mode") = some "exact_resolved_set" ∧
        SubsetL ins f.inputs ∧ SubsetL f.inputs ins ∧ SubsetL outs f.outputs ∧ SubsetL f.outputs outs) ∨
     (pstr (pfield sg "dependency_claim_mode") = some "claimed_subset" ∧
        SubsetL ins f.inputs ∧ SubsetL outs f.outputs)) ∧
    ∀ r ∈ refs, ∃ k, refKey r = some k ∧ k ∈ f.refs

/-- The analysed source is a committed certificate artifact with the analysed source path
    (so the analysis is about digest-bound artifact bytes). -/
def SourceBound (cert : List (String × JVal)) (f : FreshSource) : Prop :=
  ∃ arts am, (field cert "artifacts").bind arrOf = some arts ∧ JVal.obj am ∈ arts ∧
    strField am "id" = some f.sourceArtifactId ∧ strField am "source_path" = some f.sourcePath

/-- **`WorkflowDescribes`**: every signed static-workflow claim of the certificate is
    described, in the sense of `ClaimMatches`, by a bound analysis in `fa`. -/
def WorkflowDescribes (fa : List FreshSource) (cert : List (String × JVal)) : Prop :=
  ∀ w ns, field cert "workflow" = some (.obj w) → field w "nodes" = some (.arr ns) →
    ∀ nm, JVal.obj nm ∈ ns → ∀ sg, StaticContract nm sg →
      ∃ f ∈ fa, SourceBound cert f ∧ ClaimMatches f nm sg

/-! ## Executable check -/

def refsOK (f : FreshSource) (refs : List PVal) : Bool :=
  refs.all fun r => match refKey r with
    | some k => f.refs.contains k
    | none => false

def subsetB (xs ys : List String) : Bool := xs.all (ys.contains ·)

def modeOK (f : FreshSource) (sg : List (String × PVal)) (ins outs : List String) : Bool :=
  match pstr (pfield sg "dependency_claim_mode") with
  | some "exact_resolved_set" =>
    subsetB ins f.inputs && subsetB f.inputs ins && subsetB outs f.outputs && subsetB f.outputs outs
  | some "claimed_subset" => subsetB ins f.inputs && subsetB outs f.outputs
  | _ => false

def claimB (f : FreshSource) (nm : List (String × JVal)) (sg : List (String × PVal)) : Bool :=
  pstr (pfield sg "inference_id") == some f.inferenceId &&
  pbool (pfield sg "static_only") == some true &&
  pbool (pfield sg "user_code_executed") == some false &&
  pbool (pfield sg "human_confirmed") == some true &&
  pstr (pfield sg "source_path") == some f.sourcePath &&
  pstr (pfield sg "source_kind") == some f.sourceKind &&
  strField nm "operation" == some ("static_" ++ f.sourceKind ++ "_workflow") &&
  match (field nm "inputs").bind strArray, (field nm "outputs").bind strArray,
      parr (pfield sg "resolved_references") with
  | some ins, some outs, some refs => ins.contains f.sourceArtifactId && modeOK f sg ins outs && refsOK f refs
  | _, _, _ => false

def artOK (f : FreshSource) : JVal → Bool
  | .obj am => strField am "id" == some f.sourceArtifactId && strField am "source_path" == some f.sourcePath
  | _ => false

def boundB (cert : List (String × JVal)) (f : FreshSource) : Bool :=
  match (field cert "artifacts").bind arrOf with
  | some arts => arts.any (artOK f)
  | none => false

/-- Check one certificate workflow node (fail-closed on malformed static contracts,
    mirroring `_static_contract`, which raises in those cases). -/
def nodeOK (fa : List FreshSource) (cert : List (String × JVal)) : JVal → Bool
  | .obj nm =>
    match field nm "contract" with
    | some (.obj c) =>
      if strField c "type" == some "external" && strField c "namespace" == some workflowNamespace then
        match field c "proposition" with
        | some (.str p) =>
          match parseProp p with
          | some (.obj sg) =>
            if pstr (pfield sg "inference_format") == some workflowInferenceFormat then
              fa.any fun f => claimB f nm sg && boundB cert f
            else true
          | some _ => true
          | none => false
        | _ => false
      else true
    | _ => true
  | _ => false

/-- The Lean workflow-stage decision. -/
def workflowCheckB (fa : List FreshSource) (cert : List (String × JVal)) : Bool :=
  match field cert "workflow" with
  | none => true
  | some (.obj w) =>
    match field w "nodes" with
    | none => true
    | some (.arr ns) => ns.all (nodeOK fa cert)
    | some _ => false
  | some _ => false

/-! ## Soundness -/

theorem subsetB_sound {xs ys : List String} (h : subsetB xs ys = true) : SubsetL xs ys := by
  intro x hx
  simp only [subsetB, List.all_eq_true] at h
  simpa using h x hx

theorem modeOK_sound {f : FreshSource} {sg : List (String × PVal)} {ins outs : List String}
    (h : modeOK f sg ins outs = true) :
    (pstr (pfield sg "dependency_claim_mode") = some "exact_resolved_set" ∧
        SubsetL ins f.inputs ∧ SubsetL f.inputs ins ∧ SubsetL outs f.outputs ∧ SubsetL f.outputs outs) ∨
     (pstr (pfield sg "dependency_claim_mode") = some "claimed_subset" ∧
        SubsetL ins f.inputs ∧ SubsetL outs f.outputs) := by
  unfold modeOK at h
  split at h
  · rename_i hm
    simp only [Bool.and_eq_true] at h
    exact Or.inl ⟨hm, subsetB_sound h.1.1.1, subsetB_sound h.1.1.2, subsetB_sound h.1.2,
      subsetB_sound h.2⟩
  · rename_i hm
    simp only [Bool.and_eq_true] at h
    exact Or.inr ⟨hm, subsetB_sound h.1, subsetB_sound h.2⟩
  · cases h

theorem refsOK_sound {f : FreshSource} {refs : List PVal} (h : refsOK f refs = true) :
    ∀ r ∈ refs, ∃ k, refKey r = some k ∧ k ∈ f.refs := by
  intro r hr
  simp only [refsOK, List.all_eq_true] at h
  have := h r hr
  split at this
  · rename_i k hk
    exact ⟨k, hk, by simpa using this⟩
  · cases this

theorem claimB_sound {f : FreshSource} {nm : List (String × JVal)} {sg : List (String × PVal)}
    (h : claimB f nm sg = true) : ClaimMatches f nm sg := by
  unfold claimB at h
  simp only [Bool.and_eq_true, beq_iff_eq] at h
  obtain ⟨⟨⟨⟨⟨⟨⟨h1, h2⟩, h3⟩, h4⟩, h5⟩, h6⟩, h7⟩, h8⟩ := h
  refine ⟨h1, h2, h3, h4, h5, h6, h7, ?_⟩
  split at h8
  · rename_i ins outs refs hi ho hr
    simp only [Bool.and_eq_true] at h8
    exact ⟨ins, outs, refs, hi, ho, hr, by simpa using h8.1.1, modeOK_sound h8.1.2,
      refsOK_sound h8.2⟩
  · cases h8

theorem boundB_sound {cert : List (String × JVal)} {f : FreshSource} (h : boundB cert f = true) :
    SourceBound cert f := by
  unfold boundB at h
  split at h
  · rename_i arts ha
    obtain ⟨a, hmem, hok⟩ := List.any_eq_true.1 h
    cases a with
    | obj am =>
      simp only [artOK, Bool.and_eq_true, beq_iff_eq] at hok
      exact ⟨arts, am, ha, hmem, hok.1, hok.2⟩
    | _ => simp [artOK] at hok
  · cases h

theorem nodeOK_sound {fa : List FreshSource} {cert : List (String × JVal)}
    {nm : List (String × JVal)} (h : nodeOK fa cert (.obj nm) = true)
    {sg : List (String × PVal)} (hs : StaticContract nm sg) :
    ∃ f ∈ fa, SourceBound cert f ∧ ClaimMatches f nm sg := by
  obtain ⟨c, p, hc, ht, hn, hp, hpp, hf⟩ := hs
  simp only [nodeOK, hc, ht, hn, hp, hpp, hf, beq_self_eq_true, Bool.and_self, if_true] at h
  obtain ⟨f, hfm, hok⟩ := List.any_eq_true.1 h
  simp only [Bool.and_eq_true] at hok
  exact ⟨f, hfm, boundB_sound hok.2, claimB_sound hok.1⟩

/-- **Soundness of the Lean workflow stage**: acceptance implies `WorkflowDescribes`. -/
theorem workflowCheckB_sound {fa : List FreshSource} {cert : List (String × JVal)}
    (h : workflowCheckB fa cert = true) : WorkflowDescribes fa cert := by
  intro w ns hw hns nm hnm sg hs
  simp only [workflowCheckB, hw, hns, List.all_eq_true] at h
  exact nodeOK_sound (h _ hnm) hs

/-! ## The narrow front-end contract -/

/-- **Workflow semantics relative to a front-end meaning `A`**: every signed static claim
    is matched by a bound analysis record that satisfies `A`.  Instantiate `A f` with
    "`f` is the static analyser's normalized result on the exact committed bytes of
    artifact `f.sourceArtifactId`" to obtain the intended reading: the committed source
    bytes denote (under the analyser) at least the dependency relation the certificate
    claims. -/
def WorkflowSemantics (A : FreshSource → Prop) (cert : List (String × JVal)) : Prop :=
  ∀ w ns, field cert "workflow" = some (.obj w) → field w "nodes" = some (.arr ns) →
    ∀ nm, JVal.obj nm ∈ ns → ∀ sg, StaticContract nm sg →
      ∃ f, A f ∧ SourceBound cert f ∧ ClaimMatches f nm sg

theorem workflowDescribes_semantics {fa : List FreshSource} {cert : List (String × JVal)}
    {A : FreshSource → Prop} (h : WorkflowDescribes fa cert) (hA : ∀ f ∈ fa, A f) :
    WorkflowSemantics A cert := by
  intro w ns hw hns nm hnm sg hs
  obtain ⟨f, hf, hb, hc⟩ := h w ns hw hns nm hnm sg hs
  exact ⟨f, hA f hf, hb, hc⟩

end PCS.V2.Workflow
