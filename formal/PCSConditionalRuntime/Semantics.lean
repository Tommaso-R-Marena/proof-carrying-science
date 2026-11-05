import Std

/-!
# A heap-based executable semantics for the conditional-checker fragment

This is the shared operational semantics used to extract the *current* conditional checkers
(`pcs/experimental/conditional.py` and website `public/conditional-core.mjs`).  In contrast with
the earlier value-tree semantics (`PCSRuntimeRefinement.Core`) it has

* a **heap** of mutable objects — lists/arrays, dictionaries/`Map`s (insertion ordered, any
  hashable key, in particular tuple keys) and class instances with **mutable fields**; values
  are primitives, immutable tuples / frozen sets, or references;
* **user classes with methods** (dispatch on the class of `self`), **recursive calls**
  resolved by name through the program table, **`while` loops**, `for` loops that iterate
  live lists by index (exactly Python's list iterator), `break`, and **exceptions**
  (`raise`, `try`/`except Cls as x`, `assert`) whose propagation keeps the heap and the local
  store reached at the raise point;
* explicit **resource exhaustion**: the interpreter is a tower of levels; level `k + 1`
  evaluates syntax structurally and delegates every call and every loop back-edge to level
  `k`; level `0` returns `fuel`.  A run that returns a value or an exception at some level
  returns the same at every higher level (`PCSConditionalRuntime.Mono`), so `fuel` is never a
  semantic claim.

Anything outside the fragment (heap-content equality, unhashable keys, unknown names, …)
raises an explicit built-in exception (`Unsupported`, `TypeError`, …) rather than silently
producing a value.
-/

namespace PCSCR

inductive Dialect where
  | py | js
  deriving DecidableEq, Repr

/-! ## Values -/

inductive V where
  | none
  | undef
  | bool (b : Bool)
  | int (i : Int)
  | str (s : String)
  | tup (xs : List V)
  | fset (xs : List V)
  | ref (a : Nat)
  deriving Repr, Inhabited

mutual
def V.decEq : (a b : V) → Decidable (a = b)
  | .none, .none => isTrue rfl
  | .undef, .undef => isTrue rfl
  | .bool a, .bool b => if h : a = b then isTrue (h ▸ rfl) else isFalse (by intro e; cases e; exact h rfl)
  | .int a, .int b => if h : a = b then isTrue (h ▸ rfl) else isFalse (by intro e; cases e; exact h rfl)
  | .str a, .str b => if h : a = b then isTrue (h ▸ rfl) else isFalse (by intro e; cases e; exact h rfl)
  | .ref a, .ref b => if h : a = b then isTrue (h ▸ rfl) else isFalse (by intro e; cases e; exact h rfl)
  | .tup xs, .tup ys => match V.decEqL xs ys with
    | isTrue h => isTrue (h ▸ rfl)
    | isFalse h => isFalse (by intro e; cases e; exact h rfl)
  | .fset xs, .fset ys => match V.decEqL xs ys with
    | isTrue h => isTrue (h ▸ rfl)
    | isFalse h => isFalse (by intro e; cases e; exact h rfl)
  | .none, .undef | .none, .bool _ | .none, .int _ | .none, .str _ | .none, .tup _ | .none, .fset _
  | .none, .ref _ | .undef, .none | .undef, .bool _ | .undef, .int _ | .undef, .str _ | .undef, .tup _
  | .undef, .fset _ | .undef, .ref _ | .bool _, .none | .bool _, .undef | .bool _, .int _ | .bool _, .str _
  | .bool _, .tup _ | .bool _, .fset _ | .bool _, .ref _ | .int _, .none | .int _, .undef | .int _, .bool _
  | .int _, .str _ | .int _, .tup _ | .int _, .fset _ | .int _, .ref _ | .str _, .none | .str _, .undef
  | .str _, .bool _ | .str _, .int _ | .str _, .tup _ | .str _, .fset _ | .str _, .ref _ | .tup _, .none
  | .tup _, .undef | .tup _, .bool _ | .tup _, .int _ | .tup _, .str _ | .tup _, .fset _ | .tup _, .ref _
  | .fset _, .none | .fset _, .undef | .fset _, .bool _ | .fset _, .int _ | .fset _, .str _ | .fset _, .tup _
  | .fset _, .ref _ | .ref _, .none | .ref _, .undef | .ref _, .bool _ | .ref _, .int _ | .ref _, .str _
  | .ref _, .tup _ | .ref _, .fset _ => isFalse (by intro e; cases e)
def V.decEqL : (a b : List V) → Decidable (a = b)
  | [], [] => isTrue rfl
  | [], _ :: _ => isFalse (by intro e; cases e)
  | _ :: _, [] => isFalse (by intro e; cases e)
  | x :: xs, y :: ys => match V.decEq x y, V.decEqL xs ys with
    | isTrue h1, isTrue h2 => isTrue (h1 ▸ h2 ▸ rfl)
    | isFalse h1, _ => isFalse (by intro e; cases e; exact h1 rfl)
    | _, isFalse h2 => isFalse (by intro e; cases e; exact h2 rfl)
end

instance : DecidableEq V := V.decEq

/-! ## Syntax of the core language -/

inductive BinOp where
  | add | sub | eq | ne | lt | le | gt | ge
  deriving DecidableEq, Repr

inductive E where
  | var (x : String)
  | lit (v : V)
  | tup (es : List E)
  | listD (es : List E)
  /-- Dictionary display `{k₁: v₁, …}`: alternating keys and values, evaluated in order. -/
  | dictD (es : List E)
  /-- Set display used for membership / comparison (`{'true', 'false'}`). -/
  | setD (es : List E)
  | attr (e : E) (f : String)
  | sub (e i : E)
  | sliceFrom (e i : E)
  | bin (op : BinOp) (a b : E)
  /-- Chained comparison `a op₁ b op₂ c` (`b` evaluated once, `c` only if needed). -/
  | cmp2 (op1 op2 : BinOp) (a b c : E)
  | not (a : E)
  | and (a b : E)
  | or (a b : E)
  | cond (c t f : E)
  /-- `a is None` (`neg = false`) / `a is not None` (`neg = true`). -/
  | isNone (a : E) (neg : Bool)
  /-- `type(a) is T` / `type(a) is not T` for a built-in type name. -/
  | typeIs (a : E) (ty : String) (neg : Bool)
  /-- `x in c` / `x not in c`. -/
  | mem (x c : E) (neg : Bool)
  /-- Call of a *name*, resolved through the program table, then the built-ins. -/
  | call (f : String) (args : List E)
  /-- Method call `o.m(args)`. -/
  | mcall (o : E) (m : String) (args : List E)
  /-- Keyword method call `o.m(k₁=e₁, …)` (`dict.update`). -/
  | kwcall (o : E) (m : String) (ks : List String) (args : List E)
  /-- List comprehension `[elt for x in it if filt]` (own scope, live iteration). -/
  | comp (elt : E) (x : String) (it : E) (filt : Option E)
  deriving Repr, Inhabited

inductive Tgt where
  | name (x : String)
  | attr (e : E) (f : String)
  | sub (e i : E)
  | tup (ts : List Tgt)
  deriving Repr, Inhabited

inductive S where
  /-- `t₁ = t₂ = … = e` (right-hand side once, targets left to right). -/
  | assign (ts : List Tgt) (e : E)
  | aug (t : Tgt) (op : BinOp) (e : E)
  | expr (e : E)
  | ifte (c : E) (t f : List S)
  | forIn (t : Tgt) (it : E) (body : List S)
  | while (c : E) (body : List S)
  | ret (e : E)
  | brk
  | raise (e : E)
  /-- `try: body except cls as x: handler` (`x` is unbound after the handler). -/
  | try (body : List S) (cls : String) (x : String) (handler : List S)
  | assert (e : E)
  | pass
  deriving Repr, Inhabited

structure Fn where
  params : List String
  body : List S
  deriving Repr, Inhabited

structure ClassDef where
  name : String
  methods : List String
  isException : Bool
  deriving Repr, Inhabited

structure Prog where
  /-- Top-level functions and methods (`Cls.meth`), resolved by qualified name. -/
  funs : List (String × Fn)
  classes : List ClassDef
  /-- Functions that are source-bound but not extracted: their behaviour is an explicit
  parameter (`Ctx.ext`) of every theorem that uses them. -/
  externs : List String
  deriving Repr, Inhabited

/-! ## Heap -/

inductive Obj where
  | list (xs : List V)
  | dict (kvs : List (V × V))
  | inst (cls : String) (fs : List (String × V))
  deriving Repr, Inhabited, DecidableEq

abbrev Heap := List Obj

abbrev Env := List (String × V)

def Env.get : Env → String → Option V
  | [], _ => none
  | (k, v) :: rest, x => if k = x then some v else Env.get rest x

def Env.has : Env → String → Bool
  | [], _ => false
  | (k, _) :: rest, x => k == x || Env.has rest x

def Env.replace : Env → String → V → Env
  | [], _, _ => []
  | (k, w) :: rest, x, v => (if k = x then (k, v) else (k, w)) :: Env.replace rest x v

def Env.set (env : Env) (x : String) (v : V) : Env :=
  if env.has x then env.replace x v else (x, v) :: env

def Env.erase : Env → String → Env
  | [], _ => []
  | (k, w) :: rest, x => if k = x then Env.erase rest x else (k, w) :: Env.erase rest x

inductive Exc where
  | builtin (name : String)
  | obj (v : V)
  deriving Repr, DecidableEq

/-- Outcome of a computation: a value with the new heap, an exception with the heap reached
at the raise point, or resource exhaustion. -/
inductive Out (α : Type) where
  | ok (a : α) (h : Heap)
  | exc (e : Exc) (h : Heap)
  | fuel
  deriving Repr

def Out.bind {α β : Type} (x : Out α) (f : α → Heap → Out β) : Out β :=
  match x with
  | .ok a h => f a h
  | .exc e h => .exc e h
  | .fuel => .fuel

@[simp] theorem Out.bind_ok {α β : Type} (a : α) (h : Heap) (f : α → Heap → Out β) :
    (Out.ok a h).bind f = f a h := rfl
@[simp] theorem Out.bind_exc {α β : Type} (e : Exc) (h : Heap) (f : α → Heap → Out β) :
    (Out.exc e h : Out α).bind f = .exc e h := rfl
@[simp] theorem Out.bind_fuel {α β : Type} (f : α → Heap → Out β) : (Out.fuel : Out α).bind f = .fuel := rfl

def err {α : Type} (name : String) (h : Heap) : Out α := .exc (.builtin name) h

def alloc (h : Heap) (o : Obj) : Nat × Heap := (h.length, h ++ [o])

def hget (h : Heap) (a : Nat) : Option Obj := h[a]?

def hset (h : Heap) (a : Nat) (o : Obj) : Heap := h.set a o

/-! ## Primitive operations -/

def num : V → Option Int
  | .int i => some i
  | .bool b => some (if b then 1 else 0)
  | _ => none

/-- Python `==` on primitive set elements (`none` for anything else). -/
def eqPrim : V → V → Option Bool
  | .str a, .str b => some (a == b)
  | .none, .none => some true
  | .str _, .none | .none, .str _ => some false
  | .int a, .int b => some (a == b)
  | .str _, .int _ | .int _, .str _ | .none, .int _ | .int _, .none => some false
  | _, _ => none

def memPrim (x : V) : List V → Option Bool
  | [] => some false
  | y :: ys => (eqPrim x y).bind fun a => if a then some true else memPrim x ys

def subsetPrim : List V → List V → Option Bool
  | [], _ => some true
  | x :: xs, ys => (memPrim x ys).bind fun a => if a then subsetPrim xs ys else some false

mutual
/-- Python `==` on values (`none` = outside the fragment: heap-content comparison). -/
def eqPy : V → V → Option Bool
  | .none, .none => some true
  | .undef, .undef => some true
  | .str a, .str b => some (a == b)
  | .tup xs, .tup ys => eqPyL xs ys
  | .fset xs, .fset ys => (subsetPrim xs ys).bind fun a => (subsetPrim ys xs).map fun b => a && b
  | .ref _, .ref _ => none
  | .fset _, _ => none
  | _, .fset _ => none
  | a, b => match num a, num b with
    | some x, some y => some (x == y)
    | _, _ => some false
def eqPyL : List V → List V → Option Bool
  | [], [] => some true
  | x :: xs, y :: ys => (eqPy x y).bind fun a => (eqPyL xs ys).map fun b => a && b
  | _, _ => some false
end

def memPy (x : V) : List V → Option Bool
  | [] => some false
  | y :: ys => (eqPy x y).bind fun a => if a then some true else memPy x ys

/-- JavaScript `===` (references compare by identity). -/
def eqJs : V → V → Bool
  | .none, .none => true
  | .undef, .undef => true
  | .bool a, .bool b => a == b
  | .int a, .int b => a == b
  | .str a, .str b => a == b
  | .ref a, .ref b => a == b
  | _, _ => false

def eqD : Dialect → V → V → Option Bool
  | .py, a, b => eqPy a b
  | .js, a, b => some (eqJs a b)

/-- Hashable values (dictionary keys): no references or sets, also inside tuples. -/
def hashable : V → Bool
  | .ref _ => false
  | .fset _ => false
  | .tup xs => xs.all fun x => match x with | .ref _ => false | .fset _ => false | _ => true
  | _ => true

def keyEq (d : Dialect) (a b : V) : Bool := eqD d a b == some true

def dictFind (d : Dialect) : List (V × V) → V → Option V
  | [], _ => none
  | (k, v) :: rest, x => if keyEq d k x then some v else dictFind d rest x

def dictSet (d : Dialect) : List (V × V) → V → V → List (V × V)
  | [], k, v => [(k, v)]
  | (k', v') :: rest, k, v => if keyEq d k' k then (k', v) :: rest else (k', v') :: dictSet d rest k v

def fieldGet : List (String × V) → String → Option V
  | [], _ => none
  | (k, v) :: rest, x => if k = x then some v else fieldGet rest x

def fieldSet : List (String × V) → String → V → List (String × V)
  | [], k, v => [(k, v)]
  | (k', v') :: rest, k, v => if k' = k then (k', v) :: rest else (k', v') :: fieldSet rest k v

def truthy (d : Dialect) (h : Heap) : V → Bool
  | .none => false
  | .undef => false
  | .bool b => b
  | .int i => i != 0
  | .str s => !s.isEmpty
  | .tup xs => d == .js || !xs.isEmpty
  | .fset xs => d == .js || !xs.isEmpty
  | .ref a => d == .js || match hget h a with
    | some (.list xs) => !xs.isEmpty
    | some (.dict kvs) => !kvs.isEmpty
    | _ => true

def MAX_SAFE : Int := 9007199254740991

/-- Integer results; in JavaScript a result outside the safe-integer range raises `Inexact`. -/
def safeNum (d : Dialect) (i : Int) (h : Heap) : Out V :=
  if d = .js ∧ ¬ (-MAX_SAFE ≤ i ∧ i ≤ MAX_SAFE) then err "Inexact" h else .ok (.int i) h

def cmpOp : BinOp → Int → Int → Bool
  | .lt, x, y => decide (x < y)
  | .le, x, y => decide (x ≤ y)
  | .gt, x, y => decide (x > y)
  | .ge, x, y => decide (x ≥ y)
  | _, _, _ => false

def isBoolV : V → Bool
  | .bool _ => true
  | _ => false

def binOp (d : Dialect) (op : BinOp) (a b : V) (h : Heap) : Out V :=
  match op with
  | .eq => match eqD d a b with
    | some r => .ok (.bool r) h
    | none => err "Unsupported" h
  | .ne => match eqD d a b with
    | some r => .ok (.bool !r) h
    | none => err "Unsupported" h
  | .add => match a, b with
    | .str x, .str y => .ok (.str (x ++ y)) h
    | .tup xs, .tup ys => if d = .py then .ok (.tup (xs ++ ys)) h else err "Unsupported" h
    | _, _ => match num a, num b with
      | some x, some y => if d = .js ∧ (isBoolV a || isBoolV b) then err "Unsupported" h
          else safeNum d (x + y) h
      | _, _ => err "TypeError" h
  | .sub => match num a, num b with
    | some x, some y => if d = .js ∧ (isBoolV a || isBoolV b) then err "Unsupported" h
        else safeNum d (x - y) h
    | _, _ => err "TypeError" h
  | _ => match a, b with
    | .int x, .int y => .ok (.bool (cmpOp op x y)) h
    | _, _ => if d = .py then match num a, num b with
        | some x, some y => .ok (.bool (cmpOp op x y)) h
        | _, _ => err "TypeError" h
      else err "Unsupported" h

/-- Iteration source, element `k` (lists are read live from the heap). -/
def elemAt (h : Heap) (v : V) (k : Nat) : Except Exc (Option V) :=
  match v with
  | .tup xs => .ok xs[k]?
  | .fset xs => .ok xs[k]?
  | .ref a => match hget h a with
    | some (.list xs) => .ok xs[k]?
    | some (.dict kvs) => .ok (kvs.map (·.1))[k]?
    | _ => .error (.builtin "TypeError")
  | _ => .error (.builtin "TypeError")

/-- Snapshot of the elements of an iterable. -/
def elems (h : Heap) (v : V) : Except Exc (List V) :=
  match v with
  | .tup xs => .ok xs
  | .fset xs => .ok xs
  | .ref a => match hget h a with
    | some (.list xs) => .ok xs
    | some (.dict kvs) => .ok (kvs.map (·.1))
    | _ => .error (.builtin "TypeError")
  | _ => .error (.builtin "TypeError")

def normIdx (i : Int) (len : Nat) : Int := if i < 0 then i + len else i

/-- Subscript read. -/
def subOp (d : Dialect) (h : Heap) (c i : V) : Out V :=
  match c with
  | .tup xs => match num i with
    | some j => let k := normIdx j xs.length
        if 0 ≤ k ∧ k < xs.length then .ok (xs.getD k.toNat .none) h else err "IndexError" h
    | none => err "TypeError" h
  | .ref a => match hget h a with
    | some (.list xs) =>
      if d = .js then
        match i with
        | .int j => .ok (if 0 ≤ j ∧ j < xs.length then xs.getD j.toNat .undef else .undef) h
        | _ => err "Unsupported" h
      else match i with
        | .int j => let k := normIdx j xs.length
            if 0 ≤ k ∧ k < xs.length then .ok (xs.getD k.toNat .none) h else err "IndexError" h
        | .bool _ => err "Unsupported" h
        | _ => err "TypeError" h
    | some (.dict kvs) =>
      if d = .js then
        match i with
        | .str _ => .ok ((dictFind d kvs i).getD .undef) h
        | _ => err "Unsupported" h
      else if hashable i then match dictFind d kvs i with
        | some v => .ok v h
        | none => err "KeyError" h
      else err "TypeError" h
    | some (.inst _ fs) => if d = .js then match i with
        | .str s => .ok ((fieldGet fs s).getD .undef) h
        | _ => err "Unsupported" h
      else err "TypeError" h
    | none => err "Unsupported" h
  | .none => err "TypeError" h
  | .undef => err "TypeError" h
  | _ => if d = .js then err "Unsupported" h else err "TypeError" h

/-- Subscript store `c[i] = v`. -/
def storeOp (d : Dialect) (h : Heap) (c i v : V) : Out Unit :=
  match c with
  | .ref a => match hget h a with
    | some (.list xs) => match i with
      | .int j => let k := if d = .py then normIdx j xs.length else j
          if 0 ≤ k ∧ k < xs.length then .ok () (hset h a (.list (xs.set k.toNat v)))
          else err (if d = .py then "IndexError" else "Unsupported") h
      | _ => err "TypeError" h
    | some (.dict kvs) =>
      if (d == .py && hashable i) || (d == .js && i matches .str _) then
        .ok () (hset h a (.dict (dictSet d kvs i v)))
      else err "TypeError" h
    | some (.inst cls fs) => if d = .js then match i with
        | .str s => .ok () (hset h a (.inst cls (fieldSet fs s v)))
        | _ => err "Unsupported" h
      else err "TypeError" h
    | none => err "Unsupported" h
  | _ => err "TypeError" h

def attrOp (d : Dialect) (h : Heap) (o : V) (f : String) : Out V :=
  match o with
  | .ref a => match hget h a with
    | some (.inst _ fs) => match fieldGet fs f with
      | some v => .ok v h
      | none => if d = .js then .ok .undef h else err "AttributeError" h
    | some (.dict kvs) => if d = .js then .ok ((dictFind d kvs (.str f)).getD .undef) h else err "AttributeError" h
    | some (.list xs) => if d = .js ∧ f = "length" then .ok (.int xs.length) h else err "AttributeError" h
    | none => err "Unsupported" h
  | .none => err (if d = .js then "TypeError" else "AttributeError") h
  | .undef => err "TypeError" h
  | _ => err "AttributeError" h

def setAttrOp (h : Heap) (o : V) (f : String) (v : V) : Out Unit :=
  match o with
  | .ref a => match hget h a with
    | some (.inst cls fs) => .ok () (hset h a (.inst cls (fieldSet fs f v)))
    | some (.dict kvs) => .ok () (hset h a (.dict (dictSet .js kvs (.str f) v)))
    | _ => err "AttributeError" h
  | _ => err "AttributeError" h

def isNoneV : V → Bool
  | .none => true
  | _ => false

def typeName (h : Heap) : V → String
  | .none => "NoneType"
  | .undef => "undefined"
  | .bool _ => "bool"
  | .int _ => "int"
  | .str _ => "str"
  | .tup _ => "tuple"
  | .fset _ => "set"
  | .ref a => match hget h a with
    | some (.list _) => "list"
    | some (.dict _) => "dict"
    | some (.inst c _) => c
    | none => "?"

def memOp (d : Dialect) (h : Heap) (x c : V) : Out Bool :=
  match c with
  | .fset xs => match memPy x xs with
    | some b => .ok b h
    | none => err "Unsupported" h
  | .tup xs => match memPy x xs with
    | some b => .ok b h
    | none => err "Unsupported" h
  | .ref a => match hget h a with
    | some (.list xs) => match memPy x xs with
      | some b => .ok b h
      | none => err "Unsupported" h
    | some (.dict kvs) => if hashable x then .ok (dictFind d kvs x).isSome h else err "TypeError" h
    | _ => err "TypeError" h
  | _ => err "TypeError" h

def dedup : List V → List V
  | [] => []
  | x :: xs => if (memPy x xs) == some true then dedup xs else x :: dedup xs

/-- Set display (frozen: the fragment only tests membership / equality of sets). -/
def mkSet (xs : List V) : V := .fset (dedup xs)

/-! ## JSON trees: read-back of heap structures and allocation -/

inductive T where
  | null
  | bool (b : Bool)
  | int (i : Int)
  | str (s : String)
  | arr (xs : List T)
  | obj (kvs : List (String × T))
  deriving Repr, Inhabited

def readback : Nat → Heap → V → Option T
  | 0, _, _ => none
  | n + 1, h, v => match v with
    | .none => some .null
    | .bool b => some (.bool b)
    | .int i => some (.int i)
    | .str s => some (.str s)
    | .tup xs => (xs.mapM (readback n h)).map .arr
    | .ref a => match hget h a with
      | some (.list xs) => (xs.mapM (readback n h)).map .arr
      | some (.dict kvs) => (kvs.mapM fun (p : V × V) => match p.1 with
          | .str k => (readback n h p.2).map fun t => (k, t)
          | _ => none).map .obj
      | _ => none
    | _ => none

mutual
def allocT (h : Heap) : T → V × Heap
  | .null => (.none, h)
  | .bool b => (.bool b, h)
  | .int i => (.int i, h)
  | .str s => (.str s, h)
  | .arr xs => let p := allocL h xs
      (.ref p.2.length, p.2 ++ [.list p.1])
  | .obj kvs => let p := allocKV h kvs
      (.ref p.2.length, p.2 ++ [.dict p.1])
def allocL (h : Heap) : List T → List V × Heap
  | [] => ([], h)
  | t :: ts => let p := allocT h t
      let q := allocL p.2 ts
      (p.1 :: q.1, q.2)
def allocKV (h : Heap) : List (String × T) → List (V × V) × Heap
  | [] => ([], h)
  | (k, t) :: ts => let p := allocT h t
      let q := allocKV p.2 ts
      ((.str k, p.1) :: q.1, q.2)
end

/-! ## The interpreter -/

inductive Flow where
  | normal (env : Env)
  | brk (env : Env)
  | ret (v : V)
  | raise (e : Exc) (env : Env)
  deriving Repr

/-- The interpreter one level down: calls and loop back-edges. -/
structure Lvl where
  call : String → List V → Heap → Out V
  forLoop : Env → Heap → Tgt → V → Nat → List S → Out Flow
  whileLoop : Env → Heap → E → List S → Out Flow

/-- External (source-bound, unextracted) functions. -/
abbrev Ext := String → List V → Heap → Out V

structure Ctx where
  dialect : Dialect
  prog : Prog
  globals : Env
  ext : Ext

def lookupFn (p : Prog) (f : String) : Option Fn := (p.funs.find? (·.1 == f)).map (·.2)

def lookupClass (p : Prog) (c : String) : Option ClassDef := p.classes.find? (·.name == c)

def classHasMethod (p : Prog) (c m : String) : Bool :=
  match lookupClass p c with
  | some cd => cd.methods.contains m
  | none => false

/-- Decimal digits of a natural number (`fuel` ≥ number of digits). -/
def decDigits : Nat → Nat → List Char
  | 0, _ => []
  | fuel + 1, n => if n < 10 then [Char.ofNat (48 + n)] else decDigits fuel (n / 10) ++ [Char.ofNat (48 + n % 10)]

/-- ECMAScript `String(n)` for a (safe) integer `n`. -/
def jsIntStr (i : Int) : String :=
  if 0 ≤ i then String.ofList (decDigits (i.toNat + 1) i.toNat)
  else "-" ++ String.ofList (decDigits ((-i).toNat + 1) (-i).toNat)

/-- `Array.prototype.join(sep)` on strings and integers (anything else is outside the fragment). -/
def jsElemStr : V → Option String
  | .str s => some s
  | .int i => some (jsIntStr i)
  | _ => none

def jsJoin (sep : String) : List V → Option String
  | [] => some ""
  | [x] => jsElemStr x
  | x :: y :: rest => do
    let a ← jsElemStr x
    let b ← jsJoin sep (y :: rest)
    return a ++ sep ++ b

/-- Entries `[[k, v], …]` of `Object.fromEntries` (string keys, each entry an array of two). -/
def jsEntries (h : Heap) : List V → Option (List (V × V))
  | [] => some []
  | .ref b :: rest => match hget h b with
    | some (.list [.str k, v]) => (jsEntries h rest).map ((.str k, v) :: ·)
    | _ => none
  | _ :: _ => none

/-- ECMAScript built-ins reached through the JavaScript lowering (reserved `%` names, which are
not ECMAScript identifiers, so they cannot be shadowed by source names). -/
def builtinJs (c : Ctx) (f : String) (args : List V) (h : Heap) : Out V :=
  if c.dialect ≠ .js then err "NameError" h else
  match f, args with
  /- `[...xs]` and `Object.keys(o)`: a fresh array of the elements / own keys (insertion order). -/
  | "%spread", [v] => match elems h v with
    | .ok xs => .ok (.ref h.length) (h ++ [.list xs])
    | .error e => .exc e h
  | "%keys", [v] => match v with
    | .ref a => match hget h a with
      | some (.dict kvs) => .ok (.ref h.length) (h ++ [.list (kvs.map (·.1))])
      | _ => err "Unsupported" h
    | _ => err "Unsupported" h
  /- `Object.freeze(o)` returns `o` (the extracted code never writes to a frozen object). -/
  | "%freeze", [v] => .ok v h
  | "%Number", [.bool b] => .ok (.int (if b then 1 else 0)) h
  | "%Number", [.int i] => .ok (.int i) h
  | "%Boolean", [v] => .ok (.bool (truthy .js h v)) h
  | "%Math.min", [.int a, .int b] => .ok (.int (min a b)) h
  /- `new C(msg)` / `Error(msg)` for `Error` and its member-less subclasses `C`. -/
  | "%newError", [.str cls, msg] => .ok (.ref h.length) (h ++ [.inst cls [("message", msg)]])
  | "%structuredClone", [v] => match readback (h.length + 1) h v with
    | some t => .ok (allocT h t).1 (allocT h t).2
    | none => err "Unsupported" h
  /- Indices `0, …, n-1` of an array (the callback `(_, i) => …` of `map`). -/
  | "%indices", [v] => match elems h v with
    | .ok xs => .ok (.tup ((List.range xs.length).map fun (i : Nat) => V.int (Int.ofNat i))) h
    | .error e => .exc e h
  /- `xs.every(Boolean)` -/
  | "%every", [v] => match elems h v with
    | .ok xs => .ok (.bool (xs.all (truthy .js h))) h
    | .error e => .exc e h
  | "%fromEntries", [v] => match elems h v with
    | .ok xs => match jsEntries h xs with
      | some kvs => .ok (.ref h.length) (h ++ [.dict (kvs.foldl (fun acc p => dictSet .js acc p.1 p.2) [])])
      | none => err "Unsupported" h
    | .error e => .exc e h
  | _, _ => err "NameError" h

/-- ECMAScript built-in methods of arrays and of `Map`s with string keys. -/
def builtinMethodJs (c : Ctx) (a : Nat) (m : String) (args : List V) (h : Heap) : Out V :=
  if c.dialect ≠ .js then err "AttributeError" h else
  match hget h a, m, args with
  | some (.list xs), "push", [v] => .ok (.int (xs.length + 1)) (hset h a (.list (xs ++ [v])))
  | some (.list xs), "at", [.int j] => let k := normIdx j xs.length
      .ok (if 0 ≤ k ∧ k < xs.length then xs.getD k.toNat .undef else .undef) h
  | some (.list xs), "join", [.str sep] => match jsJoin sep xs with
    | some s => .ok (.str s) h
    | none => err "Unsupported" h
  | some (.list xs), "slice", [.int j] =>
      .ok (.ref h.length) (h ++ [.list (xs.drop (max (normIdx j xs.length) 0).toNat)])
  | some (.list xs), "indexOf", [v] => match xs.findIdx? (fun y => eqJs y v) with
    | some i => .ok (.int i) h
    | none => .ok (.int (-1)) h
  | some (.dict kvs), "has", [.str s] => .ok (.bool (dictFind .js kvs (.str s)).isSome) h
  | some (.dict kvs), "get", [.str s] => .ok ((dictFind .js kvs (.str s)).getD .undef) h
  | some (.dict kvs), "set", [.str s, v] => .ok (.ref a) (hset h a (.dict (dictSet .js kvs (.str s) v)))
  | _, _, _ => err "AttributeError" h

/-- Built-in functions (no user code runs inside them). -/
def builtin (c : Ctx) (f : String) (args : List V) (h : Heap) : Out V :=
  match f, args with
  | "len", [v] => match v with
    | .tup xs => .ok (.int xs.length) h
    | .str s => .ok (.int s.length) h
    | .ref a => match hget h a with
      | some (.list xs) => .ok (.int xs.length) h
      | some (.dict kvs) => .ok (.int kvs.length) h
      | _ => err "TypeError" h
    | _ => err "TypeError" h
  | "min", [a, b] => (binOp c.dialect .lt b a h).bind fun r h => match r with
    | .bool true => .ok b h
    | _ => .ok a h
  | "int", [v] => match v with
    | .int i => .ok (.int i) h
    | .bool b => .ok (.int (if b then 1 else 0)) h
    | _ => err "Unsupported" h
  | "list", [v] => match elems h v with
    | .ok xs => .ok (.ref h.length) (h ++ [.list xs])
    | .error e => .exc e h
  | "range", [.int k] => .ok (.tup ((List.range k.toNat).map fun (i : Nat) => V.int (Int.ofNat i))) h
  | "all", [v] => match elems h v with
    | .ok xs => .ok (.bool (xs.all (truthy c.dialect h))) h
    | .error e => .exc e h
  | "str", [v] => match v with
    | .str s => .ok (.str s) h
    | .ref a => match hget h a with
      | some (.inst _ fs) => match fieldGet fs "args" with
        | some (.tup [.str s]) => .ok (.str s) h
        | _ => err "Unsupported" h
      | _ => err "Unsupported" h
    | _ => err "Unsupported" h
  | "set", [v] => match elems h v with
    | .ok xs => .ok (mkSet xs) h
    | .error e => .exc e h
  | "deepcopy", [v] => match readback (h.length + 1) h v with
    | some t => .ok (allocT h t).1 (allocT h t).2
    | none => err "Unsupported" h
  | "dict.fromkeys", [it, v] => match elems h it with
    | .ok xs => .ok (.ref h.length) (h ++ [.dict (xs.foldl (fun kvs k => dictSet c.dialect kvs k v) [])])
    | .error e => .exc e h
  | "ValueError", [msg] => .ok (.ref h.length) (h ++ [.inst "ValueError" [("args", .tup [msg])]])
  | _, _ => builtinJs c f args h

/-- Built-in methods on lists. -/
def builtinMethod (c : Ctx) (o : V) (m : String) (args : List V) (h : Heap) : Out V :=
  match o with
  | .ref a => match hget h a, m, args with
    | some (.list xs), "append", [v] => .ok .none (hset h a (.list (xs ++ [v])))
    | some (.list xs), "index", [v] => match xs.findIdx? (fun y => keyEq c.dialect y v) with
      | some i => .ok (.int i) h
      | none => err "ValueError" h
    | _, _, _ => builtinMethodJs c a m args h
  | _ => err "AttributeError" h

def updateKw (c : Ctx) (h : Heap) (o : V) (ks : List String) (vs : List V) : Out V :=
  match o with
  | .ref a => match hget h a with
    | some (.dict kvs) =>
      .ok .none (hset h a (.dict ((ks.zip vs).foldl (fun acc p => dictSet c.dialect acc (.str p.1) p.2) kvs)))
    | _ => err "AttributeError" h
  | _ => err "AttributeError" h

def pairUp : List V → Option (List (V × V))
  | [] => some []
  | k :: v :: rest => (pairUp rest).map ((k, v) :: ·)
  | [_] => none

def bindS (env : Env) (x : Out V) (k : V → Heap → Out Flow) : Out Flow :=
  match x with
  | .ok v h => k v h
  | .exc e h => .ok (.raise e env) h
  | .fuel => .fuel

/-- Body of a comprehension: append `elt` (filtered) to the accumulator list at `a`. -/
def compBody (a : Nat) (elt : E) (filt : Option E) : List S :=
  match filt with
  | none => [.expr (.mcall (.lit (.ref a)) "append" [elt])]
  | some f => [.ifte f [.expr (.mcall (.lit (.ref a)) "append" [elt])] []]

def compResult (a : Nat) : Out Flow → Out V
  | .ok (.normal _) h2 => .ok (.ref a) h2
  | .ok (.raise e _) h2 => .exc e h2
  | .ok _ h2 => err "Unsupported" h2
  | .exc e h2 => .exc e h2
  | .fuel => .fuel

/-- Continue after a statement that completed normally. -/
def seqF (x : Out Flow) (k : Env → Heap → Out Flow) : Out Flow :=
  match x with
  | .ok (.normal env') h' => k env' h'
  | other => other

/-- Loop body outcome: continue (one level down), stop on `break`, propagate the rest. -/
def loopK (x : Out Flow) (k : Env → Heap → Out Flow) : Out Flow :=
  match x with
  | .ok (.normal env2) h2 => k env2 h2
  | .ok (.brk env2) h2 => .ok (.normal env2) h2
  | other => other

/-- Handle a raised exception. -/
def onRaise (x : Out Flow) (k : Exc → Env → Heap → Out Flow) : Out Flow :=
  match x with
  | .ok (.raise ex env') h' => k ex env' h'
  | other => other

/-- Python deletes the `except … as x` name after the handler. -/
def eraseAfter (x : String) (y : Out Flow) : Out Flow :=
  match y with
  | .ok (.normal env'') h'' => .ok (.normal (env''.erase x)) h''
  | other => other

mutual
def evalE (c : Ctx) (r : Lvl) (env : Env) (h : Heap) : E → Out V
  | .var x => match env.get x with
    | some v => .ok v h
    | none => match c.globals.get x with
      | some v => .ok v h
      | none => err "NameError" h
  | .lit v => .ok v h
  | .tup es => (evalL c r env h es).bind fun vs h => .ok (.tup vs) h
  | .listD es => (evalL c r env h es).bind fun vs h => .ok (.ref h.length) (h ++ [.list vs])
  | .dictD es => (evalL c r env h es).bind fun vs h => match pairUp vs with
    | some kvs => if kvs.all (fun p => hashable p.1) then
        .ok (.ref h.length) (h ++ [.dict (kvs.foldl (fun acc p => dictSet c.dialect acc p.1 p.2) [])])
      else err "TypeError" h
    | none => err "Unsupported" h
  | .setD es => (evalL c r env h es).bind fun vs h => .ok (mkSet vs) h
  | .attr e f => (evalE c r env h e).bind fun v h => attrOp c.dialect h v f
  | .sub e i => (evalE c r env h e).bind fun v h => (evalE c r env h i).bind fun vi h => subOp c.dialect h v vi
  | .sliceFrom e i => (evalE c r env h e).bind fun v h => (evalE c r env h i).bind fun vi h =>
      match v, vi with
      | .ref a, .int j => match hget h a with
        | some (.list xs) => .ok (.ref h.length) (h ++ [.list (xs.drop (normIdx j xs.length).toNat)])
        | _ => err "TypeError" h
      | .tup xs, .int j => .ok (.tup (xs.drop (normIdx j xs.length).toNat)) h
      | _, _ => err "TypeError" h
  | .bin op a b => (evalE c r env h a).bind fun va h => (evalE c r env h b).bind fun vb h => binOp c.dialect op va vb h
  | .cmp2 op1 op2 a b e3 => (evalE c r env h a).bind fun va h => (evalE c r env h b).bind fun vb h =>
      (binOp c.dialect op1 va vb h).bind fun r1 h => if truthy c.dialect h r1 then
        (evalE c r env h e3).bind fun vc h => binOp c.dialect op2 vb vc h else .ok r1 h
  | .not a => (evalE c r env h a).bind fun va h => .ok (.bool !(truthy c.dialect h va)) h
  | .and a b => (evalE c r env h a).bind fun va h => if truthy c.dialect h va then evalE c r env h b else .ok va h
  | .or a b => (evalE c r env h a).bind fun va h => if truthy c.dialect h va then .ok va h else evalE c r env h b
  | .cond e t f => (evalE c r env h e).bind fun vc h =>
      if truthy c.dialect h vc then evalE c r env h t else evalE c r env h f
  | .isNone a neg => (evalE c r env h a).bind fun va h => .ok (.bool (isNoneV va != neg)) h
  | .typeIs a ty neg => (evalE c r env h a).bind fun va h => .ok (.bool ((typeName h va == ty) != neg)) h
  | .mem x e neg => (evalE c r env h x).bind fun vx h => (evalE c r env h e).bind fun vs h =>
      (memOp c.dialect h vx vs).bind fun b h => .ok (.bool (b != neg)) h
  | .call f args =>
      if (lookupFn c.prog f).isSome then (evalL c r env h args).bind fun vs h => r.call f vs h
      else match lookupClass c.prog f with
      | some cd => (evalL c r env h args).bind fun vs h =>
          if cd.isException then
            .ok (.ref h.length) (h ++ [.inst cd.name [("args", .tup vs)]])
          else
            (r.call (cd.name ++ ".__init__") (.ref h.length :: vs) (h ++ [.inst cd.name []])).bind
              fun _ h' => .ok (.ref h.length) h'
      | none => if c.prog.externs.contains f then (evalL c r env h args).bind fun vs h => c.ext f vs h
        else (evalL c r env h args).bind fun vs h => builtin c f vs h
  | .mcall o m args => (evalE c r env h o).bind fun vo h => (evalL c r env h args).bind fun vs h =>
      match vo with
      | .ref a => match hget h a with
        | some (.inst cls _) => if classHasMethod c.prog cls m then r.call (cls ++ "." ++ m) (vo :: vs) h
            else builtinMethod c vo m vs h
        | _ => builtinMethod c vo m vs h
      | _ => builtinMethod c vo m vs h
  | .kwcall o m ks args => (evalE c r env h o).bind fun vo h => (evalL c r env h args).bind fun vs h =>
      if m = "update" then updateKw c h vo ks vs else err "AttributeError" h
  | .comp elt x it filt => (evalE c r env h it).bind fun vi h =>
      compResult h.length (r.forLoop env (h ++ [.list []]) (.name x) vi 0 (compBody h.length elt filt))
def evalL (c : Ctx) (r : Lvl) (env : Env) (h : Heap) : List E → Out (List V)
  | [] => .ok [] h
  | e :: es => (evalE c r env h e).bind fun v h => (evalL c r env h es).bind fun vs h => .ok (v :: vs) h
end

mutual
/-- Unpacking/assignment of a target. -/
def assignT (c : Ctx) (r : Lvl) (env : Env) (h : Heap) (v : V) : Tgt → Out Env
  | .name x => .ok (env.set x v) h
  | .attr e f => (evalE c r env h e).bind fun vo h => (setAttrOp h vo f v).bind fun _ h => .ok env h
  | .sub e i => (evalE c r env h e).bind fun vo h => (evalE c r env h i).bind fun vi h =>
      (storeOp c.dialect h vo vi v).bind fun _ h => .ok env h
  | .tup ts => match elems h v with
    | .ok xs => if xs.length = ts.length then assignTs c r env h xs ts
        else err (if c.dialect = .py then "ValueError" else "Unsupported") h
    | .error e => .exc e h
def assignTs (c : Ctx) (r : Lvl) (env : Env) (h : Heap) : List V → List Tgt → Out Env
  | v :: vs, t :: ts => (assignT c r env h v t).bind fun env h => assignTs c r env h vs ts
  | _, _ => .ok env h
end

def assignAll (c : Ctx) (r : Lvl) (env : Env) (h : Heap) (v : V) : List Tgt → Out Env
  | [] => .ok env h
  | t :: ts => (assignT c r env h v t).bind fun env h => assignAll c r env h v ts

def bindE (env : Env) (x : Out Env) (k : Env → Heap → Out Flow) : Out Flow :=
  match x with
  | .ok env' h => k env' h
  | .exc e h => .ok (.raise e env) h
  | .fuel => .fuel

def excClassIs (h : Heap) (e : Exc) (cls : String) : Bool :=
  match e with
  | .obj (.ref a) => match hget h a with
    | some (.inst c _) => c == cls
    | _ => false
  | _ => false

def excVal : Exc → V
  | .obj v => v
  | .builtin s => .str s

mutual
def execS (c : Ctx) (r : Lvl) (env : Env) (h : Heap) : S → Out Flow
  | .assign ts e => bindS env (evalE c r env h e) fun v h => bindE env (assignAll c r env h v ts) fun env h =>
      .ok (.normal env) h
  | .aug t op e => match t with
    | .name x => match env.get x with
      | none => .ok (.raise (.builtin "NameError") env) h
      | some old => bindS env (evalE c r env h e) fun ve h => bindS env (binOp c.dialect op old ve h) fun nv h =>
          .ok (.normal (env.set x nv)) h
    | .attr o f => bindS env (evalE c r env h o) fun vo h => bindS env (attrOp c.dialect h vo f) fun old h =>
        bindS env (evalE c r env h e) fun ve h => bindS env (binOp c.dialect op old ve h) fun nv h =>
        bindS env ((setAttrOp h vo f nv).bind fun _ h => .ok .none h) fun _ h => .ok (.normal env) h
    | _ => .ok (.raise (.builtin "Unsupported") env) h
  | .expr e => bindS env (evalE c r env h e) fun _ h => .ok (.normal env) h
  | .ifte e t f => bindS env (evalE c r env h e) fun vc h =>
      if truthy c.dialect h vc then execB c r env h t else execB c r env h f
  | .forIn t it body => bindS env (evalE c r env h it) fun vi h => r.forLoop env h t vi 0 body
  | .while e body => r.whileLoop env h e body
  | .ret e => bindS env (evalE c r env h e) fun v h => .ok (.ret v) h
  | .brk => .ok (.brk env) h
  | .raise e => bindS env (evalE c r env h e) fun v h => .ok (.raise (.obj v) env) h
  | .try body cls x handler => onRaise (execB c r env h body) fun ex env' h' =>
      if excClassIs h' ex cls then eraseAfter x (execB c r (env'.set x (excVal ex)) h' handler)
      else .ok (.raise ex env') h'
  | .assert e => bindS env (evalE c r env h e) fun v h =>
      if truthy c.dialect h v then .ok (.normal env) h else .ok (.raise (.builtin "AssertionError") env) h
  | .pass => .ok (.normal env) h
def execB (c : Ctx) (r : Lvl) (env : Env) (h : Heap) : List S → Out Flow
  | [] => .ok (.normal env) h
  | s :: ss => seqF (execS c r env h s) fun env' h' => execB c r env' h' ss
end

/-- One loop iteration of `for t in v` at index `k`; the next iteration runs one level down. -/
def forIter (c : Ctx) (r : Lvl) (env : Env) (h : Heap) (t : Tgt) (v : V) (k : Nat) (body : List S) : Out Flow :=
  match elemAt h v k with
  | .error e => .ok (.raise e env) h
  | .ok none => .ok (.normal env) h
  | .ok (some x) => bindE env (assignT c r env h x t) fun env1 h1 =>
      loopK (execB c r env1 h1 body) fun env2 h2 => r.forLoop env2 h2 t v (k + 1) body

/-- One iteration of `while e: body`; the next test runs one level down. -/
def whileIter (c : Ctx) (r : Lvl) (env : Env) (h : Heap) (e : E) (body : List S) : Out Flow :=
  bindS env (evalE c r env h e) fun vc h =>
    if truthy c.dialect h vc then
      loopK (execB c r env h body) fun env2 h2 => r.whileLoop env2 h2 e body
    else .ok (.normal env) h

def finishCall (d : Dialect) : Out Flow → Out V
  | .ok (.ret v) h' => .ok v h'
  | .ok (.normal _) h' => .ok (if d = .py then .none else .undef) h'
  | .ok (.brk _) h' => err "SyntaxError" h'
  | .ok (.raise e _) h' => .exc e h'
  | .exc e h' => .exc e h'
  | .fuel => .fuel

/-- Call of a resolved user function / method by its qualified name. -/
def callBody (c : Ctx) (r : Lvl) (f : String) (args : List V) (h : Heap) : Out V :=
  match lookupFn c.prog f with
  | none => err "NameError" h
  | some fn => if fn.params.length ≠ args.length then err "TypeError" h else
    finishCall c.dialect (execB c r (fn.params.zip args).reverse h fn.body)

def mkLevel (c : Ctx) (r : Lvl) : Lvl where
  call := callBody c r
  forLoop := fun env h t v k body => forIter c r env h t v k body
  whileLoop := fun env h e body => whileIter c r env h e body

def fuelLvl : Lvl := ⟨fun _ _ _ => .fuel, fun _ _ _ _ _ _ => .fuel, fun _ _ _ _ => .fuel⟩

/-- The interpreter with `k` levels of calls / loop iterations available. -/
def interp (c : Ctx) : Nat → Lvl
  | 0 => fuelLvl
  | k + 1 => mkLevel c (interp c k)

/-- Run a named function with fuel `k`. -/
def run (c : Ctx) (k : Nat) (f : String) (args : List V) (h : Heap) : Out V := (interp c k).call f args h

end PCSCR
