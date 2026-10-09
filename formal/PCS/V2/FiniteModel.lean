import PCS.V2.SemanticEquiv

/-!
# Certified finite countermodels (Semantic Intelligence v2)

When a proposed formalization is wrong, PCS should not merely say "rejected": it should,
whenever possible, exhibit a **concrete, mechanically checked finite structure** in which
the selected interpretation and the candidate have different truth values.

This file provides:

* `FinModel` — explicit finite many-sorted structures (sort carriers, function tables,
  predicate tables) and their reading `FinModel.toModel` as an ordinary `Model` of the
  independent semantics.
* `NFormula.evalF`, `NClaim.evalF` — a decidable evaluator, proved to coincide with the
  independent denotation on every finite model (`finite_evaluator_sound`,
  `finite_evaluator_complete_for_supported_finite_models`).
* `FinModel.conformsB` — a decidable check that a finite model respects the registry's
  function signatures, proved to imply `Model.Conforms` (`conformsB_sound`).
* `Countermodel`, `checkCountermodel` — a compact witness format and its checker;
  `countermodel_witness_sound` and `countermodel_demonstrates_semantic_difference` prove
  that a checked witness is a genuine, registry-conforming structure distinguishing the two
  claims; `countermodel_excludes_certificate` shows no equivalence certificate can then
  exist.  The checker also requires every approved sort to be inhabited
  (`countermodel_witness_inhabited`, `countermodel_refutes_inhabited_equivalence`), so a
  countermodel never rests on an empty domain.  (This requirement was added after the
  independent Python oracle flagged that a bundle with an empty, unused sort carrier was
  accepted; such a bundle was sound for the stated semantics but weaker evidence.)
* `searchCountermodel` — an exhaustive bounded search over an explicitly enumerated class
  of finite structures (carrier sizes `1..k` per sort, all predicate and function tables),
  ordered by total domain size.  `search_found_sound`, `search_found_minimal` and
  `search_exhausted_complete` state exactly what a search result means.
* `no_countermodel_found_within_bound_is_not_equivalence_proof` — a kernel-checked example
  in which the bounded search is exhausted without finding a countermodel although the two
  claims are **not** equivalent.  Bounded search is never an equivalence proof.
-/

set_option autoImplicit false

namespace PCS.V2.Semantic

/-! ## Finite structures -/

/-- An explicit finite many-sorted structure over the carrier `Nat`. -/
structure FinModel where
  /-- carrier of each sort -/
  sorts : List (SortId × List Nat)
  /-- function tables (missing entries default to `0`) -/
  fns : List (String × List (List Nat × Nat))
  /-- predicate tables: the tuples on which the predicate holds -/
  preds : List (String × List (List Nat))
  deriving Repr, DecidableEq, Inhabited

def FinModel.carrier (F : FinModel) (s : SortId) : List Nat :=
  match F.sorts.find? (fun e => e.1 == s) with
  | some e => e.2
  | none => []

def FinModel.fnVal (F : FinModel) (f : String) (ds : List Nat) : Nat :=
  match F.fns.find? (fun e => e.1 == f) with
  | some e =>
    match e.2.find? (fun r => r.1 == ds) with
    | some r => r.2
    | none => 0
  | none => 0

def FinModel.predVal (F : FinModel) (p : String) (ds : List Nat) : Bool :=
  match F.preds.find? (fun e => e.1 == p) with
  | some e => e.2.contains ds
  | none => false

/-- Total domain size (sum of the carrier lengths). -/
def FinModel.domainSize (F : FinModel) : Nat := (F.sorts.map (fun e => e.2.length)).sum

/-- The finite structure read as a model of the independent semantics. -/
def FinModel.toModel (F : FinModel) : Model where
  Dom := Nat
  HasSort s d := d ∈ F.carrier s
  fn := F.fnVal
  pred p ds := F.predVal p ds = true

/-! ## The evaluator -/

mutual
def NTerm.evalF (F : FinModel) (ρ : String → Nat) (env : Nat → Nat) : NTerm → Nat
  | .bvar i => env i
  | .fvar x => ρ x
  | .app f args => F.fnVal f (NTerm.evalFList F ρ env args)
def NTerm.evalFList (F : FinModel) (ρ : String → Nat) (env : Nat → Nat) : List NTerm → List Nat
  | [] => []
  | t :: ts => NTerm.evalF F ρ env t :: NTerm.evalFList F ρ env ts
end

/-- Decidable evaluation of nameless formulas in a finite structure. -/
def NFormula.evalF (F : FinModel) (ρ : String → Nat) : (Nat → Nat) → NFormula → Bool
  | _, .tt => true
  | _, .ff => false
  | env, .pred p args => F.predVal p (NTerm.evalFList F ρ env args)
  | env, .eq a b => NTerm.evalF F ρ env a == NTerm.evalF F ρ env b
  | env, .not φ => !(NFormula.evalF F ρ env φ)
  | env, .and φ ψ => NFormula.evalF F ρ env φ && NFormula.evalF F ρ env ψ
  | env, .or φ ψ => NFormula.evalF F ρ env φ || NFormula.evalF F ρ env ψ
  | env, .imp φ ψ => !(NFormula.evalF F ρ env φ) || NFormula.evalF F ρ env ψ
  | env, .quant .all s φ => (F.carrier s).all (fun d => NFormula.evalF F ρ (consEnv d env) φ)
  | env, .quant .ex s φ => (F.carrier s).any (fun d => NFormula.evalF F ρ (consEnv d env) φ)
  | _, .unsupported _ => false

mutual
theorem NTerm.evalF_eq (F : FinModel) (ρ : String → Nat) (env : Nat → Nat) :
    ∀ t : NTerm, NTerm.evalF F ρ env t = NTerm.denote F.toModel ρ env t
  | .bvar _ => rfl
  | .fvar _ => rfl
  | .app f args => by
    simp only [NTerm.evalF, NTerm.denote]
    rw [NTerm.evalFList_eq F ρ env args]; rfl
theorem NTerm.evalFList_eq (F : FinModel) (ρ : String → Nat) (env : Nat → Nat) :
    ∀ ts : List NTerm, NTerm.evalFList F ρ env ts = NTerm.denoteList F.toModel ρ env ts
  | [] => rfl
  | t :: ts => by
    simp only [NTerm.evalFList, NTerm.denoteList]
    rw [NTerm.evalF_eq F ρ env t, NTerm.evalFList_eq F ρ env ts]
end

/-- **The finite evaluator decides the independent denotation exactly.** -/
theorem NFormula.evalF_iff (F : FinModel) (ρ : String → Nat) :
    ∀ (φ : NFormula) (env : Nat → Nat),
    NFormula.evalF F ρ env φ = true ↔ NFormula.denote F.toModel ρ env φ
  | .tt, _ => by simp [NFormula.evalF, NFormula.denote]
  | .ff, _ => by simp [NFormula.evalF, NFormula.denote]
  | .pred p args, env => by
    simp only [NFormula.evalF, NFormula.denote, NTerm.evalFList_eq]; try rfl
  | .eq a b, env => by
    simp only [NFormula.evalF, NFormula.denote, NTerm.evalF_eq, beq_iff_eq]; try rfl
  | .not φ, env => by
    simp only [NFormula.evalF, NFormula.denote, Bool.not_eq_true']
    rw [← NFormula.evalF_iff F ρ φ env]; simp
  | .and φ ψ, env => by
    simp only [NFormula.evalF, NFormula.denote, Bool.and_eq_true]
    rw [NFormula.evalF_iff F ρ φ env, NFormula.evalF_iff F ρ ψ env]
  | .or φ ψ, env => by
    simp only [NFormula.evalF, NFormula.denote, Bool.or_eq_true]
    rw [NFormula.evalF_iff F ρ φ env, NFormula.evalF_iff F ρ ψ env]
  | .imp φ ψ, env => by
    simp only [NFormula.evalF, NFormula.denote, Bool.or_eq_true, Bool.not_eq_true']
    rw [← NFormula.evalF_iff F ρ φ env, ← NFormula.evalF_iff F ρ ψ env]
    cases NFormula.evalF F ρ env φ <;> simp
  | .quant .all s φ, env => by
    simp only [NFormula.evalF, NFormula.denote, List.all_eq_true]
    exact forall_congr' (fun d => imp_congr Iff.rfl (NFormula.evalF_iff F ρ φ _))
  | .quant .ex s φ, env => by
    simp only [NFormula.evalF, NFormula.denote, List.any_eq_true]
    exact exists_congr (fun d => and_congr Iff.rfl (NFormula.evalF_iff F ρ φ _))
  | .unsupported _, _ => by simp [NFormula.evalF, NFormula.denote]

/-- Evaluation of the nameless universal closure. -/
def evalParams (F : FinModel) : List SortId → (Nat → Nat) → ((Nat → Nat) → Bool) → Bool
  | [], env, k => k env
  | s :: ss, env, k => (F.carrier s).all (fun d => evalParams F ss (consEnv d env) k)

/-- Decidable evaluation of a nameless claim in a finite structure. -/
def NClaim.evalF (F : FinModel) (ρ : String → Nat) (env : Nat → Nat) (n : NClaim) : Bool :=
  evalParams F n.paramSorts env (fun e =>
    !(n.assumptions.all (NFormula.evalF F ρ e)) || NFormula.evalF F ρ e n.conclusion)

theorem evalParams_iff (F : FinModel) (ρ : String → Nat) :
    ∀ (ss : List SortId) (env : Nat → Nat) (k : (Nat → Nat) → Bool) (K : (Nat → Nat) → Prop),
    (∀ e, k e = true ↔ K e) →
    (evalParams F ss env k = true ↔ ndenoteParams F.toModel ρ ss env K)
  | [], env, k, K, h => h env
  | s :: ss, env, k, K, h => by
    simp only [evalParams, ndenoteParams, List.all_eq_true]
    exact forall_congr' (fun d => imp_congr Iff.rfl (evalParams_iff F ρ ss _ k K h))

/-- **The finite claim evaluator decides the independent claim denotation exactly.** -/
theorem NClaim.evalF_iff (F : FinModel) (ρ : String → Nat) (env : Nat → Nat) (n : NClaim) :
    n.evalF F ρ env = true ↔ n.denote F.toModel ρ env := by
  unfold NClaim.evalF NClaim.denote
  apply evalParams_iff
  intro e
  simp only [Bool.or_eq_true, Bool.not_eq_true']
  constructor
  · intro h hA
    rcases h with h | h
    · have : (n.assumptions.all (NFormula.evalF F ρ e)) = true :=
        List.all_eq_true.mpr (fun a ha => (NFormula.evalF_iff F ρ a e).mpr (hA a ha))
      rw [this] at h; cases h
    · exact (NFormula.evalF_iff F ρ _ e).mp h
  · intro h
    cases hc : NFormula.evalF F ρ e n.conclusion
    · left
      cases ha : n.assumptions.all (NFormula.evalF F ρ e)
      · rfl
      · exfalso
        have hA : ∀ a ∈ n.assumptions, NFormula.denote F.toModel ρ e a := fun a hm =>
          (NFormula.evalF_iff F ρ a e).mp (List.all_eq_true.mp ha a hm)
        have := (NFormula.evalF_iff F ρ _ e).mpr (h hA)
        rw [hc] at this; cases this
    · right; rfl

/-- `finite_evaluator_sound`: a `true` evaluation is a proof of the denotation. -/
theorem finite_evaluator_sound {F : FinModel} {ρ : String → Nat} {env : Nat → Nat} {n : NClaim}
    (h : n.evalF F ρ env = true) : n.denote F.toModel ρ env :=
  (NClaim.evalF_iff F ρ env n).mp h

/-- `finite_evaluator_complete_for_supported_finite_models`: on every finite structure the
    evaluator returns `true` exactly when the claim holds and `false` exactly when it fails. -/
theorem finite_evaluator_complete_for_supported_finite_models (F : FinModel)
    (ρ : String → Nat) (env : Nat → Nat) (n : NClaim) :
    (n.denote F.toModel ρ env → n.evalF F ρ env = true) ∧
    (¬ n.denote F.toModel ρ env → n.evalF F ρ env = false) := by
  refine ⟨(NClaim.evalF_iff F ρ env n).mpr, fun h => ?_⟩
  cases he : n.evalF F ρ env
  · rfl
  · exact absurd ((NClaim.evalF_iff F ρ env n).mp he) h

/-! ## Registry conformance of finite structures -/

/-- All argument tuples drawn from the carriers of a sort list. -/
def FinModel.tuples (F : FinModel) : List SortId → List (List Nat)
  | [] => [[]]
  | s :: ss => (F.carrier s).flatMap (fun d => (F.tuples ss).map (d :: ·))

theorem FinModel.mem_tuples (F : FinModel) :
    ∀ {ss : List SortId} {ds : List Nat}, SortsHold F.toModel ss ds → ds ∈ F.tuples ss
  | [], [], .nil => by simp [FinModel.tuples]
  | s :: ss, d :: ds, .cons hd hs => by
    simp only [FinModel.tuples, List.mem_flatMap, List.mem_map]
    exact ⟨d, hd, ds, F.mem_tuples hs, rfl⟩

/-- Decidable check that a finite structure respects every registered function signature. -/
def FinModel.conformsB (R : Registry) (F : FinModel) : Bool :=
  R.symbols.all (fun e =>
    match e.kind with
    | .fn ss r => (F.tuples ss).all (fun ds => (F.carrier r).contains (F.fnVal e.id ds))
    | .pred _ => true)

theorem Registry.resolve_mem {R : Registry} {f : String} {e : SymbolEntry}
    (h : R.resolve f = some e) : e ∈ R.symbols ∧ e.id = f := by
  unfold Registry.resolve at h
  split at h
  · rename_i e' he
    cases h
    have hm : e ∈ R.entries f := by rw [he]; exact List.mem_singleton_self e
    unfold Registry.entries at hm
    rw [List.mem_filter] at hm
    exact ⟨hm.1, by simpa using hm.2⟩
  · cases h

/-- **Conformance soundness**: a structure passing `conformsB` is a model of the registry's
    function signatures in the sense of the independent semantics. -/
theorem conformsB_sound {R : Registry} {F : FinModel} (h : F.conformsB R = true) :
    F.toModel.Conforms R := by
  intro f e ss r hres hk ds hds
  obtain ⟨hmem, hid⟩ := Registry.resolve_mem hres
  have he := List.all_eq_true.mp h e hmem
  rw [hk] at he
  simp only at he
  have := List.all_eq_true.mp he ds (F.mem_tuples hds)
  rw [hid] at this
  exact List.contains_iff_mem.mp this

/-! ## Countermodel witnesses -/

/-- The fixed valuation used by witnesses (claims checked by PCS are closed, so it is
    irrelevant there; it is fixed so that a witness is a complete, replayable object). -/
def ρ0 : String → Nat := fun _ => 0
/-- The fixed nameless environment used by witnesses. -/
def env0 : Nat → Nat := fun _ => 0

/-- A countermodel witness: a finite structure and the claimed truth values of the selected
    interpretation and of the candidate in it. -/
structure Countermodel where
  model : FinModel
  interpretationHolds : Bool
  candidateHolds : Bool
  deriving Repr, DecidableEq, Inhabited

/-- Every approved sort has a non-empty carrier (so a countermodel never relies on an empty
    domain, which no registered Lean type of the intended application need have). -/
def FinModel.inhabitedB (R : Registry) (F : FinModel) : Bool :=
  R.sorts.all (fun s => !(F.carrier s.id).isEmpty)

theorem inhabitedB_sound {R : Registry} {F : FinModel} (h : F.inhabitedB R = true) :
    ∀ s ∈ R.sorts, ∃ d, F.toModel.HasSort s.id d := by
  intro s hs
  have := List.all_eq_true.mp h s hs
  cases hc : F.carrier s.id with
  | nil => rw [hc] at this; simp at this
  | cons d _ => exact ⟨d, by show d ∈ F.carrier s.id; rw [hc]; exact List.mem_cons_self⟩

/-- **The countermodel checker**: every approved sort is inhabited, the structure conforms to
    the registry, the recorded truth values are the evaluator's, and they differ. -/
def checkCountermodel (R : Registry) (I C : SemanticClaim) (w : Countermodel) : Bool :=
  w.model.inhabitedB R && w.model.conformsB R &&
    (I.normalize.evalF w.model ρ0 env0 == w.interpretationHolds) &&
    (C.normalize.evalF w.model ρ0 env0 == w.candidateHolds) &&
    (w.interpretationHolds != w.candidateHolds)

theorem claim_evalF_iff (F : FinModel) (c : SemanticClaim) :
    c.normalize.evalF F ρ0 env0 = true ↔ c.denote F.toModel ρ0 := by
  rw [NClaim.evalF_iff, ← SemanticClaim.normalize_denote]

/-- **Countermodel witness soundness.**  A checked witness is a registry-conforming
    structure (with a trivially well-typed valuation for closed claims) in which the
    selected interpretation and the candidate have exactly the recorded, different truth
    values. -/
theorem countermodel_witness_sound {R : Registry} {I C : SemanticClaim} {w : Countermodel}
    (h : checkCountermodel R I C w = true) :
    w.model.toModel.Conforms R ∧
    (I.denote w.model.toModel ρ0 ↔ w.interpretationHolds = true) ∧
    (C.denote w.model.toModel ρ0 ↔ w.candidateHolds = true) ∧
    ¬ (I.denote w.model.toModel ρ0 ↔ C.denote w.model.toModel ρ0) := by
  unfold checkCountermodel at h
  simp only [Bool.and_eq_true, beq_iff_eq, bne_iff_ne, ne_eq] at h
  obtain ⟨⟨⟨⟨_, hc⟩, hi⟩, hcand⟩, hne⟩ := h
  have hI : I.denote w.model.toModel ρ0 ↔ w.interpretationHolds = true := by
    rw [← claim_evalF_iff, hi]
  have hC : C.denote w.model.toModel ρ0 ↔ w.candidateHolds = true := by
    rw [← claim_evalF_iff, hcand]
  refine ⟨conformsB_sound hc, hI, hC, fun hiff => hne ?_⟩
  cases hx : w.interpretationHolds <;> cases hy : w.candidateHolds
  · rfl
  · exact absurd (hI.mp (hiff.mpr (hC.mpr hy))) (by rw [hx]; simp)
  · exact absurd (hC.mp (hiff.mp (hI.mpr hx))) (by rw [hy]; simp)
  · rfl

/-- **A checked countermodel demonstrates a semantic difference**: the two claims are not
    equivalent in all models — not even in all registry-conforming models. -/
theorem countermodel_demonstrates_semantic_difference {R : Registry} {I C : SemanticClaim}
    {w : Countermodel} (h : checkCountermodel R I C w = true) :
    ¬ (∀ (M : Model) (ρ : String → M.Dom), M.Conforms R → (I.denote M ρ ↔ C.denote M ρ)) :=
  fun hall => (countermodel_witness_sound h).2.2.2
    (hall _ ρ0 (countermodel_witness_sound h).1)

/-- A checked countermodel inhabits every approved sort. -/
theorem countermodel_witness_inhabited {R : Registry} {I C : SemanticClaim} {w : Countermodel}
    (h : checkCountermodel R I C w = true) :
    ∀ s ∈ R.sorts, ∃ d, w.model.toModel.HasSort s.id d := by
  unfold checkCountermodel at h
  simp only [Bool.and_eq_true] at h
  exact inhabitedB_sound h.1.1.1.1

/-- **Stronger refutation**: the claims already differ within the restricted class of
    registry-conforming models in which **every approved sort is inhabited** — so the
    disagreement never rests on an empty domain. -/
theorem countermodel_refutes_inhabited_equivalence {R : Registry} {I C : SemanticClaim}
    {w : Countermodel} (h : checkCountermodel R I C w = true) :
    ¬ (∀ (M : Model) (ρ : String → M.Dom), M.Conforms R →
        (∀ s ∈ R.sorts, ∃ d, M.HasSort s.id d) → (I.denote M ρ ↔ C.denote M ρ)) :=
  fun hall => (countermodel_witness_sound h).2.2.2
    (hall _ ρ0 (countermodel_witness_sound h).1 (countermodel_witness_inhabited h))

/-- A checked countermodel excludes every equivalence certificate. -/
theorem countermodel_excludes_certificate {R : Registry} {I C : SemanticClaim}
    {w : Countermodel} (h : checkCountermodel R I C w = true) (cert : EquivCert) :
    checkCert cert I.normalize C.normalize = false :=
  inequivalent_claims_admit_no_certificate (countermodel_witness_sound h).2.2.2 cert

/-! ## Bounded exhaustive search -/

/-- All lists `[x₁, …, xₙ]` with `xᵢ ∈ lᵢ`. -/
def cartesian {α : Type} : List (List α) → List (List α)
  | [] => [[]]
  | l :: ls => l.flatMap (fun x => (cartesian ls).map (x :: ·))

/-- All sublists (as subsets) of a list. -/
def subsetsOf {α : Type} : List α → List (List α)
  | [] => [[]]
  | x :: xs => (subsetsOf xs).flatMap (fun s => [s, x :: s])

/-- Sort carriers for a size vector: disjoint consecutive blocks. -/
def mkCarriers : List SortId → List Nat → Nat → List (SortId × List Nat)
  | s :: ss, n :: ns, off => (s, List.range' off n) :: mkCarriers ss ns (off + n)
  | _, _, _ => []

theorem mkCarriers_size : ∀ (ss : List SortId) (ns : List Nat) (off : Nat),
    ss.length = ns.length → ((mkCarriers ss ns off).map (fun e => e.2.length)).sum = ns.sum
  | [], [], _, _ => rfl
  | s :: ss, n :: ns, off, h => by
    simp only [mkCarriers, List.map_cons, List.sum_cons, List.length_range']
    rw [mkCarriers_size ss ns (off + n) (by simpa using h)]
  | [], _ :: _, _, h => by cases h
  | _ :: _, [], _, h => by cases h

/-- The searched class: the signature to vary. -/
structure SearchSig where
  sorts : List SortId
  /-- (predicate id, argument sorts) of the predicates to vary -/
  preds : List (String × List SortId)
  /-- (function id, argument sorts, result sort) of the functions to vary -/
  fns : List (String × List SortId × SortId)
  /-- (function id, argument sorts, result sort) of the remaining registered functions
      (interpreted as constant functions onto the first element of their result carrier) -/
  fixedFns : List (String × List SortId × SortId)
  deriving Repr, Inhabited

def dedupStr : List String → List String
  | [] => []
  | x :: xs => if xs.contains x then dedupStr xs else x :: dedupStr xs

/-- The search signature induced by a registry and the two claims: every registered sort,
    the registered predicates and functions occurring in either claim are varied; other
    registered functions are fixed. -/
def searchSig (R : Registry) (I C : SemanticClaim) : SearchSig :=
  let used := dedupStr (I.symbols ++ C.symbols)
  { sorts := R.sorts.map (·.id),
    preds := R.symbols.filterMap (fun e => match e.kind with
      | .pred ss => if used.contains e.id then some (e.id, ss) else none
      | .fn _ _ => none),
    fns := R.symbols.filterMap (fun e => match e.kind with
      | .fn ss r => if used.contains e.id then some (e.id, ss, r) else none
      | .pred _ => none),
    fixedFns := R.symbols.filterMap (fun e => match e.kind with
      | .fn ss r => if used.contains e.id then none else some (e.id, ss, r)
      | .pred _ => none) }

/-- Carrier-size vectors of length `m`, entries in `1..k`, summing to `t`. -/
def vecsSum (k : Nat) : Nat → Nat → List (List Nat)
  | 0, t => if t = 0 then [[]] else []
  | m + 1, t => (List.range' 1 k).flatMap (fun x =>
      if x ≤ t then (vecsSum k m (t - x)).map (x :: ·) else [])

theorem mem_vecsSum (k : Nat) : ∀ (m t : Nat) (v : List Nat), v ∈ vecsSum k m t →
    v.sum = t ∧ v.length = m
  | 0, t, v, h => by
    simp only [vecsSum] at h
    split at h
    · simp at h; subst h; simp_all
    · simp at h
  | m + 1, t, v, h => by
    simp only [vecsSum, List.mem_flatMap] at h
    obtain ⟨x, _, hx⟩ := h
    split at hx
    · obtain ⟨w, hw, rfl⟩ := List.mem_map.mp hx
      obtain ⟨h1, h2⟩ := mem_vecsSum k m (t - x) w hw
      simp only [List.sum_cons, List.length_cons]
      constructor <;> omega
    · simp at hx

/-- Size vectors (entries `1..k`) in ascending order of total size, so the first countermodel
    found is minimal.  Defined by structural recursion so that it also reduces in the kernel. -/
def orderedSizeVectors (k m : Nat) : List (List Nat) :=
  (List.range (m * k + 1)).flatMap (fun t => vecsSum k m t)

/-- All finite structures of the class with a given size vector. -/
def modelsFor (sig : SearchSig) (sizes : List Nat) : List FinModel :=
  let carriers := mkCarriers sig.sorts sizes 0
  let F0 : FinModel := ⟨carriers, [], []⟩
  let car (s : SortId) : List Nat := F0.carrier s
  let predChoices : List (List (String × List (List Nat))) :=
    sig.preds.map (fun (p, ss) => (subsetsOf (F0.tuples ss)).map (fun t => (p, t)))
  let fnChoices : List (List (String × List (List Nat × Nat))) :=
    sig.fns.map (fun (f, ss, r) =>
      let ts := F0.tuples ss
      (cartesian (ts.map (fun _ => car r))).map (fun vs => (f, ts.zip vs)))
  let fixed : List (String × List (List Nat × Nat)) :=
    sig.fixedFns.map (fun (f, ss, r) =>
      (f, (F0.tuples ss).map (fun ds => (ds, (car r).headD 0))))
  (cartesian predChoices).flatMap (fun ps =>
    (cartesian fnChoices).map (fun fs => ⟨carriers, fs ++ fixed, ps⟩))

/-- Number of structures `modelsFor` would generate (computed without generating them). -/
def modelsForCount (sig : SearchSig) (sizes : List Nat) : Nat :=
  let F0 : FinModel := ⟨mkCarriers sig.sorts sizes 0, [], []⟩
  (sig.preds.map (fun (_, ss) => 2 ^ (F0.tuples ss).length)).foldl (· * ·) 1 *
  (sig.fns.map (fun (_, ss, r) => (F0.carrier r).length ^ (F0.tuples ss).length)).foldl (· * ·) 1

/-- Outcome of the bounded search. -/
inductive SearchOutcome where
  /-- a verified countermodel -/
  | found (F : FinModel)
  /-- the whole enumerated class was searched; no countermodel in it -/
  | exhausted
  /-- the model budget was exceeded before the class was exhausted -/
  | budgetExceeded
  deriving Repr, DecidableEq, Inhabited

/-- The search loop over blocks (fails closed: an over-budget block stops the search). -/
def searchLoop (p : FinModel → Bool) (gen : List Nat → List FinModel) (cost : List Nat → Nat) :
    List (List Nat) → Nat → SearchOutcome
  | [], _ => .exhausted
  | v :: vs, budget =>
    if budget < cost v then .budgetExceeded
    else match (gen v).find? p with
      | some F => .found F
      | none => searchLoop p gen cost vs (budget - cost v)

/-- Is `F` a countermodel (conforming, different truth values)? -/
def isCountermodel (R : Registry) (I C : SemanticClaim) (F : FinModel) : Bool :=
  F.inhabitedB R && F.conformsB R && (I.normalize.evalF F ρ0 env0 != C.normalize.evalF F ρ0 env0)

/-- The explicitly enumerated class of finite structures searched with bound `k`. -/
def searchClass (R : Registry) (I C : SemanticClaim) (k : Nat) : List FinModel :=
  let sig := searchSig R I C
  (orderedSizeVectors k sig.sorts.length).flatMap (modelsFor sig)

/-- **Bounded countermodel search** with carrier sizes `1..k` and a structure budget. -/
def searchCountermodel (R : Registry) (I C : SemanticClaim) (k budget : Nat) : SearchOutcome :=
  let sig := searchSig R I C
  searchLoop (isCountermodel R I C) (modelsFor sig) (modelsForCount sig)
    (orderedSizeVectors k sig.sorts.length) budget

/-- Package a found structure as a witness. -/
def mkWitness (I C : SemanticClaim) (F : FinModel) : Countermodel :=
  ⟨F, I.normalize.evalF F ρ0 env0, C.normalize.evalF F ρ0 env0⟩

theorem searchLoop_found {p : FinModel → Bool} {gen : List Nat → List FinModel}
    {cost : List Nat → Nat} : ∀ {vs : List (List Nat)} {budget : Nat} {F : FinModel},
    searchLoop p gen cost vs budget = .found F →
    p F = true ∧ ∃ v ∈ vs, F ∈ gen v ∧
      ∀ G ∈ vs.flatMap gen, p G = true → (vs.Pairwise (fun a b => a.sum ≤ b.sum)) →
        ∃ w ∈ vs, G ∈ gen w ∧ v.sum ≤ w.sum
  | [], _, _, h => by cases h
  | v :: vs, budget, F, h => by
    unfold searchLoop at h
    split at h
    · cases h
    · split at h
      · rename_i F' hF
        cases h
        refine ⟨List.find?_some hF, v, List.mem_cons_self, List.mem_of_find?_eq_some hF, ?_⟩
        intro G hG _ hpw
        rw [List.flatMap_cons, List.mem_append] at hG
        rcases hG with hG | hG
        · exact ⟨v, List.mem_cons_self, hG, Nat.le_refl _⟩
        · obtain ⟨w, hw, hGw⟩ := List.mem_flatMap.mp hG
          exact ⟨w, List.mem_cons_of_mem _ hw, hGw, (List.pairwise_cons.mp hpw).1 w hw⟩
      · rename_i hnone
        obtain ⟨hp, v', hv', hF, hmin⟩ := searchLoop_found h
        refine ⟨hp, v', List.mem_cons_of_mem _ hv', hF, ?_⟩
        intro G hG hpG hpw
        rw [List.flatMap_cons, List.mem_append] at hG
        rcases hG with hG | hG
        · exact absurd hpG (List.find?_eq_none.mp hnone G hG)
        · obtain ⟨w, hw, hGw, hle⟩ := hmin G hG hpG (List.pairwise_cons.mp hpw).2
          exact ⟨w, List.mem_cons_of_mem _ hw, hGw, hle⟩

theorem searchLoop_exhausted {p : FinModel → Bool} {gen : List Nat → List FinModel}
    {cost : List Nat → Nat} : ∀ {vs : List (List Nat)} {budget : Nat},
    searchLoop p gen cost vs budget = .exhausted → ∀ G ∈ vs.flatMap gen, p G = false
  | [], _, _, G, hG => by simp at hG
  | v :: vs, budget, h, G, hG => by
    unfold searchLoop at h
    split at h
    · cases h
    · split at h
      · cases h
      · rename_i hnone
        rw [List.flatMap_cons, List.mem_append] at hG
        rcases hG with hG | hG
        · have := List.find?_eq_none.mp hnone G hG
          cases hpG : p G
          · rfl
          · exact absurd hpG this
        · exact searchLoop_exhausted h G hG

theorem orderedSizeVectors_pairwise (k m : Nat) :
    (orderedSizeVectors k m).Pairwise (fun a b => a.sum ≤ b.sum) := by
  unfold orderedSizeVectors
  rw [List.pairwise_flatMap]
  constructor
  · intro t _
    rw [List.pairwise_iff_forall_sublist]
    intro a b hab
    have ha := (mem_vecsSum k m t a (hab.subset (by simp))).1
    have hb := (mem_vecsSum k m t b (hab.subset (by simp))).1
    omega
  · refine List.pairwise_lt_range.imp ?_
    intro t₁ t₂ hlt x hx y hy
    rw [(mem_vecsSum k m t₁ x hx).1, (mem_vecsSum k m t₂ y hy).1]
    omega

theorem modelsFor_domainSize (sig : SearchSig) (sizes : List Nat)
    (hlen : sig.sorts.length = sizes.length) :
    ∀ F ∈ modelsFor sig sizes, F.domainSize = sizes.sum := by
  intro F hF
  simp only [modelsFor, List.mem_flatMap, List.mem_map] at hF
  obtain ⟨_, _, _, _, rfl⟩ := hF
  exact mkCarriers_size _ _ _ hlen

theorem orderedSizeVectors_length {k m : Nat} {v : List Nat} (h : v ∈ orderedSizeVectors k m) :
    v.length = m := by
  obtain ⟨t, _, hv⟩ := List.mem_flatMap.mp h
  exact (mem_vecsSum k m t v hv).2

theorem mem_vecsSum_pos (k : Nat) : ∀ (m t : Nat) (v : List Nat), v ∈ vecsSum k m t →
    ∀ x ∈ v, 1 ≤ x
  | 0, t, v, h => by
    simp only [vecsSum] at h
    split at h
    · simp at h; subst h; simp
    · simp at h
  | m + 1, t, v, h => by
    simp only [vecsSum, List.mem_flatMap] at h
    obtain ⟨x, hxm, hx⟩ := h
    split at hx
    · obtain ⟨w, hw, rfl⟩ := List.mem_map.mp hx
      intro y hy
      rcases List.mem_cons.mp hy with rfl | hy
      · simp [List.mem_range'] at hxm; omega
      · exact mem_vecsSum_pos k m (t - x) w hw y hy
    · simp at hx

theorem mkCarriers_find : ∀ (ss : List SortId) (ns : List Nat) (off : Nat),
    ss.length = ns.length → (∀ n ∈ ns, 1 ≤ n) → ∀ s ∈ ss,
      ∃ e, (mkCarriers ss ns off).find? (fun e => e.1 == s) = some e ∧ e.2 ≠ []
  | [], _, _, _, _, s, hs => absurd hs List.not_mem_nil
  | _ :: _, [], _, hl, _, _, _ => by simp at hl
  | s0 :: ss, n0 :: ns, off, hl, hpos, s, hs => by
    simp only [mkCarriers, List.find?_cons]
    by_cases h : s0 = s
    · subst h
      have h1 := hpos n0 List.mem_cons_self
      refine ⟨(s0, List.range' off n0), by simp, ?_⟩
      cases n0 with
      | zero => omega
      | succ n => simp [List.range'_succ]
    · have hb : (s0 == s) = false := by simp [h]
      simp only [hb]
      have hs' : s ∈ ss := by
        rcases List.mem_cons.mp hs with rfl | hs
        · exact absurd rfl h
        · exact hs
      exact mkCarriers_find ss ns (off + n0) (by simpa using hl)
        (fun n hn => hpos n (List.mem_cons_of_mem _ hn)) s hs'

/-- Every structure of the searched class inhabits every approved sort. -/
theorem searchClass_inhabited {R : Registry} {I C : SemanticClaim} {k : Nat} {G : FinModel}
    (hG : G ∈ searchClass R I C k) : G.inhabitedB R = true := by
  unfold searchClass at hG
  obtain ⟨v, hv, hGv⟩ := List.mem_flatMap.mp hG
  have hlen := orderedSizeVectors_length hv
  obtain ⟨t, _, hvt⟩ := List.mem_flatMap.mp hv
  have hpos := mem_vecsSum_pos k _ t v hvt
  simp only [modelsFor, List.mem_flatMap, List.mem_map] at hGv
  obtain ⟨_, _, _, _, rfl⟩ := hGv
  unfold FinModel.inhabitedB
  apply List.all_eq_true.mpr
  intro s hs
  have hsig : s.id ∈ (searchSig R I C).sorts := by
    simp only [searchSig, List.mem_map]; exact ⟨s, hs, rfl⟩
  obtain ⟨e, he, hne⟩ := mkCarriers_find _ v 0 hlen.symm hpos s.id hsig
  simp only [FinModel.carrier, he]
  cases h2 : e.2 with
  | nil => exact absurd h2 hne
  | cons _ _ => rfl

/-- **A found countermodel is a checked witness.** -/
theorem search_found_sound {R : Registry} {I C : SemanticClaim} {k budget : Nat} {F : FinModel}
    (h : searchCountermodel R I C k budget = .found F) :
    checkCountermodel R I C (mkWitness I C F) = true := by
  have hp := (searchLoop_found h).1
  unfold isCountermodel at hp
  unfold checkCountermodel mkWitness
  simp only [Bool.and_eq_true] at hp
  simp [hp.1, hp.2]

/-- **A found countermodel is minimal**: no structure of the searched class with a strictly
    smaller total domain size is a countermodel. -/
theorem search_found_minimal {R : Registry} {I C : SemanticClaim} {k budget : Nat}
    {F : FinModel} (h : searchCountermodel R I C k budget = .found F) :
    F ∈ searchClass R I C k ∧
    ∀ G ∈ searchClass R I C k, isCountermodel R I C G = true → F.domainSize ≤ G.domainSize := by
  obtain ⟨_, v, hv, hF, hmin⟩ := searchLoop_found h
  refine ⟨List.mem_flatMap.mpr ⟨v, hv, hF⟩, fun G hG hpG => ?_⟩
  obtain ⟨w, hw, hGw, hle⟩ := hmin G hG hpG (orderedSizeVectors_pairwise _ _)
  rw [modelsFor_domainSize _ v (orderedSizeVectors_length hv).symm F hF,
    modelsFor_domainSize _ w (orderedSizeVectors_length hw).symm G hGw]
  exact hle

/-- **Completeness relative to the enumerated class**: an exhausted search means no structure
    of the explicitly enumerated class `searchClass R I C k` distinguishes the claims (as a
    registry-conforming structure).  This is *not* a proof of equivalence — see
    `no_countermodel_found_within_bound_is_not_equivalence_proof`. -/
theorem search_exhausted_complete {R : Registry} {I C : SemanticClaim} {k budget : Nat}
    (h : searchCountermodel R I C k budget = .exhausted) :
    ∀ G ∈ searchClass R I C k, G.conformsB R = true →
      (I.denote G.toModel ρ0 ↔ C.denote G.toModel ρ0) := by
  intro G hG hc
  have hp := searchLoop_exhausted h G hG
  unfold isCountermodel at hp
  rw [searchClass_inhabited hG, hc, Bool.true_and, Bool.true_and] at hp
  rw [← claim_evalF_iff, ← claim_evalF_iff]
  revert hp
  cases I.normalize.evalF G ρ0 env0 <;> cases C.normalize.evalF G ρ0 env0 <;> simp

end PCS.V2.Semantic
