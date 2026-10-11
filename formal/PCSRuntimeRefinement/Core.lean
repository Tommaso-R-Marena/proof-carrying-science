import Std

/-!
# Executable operational semantics for the pure Python / ECMAScript subset

One shared abstract syntax (`E`, `S`) with a `Dialect` parameter.  Every construct whose
meaning differs between the two languages is interpreted by the dialect:

* **values** — `none` is Python `None` / JS `null`; `undef` is JS `undefined`; `bool` and
  `int` are kept distinct (Python `bool` is *not* silently identified with `int`: `True + 1`
  is computed by explicit coercion, `type`-level distinctions are preserved); JS numbers are
  modelled as integers **inside the safe range** `|x| ≤ 2^53 - 1`: any operation whose exact
  result leaves that range raises the explicit `inexact` outcome, so a run that does not raise
  `inexact` had every *intermediate* number exactly representable;
* **truthiness**, **equality** (Python `==` with numeric `bool`/`int` comparison; JS `===`
  strict), **indexing** (Python negative indices and `IndexError`/`KeyError`; JS out-of-range
  reads give `undefined`, property reads on `null`/`undefined` raise `TypeError`),
  **bitwise operators** (Python arbitrary-precision two's complement; JS `ToInt32`),
  **destructuring** (Python exact arity or `ValueError`; JS missing elements are `undefined`),
  **block scoping** (JS `const` bindings of a loop/if body are dropped at block exit);
* **evaluation order** is left-to-right everywhere (operands, list elements, augmented
  assignment `x[i] op= e`: container, index, read, right operand, store);
* **resources** — every evaluation step consumes fuel; running out is the explicit `fuel`
  outcome, never a value.

Values are immutable trees (no heap): see `PCSRuntimeRefinement.Python` for the syntactic
no-aliased-mutation side condition under which this coincides with reference semantics.
-/

namespace PCSRuntimeRefinement

inductive Dialect where
  | py | js
  deriving DecidableEq, Repr

inductive Val where
  | none
  | undef
  | bool (b : Bool)
  | int (i : Int)
  | str (s : String)
  | list (xs : List Val)
  | tuple (xs : List Val)
  | obj (kvs : List (String × Val))
  deriving Repr, Inhabited

inductive Exc where
  | typeError | indexError | keyError | valueError | nameError | inexact | unsupported
  deriving DecidableEq, Repr

/-- Result of an evaluation: a value, an exception, or resource exhaustion. -/
inductive Res (α : Type) where
  | ok (a : α)
  | exc (e : Exc)
  | fuel
  deriving Repr

def Res.bind {α β : Type} (x : Res α) (f : α → Res β) : Res β :=
  match x with
  | .ok a => f a
  | .exc e => .exc e
  | .fuel => .fuel

instance : Monad Res where
  pure := .ok
  bind := Res.bind

@[simp] theorem Res.bind_ok {α β : Type} (a : α) (f : α → Res β) : (Res.ok a).bind f = f a := rfl
@[simp] theorem Res.bind_exc {α β : Type} (e : Exc) (f : α → Res β) : (Res.exc e).bind f = .exc e := rfl
@[simp] theorem Res.bind_fuel {α β : Type} (f : α → Res β) : (Res.fuel).bind f = .fuel := rfl

inductive Op where
  | add | bor | band | shl | pow | eq | ne | lt
  deriving DecidableEq, Repr

/-- Binding patterns: a name, or an array/tuple pattern (`""` is a JS hole). -/
inductive Pat where
  | v (x : String)
  | tup (xs : List String)
  /-- JS callback parameter pattern that also keeps the whole element under the reserved
  (non-identifier) name `w` — used to lower `xs.filter(([,c]) => …)`, which returns elements. -/
  | whole (w : String) (xs : List String)
  deriving DecidableEq, Repr

inductive E where
  | var (x : String)
  | lit (v : Val)
  | list (es : List E)
  | tuple (es : List E)
  | index (a i : E)
  | field (a : E) (k : String)
  | sliceFrom (a i : E)
  | bin (op : Op) (a b : E)
  | not (a : E)
  | and (a b : E)
  | cond (c t f : E)
  | isNone (a : E)
  | mem (x xs : E)
  | copy (a : E)
  | min (a : E)
  | comp (elt : E) (p : Pat) (it : E) (filt : Option E)
  /-- Object literal `{k₁: e₁, …}` (JS shorthand `{cells, choices}`), keys in source order. -/
  | objLit (ks : List String) (es : List E)
  deriving Repr, Inhabited

inductive S where
  | assign (p : Pat) (e : E)
  | augIndex (x : String) (i : E) (op : Op) (e : E)
  | append (x : String) (e : E)
  | forIn (p : Pat) (it : E) (body : List S)
  | ifThen (c : E) (body : List S)
  | cont
  | ret (e : E)
  deriving Repr, Inhabited

abbrev Env := List (String × Val)

def Env.get : Env → String → Option Val
  | [], _ => none
  | (k, v) :: rest, x => if k = x then some v else Env.get rest x

def Env.has : Env → String → Bool
  | [], _ => false
  | (k, _) :: rest, x => k == x || Env.has rest x

/-- Replace every binding of `x`. -/
def Env.replace : Env → String → Val → Env
  | [], _, _ => []
  | (k, w) :: rest, x, v => (if k = x then (k, v) else (k, w)) :: Env.replace rest x v

/-- Update in place if bound, otherwise bind at the front. -/
def Env.set (env : Env) (x : String) (v : Val) : Env :=
  if env.has x then env.replace x v else (x, v) :: env

/-- JS block exit: keep only the bindings that existed before the block (with their updated
values). -/
def Env.restrict (outer env : Env) : Env := env.filter (fun p => outer.any (·.1 == p.1))

/-! ## Primitive operations -/

def MAX_SAFE : Int := 9007199254740991

def jsNum (i : Int) : Res Val := if -MAX_SAFE ≤ i ∧ i ≤ MAX_SAFE then .ok (.int i) else .exc .inexact

/-- Python two's-complement `|` on arbitrary-precision integers. -/
def intOr (a b : Int) : Int :=
  match a, b with
  | .ofNat x, .ofNat y => .ofNat (x ||| y)
  | .negSucc x, .negSucc y => .negSucc (x &&& y)
  | .ofNat x, .negSucc y => .negSucc (y - (y &&& x))
  | .negSucc x, .ofNat y => .negSucc (x - (x &&& y))

/-- Python two's-complement `&` on arbitrary-precision integers. -/
def intAnd (a b : Int) : Int :=
  match a, b with
  | .ofNat x, .ofNat y => .ofNat (x &&& y)
  | .negSucc x, .negSucc y => .negSucc (x ||| y)
  | .ofNat x, .negSucc y => .ofNat (x - (x &&& y))
  | .negSucc x, .ofNat y => .ofNat (y - (y &&& x))

/-- ECMAScript `ToInt32` on an integer. -/
def toInt32 (i : Int) : Int := (i + 2 ^ 31) % 2 ^ 32 - 2 ^ 31

/-- Numeric view: Python `bool` participates in arithmetic as `0`/`1` (explicit coercion). -/
def pyNum : Val → Option Int
  | .int i => some i
  | .bool b => some (if b then 1 else 0)
  | _ => none

/-- JS `ToNumber` restricted to the supported values. -/
def jsNumOf : Val → Option Int
  | .int i => some i
  | .bool b => some (if b then 1 else 0)
  | .none => some 0
  | _ => none

def truthy : Dialect → Val → Bool
  | .py, .none => false
  | .py, .undef => false
  | .py, .bool b => b
  | .py, .int i => i != 0
  | .py, .str s => !s.isEmpty
  | .py, .list xs => !xs.isEmpty
  | .py, .tuple xs => !xs.isEmpty
  | .py, .obj kvs => !kvs.isEmpty
  | .js, .none => false
  | .js, .undef => false
  | .js, .bool b => b
  | .js, .int i => i != 0
  | .js, .str s => !s.isEmpty
  | .js, .list _ => true
  | .js, .tuple _ => true
  | .js, .obj _ => true

mutual
/-- Python `==` (numeric across `bool`/`int`, structural on lists/dicts). -/
def pyEq : Val → Val → Bool
  | .none, .none => true
  | .str a, .str b => a == b
  | .list xs, .list ys => pyEqL xs ys
  | .tuple xs, .tuple ys => pyEqL xs ys
  | a, b => match pyNum a, pyNum b with
    | some x, some y => x == y
    | _, _ => false
def pyEqL : List Val → List Val → Bool
  | [], [] => true
  | x :: xs, y :: ys => pyEq x y && pyEqL xs ys
  | _, _ => false
end

/-- JS `===` on primitives; references are not modelled (raises `unsupported`). -/
def jsStrictEq : Val → Val → Res Bool
  | .none, .none => .ok true
  | .undef, .undef => .ok true
  | .bool a, .bool b => .ok (a == b)
  | .int a, .int b => .ok (a == b)
  | .str a, .str b => .ok (a == b)
  | .list _, _ => .exc .unsupported
  | _, .list _ => .exc .unsupported
  | .tuple _, _ => .exc .unsupported
  | _, .tuple _ => .exc .unsupported
  | .obj _, _ => .exc .unsupported
  | _, .obj _ => .exc .unsupported
  | _, _ => .ok false

def eqOp : Dialect → Val → Val → Res Bool
  | .py, a, b => .ok (pyEq a b)
  | .js, a, b => jsStrictEq a b

def binOp : Dialect → Op → Val → Val → Res Val
  | d, .eq, a, b => (eqOp d a b).bind fun r => .ok (.bool r)
  | d, .ne, a, b => (eqOp d a b).bind fun r => .ok (.bool !r)
  | .py, .add, .list xs, .list ys => .ok (.list (xs ++ ys))
  | .py, .add, .tuple xs, .tuple ys => .ok (.tuple (xs ++ ys))
  | .py, .add, .str x, .str y => .ok (.str (x ++ y))
  | .py, .add, a, b => match pyNum a, pyNum b with
    | some x, some y => .ok (.int (x + y))
    | _, _ => .exc .typeError
  | .py, .bor, .bool x, .bool y => .ok (.bool (x || y))
  | .py, .band, .bool x, .bool y => .ok (.bool (x && y))
  | .py, .bor, a, b => match pyNum a, pyNum b with
    | some x, some y => .ok (.int (intOr x y))
    | _, _ => .exc .typeError
  | .py, .band, a, b => match pyNum a, pyNum b with
    | some x, some y => .ok (.int (intAnd x y))
    | _, _ => .exc .typeError
  | .py, .shl, a, b => match pyNum a, pyNum b with
    | some x, some y => if y < 0 then .exc .valueError else .ok (.int (x * 2 ^ y.toNat))
    | _, _ => .exc .typeError
  | .py, .pow, _, _ => .exc .unsupported
  | .py, .lt, a, b => match pyNum a, pyNum b with
    | some x, some y => .ok (.bool (decide (x < y)))
    | _, _ => .exc .typeError
  | .js, .add, .str x, .str y => .ok (.str (x ++ y))
  | .js, .add, a, b => match jsNumOf a, jsNumOf b with
    | some x, some y => jsNum (x + y)
    | _, _ => .exc .unsupported
  | .js, .bor, a, b => match jsNumOf a, jsNumOf b with
    | some x, some y => .ok (.int (toInt32 (intOr (toInt32 x) (toInt32 y))))
    | _, _ => .exc .unsupported
  | .js, .band, a, b => match jsNumOf a, jsNumOf b with
    | some x, some y => .ok (.int (toInt32 (intAnd (toInt32 x) (toInt32 y))))
    | _, _ => .exc .unsupported
  | .js, .shl, _, _ => .exc .unsupported
  | .js, .pow, a, b => match jsNumOf a, jsNumOf b with
    | some x, some y => if y < 0 then .exc .inexact else jsNum (x ^ y.toNat)
    | _, _ => .exc .unsupported
  | .js, .lt, a, b => match jsNumOf a, jsNumOf b with
    | some x, some y => .ok (.bool (decide (x < y)))
    | _, _ => .exc .unsupported

def lookupKey (kvs : List (String × Val)) (k : String) : Option Val :=
  (kvs.find? (·.1 == k)).map (·.2)

/-- Subscript read. -/
def indexOp : Dialect → Val → Val → Res Val
  | .py, .list xs, i => match pyNum i with
    | some j =>
      let k := if j < 0 then j + xs.length else j
      if 0 ≤ k ∧ k < xs.length then .ok (xs.getD k.toNat .none) else .exc .indexError
    | none => .exc .typeError
  | .py, .tuple xs, i => match pyNum i with
    | some j =>
      let k := if j < 0 then j + xs.length else j
      if 0 ≤ k ∧ k < xs.length then .ok (xs.getD k.toNat .none) else .exc .indexError
    | none => .exc .typeError
  | .py, .obj kvs, .str k => match lookupKey kvs k with
    | some v => .ok v
    | none => .exc .keyError
  | .py, _, _ => .exc .typeError
  | .js, .none, _ => .exc .typeError
  | .js, .undef, _ => .exc .typeError
  | .js, .list xs, .int j => .ok (if 0 ≤ j ∧ j < xs.length then xs.getD j.toNat .undef else .undef)
  | .js, .obj kvs, .str k => .ok ((lookupKey kvs k).getD .undef)
  | .js, _, _ => .ok .undef

/-- Property read `a.k` (JS) / attribute read (Python `dict` items are not attributes). -/
def fieldOp : Dialect → Val → String → Res Val
  | .js, .none, _ => .exc .typeError
  | .js, .undef, _ => .exc .typeError
  | .js, .list xs, "length" => .ok (.int xs.length)
  | .js, .obj kvs, k => .ok ((lookupKey kvs k).getD .undef)
  | .js, _, _ => .ok .undef
  | .py, _, _ => .exc .typeError

/-- Subscript store `a[i] = v`. -/
def storeOp : Dialect → Val → Val → Val → Res Val
  | .py, .list xs, i, v => match pyNum i with
    | some j =>
      let k := if j < 0 then j + xs.length else j
      if 0 ≤ k ∧ k < xs.length then .ok (.list (xs.set k.toNat v)) else .exc .indexError
    | none => .exc .typeError
  | .js, .list xs, .int j, v =>
      if 0 ≤ j ∧ j < xs.length then .ok (.list (xs.set j.toNat v)) else .exc .unsupported
  | _, _, _, _ => .exc .typeError

/-- Iteration source. -/
def iterOf : Dialect → Val → Res (List Val)
  | _, .list xs => .ok xs
  | .py, .tuple xs => .ok xs
  | _, _ => .exc .typeError

/-- Pattern binding (Python: exact arity; JS: missing elements read `undefined`). -/
def bindPat : Dialect → Pat → Val → Env → Res Env
  | _, .v x, v, env => .ok (env.set x v)
  | .py, .tup xs, .list vs, env =>
      if xs.length = vs.length then .ok ((xs.zip vs).foldl (fun e p => e.set p.1 p.2) env)
      else .exc .valueError
  | .py, .tup xs, .tuple vs, env =>
      if xs.length = vs.length then .ok ((xs.zip vs).foldl (fun e p => e.set p.1 p.2) env)
      else .exc .valueError
  | .js, .tup xs, .list vs, env =>
      .ok ((xs.zipIdx).foldl (fun e p => if p.1 = "" then e else e.set p.1 (vs.getD p.2 .undef)) env)
  | _, .tup _, _, _ => .exc .typeError
  | .js, .whole w xs, .list vs, env =>
      .ok (((xs.zipIdx).foldl (fun e p => if p.1 = "" then e else e.set p.1 (vs.getD p.2 .undef)) env).set w (.list vs))
  | _, .whole _ _, _, _ => .exc .typeError

def memOp : Dialect → Val → Val → Res Bool
  | .py, x, .list xs => .ok (xs.any (pyEq x))
  | .py, x, .tuple xs => .ok (xs.any (pyEq x))
  | .js, x, .list xs => .ok (xs.any fun y => match jsStrictEq x y with | .ok b => b | _ => false)
  | _, _, _ => .exc .typeError

/-- `min` (Python: first minimal element, `ValueError` on empty; JS `Math.min(...)`: empty gives
`Infinity`, which is outside the supported exact numbers). -/
def minOp : Dialect → List Val → Res Val
  | .py, [] => .exc .valueError
  | .js, [] => .exc .inexact
  | d, x :: xs => xs.foldlM (fun m y => (binOp d .lt y m).bind fun c => match c with
      | .bool true => .ok y
      | .bool false => .ok m
      | _ => .exc .typeError) x

def sliceOp : Val → Val → Res Val
  | .list xs, .int i => if 0 ≤ i then .ok (.list (xs.drop i.toNat)) else .exc .unsupported
  | .tuple xs, .int i => if 0 ≤ i then .ok (.tuple (xs.drop i.toNat)) else .exc .unsupported
  | _, _ => .exc .typeError

/-- Python `x is None` / JS `x === null`. -/
def isNoneV : Val → Bool
  | .none => true
  | _ => false

/-! ## The interpreter -/

mutual
def evalE (d : Dialect) : Nat → Env → E → Res Val
  | 0, _, _ => .fuel
  | n + 1, env, e => match e with
    | .var x => match env.get x with
      | some v => .ok v
      | none => .exc .nameError
    | .lit v => .ok v
    | .list es => (evalL d n env es).bind fun vs => .ok (.list vs)
    | .tuple es => (evalL d n env es).bind fun vs => .ok (.tuple vs)
    | .index a i => (evalE d n env a).bind fun va => (evalE d n env i).bind fun vi => indexOp d va vi
    | .field a k => (evalE d n env a).bind fun va => fieldOp d va k
    | .sliceFrom a i => (evalE d n env a).bind fun va => (evalE d n env i).bind fun vi => sliceOp va vi
    | .bin op a b => (evalE d n env a).bind fun va => (evalE d n env b).bind fun vb => binOp d op va vb
    | .not a => (evalE d n env a).bind fun va => .ok (.bool !(truthy d va))
    | .and a b => (evalE d n env a).bind fun va => if truthy d va then evalE d n env b else .ok va
    | .cond c t f => (evalE d n env c).bind fun vc => if truthy d vc then evalE d n env t else evalE d n env f
    | .isNone a => (evalE d n env a).bind fun va => .ok (.bool (isNoneV va))
    | .mem x xs => (evalE d n env x).bind fun vx => (evalE d n env xs).bind fun vs =>
        (memOp d vx vs).bind fun b => .ok (.bool b)
    | .copy a => (evalE d n env a).bind fun va => (iterOf d va).bind fun xs => .ok (.list xs)
    | .min a => (evalE d n env a).bind fun va => (iterOf d va).bind fun xs => minOp d xs
    | .comp elt p it filt => (evalE d n env it).bind fun vi => (iterOf d vi).bind fun xs =>
        (evalComp d n env elt p filt xs).bind fun vs => .ok (.list vs)
    | .objLit ks es => (evalL d n env es).bind fun vs => .ok (.obj (ks.zip vs))
def evalL (d : Dialect) : Nat → Env → List E → Res (List Val)
  | 0, _, _ => .fuel
  | _ + 1, _, [] => .ok []
  | n + 1, env, e :: es => (evalE d n env e).bind fun v => (evalL d n env es).bind fun vs => .ok (v :: vs)
def evalComp (d : Dialect) : Nat → Env → E → Pat → Option E → List Val → Res (List Val)
  | 0, _, _, _, _, _ => .fuel
  | _ + 1, _, _, _, _, [] => .ok []
  | n + 1, env, elt, p, none, x :: xs => (bindPat d p x env).bind fun env' =>
      (evalE d n env' elt).bind fun v =>
      (evalComp d n env elt p none xs).bind fun rest => .ok (v :: rest)
  | n + 1, env, elt, p, some c, x :: xs => (bindPat d p x env).bind fun env' =>
      (evalE d n env' c).bind fun vc =>
      if truthy d vc then (evalE d n env' elt).bind fun v =>
        (evalComp d n env elt p (some c) xs).bind fun rest => .ok (v :: rest)
      else evalComp d n env elt p (some c) xs
end

/-- Control flow of statements. -/
inductive Flow where
  | normal (env : Env)
  | cont (env : Env)
  | ret (v : Val)
  deriving Repr

/-- Block exit (JS drops block-scoped bindings; Python has function scope). -/
def exitBlock : Dialect → Env → Env → Env
  | .py, _, env => env
  | .js, outer, env => outer.restrict env |>.reverse.reverse

mutual
def execS (d : Dialect) : Nat → Env → S → Res Flow
  | 0, _, _ => .fuel
  | n + 1, env, s => match s with
    | .assign p e => (evalE d n env e).bind fun v => (bindPat d p v env).bind fun env' => .ok (.normal env')
    | .augIndex x i op e => match env.get x with
      | none => .exc .nameError
      | some vx => (evalE d n env i).bind fun vi => (indexOp d vx vi).bind fun old =>
          (evalE d n env e).bind fun ve => (binOp d op old ve).bind fun nv =>
          (storeOp d vx vi nv).bind fun vx' => .ok (.normal (env.set x vx'))
    | .append x e => match env.get x with
      | some (.list xs) => (evalE d n env e).bind fun v => .ok (.normal (env.set x (.list (xs ++ [v]))))
      | some _ => .exc .typeError
      | none => .exc .nameError
    | .forIn p it body => (evalE d n env it).bind fun vi => (iterOf d vi).bind fun xs =>
        execFor d n env p body xs
    | .ifThen c body => (evalE d n env c).bind fun vc =>
        if truthy d vc then (execB d n env body).bind fun fl => match fl with
          | .normal env' => .ok (.normal (exitBlock d env env'))
          | .cont env' => .ok (.cont (exitBlock d env env'))
          | .ret v => .ok (.ret v)
        else .ok (.normal env)
    | .cont => .ok (.cont env)
    | .ret e => (evalE d n env e).bind fun v => .ok (.ret v)
def execB (d : Dialect) : Nat → Env → List S → Res Flow
  | 0, _, _ => .fuel
  | _ + 1, env, [] => .ok (.normal env)
  | n + 1, env, s :: ss => (execS d n env s).bind fun fl => match fl with
    | .normal env' => execB d n env' ss
    | .cont env' => .ok (.cont env')
    | .ret v => .ok (.ret v)
def execFor (d : Dialect) : Nat → Env → Pat → List S → List Val → Res Flow
  | 0, _, _, _, _ => .fuel
  | _ + 1, env, _, _, [] => .ok (.normal env)
  | n + 1, env, p, body, x :: xs => (bindPat d p x env).bind fun env1 =>
      (execB d n env1 body).bind fun fl => match fl with
        | .normal env' => execFor d n (exitBlock d env env') p body xs
        | .cont env' => execFor d n (exitBlock d env env') p body xs
        | .ret v => .ok (.ret v)
end

/-- A function: parameter names and body. -/
structure Fn where
  params : List String
  body : List S
  deriving Repr

/-- Call a function on arguments (missing return gives `None`/`undefined`). -/
def callFn (d : Dialect) (fuel : Nat) (f : Fn) (args : List Val) : Res Val :=
  if f.params.length ≠ args.length then .exc .typeError else
  (execB d fuel ((f.params.zip args).reverse) f.body).bind fun fl => match fl with
    | .ret v => .ok v
    | .normal _ => .ok (if d = .py then .none else .undef)
    | .cont _ => .exc .unsupported

end PCSRuntimeRefinement
