import PCS.V2.Units

/-!
# A verified replay executor for `csv_disjoint` evidence (strict CSV subset)

`csv_disjoint` asks whether the key column `key` has disjoint value sets in two committed
CSV artifacts.  Matching every behaviour of Python's `csv.DictReader` (quoting dialects,
embedded newlines, short/long rows filled with `None`/`restkey`, duplicate header names
resolved last-wins, lone-CR line ends, NUL handling, the 131072-character field limit)
would put an unspecified parser into the trusted base.  PCS therefore fixes a **strict,
fail-closed high-assurance CSV subset** (`CsvTable`), implemented identically by the Lean
authority (`parseCsv`) and by production (`pcs/checks/splits.py`):

* the bytes are valid UTF-8 (Python decodes with `encoding="utf-8"`);
* no `"` (0x22) and no NUL (0x00) byte occurs, so no quoting rule can apply;
* lines are separated by LF; a line may end in one CR (CRLF line ends); no other CR;
* the first line is the non-empty header; empty lines after it are ignored (as
  `DictReader` does);
* fields are separated by `,` with no unquoting or trimming;
* header names are pairwise distinct, every data row has exactly as many fields as the
  header, and every field is at most 131072 bytes.

Files outside the subset make the check `FAIL` (never `PASS`).  Inside the subset the
table is exactly what `csv.DictReader` produces (differentially tested in
`tests/test_frontier_tcb.py`).

Proved here:

* `parseCsv_sound` / `parseCsv_complete`: the executable parser decides `CsvTable`;
* `csvTable_unique`: a byte string denotes at most one table;
* `csvDisjointB_iff`: the executable check decides `CsvDisjoint`;
* `csvRun_sound`: a `PASS` for a `csv_disjoint` evidence object means the two committed
  artifacts (looked up by the ids named in the evidence) are strict CSV tables with the
  key column and disjoint key sets.
-/

namespace PCS.V2.Csv

open PCS PCS.V2.Json PCS.V2.Common PCS.V2.Package PCS.V2.Replay PCS.V2.TextSplit PCS.V2.Index
open PCS.V2.Chemistry (checkSpec)

abbrev Bytes := List UInt8

def LF : UInt8 := 10
def CR : UInt8 := 13
def COMMA : UInt8 := 44
def QUOTE : UInt8 := 34
def NUL : UInt8 := 0

/-- Python's default `csv.field_size_limit()`. -/
def maxField : Nat := 131072

def ValidUTF8 (b : Bytes) : Prop := ByteArray.IsValidUTF8 ⟨b.toArray⟩

/-! ## Declarative table semantics -/

/-- A raw line `rl` is the line `l`, optionally followed by one CR; `l` has no CR. -/
def LineTerm (rl l : Bytes) : Prop := (rl = l ∨ rl = l ++ [CR]) ∧ CR ∉ l

/-- **The strict CSV table denoted by the bytes `b`**: header fields and data rows. -/
structure CsvTable (b : Bytes) (header : List Bytes) (rows : List (List Bytes)) : Prop where
  utf8 : ValidUTF8 b
  noQuote : QUOTE ∉ b
  noNul : NUL ∉ b
  lines : ∃ rawLines hl rest, SplitBy LF b rawLines ∧ Pointwise LineTerm rawLines (hl :: rest) ∧
    hl ≠ [] ∧ SplitBy COMMA hl header ∧
    Pointwise (fun l r => SplitBy COMMA l r) (rest.filter (fun l => !l.isEmpty)) rows
  headerDistinct : header.Nodup
  rectangular : ∀ r ∈ rows, r.length = header.length
  fieldLimit : ∀ f ∈ header ++ rows.flatten, f.length ≤ maxField

/-- **Scientific meaning of `csv_disjoint`**: both artifacts are strict CSV tables that
    have the key column, and no key value occurs in both. -/
def CsvDisjoint (left right : Bytes) (key : Bytes) : Prop :=
  ∃ (hL : List Bytes) (rL : List (List Bytes)) (iL : Nat) (hR : List Bytes)
    (rR : List (List Bytes)) (iR : Nat), CsvTable left hL rL ∧ CsvTable right hR rR ∧
    hL[iL]? = some key ∧ hR[iR]? = some key ∧
    ∀ r₁ ∈ rL, ∀ r₂ ∈ rR, r₁[iL]? ≠ r₂[iR]?

/-! ## Executable parser -/

def stripCR (rl : Bytes) : Option Bytes :=
  if rl.getLast? = some CR then
    if CR ∈ rl.dropLast then none else some rl.dropLast
  else if CR ∈ rl then none else some rl

def parseCsv (b : Bytes) : Option (List Bytes × List (List Bytes)) :=
  if ByteArray.validateUTF8 ⟨b.toArray⟩ = true ∧ QUOTE ∉ b ∧ NUL ∉ b then
    match mapOpt stripCR (splitAt LF b) with
    | some (hl :: rest) =>
      if hl = [] then none
      else
        let header := splitAt COMMA hl
        let rows := (rest.filter (fun l => !l.isEmpty)).map (splitAt COMMA)
        if header.Nodup ∧ (∀ r ∈ rows, r.length = header.length) ∧
            (∀ f ∈ header ++ rows.flatten, f.length ≤ maxField) then
          some (header, rows)
        else none
    | _ => none
  else none

def indexOf (k : Bytes) : List Bytes → Option Nat
  | [] => none
  | x :: xs => if x = k then some 0 else (indexOf k xs).map (· + 1)

def keysAt (rows : List (List Bytes)) (i : Nat) : List Bytes := rows.filterMap (·[i]?)

def csvDisjointB (left right key : Bytes) : Bool :=
  match parseCsv left, parseCsv right with
  | some (hL, rL), some (hR, rR) =>
    match indexOf key hL, indexOf key hR with
    | some iL, some iR =>
      let kR := keysAt rR iR
      (keysAt rL iL).all (fun k => !kR.contains k)
    | _, _ => false
  | _, _ => false

/-! ## Parser correctness -/

theorem stripCR_sound {rl l : Bytes} (h : stripCR rl = some l) : LineTerm rl l := by
  unfold stripCR at h
  split at h
  · rename_i hl
    split at h
    · cases h
    · rename_i hcr
      cases h
      refine ⟨Or.inr ?_, hcr⟩
      have hne : rl ≠ [] := by intro e; subst e; simp at hl
      have hlast : rl.getLast hne = CR := by
        rw [List.getLast?_eq_some_getLast hne] at hl; exact Option.some.inj hl
      have := List.dropLast_concat_getLast hne
      rw [hlast] at this
      exact this.symm
  · split at h
    · cases h
    · rename_i _ hcr
      cases h
      exact ⟨Or.inl rfl, hcr⟩

theorem stripCR_complete {rl l : Bytes} (h : LineTerm rl l) : stripCR rl = some l := by
  obtain ⟨h1 | h1, hcr⟩ := h
  · rw [h1]
    unfold stripCR
    have : l.getLast? ≠ some CR := by
      intro e
      exact hcr (List.mem_of_getLast? e)
    rw [if_neg this, if_neg hcr]
  · rw [h1]
    unfold stripCR
    rw [if_pos (by simp), List.dropLast_concat, if_neg hcr]

theorem mapOpt_stripCR_iff {raw lines : List Bytes} :
    mapOpt stripCR raw = some lines ↔ Pointwise LineTerm raw lines := by
  rw [mapOpt_pointwise]
  exact ⟨Pointwise.imp (fun _ _ h => stripCR_sound h),
    Pointwise.imp (fun _ _ h => stripCR_complete h)⟩

theorem splitRows_iff (ls : List Bytes) (rows : List (List Bytes)) :
    ls.map (splitAt COMMA) = rows ↔ Pointwise (fun l r => SplitBy COMMA l r) ls rows := by
  induction ls generalizing rows with
  | nil =>
    constructor
    · intro h; subst h; exact Pointwise.nil
    · intro h; cases h; rfl
  | cons l ls ih =>
    constructor
    · intro h
      subst h
      exact Pointwise.cons (splitAt_sound COMMA l) ((ih _).1 rfl)
    · intro h
      cases h with
      | cons hl hrest =>
        rw [List.map_cons, splitAt_complete COMMA l _ hl, (ih _).2 hrest]

/-- The executable parser only returns tables the declarative semantics assigns. -/
theorem parseCsv_sound {b : Bytes} {header : List Bytes} {rows : List (List Bytes)}
    (h : parseCsv b = some (header, rows)) : CsvTable b header rows := by
  unfold parseCsv at h
  split at h
  · rename_i hpre
    obtain ⟨hu, hq, hn⟩ := hpre
    split at h
    · rename_i hl rest hm
      split at h
      · cases h
      · rename_i hne
        simp only at h
        split at h
        · rename_i hconds
          cases h
          exact ⟨ByteArray.validateUTF8_eq_true_iff.1 hu, hq, hn,
            ⟨splitAt LF b, hl, rest, splitAt_sound LF b, mapOpt_stripCR_iff.1 hm, hne,
              splitAt_sound COMMA hl, (splitRows_iff _ _).1 rfl⟩,
            hconds.1, hconds.2.1, hconds.2.2⟩
        · cases h
    · cases h
  · cases h

/-- The executable parser accepts every strict CSV table. -/
theorem parseCsv_complete {b : Bytes} {header : List Bytes} {rows : List (List Bytes)}
    (h : CsvTable b header rows) : parseCsv b = some (header, rows) := by
  obtain ⟨hu, hq, hn, ⟨raw, hl, rest, hsplit, hpw, hne, hhead, hrows⟩, hnd, hrect, hlim⟩ := h
  unfold parseCsv
  rw [if_pos ⟨ByteArray.validateUTF8_eq_true_iff.2 hu, hq, hn⟩, splitAt_complete LF b raw hsplit,
    mapOpt_stripCR_iff.2 hpw]
  simp only
  rw [if_neg hne, splitAt_complete COMMA hl header hhead, (splitRows_iff _ _).2 hrows]
  rw [if_pos ⟨hnd, hrect, hlim⟩]

theorem parseCsv_iff (b : Bytes) (header : List Bytes) (rows : List (List Bytes)) :
    parseCsv b = some (header, rows) ↔ CsvTable b header rows :=
  ⟨parseCsv_sound, parseCsv_complete⟩

/-- A byte string denotes at most one strict CSV table. -/
theorem csvTable_unique {b : Bytes} {h₁ h₂ : List Bytes} {r₁ r₂ : List (List Bytes)}
    (t₁ : CsvTable b h₁ r₁) (t₂ : CsvTable b h₂ r₂) : h₁ = h₂ ∧ r₁ = r₂ := by
  have := (parseCsv_complete t₁).symm.trans (parseCsv_complete t₂)
  simp only [Option.some.injEq, Prod.mk.injEq] at this
  exact this

/-! ## Key columns and disjointness -/

theorem indexOf_sound : ∀ {k : Bytes} {xs : List Bytes} {i : Nat},
    indexOf k xs = some i → xs[i]? = some k
  | _, [], _, h => by cases h
  | k, x :: xs, i, h => by
    unfold indexOf at h
    split at h
    · rename_i hx; cases h; simp [hx]
    · cases hi : indexOf k xs with
      | none => rw [hi] at h; cases h
      | some j =>
        rw [hi] at h
        cases h
        simpa using indexOf_sound hi

theorem indexOf_complete : ∀ {k : Bytes} {xs : List Bytes} {i : Nat},
    xs[i]? = some k → ∃ j, indexOf k xs = some j
  | _, [], _, h => by simp at h
  | k, x :: xs, i, h => by
    unfold indexOf
    split
    · exact ⟨0, rfl⟩
    · rename_i hx
      cases i with
      | zero => simp at h; exact absurd h hx
      | succ i =>
        obtain ⟨j, hj⟩ := indexOf_complete (xs := xs) (i := i) (by simpa using h)
        exact ⟨j + 1, by rw [hj]; rfl⟩

theorem getElem?_inj_of_nodup : ∀ {xs : List Bytes}, xs.Nodup → ∀ {i j : Nat} {k : Bytes},
    xs[i]? = some k → xs[j]? = some k → i = j
  | [], _, _, _, _, hi, _ => by simp at hi
  | x :: xs, hnd, i, j, k, hi, hj => by
    have hx : x ∉ xs := (List.nodup_cons.1 hnd).1
    have hnd' : xs.Nodup := (List.nodup_cons.1 hnd).2
    cases i with
    | zero =>
      cases j with
      | zero => rfl
      | succ j =>
        simp only [List.getElem?_cons_zero, Option.some.injEq] at hi
        simp only [List.getElem?_cons_succ] at hj
        subst hi
        exact absurd (List.mem_of_getElem? hj) hx
    | succ i =>
      cases j with
      | zero =>
        simp only [List.getElem?_cons_zero, Option.some.injEq] at hj
        simp only [List.getElem?_cons_succ] at hi
        subst hj
        exact absurd (List.mem_of_getElem? hi) hx
      | succ j =>
        simp only [List.getElem?_cons_succ] at hi hj
        rw [getElem?_inj_of_nodup hnd' hi hj]

theorem mem_keysAt {rows : List (List Bytes)} {i : Nat} {k : Bytes} :
    k ∈ keysAt rows i ↔ ∃ r ∈ rows, r[i]? = some k := by
  simp [keysAt]

theorem getElem?_isSome_of_rect {header : List Bytes} {rows : List (List Bytes)}
    (hrect : ∀ r ∈ rows, r.length = header.length) {i : Nat} {k : Bytes}
    (hi : header[i]? = some k) : ∀ r ∈ rows, ∃ v, r[i]? = some v := by
  intro r hr
  have hlt : i < header.length := by
    rcases Nat.lt_or_ge i header.length with h | h
    · exact h
    · rw [List.getElem?_eq_none h] at hi; cases hi
  exact ⟨r[i]'(by rw [hrect r hr]; exact hlt), List.getElem?_eq_getElem _⟩

theorem disjoint_keys_iff {rL rR : List (List Bytes)} {iL iR : Nat}
    (hL : ∀ r ∈ rL, ∃ v, r[iL]? = some v) :
    ((keysAt rL iL).all (fun k => !(keysAt rR iR).contains k)) = true ↔
      ∀ r₁ ∈ rL, ∀ r₂ ∈ rR, r₁[iL]? ≠ r₂[iR]? := by
  constructor
  · intro h r₁ h₁ r₂ h₂ heq
    obtain ⟨v, hv⟩ := hL r₁ h₁
    rw [List.all_eq_true] at h
    have := h v (mem_keysAt.2 ⟨r₁, h₁, hv⟩)
    simp only [Bool.not_eq_eq_eq_not, Bool.not_true, List.contains_eq_mem,
      decide_eq_false_iff_not] at this
    exact this (mem_keysAt.2 ⟨r₂, h₂, heq ▸ hv⟩)
  · intro h
    rw [List.all_eq_true]
    intro k hk
    obtain ⟨r₁, h₁, hv⟩ := mem_keysAt.1 hk
    simp only [Bool.not_eq_eq_eq_not, Bool.not_true, List.contains_eq_mem,
      decide_eq_false_iff_not]
    intro hk'
    obtain ⟨r₂, h₂, hv'⟩ := mem_keysAt.1 hk'
    exact h r₁ h₁ r₂ h₂ (hv.trans hv'.symm)

/-- **The executable check decides `CsvDisjoint`.** -/
theorem csvDisjointB_iff (left right key : Bytes) :
    csvDisjointB left right key = true ↔ CsvDisjoint left right key := by
  unfold csvDisjointB CsvDisjoint
  constructor
  · intro h
    split at h
    · rename_i hL rL hR rR hpl hpr
      have tL := parseCsv_sound hpl
      have tR := parseCsv_sound hpr
      split at h
      · rename_i iL iR hiL hiR
        have hkL := indexOf_sound hiL
        have hkR := indexOf_sound hiR
        exact ⟨hL, rL, iL, hR, rR, iR, tL, tR, hkL, hkR,
          (disjoint_keys_iff (getElem?_isSome_of_rect tL.rectangular hkL)).1 h⟩
      · cases h
    · cases h
  · rintro ⟨hL, rL, iL, hR, rR, iR, tL, tR, hkL, hkR, hdisj⟩
    rw [parseCsv_complete tL, parseCsv_complete tR]
    simp only
    obtain ⟨jL, hjL⟩ := indexOf_complete hkL
    obtain ⟨jR, hjR⟩ := indexOf_complete hkR
    have eL := getElem?_inj_of_nodup tL.headerDistinct (indexOf_sound hjL) hkL
    have eR := getElem?_inj_of_nodup tR.headerDistinct (indexOf_sound hjR) hkR
    subst eL eR
    rw [hjL, hjR]
    exact (disjoint_keys_iff (getElem?_isSome_of_rect tL.rectangular hkL)).2 hdisj

/-! ## The `csv_disjoint` evidence object -/

def isCsvCheck (ev : JVal) : Bool :=
  match checkSpec ev with
  | some sp => decide (strField sp "type" = some "csv_disjoint")
  | none => false

/-- `(left artifact id, right artifact id, key)` of a `csv_disjoint` check spec. -/
def csvSpec (ev : JVal) : Option (String × String × String) :=
  match checkSpec ev with
  | some sp =>
    match field sp "left_artifact", field sp "right_artifact", field sp "key" with
    | some (.str l), some (.str r), some (.str k) => some (l, r, k)
    | _, _, _ => none
  | none => none

/-- **Scientific predicate of a `csv_disjoint` item**: the committed artifacts named by
    the evidence are strict CSV tables with the key column and disjoint key sets. -/
def CsvHolds (req : ReplayRequest) : Prop :=
  ∃ sp l r k bl br, checkSpec req.evidence = some sp ∧
    strField sp "type" = some "csv_disjoint" ∧
    field sp "left_artifact" = some (.str l) ∧ field sp "right_artifact" = some (.str r) ∧
    field sp "key" = some (.str k) ∧
    lookup req.artifacts l = some bl ∧ lookup req.artifacts r = some br ∧
    CsvDisjoint bl.data.toList br.data.toList k.toUTF8.data.toList

/-- Lean replay of a `csv_disjoint` item (missing artifacts or malformed specs fail). -/
def csvRun (req : ReplayRequest) : Observation :=
  match csvSpec req.evidence with
  | some (l, r, k) =>
    match lookup req.artifacts l, lookup req.artifacts r with
    | some bl, some br =>
      ⟨.computationalTest,
        if csvDisjointB bl.data.toList br.data.toList k.toUTF8.data.toList then .pass else .fail⟩
    | _, _ => ⟨.computationalTest, .fail⟩
  | none => ⟨.computationalTest, .fail⟩

theorem csvRun_sound (req : ReplayRequest) (hc : isCsvCheck req.evidence = true)
    (hp : (csvRun req).outcome = .pass) : CsvHolds req := by
  unfold csvRun at hp
  unfold isCsvCheck at hc
  split at hp
  · rename_i l r k hspec
    unfold csvSpec at hspec
    split at hspec
    · rename_i sp hsp
      rw [hsp] at hc
      simp only [decide_eq_true_eq] at hc
      split at hspec
      · rename_i l' r' k' hl hr hk
        cases hspec
        split at hp
        · rename_i bl br hbl hbr
          have hb : csvDisjointB bl.data.toList br.data.toList k.toUTF8.data.toList = true := by
            cases hh : csvDisjointB bl.data.toList br.data.toList k.toUTF8.data.toList
            · rw [hh] at hp; cases hp
            · rfl
          exact ⟨sp, l, r, k, bl, br, hsp, hc, hl, hr, hk, hbl, hbr,
            (csvDisjointB_iff _ _ _).1 hb⟩
        · cases hp
      · cases hspec
    · cases hspec
  · cases hp

end PCS.V2.Csv
