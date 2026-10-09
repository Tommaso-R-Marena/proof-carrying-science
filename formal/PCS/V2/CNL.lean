import PCS.V2.ExplanationIR
import PCS.V2.SemanticEquiv
import PCS.V2.TextSplit

/-!
# A controlled natural language with an exact grammar (Semantic Intelligence v2)

`PCS-CNL` is a small, fully bracketed, keyword-driven controlled English for the supported
formula fragment, e.g.

    for-every t of-sort Time ( if ( holds revoked of ( var t ) ) then ( not ( ... ) ) )

Unlike free English, its grammar and meaning are exact:

* `Formula.toks` prints a formula as tokens; `parseFormula` parses tokens (fuel-bounded,
  total).  `renderCNL` / `parseCNL` add the word level (space-separated words; a word is a
  keyword exactly when it is in the keyword list).
* `controlled_language_print_parse` — for every formula whose identifiers are CNL-valid (no
  space, not a keyword), `parseCNL (renderCNL φ) = some φ`.
* `controlled_language_parse_print` — for **every** string `s`, if `parseCNL s = some φ` then
  `renderCNL φ = s`: each accepted sentence is the unique rendering of its formula.
* `controlled_language_render_preserves_semantics` — the meaning of a CNL sentence (the
  denotation of its parse) is exactly the meaning of the rendered formula.

Explanation corollaries (`explanation_preserves_quantifier_scope`,
`explanation_preserves_assumptions`, `explanation_preserves_grounded_definitions`,
`explanation_preserves_proof_limitations`) restate what the structural Explanation IR keeps.

Free-form English paraphrases (beginner views, LLM renderings) are **not** in this language
and are not certified.
-/

set_option autoImplicit false

namespace PCS.V2.Semantic.CNL

open PCS.V2.Semantic

/-- Keywords of the controlled language. -/
inductive Kw where
  | var | apply | lp | rp | tru | fls | holds | of | equals | differs | not | both | and
  | either | or | if_ | then_ | forEvery | thereExists | ofSort | unsupported
  deriving Repr, DecidableEq, Inhabited

def Kw.all : List Kw :=
  [.var, .apply, .lp, .rp, .tru, .fls, .holds, .of, .equals, .differs, .not, .both, .and,
   .either, .or, .if_, .then_, .forEvery, .thereExists, .ofSort, .unsupported]

def Kw.word : Kw → String
  | .var => "var" | .apply => "apply" | .lp => "(" | .rp => ")" | .tru => "true"
  | .fls => "false" | .holds => "holds" | .of => "of" | .equals => "equals"
  | .differs => "differs-from" | .not => "not" | .both => "both" | .and => "and"
  | .either => "either" | .or => "or" | .if_ => "if" | .then_ => "then"
  | .forEvery => "for-every" | .thereExists => "there-exists" | .ofSort => "of-sort"
  | .unsupported => "unsupported"

/-- Tokens: keywords and identifiers. -/
inductive Tok where
  | kw (k : Kw)
  | name (s : String)
  deriving Repr, DecidableEq, Inhabited

/-! ## Printing -/

mutual
def Term.toks : Term → List Tok
  | .var x => [.kw .var, .name x]
  | .app f args => [.kw .apply, .name f, .kw .lp] ++ Term.toksList args ++ [.kw .rp]
def Term.toksList : List Term → List Tok
  | [] => []
  | t :: ts => Term.toks t ++ Term.toksList ts
end

def br (l : List Tok) : List Tok := [.kw .lp] ++ l ++ [.kw .rp]

def Formula.toks : Formula → List Tok
  | .tt => [.kw .tru]
  | .ff => [.kw .fls]
  | .pred p args => [.kw .holds, .name p, .kw .of, .kw .lp] ++ Term.toksList args ++ [.kw .rp]
  | .eq a b => [.kw .lp] ++ Term.toks a ++ [.kw .equals] ++ Term.toks b ++ [.kw .rp]
  | .ne a b => [.kw .lp] ++ Term.toks a ++ [.kw .differs] ++ Term.toks b ++ [.kw .rp]
  | .not φ => [.kw .not] ++ br (Formula.toks φ)
  | .and φ ψ => [.kw .both] ++ br (Formula.toks φ) ++ [.kw .and] ++ br (Formula.toks ψ)
  | .or φ ψ => [.kw .either] ++ br (Formula.toks φ) ++ [.kw .or] ++ br (Formula.toks ψ)
  | .imp φ ψ => [.kw .if_] ++ br (Formula.toks φ) ++ [.kw .then_] ++ br (Formula.toks ψ)
  | .quant .all x s φ => [.kw .forEvery, .name x, .kw .ofSort, .name s] ++ br (Formula.toks φ)
  | .quant .ex x s φ => [.kw .thereExists, .name x, .kw .ofSort, .name s] ++ br (Formula.toks φ)
  | .unsupported t => [.kw .unsupported, .name t]

/-! ## Parsing (fuel-bounded, total) -/

mutual
def parseTerm : Nat → List Tok → Option (Term × List Tok)
  | _ + 1, .kw .var :: .name x :: rest => some (.var x, rest)
  | n + 1, .kw .apply :: .name f :: .kw .lp :: rest =>
    match parseTerms n rest with
    | some (args, .kw .rp :: rest') => some (.app f args, rest')
    | _ => none
  | _, _ => none
def parseTerms : Nat → List Tok → Option (List Term × List Tok)
  | 0, _ => none
  | n + 1, toks =>
    match toks with
    | .kw .rp :: _ => some ([], toks)
    | _ =>
      match parseTerm n toks with
      | some (t, rest) =>
        match parseTerms n rest with
        | some (ts, r) => some (t :: ts, r)
        | none => none
      | none => none
end

/-- Expect a bracketed formula. -/
def parseFormula : Nat → List Tok → Option (Formula × List Tok)
  | 0, _ => none
  | n + 1, toks =>
    let brk := fun (toks : List Tok) =>
      match toks with
      | .kw .lp :: rest =>
        match parseFormula n rest with
        | some (φ, .kw .rp :: rest') => some (φ, rest')
        | _ => none
      | _ => none
    match toks with
    | .kw .tru :: rest => some (.tt, rest)
    | .kw .fls :: rest => some (.ff, rest)
    | .kw .holds :: .name p :: .kw .of :: .kw .lp :: rest =>
      match parseTerms n rest with
      | some (args, .kw .rp :: rest') => some (.pred p args, rest')
      | _ => none
    | .kw .lp :: rest =>
      match parseTerm n rest with
      | some (a, .kw .equals :: rest') =>
        match parseTerm n rest' with
        | some (b, .kw .rp :: rest'') => some (.eq a b, rest'')
        | _ => none
      | some (a, .kw .differs :: rest') =>
        match parseTerm n rest' with
        | some (b, .kw .rp :: rest'') => some (.ne a b, rest'')
        | _ => none
      | _ => none
    | .kw .not :: rest => (brk rest).map (fun (φ, r) => (.not φ, r))
    | .kw .both :: rest =>
      match brk rest with
      | some (φ, .kw .and :: rest') => (brk rest').map (fun (ψ, r) => (.and φ ψ, r))
      | _ => none
    | .kw .either :: rest =>
      match brk rest with
      | some (φ, .kw .or :: rest') => (brk rest').map (fun (ψ, r) => (.or φ ψ, r))
      | _ => none
    | .kw .if_ :: rest =>
      match brk rest with
      | some (φ, .kw .then_ :: rest') => (brk rest').map (fun (ψ, r) => (.imp φ ψ, r))
      | _ => none
    | .kw .forEvery :: .name x :: .kw .ofSort :: .name s :: rest =>
      (brk rest).map (fun (φ, r) => (.quant .all x s φ, r))
    | .kw .thereExists :: .name x :: .kw .ofSort :: .name s :: rest =>
      (brk rest).map (fun (φ, r) => (.quant .ex x s φ, r))
    | .kw .unsupported :: .name t :: rest => some (.unsupported t, rest)
    | _ => none

/-! ## Sizes (fuel bounds) -/

mutual
def Term.size : Term → Nat
  | .var _ => 1
  | .app _ args => Term.sizeList args + 1
def Term.sizeList : List Term → Nat
  | [] => 1
  | t :: ts => Term.size t + Term.sizeList ts + 1
end

def Formula.size : Formula → Nat
  | .tt | .ff | .unsupported _ => 1
  | .pred _ args => Term.sizeList args + 1
  | .eq a b | .ne a b => Term.size a + Term.size b + 1
  | .not φ | .quant _ _ _ φ => Formula.size φ + 2
  | .and φ ψ | .or φ ψ | .imp φ ψ => Formula.size φ + Formula.size ψ + 2

/-! ## parse ∘ print = id -/

theorem Term.toks_head (t : Term) : ∃ k rest, Term.toks t = .kw k :: rest ∧ k ≠ .rp := by
  cases t with
  | var x => exact ⟨.var, _, rfl, by decide⟩
  | app f args => exact ⟨.apply, _, rfl, by decide⟩

mutual
theorem parseTerm_toks : ∀ (t : Term) (rest : List Tok) (n : Nat), Term.size t ≤ n →
    parseTerm n (Term.toks t ++ rest) = some (t, rest)
  | .var x, rest, n + 1, _ => by simp [Term.toks, parseTerm]
  | .app f args, rest, n + 1, h => by
    simp only [Term.size] at h
    have ih := parseTerms_toks args rest n (by omega)
    simp only [Term.toks, List.append_assoc, List.cons_append, List.nil_append, parseTerm]
    rw [ih]
  | .var _, _, 0, h => by simp [Term.size] at h
  | .app _ _, _, 0, h => by simp [Term.size] at h
theorem parseTerms_toks : ∀ (ts : List Term) (rest : List Tok) (n : Nat), Term.sizeList ts ≤ n →
    parseTerms n (Term.toksList ts ++ .kw .rp :: rest) = some (ts, .kw .rp :: rest)
  | [], rest, n + 1, _ => by simp [Term.toksList, parseTerms]
  | t :: ts, rest, n + 1, h => by
    simp only [Term.sizeList] at h
    obtain ⟨k, r, hk, hne⟩ := Term.toks_head t
    have h1 := parseTerm_toks t (Term.toksList ts ++ .kw .rp :: rest) n (by omega)
    have h2 := parseTerms_toks ts rest n (by omega)
    simp only [Term.toksList, List.append_assoc]
    unfold parseTerms
    rw [hk]
    simp only [List.cons_append]
    split
    · rename_i heq; simp at heq; exact absurd heq.1 hne
    · rw [← List.cons_append, ← hk, h1]
      simp only [h2]
  | [], _, 0, h => by simp [Term.sizeList] at h
  | _ :: _, _, 0, h => by simp [Term.sizeList] at h
end

theorem parseFormula_toks : ∀ (φ : Formula) (rest : List Tok) (n : Nat), Formula.size φ ≤ n →
    parseFormula n (Formula.toks φ ++ rest) = some (φ, rest) := by
  intro φ
  induction φ with
  | tt => intro rest n h; cases n with | zero => simp [Formula.size] at h | succ n => rfl
  | ff => intro rest n h; cases n with | zero => simp [Formula.size] at h | succ n => rfl
  | unsupported t => intro rest n h; cases n with | zero => simp [Formula.size] at h | succ n => rfl
  | pred p args =>
    intro rest n h
    cases n with
    | zero => simp [Formula.size] at h
    | succ n =>
      simp only [Formula.size] at h
      have := parseTerms_toks args rest n (by omega)
      simp only [Formula.toks, List.append_assoc, List.cons_append, List.nil_append, parseFormula]
      rw [this]
  | eq a b =>
    intro rest n h
    cases n with
    | zero => simp [Formula.size] at h
    | succ n =>
      simp only [Formula.size] at h
      have ha := parseTerm_toks a (.kw .equals :: (Term.toks b ++ .kw .rp :: rest)) n (by omega)
      have hb := parseTerm_toks b (.kw .rp :: rest) n (by omega)
      simp only [Formula.toks, List.append_assoc, List.cons_append, List.nil_append, parseFormula]
      rw [ha]; simp only; rw [hb]
  | ne a b =>
    intro rest n h
    cases n with
    | zero => simp [Formula.size] at h
    | succ n =>
      simp only [Formula.size] at h
      have ha := parseTerm_toks a (.kw .differs :: (Term.toks b ++ .kw .rp :: rest)) n (by omega)
      have hb := parseTerm_toks b (.kw .rp :: rest) n (by omega)
      simp only [Formula.toks, List.append_assoc, List.cons_append, List.nil_append, parseFormula]
      rw [ha]; simp only; rw [hb]
  | not φ ih =>
    intro rest n h
    cases n with
    | zero => simp [Formula.size] at h
    | succ n =>
      simp only [Formula.size] at h
      have := ih (.kw .rp :: rest) n (by omega)
      simp only [Formula.toks, br, List.append_assoc, List.cons_append, List.nil_append, parseFormula]
      rw [this]; rfl
  | and φ ψ ih₁ ih₂ =>
    intro rest n h
    cases n with
    | zero => simp [Formula.size] at h
    | succ n =>
      simp only [Formula.size] at h
      have h1 := ih₁ (.kw .rp :: .kw .and :: (br (Formula.toks ψ) ++ rest)) n (by omega)
      have h2 := ih₂ (.kw .rp :: rest) n (by omega)
      simp only [br, List.append_assoc, List.cons_append, List.nil_append] at h1
      simp only [Formula.toks, br, List.append_assoc, List.cons_append, List.nil_append, parseFormula]
      rw [h1]; simp only; rw [h2]; rfl
  | or φ ψ ih₁ ih₂ =>
    intro rest n h
    cases n with
    | zero => simp [Formula.size] at h
    | succ n =>
      simp only [Formula.size] at h
      have h1 := ih₁ (.kw .rp :: .kw .or :: (br (Formula.toks ψ) ++ rest)) n (by omega)
      have h2 := ih₂ (.kw .rp :: rest) n (by omega)
      simp only [br, List.append_assoc, List.cons_append, List.nil_append] at h1
      simp only [Formula.toks, br, List.append_assoc, List.cons_append, List.nil_append, parseFormula]
      rw [h1]; simp only; rw [h2]; rfl
  | imp φ ψ ih₁ ih₂ =>
    intro rest n h
    cases n with
    | zero => simp [Formula.size] at h
    | succ n =>
      simp only [Formula.size] at h
      have h1 := ih₁ (.kw .rp :: .kw .then_ :: (br (Formula.toks ψ) ++ rest)) n (by omega)
      have h2 := ih₂ (.kw .rp :: rest) n (by omega)
      simp only [br, List.append_assoc, List.cons_append, List.nil_append] at h1
      simp only [Formula.toks, br, List.append_assoc, List.cons_append, List.nil_append, parseFormula]
      rw [h1]; simp only; rw [h2]; rfl
  | quant q x s φ ih =>
    intro rest n h
    cases n with
    | zero => simp [Formula.size] at h
    | succ n =>
      simp only [Formula.size] at h
      have := ih (.kw .rp :: rest) n (by omega)
      cases q <;>
      · simp only [Formula.toks, br, List.append_assoc, List.cons_append, List.nil_append, parseFormula]
        rw [this]; rfl

/-! ## print ∘ parse = id (each accepted token string is a rendering) -/

mutual
theorem parseTerm_inv : ∀ (n : Nat) (toks : List Tok) (t : Term) (rest : List Tok),
    parseTerm n toks = some (t, rest) → toks = Term.toks t ++ rest
  | 0, toks, t, rest, h => by unfold parseTerm at h; cases h
  | n + 1, toks, t, rest, h => by
    unfold parseTerm at h
    split at h
    · cases h; rfl
    · rename_i m fn r heq
      have hm : m = n := by simp at heq; omega
      subst hm
      split at h
      · rename_i args r' hpt
        cases h
        have := parseTerms_inv m r args (.kw .rp :: rest) hpt
        subst this
        simp [Term.toks]
      · cases h
    · cases h
theorem parseTerms_inv : ∀ (n : Nat) (toks : List Tok) (ts : List Term) (rest : List Tok),
    parseTerms n toks = some (ts, rest) → toks = Term.toksList ts ++ rest
  | 0, toks, ts, rest, h => by unfold parseTerms at h; cases h
  | n + 1, toks, ts, rest, h => by
    unfold parseTerms at h
    split at h
    · cases h; rfl
    · split at h
      · rename_i t r ht
        split at h
        · rename_i ts' r' hts
          cases h
          rw [parseTerm_inv n toks t r ht, parseTerms_inv n r ts' rest hts]
          simp [Term.toksList]
        · cases h
      · cases h
end

theorem brk_inv {n : Nat}
    (ih : ∀ toks φ rest, parseFormula n toks = some (φ, rest) → toks = Formula.toks φ ++ rest)
    {toks : List Tok} {φ : Formula} {rest : List Tok}
    (h : (match toks with
      | .kw .lp :: rest =>
        match parseFormula n rest with
        | some (φ, .kw .rp :: rest') => some (φ, rest')
        | _ => none
      | _ => none) = some (φ, rest)) : toks = br (Formula.toks φ) ++ rest := by
  split at h
  · rename_i r
    split at h
    · rename_i ψ r' hp
      cases h
      rw [ih _ _ _ hp]
      simp [br]
    · cases h
  · cases h

theorem parseFormula_inv : ∀ (n : Nat) (toks : List Tok) (φ : Formula) (rest : List Tok),
    parseFormula n toks = some (φ, rest) → toks = Formula.toks φ ++ rest
  | 0, toks, φ, rest, h => by unfold parseFormula at h; cases h
  | n + 1, toks, φ, rest, h => by
    have ih := parseFormula_inv n
    unfold parseFormula at h
    simp only at h
    split at h
    · cases h; rfl
    · cases h; rfl
    · split at h
      · rename_i hp
        cases h
        rw [parseTerms_inv n _ _ _ hp]
        simp [Formula.toks]
      · cases h
    · rename_i r
      split at h
      · rename_i a r' ha
        split at h
        · rename_i b r'' hb
          cases h
          rw [parseTerm_inv n _ _ _ ha, parseTerm_inv n _ _ _ hb]
          simp [Formula.toks]
        · cases h
      · rename_i a r' ha
        split at h
        · rename_i b r'' hb
          cases h
          rw [parseTerm_inv n _ _ _ ha, parseTerm_inv n _ _ _ hb]
          simp [Formula.toks]
        · cases h
      · cases h
    · rename_i r
      obtain ⟨⟨ψ, r'⟩, hb, he⟩ := option_map_eq_some h
      cases he
      rw [brk_inv ih hb]; simp [Formula.toks]
    · rename_i r
      split at h
      · rename_i ψ r' hb
        obtain ⟨⟨χ, r''⟩, hb', he⟩ := option_map_eq_some h
        cases he
        rw [brk_inv ih hb, brk_inv ih hb']; simp [Formula.toks]
      · cases h
    · rename_i r
      split at h
      · rename_i ψ r' hb
        obtain ⟨⟨χ, r''⟩, hb', he⟩ := option_map_eq_some h
        cases he
        rw [brk_inv ih hb, brk_inv ih hb']; simp [Formula.toks]
      · cases h
    · rename_i r
      split at h
      · rename_i ψ r' hb
        obtain ⟨⟨χ, r''⟩, hb', he⟩ := option_map_eq_some h
        cases he
        rw [brk_inv ih hb, brk_inv ih hb']; simp [Formula.toks]
      · cases h
    · rename_i x s r
      obtain ⟨⟨ψ, r'⟩, hb, he⟩ := option_map_eq_some h
      cases he
      rw [brk_inv ih hb]; simp [Formula.toks]
    · rename_i x s r
      obtain ⟨⟨ψ, r'⟩, hb, he⟩ := option_map_eq_some h
      cases he
      rw [brk_inv ih hb]; simp [Formula.toks]
    · cases h; rfl
    · cases h

/-! ## Fuel bound: size ≤ token count -/

mutual
theorem Term.size_le_toks : ∀ t : Term, Term.size t + 1 ≤ (Term.toks t).length
  | .var _ => by simp [Term.size, Term.toks]
  | .app _ args => by
    have := Term.sizeList_le_toks args
    simp [Term.size, Term.toks]; omega
theorem Term.sizeList_le_toks : ∀ ts : List Term, Term.sizeList ts ≤ (Term.toksList ts).length + 1
  | [] => by simp [Term.sizeList, Term.toksList]
  | t :: ts => by
    have h1 := Term.size_le_toks t
    have h2 := Term.sizeList_le_toks ts
    simp [Term.sizeList, Term.toksList]; omega
end

theorem Formula.size_le_toks : ∀ φ : Formula, Formula.size φ ≤ (Formula.toks φ).length := by
  intro φ
  induction φ with
  | tt | ff | unsupported _ => simp [Formula.size, Formula.toks]
  | pred p args =>
    have := Term.sizeList_le_toks args
    simp [Formula.size, Formula.toks]; omega
  | eq a b | ne a b =>
    have := Term.size_le_toks a; have := Term.size_le_toks b
    simp [Formula.size, Formula.toks]; omega
  | not φ ih => simp [Formula.size, Formula.toks, br]; omega
  | and φ ψ ih₁ ih₂ | or φ ψ ih₁ ih₂ | imp φ ψ ih₁ ih₂ =>
    simp [Formula.size, Formula.toks, br]; omega
  | quant q x s φ ih => cases q <;> (simp [Formula.size, Formula.toks, br]; omega)

theorem Formula.toks_ne_nil (φ : Formula) : Formula.toks φ ≠ [] := by
  cases φ with
  | quant q _ _ _ => cases q <;> simp [Formula.toks]
  | _ => simp [Formula.toks]

/-! ## Words

A word is a keyword exactly when it is one of the keyword spellings; every other word is
an identifier.  An identifier is *CNL-valid* when it is not a keyword spelling and contains
no space. -/

def Tok.word : Tok → String
  | .kw k => k.word
  | .name s => s

def wordTok (w : String) : Tok :=
  match Kw.all.find? (fun k => k.word == w) with
  | some k => .kw k
  | none => .name w

def validIdent (s : String) : Bool :=
  !(Kw.all.any (fun k => k.word == s)) && !(s.toList.contains ' ')

def Tok.valid : Tok → Bool
  | .kw _ => true
  | .name s => validIdent s

/-- A formula is expressible in PCS-CNL when all its identifiers are CNL-valid. -/
def _root_.PCS.V2.Semantic.Formula.cnlValid (φ : Formula) : Bool := (Formula.toks φ).all Tok.valid

theorem Kw.wordTok_word : ∀ k : Kw, wordTok k.word = .kw k := by
  intro k; cases k <;> decide

theorem Kw.word_no_space : ∀ k : Kw, ' ' ∉ k.word.toList := by
  intro k; cases k <;> decide

theorem Kw.mem_all : ∀ k : Kw, k ∈ Kw.all := by
  intro k; cases k <;> decide

/-- Every word is the spelling of the token it denotes. -/
theorem word_wordTok (w : String) : (wordTok w).word = w := by
  unfold wordTok
  split
  · rename_i k hk
    have := List.find?_some hk
    simpa [Tok.word] using this
  · rfl

theorem wordTok_word_of_valid : ∀ t : Tok, t.valid = true → wordTok t.word = t
  | .kw k, _ => Kw.wordTok_word k
  | .name s, h => by
    simp only [Tok.valid, validIdent, Bool.and_eq_true, Bool.not_eq_true',
      List.any_eq_false, beq_iff_eq] at h
    unfold wordTok
    have : Kw.all.find? (fun k => k.word == s) = none := by
      rw [List.find?_eq_none]
      intro k hk; simpa using h.1 k hk
    simp only [Tok.word]; rw [this]

theorem word_no_space_of_valid : ∀ t : Tok, t.valid = true → ' ' ∉ t.word.toList
  | .kw k, _ => Kw.word_no_space k
  | .name s, h => by
    simp only [Tok.valid, validIdent, Bool.and_eq_true, Bool.not_eq_true'] at h
    have := h.2
    simpa [Tok.word] using this

/-- The word list of a formula's CNL sentence. -/
def renderWords (φ : Formula) : List String := (Formula.toks φ).map Tok.word

/-- Parse a word list: the whole input must be consumed. -/
def parseWords (ws : List String) : Option Formula :=
  match parseFormula (ws.length + 1) (ws.map wordTok) with
  | some (φ, []) => some φ
  | _ => none

theorem parseWords_renderWords (φ : Formula) (hv : φ.cnlValid = true) :
    parseWords (renderWords φ) = some φ := by
  have hmap : (renderWords φ).map wordTok = Formula.toks φ := by
    unfold renderWords
    rw [List.map_map]
    conv => rhs; rw [← List.map_id (Formula.toks φ)]
    apply List.map_congr_left
    intro t ht
    exact wordTok_word_of_valid t (List.all_eq_true.mp hv t ht)
  unfold parseWords
  rw [hmap]
  have hs := Formula.size_le_toks φ
  have := parseFormula_toks φ [] ((renderWords φ).length + 1)
    (by simp [renderWords]; omega)
  rw [List.append_nil] at this
  rw [this]

theorem renderWords_parseWords (ws : List String) (φ : Formula)
    (h : parseWords ws = some φ) : renderWords φ = ws := by
  unfold parseWords at h
  split at h
  · rename_i hp
    cases h
    have := parseFormula_inv _ _ _ _ hp
    rw [List.append_nil] at this
    unfold renderWords
    rw [← this, List.map_map]
    conv => rhs; rw [← List.map_id ws]
    apply List.map_congr_left
    intro w _
    exact word_wordTok w
  · cases h

/-! ## Sentences (strings of words separated by single spaces) -/

/-- **The literal CNL rendering** of a formula. -/
def renderCNL (φ : Formula) : String :=
  String.ofList (TextSplit.joinWith ' ' ((renderWords φ).map String.toList))

/-- **The exact CNL parser.** -/
def parseCNL (s : String) : Option Formula :=
  parseWords ((TextSplit.splitAt ' ' s.toList).map String.ofList)

/-- **print ∘ parse**: every CNL-valid formula is recovered from its rendering. -/
theorem controlled_language_print_parse (φ : Formula) (hv : φ.cnlValid = true) :
    parseCNL (renderCNL φ) = some φ := by
  unfold parseCNL renderCNL
  rw [String.toList_ofList]
  have hsplit : TextSplit.splitAt ' ' (TextSplit.joinWith ' ' ((renderWords φ).map String.toList))
      = (renderWords φ).map String.toList := by
    apply TextSplit.splitAt_complete
    refine ⟨?_, rfl, ?_⟩
    · simp [renderWords, Formula.toks_ne_nil]
    · intro p hp
      simp only [renderWords, List.map_map, List.mem_map, Function.comp] at hp
      obtain ⟨t, ht, rfl⟩ := hp
      exact word_no_space_of_valid t (List.all_eq_true.mp hv t ht)
  rw [hsplit, List.map_map]
  have : (String.ofList ∘ String.toList) = id := by funext x; simp
  rw [this, List.map_id]
  exact parseWords_renderWords φ hv

/-- **parse ∘ print**: for *every* string, an accepted sentence is exactly the rendering of
    the formula it parses to (no two sentences parse to the same formula; no hidden slack). -/
theorem controlled_language_parse_print (s : String) (φ : Formula) (h : parseCNL s = some φ) :
    renderCNL φ = s := by
  unfold parseCNL at h
  have hw := renderWords_parseWords _ _ h
  unfold renderCNL
  rw [hw, List.map_map]
  have : (String.toList ∘ String.ofList) = id := by funext x; simp
  rw [this, List.map_id, TextSplit.splitAt_join, String.ofList_toList]

/-- Meaning of a CNL sentence: the denotation of its unique parse (`False` if it does not
    parse — a sentence outside the language asserts nothing PCS certifies). -/
def cnlMeaning (M : Model) (ρ : String → M.Dom) (s : String) : Prop :=
  match parseCNL s with
  | some φ => Formula.denote M ρ φ
  | none => False

/-- **Rendering preserves semantics**: the sentence PCS prints for a CNL-valid formula
    means exactly what the formula means, in every model and valuation. -/
theorem controlled_language_render_preserves_semantics (φ : Formula) (hv : φ.cnlValid = true)
    (M : Model) (ρ : String → M.Dom) : cnlMeaning M ρ (renderCNL φ) ↔ Formula.denote M ρ φ := by
  unfold cnlMeaning
  rw [controlled_language_print_parse φ hv]

/-- Two CNL-valid formulas with the same rendering are identical (rendering is injective). -/
theorem renderCNL_injective (φ ψ : Formula) (hφ : φ.cnlValid = true) (hψ : ψ.cnlValid = true)
    (h : renderCNL φ = renderCNL ψ) : φ = ψ := by
  have h1 := controlled_language_print_parse φ hφ
  rw [h, controlled_language_print_parse ψ hψ] at h1
  exact (Option.some.inj h1).symm


/-! ## Explanation corollaries -/

/-- The explanation's conclusion tree is the claim's conclusion, so its literal CNL sentence
    is exactly the claim's: quantifier kinds, order and scope are preserved verbatim. -/
theorem explanation_preserves_quantifier_scope (R : Registry) (c : SemanticClaim) :
    (toExplanation R c).conclusion.toFormula = c.conclusion ∧
    renderCNL (toExplanation R c).conclusion.toFormula = renderCNL c.conclusion ∧
    (toExplanation R c).quantifiers = c.quantifiers := by
  have h : (toExplanation R c).conclusion.toFormula = c.conclusion :=
    toNode_roundtrip R c.conclusion
  exact ⟨h, by rw [h], rfl⟩

/-- Assumptions are kept, in order, as separate trees (never merged into the conclusion). -/
theorem explanation_preserves_assumptions (R : Registry) (c : SemanticClaim) :
    (toExplanation R c).assumptions.map ExplNode.toFormula = c.assumptions ∧
    (toExplanation R c).variables = c.params := by
  have h := congrArg SemanticClaim.assumptions (explanation_roundtrip R c)
  exact ⟨h, rfl⟩

/-- Referenced definitions are exactly unique registry resolutions of the claim's symbols. -/
theorem explanation_preserves_grounded_definitions (R : Registry) (c : SemanticClaim) :
    ∀ e ∈ (toExplanation R c).references, e.id ∈ c.symbols ∧ R.resolve e.id = some e ∧
      e ∈ R.symbols :=
  explanation_references_grounded R c

/-- Every explanation carries the fixed trust boundary and the fixed list of what is **not**
    established (intent, uniqueness of English meaning, prose certification, empirical truth,
    model correctness); a renderer cannot drop them without changing the Explanation IR. -/
theorem explanation_preserves_proof_limitations (R : Registry) (c : SemanticClaim) :
    (toExplanation R c).trustBoundary = trustBoundaryStatement ∧
    (toExplanation R c).notEstablished = notEstablishedStatement ∧
    (toExplanation R c).notEstablished.length = 5 :=
  ⟨rfl, rfl, rfl⟩


end PCS.V2.Semantic.CNL
