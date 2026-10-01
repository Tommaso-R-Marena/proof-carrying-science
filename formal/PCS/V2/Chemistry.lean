import PCS.V2.TCB

/-!
# A verified replay executor for `reaction_balance` evidence

`pcs/replay_v06.py::_replay_one` dispatches `check_spec.type == "reaction_balance"` to
`pcs/checks/chemistry.py::reaction_balanced`, which

* tokenizes each molecular formula with `_TOKEN = ([A-Z][a-z]?)([0-9]*)`, requiring the
  tokens to cover the whole (non-empty) formula;
* multiplies element counts by the entry's positive integer `coefficient` (default 1);
* reports `PASS` iff every element has the same total count on both sides, and `FAIL`
  otherwise or on any malformed input.

This file implements that check in Lean (`chemExecWith`) and proves it **faithful to a
declarative chemical semantics** (`ReactionDenotes`, `Balanced`), so for this evidence
type the replay assumption `ReplayFaithful` is a theorem rather than a hypothesis:

* `tokenize_sound` / `tokenize_complete`: the executable tokenizer decides the token
  grammar `Tokens`;
* `tokens_functional`: a formula has at most one token parse, so its meaning is unique;
* `balancedB_iff`: the executable balance test decides `Balanced`;
* `chemExecWith_faithful`: composing the Lean chemistry executor with any fallback
  executor for the other check types yields a faithful executor, provided only the
  fallback is faithful for those other types;
* `pcs_reaction_evidence_balanced`: with this executor, every accepted, passing
  `reaction_balance` evidence item denotes an atom-balanced reaction.  No assumption
  about Python, R, or any native code is involved for these items.
-/

namespace PCS.V2.Chemistry

open PCS PCS.V2.Json PCS.V2.Common PCS.V2.Package PCS.V2.Replay PCS.V2.EndToEnd
open PCS.V2.Flagship PCS.V2.CertificateModel

/-! ## Formula grammar -/

/-- ASCII `[A-Z]`. -/
def isUp (c : Char) : Bool := 65 ≤ c.toNat && c.toNat ≤ 90
/-- ASCII `[a-z]`. -/
def isLo (c : Char) : Bool := 97 ≤ c.toNat && c.toNat ≤ 122
/-- ASCII `[0-9]` (production uses `re.ASCII`, see counterexample 3 in the report). -/
def isDig (c : Char) : Bool := 48 ≤ c.toNat && c.toNat ≤ 57

theorem dropWhile_length_le (p : Char → Bool) : ∀ l : List Char, (l.dropWhile p).length ≤ l.length
  | [] => by simp
  | x :: xs => by
    by_cases hx : p x = true
    · rw [List.dropWhile_cons_of_pos hx]
      have := dropWhile_length_le p xs
      simp only [List.length_cons]; omega
    · rw [List.dropWhile_cons_of_neg hx]
      exact Nat.le_refl _

def digitsVal (ds : List Char) : Nat := ds.foldl (fun n d => 10 * n + (d.toNat - 48)) 0

/-- Count written after an element symbol: absent means 1. -/
def countOf (ds : List Char) : Nat := if ds = [] then 1 else digitsVal ds

/-- Declarative token grammar of `([A-Z][a-z]?)([0-9]*)`, repeated over the whole string. -/
inductive Tokens : List Char → List (String × Nat) → Prop
  | nil : Tokens [] []
  | cons {u : Char} {lw ds rest : List Char} {ts : List (String × Nat)} :
      isUp u = true → (lw = [] ∨ ∃ l, lw = [l] ∧ isLo l = true) →
      (∀ d ∈ ds, isDig d = true) → Tokens rest ts →
      Tokens (u :: (lw ++ (ds ++ rest))) ((String.ofList (u :: lw), countOf ds) :: ts)

def splitLower : List Char → List Char × List Char
  | l :: r => if isLo l then ([l], r) else ([], l :: r)
  | [] => ([], [])

theorem splitLower_append (cs : List Char) : (splitLower cs).1 ++ (splitLower cs).2 = cs := by
  unfold splitLower
  split
  · split <;> rfl
  · rfl

theorem splitLower_length (cs : List Char) : (splitLower cs).2.length ≤ cs.length := by
  have := congrArg List.length (splitLower_append cs)
  simp only [List.length_append] at this
  omega

/-- Executable tokenizer (maximal munch, exactly like `re.finditer` with a contiguity check). -/
def tokenize : List Char → Option (List (String × Nat))
  | [] => some []
  | u :: cs =>
    if isUp u then
      match tokenize ((splitLower cs).2.dropWhile isDig) with
      | some ts => some ((String.ofList (u :: (splitLower cs).1),
          countOf ((splitLower cs).2.takeWhile isDig)) :: ts)
      | none => none
    else none
termination_by l => l.length
decreasing_by
  have h1 := splitLower_length cs
  have h2 : ((splitLower cs).2.dropWhile isDig).length ≤ (splitLower cs).2.length :=
    dropWhile_length_le _ _
  simp only [List.length_cons]
  omega

theorem takeWhile_all {p : Char → Bool} : ∀ {l : List Char}, ∀ d ∈ l.takeWhile p, p d = true
  | [], d, hd => by simp at hd
  | x :: xs, d, hd => by
    by_cases hx : p x = true
    · rw [List.takeWhile_cons_of_pos hx] at hd
      rcases List.mem_cons.mp hd with rfl | hd
      · exact hx
      · exact takeWhile_all d hd
    · rw [List.takeWhile_cons_of_neg hx] at hd
      simp at hd

theorem tokenize_sound : ∀ {s : List Char} {ts : List (String × Nat)},
    tokenize s = some ts → Tokens s ts
  | [], ts, h => by
    rw [tokenize] at h
    cases h
    exact Tokens.nil
  | u :: cs, ts, h => by
    rw [tokenize] at h
    split at h
    · rename_i hu
      split at h
      · rename_i ts' hts'
        cases h
        have ih := tokenize_sound hts'
        have hsplit : cs = (splitLower cs).1 ++
            ((splitLower cs).2.takeWhile isDig ++ (splitLower cs).2.dropWhile isDig) := by
          rw [List.takeWhile_append_dropWhile, splitLower_append]
        have hlw : (splitLower cs).1 = [] ∨ ∃ l, (splitLower cs).1 = [l] ∧ isLo l = true := by
          unfold splitLower
          split
          · rename_i l r
            split
            · rename_i hl
              exact Or.inr ⟨l, rfl, hl⟩
            · exact Or.inl rfl
          · exact Or.inl rfl
        have := Tokens.cons (u := u) (lw := (splitLower cs).1)
          (ds := (splitLower cs).2.takeWhile isDig) hu hlw (fun d hd => takeWhile_all d hd) ih
        rw [← hsplit] at this
        exact this
      · cases h
    · cases h
termination_by s => s.length
decreasing_by
  have h1 := splitLower_length cs
  have h2 : ((splitLower cs).2.dropWhile isDig).length ≤ (splitLower cs).2.length :=
    dropWhile_length_le _ _
  simp only [List.length_cons]
  omega

theorem isUp_not_lo {c : Char} (h : isUp c = true) : isLo c = false := by
  simp only [isUp, isLo, Bool.and_eq_true, decide_eq_true_eq, Bool.and_eq_false_iff,
    decide_eq_false_iff_not] at h ⊢
  omega

theorem isUp_not_dig {c : Char} (h : isUp c = true) : isDig c = false := by
  simp only [isUp, isDig, Bool.and_eq_true, decide_eq_true_eq, Bool.and_eq_false_iff,
    decide_eq_false_iff_not] at h ⊢
  omega

theorem isLo_not_dig {c : Char} (h : isLo c = true) : isDig c = false := by
  simp only [isLo, isDig, Bool.and_eq_true, decide_eq_true_eq, Bool.and_eq_false_iff,
    decide_eq_false_iff_not] at h ⊢
  omega

/-- A token sequence starts with an upper-case letter (or is empty). -/
theorem Tokens.head_up {s : List Char} {ts : List (String × Nat)} (h : Tokens s ts) :
    ∀ c, s.head? = some c → isUp c = true := by
  cases h with
  | nil => intro c hc; cases hc
  | cons hu _ _ _ => intro c hc; simp at hc; subst hc; exact hu

theorem takeWhile_dig_append {ds rest : List Char} (hds : ∀ d ∈ ds, isDig d = true)
    (hrest : ∀ c, rest.head? = some c → isDig c = false) :
    (ds ++ rest).takeWhile isDig = ds ∧ (ds ++ rest).dropWhile isDig = rest := by
  induction ds with
  | nil =>
    cases rest with
    | nil => simp
    | cons c r =>
      have := hrest c rfl
      simp [List.takeWhile_cons_of_neg, List.dropWhile_cons_of_neg, this]
  | cons d ds ih =>
    have hd := hds d List.mem_cons_self
    have ih' := ih (fun x hx => hds x (List.mem_cons_of_mem _ hx))
    simp [List.takeWhile_cons_of_pos, List.dropWhile_cons_of_pos, hd, ih'.1, ih'.2]

/-- The executable tokenizer finds every grammatical parse. -/
theorem tokenize_complete {s : List Char} {ts : List (String × Nat)} (h : Tokens s ts) :
    tokenize s = some ts := by
  induction h with
  | nil => rw [tokenize]
  | @cons u lw ds rest ts hu hlw hds hrest ih =>
    have hrd : ∀ c, rest.head? = some c → isDig c = false :=
      fun c hc => isUp_not_dig (hrest.head_up c hc)
    have hsplit : splitLower (lw ++ (ds ++ rest)) = (lw, ds ++ rest) := by
      rcases hlw with rfl | ⟨l, rfl, hl⟩
      · simp only [List.nil_append]
        cases ds with
        | cons d ds' =>
          have hd := hds d List.mem_cons_self
          have hnl : isLo d = false := by
            cases hh : isLo d
            · rfl
            · rw [isLo_not_dig hh] at hd; cases hd
          simp [splitLower, hnl]
        | nil =>
          cases rest with
          | nil => rfl
          | cons c r =>
            have := isUp_not_lo (hrest.head_up c rfl)
            simp [splitLower, this]
      · simp [splitLower, hl]
    have htd := takeWhile_dig_append hds hrd
    rw [tokenize, if_pos hu]
    split
    · rename_i ts' h'
      rw [hsplit] at h'
      simp only [htd.2, ih] at h'
      cases h'
      simp only [hsplit, htd.1]
    · rename_i h'
      rw [hsplit] at h'
      simp only [htd.2, ih] at h'
      cases h'

/-- A formula has at most one parse: its chemical meaning is unambiguous. -/
theorem tokens_functional {s : List Char} {ts₁ ts₂ : List (String × Nat)}
    (h₁ : Tokens s ts₁) (h₂ : Tokens s ts₂) : ts₁ = ts₂ := by
  have := (tokenize_complete h₁).symm.trans (tokenize_complete h₂)
  cases this
  rfl

/-! ## Atom counts and balance -/

def tokCount (ts : List (String × Nat)) (e : String) : Nat :=
  ((ts.filter (fun t => t.1 == e)).map (·.2)).sum

abbrev Side := List (Nat × List (String × Nat))

def sideCount (side : Side) (e : String) : Nat :=
  (side.map (fun kt => kt.1 * tokCount kt.2 e)).sum

/-- A reaction is balanced when every element occurs equally often on both sides. -/
def Balanced (rs ps : Side) : Prop := ∀ e, sideCount rs e = sideCount ps e

def elems (side : Side) : List String := side.flatMap (fun kt => kt.2.map (·.1))

def balancedB (rs ps : Side) : Bool :=
  (elems rs ++ elems ps).all (fun e => sideCount rs e == sideCount ps e)

theorem tokCount_zero {ts : List (String × Nat)} {e : String} (h : e ∉ ts.map (·.1)) :
    tokCount ts e = 0 := by
  induction ts with
  | nil => rfl
  | cons t ts ih =>
    simp only [List.map_cons, List.mem_cons, not_or] at h
    have hne : (t.1 == e) = false := by
      simp only [beq_eq_false_iff_ne]; exact fun h' => h.1 h'.symm
    simp only [tokCount, List.filter_cons, hne] at ih ⊢
    exact ih h.2

theorem sideCount_zero {side : Side} {e : String} (h : e ∉ elems side) : sideCount side e = 0 := by
  induction side with
  | nil => rfl
  | cons kt side ih =>
    simp only [elems, List.flatMap_cons, List.mem_append, not_or] at h
    simp only [sideCount, List.map_cons, List.sum_cons] at ih ⊢
    rw [tokCount_zero h.1, ih h.2]
    simp

/-- The executable balance test decides `Balanced`. -/
theorem balancedB_iff (rs ps : Side) : balancedB rs ps = true ↔ Balanced rs ps := by
  constructor
  · intro h e
    simp only [balancedB, List.all_eq_true, beq_iff_eq] at h
    by_cases he : e ∈ elems rs ++ elems ps
    · exact h e he
    · simp only [List.mem_append, not_or] at he
      rw [sideCount_zero he.1, sideCount_zero he.2]
  · intro h
    simp only [balancedB, List.all_eq_true, beq_iff_eq]
    exact fun e _ => h e

/-! ## The `reaction_balance` check specification -/

/-- `entry.get("coefficient", 1)` must be a positive integer. -/
def coefficientOf (ms : List (String × JVal)) : Option Nat :=
  match field ms "coefficient" with
  | none => some 1
  | some (.num n) => if 0 < n then some n.toNat else none
  | _ => none

def decodeEntry : JVal → Option (Nat × List (String × Nat))
  | .obj ms =>
    match coefficientOf ms, field ms "formula" with
    | some k, some (.str f) =>
      match tokenize f.toList with
      | some ts => if ts = [] then none else some (k, ts)
      | none => none
    | _, _ => none
  | _ => none

def decodeSide : JVal → Option Side
  | .arr xs => mapOpt decodeEntry xs
  | _ => none

def checkSpec (ev : JVal) : Option (List (String × JVal)) :=
  match ev with
  | .obj ms =>
    match field ms "check_spec" with
    | some (.obj sp) => some sp
    | _ => none
  | _ => none

def isReactionCheck (ev : JVal) : Bool :=
  match checkSpec ev with
  | some sp => decide (strField sp "type" = some "reaction_balance")
  | none => false

def reactionSpec (ev : JVal) : Option (Side × Side) :=
  match checkSpec ev with
  | some sp =>
    match field sp "reactants", field sp "products" with
    | some r, some p =>
      match decodeSide r, decodeSide p with
      | some a, some b => some (a, b)
      | _, _ => none
    | _, _ => none
  | none => none

/-! ## Declarative meaning of a `reaction_balance` evidence object -/

/-- One reaction entry denotes `(coefficient, element tokens)`. -/
def EntryDenotes (v : JVal) (kt : Nat × List (String × Nat)) : Prop :=
  ∃ ms f, v = .obj ms ∧ coefficientOf ms = some kt.1 ∧ field ms "formula" = some (.str f) ∧
    Tokens f.toList kt.2 ∧ kt.2 ≠ []

/-- Pointwise denotation of a list of entries. -/
inductive EntriesDenote : List JVal → Side → Prop
  | nil : EntriesDenote [] []
  | cons {v kt xs side} : EntryDenotes v kt → EntriesDenote xs side →
      EntriesDenote (v :: xs) (kt :: side)

def SideDenotes (v : JVal) (side : Side) : Prop :=
  ∃ xs, v = .arr xs ∧ EntriesDenote xs side

/-- The evidence object is a `reaction_balance` check whose sides denote `rs` / `ps`. -/
def ReactionDenotes (ev : JVal) (rs ps : Side) : Prop :=
  ∃ sp r p, checkSpec ev = some sp ∧ strField sp "type" = some "reaction_balance" ∧
    field sp "reactants" = some r ∧ field sp "products" = some p ∧
    SideDenotes r rs ∧ SideDenotes p ps

/-- The scientific predicate of a `reaction_balance` item: its reaction is atom-balanced. -/
def ReactionHolds (ev : JVal) : Prop := ∃ rs ps, ReactionDenotes ev rs ps ∧ Balanced rs ps

theorem decodeEntry_sound {v : JVal} {kt : Nat × List (String × Nat)}
    (h : decodeEntry v = some kt) : EntryDenotes v kt := by
  unfold decodeEntry at h
  split at h
  · rename_i ms
    split at h
    · rename_i k f hk hf
      split at h
      · rename_i ts hts
        split at h
        · cases h
        · rename_i hne
          cases h
          exact ⟨ms, f, rfl, hk, hf, tokenize_sound hts, hne⟩
      · cases h
    · cases h
  · cases h

theorem mapOpt_entries :
    ∀ {xs : List JVal} {ys : Side}, mapOpt decodeEntry xs = some ys → EntriesDenote xs ys
  | [], ys, h => by cases h; exact EntriesDenote.nil
  | x :: xs, ys, h => by
    simp only [mapOpt] at h
    split at h
    · rename_i y ys' hy hys
      cases h
      exact EntriesDenote.cons (decodeEntry_sound hy) (mapOpt_entries hys)
    · cases h

theorem decodeSide_sound {v : JVal} {side : Side} (h : decodeSide v = some side) :
    SideDenotes v side := by
  unfold decodeSide at h
  split at h
  · rename_i xs
    exact ⟨xs, rfl, mapOpt_entries h⟩
  · cases h

theorem reactionSpec_sound {ev : JVal} {rs ps : Side} (hc : isReactionCheck ev = true)
    (h : reactionSpec ev = some (rs, ps)) : ReactionDenotes ev rs ps := by
  unfold isReactionCheck at hc
  unfold reactionSpec at h
  split at h
  · rename_i sp hsp
    rw [hsp] at hc
    simp only [decide_eq_true_eq] at hc
    split at h
    · rename_i r p hr hp
      split at h
      · rename_i a b ha hb
        cases h
        exact ⟨sp, r, p, hsp, hc, hr, hp, decodeSide_sound ha, decodeSide_sound hb⟩
      · cases h
    · cases h
  · cases h

/-! ## The executor and its faithfulness -/

/-- The Lean `reaction_balance` executor, delegating every other check type to
    `fallback` (e.g. the production Python/R runtime). -/
def chemExecWith (fallback : Executor) : Executor := fun req =>
  if isReactionCheck req.evidence then
    match reactionSpec req.evidence with
    | some (rs, ps) => ⟨.computationalTest, if balancedB rs ps then .pass else .fail⟩
    | none => ⟨.computationalTest, .fail⟩
  else fallback req

/-- Replay predicate of the composed executor: chemistry items mean balanced reactions;
    every other item means whatever the fallback's predicate says. -/
def ChemHolds (fallbackHolds : ReplayRequest → Prop) (req : ReplayRequest) : Prop :=
  (isReactionCheck req.evidence = true → ReactionHolds req.evidence) ∧
  (isReactionCheck req.evidence = false → fallbackHolds req)

/-- Faithfulness of the composed executor needs faithfulness of the fallback only. -/
theorem chemExecWith_faithful {fallback : Executor} {fallbackHolds : ReplayRequest → Prop}
    (hfb : ReplayFaithful fallback fallbackHolds) :
    ReplayFaithful (chemExecWith fallback) (ChemHolds fallbackHolds) := by
  intro req hpass
  unfold chemExecWith at hpass
  by_cases hc : isReactionCheck req.evidence = true
  · rw [if_pos hc] at hpass
    refine ⟨fun _ => ?_, fun hf => (by rw [hc] at hf; cases hf)⟩
    split at hpass
    · rename_i rs ps hspec
      have hb : balancedB rs ps = true := by
        cases hbb : balancedB rs ps
        · rw [hbb] at hpass; cases hpass
        · rfl
      exact ⟨rs, ps, reactionSpec_sound hc hspec, (balancedB_iff rs ps).1 hb⟩
    · cases hpass
  · have hc' : isReactionCheck req.evidence = false := by simpa using hc
    rw [if_neg hc] at hpass
    exact ⟨fun h => (by rw [hc'] at h; cases h), fun _ => hfb req hpass⟩

/-- The pure Lean executor (every non-chemistry item is reported `UNVERIFIED`) is
    faithful with no hypothesis at all. -/
def unverifiedExec : Executor := fun _ => ⟨.provenance, .unverified⟩

theorem unverifiedExec_faithful : ReplayFaithful unverifiedExec (fun _ => False) := by
  intro req h
  cases h

theorem chemExec_faithful :
    ReplayFaithful (chemExecWith unverifiedExec) (ChemHolds (fun _ => False)) :=
  chemExecWith_faithful unverifiedExec_faithful

/-- **End-to-end chemistry assurance.**  If the Lean checker, running the Lean
    `reaction_balance` executor (with any fallback that is faithful for the other check
    types), accepts a package, then every accepted, passing `reaction_balance` evidence
    item of every claim is a certificate evidence object whose reaction is atom-balanced
    under the declarative formula semantics. -/
theorem pcs_reaction_evidence_balanced {O : Oracles} {T : TrustAnchor} {inp : PackageInput}
    {r : AcceptedResult} {fallbackHolds : ReplayRequest → Prop}
    (hO : ∃ fb, O.exec = chemExecWith fb ∧ ReplayFaithful fb fallbackHolds)
    (h : acceptPCS O T inp = some r) :
    ∀ p ∈ r.claims, ∀ ev ∈ p.2.evidence, ev.outcome = .pass →
      ∃ e ∈ r.model.evidence, e.id = ev.id ∧
        (isReactionCheck e.json = true → ReactionHolds e.json) := by
  obtain ⟨fb, hex, hfb⟩ := hO
  have hR : ReplayFaithful O.exec (ChemHolds fallbackHolds) := by
    rw [hex]; exact chemExecWith_faithful hfb
  intro p hp ev hev hpass
  obtain ⟨e, he, hid, hholds⟩ := pcs_evidence_holds h hR p hp ev hev hpass
  exact ⟨e, he, hid, hholds.1⟩

end PCS.V2.Chemistry
