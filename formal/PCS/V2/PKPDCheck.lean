import PCS.V2.Csv
import PCS.V2.Workflow

/-!
# Verified high-assurance replay for `pkpd_contract` and `pkpd_reference_match`

PCS supports one restricted PK/PD model (`pcs/adapters/pkpd.py`):

```text
C(t) = (Dose / V) * exp(-(CL / V) * t)          one-compartment IV bolus
E(C) = E0 + Emax * C / (EC50 + C)               direct Emax (optional)
```

The production replay evaluates these with Python `Decimal` at 50 digits.  The Lean
authority does **not** try to reproduce that floating/decimal computation.  Instead it
runs an independent **exact-rational, certified-interval** evaluation:

* every number in the committed model JSON, in the committed prediction CSV and in the
  tolerances is read as an *exact* rational from its decimal spelling (`decimalQ`);
* unit symbols are read with their exact rational SI scale (`unitInfo`), and the physical
  dimension is the verified `PCS.V2.Units.parseUnit` dimension;
* `exp` is enclosed by `expEncl`: argument halving, the Taylor polynomial with the
  Lagrange-type remainder bound `|y|^n (n+1)/(n! n)` (valid for `|y| ≤ 1`), then repeated
  squaring with outward dyadic rounding;
* a prediction row passes only if the observed value is within tolerance of **every**
  point of the enclosure (`CloseEncl`).

This file proves that the executable checks imply their declarative, exact-rational
meaning (`pkpdContractRun_sound`, `pkpdMatchRun_sound`).  The real-analysis step —
that `expEncl x` really encloses `Real.exp x`, so that a `PASS` means the *real-valued*
analytic model lies within the declared tolerance of every committed reported value —
needs real numbers and is proved in the Mathlib bridge `PCSReal.PKPD`
(`pkpd_reference_match_real`).

High-assurance numeric subset (fail-closed; production `pcs/adapters/pkpd.py` was
narrowed to the same surface):
* decimal numbers `-?[0-9]+(.[0-9]+)?([eE][+-]?[0-9]+)?` with `|exponent| ≤ 400`;
* the model artifact is UTF-8 JSON (whitespace allowed, duplicate keys rejected);
* the prediction table is a strict CSV table (`PCS.V2.Csv.CsvTable`).
-/

set_option autoImplicit false

namespace PCS.V2.PKPDCheck

open PCS PCS.V2.Json PCS.V2.Common PCS.V2.Package PCS.V2.Replay PCS.V2.TextSplit PCS.V2.Index
open PCS.V2.Chemistry (checkSpec isDig digitsVal)
open PCS.V2.Units (Dim parseUnit ExprDenotes parseExp)
open PCS.V2.Workflow (PVal pfield pstr parseNumber)

/-! ## Rational helpers -/

def qabs (q : Rat) : Rat := if q < 0 then -q else q

/-- `10 ^ e` for an integer exponent, as an exact rational. -/
def pow10 (e : Int) : Rat :=
  if 0 ≤ e then ((10 ^ e.toNat : Nat) : Rat) else 1 / ((10 ^ (-e).toNat : Nat) : Rat)

/-! ## Exact decimal numbers -/

def spanDig : List Char → List Char × List Char
  | [] => ([], [])
  | c :: r => if isDig c then let p := spanDig r; (c :: p.1, p.2) else ([], c :: r)

/-- Maximal decimal exponent magnitude of the high-assurance subset. -/
def maxExp : Nat := 400

/-- The decimal value `±(I.F) × 10^(±E)` of `-?I(.F)?([eE][+-]?E)?`. -/
def decValue (neg : Bool) (ids fds : List Char) (eneg : Bool) (eds : List Char) : Rat :=
  let m : Rat := ((digitsVal (ids ++ fds) : Nat) : Rat)
  let e : Int := (if eneg then -(digitsVal eds : Int) else (digitsVal eds : Int)) - fds.length
  (if neg then -m else m) * pow10 e

/-- Strict decimal parser: `-?[0-9]+(\.[0-9]+)?([eE][+-]?[0-9]+)?`, whole input. -/
def decimalChars (cs : List Char) : Option Rat :=
  let (neg, r0) := match cs with
    | '-' :: r => (true, r)
    | r => (false, r)
  match spanDig r0 with
  | ([], _) => none
  | (ids, r1) =>
    let frac : Option (List Char × List Char) := match r1 with
      | '.' :: r => match spanDig r with
        | ([], _) => none
        | (ds, r') => some (ds, r')
      | r => some ([], r)
    match frac with
    | none => none
    | some (fds, r2) =>
      let ex : Option (Bool × List Char) := match r2 with
        | [] => some (false, [])
        | e :: r =>
          if e = 'e' ∨ e = 'E' then
            let (eneg, r') := match r with
              | '+' :: q => (false, q)
              | '-' :: q => (true, q)
              | q => (false, q)
            match spanDig r' with
            | ([], _) => none
            | (eds, []) => some (eneg, eds)
            | (_, _ :: _) => none
          else none
      match ex with
      | none => none
      | some (eneg, eds) =>
        if digitsVal eds ≤ maxExp ∧ eds.length ≤ 4 then some (decValue neg ids fds eneg eds)
        else none

def decimalQ (s : String) : Option Rat := decimalChars s.toList

/-! ## JSON with insignificant whitespace (model artifact) -/

def isWs (c : Char) : Bool := c = ' ' || c = '\t' || c = '\n' || c = '\r'

def skipWs : List Char → List Char
  | [] => []
  | c :: r => if isWs c then skipWs r else c :: r

/-- JSON forbids leading zeros (`01`, `-01`); production's `json` rejects them. -/
def jsonNumOK : List Char → Bool
  | '0' :: d :: _ => !isDig d
  | '-' :: '0' :: d :: _ => !isDig d
  | _ => true

/-- Parse a string body, rejecting raw control characters (as Python's strict `json`). -/
def jStr (r : List Char) : Option (List Char × List Char) :=
  match parseStrBody r with
  | some (v, rest) => if (r.take (r.length - rest.length)).all (fun c => 32 ≤ c.toNat) then
      some (v, rest) else none
  | none => none

mutual
def jVal : Nat → List Char → Option (PVal × List Char)
  | 0, _ => none
  | n + 1, cs =>
    match skipWs cs with
    | [] => none
    | c :: r =>
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
        (jStr r).map fun p => (.str (String.ofList p.1), p.2)
      else if c = '[' then
        match skipWs r with
        | ']' :: r' => some (.arr [], r')
        | _ =>
          match jVal n r with
          | some (x, r') =>
            match jElems n r' with
            | some (xs, r'') => some (.arr (x :: xs), r'')
            | none => none
          | none => none
      else if c = '{' then
        match skipWs r with
        | '}' :: r' => some (.obj [], r')
        | '"' :: r1 =>
          match jStr r1 with
          | some (k, r2) =>
            match skipWs r2 with
            | ':' :: r3 =>
              match jVal n r3 with
              | some (v, r4) =>
                match jMembers n r4 with
                | some (ms, r5) =>
                  let all := (String.ofList k, v) :: ms
                  if (all.map (·.1)).Nodup then some (.obj all, r5) else none
                | none => none
              | none => none
            | _ => none
          | none => none
        | _ => none
      else if c = '-' ∨ isDig c then
        match parseNumber (c :: r) with
        | some (raw, r') => if jsonNumOK raw then some (.num (String.ofList raw), r') else none
        | none => none
      else none

def jElems : Nat → List Char → Option (List PVal × List Char)
  | 0, _ => none
  | n + 1, cs =>
    match skipWs cs with
    | ']' :: r => some ([], r)
    | ',' :: r =>
      match jVal n r with
      | some (x, r') =>
        match jElems n r' with
        | some (xs, r'') => some (x :: xs, r'')
        | none => none
      | none => none
    | _ => none

def jMembers : Nat → List Char → Option (List (String × PVal) × List Char)
  | 0, _ => none
  | n + 1, cs =>
    match skipWs cs with
    | '}' :: r => some ([], r)
    | ',' :: r0 =>
      match skipWs r0 with
      | '"' :: r1 =>
        match jStr r1 with
        | some (k, r2) =>
          match skipWs r2 with
          | ':' :: r3 =>
            match jVal n r3 with
            | some (v, r4) =>
              match jMembers n r4 with
              | some (ms, r5) => some ((String.ofList k, v) :: ms, r5)
              | none => none
            | none => none
          | _ => none
        | none => none
      | _ => none
    | _ => none
end

/-- Parse a complete UTF-8 JSON document (fail-closed). -/
def parseJsonDoc (b : List UInt8) : Option PVal :=
  match String.fromUTF8? ⟨b.toArray⟩ with
  | none => none
  | some s =>
    match jVal (s.length + 1) s.toList with
    | some (v, rest) => if skipWs rest = [] then some v else none
    | none => none

/-! ## Units with exact SI scale -/

/-- The PCS unit table `_BASE` (symbol ↦ exact SI scale). -/
def scaleTable : List (String × Rat) :=
  [("1", 1), ("kg", 1), ("g", 1 / 1000), ("mg", 1 / 1000000), ("ug", 1 / 1000000000),
   ("m", 1), ("cm", 1 / 100),
   ("L", 1 / 1000), ("mL", 1 / 1000000), ("uL", 1 / 1000000000),
   ("s", 1), ("min", 60), ("h", 3600),
   ("mol", 1), ("mmol", 1 / 1000), ("umol", 1 / 1000000),
   ("M", 1000), ("mM", 1)]

def baseScale (name : List Char) : Option Rat :=
  (scaleTable.find? (·.1 == String.ofList name)).map (·.2)

def ratPowInt (q : Rat) (e : Int) : Rat :=
  if 0 ≤ e then q ^ e.toNat else 1 / q ^ (-e).toNat

def termScale (t : List Char) : Option Rat :=
  match splitAt '^' t with
  | [name] => baseScale name
  | [name, es] =>
    match baseScale name, parseExp es with
    | some k, some e => some (ratPowInt k e)
    | _, _ => none
  | _ => none

def prodQ : List Rat → Rat
  | [] => 1
  | q :: qs => q * prodQ qs

def productScale (p : List Char) : Option Rat :=
  if p = [] then some 1 else (mapOpt termScale (splitAt '*' p)).map prodQ

def unitScale (s : List Char) : Option Rat :=
  match splitAt '/' (s.filter (· != ' ')) with
  | [] => none
  | p :: ps =>
    match productScale p, mapOpt productScale ps with
    | some a, some bs => some (a / prodQ bs)
    | _, _ => none

/-- Dimension (verified parser) and exact positive SI scale of a non-empty unit string. -/
def unitInfo (u : String) : Option (Dim × Rat) :=
  if u = "" then none else
  match parseUnit u.toList, unitScale u.toList with
  | some d, some k => if 0 < k then some (d, k) else none
  | _, _ => none

theorem unitInfo_sound {u : String} {d : Dim} {k : Rat} (h : unitInfo u = some (d, k)) :
    u ≠ "" ∧ ExprDenotes u.toList d ∧ unitScale u.toList = some k ∧ 0 < k := by
  unfold unitInfo at h
  split at h
  · cases h
  · rename_i hu
    split at h
    · rename_i d' k' hd hk
      split at h
      · rename_i hpos
        cases h
        exact ⟨hu, PCS.V2.Units.parseUnit_sound hd, hk, hpos⟩
      · cases h
    · cases h

/-! ## Model contract -/

def massD : Dim := ⟨1, 0, 0, 0⟩
def volumeD : Dim := ⟨0, 3, 0, 0⟩
def clearanceD : Dim := ⟨0, 3, -1, 0⟩
def timeD : Dim := ⟨0, 0, 1, 0⟩
def concD : Dim := ⟨1, -3, 0, 0⟩

/-- A physical quantity of the model: exact value, unit dimension and SI scale. -/
structure Qty where
  value : Rat
  dim : Dim
  scale : Rat

/-- The SI value of a quantity. -/
def Qty.si (q : Qty) : Rat := q.value * q.scale

def numOf : Option PVal → Option Rat
  | some (.num raw) => decimalQ raw
  | _ => none

/-- `_quantity`: an object `{value, unit}` with the expected dimension (and `value > 0`
    when `strict`). -/
def quantity (v : Option PVal) (expected : Dim) (strict : Bool) : Option Qty :=
  match v with
  | some (.obj ms) =>
    match numOf (pfield ms "value"), pstr (pfield ms "unit") with
    | some x, some u =>
      match unitInfo u with
      | some (d, k) => if d = expected ∧ (strict = true → 0 < x) then some ⟨x, d, k⟩ else none
      | none => none
    | _, _ => none
  | _ => none

structure PDModel where
  e0 : Qty
  emax : Qty
  ec50 : Qty
  effectDim : Dim
  effectScale : Rat

structure PKModel where
  dose : Qty
  volume : Qty
  clearance : Qty
  timeScale : Rat
  concScale : Rat
  pd : Option PDModel

def decodePD (pms : List (String × PVal)) : Option PDModel :=
  if pstr (pfield pms "model_type") = some "direct_emax" then
    match pstr (pfield pms "effect_unit") with
    | some eu =>
      match unitInfo eu with
      | some (ed, es) =>
        match quantity (pfield pms "e0") ed false, quantity (pfield pms "emax") ed true,
            quantity (pfield pms "ec50") concD true with
        | some e0, some emax, some ec50 => some ⟨e0, emax, ec50, ed, es⟩
        | _, _, _ => none
      | none => none
    | none => none
  else none

def decodeModelObj (ms : List (String × PVal)) : Option PKModel :=
  if pstr (pfield ms "model_type") = some "one_compartment_iv_bolus" then
    match quantity (pfield ms "dose") massD true, quantity (pfield ms "volume") volumeD true,
        quantity (pfield ms "clearance") clearanceD true with
    | some dose, some vol, some cl =>
      match pstr (pfield ms "time_unit"), pstr (pfield ms "concentration_unit") with
      | some tu, some cu =>
        match unitInfo tu, unitInfo cu with
        | some (td, ts), some (cd, cs) =>
          if td = timeD ∧ cd = concD then
            match pfield ms "pd" with
            | none => some ⟨dose, vol, cl, ts, cs, none⟩
            | some .null => some ⟨dose, vol, cl, ts, cs, none⟩
            | some (.obj pms) => (decodePD pms).map fun pd => ⟨dose, vol, cl, ts, cs, some pd⟩
            | some _ => none
          else none
        | _, _ => none
      | _, _ => none
    | _, _, _ => none
  else none

/-- Decode and contract-check a committed model artifact. -/
def decodeModel (b : List UInt8) : Option PKModel :=
  match parseJsonDoc b with
  | some (.obj ms) => decodeModelObj ms
  | _ => none

/-! ### Declarative meaning of the contract -/

/-- `q` is the quantity denoted by the JSON member `v`: an object whose `value` is a decimal
    number denoting `q.value` and whose `unit` is a non-empty unit expression of dimension
    `expected` (`ExprDenotes`) with exact SI scale `q.scale > 0`. -/
structure QtyDenotes (v : Option PVal) (expected : Dim) (strict : Bool) (q : Qty) : Prop where
  shape : ∃ ms raw u, v = some (.obj ms) ∧ pfield ms "value" = some (.num raw) ∧
    decimalQ raw = some q.value ∧ pfield ms "unit" = some (.str u) ∧ u ≠ "" ∧
    ExprDenotes u.toList expected ∧ unitScale u.toList = some q.scale
  dim : q.dim = expected
  scalePos : 0 < q.scale
  positive : strict = true → 0 < q.value

/-- A unit member denotes dimension `d` with exact SI scale `k > 0`. -/
def UnitDenotes (v : Option PVal) (d : Dim) (k : Rat) : Prop :=
  ∃ u, v = some (.str u) ∧ u ≠ "" ∧ ExprDenotes u.toList d ∧ unitScale u.toList = some k ∧ 0 < k

/-- **Meaning of the restricted PD block.** -/
structure PDContract (pms : List (String × PVal)) (pd : PDModel) : Prop where
  modelType : pfield pms "model_type" = some (.str "direct_emax")
  effectUnit : UnitDenotes (pfield pms "effect_unit") pd.effectDim pd.effectScale
  e0 : QtyDenotes (pfield pms "e0") pd.effectDim false pd.e0
  emax : QtyDenotes (pfield pms "emax") pd.effectDim true pd.emax
  ec50 : QtyDenotes (pfield pms "ec50") concD true pd.ec50

/-- **Meaning of `pkpd_contract`**: the committed bytes are a JSON object declaring the
    one-compartment IV-bolus model with positive dose (mass), volume (length³) and
    clearance (length³/time), a time unit and a mass/volume concentration unit, and —
    if present and not `null` — a direct-Emax PD block with positive `Emax`, positive
    `EC50` (mass/volume) and `E0`, `Emax` in the declared effect unit. -/
structure ModelContract (b : List UInt8) (m : PKModel) : Prop where
  json : ∃ ms, parseJsonDoc b = some (.obj ms) ∧
    pfield ms "model_type" = some (.str "one_compartment_iv_bolus") ∧
    QtyDenotes (pfield ms "dose") massD true m.dose ∧
    QtyDenotes (pfield ms "volume") volumeD true m.volume ∧
    QtyDenotes (pfield ms "clearance") clearanceD true m.clearance ∧
    UnitDenotes (pfield ms "time_unit") timeD m.timeScale ∧
    UnitDenotes (pfield ms "concentration_unit") concD m.concScale ∧
    (match m.pd with
      | none => pfield ms "pd" = none ∨ pfield ms "pd" = some .null
      | some pd => ∃ pms, pfield ms "pd" = some (.obj pms) ∧ PDContract pms pd)

theorem pstr_eq_some {v : Option PVal} {s : String} (h : pstr v = some s) : v = some (.str s) := by
  unfold pstr at h; split at h <;> simp_all

theorem numOf_eq_some {v : Option PVal} {q : Rat} (h : numOf v = some q) :
    ∃ raw, v = some (.num raw) ∧ decimalQ raw = some q := by
  unfold numOf at h; split at h
  · exact ⟨_, rfl, h⟩
  · cases h

theorem quantity_sound {v : Option PVal} {e : Dim} {st : Bool} {q : Qty}
    (h : quantity v e st = some q) : QtyDenotes v e st q := by
  unfold quantity at h
  split at h
  · rename_i ms
    split at h
    · rename_i x u hx hu
      split at h
      · rename_i d k hk
        split at h
        · rename_i hc
          cases h
          obtain ⟨raw, hraw, hq⟩ := numOf_eq_some hx
          obtain ⟨hne, hden, hsc, hpos⟩ := unitInfo_sound hk
          rw [hc.1] at hden
          exact ⟨⟨ms, raw, u, rfl, hraw, hq, pstr_eq_some hu, hne, hden, hsc⟩, hc.1, hpos, hc.2⟩
        · cases h
      · cases h
    · cases h
  · cases h

theorem unitDenotes_of {v : Option PVal} {u : String} {d : Dim} {k : Rat}
    (hu : pstr v = some u) (hk : unitInfo u = some (d, k)) : UnitDenotes v d k := by
  obtain ⟨hne, hden, hsc, hpos⟩ := unitInfo_sound hk
  exact ⟨u, pstr_eq_some hu, hne, hden, hsc, hpos⟩

theorem decodePD_sound {pms : List (String × PVal)} {pd : PDModel} (h : decodePD pms = some pd) :
    PDContract pms pd := by
  unfold decodePD at h
  split at h
  · rename_i hmt
    split at h
    · rename_i eu heu
      split at h
      · rename_i ed es hes
        split at h
        · rename_i e0 emax ec50 h0 h1 h2
          cases h
          exact ⟨pstr_eq_some hmt, unitDenotes_of heu hes, quantity_sound h0, quantity_sound h1,
            quantity_sound h2⟩
        · cases h
      · cases h
    · cases h
  · cases h

theorem decodeModel_sound {b : List UInt8} {m : PKModel} (h : decodeModel b = some m) :
    ModelContract b m := by
  unfold decodeModel at h
  split at h
  · rename_i ms hms
    unfold decodeModelObj at h
    split at h
    · rename_i hmt
      split at h
      · rename_i dose vol cl hd hv hc
        split at h
        · rename_i tu cu htu hcu
          split at h
          · rename_i td ts cd cs hts hcs
            split at h
            · rename_i hdims
              have ht : UnitDenotes (pfield ms "time_unit") timeD ts := by
                rw [← hdims.1]; exact unitDenotes_of htu hts
              have hcc : UnitDenotes (pfield ms "concentration_unit") concD cs := by
                rw [← hdims.2]; exact unitDenotes_of hcu hcs
              have base := fun (pdv : Option PDModel) (hpd : match pdv with
                  | none => pfield ms "pd" = none ∨ pfield ms "pd" = some .null
                  | some pd => ∃ pms, pfield ms "pd" = some (.obj pms) ∧ PDContract pms pd) =>
                (⟨⟨ms, hms, pstr_eq_some hmt, quantity_sound hd, quantity_sound hv,
                  quantity_sound hc, ht, hcc, hpd⟩⟩ : ModelContract b ⟨dose, vol, cl, ts, cs, pdv⟩)
              split at h
              · rename_i hp; cases h; exact base none (Or.inl hp)
              · rename_i hp; cases h; exact base none (Or.inr hp)
              · rename_i pms hp
                cases hdp : decodePD pms with
                | none => rw [hdp] at h; cases h
                | some pd =>
                  rw [hdp] at h
                  cases h
                  exact base (some pd) ⟨pms, hp, decodePD_sound hdp⟩
              · cases h
            · cases h
          · cases h
        · cases h
      · cases h
    · cases h
  · cases h

/-! ## Certified enclosure of `exp` -/

/-- Number of Taylor terms. -/
def taylorTerms : Nat := 30

/-- Dyadic precision (bits) of the outward rounding. -/
def roundBits : Nat := 256

/-- `n!`. -/
def fact : Nat → Nat
  | 0 => 1
  | n + 1 => (n + 1) * fact n

/-- `∑_{i<n} y^i / i!`. -/
def taylorSum (y : Rat) : Nat → Rat
  | 0 => 0
  | n + 1 => taylorSum y n + y ^ n / ((fact n : Nat) : Rat)

/-- The remainder bound `|y|^n (n+1) / (n! n)` (valid for `|y| ≤ 1`, `n > 0`). -/
def taylorRem (y : Rat) (n : Nat) : Rat :=
  qabs y ^ n * (((n + 1 : Nat) : Rat) / (((fact n : Nat) : Rat) * (n : Rat)))

def roundDown (p : Nat) (q : Rat) : Rat := ((q * ((2 ^ p : Nat) : Rat)).floor : Rat) / ((2 ^ p : Nat) : Rat)
def roundUp (p : Nat) (q : Rat) : Rat := -roundDown p (-q)

/-- `k` squarings with outward rounding; the lower end is kept non-negative. -/
def squareN : Nat → Rat × Rat → Rat × Rat
  | 0, i => i
  | k + 1, (lo, hi) =>
    squareN k (max 0 (roundDown roundBits (lo * lo)), roundUp roundBits (hi * hi))

/-- Number of halvings so that `|x| / 2^k ≤ 1/2`. -/
def halvings (x : Rat) : Nat := Nat.log2 (qabs x).ceil.toNat + 2

/-- **Certified enclosure of `exp x`**: `some (lo, hi)` with (proved in `PCSReal.PKPD`)
    `lo ≤ Real.exp x ≤ hi`. -/
def expEncl (x : Rat) : Option (Rat × Rat) :=
  let k := halvings x
  let y := x / ((2 ^ k : Nat) : Rat)
  if qabs y ≤ 1 then
    let s := taylorSum y taylorTerms
    let r := taylorRem y taylorTerms
    some (squareN k (max 0 (roundDown roundBits (s - r)), roundUp roundBits (s + r)))
  else none

/-! ## Model evaluation on enclosures -/

/-- Elimination rate `CL / V` (SI). -/
def PKModel.kel (m : PKModel) : Rat := m.clearance.si / m.volume.si
/-- Initial concentration `Dose / V` (SI). -/
def PKModel.c0 (m : PKModel) : Rat := m.dose.si / m.volume.si

/-- Exponent `-(CL/V) · t_SI` for a time `t` in the declared time unit. -/
def PKModel.expo (m : PKModel) (t : Rat) : Rat := -m.kel * (t * m.timeScale)

/-- The direct-Emax effect, in the declared effect unit, of an SI concentration. -/
def PDModel.effect (pd : PDModel) (cSI : Rat) : Rat :=
  (pd.e0.si + pd.emax.si * cSI / (pd.ec50.si + cSI)) / pd.effectScale

/-- Smallest absolute value on `[lo, hi]`. -/
def minAbs (lo hi : Rat) : Rat := if 0 ≤ lo then lo else if hi ≤ 0 then -hi else 0

/-- Python `_decimal_isclose(a, v)` holds for **every** `v ∈ [lo, hi]` (endpoint form). -/
def CloseEncl (a lo hi atol rtol : Rat) : Prop :=
  lo ≤ hi ∧ qabs (a - lo) ≤ max atol (rtol * max (qabs a) (minAbs lo hi)) ∧
    qabs (a - hi) ≤ max atol (rtol * max (qabs a) (minAbs lo hi))

instance (a lo hi atol rtol : Rat) : Decidable (CloseEncl a lo hi atol rtol) := by
  unfold CloseEncl; infer_instance

/-! ## Prediction rows -/

abbrev Bytes := List UInt8

def fieldQ (row : List Bytes) (i : Nat) : Option Rat :=
  match row[i]? with
  | some f =>
    match String.fromUTF8? ⟨f.toArray⟩ with
    | some s => decimalQ s
    | none => none
  | none => none

/-- **Meaning of one passing prediction row.** -/
structure RowHolds (m : PKModel) (atol rtol : Rat) (iT iC : Nat) (iE : Option Nat)
    (row : List Bytes) : Prop where
  values : ∃ t c lo hi, fieldQ row iT = some t ∧ fieldQ row iC = some c ∧ 0 ≤ t ∧
    expEncl (m.expo t) = some (lo, hi) ∧ 0 ≤ lo ∧
    CloseEncl c (m.c0 * lo / m.concScale) (m.c0 * hi / m.concScale) atol rtol ∧
    (∀ pd, m.pd = some pd → ∃ i e, iE = some i ∧ fieldQ row i = some e ∧
      CloseEncl e (pd.effect (m.c0 * lo)) (pd.effect (m.c0 * hi)) atol rtol)

def rowB (m : PKModel) (atol rtol : Rat) (iT iC : Nat) (iE : Option Nat) (row : List Bytes) :
    Bool :=
  match fieldQ row iT, fieldQ row iC with
  | some t, some c =>
    match expEncl (m.expo t) with
    | some (lo, hi) =>
      decide (0 ≤ t) && decide (0 ≤ lo) &&
      decide (CloseEncl c (m.c0 * lo / m.concScale) (m.c0 * hi / m.concScale) atol rtol) &&
      (match m.pd with
        | none => true
        | some pd =>
          match iE with
          | some i =>
            match fieldQ row i with
            | some e => decide (CloseEncl e (pd.effect (m.c0 * lo)) (pd.effect (m.c0 * hi)) atol rtol)
            | none => false
          | none => false)
    | none => false
  | _, _ => false

theorem rowB_sound {m : PKModel} {atol rtol : Rat} {iT iC : Nat} {iE : Option Nat}
    {row : List Bytes} (h : rowB m atol rtol iT iC iE row = true) :
    RowHolds m atol rtol iT iC iE row := by
  unfold rowB at h
  split at h
  · rename_i t c ht hc
    split at h
    · rename_i lo hi he
      simp only [Bool.and_eq_true, decide_eq_true_eq] at h
      obtain ⟨⟨⟨h0, hlo⟩, hcl⟩, hpd⟩ := h
      refine ⟨t, c, lo, hi, ht, hc, h0, he, hlo, hcl, ?_⟩
      intro pd hp
      rw [hp] at hpd
      simp only at hpd
      split at hpd
      · rename_i i
        split at hpd
        · rename_i e hfe
          exact ⟨i, e, rfl, hfe, of_decide_eq_true hpd⟩
        · cases hpd
      · cases hpd
    · cases h
  · cases h

/-! ## The evidence objects -/

def isCheckType (ty : String) (ev : JVal) : Bool :=
  match checkSpec ev with
  | some sp => decide (strField sp "type" = some ty)
  | none => false

def isPkpdContract (ev : JVal) : Bool := isCheckType "pkpd_contract" ev
def isPkpdMatch (ev : JVal) : Bool := isCheckType "pkpd_reference_match" ev

/-- A tolerance (`rel_tol` / `abs_tol`): a decimal string or an integer, non-negative. -/
def tolOf : Option JVal → Option Rat
  | some (.str s) => match decimalQ s with
    | some q => if 0 ≤ q then some q else none
    | none => none
  | some (.num i) => if 0 ≤ i then some (i : Rat) else none
  | _ => none

/-- **Meaning of a passing `pkpd_contract` item.** -/
def PkpdContractHolds (req : ReplayRequest) : Prop :=
  ∃ sp a b m, checkSpec req.evidence = some sp ∧ strField sp "type" = some "pkpd_contract" ∧
    field sp "model_artifact" = some (.str a) ∧ lookup req.artifacts a = some b ∧
    ModelContract b.data.toList m

def pkpdContractRun (req : ReplayRequest) : Observation :=
  match checkSpec req.evidence with
  | some sp =>
    match field sp "model_artifact" with
    | some (.str a) =>
      match lookup req.artifacts a with
      | some b =>
        ⟨.computationalTest, if (decodeModel b.data.toList).isSome then .pass else .fail⟩
      | none => ⟨.computationalTest, .fail⟩
    | _ => ⟨.computationalTest, .fail⟩
  | none => ⟨.computationalTest, .fail⟩

theorem pkpdContractRun_sound (req : ReplayRequest) (hc : isPkpdContract req.evidence = true)
    (hp : (pkpdContractRun req).outcome = .pass) : PkpdContractHolds req := by
  unfold isPkpdContract isCheckType at hc
  unfold pkpdContractRun at hp
  split at hp
  · rename_i sp hsp
    rw [hsp] at hc
    simp only [decide_eq_true_eq] at hc
    split at hp
    · rename_i a ha
      split at hp
      · rename_i b hb
        cases hm : decodeModel b.data.toList with
        | none => rw [hm] at hp; cases hp
        | some m => exact ⟨sp, a, b, m, hsp, hc, ha, hb, decodeModel_sound hm⟩
      · cases hp
    · cases hp
  · cases hp

/-- The parameters of a `pkpd_reference_match` check spec. -/
structure MatchSpec where
  model : String
  output : String
  timeCol : String
  concCol : String
  effectCol : String
  relTol : Rat
  absTol : Rat

def matchSpec (sp : List (String × JVal)) : Option MatchSpec :=
  match field sp "model_artifact", field sp "output_artifact", field sp "time_column",
      field sp "concentration_column", field sp "effect_column",
      tolOf (field sp "rel_tol"), tolOf (field sp "abs_tol") with
  | some (.str a), some (.str o), some (.str tc), some (.str cc), some (.str ec), some rt,
      some at_ => some ⟨a, o, tc, cc, ec, rt, at_⟩
  | _, _, _, _, _, _, _ => none

/-- **Meaning of a passing `pkpd_reference_match` item** (exact-rational form): the model
    artifact satisfies the contract, the output artifact is a strict CSV table with the
    named columns and at least one row, and in every row the reported concentration (and
    effect, if a PD block is declared) is within tolerance of every point of the certified
    enclosure of the analytic model value at the reported time. -/
def PkpdMatchHolds (req : ReplayRequest) : Prop :=
  ∃ sp ms bm bo m header rows iT iC,
    checkSpec req.evidence = some sp ∧ strField sp "type" = some "pkpd_reference_match" ∧
    matchSpec sp = some ms ∧
    lookup req.artifacts ms.model = some bm ∧ lookup req.artifacts ms.output = some bo ∧
    ModelContract bm.data.toList m ∧
    PCS.V2.Csv.CsvTable bo.data.toList header rows ∧ rows ≠ [] ∧
    header[iT]? = some ms.timeCol.toUTF8.data.toList ∧
    header[iC]? = some ms.concCol.toUTF8.data.toList ∧
    (m.pd.isSome = true → ∃ iE : Nat, header[iE]? = some ms.effectCol.toUTF8.data.toList) ∧
    ∀ row ∈ rows, RowHolds m ms.absTol ms.relTol iT iC
      (PCS.V2.Csv.indexOf ms.effectCol.toUTF8.data.toList header) row

def matchB (ms : MatchSpec) (bm bo : ByteArray) : Bool :=
  match decodeModel bm.data.toList, PCS.V2.Csv.parseCsv bo.data.toList with
  | some m, some (header, rows) =>
    match PCS.V2.Csv.indexOf ms.timeCol.toUTF8.data.toList header,
        PCS.V2.Csv.indexOf ms.concCol.toUTF8.data.toList header with
    | some iT, some iC =>
      let iE := PCS.V2.Csv.indexOf ms.effectCol.toUTF8.data.toList header
      !rows.isEmpty && (m.pd.isNone || iE.isSome) &&
        rows.all (rowB m ms.absTol ms.relTol iT iC iE)
    | _, _ => false
  | _, _ => false

def pkpdMatchRun (req : ReplayRequest) : Observation :=
  match checkSpec req.evidence with
  | some sp =>
    match matchSpec sp with
    | some ms =>
      match lookup req.artifacts ms.model, lookup req.artifacts ms.output with
      | some bm, some bo => ⟨.computationalTest, if matchB ms bm bo then .pass else .fail⟩
      | _, _ => ⟨.computationalTest, .fail⟩
    | none => ⟨.computationalTest, .fail⟩
  | none => ⟨.computationalTest, .fail⟩

theorem pkpdMatchRun_sound (req : ReplayRequest) (hc : isPkpdMatch req.evidence = true)
    (hp : (pkpdMatchRun req).outcome = .pass) : PkpdMatchHolds req := by
  unfold isPkpdMatch isCheckType at hc
  unfold pkpdMatchRun at hp
  split at hp
  · rename_i sp hsp
    rw [hsp] at hc
    simp only [decide_eq_true_eq] at hc
    split at hp
    · rename_i ms hms
      split at hp
      · rename_i bm bo hbm hbo
        have hb : matchB ms bm bo = true := by
          cases hh : matchB ms bm bo
          · rw [hh] at hp; cases hp
          · rfl
        unfold matchB at hb
        split at hb
        · rename_i m header rows hm hcsv
          split at hb
          · rename_i iT iC hiT hiC
            simp only [Bool.and_eq_true, Bool.not_eq_true', List.isEmpty_eq_false_iff,
              List.all_eq_true, Bool.or_eq_true, Option.isNone_iff_eq_none,
              Option.isSome_iff_exists] at hb
            obtain ⟨⟨hne, hpdE⟩, hrows⟩ := hb
            have ht := PCS.V2.Csv.parseCsv_sound hcsv
            refine ⟨sp, ms, bm, bo, m, header, rows, iT, iC, hsp, hc, hms, hbm, hbo,
              decodeModel_sound hm, ht, hne, PCS.V2.Csv.indexOf_sound hiT,
              PCS.V2.Csv.indexOf_sound hiC, ?_, fun row hr => rowB_sound (hrows row hr)⟩
            intro hs
            rcases hpdE with hn | ⟨iE, hiE⟩
            · rw [hn] at hs; cases hs
            · exact ⟨iE, PCS.V2.Csv.indexOf_sound hiE⟩
          · cases hb
        · cases hb
      · cases hp
    · cases hp
  · cases hp


/-! ## Certified maximum reported concentration threshold -/

def isPkpdPeak (ev : JVal) : Bool :=
  isCheckType "pkpd_peak_concentration_threshold" ev

/-- Parameters of the committed-table concentration upper-bound check. -/
structure PeakSpec where
  model : String
  output : String
  concCol : String
  upper : Rat
  unit : String

def peakSpec (sp : List (String × JVal)) : Option PeakSpec :=
  match field sp "model_artifact", field sp "output_artifact",
      field sp "concentration_column", tolOf (field sp "upper_bound"), field sp "unit" with
  | some (.str m), some (.str o), some (.str cc), some ub, some (.str u) =>
      some ⟨m, o, cc, ub, u⟩
  | _, _, _, _, _ => none

/-- Read the model-declared concentration unit directly from the exact committed JSON bytes. -/
def modelConcentrationUnit (b : List UInt8) : Option String :=
  match parseJsonDoc b with
  | some (.obj ms) => pstr (pfield ms "concentration_unit")
  | _ => none

/-- Declarative meaning of one committed concentration cell satisfying the upper bound. -/
def PeakRowHolds (upper : Rat) (iC : Nat) (row : List Bytes) : Prop :=
  ∃ c, fieldQ row iC = some c ∧ 0 ≤ c ∧ c ≤ upper

def peakRowB (upper : Rat) (iC : Nat) (row : List Bytes) : Bool :=
  match fieldQ row iC with
  | some c => decide (0 ≤ c ∧ c ≤ upper)
  | none => false

theorem peakRowB_sound {upper : Rat} {iC : Nat} {row : List Bytes}
    (h : peakRowB upper iC row = true) : PeakRowHolds upper iC row := by
  unfold peakRowB at h
  split at h
  · rename_i c hc
    exact ⟨c, hc, (of_decide_eq_true h).1, (of_decide_eq_true h).2⟩
  · cases h

/-- **Meaning of a passing `pkpd_peak_concentration_threshold` item**:
    the model artifact satisfies the restricted PK/PD contract; the threshold unit is
    exactly the concentration unit declared by those committed model bytes; the output
    is a non-empty strict CSV table containing the named concentration column; and every
    committed concentration cell is an exact non-negative decimal not exceeding the
    committed upper bound. This is the maximum of the committed table, not a theorem
    about the continuous-time analytic trajectory or clinical safety. -/
def PkpdPeakHolds (req : ReplayRequest) : Prop :=
  ∃ sp ps bm bo m header rows iC,
    checkSpec req.evidence = some sp ∧
    strField sp "type" = some "pkpd_peak_concentration_threshold" ∧
    peakSpec sp = some ps ∧
    lookup req.artifacts ps.model = some bm ∧
    lookup req.artifacts ps.output = some bo ∧
    ModelContract bm.data.toList m ∧
    modelConcentrationUnit bm.data.toList = some ps.unit ∧
    PCS.V2.Csv.CsvTable bo.data.toList header rows ∧
    rows ≠ [] ∧
    header[iC]? = some ps.concCol.toUTF8.data.toList ∧
    ∀ row ∈ rows, PeakRowHolds ps.upper iC row

def peakB (ps : PeakSpec) (bm bo : ByteArray) : Bool :=
  match decodeModel bm.data.toList, modelConcentrationUnit bm.data.toList,
      PCS.V2.Csv.parseCsv bo.data.toList with
  | some _m, some u, some (header, rows) =>
    match PCS.V2.Csv.indexOf ps.concCol.toUTF8.data.toList header with
    | some iC =>
      !rows.isEmpty && decide (u = ps.unit) &&
        rows.all (peakRowB ps.upper iC)
    | none => false
  | _, _, _ => false

def pkpdPeakRun (req : ReplayRequest) : Observation :=
  match checkSpec req.evidence with
  | some sp =>
    match peakSpec sp with
    | some ps =>
      match lookup req.artifacts ps.model, lookup req.artifacts ps.output with
      | some bm, some bo =>
        ⟨.computationalTest, if peakB ps bm bo then .pass else .fail⟩
      | _, _ => ⟨.computationalTest, .fail⟩
    | none => ⟨.computationalTest, .fail⟩
  | none => ⟨.computationalTest, .fail⟩

theorem pkpdPeakRun_sound (req : ReplayRequest) (hc : isPkpdPeak req.evidence = true)
    (hp : (pkpdPeakRun req).outcome = .pass) : PkpdPeakHolds req := by
  unfold isPkpdPeak isCheckType at hc
  unfold pkpdPeakRun at hp
  split at hp
  · rename_i sp hsp
    rw [hsp] at hc
    simp only [decide_eq_true_eq] at hc
    split at hp
    · rename_i ps hps
      split at hp
      · rename_i bm bo hbm hbo
        have hb : peakB ps bm bo = true := by
          cases hh : peakB ps bm bo
          · rw [hh] at hp; cases hp
          · rfl
        unfold peakB at hb
        split at hb
        · rename_i m u header rows hm hu hcsv
          split at hb
          · rename_i iC hiC
            simp only [Bool.and_eq_true, Bool.not_eq_true',
              List.isEmpty_eq_false_iff, List.all_eq_true, decide_eq_true_eq] at hb
            obtain ⟨⟨hne, hunit⟩, hrows⟩ := hb
            have htable := PCS.V2.Csv.parseCsv_sound hcsv
            have hcol := PCS.V2.Csv.indexOf_sound hiC
            rw [hunit] at hu
            refine ⟨sp, ps, bm, bo, m, header, rows, iC, hsp, hc, hps, hbm, hbo,
              decodeModel_sound hm, hu, htable, hne, hcol, ?_⟩
            intro row hr
            exact peakRowB_sound (hrows row hr)
          · cases hb
        · cases hb
      · cases hp
    · cases hp
  · cases hp

end PCS.V2.PKPDCheck
