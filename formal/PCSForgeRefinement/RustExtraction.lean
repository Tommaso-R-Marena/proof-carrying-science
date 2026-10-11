import PCSForgeRefinement.RustSemantics
import PCSForgeRefinement.Rewrite

/-!
# Extraction soundness for the actual Rust CertIR interpreter

Values of the CertIR crates are represented as Rust runtime values (`RV`) by `encWidth`,
`encVal`, `encExpr`, `encStore`, `encRes`, following the `serde`-free in-memory layout of the
Rust enums (`Width::U8`, `Value::BitVec { width, bits }`, `Expr::BinOp { op, lhs, rhs }`, …).

`rust_certir_extraction_sound`: running the **source-bound extracted** `eval_expr` (with its
callees `Value::bitvec`, `eval_binop`, `eval_cmp_bv`, `Width::bits`, `Width::mask`) under the
Rust-subset semantics returns exactly the encoding of the Lean transcription `evalExpr`, for
every store and every expression, at every width, including every error path and the
evaluation order, given call-depth fuel at least `depth e + 4`.

Composed with `certir_eval_correspondence` and `rewrite_certificate_universally_sound`, every
accepted rewrite certificate preserves the behaviour of the actual Rust `eval_expr` on every
well-typed store (`rust_certificate_preserves_eval_expr`).
-/

namespace PCSForgeRefinement.Rust

open PCSForgeRefinement

def encWidth : Width → RV
  | .u8 => .ctor "Width" "U8" []
  | .u16 => .ctor "Width" "U16" []
  | .u32 => .ctor "Width" "U32" []
  | .u64 => .ctor "Width" "U64" []

def encBinOp : BinOp → RV
  | .add => .ctor "BinOp" "Add" []
  | .sub => .ctor "BinOp" "Sub" []
  | .mul => .ctor "BinOp" "Mul" []
  | .and => .ctor "BinOp" "And" []
  | .or => .ctor "BinOp" "Or" []
  | .xor => .ctor "BinOp" "Xor" []
  | .shl => .ctor "BinOp" "Shl" []
  | .lshr => .ctor "BinOp" "Lshr" []

def encCmpOp : CmpOp → RV
  | .eq => .ctor "CmpOp" "Eq" []
  | .ne => .ctor "CmpOp" "Ne" []
  | .ult => .ctor "CmpOp" "Ult" []
  | .ule => .ctor "CmpOp" "Ule" []
  | .ugt => .ctor "CmpOp" "Ugt" []
  | .uge => .ctor "CmpOp" "Uge" []

def encUnOp : UnOp → RV
  | .not => .ctor "UnOp" "Not" []
  | .neg => .ctor "UnOp" "Neg" []

def encVal : Value → RV
  | .bool b => .ctor "Value" "Bool" [.bool b]
  | .bitvec w bits => .strct "Value" "BitVec" [("width", encWidth w), ("bits", .int bits)]

def encExpr : Expr → RV
  | .constBool b => .strct "Expr" "ConstBool" [("value", .bool b)]
  | .constBv w x => .strct "Expr" "ConstBv" [("width", encWidth w), ("value", .int x)]
  | .var x => .strct "Expr" "Var" [("name", .str x)]
  | .unop op e => .strct "Expr" "UnOp" [("op", encUnOp op), ("expr", encExpr e)]
  | .binop op l r => .strct "Expr" "BinOp" [("op", encBinOp op), ("lhs", encExpr l), ("rhs", encExpr r)]
  | .cmp op l r => .strct "Expr" "Cmp" [("op", encCmpOp op), ("lhs", encExpr l), ("rhs", encExpr r)]
  | .select c t e =>
    .strct "Expr" "Select" [("cond", encExpr c), ("then_expr", encExpr t), ("else_expr", encExpr e)]

def encStore (σ : Store) : RV := .map (σ.map fun p => (p.1, encVal p.2))

/-- `EvalError` (the interpreter's `eval_expr` only produces these two variants). -/
def encErr : EvalError → RV
  | .undefinedVar x => .ctor "EvalError" "UndefinedVar" [.str x]
  | .runtime m => .ctor "EvalError" "Runtime" [.str m]
  | .inputMismatch x => .ctor "EvalError" "Runtime" [.str x]
  | .arity a b => .strct "EvalError" "Arity" [("expected", .int a), ("got", .int b)]

def encRes : Except EvalError Value → RV
  | .ok v => .ctor "" "Ok" [encVal v]
  | .error e => .ctor "" "Err" [encErr e]

def depth : Expr → Nat
  | .constBool _ | .constBv _ _ | .var _ => 0
  | .unop _ e => depth e + 1
  | .binop _ l r | .cmp _ l r => max (depth l) (depth r) + 1
  | .select c t e => max (depth c) (max (depth t) (depth e)) + 1

/-- Run the extracted `eval_expr`. -/
def rustEvalExpr (fuel : Nat) (σ : Store) (e : Expr) : Option Out :=
  runFn certirFns fuel ["eval_expr"] [encStore σ, encExpr e]


/-! ## The callees -/

theorem rust_width_bits (w : Width) (n : Nat) :
    runFn certirFns (n + 1) ["Width", "bits"] [encWidth w] = some (.val (.int w.bits)) := by
  cases w <;> rfl

theorem rust_width_mask (w : Width) (n : Nat) :
    runFn certirFns (n + 2) ["Width", "mask"] [encWidth w] = some (.val (.int w.mask)) := by
  cases w <;> rfl

theorem rust_value_bitvec (w : Width) (b n : Nat) :
    runFn certirFns (n + 3) ["Value", "bitvec"] [encWidth w, .int b] =
      some (.val (encVal (Value.mk w b))) := by
  cases w <;> rfl

theorem rust_eval_cmp_bv (op : CmpOp) (a b n : Nat) :
    runFn certirFns (n + 1) ["eval_cmp_bv"] [encCmpOp op, .int a, .int b] =
      some (.val (.bool (evalCmpBv op a b))) := by
  cases op <;> rfl

/-- `eval_binop` after its two input maskings. -/
def binopCore (op : BinOp) (w : Width) (a b : Nat) : Nat :=
  let r := match op with
    | .add => wrappingAdd a b
    | .sub => wrappingSub a b
    | .mul => wrappingMul a b
    | .and => a &&& b
    | .or => a ||| b
    | .xor => a ^^^ b
    | .shl => if b ≥ w.bits then 0 else u64Shl a b
    | .lshr => if b ≥ w.bits then 0 else u64Shr a b
  r &&& w.mask

theorem evalBinop_core (op : BinOp) (w : Width) (a b : Nat) :
    evalBinop op w a b = binopCore op w (a &&& w.mask) (b &&& w.mask) := rfl

/-- The `match op { … }` of `eval_binop`. -/
def binopMatch : RExpr :=
  match evalBinopFn.body with
  | .block (.cons _ _ (.cons _ _ (.cons _ _ (.cons _ e _)))) _ => e
  | _ => .lit 0 ""

/-- The rest of `eval_binop` once `mask`, `a`, `b` are bound (masked values `A`, `B`). -/
def binopTail (n : Nat) (op : BinOp) (w : Width) (a b A B : Nat) : Out :=
  fixRet (evalE (runFn certirFns (n + 2))
      [("b", .int B), ("a", .int A), ("mask", .int w.mask), ("op", encBinOp op), ("width", encWidth w),
       ("a", .int a), ("b", .int b)]
      (.block (.cons (.bind "r") binopMatch .nil) (.bin "&" (v "r") (v "mask"))) .val)

theorem binop_tail (op : BinOp) (w : Width) (a b n : Nat) :
    runFn certirFns (n + 3) ["eval_binop"] [encBinOp op, encWidth w, .int a, .int b] =
      some (binopTail n op w a b (a &&& w.mask) (b &&& w.mask)) := by
  cases w <;> rfl

theorem forall_lt_succ' {P : Nat → Prop} {n : Nat} (h : ∀ i, i < n → P i) (hn : P n) :
    ∀ i, i < n + 1 → P i := by
  intro i hi
  rcases Nat.lt_or_ge i n with h' | h'
  · exact h i h'
  · have : i = n := by omega
    subst this; exact hn

theorem forall_lt_zero' {P : Nat → Prop} : ∀ i, i < 0 → P i := fun _ h => absurd h (Nat.not_lt_zero _)

set_option maxHeartbeats 4000000 in
/-- The shift arms: the Rust guard `b >= u64::from(width.bits())` decided for every masked shift
amount (each amount below the width by evaluation, every larger amount uniformly). -/
theorem binop_tail_shift (w : Width) (a b n A B : Nat) (sh : BinOp) (hs : sh = .shl ∨ sh = .lshr) :
    binopTail n sh w a b A B = .val (.int (binopCore sh w A B)) := by
  rcases Nat.lt_or_ge B w.bits with h | h
  · revert B
    rcases hs with rfl | rfl <;> cases w <;>
    · simp only [Width.bits]
      repeat (first | exact forall_lt_zero' | (apply forall_lt_succ'; rotate_left; rfl))
  · obtain ⟨k, rfl⟩ := Nat.exists_eq_add_of_le' h
    rcases hs with rfl | rfl <;> cases w <;> rfl

theorem rust_eval_binop (op : BinOp) (w : Width) (a b n : Nat) :
    runFn certirFns (n + 3) ["eval_binop"] [encBinOp op, encWidth w, .int a, .int b] =
      some (.val (.int (evalBinop op w a b))) := by
  rw [binop_tail, evalBinop_core]
  cases op
  case shl => rw [binop_tail_shift _ _ _ _ _ _ _ (Or.inl rfl)]
  case lshr => rw [binop_tail_shift _ _ _ _ _ _ _ (Or.inr rfl)]
  all_goals cases w <;> rfl


/-! ## `eval_expr` -/

theorem callK_val {C : Caller} {f : List String} {ws : List RV} {w : RV} (k : RV → Out)
    (h : C f ws = some (.val w)) : callK C f ws k = k w := by
  unfold callK; rw [h]

theorem callK_val' {C : Caller} {f : List String} {ws : List RV} {w : RV}
    (h : C f ws = some (.val w)) : ∀ k, callK C f ws k = k w := fun k => callK_val k h

/-- The parameter bindings of `eval_expr(store, expr)`. -/
abbrev E0 (σ : Store) (e : Expr) : REnv := [("store", encStore σ), ("expr", encExpr e)]

abbrev E1b (σ : Store) (op : BinOp) (l r : Expr) : REnv :=
  ("op", encBinOp op) :: ("lhs", encExpr l) :: ("rhs", encExpr r) :: E0 σ (.binop op l r)

abbrev E1c (σ : Store) (op : CmpOp) (l r : Expr) : REnv :=
  ("op", encCmpOp op) :: ("lhs", encExpr l) :: ("rhs", encExpr r) :: E0 σ (.cmp op l r)

abbrev E1s (σ : Store) (c t e : Expr) : REnv :=
  ("cond", encExpr c) :: ("then_expr", encExpr t) :: ("else_expr", encExpr e) :: E0 σ (.select c t e)

/-- Shorthand for the recursive-call hypothesis at fuel `j + 3`. -/
abbrev RecOK (σ : Store) (j : Nat) (e : Expr) : Prop :=
  runFn certirFns (j + 3) ["eval_expr"] [encStore σ, encExpr e] = some (.val (encRes (evalExpr σ e)))

abbrev Goal (σ : Store) (j : Nat) (e : Expr) : Prop :=
  runFn certirFns (j + 4) ["eval_expr"] [encStore σ, encExpr e] = some (.val (encRes (evalExpr σ e)))

theorem eval_expr_constBool (σ : Store) (b : Bool) (j : Nat) : Goal σ j (.constBool b) := rfl

theorem eval_expr_constBv (σ : Store) (w : Width) (x : Nat) (j : Nat) : Goal σ j (.constBv w x) := by
  cases w <;> rfl

theorem find_encStore (σ : Store) (x : String) :
    (σ.map fun p => (p.1, encVal p.2)).find? (fun kv => kv.1 == x) =
      (σ.find? (fun p => p.1 == x)).map (fun p => (p.1, encVal p.2)) := by
  rw [List.find?_map]; rfl

theorem eval_expr_var (σ : Store) (x : String) (j : Nat) : Goal σ j (.var x) := by
  show some (fixRet (okOrElseK
    (match (σ.map fun p => (p.1, encVal p.2)).find? (fun kv => kv.1 == x) with
      | some (_, y) => RV.ctor "" "Some" [y]
      | none => RV.ctor "" "None" [])
    (fun k' => evalE (runFn certirFns (j + 3)) (("name", .str x) :: E0 σ (.var x))
      (cl ["EvalError", "UndefinedVar"] [mc (v "name") "clone"]) k') .val)) = _
  rw [find_encStore]
  simp only [evalExpr, Store.get]
  cases σ.find? (fun p => p.1 == x) with
  | none => rfl
  | some p => rfl

theorem eval_expr_unop (σ : Store) (op : UnOp) (e1 : Expr) (j : Nat) (ih : RecOK σ j e1) :
    Goal σ j (.unop op e1) := by
  show some (fixRet (callK (runFn certirFns (j + 3)) ["eval_expr"] [encStore σ, encExpr e1]
    (fun w => qK w (fun x => evalE (runFn certirFns (j + 3))
      (("v", x) :: ("op", encUnOp op) :: ("expr", encExpr e1) :: E0 σ (.unop op e1)) unopMatchE .val)))) = _
  rw [callK_val _ ih]
  simp only [evalExpr]
  cases evalExpr σ e1 with
  | error err => rfl
  | ok val =>
    cases op <;> cases val with
    | bool b => rfl
    | bitvec w bits => cases w <;> rfl

set_option hygiene false in
local macro "binop_arm_tac" W:term : tactic => `(tactic| (
  show callK (runFn certirFns (j + 3)) ["eval_binop"] [encBinOp op, encWidth $W, .int a, .int b]
    (fun x => evalE (runFn certirFns (j + 3)) (("$r", x) :: ("w1", encWidth $W) :: ("a", .int a) ::
      ("w2", encWidth $W) :: ("b", .int b) :: ("r", encVal (.bitvec $W b)) :: ("l", encVal (.bitvec $W a)) ::
      E1b σ op l r) (cl ["Ok"] [cl ["Value", "bitvec"] [v "w1", v "$r"]]) .val) = _
  rw [callK_val _ (rust_eval_binop _ _ _ _ _)]
  rfl))

/-- The guarded arm `(BitVec{w1,a}, BitVec{w2,b}) if w1 == w2 => Ok(Value::bitvec(w1, eval_binop(…)))`. -/
theorem binop_arm (σ : Store) (op : BinOp) (l r : Expr) (j : Nat) (w : Width) (a b : Nat) :
    evalE (runFn certirFns (j + 3)) (("r", encVal (.bitvec w b)) :: ("l", encVal (.bitvec w a)) :: E1b σ op l r)
      binopMatchE .val = .val (encRes (.ok (Value.mk w (evalBinop op w a b)))) := by
  cases w
  · binop_arm_tac .u8
  · binop_arm_tac .u16
  · binop_arm_tac .u32
  · binop_arm_tac .u64

theorem eval_expr_binop (σ : Store) (op : BinOp) (l r : Expr) (j : Nat) (ihl : RecOK σ j l)
    (ihr : RecOK σ j r) : Goal σ j (.binop op l r) := by
  show some (fixRet (callK (runFn certirFns (j + 3)) ["eval_expr"] [encStore σ, encExpr l]
    (fun w => qK w (fun lv => callK (runFn certirFns (j + 3)) ["eval_expr"] [encStore σ, encExpr r]
      (fun w' => qK w' (fun rv => evalE (runFn certirFns (j + 3))
        (("r", rv) :: ("l", lv) :: E1b σ op l r) binopMatchE .val)))))) = _
  simp only [callK_val' ihl, callK_val' ihr, evalExpr]
  cases evalExpr σ l with
  | error err => rfl
  | ok lv =>
    cases evalExpr σ r with
    | error err => rfl
    | ok rv =>
      cases lv with
      | bool x => cases rv with
        | bool y => rfl
        | bitvec w2 b => cases w2 <;> rfl
      | bitvec w1 a => cases rv with
        | bool y => cases w1 <;> rfl
        | bitvec w2 b =>
          by_cases hw : w1 = w2
          · subst hw
            have := binop_arm σ op l r j w1 a b
            simp only [qK, encRes, encVal] at this ⊢
            rw [this]
            cases w1 <;> rfl
          · cases w1 <;> cases w2 <;> first | rfl | exact absurd rfl hw

theorem eval_expr_cmp (σ : Store) (op : CmpOp) (l r : Expr) (j : Nat) (ihl : RecOK σ j l)
    (ihr : RecOK σ j r) : Goal σ j (.cmp op l r) := by
  show some (fixRet (callK (runFn certirFns (j + 3)) ["eval_expr"] [encStore σ, encExpr l]
    (fun w => qK w (fun lv => callK (runFn certirFns (j + 3)) ["eval_expr"] [encStore σ, encExpr r]
      (fun w' => qK w' (fun rv => evalE (runFn certirFns (j + 3))
        (("r", rv) :: ("l", lv) :: E1c σ op l r) cmpMatchE .val)))))) = _
  simp only [callK_val' ihl, callK_val' ihr, evalExpr]
  cases evalExpr σ l with
  | error err => rfl
  | ok lv =>
    cases evalExpr σ r with
    | error err => rfl
    | ok rv =>
      cases lv with
      | bool x => cases rv with
        | bool y => cases op <;> rfl
        | bitvec w2 b => cases w2 <;> rfl
      | bitvec w1 a => cases rv with
        | bool y => cases w1 <;> rfl
        | bitvec w2 b => cases op <;> cases w1 <;> cases w2 <;> rfl

theorem eval_expr_select (σ : Store) (c t e : Expr) (j : Nat) (ihc : RecOK σ j c)
    (iht : RecOK σ j t) (ihe : RecOK σ j e) : Goal σ j (.select c t e) := by
  show some (fixRet (callK (runFn certirFns (j + 3)) ["eval_expr"] [encStore σ, encExpr c]
    (fun w => qK w (fun cv => evalArms (runFn certirFns (j + 3)) (E1s σ c t e) cv selectArmsE .val)))) = _
  rw [callK_val _ ihc]
  simp only [evalExpr]
  cases evalExpr σ c with
  | error err => rfl
  | ok cv =>
    cases cv with
    | bool b =>
      cases b
      · show some (fixRet (callK (runFn certirFns (j + 3)) ["eval_expr"] [encStore σ, encExpr e] .val)) = _
        rw [callK_val _ ihe]; rfl
      · show some (fixRet (callK (runFn certirFns (j + 3)) ["eval_expr"] [encStore σ, encExpr t] .val)) = _
        rw [callK_val _ iht]; rfl
    | bitvec w bits => cases w <;> rfl

/-- **Extraction soundness of the Rust CertIR interpreter.**  For every store, every
expression and every call-depth fuel `≥ depth e + 4`, the source-bound extracted `eval_expr`
(`interp_eval_expr_source_bound`) run under the Rust-subset semantics returns exactly the
encoding of the Lean `evalExpr` — the same value or the same error, at every width, with
oversized shift amounts, wrapping arithmetic, `?`-propagation of the first error in
left-to-right order, and lazy `select`. -/
theorem rust_certir_extraction_sound (σ : Store) (e : Expr) (fuel : Nat) (hfuel : depth e + 4 ≤ fuel) :
    runFn certirFns fuel ["eval_expr"] [encStore σ, encExpr e] = some (.val (encRes (evalExpr σ e))) := by
  obtain ⟨j, rfl, hj⟩ : ∃ j, fuel = j + 4 ∧ depth e ≤ j := ⟨fuel - 4, by omega, by omega⟩
  clear hfuel
  induction e generalizing j with
  | constBool b => exact eval_expr_constBool σ b j
  | constBv w x => exact eval_expr_constBv σ w x j
  | var x => exact eval_expr_var σ x j
  | unop op e1 ih =>
    obtain ⟨j', rfl⟩ : ∃ j', j = j' + 1 := ⟨j - 1, by simp only [depth] at hj; omega⟩
    exact eval_expr_unop σ op e1 (j' + 1) (ih j' (by simp only [depth] at hj; omega))
  | binop op l r ihl ihr =>
    obtain ⟨j', rfl⟩ : ∃ j', j = j' + 1 := ⟨j - 1, by simp only [depth] at hj; omega⟩
    have h1 : depth l ≤ j' := by simp only [depth] at hj; have := Nat.le_max_left (depth l) (depth r); omega
    have h2 : depth r ≤ j' := by simp only [depth] at hj; have := Nat.le_max_right (depth l) (depth r); omega
    exact eval_expr_binop σ op l r (j' + 1) (ihl j' h1) (ihr j' h2)
  | cmp op l r ihl ihr =>
    obtain ⟨j', rfl⟩ : ∃ j', j = j' + 1 := ⟨j - 1, by simp only [depth] at hj; omega⟩
    have h1 : depth l ≤ j' := by simp only [depth] at hj; have := Nat.le_max_left (depth l) (depth r); omega
    have h2 : depth r ≤ j' := by simp only [depth] at hj; have := Nat.le_max_right (depth l) (depth r); omega
    exact eval_expr_cmp σ op l r (j' + 1) (ihl j' h1) (ihr j' h2)
  | select c t e ihc iht ihe =>
    obtain ⟨j', rfl⟩ : ∃ j', j = j' + 1 := ⟨j - 1, by simp only [depth] at hj; omega⟩
    have hm1 := Nat.le_max_left (depth c) (max (depth t) (depth e))
    have hm2 := Nat.le_max_left (depth t) (depth e)
    have hm3 := Nat.le_max_right (depth t) (depth e)
    have hm4 := Nat.le_max_right (depth c) (max (depth t) (depth e))
    simp only [depth] at hj
    exact eval_expr_select σ c t e (j' + 1) (ihc j' (by omega)) (iht j' (by omega)) (ihe j' (by omega))


/-- **Composition with certificate soundness.**  For every accepted rewrite certificate and every
well-typed store, the actual (source-bound, extracted) Rust `eval_expr` returns the same result on
the optimized candidate as on the original expression — for every width `u8 … u64`. -/
theorem rust_certificate_preserves_eval_expr {c : Cert} (h : checkCert c = true) (δ : DStore)
    (hwt : WTStore c.original.env δ) (f1 f2 : Nat) (h1 : depth c.candidate.body + 4 ≤ f1)
    (h2 : depth c.original.body + 4 ≤ f2) :
    runFn certirFns f1 ["eval_expr"] [encStore (PCSForgeRefinement.encStore δ), encExpr c.candidate.body] =
      runFn certirFns f2 ["eval_expr"] [encStore (PCSForgeRefinement.encStore δ), encExpr c.original.body] := by
  rw [rust_certir_extraction_sound _ _ _ h1, rust_certir_extraction_sound _ _ _ h2,
    certir_eval_correspondence, certir_eval_correspondence, (rewrite_certificate_universally_sound h).2 δ hwt]

end PCSForgeRefinement.Rust
