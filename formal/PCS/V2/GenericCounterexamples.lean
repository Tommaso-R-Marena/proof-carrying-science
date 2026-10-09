import PCS.V2.Witnesses.Instances

/-!
# Falsification attempts against the generic abstractions

Each attack is either **impossible** (the deterministic checker rejects it — proved by
evaluation) or appears as an **explicitly failed premise** (proved by exhibiting the
counter-model).  Concrete attacks reuse the biology witness (`MAVKL`, sites `2 3 5`,
threshold 3) whose honest graph `bioGraph` is accepted (`bioGraph_accepted`).

| attack | outcome |
|---|---|
| cyclic decomposition | rejected (`cyclic_rejected`; general: `ClaimGraph.cycle_rejected`) |
| missing leaf / unresolved child | rejected (`missing_leaf_rejected`; general: `missing_child_rejected`) |
| duplicate node ids | rejected (`duplicate_rejected`; general: `duplicate_ids_rejected`) |
| unsupported node | rejected (`unsupported_node_rejected`; general: `unsupported_rejected`) |
| wrong claim binding (graph for another root) | rejected (`wrong_root_rejected`) |
| swapped artifact in evidence | rejected (`swapped_artifact_rejected`) |
| stale / failed evidence | rejected (`failed_evidence_rejected`) |
| evidence not required by the claim | rejected (`unrequired_evidence_rejected`) |
| leaf proposition ≠ parent's expectation | rejected (`weaker_leaf_rejected`) |
| dishonest adaptive proposer | loop returns nothing (`adversary_gets_nothing`) |
| unsound decomposition rule | premise `CheckerSound.rule` fails (`rule_soundness_necessary`) |
| unsound leaf validator | premise `CheckerSound.leaf` fails (`leaf_soundness_necessary`) |
| checker PASS without semantics | `AdapterSound` is unprovable (`trusting_reports_unsound`) |
| semantics-dropping compilation | premise `compile_sound` fails (`lossy_compile_unsound`) |
| two domains registering the same tag | premise `Registered.nodup` necessary (`duplicate_tag_shadowing`) |
-/

set_option autoImplicit false

namespace PCS.V2.GenericCounterexamples

open PCS PCS.V2.Json PCS.V2.Replay PCS.V2.CertificateModel PCS.V2.ClaimGraph
open PCS.V2.DomainAdapter PCS.V2.Witnesses PCS.V2.Witnesses.Biology PCS.V2.Witnesses.Instances
open PCS.V2.Proposer

abbrev V := pcsCheckerIn bioAdapter bioEvidence bioCertClaim

/-- Cycle: `root → l1 → root`. -/
def cyclicGraph : Graph String BioIR :=
  ⟨[⟨"root", .sites bioClaim, .derive "bio.split" ["l1", "l2"]⟩,
    ⟨"l1", .inRange "seq" "sites", .derive "bio.split" ["root"]⟩,
    ⟨"l2", .score "seq" "sites" 3, .leaf "e2"⟩], "root"⟩

theorem cyclic_rejected : checkGraph V cyclicGraph (.sites bioClaim) = false := by decide

/-- The score leaf is referenced but absent. -/
def missingLeafGraph : Graph String BioIR :=
  ⟨[⟨"root", .sites bioClaim, .derive "bio.split" ["l1", "l2"]⟩,
    ⟨"l1", .inRange "seq" "sites", .leaf "e1"⟩], "root"⟩

theorem missing_leaf_rejected : checkGraph V missingLeafGraph (.sites bioClaim) = false := by
  decide

def duplicateGraph : Graph String BioIR :=
  ⟨bioGraph.nodes ++ [⟨"l2", .score "seq" "sites" 0, .leaf "e2"⟩], "root"⟩

theorem duplicate_rejected : checkGraph V duplicateGraph (.sites bioClaim) = false := by decide

def unsupportedGraph : Graph String BioIR :=
  ⟨[⟨"root", .sites bioClaim, .derive "bio.split" ["l1", "l2"]⟩,
    ⟨"l1", .inRange "seq" "sites", .leaf "e1"⟩,
    ⟨"l2", .score "seq" "sites" 3, .unsupported "llm-says-so"⟩], "root"⟩

theorem unsupported_node_rejected : checkGraph V unsupportedGraph (.sites bioClaim) = false := by
  decide

/-- The honest graph is not accepted for a *different* root claim (threshold 4). -/
theorem wrong_root_rejected : checkGraph V bioGraph (.sites ⟨"seq", "sites", 4⟩) = false := by
  decide

/-- Evidence `e1` checks a *different* artifact (`bad_sites`) than the leaf claims. -/
def swappedEvidence : List CertEvidence :=
  [⟨"e1", .computationalTest, .pass, .null, boundsEv "seq" "bad_sites"⟩,
   ⟨"e2", .computationalTest, .pass, .null, scoreEv "seq" "sites" 3⟩]

theorem swapped_artifact_rejected :
    checkGraph (pcsCheckerIn bioAdapter swappedEvidence bioCertClaim) bioGraph
      (.sites bioClaim) = false := by decide

/-- Evidence `e2` did not pass on replay. -/
def failedEvidence : List CertEvidence :=
  [⟨"e1", .computationalTest, .pass, .null, boundsEv "seq" "sites"⟩,
   ⟨"e2", .computationalTest, .fail, .null, scoreEv "seq" "sites" 3⟩]

theorem failed_evidence_rejected :
    checkGraph (pcsCheckerIn bioAdapter failedEvidence bioCertClaim) bioGraph
      (.sites bioClaim) = false := by decide

/-- The certificate claim does not require `e2` (evidence of some other claim). -/
def narrowClaim : CertClaim := ⟨"c1", .computational, .null, ["e1"], [], .computational⟩

theorem unrequired_evidence_rejected :
    checkGraph (pcsCheckerIn bioAdapter bioEvidence narrowClaim) bioGraph
      (.sites bioClaim) = false := by decide

/-- The score leaf is honestly discharged for threshold 2, but the parent's rule expects
    threshold 3. -/
def weakEvidence : List CertEvidence :=
  [⟨"e1", .computationalTest, .pass, .null, boundsEv "seq" "sites"⟩,
   ⟨"e2", .computationalTest, .pass, .null, scoreEv "seq" "sites" 2⟩]
def weakLeafGraph : Graph String BioIR :=
  ⟨[⟨"root", .sites bioClaim, .derive "bio.split" ["l1", "l2"]⟩,
    ⟨"l1", .inRange "seq" "sites", .leaf "e1"⟩,
    ⟨"l2", .score "seq" "sites" 2, .leaf "e2"⟩], "root"⟩

theorem weaker_leaf_accepted_alone :
    evalNode (pcsCheckerIn bioAdapter weakEvidence bioCertClaim) weakLeafGraph 1 [] "l2" = true := by
  decide

theorem weaker_leaf_rejected :
    checkGraph (pcsCheckerIn bioAdapter weakEvidence bioCertClaim) weakLeafGraph
      (.sites bioClaim) = false := by decide

/-- An adaptive adversary cycling through all the attacks above (choosing by the length of
    the feedback history) never gets a graph accepted for the honest root. -/
def adversary : Strategy (Graph String BioIR) := fun h =>
  match h.length with
  | 0 => cyclicGraph
  | 1 => missingLeafGraph
  | 2 => duplicateGraph
  | 3 => unsupportedGraph
  | _ => weakLeafGraph

theorem adversary_gets_nothing :
    runLoop (fun g => checkGraph V g (.sites bioClaim)) adversary 6 [] = none := by decide

/-! ## Necessity of the soundness premises -/

/-- A toy claim language: `Sem b := b = true`. -/
def toySem (b : Bool) : Prop := b = true

/-- A sound leaf validator with an **unsound** rule checker (accepts any derivation). -/
def unsoundRuleChecker : Checker Unit Bool := { leaf := fun _ c => c, rule := fun _ _ _ => true }

def emptyDerivation : Graph Unit Bool := ⟨[⟨"root", false, .derive "anything" []⟩], "root"⟩

/-- Leaf soundness alone does not suffice: the graph is accepted, the leaf validator is
    sound, and the root claim is false. -/
theorem rule_soundness_necessary :
    checkGraph unsoundRuleChecker emptyDerivation false = true ∧
      (∀ ob c, unsoundRuleChecker.leaf ob c = true → toySem c) ∧ ¬ toySem false :=
  ⟨by decide, fun _ c h => h, by simp [toySem]⟩

/-- A sound rule checker (accepts nothing) with an **unsound** leaf validator. -/
def unsoundLeafChecker : Checker Unit Bool := { leaf := fun _ _ => true, rule := fun _ _ _ => false }

def lyingLeaf : Graph Unit Bool := ⟨[⟨"root", false, .leaf ()⟩], "root"⟩

theorem leaf_soundness_necessary :
    checkGraph unsoundLeafChecker lyingLeaf false = true ∧
      (∀ r p cs, unsoundLeafChecker.rule r p cs = true → (∀ c ∈ cs, toySem c) → toySem p) ∧
      ¬ toySem false :=
  ⟨by decide, fun _ _ _ h _ => (by cases h), by simp [toySem]⟩

/-- **A checker that "returns success without proving its semantics" cannot be used.**  If
    replay PASS is given no meaning (`Valid := True`, i.e. trusting reports), the biology
    adapter's contract is false: a PASS-labelled bounds request over an empty artifact
    table would have to denote an in-range claim about non-existent artifacts. -/
theorem trusting_reports_unsound : ¬ AdapterSound bioAdapter (fun _ => True) := by
  intro h
  have := h.leaf_sound (req (boundsEv "seq" "sites") []) (.inRange "seq" "sites") (by decide) trivial
  obtain ⟨sq, st, h1, _, _⟩ := this
  simp [bioAdapter, artBytes, PCS.V2.Index.lookup, req] at h1

/-- A lossy compilation that drops the score obligation. -/
def lossyCompile (c : BioClaim) : Option BioIR := some (.inRange c.seqA c.sitesA)

/-- `compile_sound` fails for it: in the witness world the compiled IR holds but the domain
    claim with threshold 4 is false.  So `compile_sound` is a genuine obligation. -/
theorem lossy_compile_unsound :
    ¬ ∀ w c ir, lossyCompile c = some ir → bioSem w ir → bioDomain.Holds w c := by
  intro h
  have hsem : bioSem bioTable (.inRange "seq" "sites") :=
    boundsTest_sound ("seq", "sites") bioTable (by decide)
  obtain ⟨sq, st, h1, h2, _, hk⟩ := h bioTable ⟨"seq", "sites", 4⟩ _ rfl hsem
  have e1 : sq = seqBytes.data.toList := by
    simpa [artBytes, PCS.V2.Index.lookup, bioTable] using h1.symm
  have e2 : st = sitesBytes.data.toList := by
    simpa [artBytes, PCS.V2.Index.lookup, bioTable] using h2.symm
  subst e1 e2
  revert hk; decide

/-! ## Registration: duplicate tags shadow -/

open PCS.V2.DomainAuthority PCS.V2.PKPDCheck

/-- A checker that always passes, meaning `True`. -/
def passAll : DomainChecker :=
  { tag := "dup", run := fun _ => ⟨.computationalTest, .pass⟩, Holds := fun _ => True,
    sound := fun _ _ _ => trivial }

/-- A checker that never passes, meaning `False` (vacuously sound). -/
def passNone : DomainChecker :=
  { tag := "dup", run := fun _ => ⟨.computationalTest, .fail⟩, Holds := fun _ => False,
    sound := fun _ _ h => by cases h }

def dupReq : ReplayRequest := req (.obj [("check_spec", .obj [("type", .str "dup")])]) []

/-- With two registrations of tag `"dup"`, the authority's PASS-meaning is the *first*
    checker's: the second checker's proposition need not hold.  Hence the conclusion of
    `registry_valid` fails without `Registered.nodup`. -/
theorem duplicate_tag_shadowing :
    AuthorityValid (registry [passAll, passNone]) (fun _ => False) dupReq ∧
      isCheckType passNone.tag dupReq.evidence = true ∧ ¬ passNone.Holds dupReq := by
  refine ⟨?_, by decide, fun h => h⟩
  unfold AuthorityValid PCS.V2.Checkers.DispatchHolds
  have hb : PCS.V2.Checkers.builtinCheckers.find? (·.handles dupReq) = none := by decide
  rw [List.find?_append, hb]
  show (match ([passAll, passNone].map DomainChecker.toCertified).find? (·.handles dupReq) with
    | some c => c.Holds dupReq | none => False)
  have hh : passAll.toCertified.handles dupReq = true := by decide
  simp only [List.map_cons, List.find?_cons, hh]
  trivial

end PCS.V2.GenericCounterexamples
