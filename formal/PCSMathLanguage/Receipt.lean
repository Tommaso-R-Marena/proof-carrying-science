import PCSMathLanguage.Goals

/-!
# Action rendering, statement correspondence, final receipts and replay

* `ofJson` / `renderAction` — `render_action` on JSON `{kind, argument}`: `JArg` keeps
  Python's `bool`/`int` distinction (`type(a) is int` rejects `True`), references follow
  `REFERENCE` with the forbidden heads, hypothesis names follow `h[0-9]{1,2}`.
* `action_rendering_closed` — every rendered action is a single tactic line over a fixed safe
  alphabet (no newline, `;`, `:`, `(`, `#`, quotes …), so it cannot inject imports,
  declarations, axioms or commands.
* `tr` / `declGoal` — translation of the typed IR into the receiver goal language;
  `tr_agrees` — it preserves denotation; `decl_goal_sound` — a valid receiver goal yields the
  Lean statement of the declaration under every binder environment.
* `verifyReceipt` — independent final verification of a receipt bound to the full original
  declaration, the selected interpretation among the exact candidate list, the action
  sequence, the definitions/checker revisions and the axiom inventory;
  `final_receipt_sound`, `replay_reestablishes_original_claim`, `digest_is_only_an_index`.
-/

namespace PCSMathLanguage

/-! ## JSON actions and rendering -/

inductive JArg where
  | none
  | str (s : String)
  | int (n : Int)
  | bool (b : Bool)
  deriving DecidableEq, Repr

def FORBIDDEN : List String := ["sorry", "admit", "axiom", "unsafe", "native_decide"]

def isDigit (c : Char) : Bool := '0' ≤ c && c ≤ '9'

/-- `h[0-9]{1,2}`. -/
def validHyp (s : String) : Bool :=
  match s.toList with
  | ['h', d] => isDigit d
  | ['h', d, e] => isDigit d && isDigit e
  | _ => false

/-- Split a character list at every occurrence of `c` (Python `str.split(c)`). -/
def splitOnChar (c : Char) : List Char → List (List Char)
  | [] => [[]]
  | x :: xs => if x = c then [] :: splitOnChar c xs else
    match splitOnChar c xs with
    | w :: ws => (x :: w) :: ws
    | [] => [[x]]

/-- `REFERENCE = [A-Za-z][A-Za-z0-9_]{0,23}(?:\.[12]){0,3}` minus forbidden heads. -/
def parseRef (s : String) : Option Ref :=
  match splitOnChar '.' s.toList with
  | [] => none
  | head :: rest =>
    if validName (String.ofList head) && !FORBIDDEN.contains (String.ofList head) &&
        rest.length ≤ 3 && rest.all (fun p => p == ['1'] || p == ['2']) then
      some ⟨String.ofList head, rest.map (· == ['2'])⟩
    else none

def LEMMAS : List (String × LemmaName) :=
  [("Nat.add_zero", .add_zero), ("Nat.zero_add", .zero_add), ("Nat.add_comm", .add_comm),
   ("Nat.add_assoc", .add_assoc), ("Nat.mul_zero", .mul_zero), ("Nat.zero_mul", .zero_mul),
   ("Nat.mul_comm", .mul_comm), ("Nat.mul_one", .mul_one), ("Nat.one_mul", .one_mul)]

def simple? : String → Option Act
  | "constructor" => some .constructor
  | "assumption" => some .assumption
  | "rfl" => some .rfl
  | "left" => some .left
  | "right" => some .right
  | "contradiction" => some .contradiction
  | _ => none

/-- `cases` argument `"R as hN"` (reference and hypothesis contain no spaces). -/
def parseBranch (s : String) : Option (Ref × String) :=
  match splitOnChar ' ' s.toList with
  | [r, ['a', 's'], h] => match parseRef (String.ofList r) with
    | some ref => if validHyp (String.ofList h) then some (ref, String.ofList h) else none
    | none => none
  | _ => none

def ofJson (kind : String) (arg : JArg) : Option Act :=
  match simple? kind, arg with
  | some a, .none => some a
  | _, _ =>
  match kind, arg with
  | "intro", .str a => if validHyp a then some (.intro a) else none
  | "cases", .str a => match parseBranch a with
    | some (r, h) => some (.cases r (some h))
    | none => (parseRef a).map (.cases · none)
  | "exact", .str a => (parseRef a).map .exact
  | "apply", .str a => (parseRef a).map .apply
  | "rewrite", .str a => (parseRef a).map .rewrite
  | "lemma", .str a => (LEMMAS.lookup a).map .lemma
  | "simp", .none => some .simp
  | "witness", .int n => if 0 ≤ n ∧ n ≤ 8 then some (.witness n.toNat) else none
  | _, _ => none

def projText : List Bool → String
  | [] => ""
  | b :: ps => (if b then ".2" else ".1") ++ projText ps

def Ref.render (r : Ref) : String := r.name ++ projText r.proj

def SIMP_TEXT : String :=
  "simp only [Nat.add_zero, Nat.zero_add, Nat.mul_zero, Nat.zero_mul, Nat.mul_one, Nat.one_mul]"

def Act.render : Act → String
  | .intro h => "intro " ++ h
  | .constructor => "constructor"
  | .assumption => "assumption"
  | .rfl => "rfl"
  | .left => "left"
  | .right => "right"
  | .contradiction => "contradiction"
  | .exact r => "exact " ++ r.render
  | .apply r => "apply " ++ r.render
  | .cases r (some h) => "rcases " ++ r.render ++ " with " ++ h ++ " | " ++ h
  | .cases r none => "cases " ++ r.render
  | .rewrite r => "rw [" ++ r.render ++ "]"
  | .lemma n => "apply " ++ n.leanName
  | .simp => SIMP_TEXT
  | .witness n => "refine ⟨" ++ toString n ++ ", ?_⟩"

def renderAction (kind : String) (arg : JArg) : Option String := (ofJson kind arg).map Act.render

/-- The safe single-line alphabet. -/
def safeChar (c : Char) : Bool :=
  isAsciiAlnumU c || c == '.' || c == ' ' || c == '[' || c == ']' || c == ',' || c == '|' ||
    c == '?' || c == '⟨' || c == '⟩'

theorem validName_chars (s : String) (h : validName s = true) : s.toList.all safeChar = true := by
  unfold validName at h
  split at h
  · cases h
  · rename_i c cs hs
    rw [hs]
    simp only [Bool.and_eq_true, List.all_eq_true] at h ⊢
    intro x hx
    rcases List.mem_cons.1 hx with rfl | hx
    · simp [safeChar, isAsciiAlnumU, h.1.1]
    · simp [safeChar, h.1.2 x hx]

theorem validHyp_chars (s : String) (h : validHyp s = true) : s.toList.all safeChar = true := by
  unfold validHyp at h
  split at h
  · rename_i d hs; rw [hs]; simp_all [safeChar, isAsciiAlnumU, isAsciiLetter, isDigit]
  · rename_i d e hs; rw [hs]; simp_all [safeChar, isAsciiAlnumU, isAsciiLetter, isDigit]
  · cases h

theorem parseRef_chars (s : String) (r : Ref) (h : parseRef s = some r) :
    r.render.toList.all safeChar = true := by
  unfold parseRef at h
  split at h
  · cases h
  · rename_i head rest _
    split at h
    · rename_i hc
      cases h
      simp only [Bool.and_eq_true, Bool.not_eq_true'] at hc
      simp only [Ref.render, String.toList_append, List.all_append, Bool.and_eq_true]
      refine ⟨validName_chars _ hc.1.1.1, ?_⟩
      generalize rest.map (· == ['2']) = ps
      induction ps with
      | nil => decide
      | cons b ps ih =>
          simp only [projText, String.toList_append, List.all_append, Bool.and_eq_true]
          exact ⟨by cases b <;> decide, ih⟩
    · cases h

theorem witness_chars (n : Nat) (h : n ≤ 8) :
    ("refine ⟨" ++ toString n ++ ", ?_⟩").toList.all safeChar = true := by
  have : ∀ m, m < 9 → ("refine ⟨" ++ toString m ++ ", ?_⟩").toList.all safeChar = true := by
    decide
  exact this n (by omega)

/-- **Action rendering is closed**: every rendered action is one line over the safe alphabet. -/
theorem action_rendering_closed (kind : String) (arg : JArg) (s : String)
    (h : renderAction kind arg = some s) : s.toList.all safeChar = true ∧ '\n' ∉ s.toList := by
  suffices H : s.toList.all safeChar = true by
    refine ⟨H, fun hn => ?_⟩
    have := List.all_eq_true.1 H _ hn
    simp [safeChar, isAsciiAlnumU, isAsciiLetter] at this
  unfold renderAction at h
  simp only [Option.map_eq_some_iff] at h
  obtain ⟨act, ha, rfl⟩ := h
  unfold ofJson at ha
  split at ha
  · rename_i a _ hs
    cases ha
    unfold simple? at hs
    split at hs <;> (try cases hs) <;> decide
  · split at ha
    · split at ha
      · cases ha
        simp only [Act.render, String.toList_append, List.all_append, Bool.and_eq_true]
        exact ⟨by decide, validHyp_chars _ (by assumption)⟩
      · cases ha
    · split at ha
      · rename_i r h' hb
        cases ha
        unfold parseBranch at hb
        split at hb
        · rename_i rs hs' hsplit
          split at hb
          · rename_i ref href
            split at hb
            · cases hb
              simp only [Act.render, String.toList_append, List.all_append, Bool.and_eq_true]
              have hr := parseRef_chars _ _ href
              have hh := validHyp_chars _ (by assumption)
              exact ⟨⟨⟨⟨⟨by decide, hr⟩, by decide⟩, hh⟩, by decide⟩, hh⟩
            · cases hb
          · cases hb
        · cases hb
      · simp only [Option.map_eq_some_iff] at ha
        obtain ⟨r, hr, rfl⟩ := ha
        simp only [Act.render, String.toList_append, List.all_append, Bool.and_eq_true]
        exact ⟨by decide, parseRef_chars _ _ hr⟩
    · simp only [Option.map_eq_some_iff] at ha
      obtain ⟨r, hr, rfl⟩ := ha
      simp only [Act.render, String.toList_append, List.all_append, Bool.and_eq_true]
      exact ⟨by decide, parseRef_chars _ _ hr⟩
    · simp only [Option.map_eq_some_iff] at ha
      obtain ⟨r, hr, rfl⟩ := ha
      simp only [Act.render, String.toList_append, List.all_append, Bool.and_eq_true]
      exact ⟨by decide, parseRef_chars _ _ hr⟩
    · simp only [Option.map_eq_some_iff] at ha
      obtain ⟨r, hr, rfl⟩ := ha
      simp only [Act.render, String.toList_append, List.all_append, Bool.and_eq_true]
      exact ⟨⟨by decide, parseRef_chars _ _ hr⟩, by decide⟩
    · simp only [Option.map_eq_some_iff] at ha
      obtain ⟨n, _, rfl⟩ := ha
      cases n <;> decide
    · cases ha; decide
    · split at ha
      · rename_i n hn
        cases ha
        exact witness_chars _ (by omega)
      · cases ha
    · cases ha

/-! ## Typed IR → receiver goals -/

def Var.idx : {Γ : List Ty} → {τ : Ty} → Var Γ τ → Nat
  | _, _, .zero => 0
  | _, _, .succ x => x.idx + 1

def valAt : {Γ : List Ty} → Env Γ → Lookup
  | [], _, _ => none
  | τ :: _, (v, _), 0 => some ⟨τ, v⟩
  | _ :: _, (_, ρ), i + 1 => valAt ρ i

theorem valAt_var : ∀ {Γ : List Ty} {τ : Ty} (x : Var Γ τ) (η : Env Γ),
    valAt η x.idx = some ⟨τ, x.get η⟩
  | _ :: _, _, .zero, (_, _) => rfl
  | _ :: _, _, .succ x, (_, ρ) => valAt_var x ρ

inductive Tr where
  | p (f : GF)
  | n (e : NT)
  | fn (i : Nat)
  | pr (i : Nat)

def ofVar : Ty → Nat → Option Tr
  | .prop, i => some (.p (.atom i))
  | .nat, i => some (.n (.var i))
  | .natFn, i => some (.fn i)
  | .natPred, i => some (.pr i)
  | .int, _ => none

def trP : Option Tr → Option GF
  | some (.p f) => some f
  | _ => none

def trN : Option Tr → Option NT
  | some (.n e) => some e
  | _ => none

def tr : {Γ : List Ty} → {τ : Ty} → TExpr Γ τ → Option Tr
  | _, τ, .var x => ofVar τ x.idx
  | _, _, .natLit n => some (.n (.lit n))
  | _, _, .intLit _ => none
  | _, _, .tt => some (.p .tt)
  | _, _, .ff => some (.p .ff)
  | _, _, .not a => (trP (tr a)).map (.p ∘ .not)
  | _, _, .appF f a => match tr f, trN (tr a) with
    | some (.fn i), some e => some (.n (.app i e))
    | _, _ => none
  | _, _, .appP f a => match tr f, trN (tr a) with
    | some (.pr i), some e => some (.p (.papp i e))
    | _, _ => none
  | _, _, .all _ _ => none
  | _, _, .ex _ _ => none
  | _, _, .and a b => match trP (tr a), trP (tr b) with
    | some x, some y => some (.p (.and x y)) | _, _ => none
  | _, _, .or a b => match trP (tr a), trP (tr b) with
    | some x, some y => some (.p (.or x y)) | _, _ => none
  | _, _, .imp a b => match trP (tr a), trP (tr b) with
    | some x, some y => some (.p (.imp x y)) | _, _ => none
  | _, _, .iff a b => match trP (tr a), trP (tr b) with
    | some x, some y => some (.p (.iff x y)) | _, _ => none
  | _, _, .addN a b => match trN (tr a), trN (tr b) with
    | some x, some y => some (.n (.add x y)) | _, _ => none
  | _, _, .addI _ _ => none
  | _, _, .mulN a b => match trN (tr a), trN (tr b) with
    | some x, some y => some (.n (.mul x y)) | _, _ => none
  | _, _, .mulI _ _ => none
  | _, _, .eqN a b => match trN (tr a), trN (tr b) with
    | some x, some y => some (.p (.eq x y)) | _, _ => none
  | _, _, .eqI _ _ => none
  | _, _, .leN a b => match trN (tr a), trN (tr b) with
    | some x, some y => some (.p (.le x y)) | _, _ => none
  | _, _, .leI _ _ => none

def Agrees (L : Lookup) : (τ : Ty) → Val τ → Tr → Prop
  | .prop, p, .p f => (f.den L ↔ p)
  | .nat, n, .n e => e.eval L = n
  | .natFn, g, .fn i => fnAt L i = g
  | .natPred, g, .pr i => predAt L i = g
  | _, _, _ => False

theorem trP_agrees {L : Lookup} {p : Prop} {o : Option Tr} {f : GF}
    (hA : ∀ r, o = some r → Agrees L .prop p r) (h : trP o = some f) : (f.den L ↔ p) := by
  match o, h with
  | some (.p g), h => cases h; exact hA _ rfl

theorem trN_agrees {L : Lookup} {n : Nat} {o : Option Tr} {e : NT}
    (hA : ∀ r, o = some r → Agrees L .nat n r) (h : trN o = some e) : e.eval L = n := by
  match o, h with
  | some (.n g), h => cases h; exact hA _ rfl

/-- **The translation preserves denotation.** -/
theorem tr_agrees : ∀ {Γ : List Ty} {τ : Ty} (t : TExpr Γ τ) (η : Env Γ) (r : Tr),
    tr t = some r → Agrees (valAt η) τ (t.den η) r := by
  intro Γ τ t
  induction t with
  | var x =>
      intro η r h
      simp only [tr] at h
      have hv := valAt_var x η
      rename_i τ'
      cases τ' <;> simp [ofVar] at h <;> subst h <;>
        simp only [Agrees, GF.den, NT.eval, propAt, natAt, fnAt, predAt, hv, TExpr.den] <;> rfl
  | natLit n => intro η r h; cases h; rfl
  | intLit n => intro η r h; cases h
  | tt => intro η r h; cases h; simp [Agrees, GF.den, TExpr.den]
  | ff => intro η r h; cases h; simp [Agrees, GF.den, TExpr.den]
  | not a ih =>
      intro η r h
      simp only [tr, Option.map_eq_some_iff] at h
      obtain ⟨f, hf, rfl⟩ := h
      have := trP_agrees (ih η) hf
      simp only [Function.comp, Agrees, GF.den, TExpr.den, this]
  | appF f a ihf iha =>
      intro η r h
      simp only [tr] at h
      split at h
      · rename_i i e hf he
        cases h
        have h1 := ihf η _ hf
        have h2 := trN_agrees (iha η) he
        simp only [Agrees] at h1
        simp only [Agrees, NT.eval, TExpr.den, h1, h2]
      · cases h
  | appP f a ihf iha =>
      intro η r h
      simp only [tr] at h
      split at h
      · rename_i i e hf he
        cases h
        have h1 := ihf η _ hf
        have h2 := trN_agrees (iha η) he
        simp only [Agrees] at h1
        simp only [Agrees, GF.den, TExpr.den, h1, h2]
      · cases h
  | all _ _ _ => intro η r h; cases h
  | ex _ _ _ => intro η r h; cases h
  | and a b iha ihb | or a b iha ihb | imp a b iha ihb | iff a b iha ihb =>
      intro η r h
      simp only [tr] at h
      split at h
      · rename_i x y hx hy
        cases h
        have h1 := trP_agrees (iha η) hx
        have h2 := trP_agrees (ihb η) hy
        simp only [Agrees, GF.den, TExpr.den, h1, h2]
      · cases h
  | addN a b iha ihb | mulN a b iha ihb =>
      intro η r h
      simp only [tr] at h
      split at h
      · rename_i x y hx hy
        cases h
        have h1 := trN_agrees (iha η) hx
        have h2 := trN_agrees (ihb η) hy
        simp only [Agrees, NT.eval, TExpr.den, h1, h2]
      · cases h
  | eqN a b iha ihb | leN a b iha ihb =>
      intro η r h
      simp only [tr] at h
      split at h
      · rename_i x y hx hy
        cases h
        have h1 := trN_agrees (iha η) hx
        have h2 := trN_agrees (ihb η) hy
        simp only [Agrees, GF.den, TExpr.den, h1, h2]
      · cases h
  | addI _ _ _ _ | mulI _ _ _ _ | eqI _ _ _ _ | leI _ _ _ _ => intro η r h; cases h

/-- Binder context of a declaration (newest first, as Python's `variables`). -/
def Decl.vars (d : Decl) : List (String × Ty) := d.binders.reverse

/-- The Lean statement of a declaration, by the independent named semantics: for every binder
environment, the body holds. -/
def DeclHolds (d : Decl) : Prop :=
  ∀ (ρ : NEnv) (η : Env (d.vars.map (·.2))), Realises d.vars ρ η → asProp (rawDen ρ d.body)

/-- The receiver goal of a declaration (checked, lowered, translated). -/
def declGoal (d : Decl) : Option Goal :=
  match check d.vars 0 d.body with
  | some (.prop, _) => match lower d.vars d.body with
    | some ⟨.prop, t⟩ => (trP (tr t)).map fun f => ⟨[], f⟩
    | _ => none
  | _ => none

/-- **A valid receiver goal yields the Lean statement of the original declaration.** -/
theorem decl_goal_sound (d : Decl) (g : Goal) (hg : declGoal d = some g) (hv : g.Valid) :
    DeclHolds d := by
  unfold declGoal at hg
  split at hg
  · split at hg
    · rename_i t ht
      simp only [Option.map_eq_some_iff] at hg
      obtain ⟨f, hf, rfl⟩ := hg
      intro ρ η hR
      rw [typed_lowering_preserves_denotation d.body d.vars ρ η .prop t hR ht]
      have hag := trP_agrees (fun r hr => tr_agrees t η r hr) hf
      exact hag.1 (hv (valAt η) (by intro x hx; cases hx))
    · cases hg
  · cases hg

/-! ## Final receipts and replay -/

structure Receipt where
  decl : Decl
  candidates : List Decl
  interpretation : Nat
  actions : List Act
  definitions : String
  checker : String
  axioms : List String
  digest : String
  deriving DecidableEq, Repr

structure Config where
  checker : String
  definitions : String
  allowedAxioms : List String
  maxSteps : Nat

def verifyReceipt (c : Config) (r : Receipt) : Bool :=
  r.checker == c.checker && r.definitions == c.definitions &&
  r.axioms.all (· ∈ c.allowedAxioms) &&
  r.candidates[r.interpretation]? == some r.decl &&
  match declGoal r.decl with
  | some g => (runActs c.maxSteps (PState.init g) r.actions).goals.isEmpty
  | none => false

/-- **Final receipt soundness**: independent verification establishes the exact original
declaration (its binders, assumptions and quantifier order are part of `decl`), selected among
the recorded candidates, under the pinned checker/definitions and allowed axioms. -/
theorem final_receipt_sound (c : Config) (r : Receipt) (h : verifyReceipt c r = true) :
    DeclHolds r.decl ∧ r.candidates[r.interpretation]? = some r.decl ∧
      r.checker = c.checker ∧ r.definitions = c.definitions ∧
      (∀ a ∈ r.axioms, a ∈ c.allowedAxioms) := by
  unfold verifyReceipt at h
  simp only [Bool.and_eq_true, beq_iff_eq, List.all_eq_true, decide_eq_true_eq] at h
  obtain ⟨⟨⟨⟨h1, h2⟩, h3⟩, h4⟩, h5⟩ := h
  refine ⟨?_, h4, h1, h2, h3⟩
  split at h5
  · rename_i g hg
    simp only [List.isEmpty_iff] at h5
    exact decl_goal_sound _ g hg (closed_state_proves_original _ g _ h5)
  · cases h5

/-- Replay re-establishes the original claim from the stored receipt content alone. -/
theorem replay_reestablishes_original_claim (c : Config) (r : Receipt)
    (h : verifyReceipt c r = true) (r' : Receipt) (heq : r' = r) : DeclHolds r'.decl := by
  subst heq; exact (final_receipt_sound c r' h).1

/-- The digest is only an index: verification is independent of it. -/
theorem digest_is_only_an_index (c : Config) (r : Receipt) (d : String) :
    verifyReceipt c { r with digest := d } = verifyReceipt c r := rfl

/-- A receipt for one declaration says nothing about a different declaration: changing the
declaration (assumptions, quantifier order, environment) changes the certified claim. -/
theorem receipt_binds_exact_declaration (c : Config) (r : Receipt) (d : Decl)
    (h : verifyReceipt c { r with decl := d } = true) : DeclHolds d :=
  (final_receipt_sound c _ h).1

end PCSMathLanguage
