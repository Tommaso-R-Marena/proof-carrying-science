import PCSMathLanguage.IR
import PCSMathLanguage.Alpha

/-!
# Rendering/parsing round trip for the receiver-owned Math IR rendering

`check` (the transcription of `ir.py`'s `expression`) renders every accepted expression to the
exact Lean source string the receiver elaborates.  Here we

* define `renderL : Expr → List Char`, the same rendering at character level, and prove
  `check_render_exact`: the checker's string is *character for character* `renderL e`;
* define an independent scannerless recursive-descent parser `parse` over Unicode characters
  (words, decimal numerals with `Nat.toDigits`, `¬ ∀ ∃ ∧ ∨ → ↔ + * = ≤`, single spaces,
  parentheses, `:` and `,`);
* prove `render_parse_alpha_roundtrip`: for every checker-accepted expression (over a context
  of valid, non-reserved names) parsing the receiver's string returns exactly the original IR
  (hence in particular an alpha-equivalent one, with the same quantifier order, binder types
  and canonical de Bruijn form);
* derive `render_injective_on_checked`: two accepted expressions with the same rendering are
  equal — distinct meanings can never be conflated by the rendered Lean statement.
-/

namespace PCSMathLanguage
namespace RoundTrip

/-! ## Character-level rendering -/

def _root_.PCSMathLanguage.Op.sym : Op → Char
  | .and => '∧' | .or => '∨' | .implies => '→' | .iff => '↔'
  | .add => '+' | .mul => '*' | .eq => '=' | .le => '≤'

def _root_.PCSMathLanguage.Q.sym : Q → Char
  | .all => '∀' | .ex => '∃'

def renderL : Expr → List Char
  | .var n => n.toList
  | .num n t => '(' :: Nat.toDigits 10 n ++ ' ' :: ':' :: ' ' :: t.key.toList ++ [')']
  | .tt => "True".toList
  | .ff => "False".toList
  | .not a => '(' :: '¬' :: ' ' :: renderL a ++ [')']
  | .apply f a => '(' :: renderL f ++ ' ' :: renderL a ++ [')']
  | .quant q n t b => '(' :: q.sym :: ' ' :: '(' :: n.toList ++ ' ' :: ':' :: ' ' ::
      t.lean.toList ++ ')' :: ',' :: ' ' :: renderL b ++ [')']
  | .bin op l r => '(' :: renderL l ++ ' ' :: op.sym :: ' ' :: renderL r ++ [')']

@[simp] theorem lit_lp : "(".toList = ['('] := by decide
@[simp] theorem lit_rp : ")".toList = [')'] := by decide
@[simp] theorem lit_sp : " ".toList = [' '] := by decide
@[simp] theorem lit_colon : " : ".toList = [' ', ':', ' '] := by decide
@[simp] theorem lit_not : "(¬ ".toList = ['(', '¬', ' '] := by decide
@[simp] theorem lit_all : "(∀ (".toList = ['(', '∀', ' ', '('] := by decide
@[simp] theorem lit_ex : "(∃ (".toList = ['(', '∃', ' ', '('] := by decide
@[simp] theorem lit_comma : "), ".toList = [')', ',', ' '] := by decide
@[simp] theorem lit_forall : "∀".toList = ['∀'] := by decide
@[simp] theorem lit_exists : "∃".toList = ['∃'] := by decide

theorem op_spec_sym (op : Op) : op.spec.2.2.toList = [Op.sym op] := by
  cases op <;> decide

theorem check_render_exact : ∀ (e : Expr) (vars : List (String × Ty)) (d : Nat) (τ : Ty)
    (s : String), check vars d e = some (τ, s) → s.toList = renderL e := by
  intro e
  induction e with
  | var n =>
    intro vars d τ s h
    simp only [check, gd] at h
    split at h
    · cases h
    · cases hl : lookupTy vars n <;> simp_all [renderL]
  | num n t =>
    intro vars d τ s h
    simp only [check, gd] at h
    split at h
    · cases h
    · split at h
      · cases h; simp [renderL, String.toList_append, toString, Nat.repr]
      · cases h
  | tt => intro vars d τ s h; simp only [check, gd] at h; split at h <;> simp_all [renderL]
  | ff => intro vars d τ s h; simp only [check, gd] at h; split at h <;> simp_all [renderL]
  | not a ih =>
    intro vars d τ s h
    simp only [check, gd] at h
    split at h
    · cases h
    · split at h
      · rename_i s' hc; cases h
        simp [renderL, String.toList_append, toString, ih _ _ _ _ hc]
      · cases h
  | apply f a ihf iha =>
    intro vars d τ s h
    simp only [check, gd] at h
    split at h
    · cases h
    · split at h
      · rename_i sf sa hf ha; cases h
        simp [renderL, String.toList_append, toString, ihf _ _ _ _ hf, iha _ _ _ _ ha]
      · rename_i sf sa hf ha; cases h
        simp [renderL, String.toList_append, toString, ihf _ _ _ _ hf, iha _ _ _ _ ha]
      · cases h
  | quant q n t b ih =>
    intro vars d τ s h
    simp only [check, gd] at h
    split at h
    · cases h
    · split at h
      · cases h
      · split at h
        · rename_i sb hb; cases h
          cases q <;>
            simp [renderL, String.toList_append, toString, ih _ _ _ _ hb, Q.sym]
        · cases h
  | bin op l r ihl ihr =>
    intro vars d τ s h
    simp only [check, gd] at h
    split at h
    · cases h
    · split at h
      · rename_i lt sl rt sr hl hr
        have e1 := op_spec_sym op
        split at h <;>
          (simp at h; obtain ⟨-, -, rfl⟩ := h
           simp [renderL, String.toList_append, toString, ihl _ _ _ _ hl, ihr _ _ _ _ hr, e1])
      · cases h

/-! ## The independent parser -/

def isAN (c : Char) : Bool := isAsciiAlnumU c
def isD (c : Char) : Bool := '0' ≤ c && c ≤ '9'

/-- Longest prefix satisfying `p`, and the remainder. -/
def spanW (p : Char → Bool) : List Char → List Char × List Char
  | [] => ([], [])
  | c :: cs => if p c then ((c :: (spanW p cs).1), (spanW p cs).2) else ([], c :: cs)

def digVal (L : List Char) : Nat := L.foldl (fun a c => 10 * a + (c.toNat - 48)) 0

/-- Strip an expected literal prefix. -/
def expect : List Char → List Char → Option (List Char)
  | [], r => some r
  | c :: cs, d :: r => if c = d then expect cs r else none
  | _ :: _, [] => none

def opOfChar (c : Char) : Option Op :=
  if c = '∧' then some .and else if c = '∨' then some .or else if c = '→' then some .implies
  else if c = '↔' then some .iff else if c = '+' then some .add else if c = '*' then some .mul
  else if c = '=' then some .eq else if c = '≤' then some .le else none

def keyOf (w : List Char) : Option Ty :=
  if w = "Prop".toList then some .prop else if w = "Nat".toList then some .nat
  else if w = "Int".toList then some .int else if w = "NatFn".toList then some .natFn
  else if w = "NatPred".toList then some .natPred else none

def parseTy (cs : List Char) : Option (Ty × List Char) :=
  match spanW isAN cs with
  | (w, r) =>
    if w = "Prop".toList then some (.prop, r)
    else if w = "Int".toList then some (.int, r)
    else if w = "Nat".toList then
      match r with
      | ' ' :: '→' :: ' ' :: r' =>
        match spanW isAN r' with
        | (w2, r2) =>
          if w2 = "Nat".toList then some (.natFn, r2)
          else if w2 = "Prop".toList then some (.natPred, r2) else none
      | _ => some (.nat, r)
    else none

def parse : Nat → List Char → Option (Expr × List Char)
  | 0, _ => none
  | _ + 1, [] => none
  | f + 1, c :: cs =>
    if isAsciiLetter c then
      match spanW isAN (c :: cs) with
      | (w, r) =>
        if w = "True".toList then some (.tt, r)
        else if w = "False".toList then some (.ff, r)
        else some (.var (String.ofList w), r)
    else if c = '(' then
      match cs with
      | [] => none
      | c2 :: r =>
        if c2 = '¬' then
          match r with
          | ' ' :: r1 =>
            match parse f r1 with
            | some (a, ')' :: r2) => some (.not a, r2)
            | _ => none
          | _ => none
        else if c2 = '∀' ∨ c2 = '∃' then
          match r with
          | ' ' :: '(' :: r1 =>
            match spanW isAN r1 with
            | (w, ' ' :: ':' :: ' ' :: r2) =>
              match parseTy r2 with
              | some (t, ')' :: ',' :: ' ' :: r3) =>
                match parse f r3 with
                | some (b, ')' :: r4) =>
                  some (.quant (if c2 = '∀' then .all else .ex) (String.ofList w) t b, r4)
                | _ => none
              | _ => none
            | _ => none
          | _ => none
        else if isD c2 then
          match spanW isD (c2 :: r) with
          | (ds, ' ' :: ':' :: ' ' :: r1) =>
            match spanW isAN r1 with
            | (w, ')' :: r2) =>
              match keyOf w with
              | some t => some (.num (digVal ds) t, r2)
              | none => none
            | _ => none
          | _ => none
        else
          match parse f (c2 :: r) with
          | some (l, ' ' :: r1) =>
            match r1 with
            | o :: ' ' :: r2 =>
              match opOfChar o with
              | some op =>
                match parse f r2 with
                | some (rr, ')' :: r3) => some (.bin op l rr, r3)
                | _ => none
              | none =>
                match parse f r1 with
                | some (a, ')' :: r3) => some (.apply l a, r3)
                | _ => none
            | _ =>
              match parse f r1 with
              | some (a, ')' :: r3) => some (.apply l a, r3)
              | _ => none
          | _ => none
    else none

/-- Parse a complete rendered string. -/
def parseString (s : String) : Option Expr :=
  match parse (s.length + 1) s.toList with
  | some (e, []) => some e
  | _ => none

end RoundTrip
end PCSMathLanguage

namespace PCSMathLanguage
namespace RoundTrip

/-! ## Round-trip proof -/

/-- Well-formed names for the round trip: free and bound variable names are `NAME`-valid, and
free variables are not the constants `True`/`False`. -/
def WF : Expr → Prop
  | .var n => validName n = true ∧ n ≠ "True" ∧ n ≠ "False"
  | .num _ _ => True
  | .tt => True
  | .ff => True
  | .not a => WF a
  | .apply f a => WF f ∧ WF a
  | .quant _ n _ b => validName n = true ∧ WF b
  | .bin _ l r => WF l ∧ WF r

def sz : Expr → Nat
  | .not a => sz a + 1
  | .apply f a => sz f + sz a + 1
  | .quant _ _ _ b => sz b + 1
  | .bin _ l r => sz l + sz r + 1
  | _ => 1

/-- The continuation after a rendered expression does not extend its last word. -/
def Stop (r : List Char) : Prop := ∀ c, r.head? = some c → isAN c = false

theorem span_app (p : Char → Bool) : ∀ (L r : List Char), (∀ c ∈ L, p c = true) →
    (∀ c, r.head? = some c → p c = false) → spanW p (L ++ r) = (L, r) := by
  intro L r hL hr
  induction L with
  | nil =>
    cases r with
    | nil => rfl
    | cons c r' => simp [spanW, hr c rfl]
  | cons c L ih =>
    have hc := hL c (by simp)
    have ih' := ih (fun x hx => hL x (by simp [hx]))
    simp [spanW, hc, ih']

theorem validName_parts (n : String) (h : validName n = true) :
    ∃ c cs, n.toList = c :: cs ∧ isAsciiLetter c = true ∧ ∀ x ∈ n.toList, isAN x = true := by
  unfold validName at h
  revert h
  cases hn : n.toList with
  | nil => simp
  | cons c cs =>
    intro h
    simp only [Bool.and_eq_true, List.all_eq_true, decide_eq_true_eq] at h
    refine ⟨c, cs, rfl, h.1.1, ?_⟩
    intro x hx
    simp only [List.mem_cons] at hx
    rcases hx with rfl | hx
    · simp [isAN, isAsciiAlnumU, h.1.1]
    · exact h.1.2 x hx

theorem toList_ne_of_ne {a b : String} (h : a ≠ b) : a.toList ≠ b.toList := by
  intro h'; exact h (String.toList_inj.mp h')

/-- First character of every well-formed rendering: an ASCII letter or `(`. -/
theorem render_head : ∀ e, WF e → ∃ c cs, renderL e = c :: cs ∧ (isAsciiLetter c = true ∨ c = '(')
  | .var n, h => by
    obtain ⟨c, cs, hc, hl, -⟩ := validName_parts n h.1
    exact ⟨c, cs, by simp [renderL, hc], .inl hl⟩
  | .num _ _, _ => ⟨_, _, rfl, .inr rfl⟩
  | .tt, _ => ⟨'T', ['r', 'u', 'e'], by decide, .inl (by decide)⟩
  | .ff, _ => ⟨'F', ['a', 'l', 's', 'e'], by decide, .inl (by decide)⟩
  | .not _, _ => ⟨_, _, rfl, .inr rfl⟩
  | .apply _ _, _ => ⟨_, _, rfl, .inr rfl⟩
  | .quant _ _ _ _, _ => ⟨_, _, rfl, .inr rfl⟩
  | .bin _ _ _, _ => ⟨_, _, rfl, .inr rfl⟩


theorem digitChar_ok : ∀ k, k < 10 → isD (Nat.digitChar k) = true ∧ (Nat.digitChar k).toNat - 48 = k := by
  decide

theorem toDigitsCore_acc : ∀ (fuel n : Nat) (ds : List Char),
    Nat.toDigitsCore 10 fuel n ds = Nat.toDigitsCore 10 fuel n [] ++ ds := by
  intro fuel
  induction fuel with
  | zero => intro n ds; rfl
  | succ f ih =>
    intro n ds
    simp only [Nat.toDigitsCore]
    split
    · rfl
    · rw [ih _ (_ :: ds), ih _ [_]]; simp

theorem digVal_snoc (L : List Char) (d : Char) : digVal (L ++ [d]) = 10 * digVal L + (d.toNat - 48) := by
  simp [digVal, List.foldl_append]

theorem toDigitsCore_ok : ∀ (fuel n : Nat), n < fuel →
    (∀ c ∈ Nat.toDigitsCore 10 fuel n [], isD c = true) ∧ Nat.toDigitsCore 10 fuel n [] ≠ [] ∧
    digVal (Nat.toDigitsCore 10 fuel n []) = n := by
  intro fuel
  induction fuel with
  | zero => intro n h; omega
  | succ f ih =>
    intro n hn
    have hd := digitChar_ok (n % 10) (Nat.mod_lt _ (by omega))
    simp only [Nat.toDigitsCore]
    split
    · rename_i h0
      refine ⟨by simp [hd.1], by simp, ?_⟩
      simp only [digVal, List.foldl]
      have := Nat.div_add_mod n 10
      omega
    · rename_i h0
      rw [toDigitsCore_acc]
      have hlt : n / 10 < f := by
        have : n / 10 < n := Nat.div_lt_self (by omega) (by omega)
        omega
      obtain ⟨h1, h2, h3⟩ := ih (n / 10) hlt
      refine ⟨?_, by simp, ?_⟩
      · intro c hc
        simp only [List.mem_append, List.mem_singleton] at hc
        rcases hc with hc | rfl
        · exact h1 c hc
        · exact hd.1
      · rw [digVal_snoc, h3, hd.2]
        have := Nat.div_add_mod n 10
        omega

theorem toDigits_ok (n : Nat) :
    (∀ c ∈ Nat.toDigits 10 n, isD c = true) ∧ Nat.toDigits 10 n ≠ [] ∧
    digVal (Nat.toDigits 10 n) = n :=
  toDigitsCore_ok (n + 1) n (by omega)

theorem keyOf_key (t : Ty) : keyOf t.key.toList = some t := by cases t <;> decide

theorem key_AN (t : Ty) : ∀ c ∈ t.key.toList, isAN c = true := by cases t <;> decide

theorem parseTy_lean (t : Ty) (X : List Char) :
    parseTy (t.lean.toList ++ ')' :: X) = some (t, ')' :: X) := by
  have e1 : "Prop".toList = ['P', 'r', 'o', 'p'] := by decide
  have e2 : "Nat".toList = ['N', 'a', 't'] := by decide
  have e3 : "Int".toList = ['I', 'n', 't'] := by decide
  have e4 : "Nat → Nat".toList = ['N', 'a', 't', ' ', '→', ' ', 'N', 'a', 't'] := by decide
  have e5 : "Nat → Prop".toList = ['N', 'a', 't', ' ', '→', ' ', 'P', 'r', 'o', 'p'] := by decide
  cases t <;> simp [parseTy, Ty.lean, e1, e2, e3, e4, e5, spanW, isAN, isAsciiAlnumU, isAsciiLetter]

theorem opOfChar_sym (op : Op) : opOfChar op.sym = some op := by cases op <;> decide

theorem opOfChar_head (c : Char) (h : isAsciiLetter c = true ∨ c = '(') : opOfChar c = none := by
  rcases h with h | rfl
  · unfold opOfChar
    have : c ≠ '∧' ∧ c ≠ '∨' ∧ c ≠ '→' ∧ c ≠ '↔' ∧ c ≠ '+' ∧ c ≠ '*' ∧ c ≠ '=' ∧ c ≠ '≤' := by
      refine ⟨?_, ?_, ?_, ?_, ?_, ?_, ?_, ?_⟩ <;> (rintro rfl; revert h; decide)
    simp [this.1, this.2.1, this.2.2.1, this.2.2.2.1, this.2.2.2.2.1, this.2.2.2.2.2.1,
      this.2.2.2.2.2.2.1, this.2.2.2.2.2.2.2]
  · decide


theorem stop_rp (r : List Char) : Stop (')' :: r) := by
  intro c h; cases h; decide
theorem stop_sp (r : List Char) : Stop (' ' :: r) := by
  intro c h; cases h; decide

theorem letter_AN (c : Char) (h : isAsciiLetter c = true) : isAN c = true := by
  simp [isAN, isAsciiAlnumU, h]

theorem letter_not_digit (c : Char) (h : isAsciiLetter c = true) : isD c = false := by
  revert h; simp only [isAsciiLetter, isD, Bool.or_eq_true, Bool.and_eq_true, decide_eq_true_eq]
  intro h
  rcases h with ⟨h1, h2⟩ | ⟨h1, h2⟩ <;>
  · cases hc : decide ('0' ≤ c) <;> cases hd : decide (c ≤ '9') <;> simp_all <;>
      (simp [Char.le_def, UInt32.le_iff_toNat_le] at *; omega)

theorem head_ne (c : Char) (h : isAsciiLetter c = true ∨ c = '(') :
    c ≠ '¬' ∧ ¬ (c = '∀' ∨ c = '∃') ∧ isD c = false ∧ opOfChar c = none := by
  refine ⟨?_, ?_, ?_, opOfChar_head c h⟩
  · rcases h with h | rfl
    · rintro rfl; revert h; decide
    · decide
  · rcases h with h | rfl
    · rintro (rfl | rfl) <;> revert h <;> decide
    · decide
  · rcases h with h | rfl
    · exact letter_not_digit c h
    · decide

theorem parse_render : ∀ e, WF e → ∀ (fuel : Nat) (r : List Char), sz e ≤ fuel → Stop r →
    parse fuel (renderL e ++ r) = some (e, r) := by
  intro e
  induction e with
  | var n =>
    intro hw fuel r hf hr
    obtain ⟨c, cs, hc, hl, han⟩ := validName_parts n hw.1
    obtain ⟨f, rfl⟩ : ∃ f, fuel = f + 1 := ⟨fuel - 1, by simp [sz] at hf; omega⟩
    have hs := span_app isAN n.toList r han hr
    rw [hc, List.cons_append] at hs
    simp only [renderL, hc, List.cons_append, parse, hl, if_true]
    rw [hs]
    have h1 := toList_ne_of_ne hw.2.1
    have h2 := toList_ne_of_ne hw.2.2
    simp only [← hc]; simp [h1, h2]
  | tt =>
    intro hw fuel r hf hr
    obtain ⟨f, rfl⟩ : ∃ f, fuel = f + 1 := ⟨fuel - 1, by simp [sz] at hf; omega⟩
    have e : "True".toList = ['T', 'r', 'u', 'e'] := by decide
    have hs := span_app isAN ['T', 'r', 'u', 'e'] r (by decide) hr
    simp only [List.cons_append, List.nil_append] at hs
    simp only [renderL, e, List.cons_append, List.nil_append, parse]
    rw [hs]; simp; decide
  | ff =>
    intro hw fuel r hf hr
    obtain ⟨f, rfl⟩ : ∃ f, fuel = f + 1 := ⟨fuel - 1, by simp [sz] at hf; omega⟩
    have e : "False".toList = ['F', 'a', 'l', 's', 'e'] := by decide
    have hs := span_app isAN ['F', 'a', 'l', 's', 'e'] r (by decide) hr
    simp only [List.cons_append, List.nil_append] at hs
    simp only [renderL, e, List.cons_append, List.nil_append, parse]
    rw [hs]; simp; decide
  | num n t =>
    intro hw fuel r hf hr
    obtain ⟨f, rfl⟩ : ∃ f, fuel = f + 1 := ⟨fuel - 1, by simp [sz] at hf; omega⟩
    obtain ⟨hd, hne, hv⟩ := toDigits_ok n
    obtain ⟨d, ds, hdd⟩ : ∃ d ds, Nat.toDigits 10 n = d :: ds := by
      cases h : Nat.toDigits 10 n with
      | nil => exact absurd h hne
      | cons d ds => exact ⟨d, ds, rfl⟩
    have hdD : isD d = true := hd d (by simp [hdd])
    have s1 := span_app isD (Nat.toDigits 10 n) (' ' :: ':' :: ' ' :: (t.key.toList ++ ')' :: r)) hd
      (by intro c h; cases h; decide)
    have s2 := span_app isAN t.key.toList (')' :: r) (key_AN t) (stop_rp r)
    rw [hdd, List.cons_append] at s1
    have hd1 : d ≠ '¬' := by rintro rfl; revert hdD; decide
    have hd2 : ¬ (d = '∀' ∨ d = '∃') := by rintro (rfl | rfl) <;> revert hdD <;> decide
    simp only [renderL, hdd, List.cons_append, List.append_assoc, List.nil_append, parse]
    simp only [show isAsciiLetter '(' = false by decide, if_true, hd1, hd2, hdD, if_false,
      Bool.false_eq_true]
    rw [s1]
    simp only [s2, keyOf_key]
    rw [← hdd, hv]
  | not a ih =>
    intro hw fuel r hf hr
    obtain ⟨f, rfl⟩ : ∃ f, fuel = f + 1 := ⟨fuel - 1, by simp [sz] at hf; omega⟩
    have ih' := ih hw f (')' :: r) (by simp [sz] at hf; omega) (stop_rp r)
    simp only [renderL, List.cons_append, List.append_assoc, List.nil_append, parse]
    simp only [show isAsciiLetter '(' = false by decide, if_true, Bool.false_eq_true, ite_false]
    rw [ih']; rfl
  | quant q n t b ih =>
    intro hw fuel r hf hr
    obtain ⟨f, rfl⟩ : ∃ f, fuel = f + 1 := ⟨fuel - 1, by simp [sz] at hf; omega⟩
    have ih' := ih hw.2 f (')' :: r) (by simp [sz] at hf; omega) (stop_rp r)
    obtain ⟨c, cs, hc, hl, han⟩ := validName_parts n hw.1
    have s1 := span_app isAN n.toList (' ' :: ':' :: ' ' :: (t.lean.toList ++ ')' :: ',' :: ' ' ::
      (renderL b ++ ')' :: r))) han (by intro c h; cases h; decide)
    have hp := parseTy_lean t (',' :: ' ' :: (renderL b ++ ')' :: r))
    simp only [renderL, List.cons_append, List.append_assoc, List.nil_append, parse]
    simp only [show isAsciiLetter '(' = false by decide, if_true, Bool.false_eq_true, ite_false]
    cases q <;>
    · simp only [Q.sym, show ('∀' : Char) ≠ '¬' by decide, show ('∃' : Char) ≠ '¬' by decide,
        if_false, true_or, or_true, if_true]
      rw [s1]
      simp only [hp, ih']
      simp
  | apply g a ihg iha =>
    intro hw fuel r hf hr
    obtain ⟨f, rfl⟩ : ∃ f, fuel = f + 1 := ⟨fuel - 1, by simp [sz] at hf; omega⟩
    have iha' := iha hw.2 f (')' :: r) (by simp [sz] at hf; omega) (stop_rp r)
    have ihg' := ihg hw.1 f (' ' :: (renderL a ++ ')' :: r)) (by simp [sz] at hf; omega) (stop_sp _)
    obtain ⟨c, cs, hc, hch⟩ := render_head g hw.1
    obtain ⟨d, ds, hd, hdh⟩ := render_head a hw.2
    obtain ⟨n1, n2, n3, _⟩ := head_ne c hch
    obtain ⟨-, -, -, n4⟩ := head_ne d hdh
    rw [hc, List.cons_append] at ihg'
    simp only [renderL, List.cons_append, List.append_assoc, List.nil_append, parse]
    simp only [show isAsciiLetter '(' = false by decide, if_true, Bool.false_eq_true, ite_false]
    rw [hc]
    simp only [List.cons_append, n1, n2, n3, if_false, Bool.false_eq_true]
    rw [ihg']
    simp only
    rw [hd] at iha' ⊢
    simp only [List.cons_append] at iha' ⊢
    split
    · rename_i o r2 heq
      simp only [List.cons.injEq] at heq
      obtain ⟨rfl, -⟩ := heq
      simp only [n4]
      rw [iha']; rfl
    · rw [iha']; rfl
  | bin op l rr ihl ihr =>
    intro hw fuel r hf hr
    obtain ⟨f, rfl⟩ : ∃ f, fuel = f + 1 := ⟨fuel - 1, by simp [sz] at hf; omega⟩
    have ihr' := ihr hw.2 f (')' :: r) (by simp [sz] at hf; omega) (stop_rp r)
    have ihl' := ihl hw.1 f (' ' :: op.sym :: ' ' :: (renderL rr ++ ')' :: r)) (by simp [sz] at hf; omega) (stop_sp _)
    obtain ⟨c, cs, hc, hch⟩ := render_head l hw.1
    obtain ⟨n1, n2, n3, _⟩ := head_ne c hch
    rw [hc, List.cons_append] at ihl'
    simp only [renderL, List.cons_append, List.append_assoc, List.nil_append, parse]
    simp only [show isAsciiLetter '(' = false by decide, if_true, Bool.false_eq_true, ite_false]
    rw [hc]
    simp only [List.cons_append, n1, n2, n3, if_false, Bool.false_eq_true]
    rw [ihl']
    simp only [opOfChar_sym]
    rw [ihr']; rfl

theorem sz_le_render : ∀ e, sz e ≤ (renderL e).length + 1 := by
  intro e
  induction e with
  | not a ih => simp [sz, renderL]; omega
  | apply g a ihg iha => simp [sz, renderL]; omega
  | quant q n t b ih => simp [sz, renderL]; omega
  | bin op l r ihl ihr => simp [sz, renderL]; omega
  | _ => simp [sz]

/-- Context names admitted by the round trip: `NAME`-valid and not the constants. -/
def GoodVars (vars : List (String × Ty)) : Prop :=
  ∀ p ∈ vars, validName p.1 = true ∧ p.1 ≠ "True" ∧ p.1 ≠ "False"

theorem lookupTy_mem (vars : List (String × Ty)) (n : String) (t : Ty)
    (h : lookupTy vars n = some t) : ∃ p ∈ vars, p.1 = n := by
  unfold lookupTy at h
  cases hf : vars.find? (·.1 == n) with
  | none => simp [hf] at h
  | some p =>
    have hm := List.mem_of_find?_eq_some hf
    have hp := List.find?_some hf
    exact ⟨p, hm, by simpa using hp⟩

theorem check_wf : ∀ (e : Expr) (vars : List (String × Ty)) (d : Nat) (τ : Ty) (s : String),
    GoodVars vars → check vars d e = some (τ, s) → WF e := by
  intro e
  induction e with
  | var n =>
    intro vars d τ s hg h
    simp only [check, gd] at h
    split at h
    · cases h
    · cases hl : lookupTy vars n with
      | none => simp [hl] at h
      | some t =>
        obtain ⟨p, hp, rfl⟩ := lookupTy_mem vars n t hl
        exact hg p hp
  | num => intro _ _ _ _ _ _; trivial
  | tt => intro _ _ _ _ _ _; trivial
  | ff => intro _ _ _ _ _ _; trivial
  | not a ih =>
    intro vars d τ s hg h
    simp only [check, gd] at h
    split at h
    · cases h
    · split at h
      · rename_i s' hc; exact ih _ _ _ _ hg hc
      · cases h
  | apply f a ihf iha =>
    intro vars d τ s hg h
    simp only [check, gd] at h
    split at h
    · cases h
    · split at h
      · rename_i sf sa hf ha; exact ⟨ihf _ _ _ _ hg hf, iha _ _ _ _ hg ha⟩
      · rename_i sf sa hf ha; exact ⟨ihf _ _ _ _ hg hf, iha _ _ _ _ hg ha⟩
      · cases h
  | quant q n t b ih =>
    intro vars d τ s hg h
    simp only [check, gd] at h
    split at h
    · cases h
    · split at h
      · cases h
      · rename_i hcond
        simp only [Bool.or_eq_true, Bool.not_eq_true', not_or, Bool.not_eq_true,
          Option.isSome_eq_false_iff, Option.isNone_iff_eq_none] at hcond
        obtain ⟨⟨hv, hr⟩, -⟩ := hcond
        split at h
        · rename_i sb hb
          refine ⟨by simpa using hv, ih _ _ _ _ ?_ hb⟩
          intro p hp
          simp only [List.mem_cons] at hp
          rcases hp with rfl | hp
          · refine ⟨by simpa using hv, ?_, ?_⟩ <;> (rintro rfl; revert hr; decide)
          · exact hg p hp
        · cases h
  | bin op l r ihl ihr =>
    intro vars d τ s hg h
    simp only [check, gd] at h
    split at h
    · cases h
    · split at h
      · rename_i lt sl rt sr hl hr
        exact ⟨ihl _ _ _ _ hg hl, ihr _ _ _ _ hg hr⟩
      · cases h

/-- **`render_parse_alpha_roundtrip`.**  For every expression accepted by the receiver's
checker over a context of `NAME`-valid variable names, parsing the receiver-rendered Lean
statement string returns exactly the original IR.  In particular the result is alpha
equivalent to the original (same canonical de Bruijn form, quantifier order, binder types and
free names), and the checker reports the same type and the same string for it. -/
theorem render_parse_alpha_roundtrip (vars : List (String × Ty)) (d : Nat) (e : Expr) (τ : Ty)
    (s : String) (hg : GoodVars vars) (h : check vars d e = some (τ, s)) :
    ∃ e', parseString s = some e' ∧ e' = e ∧ canonE (vars.map (·.1)) e' = canonE (vars.map (·.1)) e ∧
      check vars d e' = some (τ, s) := by
  refine ⟨e, ?_, rfl, rfl, h⟩
  have hs := check_render_exact e vars d τ s h
  have hw := check_wf e vars d τ s hg h
  unfold parseString
  have hp := parse_render e hw (s.length + 1) [] (by
    have := sz_le_render e; rw [← hs] at this; simpa using this) (by intro c h; cases h)
  rw [List.append_nil, ← hs] at hp
  rw [hp]

/-- Distinct checker-accepted meanings never share a rendered statement. -/
theorem render_injective_on_checked (vars : List (String × Ty)) (d₁ d₂ : Nat) (e₁ e₂ : Expr)
    (τ₁ τ₂ : Ty) (s : String) (hg : GoodVars vars) (h₁ : check vars d₁ e₁ = some (τ₁, s))
    (h₂ : check vars d₂ e₂ = some (τ₂, s)) : e₁ = e₂ := by
  obtain ⟨_, p₁, rfl, -⟩ := render_parse_alpha_roundtrip vars d₁ e₁ τ₁ s hg h₁
  obtain ⟨_, p₂, rfl, -⟩ := render_parse_alpha_roundtrip vars d₂ e₂ τ₂ s hg h₂
  rw [p₁] at p₂; cases p₂; rfl

end RoundTrip
end PCSMathLanguage
