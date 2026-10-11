import Std

/-!
# CertIR syntax, the Rust interpreter transcription and type checking

Source-bound transcription of CertiForge `crates/certir/src/lib.rs` (types, `type_of`,
`Program::check`) and `crates/certir-interpreter/src/lib.rs` (`Value::bitvec`, `eval_binop`,
`eval_cmp_bv`, `eval_expr`, `eval`).  Rust `u64` arithmetic is modelled on `Nat` values below
`2^64` with explicit wrapping (`wrapping_add/sub/mul/neg`, `!`, `<<`, `>>`) and the explicit
width mask `& width.mask()`; the evaluation order (`lhs` then `rhs`, `cond` then the selected
branch only) and the error constructors are transcribed exactly.  The only abstraction is the
formatted text of the input-type-mismatch message, kept as a structured payload.

`typeOfPatched` is the proposed repair (boolean comparisons only `eq`/`ne`); see
`PCSForgeRefinement.Counterexample` for the original-checker counterexample.
-/

namespace PCSForgeRefinement

inductive Width where
  | u8 | u16 | u32 | u64
  deriving DecidableEq, Repr

def Width.bits : Width → Nat
  | .u8 => 8
  | .u16 => 16
  | .u32 => 32
  | .u64 => 64

/-- `Width::mask` (`u64::MAX` for `U64`). -/
def Width.mask (w : Width) : Nat := 2 ^ w.bits - 1

theorem Width.bits_le (w : Width) : w.bits ≤ 64 := by cases w <;> decide

inductive Ty where
  | bool
  | bv (w : Width)
  deriving DecidableEq, Repr

inductive BinOp where
  | add | sub | mul | and | or | xor | shl | lshr
  deriving DecidableEq, Repr

inductive CmpOp where
  | eq | ne | ult | ule | ugt | uge
  deriving DecidableEq, Repr

inductive UnOp where
  | not | neg
  deriving DecidableEq, Repr

inductive Expr where
  | constBool (value : Bool)
  | constBv (width : Width) (value : Nat)
  | var (name : String)
  | unop (op : UnOp) (e : Expr)
  | binop (op : BinOp) (lhs rhs : Expr)
  | cmp (op : CmpOp) (lhs rhs : Expr)
  | select (c t e : Expr)
  deriving DecidableEq, Repr

structure Param where
  name : String
  ty : Ty
  deriving DecidableEq, Repr

structure Program where
  name : String
  params : List Param
  body : Expr
  retTy : Ty
  deriving DecidableEq, Repr

/-- Decidable equality of `Except` results (used by executable checkers and controls). -/
instance instDecEqExcept {ε α : Type} [DecidableEq ε] [DecidableEq α] : DecidableEq (Except ε α) :=
  fun a b =>
    match a, b with
    | .ok x, .ok y => if h : x = y then isTrue (h ▸ rfl) else isFalse (fun e => h (by cases e; rfl))
    | .error x, .error y =>
        if h : x = y then isTrue (h ▸ rfl) else isFalse (fun e => h (by cases e; rfl))
    | .ok _, .error _ => isFalse (fun e => by cases e)
    | .error _, .ok _ => isFalse (fun e => by cases e)

/-! ## Rust `u64` primitives -/

def U64 : Nat := 2 ^ 64

def wrappingAdd (a b : Nat) : Nat := (a + b) % U64
def wrappingSub (a b : Nat) : Nat := (a + (U64 - b)) % U64
def wrappingMul (a b : Nat) : Nat := (a * b) % U64
def wrappingNeg (a : Nat) : Nat := (U64 - a) % U64
def u64Not (a : Nat) : Nat := U64 - 1 - a
/-- `a << b` on `u64` for `b < 64` (overflowing bits discarded). -/
def u64Shl (a b : Nat) : Nat := (a <<< b) % U64
def u64Shr (a b : Nat) : Nat := a >>> b

/-! ## Interpreter values -/

inductive Value where
  | bool (b : Bool)
  | bitvec (width : Width) (bits : Nat)
  deriving DecidableEq, Repr

/-- `Value::bitvec` masks its payload. -/
def Value.mk (w : Width) (bits : Nat) : Value := .bitvec w (bits &&& w.mask)

def Value.ty : Value → Ty
  | .bool _ => .bool
  | .bitvec w _ => .bv w

inductive EvalError where
  | undefinedVar (name : String)
  | runtime (msg : String)
  | inputMismatch (name : String)
  | arity (expected got : Nat)
  deriving DecidableEq, Repr

/-- `eval_binop`. -/
def evalBinop (op : BinOp) (w : Width) (a b : Nat) : Nat :=
  let a := a &&& w.mask
  let b := b &&& w.mask
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

/-- `eval_cmp_bv`. -/
def evalCmpBv (op : CmpOp) (a b : Nat) : Bool :=
  match op with
  | .eq => a == b
  | .ne => a != b
  | .ult => decide (a < b)
  | .ule => decide (a ≤ b)
  | .ugt => decide (a > b)
  | .uge => decide (a ≥ b)

/-- Interpreter store (`HashMap<String, Value>`): later insertions shadow earlier ones. -/
abbrev Store := List (String × Value)

def Store.get (σ : Store) (x : String) : Option Value := (σ.find? (·.1 == x)).map (·.2)

/-- `eval_expr`. -/
def evalExpr (σ : Store) : Expr → Except EvalError Value
  | .constBool b => .ok (.bool b)
  | .constBv w v => .ok (Value.mk w v)
  | .var x => match σ.get x with
    | some v => .ok v
    | none => .error (.undefinedVar x)
  | .unop op e => do
    let v ← evalExpr σ e
    match op, v with
    | .not, .bool b => .ok (.bool (!b))
    | .not, .bitvec w bits => .ok (Value.mk w (u64Not bits))
    | .neg, .bitvec w bits => .ok (Value.mk w (wrappingNeg bits))
    | _, _ => .error (.runtime "bad unop")
  | .binop op l r => do
    let lv ← evalExpr σ l
    let rv ← evalExpr σ r
    match lv, rv with
    | .bitvec w1 a, .bitvec w2 b =>
      if w1 = w2 then .ok (Value.mk w1 (evalBinop op w1 a b)) else .error (.runtime "bad binop")
    | _, _ => .error (.runtime "bad binop")
  | .cmp op l r => do
    let lv ← evalExpr σ l
    let rv ← evalExpr σ r
    match lv, rv with
    | .bitvec w1 a, .bitvec w2 b =>
      if w1 = w2 then .ok (.bool (evalCmpBv op a b)) else .error (.runtime "bad cmp")
    | .bool a, .bool b =>
      match op with
      | .eq => .ok (.bool (a == b))
      | .ne => .ok (.bool (a != b))
      | _ => .error (.runtime "bad bool cmp")
    | _, _ => .error (.runtime "bad cmp")
  | .select c t e => do
    let cv ← evalExpr σ c
    match cv with
    | .bool true => evalExpr σ t
    | .bool false => evalExpr σ e
    | _ => .error (.runtime "select cond not bool")

/-- Parameter binding loop of `eval` (type check per parameter, in order). -/
def bindInputs : List Param → List Value → Store → Except EvalError Store
  | p :: ps, v :: vs, σ =>
    if p.ty ≠ v.ty then .error (.inputMismatch p.name) else bindInputs ps vs ((p.name, v) :: σ)
  | _, _, σ => .ok σ

/-- `eval`. -/
def eval (p : Program) (inputs : List Value) : Except EvalError Value :=
  if inputs.length ≠ p.params.length then .error (.arity p.params.length inputs.length) else
  match bindInputs p.params inputs [] with
  | .error e => .error e
  | .ok σ => do
    let out ← evalExpr σ p.body
    if out.ty ≠ p.retTy then .error (.runtime "return type mismatch") else .ok out

/-! ## Type checking -/

inductive TypeError where
  | duplicateParam (name : String)
  | undefinedVar (name : String)
  | mismatch
  | badOperands
  deriving DecidableEq, Repr

abbrev Env := List (String × Ty)

/-- `lookup`: `env.iter().rev().find(..)` — the last binding wins. -/
def Env.lookup (env : Env) (x : String) : Option Ty := (env.reverse.find? (·.1 == x)).map (·.2)

/-- `type_of`, parameterised by whether boolean comparisons are restricted to `eq`/`ne`
(`patched = false` is the original source). -/
def typeOfG (patched : Bool) (env : Env) : Expr → Except TypeError Ty
  | .constBool _ => .ok .bool
  | .constBv w _ => .ok (.bv w)
  | .var x => match env.lookup x with
    | some t => .ok t
    | none => .error (.undefinedVar x)
  | .unop op e => do
    let t ← typeOfG patched env e
    match op, t with
    | .not, .bool => .ok .bool
    | .not, .bv w => .ok (.bv w)
    | .neg, .bv w => .ok (.bv w)
    | _, _ => .error .badOperands
  | .binop _ l r => do
    let tl ← typeOfG patched env l
    let tr ← typeOfG patched env r
    match tl, tr with
    | .bv w1, .bv w2 => if w1 = w2 then .ok (.bv w1) else .error .badOperands
    | _, _ => .error .badOperands
  | .cmp op l r => do
    let tl ← typeOfG patched env l
    let tr ← typeOfG patched env r
    match tl, tr with
    | .bv w1, .bv w2 => if w1 = w2 then .ok .bool else .error .badOperands
    | .bool, .bool =>
      if patched && !(op == .eq || op == .ne) then .error .badOperands else .ok .bool
    | _, _ => .error .badOperands
  | .select c t e => do
    let tc ← typeOfG patched env c
    if tc ≠ .bool then .error .mismatch else
    let tt ← typeOfG patched env t
    let te ← typeOfG patched env e
    if tt ≠ te then .error .mismatch else .ok tt

def Program.env (p : Program) : Env := p.params.map (fun q => (q.name, q.ty))

/-- `Program::check` (original when `patched = false`). -/
def Program.checkG (patched : Bool) (p : Program) : Except TypeError Unit :=
  if ¬ (p.params.map (·.name)).Nodup then .error (.duplicateParam "") else
  match typeOfG patched p.env p.body with
  | .error e => .error e
  | .ok t => if t ≠ p.retTy then .error .mismatch else .ok ()

/-- `forgeopt-cost::op_weight`. -/
def opWeight : BinOp → Nat
  | .and | .or | .xor => 1
  | .shl | .lshr => 1
  | .add | .sub => 2
  | .mul => 4

/-- `forgeopt-cost::expr_cost`. -/
def exprCost : Expr → Nat
  | .constBool _ | .constBv _ _ | .var _ => 0
  | .unop _ e => 1 + exprCost e
  | .binop op l r => opWeight op + exprCost l + exprCost r
  | .cmp _ l r => 2 + exprCost l + exprCost r
  | .select c t e => 3 + exprCost c + exprCost t + exprCost e

def programCost (p : Program) : Nat := exprCost p.body

end PCSForgeRefinement
