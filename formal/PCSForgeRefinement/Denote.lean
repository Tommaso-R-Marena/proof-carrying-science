import PCSForgeRefinement.Syntax

/-!
# Mathematical denotation of CertIR and the Rust-interpreter correspondence

`denote` interprets CertIR with Lean's `BitVec w` (modular arithmetic, bitwise operations,
unbounded mathematical shifts `x <<< n`, `x >>> n`), defined independently of the `u64`
wrapping/masking code of the Rust interpreter transcription `evalExpr`.

`certir_eval_correspondence`: for every expression and every store, running the transcribed
Rust interpreter on the encoded store gives exactly the encoding of the denotation —
including every error path and the evaluation order.  This covers every width `u8 … u64`,
`wrapping_add/sub/mul/neg`, `!`, and oversized shift amounts (the Rust guard
`b ≥ width.bits() ⇒ 0` coincides with the mathematical shift).
-/

namespace PCSForgeRefinement

/-- Denotational values: booleans and width-indexed bit vectors. -/
inductive DVal where
  | bool (b : Bool)
  | bv (w : Width) (x : BitVec w.bits)

def DVal.enc : DVal → Value
  | .bool b => .bool b
  | .bv w x => .bitvec w x.toNat

def DVal.ty : DVal → Ty
  | .bool _ => .bool
  | .bv w _ => .bv w

theorem DVal.ty_enc (v : DVal) : v.enc.ty = v.ty := by cases v <;> rfl

abbrev DStore := List (String × DVal)

def DStore.get (σ : DStore) (x : String) : Option DVal := (σ.find? (·.1 == x)).map (·.2)

def encStore (σ : DStore) : Store := σ.map (fun p => (p.1, p.2.enc))

theorem get_encStore (σ : DStore) (x : String) : (encStore σ).get x = (σ.get x).map DVal.enc := by
  induction σ with
  | nil => rfl
  | cons p σ ih =>
      simp only [encStore, List.map_cons, Store.get, DStore.get, List.find?_cons] at ih ⊢
      by_cases h : (p.1 == x) = true
      · simp [h]
      · simp only [h]; exact ih

def denBin (op : BinOp) {n : Nat} (x y : BitVec n) : BitVec n :=
  match op with
  | .add => x + y
  | .sub => x - y
  | .mul => x * y
  | .and => x &&& y
  | .or => x ||| y
  | .xor => x ^^^ y
  | .shl => x <<< y.toNat
  | .lshr => x >>> y.toNat

def denCmp (op : CmpOp) {n : Nat} (x y : BitVec n) : Bool :=
  match op with
  | .eq => x == y
  | .ne => x != y
  | .ult => x.ult y
  | .ule => x.ule y
  | .ugt => y.ult x
  | .uge => y.ule x

/-- The denotation (same control structure and error discipline, mathematical arithmetic). -/
def denote (σ : DStore) : Expr → Except EvalError DVal
  | .constBool b => .ok (.bool b)
  | .constBv w v => .ok (.bv w (BitVec.ofNat w.bits v))
  | .var x => match σ.get x with
    | some v => .ok v
    | none => .error (.undefinedVar x)
  | .unop op e => do
    let v ← denote σ e
    match op, v with
    | .not, .bool b => .ok (.bool (!b))
    | .not, .bv w x => .ok (.bv w (~~~x))
    | .neg, .bv w x => .ok (.bv w (-x))
    | _, _ => .error (.runtime "bad unop")
  | .binop op l r => do
    let lv ← denote σ l
    let rv ← denote σ r
    match lv, rv with
    | .bv w1 a, .bv w2 b =>
      if h : w1 = w2 then .ok (.bv w1 (denBin op a (h ▸ b))) else .error (.runtime "bad binop")
    | _, _ => .error (.runtime "bad binop")
  | .cmp op l r => do
    let lv ← denote σ l
    let rv ← denote σ r
    match lv, rv with
    | .bv w1 a, .bv w2 b =>
      if h : w1 = w2 then .ok (.bool (denCmp op a (h ▸ b))) else .error (.runtime "bad cmp")
    | .bool a, .bool b =>
      match op with
      | .eq => .ok (.bool (a == b))
      | .ne => .ok (.bool (a != b))
      | _ => .error (.runtime "bad bool cmp")
    | _, _ => .error (.runtime "bad cmp")
  | .select c t e => do
    let cv ← denote σ c
    match cv with
    | .bool true => denote σ t
    | .bool false => denote σ e
    | _ => .error (.runtime "select cond not bool")

/-! ## Arithmetic bridge lemmas -/

section Arith

theorem mask_eq_mod (w : Width) (z : Nat) : z &&& w.mask = z % 2 ^ w.bits :=
  Nat.and_two_pow_sub_one_eq_mod z w.bits

theorem pow_dvd_U64 (w : Width) : 2 ^ w.bits ∣ U64 := Nat.pow_dvd_pow 2 w.bits_le

theorem mod_U64_mod (w : Width) (z : Nat) : z % U64 % 2 ^ w.bits = z % 2 ^ w.bits :=
  Nat.mod_mod_of_dvd z (pow_dvd_U64 w)

/-- `U64 = 2^w · M` with `M ≥ 1`. -/
theorem U64_split (w : Width) : ∃ t, U64 = 2 ^ w.bits + 2 ^ w.bits * t := by
  obtain ⟨M, hM⟩ := pow_dvd_U64 w
  have hpos : 0 < M := by
    rcases Nat.eq_zero_or_pos M with h | h
    · rw [h] at hM; simp [U64] at hM
    · exact h
  refine ⟨M - 1, ?_⟩
  rw [hM]
  have : M = (M - 1) + 1 := by omega
  conv => lhs; rw [this]
  rw [Nat.mul_add, Nat.mul_one, Nat.add_comm]

theorem lt_pow (w : Width) {n : Nat} (x : BitVec n) (h : n = w.bits) : x.toNat < 2 ^ w.bits := by
  subst h; exact x.isLt

theorem mod_self_lt {z K : Nat} (h : z < K) : z % K = z := Nat.mod_eq_of_lt h

theorem mask_of_lt (w : Width) {z : Nat} (h : z < 2 ^ w.bits) : z &&& w.mask = z := by
  rw [mask_eq_mod, Nat.mod_eq_of_lt h]

theorem not_correct (w : Width) (x : BitVec w.bits) :
    (u64Not x.toNat) &&& w.mask = (~~~x).toNat := by
  rw [mask_eq_mod, BitVec.toNat_not]
  obtain ⟨t, ht⟩ := U64_split w
  have hx := x.isLt
  unfold u64Not
  rw [ht]
  have : 2 ^ w.bits + 2 ^ w.bits * t - 1 - x.toNat = (2 ^ w.bits - 1 - x.toNat) + 2 ^ w.bits * t := by
    omega
  rw [this, Nat.add_mul_mod_self_left, Nat.mod_eq_of_lt (by omega)]

theorem neg_correct (w : Width) (x : BitVec w.bits) :
    (wrappingNeg x.toNat) &&& w.mask = (-x).toNat := by
  rw [mask_eq_mod, BitVec.toNat_neg]
  unfold wrappingNeg
  rw [mod_U64_mod]
  obtain ⟨t, ht⟩ := U64_split w
  have hx := x.isLt
  rw [ht]
  have : 2 ^ w.bits + 2 ^ w.bits * t - x.toNat = (2 ^ w.bits - x.toNat) + 2 ^ w.bits * t := by omega
  rw [this, Nat.add_mul_mod_self_left]

theorem const_correct (w : Width) (v : Nat) : v &&& w.mask = (BitVec.ofNat w.bits v).toNat := by
  rw [mask_eq_mod, BitVec.toNat_ofNat]

theorem binop_correct (op : BinOp) (w : Width) (x y : BitVec w.bits) :
    evalBinop op w x.toNat y.toNat = (denBin op x y).toNat := by
  have hx := x.isLt
  have hy := y.isLt
  unfold evalBinop
  simp only [mask_of_lt w hx, mask_of_lt w hy]
  rw [mask_eq_mod]
  cases op with
  | add => simp only [denBin, wrappingAdd, mod_U64_mod, BitVec.toNat_add]
  | sub =>
      simp only [denBin, wrappingSub, mod_U64_mod, BitVec.toNat_sub]
      obtain ⟨t, ht⟩ := U64_split w
      rw [ht]
      have : x.toNat + (2 ^ w.bits + 2 ^ w.bits * t - y.toNat) =
          (2 ^ w.bits - y.toNat + x.toNat) + 2 ^ w.bits * t := by omega
      rw [this, Nat.add_mul_mod_self_left]
  | mul => simp only [denBin, wrappingMul, mod_U64_mod, BitVec.toNat_mul]
  | and =>
      simp only [denBin, BitVec.toNat_and]
      exact Nat.mod_eq_of_lt (Nat.and_lt_two_pow _ hy)
  | or =>
      simp only [denBin, BitVec.toNat_or]
      exact Nat.mod_eq_of_lt (Nat.or_lt_two_pow hx hy)
  | xor =>
      simp only [denBin, BitVec.toNat_xor]
      exact Nat.mod_eq_of_lt (Nat.xor_lt_two_pow hx hy)
  | shl =>
      simp only [denBin, BitVec.toNat_shiftLeft]
      split
      · rename_i hb
        rw [Nat.zero_mod, Nat.shiftLeft_eq]
        exact (Nat.mod_eq_zero_of_dvd (Nat.dvd_trans (Nat.pow_dvd_pow 2 hb)
          (Nat.dvd_mul_left _ _))).symm
      · simp only [u64Shl, mod_U64_mod]
  | lshr =>
      simp only [denBin, BitVec.toNat_ushiftRight]
      split
      · rename_i hb
        rw [Nat.zero_mod, Nat.shiftRight_eq_div_pow]
        exact (Nat.div_eq_of_lt (Nat.lt_of_lt_of_le hx (Nat.pow_le_pow_right (by decide) hb))).symm
      · simp only [u64Shr]
        exact Nat.mod_eq_of_lt (Nat.lt_of_le_of_lt (Nat.shiftRight_le _ _) hx)

theorem cmp_correct (op : CmpOp) {n : Nat} (x y : BitVec n) :
    evalCmpBv op x.toNat y.toNat = denCmp op x y := by
  cases op
  · simp only [evalCmpBv, denCmp]; rw [Bool.eq_iff_iff, beq_iff_eq, beq_iff_eq, BitVec.toNat_eq]
  · simp only [evalCmpBv, denCmp, bne]; congr 1
    rw [Bool.eq_iff_iff, beq_iff_eq, beq_iff_eq, BitVec.toNat_eq]
  · simp [evalCmpBv, denCmp, BitVec.ult]
  · simp [evalCmpBv, denCmp, BitVec.ule]
  · simp [evalCmpBv, denCmp, BitVec.ult]
  · simp [evalCmpBv, denCmp, BitVec.ule]

end Arith

/-! ## Correspondence -/

theorem mk_toNat (w : Width) (x : BitVec w.bits) : Value.mk w x.toNat = .bitvec w x.toNat := by
  simp [Value.mk, mask_of_lt w x.isLt]

/-- **Rust interpreter ↔ mathematical denotation**, all expressions, all stores, all widths,
success and failure. -/
theorem certir_eval_correspondence (σ : DStore) (e : Expr) :
    evalExpr (encStore σ) e = (denote σ e).map DVal.enc := by
  induction e with
  | constBool b => rfl
  | constBv w v =>
      simp only [evalExpr, denote, Except.map, DVal.enc, Value.mk, const_correct]
  | var x =>
      simp only [evalExpr, denote, get_encStore]
      cases σ.get x <;> rfl
  | unop op e ih =>
      simp only [evalExpr, denote, ih]
      cases denote σ e with
      | error err => rfl
      | ok v =>
          cases op <;> cases v <;>
            simp [Except.map, bind, Except.bind, DVal.enc, Value.mk, not_correct, neg_correct]
  | binop op l r ihl ihr =>
      simp only [evalExpr, denote, ihl, ihr]
      cases denote σ l with
      | error err => rfl
      | ok lv =>
          cases denote σ r with
          | error err => cases lv <;> rfl
          | ok rv =>
              cases lv with
              | bool a => cases rv <;> rfl
              | bv w1 a =>
                  cases rv with
                  | bool b => rfl
                  | bv w2 b =>
                      by_cases h : w1 = w2
                      · subst h
                        simp [Except.map, bind, Except.bind, DVal.enc, binop_correct, mk_toNat]
                      · simp [Except.map, bind, Except.bind, DVal.enc, h]
  | cmp op l r ihl ihr =>
      simp only [evalExpr, denote, ihl, ihr]
      cases denote σ l with
      | error err => rfl
      | ok lv =>
          cases denote σ r with
          | error err => cases lv <;> rfl
          | ok rv =>
              cases lv with
              | bool a => cases rv <;> cases op <;> rfl
              | bv w1 a =>
                  cases rv with
                  | bool b => rfl
                  | bv w2 b =>
                      by_cases h : w1 = w2
                      · subst h
                        simp [Except.map, bind, Except.bind, DVal.enc, cmp_correct]
                      · simp [Except.map, bind, Except.bind, DVal.enc, h]
  | select c t e ihc iht ihe =>
      simp only [evalExpr, denote, ihc, iht, ihe]
      cases denote σ c with
      | error err => rfl
      | ok cv =>
          cases cv with
          | bool b => cases b <;> rfl
          | bv w x => rfl

end PCSForgeRefinement
