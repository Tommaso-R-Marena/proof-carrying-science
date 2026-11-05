import PCSConditionalRuntime.JsFront

/-!
# ECMAScript lowering into the shared heap semantics (scope resolution included)

`lowerJSegs` turns the source-bound concrete syntax of an ECMAScript module into a `Module`
of the shared semantics (dialect `js`).  The lowering is *partial*: anything outside the
supported fragment, or any use whose meaning would differ from ECMAScript, makes it fail
(`none`).

**Scopes.**  ECMAScript `const`/`let`/`for (const x of …)`/`catch (x)`/parameters are block
scoped, while the core language has one store per call.  The lowering resolves every name
statically: each declaration gets a core name that is unique in its function (`x`, or `x#k` for
the `k`-th declaration of `x`; module-level names are never reused), so a block-scoped binding can
never be confused with another one after its block ends.  A name in its temporal dead zone
(the initialiser of its own declaration, the callback of `const x = a.map(…)`) is *poisoned*:
referring to it makes the lowering fail.  Free names must be declared module constants,
functions, classes or imports.

**Supported built-ins** (each recognised only when the global name is not shadowed):
`Object.freeze/fromEntries/keys/assign`, `Math.min`, `Number`, `Boolean`, `Error`,
`structuredClone`, `new Map()`, array literals with one spread `[...xs]`, `xs.map(p=>e)`,
`xs.map((_,i)=>e)` (the element parameter `_` is poisoned), `xs.filter(p=>e)`,
`xs.every(Boolean)`, and the methods `push/at/join/slice/indexOf` (arrays) and `has/get/set`
(`Map`, string keys) of the semantics.  `await e` is lowered to `e` (the only awaited callee,
`digest`, is an extern whose contract is stated for its resolved value).

**Statements.**  `switch` with string cases each ending in `return`/`throw` (no fall-through)
becomes a chain of `===` tests on a fresh temporary; `try{…}catch(e){if(!(e instanceof C))throw e;…}`
for a member-less `Error` subclass `C` becomes the core `try … except C as e`;
`const x = a.map(p=>{…; return e;})` (no other `return`/`break` in the callback) becomes
`x = []; for p of a { …; x.push(e) }`; an assignment whose target has non-atomic operands
requires a call-free right-hand side (so ECMAScript's left-to-right reference evaluation and the
core's right-hand-side-first order agree).
-/

namespace PCSCR.Js

open PCSCR PCSCR.Py

/-- Module-level names. -/
structure LCx where
  funs : List String
  classes : List String
  /-- Member-less subclasses of `Error`. -/
  errClasses : List String
  externs : List String
  methods : List String
  globals : List String

def LCx.all (cx : LCx) : List String :=
  cx.funs ++ cx.classes ++ cx.errClasses ++ cx.externs ++ cx.globals

structure LSt where
  /-- Source names declared so far in the current function (with multiplicity). -/
  decls : List String
  /-- Innermost-first scope: source name ↦ core name (`none` = temporal dead zone). -/
  scope : List (String × Option String)
  noRet : Bool
  noBrk : Bool

abbrev LM := StateT LSt Option

def lookupScope (x : String) : List (String × Option String) → Option (Option String)
  | [] => none
  | (y, v) :: rest => if y = x then some v else lookupScope x rest

def declare (x : String) : LM String := do
  let st ← get
  let k := st.decls.count x
  let x' := if k = 0 then x else x ++ "#" ++ natStr (k + 1)
  set { st with decls := x :: st.decls, scope := (x, some x') :: st.scope }
  return x'

def poison (x : String) : LM Unit :=
  modify fun st => { st with scope := (x, none) :: st.scope }

def withScope {α : Type} (act : LM α) : LM α := do
  let st ← get
  let r ← act
  modify fun st' => { st' with scope := st.scope, noRet := st.noRet, noBrk := st.noBrk }
  return r

def setFlags (noRet noBrk : Bool) : LM Unit :=
  modify fun st => { st with noRet := noRet, noBrk := noBrk }

def resolve (cx : LCx) (x : String) : LM String := do
  match lookupScope x (← get).scope with
  | some (some x') => return x'
  | some none => failure
  | none => if cx.globals.contains x then return x else failure

/-- `name` refers to the ECMAScript global of that name (not shadowed). -/
def guardG (cx : LCx) (name : String) : LM Unit := do
  if (lookupScope name (← get).scope).isSome || cx.all.contains name then failure

/-- `f` is a callable module function / import (not shadowed). -/
def guardCallee (cx : LCx) (f : String) : LM Unit := do
  if (lookupScope f (← get).scope).isSome then failure
  if !(cx.funs.contains f || cx.externs.contains f) then failure

def JOp.core : JOp → Option BinOp
  | .add => some .add | .sub => some .sub | .seq => some .eq | .sne => some .ne
  | .lt => some .lt | .gt => some .gt | .le => some .le | .ge => some .ge
  | _ => none

mutual
def JE.callFree : JE → Bool
  | .call .. | .new .. | .await _ | .arrow1 .. | .arrowP .. | .arrowB .. => false
  | .paren e | .mem e _ | .not e | .neg e | .spread e => e.callFree
  | .idx a i | .bin _ a i => a.callFree && i.callFree
  | .cond c t f => c.callFree && t.callFree && f.callFree
  | .arr es => JE.callFreeL es
  | .obj ps => JP.callFreeL ps
  | _ => true
def JE.callFreeL : List JE → Bool
  | [] => true
  | e :: es => e.callFree && JE.callFreeL es
def JP.callFreeL : List JP → Bool
  | [] => true
  | .kv _ v :: ps => v.callFree && JP.callFreeL ps
  | .short _ :: ps => JP.callFreeL ps
end

def JE.atomic : JE → Bool
  | .name _ | .num _ | .str _ => true
  | _ => false

/-- Operands of an assignment target are atomic. -/
def JE.atomicTarget : JE → Bool
  | .name _ => true
  | .mem a _ => a.atomic
  | .idx a i => a.atomic && i.atomic
  | .arr es => es.all JE.atomic
  | _ => false

def JS.endsJumpB : List JS → Bool
  | [] => false
  | [.ret _] | [.throw _] => true
  | _ :: rest => JS.endsJumpB rest

/-- A statement list whose last statement always exits (`return` / `throw`). -/
def JS.endsJump : List JS → Bool
  | [] => false
  | [.ret _] | [.throw _] => true
  | [.block ss] => JS.endsJumpB ss
  | _ :: rest => JS.endsJump rest

mutual
def JE.lw (cx : LCx) : JE → LM E
  | .name s => return .var (← resolve cx s)
  | .num n => return .lit (.int n)
  | .str s => return .lit (.str s)
  | .tru => return .lit (.bool true)
  | .fls => return .lit (.bool false)
  | .null => return .lit .none
  | .paren e => e.lw cx
  | .arr [.spread e] => return .call "%spread" [← e.lw cx]
  | .arr es => return .listD (← JE.lwL cx es)
  | .obj ps => return .dictD (← JP.lwL cx ps)
  | .mem a k => return .attr (← a.lw cx) k
  | .idx a i => return .sub (← a.lw cx) (← i.lw cx)
  | .call (.mem (.name "Object") "freeze") [x] => do guardG cx "Object"; return .call "%freeze" [← x.lw cx]
  | .call (.mem (.name "Object") "fromEntries") [x] => do
      guardG cx "Object"; return .call "%fromEntries" [← x.lw cx]
  | .call (.mem (.name "Object") "keys") [x] => do guardG cx "Object"; return .call "%keys" [← x.lw cx]
  | .call (.mem (.name "Object") "assign") [o, .obj ps] => do
      guardG cx "Object"
      let o' ← o.lw cx
      let (ks, vs) ← JP.lwKw cx ps
      return .kwcall o' "update" ks vs
  | .call (.mem (.name "Math") "min") [a, b] => do
      guardG cx "Math"; return .call "%Math.min" [← a.lw cx, ← b.lw cx]
  | .call (.name "Number") [x] => do guardG cx "Number"; return .call "%Number" [← x.lw cx]
  | .call (.name "Boolean") [x] => do guardG cx "Boolean"; return .call "%Boolean" [← x.lw cx]
  | .call (.name "Error") [x] => do guardG cx "Error"; return .call "%newError" [.lit (.str "Error"), ← x.lw cx]
  | .call (.name "structuredClone") [x] => do
      guardG cx "structuredClone"; return .call "%structuredClone" [← x.lw cx]
  | .call (.mem o "map") [.arrow1 p body] => do
      let o' ← o.lw cx
      withScope do
        let p' ← declare p
        return .comp (← body.lw cx) p' o' none
  | .call (.mem o "map") [.arrowP ["_", q] body] => do
      if q = "_" then failure
      let o' ← o.lw cx
      withScope do
        poison "_"
        let q' ← declare q
        return .comp (← body.lw cx) q' (.call "%indices" [o']) none
  | .call (.mem o "filter") [.arrow1 p body] => do
      let o' ← o.lw cx
      withScope do
        let p' ← declare p
        return .comp (.var p') p' o' (some (← body.lw cx))
  | .call (.mem o "every") [.name "Boolean"] => do
      guardG cx "Boolean"; return .call "%every" [← o.lw cx]
  | .call (.mem o m) args => do
      if (m = "append" || m = "index") && !cx.methods.contains m then failure
      let o' ← o.lw cx
      return .mcall o' m (← JE.lwL cx args)
  | .call (.name f) args => do guardCallee cx f; return .call f (← JE.lwL cx args)
  | .call _ _ => failure
  | .new c args => do
      if (lookupScope c (← get).scope).isSome then failure
      if c = "Map" && args.isEmpty && !cx.all.contains "Map" then return .dictD []
      else if cx.errClasses.contains c then return .call "%newError" (.lit (.str c) :: (← JE.lwL cx args))
      else if cx.classes.contains c then return .call c (← JE.lwL cx args)
      else failure
  | .bin .and l r => return .and (← l.lw cx) (← r.lw cx)
  | .bin .or l r => return .or (← l.lw cx) (← r.lw cx)
  | .bin op l r => do
      let o ← liftM (m := Option) op.core
      return .bin o (← l.lw cx) (← r.lw cx)
  | .not a => return .not (← a.lw cx)
  | .neg (.num n) => return .lit (.int (-(n : Int)))
  | .neg _ => failure
  | .cond c t f => return .cond (← c.lw cx) (← t.lw cx) (← f.lw cx)
  | .await e => e.lw cx
  | .spread _ | .arrow1 .. | .arrowP .. | .arrowB .. => failure
def JE.lwL (cx : LCx) : List JE → LM (List E)
  | [] => return []
  | .spread _ :: _ => failure
  | e :: es => return (← e.lw cx) :: (← JE.lwL cx es)
def JP.lwL (cx : LCx) : List JP → LM (List E)
  | [] => return []
  | .kv k v :: ps => return .lit (.str k) :: (← v.lw cx) :: (← JP.lwL cx ps)
  | .short k :: ps => return .lit (.str k) :: .var (← resolve cx k) :: (← JP.lwL cx ps)
def JP.lwKw (cx : LCx) : List JP → LM (List String × List E)
  | [] => return ([], [])
  | .kv k v :: ps => do
      let v' ← v.lw cx
      let (ks, vs) ← JP.lwKw cx ps
      return (k :: ks, v' :: vs)
  | .short k :: ps => do
      let v' := E.var (← resolve cx k)
      let (ks, vs) ← JP.lwKw cx ps
      return (k :: ks, v' :: vs)
def JE.lwTgt (cx : LCx) : JE → LM Tgt
  | .name x => do
      match lookupScope x (← get).scope with
      | some (some x') => return .name x'
      | _ => failure
  | .mem a k => return .attr (← a.lw cx) k
  | .idx a i => return .sub (← a.lw cx) (← i.lw cx)
  | .arr es => return .tup (← JE.lwTgts cx es)
  | _ => failure
def JE.lwTgts (cx : LCx) : List JE → LM (List Tgt)
  | [] => return []
  | .name x :: es => do
      match lookupScope x (← get).scope with
      | some (some x') => return .name x' :: (← JE.lwTgts cx es)
      | _ => failure
  | _ :: _ => failure
def JD.lw (cx : LCx) : JD → LM (List S)
  | .name x none => do
      let x' ← declare x
      return [.assign [.name x'] (.lit .undef)]
  | .name x (some (.call (.mem o "map") [.arrowB p body])) => do
      let o' ← o.lw cx
      let st ← get
      let k := st.decls.count x
      let x' := if k = 0 then x else x ++ "#" ++ natStr (k + 1)
      let body' ← withScope do
        poison x
        setFlags true true
        let p' ← declare p
        let b ← JS.lwMap cx x' body
        return [.assign [.name x'] (.listD []), .forIn (.name p') o' b]
      let x'' ← declare x
      if x'' ≠ x' then failure
      return body'
  | .name x (some e) => do
      let e' ← withScope do poison x; e.lw cx
      let x' ← declare x
      return [.assign [.name x'] e']
  | .arrPat xs e => do
      let e' ← withScope do
        for x in xs do poison x
        e.lw cx
      let mut ts := []
      for x in xs do
        let x' ← declare x
        ts := ts ++ [Tgt.name x']
      return [.assign [.tup ts] e']
def JD.lwL (cx : LCx) : List JD → LM (List S)
  | [] => return []
  | d :: ds => return (← d.lw cx) ++ (← JD.lwL cx ds)
/-- Body of a block callback of `map` that pushes onto `x'`: the last statement is the only `return`. -/
def JS.lwMap (cx : LCx) (x' : String) : List JS → LM (List S)
  | [] => failure
  | [.ret (some e)] => return [.expr (.mcall (.var x') "push" [← e.lw cx])]
  | s :: rest => return (← s.lw cx) ++ (← JS.lwMap cx x' rest)
def JS.lw (cx : LCx) : JS → LM (List S)
  | .expr e => return [.expr (← e.lw cx)]
  | .decl _ ds => JD.lwL cx ds
  | .assign t e => do
      if !(t.atomicTarget || e.callFree) then failure
      let e' ← e.lw cx
      let t' ← t.lwTgt cx
      return [.assign [t'] e']
  | .incr (.name x) => do
      match lookupScope x (← get).scope with
      | some (some x') => return [.aug (.name x') .add (.lit (.int 1))]
      | _ => failure
  | .incr (.mem a k) => return [.aug (.attr (← a.lw cx) k) .add (.lit (.int 1))]
  | .incr _ => failure
  | .ret none => do
      guard !(← get).noRet
      return [.ret (.lit .undef)]
  | .ret (some e) => do
      guard !(← get).noRet
      return [.ret (← e.lw cx)]
  | .brk => do
      guard !(← get).noBrk
      return [.brk]
  | .throw e => return [.raise (← e.lw cx)]
  | .ifS c t _ els => do
      let c' ← c.lw cx
      let t' ← withScope (t.lw cx)
      let f' ← match els with
        | none => pure []
        | some s => withScope (s.lw cx)
      return [.ifte c' t' f']
  | .block ss => withScope (JS.lwL cx ss)
  | .forOf _ x it b => do
      let it' ← it.lw cx
      withScope do
        let x' ← declare x
        modify fun st => { st with noBrk := false }
        return [.forIn (.name x') it' (← b.lw cx)]
  | .while c b => do
      let c' ← c.lw cx
      withScope do
        modify fun st => { st with noBrk := false }
        return [.while c' (← b.lw cx)]
  | .tryCatch b x (.ifS (.not (.paren (.bin .inst (.name x2) (.name cls)))) (.throw (.name x3)) none none :: hd) => do
      if !(x2 = x && x3 = x && cx.errClasses.contains cls) then failure
      if (lookupScope cls (← get).scope).isSome then failure
      let b' ← withScope (JS.lwL cx b)
      let hd' ← withScope do
        let x' ← declare x
        let r ← JS.lwL cx hd
        return (x', r)
      return [.try b' cls hd'.1 hd'.2]
  | .tryCatch .. => failure
  | .switch e cs d => do
      let e' ← e.lw cx
      let sw ← declare "%sw"
      let chain ← withScope do
        modify fun st => { st with noBrk := true }
        guard (JS.endsJump d)
        let d' ← withScope (JS.lwL cx d)
        JS.lwCases cx sw cs d'
      return .assign [.name sw] e' :: chain
  | .nl _ => return []
def JS.lwL (cx : LCx) : List JS → LM (List S)
  | [] => return []
  | s :: ss => return (← s.lw cx) ++ (← JS.lwL cx ss)
def JS.lwCases (cx : LCx) (sw : String) : List (String × List JS) → List S → LM (List S)
  | [], d' => return d'
  | (l, ss) :: rest, d' => do
      guard (JS.endsJump ss)
      let ss' ← withScope (JS.lwL cx ss)
      let rest' ← JS.lwCases cx sw rest d'
      return [.ifte (.bin .eq (.var sw) (.lit (.str l))) ss' rest']
end

/-! ## Functions, classes, modules -/

def initSt (cx : LCx) : LSt := ⟨cx.all, [], false, true⟩

/-- Parameters: plain names, or `{k=d}={}` (bound to the reserved parameter `%opts`). -/
def lowerParams (cx : LCx) : List JParam → LM (List String × List S)
  | [] => return ([], [])
  | .plain x :: ps => do
      let x' ← declare x
      let (xs, pre) ← lowerParams cx ps
      return (x' :: xs, pre)
  | .objDefault k d :: ps => do
      let d' ← d.lw cx
      let k' ← declare k
      let pre := [S.ifte (.bin .eq (.var "%opts") (.lit .undef)) [.assign [.name "%opts"] (.dictD [])] [],
        .assign [.name k'] (.attr (.var "%opts") k),
        .ifte (.bin .eq (.var k') (.lit .undef)) [.assign [.name k'] d'] []]
      let (xs, pre2) ← lowerParams cx ps
      return ("%opts" :: xs, pre ++ pre2)

def lowerFunc (cx : LCx) (qual : String) (this : Bool) (params : List JParam) (body : List JS) :
    Option (String × Fn) :=
  (do
    let self ← if this then (do let t ← declare "this"; pure [t]) else pure []
    let (xs, pre) ← lowerParams cx params
    let b ← JS.lwL cx body
    return (qual, (⟨self ++ xs, pre ++ b⟩ : Fn))).run' (initSt cx)

def JMethod.qual (cls : String) (m : JMethod) : String :=
  cls ++ "." ++ (if m.name = "constructor" then "__init__" else m.name)

def lowerMethods (cx : LCx) (cls : String) : List JMethod → Option (List (String × Fn))
  | [] => some []
  | m :: ms => do
      let f ← lowerFunc cx (m.qual cls) true (m.params.map .plain) m.body
      return f :: (← lowerMethods cx cls ms)

/-- Module-level `const` declarations: assignments of the (unrenamed) module constants. -/
def lowerTopDecl (cx : LCx) : List JD → Option (List S)
  | [] => some []
  | .name x (some e) :: ds => do
      let e' ← (e.lw cx).run' (initSt cx)
      return .assign [.name x] e' :: (← lowerTopDecl cx ds)
  | _ => none

def lowerJItem (cx : LCx) : JItem → Option Module
  | .stmt _ (.decl "const" ds) => (lowerTopDecl cx ds).map fun init => ⟨[], [], [], init⟩
  | .stmt _ _ => none
  | .func _ _ name params body => (lowerFunc cx name false params body).map fun f => ⟨[f], [], [], []⟩
  | .cls _ (some "Error") [] => some .empty
  | .cls name none ms => (lowerMethods cx name ms).map fun fs =>
      ⟨fs, [⟨name, ms.map fun m => if m.name = "constructor" then "__init__" else m.name, false⟩], [], []⟩
  | .cls _ _ _ => none

def lowerJItems (cx : LCx) : List JItem → Option Module
  | [] => some .empty
  | i :: is => do return (← lowerJItem cx i).append (← lowerJItems cx is)

/-! ### Module-level names (collected from the segments) -/

def JItem.cxOf : JItem → LCx
  | .stmt _ (.decl _ ds) => ⟨[], [], [], [], [], ds.filterMap fun d => match d with | .name x _ => some x | _ => none⟩
  | .stmt _ _ => ⟨[], [], [], [], [], []⟩
  | .func _ _ n _ _ => ⟨[n], [], [], [], [], []⟩
  | .cls n (some "Error") [] => ⟨[], [], [n], [], [], []⟩
  | .cls n _ ms => ⟨[], [n], [], [], ms.map fun m => if m.name = "constructor" then "__init__" else m.name, []⟩

def LCx.app (a b : LCx) : LCx :=
  ⟨a.funs ++ b.funs, a.classes ++ b.classes, a.errClasses ++ b.errClasses, a.externs ++ b.externs,
   a.methods ++ b.methods, a.globals ++ b.globals⟩

def LCx.empty : LCx := ⟨[], [], [], [], [], []⟩

def segsCx : List JSeg → LCx
  | [] => .empty
  | .header _ :: rest => segsCx rest
  | .imports ns _ :: rest => LCx.app ⟨[], [], [], ns, [], []⟩ (segsCx rest)
  | .code items :: rest => (items.foldr (fun i acc => LCx.app i.cxOf acc) .empty).app (segsCx rest)
  | .opaque n _ :: rest => LCx.app ⟨[], [], [], [n], [], []⟩ (segsCx rest)

/-- Every module-level name is declared once. -/
def LCx.nodup (cx : LCx) : Bool := cx.all.eraseDups.length == cx.all.length

def lowerJSegsWith (cx : LCx) : List JSeg → Option Module
  | [] => some .empty
  | .header _ :: rest => lowerJSegsWith cx rest
  | .imports ns _ :: rest => (lowerJSegsWith cx rest).map fun m => Module.append ⟨[], [], ns, []⟩ m
  | .code items :: rest => do return (← lowerJItems cx items).append (← lowerJSegsWith cx rest)
  | .opaque n _ :: rest => (lowerJSegsWith cx rest).map fun m => Module.append ⟨[], [], [n], []⟩ m

/-- **The ECMAScript extractor.** -/
def lowerJSegs (segs : List JSeg) : Option Module :=
  let cx := segsCx segs
  if cx.nodup then lowerJSegsWith cx segs else none

end PCSCR.Js
