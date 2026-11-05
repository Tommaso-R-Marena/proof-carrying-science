import PCS.V2.Chemistry
import PCS.V2.TextSplit

/-!
# A verified replay executor for `unit_compatible` evidence

`pcs/checks/units.py::units_compatible(left, right)` parses two unit expressions over
the fixed PCS unit table `_BASE` and reports `PASS` iff they have the same physical
dimension (mass `M`, length `L`, time `T`, amount `N`).  The SI scale factors it also
computes are diagnostic only and do not influence the outcome.

This file gives

* a **declarative** semantics: the grammar and dimension of a unit expression as
  inductive relations (`ExpDenotes`, `TermDenotes`, `ProductDenotes`, `ExprDenotes`)
  over the table `baseTable`, and `UnitCompatible a b` (both denote the same
  dimension);
* an **executable** parser/checker (`parseUnit`, `unitCompatibleB`);
* `parseUnit_sound`, `parseUnit_complete`: the parser decides the declarative semantics;
* `exprDenotes_unique`: a unit expression has at most one dimension;
* `unitCompatibleB_iff`: `unitCompatibleB a b = true ↔ UnitCompatible a b`;
* `unitExec_sound`: the Lean replay of a `unit_compatible` evidence object reports
  `PASS` only if its two committed unit strings are dimensionally compatible.

Accepted grammar (after deleting U+0020 spaces, as production does):
`expr := product ('/' product)*`, `product := '' | term ('*' term)*`,
`term := name ('^' '-'? digit+)?`, `name := [A-Za-z0-9]+` and a key of the table,
`digit := [0-9]` (ASCII only).  See counterexamples 5–8 in
`PCS_FRONTIER_FORMALIZATION_REPORT.md` for the production behaviours that were
repaired to coincide with this grammar (Unicode digits, trailing newline, float
overflow/underflow in the diagnostic scale).
-/

namespace PCS.V2.Units

open PCS PCS.V2.Json PCS.V2.Common PCS.V2.Package PCS.V2.Replay PCS.V2.TextSplit
open PCS.V2.Chemistry (isUp isLo isDig digitsVal checkSpec)

/-! ## Dimensions -/

/-- A physical dimension `M^m L^l T^t N^n`. -/
structure Dim where
  M : Int
  L : Int
  T : Int
  N : Int
  deriving DecidableEq, Repr

namespace Dim
def zero : Dim := ⟨0, 0, 0, 0⟩
def add (a b : Dim) : Dim := ⟨a.M + b.M, a.L + b.L, a.T + b.T, a.N + b.N⟩
def sub (a b : Dim) : Dim := ⟨a.M - b.M, a.L - b.L, a.T - b.T, a.N - b.N⟩
/-- Raising a unit to the integer power `e` multiplies its dimension by `e`. -/
def smul (e : Int) (a : Dim) : Dim := ⟨e * a.M, e * a.L, e * a.T, e * a.N⟩
/-- The dimension of a product of units. -/
def sum : List Dim → Dim
  | [] => zero
  | d :: ds => add d (sum ds)
end Dim

/-- The PCS unit table `_BASE` (symbol ↦ dimension). -/
def baseTable : List (String × Dim) :=
  [("1", ⟨0, 0, 0, 0⟩),
   ("kg", ⟨1, 0, 0, 0⟩), ("g", ⟨1, 0, 0, 0⟩), ("mg", ⟨1, 0, 0, 0⟩), ("ug", ⟨1, 0, 0, 0⟩),
   ("m", ⟨0, 1, 0, 0⟩), ("cm", ⟨0, 1, 0, 0⟩),
   ("L", ⟨0, 3, 0, 0⟩), ("mL", ⟨0, 3, 0, 0⟩), ("uL", ⟨0, 3, 0, 0⟩),
   ("s", ⟨0, 0, 1, 0⟩), ("min", ⟨0, 0, 1, 0⟩), ("h", ⟨0, 0, 1, 0⟩),
   ("mol", ⟨0, 0, 0, 1⟩), ("mmol", ⟨0, 0, 0, 1⟩), ("umol", ⟨0, 0, 0, 1⟩),
   ("M", ⟨0, -3, 0, 1⟩), ("mM", ⟨0, -3, 0, 1⟩)]

theorem baseTable_keys_nodup : (baseTable.map (·.1)).Nodup := by decide

def baseDim (name : String) : Option Dim := (baseTable.find? (·.1 == name)).map (·.2)

theorem baseDim_sound {n : String} {d : Dim} (h : baseDim n = some d) : (n, d) ∈ baseTable := by
  unfold baseDim at h
  cases hf : baseTable.find? (·.1 == n) with
  | none => rw [hf] at h; cases h
  | some p =>
    rw [hf] at h
    simp only [Option.map_some, Option.some.injEq] at h
    have hm := List.mem_of_find?_eq_some hf
    have hk := List.find?_some hf
    simp only [beq_iff_eq] at hk
    obtain ⟨k, v⟩ := p
    simp only at hk h
    subst hk h
    exact hm

theorem baseDim_complete {n : String} {d : Dim} (h : (n, d) ∈ baseTable) : baseDim n = some d := by
  unfold baseTable at h
  simp only [List.mem_cons, Prod.mk.injEq, List.not_mem_nil, or_false] at h
  rcases h with ⟨rfl, rfl⟩ | ⟨rfl, rfl⟩ | ⟨rfl, rfl⟩ | ⟨rfl, rfl⟩ | ⟨rfl, rfl⟩ | ⟨rfl, rfl⟩ |
    ⟨rfl, rfl⟩ | ⟨rfl, rfl⟩ | ⟨rfl, rfl⟩ | ⟨rfl, rfl⟩ | ⟨rfl, rfl⟩ | ⟨rfl, rfl⟩ | ⟨rfl, rfl⟩ |
    ⟨rfl, rfl⟩ | ⟨rfl, rfl⟩ | ⟨rfl, rfl⟩ | ⟨rfl, rfl⟩ | ⟨rfl, rfl⟩ <;> decide

theorem baseDim_iff (n : String) (d : Dim) : baseDim n = some d ↔ (n, d) ∈ baseTable :=
  ⟨baseDim_sound, baseDim_complete⟩

/-! ## Declarative grammar and dimension -/

/-- ASCII `[A-Za-z0-9]`. -/
def isNameChar (c : Char) : Bool := isUp c || isLo c || isDig c

/-- `-?[0-9]+` denoting the integer exponent `e`. -/
inductive ExpDenotes : List Char → Int → Prop
  | pos {ds : List Char} : ds ≠ [] → (∀ d ∈ ds, isDig d = true) →
      ExpDenotes ds (digitsVal ds : Int)
  | neg {ds : List Char} : ds ≠ [] → (∀ d ∈ ds, isDig d = true) →
      ExpDenotes ('-' :: ds) (-(digitsVal ds : Int))

/-- A term `name` or `name^exp` denoting the table dimension of `name`, times `exp`. -/
inductive TermDenotes : List Char → Dim → Prop
  | plain {name : List Char} {d : Dim} : name ≠ [] → (∀ c ∈ name, isNameChar c = true) →
      (String.ofList name, d) ∈ baseTable → TermDenotes name d
  | pow {name es : List Char} {d : Dim} {e : Int} : name ≠ [] →
      (∀ c ∈ name, isNameChar c = true) → (String.ofList name, d) ∈ baseTable →
      ExpDenotes es e → TermDenotes (name ++ '^' :: es) (Dim.smul e d)

/-- A product: empty (dimensionless) or `*`-separated terms whose dimensions add. -/
inductive ProductDenotes : List Char → Dim → Prop
  | empty : ProductDenotes [] Dim.zero
  | terms {s : List Char} {parts : List (List Char)} {ds : List Dim} : s ≠ [] →
      SplitBy '*' s parts → Pointwise TermDenotes parts ds → ProductDenotes s (Dim.sum ds)

/-- A unit expression `num / den₁ / den₂ / …` (spaces removed). -/
def ExprDenotes (s : List Char) (d : Dim) : Prop :=
  ∃ p ps dn dds, SplitBy '/' (s.filter (· != ' ')) (p :: ps) ∧ ProductDenotes p dn ∧
    Pointwise ProductDenotes ps dds ∧ d = Dim.sub dn (Dim.sum dds)

/-- **Scientific meaning of `unit_compatible`**: both unit expressions are well formed and
    denote the same physical dimension. -/
def UnitCompatible (a b : String) : Prop :=
  ∃ d, ExprDenotes a.toList d ∧ ExprDenotes b.toList d

/-! ## Executable parser -/

def parseExp : List Char → Option Int
  | '-' :: ds => if ds ≠ [] ∧ ds.all isDig = true then some (-(digitsVal ds : Int)) else none
  | ds => if ds ≠ [] ∧ ds.all isDig = true then some (digitsVal ds : Int) else none

def nameOK (name : List Char) : Bool := !name.isEmpty && name.all isNameChar

def parseTerm (t : List Char) : Option Dim :=
  match splitAt '^' t with
  | [name] => if nameOK name then baseDim (String.ofList name) else none
  | [name, es] =>
    if nameOK name then
      match baseDim (String.ofList name), parseExp es with
      | some d, some e => some (Dim.smul e d)
      | _, _ => none
    else none
  | _ => none

def parseProduct (s : List Char) : Option Dim :=
  if s = [] then some Dim.zero else (mapOpt parseTerm (splitAt '*' s)).map Dim.sum

def parseUnit (s : List Char) : Option Dim :=
  match splitAt '/' (s.filter (· != ' ')) with
  | [] => none
  | p :: ps =>
    match parseProduct p, mapOpt parseProduct ps with
    | some dn, some dds => some (Dim.sub dn (Dim.sum dds))
    | _, _ => none

/-- The executable `unit_compatible` decision. -/
def unitCompatibleB (a b : String) : Bool :=
  match parseUnit a.toList, parseUnit b.toList with
  | some x, some y => x == y
  | _, _ => false

/-! ## Parser correctness -/

theorem nameOK_iff (name : List Char) :
    nameOK name = true ↔ name ≠ [] ∧ ∀ c ∈ name, isNameChar c = true := by
  unfold nameOK
  cases name <;> simp

theorem parseExp_sound {es : List Char} {e : Int} (h : parseExp es = some e) : ExpDenotes es e := by
  unfold parseExp at h
  split at h
  · rename_i ds
    split at h
    · rename_i hc
      cases h
      exact ExpDenotes.neg hc.1 (by simpa using hc.2)
    · cases h
  · split at h
    · rename_i hc
      cases h
      exact ExpDenotes.pos hc.1 (by simpa using hc.2)
    · cases h

theorem minus_not_dig : isDig '-' = false := by decide

theorem parseExp_complete_pos : ∀ (ds : List Char), ds ≠ [] → (∀ d ∈ ds, isDig d = true) →
    parseExp ds = some (digitsVal ds : Int)
  | [], hne, _ => absurd rfl hne
  | c :: cs, _, hds => by
    have hc : c ≠ '-' := by
      intro e; subst e; have := hds '-' (by simp); rw [minus_not_dig] at this; cases this
    unfold parseExp
    split
    · rename_i ds' heq
      simp only [List.cons.injEq] at heq
      exact absurd heq.1 hc
    · rw [if_pos ⟨by simp, by simpa using hds⟩]

theorem parseExp_complete {es : List Char} {e : Int} (h : ExpDenotes es e) : parseExp es = some e := by
  cases h with
  | neg hne hds =>
    simp only [parseExp]
    rw [if_pos ⟨hne, by simpa using hds⟩]
  | pos hne hds => exact parseExp_complete_pos _ hne hds

theorem no_caret_of_name {name : List Char} (h : ∀ c ∈ name, isNameChar c = true) : '^' ∉ name := by
  intro hm
  have := h '^' hm
  simp [isNameChar, isUp, isLo, isDig] at this

theorem no_caret_of_exp {es : List Char} {e : Int} (h : ExpDenotes es e) : '^' ∉ es := by
  cases h with
  | pos _ hds =>
    intro hm; have := hds '^' hm; simp [isDig] at this
  | neg _ hds =>
    intro hm
    simp only [List.mem_cons] at hm
    rcases hm with hm | hm
    · cases hm
    · have := hds '^' hm; simp [isDig] at this

theorem parseTerm_sound {t : List Char} {d : Dim} (h : parseTerm t = some d) : TermDenotes t d := by
  have hj := splitAt_join '^' t
  unfold parseTerm at h
  split at h
  · rename_i name hs
    split at h
    · rename_i hn
      rw [hs] at hj
      simp only [joinWith] at hj
      subst hj
      obtain ⟨h1, h2⟩ := (nameOK_iff name).1 hn
      exact TermDenotes.plain h1 h2 (baseDim_sound h)
    · cases h
  · rename_i name es hs
    split at h
    · rename_i hn
      rw [hs] at hj
      simp only [joinWith] at hj
      subst hj
      obtain ⟨h1, h2⟩ := (nameOK_iff name).1 hn
      split at h
      · rename_i d' e hd he
        cases h
        exact TermDenotes.pow h1 h2 (baseDim_sound hd) (parseExp_sound he)
      · cases h
    · cases h
  · cases h

theorem parseTerm_complete {t : List Char} {d : Dim} (h : TermDenotes t d) : parseTerm t = some d := by
  cases h with
  | plain h1 h2 h3 =>
    unfold parseTerm
    rw [splitAt_of_no_sep '^' _ (no_caret_of_name h2)]
    simp only
    rw [if_pos ((nameOK_iff _).2 ⟨h1, h2⟩), baseDim_complete h3]
  | pow h1 h2 h3 h4 =>
    unfold parseTerm
    rw [splitAt_append_sep '^' _ _ (no_caret_of_name h2),
      splitAt_of_no_sep '^' _ (no_caret_of_exp h4)]
    simp only
    rw [if_pos ((nameOK_iff _).2 ⟨h1, h2⟩), baseDim_complete h3, parseExp_complete h4]

theorem parseTerms_sound {parts : List (List Char)} {ds : List Dim}
    (h : mapOpt parseTerm parts = some ds) : Pointwise TermDenotes parts ds :=
  Pointwise.imp (fun _ _ hx => parseTerm_sound hx) (mapOpt_pointwise.1 h)

theorem parseTerms_complete {parts : List (List Char)} {ds : List Dim}
    (h : Pointwise TermDenotes parts ds) : mapOpt parseTerm parts = some ds :=
  mapOpt_pointwise.2 (Pointwise.imp (fun _ _ hx => parseTerm_complete hx) h)

theorem parseProduct_sound {s : List Char} {d : Dim} (h : parseProduct s = some d) :
    ProductDenotes s d := by
  unfold parseProduct at h
  split at h
  · rename_i hs
    cases h; subst hs; exact ProductDenotes.empty
  · rename_i hs
    cases hm : mapOpt parseTerm (splitAt '*' s) with
    | none => rw [hm] at h; cases h
    | some ds =>
      rw [hm] at h
      cases h
      exact ProductDenotes.terms hs (splitAt_sound '*' s) (parseTerms_sound hm)

theorem parseProduct_complete {s : List Char} {d : Dim} (h : ProductDenotes s d) :
    parseProduct s = some d := by
  cases h with
  | empty => rfl
  | terms hs hsplit hpw =>
    unfold parseProduct
    rw [if_neg hs, splitAt_complete '*' _ _ hsplit, parseTerms_complete hpw]
    rfl

theorem parseProducts_sound {ps : List (List Char)} {ds : List Dim}
    (h : mapOpt parseProduct ps = some ds) : Pointwise ProductDenotes ps ds :=
  Pointwise.imp (fun _ _ hx => parseProduct_sound hx) (mapOpt_pointwise.1 h)

theorem parseProducts_complete {ps : List (List Char)} {ds : List Dim}
    (h : Pointwise ProductDenotes ps ds) : mapOpt parseProduct ps = some ds :=
  mapOpt_pointwise.2 (Pointwise.imp (fun _ _ hx => parseProduct_complete hx) h)

/-- The executable parser only returns dimensions the declarative semantics assigns. -/
theorem parseUnit_sound {s : List Char} {d : Dim} (h : parseUnit s = some d) : ExprDenotes s d := by
  have hsp := splitAt_sound '/' (s.filter (· != ' '))
  unfold parseUnit at h
  split at h
  · cases h
  · rename_i p ps hs
    rw [hs] at hsp
    split at h
    · rename_i dn dds hdn hdds
      cases h
      exact ⟨p, ps, dn, dds, hsp, parseProduct_sound hdn, parseProducts_sound hdds, rfl⟩
    · cases h

/-- The executable parser finds the dimension of every well-formed unit expression. -/
theorem parseUnit_complete {s : List Char} {d : Dim} (h : ExprDenotes s d) : parseUnit s = some d := by
  obtain ⟨p, ps, dn, dds, hsp, hdn, hdds, rfl⟩ := h
  unfold parseUnit
  rw [splitAt_complete '/' _ _ hsp]
  simp only
  rw [parseProduct_complete hdn, parseProducts_complete hdds]

theorem parseUnit_iff (s : List Char) (d : Dim) : parseUnit s = some d ↔ ExprDenotes s d :=
  ⟨parseUnit_sound, parseUnit_complete⟩

/-- A unit expression has at most one dimension: its meaning is unambiguous. -/
theorem exprDenotes_unique {s : List Char} {d₁ d₂ : Dim}
    (h₁ : ExprDenotes s d₁) (h₂ : ExprDenotes s d₂) : d₁ = d₂ := by
  have := (parseUnit_complete h₁).symm.trans (parseUnit_complete h₂)
  cases this; rfl

/-- **The executable checker decides dimensional compatibility.** -/
theorem unitCompatibleB_iff (a b : String) : unitCompatibleB a b = true ↔ UnitCompatible a b := by
  unfold unitCompatibleB UnitCompatible
  constructor
  · intro h
    split at h
    · rename_i x y hx hy
      have hxy : x = y := by simpa using h
      subst hxy
      exact ⟨x, parseUnit_sound hx, parseUnit_sound hy⟩
    · cases h
  · rintro ⟨d, ha, hb⟩
    rw [parseUnit_complete ha, parseUnit_complete hb]
    simp

/-! ## The `unit_compatible` evidence object -/

def isUnitCheck (ev : JVal) : Bool :=
  match checkSpec ev with
  | some sp => decide (strField sp "type" = some "unit_compatible")
  | none => false

def unitSpec (ev : JVal) : Option (String × String) :=
  match checkSpec ev with
  | some sp =>
    match field sp "left_unit", field sp "right_unit" with
    | some (.str l), some (.str r) => some (l, r)
    | _, _ => none
  | none => none

/-- **Scientific predicate of a `unit_compatible` item**: its two committed unit strings
    denote the same physical dimension. -/
def UnitHolds (ev : JVal) : Prop :=
  ∃ sp l r, checkSpec ev = some sp ∧ strField sp "type" = some "unit_compatible" ∧
    field sp "left_unit" = some (.str l) ∧ field sp "right_unit" = some (.str r) ∧
    UnitCompatible l r

/-- Lean replay of a `unit_compatible` item (malformed specs fail, as in production). -/
def unitRun (req : ReplayRequest) : Observation :=
  match unitSpec req.evidence with
  | some (l, r) => ⟨.computationalTest, if unitCompatibleB l r then .pass else .fail⟩
  | none => ⟨.computationalTest, .fail⟩

theorem unitRun_sound (req : ReplayRequest) (hc : isUnitCheck req.evidence = true)
    (hp : (unitRun req).outcome = .pass) : UnitHolds req.evidence := by
  unfold unitRun at hp
  unfold isUnitCheck at hc
  split at hp
  · rename_i l r hspec
    unfold unitSpec at hspec
    split at hspec
    · rename_i sp hsp
      rw [hsp] at hc
      simp only [decide_eq_true_eq] at hc
      split at hspec
      · rename_i l' r' hl hr
        cases hspec
        have hb : unitCompatibleB l r = true := by
          cases hh : unitCompatibleB l r
          · rw [hh] at hp; cases hp
          · rfl
        exact ⟨sp, l, r, hsp, hc, hl, hr, (unitCompatibleB_iff l r).1 hb⟩
      · cases hspec
    · cases hspec
  · cases hp

end PCS.V2.Units
