import PCSForgeRefinement.RustSyntax

/-!
# Operational semantics of the supported Rust subset

An executable big-step semantics for the Rust fragment of `PCSForgeRefinement.RustSyntax`,
defined from Rust's language rules (not from the CertIR transcription):

* values: integers (the bound windows compute in `u64`; the `u32` results of `Width::bits`
  flow only into `u64::from`, `== 64` and shift amounts), `bool`, string slices/`String`s,
  enum tuple variants and unit variants (`ctor ty variant args`), enum struct variants
  (`strct ty variant fields`), tuples and `HashMap<String, _>` (`map`).  References and `Box`
  are transparent (`*e`, auto-deref, default binding modes);
* left-to-right evaluation of operands, arguments, struct fields and `let` statements;
* `?` on `Result` performs an early return of the `Err`, propagated as the `ret` outcome up to
  the enclosing function call;
* `match` tries the arms in source order; a guard is evaluated after its pattern bound;
* integer operators are Rust's `u64` operators in debug mode: `-` and `<<`/`>>` with a shift
  amount `≥ 64` panic (`stuck`), `wrapping_*` wrap modulo `2^64`, `!` is bitwise complement;
* `Option::copied`, `clone`, `into` are identities on values; `HashMap::get` returns
  `Some(v)`/`None`; `ok_or_else(|| e)` evaluates its closure body only on `None`;
* a call of a path that is not a user function is an enum tuple-variant constructor
  (`Ok`, `Err`, `Value::Bool`, `EvalError::Runtime`, …); method calls on enum values
  dispatch to the inherent method `Type::name`.

User functions are run by `runFn` with explicit call-depth fuel; running out of fuel is an
explicit `stuck "fuel"` outcome, never a fabricated value.
-/

namespace PCSForgeRefinement.Rust

inductive RV where
  | int (n : Nat)
  | bool (b : Bool)
  | str (s : String)
  | ctor (ty var : String) (args : List RV)
  | strct (ty var : String) (fields : List (String × RV))
  | tuple (vs : List RV)
  | map (kvs : List (String × RV))

/-- Outcome of evaluating an expression: a value, an early `return` (from `?`), or a stuck
state (panic, type error, missing arm, exhausted fuel). -/
inductive Out where
  | val (v : RV)
  | ret (v : RV)
  | stuck (why : String)

abbrev REnv := List (String × RV)

def REnv.get (env : REnv) (x : String) : Option RV := (env.find? (·.1 == x)).map (·.2)

/-- `Type::Variant` or a prelude variant (`Ok`, `Err`, `Some`, `None`). -/
def pathParts : List String → String × String
  | [x] => ("", x)
  | [t, x] => (t, x)
  | _ => ("?", "?")

/-- `==` on the comparable values of the fragment (integers, booleans, unit variants). -/
def RV.eqv : RV → RV → Option Bool
  | .int a, .int b => some (a == b)
  | .bool a, .bool b => some (a == b)
  | .ctor t x [], .ctor t' x' [] => some (t == t' && x == x')
  | _, _ => none

def M64 : Nat := 2 ^ 64

/-- Rust binary operators on `u64` / `bool` (debug-mode overflow checks). -/
def binOpSem (op : String) (a b : RV) : Out :=
  if op = "==" then (match a.eqv b with
    | some r => .val (.bool r)
    | none => .stuck "==")
  else if op = "!=" then (match a.eqv b with
    | some r => .val (.bool (!r))
    | none => .stuck "!=")
  else match a, b with
  | .int x, .int y =>
    if op = "&" then .val (.int (x &&& y))
    else if op = "|" then .val (.int (x ||| y))
    else if op = "^" then .val (.int (x ^^^ y))
    else if op = "<<" then (if y < 64 then .val (.int ((x <<< y) % M64)) else .stuck "shl overflow")
    else if op = ">>" then (if y < 64 then .val (.int (x >>> y)) else .stuck "shr overflow")
    else if op = "-" then (if y ≤ x then .val (.int (x - y)) else .stuck "sub overflow")
    else if op = "<" then .val (.bool (decide (x < y)))
    else if op = "<=" then .val (.bool (decide (x ≤ y)))
    else if op = ">" then .val (.bool (decide (x > y)))
    else if op = ">=" then .val (.bool (decide (x ≥ y)))
    else .stuck "binop"
  | _, _ => .stuck "binop"

/-- Built-in methods (`None` = not built in: dispatch to a user method). -/
def methodSem (m : String) (r : RV) (args : List RV) : Option Out :=
  if m = "copied" ∨ m = "clone" ∨ m = "into" then
    (match args with
      | [] => some (.val r)
      | _ => some (.stuck "arity"))
  else if m = "get" then
    (match r, args with
      | .map kvs, [.str k] => some (.val (match (kvs.find? (·.1 == k)) with
        | some (_, x) => .ctor "" "Some" [x]
        | none => .ctor "" "None" []))
      | _, _ => some (.stuck "get"))
  else match r, args with
  | .int a, [.int b] =>
    if m = "wrapping_add" then some (.val (.int ((a + b) % M64)))
    else if m = "wrapping_sub" then some (.val (.int ((a + (M64 - b)) % M64)))
    else if m = "wrapping_mul" then some (.val (.int ((a * b) % M64)))
    else none
  | .int a, [] => if m = "wrapping_neg" then some (.val (.int ((M64 - a) % M64))) else none
  | _, _ => none

mutual
def matchPat : RPat → RV → Option REnv
  | .wild, _ => some []
  | .bind x, w => some [(x, w)]
  | .litBool b, .bool b' => if b == b' then some [] else none
  | .path p, .ctor t x [] => if pathParts p == (t, x) then some [] else none
  | .tupleS p qs, .ctor t x args => if pathParts p == (t, x) then matchPats qs args else none
  | .structS p fqs _ _, .strct t x flds => if pathParts p == (t, x) then matchFields fqs flds else none
  | .tuple qs, .tuple ws => matchPats qs ws
  | _, _ => none
def matchPats : RPats → List RV → Option REnv
  | .nil, [] => some []
  | .cons q qs, w :: ws =>
    match matchPat q w, matchPats qs ws with
    | some b1, some b2 => some (b1 ++ b2)
    | _, _ => none
  | _, _ => none
def matchFields : RFPats → List (String × RV) → Option REnv
  | .nil, _ => some []
  | .cons n q rest, flds =>
    match flds.find? (·.1 == n) with
    | some (_, w) =>
      match matchPat q w, matchFields rest flds with
      | some b1, some b2 => some (b1 ++ b2)
      | _, _ => none
    | none => none
end

/-- How user functions are invoked: `none` when the path is not a user function. -/
abbrev Caller := List String → List RV → Option Out

/-- Continue with the value of a call: user function result, `u64::from`, or a tuple-variant
constructor.  A user function's non-value outcome (stuck) aborts. -/
def callK (call : Caller) (f : List String) (ws : List RV) (k : RV → Out) : Out :=
  match call f ws with
  | some (.val w) => k w
  | some o => o
  | none =>
    if f == ["u64", "from"] then
      (match ws with
        | [.int n] => k (.int n)
        | _ => .stuck "from")
    else k (.ctor (pathParts f).1 (pathParts f).2 ws)

def methodK (call : Caller) (m : String) (rv : RV) (ws : List RV) (k : RV → Out) : Out :=
  match methodSem m rv ws with
  | some (.val w) => k w
  | some o => o
  | none => match rv with
    | .ctor t _ _ => (match call [t, m] (rv :: ws) with
      | some (.val w) => k w
      | some o => o
      | none => .stuck "no method")
    | _ => .stuck "no method"

def binK (op : String) (a b : RV) (k : RV → Out) : Out :=
  match binOpSem op a b with
  | .val w => k w
  | o => o

def bangK (w : RV) (k : RV → Out) : Out :=
  match w with
  | .bool b => k (.bool (!b))
  | .int n => k (.int (M64 - 1 - n))
  | _ => .stuck "!"

/-- `?` on a `Result`: continue with the `Ok` payload, or return the `Err` early. -/
def qK (w : RV) (k : RV → Out) : Out :=
  match w with
  | .ctor "" "Ok" [x] => k x
  | .ctor "" "Err" [x] => .ret (.ctor "" "Err" [x])
  | _ => .stuck "?"

def okOrElseK (rv : RV) (onNone : (RV → Out) → Out) (k : RV → Out) : Out :=
  match rv with
  | .ctor "" "Some" [x] => k (.ctor "" "Ok" [x])
  | .ctor "" "None" [] => onNone (fun e => k (.ctor "" "Err" [e]))
  | _ => .stuck "ok_or_else"

/-! The evaluator is written in continuation-passing style: `evalE call env e k` evaluates `e`
and passes its value to `k`; a stuck state or an early `return` aborts by not invoking `k`. -/
mutual
def evalE (call : Caller) (env : REnv) : RExpr → (RV → Out) → Out
  | .var x, k => match env.get x with
    | some w => k w
    | none => .stuck "unbound"
  | .path p, k => if p == ["u64", "MAX"] then k (.int (M64 - 1)) else
      k (.ctor (pathParts p).1 (pathParts p).2 [])
  | .lit n _, k => k (.int n)
  | .str s, k => k (.str s)
  | .call f args, k => evalEs call env args (fun ws => callK call f ws k)
  | .mcall r m args, k => evalE call env r (fun rv => evalEs call env args (fun ws => methodK call m rv ws k))
  | .mcallCl r m body, k => evalE call env r (fun rv =>
      if m == "ok_or_else" then okOrElseK rv (fun k' => evalE call env body k') k
      else .stuck "closure argument")
  | .deref e, k => evalE call env e k
  | .paren e, k => evalE call env e k
  | .bang e, k => evalE call env e (fun w => bangK w k)
  | .bin op l r, k => evalE call env l (fun a => evalE call env r (fun b => binK op a b k))
  | .question e, k => evalE call env e (fun w => qK w k)
  | .structE p flds _, k => evalFields call env flds (fun kvs => k (.strct (pathParts p).1 (pathParts p).2 kvs))
  | .ite c t e, k => evalE call env c (fun w => match w with
    | .bool true => evalE call env t k
    | .bool false => evalE call env e k
    | _ => .stuck "if")
  | .mtch s as, k => evalE call env s (fun sv => evalArms call env sv as k)
  | .block ls tl, k => evalLets call env ls (fun env' => evalE call env' tl k)
  | .tuple xs, k => evalEs call env xs (fun ws => k (.tuple ws))
def evalEs (call : Caller) (env : REnv) : RExprs → (List RV → Out) → Out
  | .nil, k => k []
  | .cons e rest, k => evalE call env e (fun w => evalEs call env rest (fun ws => k (w :: ws)))
def evalFields (call : Caller) (env : REnv) : RFields → (List (String × RV) → Out) → Out
  | .nil, k => k []
  | .cons n e rest, k => evalE call env e (fun w => evalFields call env rest (fun ws => k ((n, w) :: ws)))
def evalArms (call : Caller) (env : REnv) (sv : RV) : RArms → (RV → Out) → Out
  | .nil, _ => .stuck "no arm"
  | .cons p g b _ rest, k => match matchPat p sv with
    | none => evalArms call env sv rest k
    | some bs => match g with
      | .none => evalE call (bs ++ env) b k
      | .some ge => evalE call (bs ++ env) ge (fun w => match w with
        | .bool true => evalE call (bs ++ env) b k
        | .bool false => evalArms call env sv rest k
        | _ => .stuck "guard")
def evalLets (call : Caller) : REnv → RLets → (REnv → Out) → Out
  | env, .nil, k => k env
  | env, .cons p e rest, k => evalE call env e (fun w => match matchPat p w with
    | some bs => evalLets call (bs ++ env) rest k
    | none => .stuck "let")
end

def bindParams : List (String × List String) → List RV → Option REnv
  | [], [] => some []
  | (x, _) :: ps, w :: ws => (bindParams ps ws).map (fun env => (x, w) :: env)
  | _, _ => none

def findFn (fns : List RFn) (f : List String) : Option RFn := fns.find? (·.path == f)

/-- A function call's outcome: an early `return` becomes the call's value. -/
def fixRet : Out → Out
  | .ret w => .val w
  | o => o

/-- Run user functions with call-depth fuel. -/
def runFn (fns : List RFn) : Nat → Caller
  | 0 => fun f _ => (findFn fns f).map (fun _ => .stuck "fuel")
  | n + 1 => fun f args => (findFn fns f).map fun fn =>
    match bindParams fn.params args with
    | none => .stuck "arity"
    | some env => fixRet (evalE (runFn fns n) env fn.body .val)

/-- The extracted CertIR interpreter functions (source-bound in `RustSyntax`). -/
def certirFns : List RFn :=
  [widthBitsFn, widthMaskFn, valueBitvecFn, evalBinopFn, evalCmpBvFn, evalExprFn]

end PCSForgeRefinement.Rust
