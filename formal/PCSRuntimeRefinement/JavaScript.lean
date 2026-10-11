import PCSRuntimeRefinement.Python

/-!
# ECMAScript front end: concrete syntax, exact rendering, scope check and lowering

* `JE` / `JS` / `JFun` — a concrete syntax tree for the supported ECMAScript subset (the
  compact style of the website modules: no optional spaces, `const` declarations, `for…of`
  over array patterns, `if` with statement or block bodies, `continue`, `return`, method calls
  `includes` / `push` / `map` / `filter` / `slice`, `Math.min(...)`, spread copies `[...a]`,
  arrow callbacks with array-hole patterns and shorthand object literals).  `JFun.render`
  reproduces the source text byte for byte, including the layout of statements over lines.
* `JE.wf` — operator precedence / associativity discipline (unambiguous rendering).
* `JFun.scopeOK` — every `const` / loop / callback binding is fresh: it never shadows a name
  already in scope (parameters, enclosing declarations).  Under this check the flat-environment
  semantics with JS block exit (`exitBlock .js`) coincides with lexical block scoping.
* `JFun.lower` — partial extraction into the shared executable semantics.  Unsupported
  constructs (any other call or method, `let`, assignment to names, …) are rejected.
  `x === null` lowers to the `null` test, so references are never compared.  `a.includes(x)`
  is accepted only for a plain name `x`; the shared semantics evaluates that (scope-checked,
  hence always bound and effect-free) name before `a`, which is unobservable.
* **Extraction certificate** for `bellman` of website `public/intervention-core.mjs`:
  `javascript_bellman_source_bound` (exact source lines 14–27), `javascript_bellman_wf`,
  `javascript_bellman_scope` and `javascript_bellman_lowers`.
-/

namespace PCSRuntimeRefinement.Js

open PCSRuntimeRefinement

inductive JOp where
  | add | bor | band | pow | seq | sne | and
  deriving DecidableEq, Repr

def JOp.sym : JOp → String
  | .add => "+" | .bor => "|" | .band => "&" | .pow => "**" | .seq => "===" | .sne => "!==" | .and => "&&"

/-- ECMAScript precedence levels (higher binds tighter). -/
def JOp.prec : JOp → Nat
  | .pow => 14 | .add => 12 | .seq | .sne => 8 | .band => 7 | .bor => 5 | .and => 4

inductive JE where
  | name (s : String)
  | num (n : Nat)
  | tru | fls | null
  | paren (e : JE)
  | arr (es : List JE)
  | spread (e : JE)
  | mem (a : JE) (k : String)
  | idx (a i : JE)
  | call (f : JE) (args : List JE)
  /-- `([p₀,p₁,…])=>body`, `""` is a hole. -/
  | arrow (pat : List String) (body : JE)
  | bin (op : JOp) (l r : JE)
  | not (a : JE)
  | cond (c t f : JE)
  /-- `{k₀,k₁,…}` shorthand object literal. -/
  | objShort (ks : List String)
  deriving Repr, Inhabited

def commas (xs : List String) : String := ",".intercalate xs

mutual
def JE.render : JE → String
  | .name s => s
  | .num n => Py.natStr n
  | .tru => "true"
  | .fls => "false"
  | .null => "null"
  | .paren e => "(" ++ e.render ++ ")"
  | .arr es => "[" ++ JE.renderL es ++ "]"
  | .spread e => "..." ++ e.render
  | .mem a k => a.render ++ "." ++ k
  | .idx a i => a.render ++ "[" ++ i.render ++ "]"
  | .call f args => f.render ++ "(" ++ JE.renderL args ++ ")"
  | .arrow pat body => "([" ++ commas pat ++ "])=>" ++ body.render
  | .bin op l r => l.render ++ op.sym ++ r.render
  | .not a => "!" ++ a.render
  | .cond c t f => c.render ++ "?" ++ t.render ++ ":" ++ f.render
  | .objShort ks => "{" ++ commas ks ++ "}"
def JE.renderL : List JE → String
  | [] => ""
  | [e] => e.render
  | e :: es => e.render ++ "," ++ JE.renderL es
end

/-- Grammar level (`20` = primary / member / call). -/
def JE.prec : JE → Nat
  | .spread _ => 1
  | .arrow .. => 2
  | .cond .. => 2
  | .bin op _ _ => op.prec
  | .not _ => 15
  | _ => 20

mutual
def JE.wf : JE → Bool
  | .name s => !s.isEmpty
  | .num _ | .tru | .fls | .null => true
  | .paren e => e.wf
  | .arr es => JE.wfL es
  | .spread e => decide (e.prec > 2) && e.wf
  | .mem a k => a.prec == 20 && a.wf && !k.isEmpty
  | .idx a i => a.prec == 20 && a.wf && decide (i.prec > 1) && i.wf
  | .call f args => f.prec == 20 && f.wf && JE.wfL args
  | .arrow _ body => decide (body.prec > 1) && body.wf
  | .bin op l r =>
      (if op = .pow then decide (l.prec > 14) && decide (r.prec ≥ 14)
       else decide (l.prec ≥ op.prec) && decide (r.prec > op.prec)) && l.wf && r.wf
  | .not a => decide (a.prec ≥ 15) && a.wf
  | .cond c t f => decide (c.prec > 2) && decide (t.prec > 1) && decide (f.prec > 1) &&
      c.wf && t.wf && f.wf
  | .objShort ks => !ks.isEmpty
def JE.wfL : List JE → Bool
  | [] => true
  | e :: es => decide (e.prec ≥ 1) && e.wf && JE.wfL es
end

/-- Declaration targets: a name or an array pattern. -/
inductive JPat where
  | n (s : String)
  | arr (xs : List String)
  deriving Repr, Inhabited

def JPat.render : JPat → String
  | .n s => s
  | .arr xs => "[" ++ commas xs ++ "]"

def JPat.names : JPat → List String
  | .n s => [s]
  | .arr xs => xs.filter (· ≠ "")

/-- Statements; `none` separators glue, `some k` starts a new line indented by `k`. -/
inductive JS where
  | decl (ds : List (JPat × JE))
  | forOf (pat : List String) (it : JE) (body : JS)
  | ifS (c : JE) (body : JS)
  | block (items : List (Option Nat × JS)) (close : Option Nat)
  | cont
  | expr (e : JE)
  | augIdx (x : String) (i : JE) (op : JOp) (rhs : JE)
  | ret (e : JE)
  deriving Repr, Inhabited

def sepDoc : Option Nat → Py.Doc
  | none => [""]
  | some k => ["", Py.spaces k]

mutual
def JS.render : JS → Py.Doc
  | .decl ds => ["const " ++ JS.renderDecls ds ++ ";"]
  | .forOf pat it body => Py.Doc.cat ["for(const [" ++ commas pat ++ "] of " ++ it.render ++ ")"] body.render
  | .ifS c body => Py.Doc.cat ["if(" ++ c.render ++ ")"] body.render
  | .block items close => Py.Doc.cats [["{"], JS.renderItems items, sepDoc close, ["}"]]
  | .cont => ["continue;"]
  | .expr e => [e.render ++ ";"]
  | .augIdx x i op rhs => [x ++ "[" ++ i.render ++ "]" ++ op.sym ++ "=" ++ rhs.render ++ ";"]
  | .ret e => ["return " ++ e.render ++ ";"]
def JS.renderDecls : List (JPat × JE) → String
  | [] => ""
  | [(p, e)] => p.render ++ "=" ++ e.render
  | (p, e) :: ds => p.render ++ "=" ++ e.render ++ "," ++ JS.renderDecls ds
def JS.renderItems : List (Option Nat × JS) → Py.Doc
  | [] => [""]
  | (sep, s) :: rest => Py.Doc.cats [sepDoc sep, s.render, JS.renderItems rest]
end

mutual
def JS.wf : JS → Bool
  | .decl ds => !ds.isEmpty && JS.wfDecls ds
  | .forOf pat it body => !pat.isEmpty && decide (it.prec > 1) && it.wf && body.isBlock && body.wf
  | .ifS c body => c.wf && body.wf
  | .block items _ => JS.wfItems items
  | .cont => true
  | .expr e => e.wf
  | .augIdx _ i op rhs => i.wf && rhs.wf && decide (rhs.prec > 1) && (op == .add || op == .band || op == .bor)
  | .ret e => e.wf
def JS.isBlock : JS → Bool
  | .block .. => true
  | _ => false
def JS.wfDecls : List (JPat × JE) → Bool
  | [] => true
  | (_, e) :: ds => decide (e.prec > 1) && e.wf && JS.wfDecls ds
def JS.wfItems : List (Option Nat × JS) → Bool
  | [] => true
  | (_, s) :: rest => s.wf && JS.wfItems rest
end

structure JFun where
  name : String
  params : List String
  items : List (Option Nat × JS)
  close : Option Nat
  deriving Repr

def JFun.render (f : JFun) : List String :=
  Py.Doc.cats [["function " ++ f.name ++ "(" ++ commas f.params ++ ")"], (JS.block f.items f.close).render]

def JFun.wf (f : JFun) : Bool := !f.params.isEmpty && JS.wfItems f.items

/-! ## Scope discipline -/

mutual
/-- Names bound by callbacks inside an expression must be fresh. -/
def JE.scopeOK (sc : List String) : JE → Bool
  | .paren e | .spread e | .mem e _ | .not e => e.scopeOK sc
  | .arr es => JE.scopeOKL sc es
  | .idx a i => a.scopeOK sc && i.scopeOK sc
  | .call f args => f.scopeOK sc && JE.scopeOKL sc args
  | .arrow pat body => (pat.filter (· ≠ "")).all (fun x => !sc.contains x) &&
      body.scopeOK (pat.filter (· ≠ "") ++ sc)
  | .bin _ l r => l.scopeOK sc && r.scopeOK sc
  | .cond c t f => c.scopeOK sc && t.scopeOK sc && f.scopeOK sc
  | _ => true
def JE.scopeOKL (sc : List String) : List JE → Bool
  | [] => true
  | e :: es => e.scopeOK sc && JE.scopeOKL sc es
end

mutual
/-- Scope check of a statement; returns the names it adds to the current block, if fresh. -/
def JS.scope (sc : List String) : JS → Option (List String)
  | .decl ds => JS.scopeDecls sc ds
  | .forOf pat it body =>
      let xs := pat.filter (· ≠ "")
      if it.scopeOK sc && xs.all (fun x => !sc.contains x) then
        (body.scope (xs ++ sc)).map (fun _ => sc) else none
  | .ifS c body => if c.scopeOK sc then (body.scope sc).map (fun _ => sc) else none
  | .block items _ => (JS.scopeItems sc items).map (fun _ => sc)
  | .cont => some sc
  | .expr e | .ret e => if e.scopeOK sc then some sc else none
  | .augIdx _ i _ rhs => if i.scopeOK sc && rhs.scopeOK sc then some sc else none
def JS.scopeDecls (sc : List String) : List (JPat × JE) → Option (List String)
  | [] => some sc
  | (p, e) :: ds => if e.scopeOK sc && p.names.all (fun x => !sc.contains x) then
      JS.scopeDecls (p.names ++ sc) ds else none
def JS.scopeItems (sc : List String) : List (Option Nat × JS) → Option (List String)
  | [] => some sc
  | (_, s) :: rest => (s.scope sc).bind (fun sc' => JS.scopeItems sc' rest)
end

def JFun.scopeOK (f : JFun) : Bool := (JS.scopeItems f.params f.items).isSome

/-! ## Lowering (extraction) -/

/-- Reserved (non-identifier) name holding the whole element of a `filter` callback. -/
def wholeName : String := "%elt"

def JOp.core : JOp → Option Op
  | .add => some .add | .bor => some .bor | .band => some .band | .pow => some .pow
  | .seq => some .eq | .sne => some .ne | .and => none

mutual
def JE.lower : JE → Option E
  | .name s => some (.var s)
  | .num n => some (.lit (.int n))
  | .tru => some (.lit (.bool true))
  | .fls => some (.lit (.bool false))
  | .null => some (.lit .none)
  | .paren e => e.lower
  | .arr [.spread a] => do return .copy (← a.lower)
  | .arr es => (JE.lowerL es).map .list
  | .spread _ => none
  | .mem a k => do return .field (← a.lower) k
  | .idx a i => do return .index (← a.lower) (← i.lower)
  | .call (.mem a "includes") [.name x] => do return .mem (.var x) (← a.lower)
  | .call (.mem (.name "Math") "min") [.spread (.call (.mem a "map") [.arrow pat body])] => do
      return .min (.comp (← body.lower) (.tup pat) (← a.lower) none)
  | .call (.mem a "filter") [.arrow pat body] => do
      return .comp (.var wholeName) (.whole wholeName pat) (← a.lower) (some (← body.lower))
  | .call (.mem a "slice") [i] => do return .sliceFrom (← a.lower) (← i.lower)
  | .call _ _ => none
  | .arrow _ _ => none
  | .bin .seq l .null => do return .isNone (← l.lower)
  | .bin .and l r => do return .and (← l.lower) (← r.lower)
  | .bin op l r => do return .bin (← op.core) (← l.lower) (← r.lower)
  | .not a => do return .not (← a.lower)
  | .cond c t f => do return .cond (← c.lower) (← t.lower) (← f.lower)
  | .objShort ks => some (.objLit ks (ks.map .var))
def JE.lowerL : List JE → Option (List E)
  | [] => some []
  | .spread _ :: _ => none
  | e :: es => do return (← e.lower) :: (← JE.lowerL es)
end

def JPat.core : JPat → Pat
  | .n s => .v s
  | .arr xs => .tup xs

mutual
def JS.lower : JS → Option (List S)
  | .decl ds => JS.lowerDecls ds
  | .forOf pat it (.block items _) => do return [.forIn (.tup pat) (← it.lower) (← JS.lowerItems items)]
  | .forOf _ _ _ => none
  | .ifS c body => do return [.ifThen (← c.lower) (← body.lower)]
  | .block items _ => JS.lowerItems items
  | .cont => some [.cont]
  | .expr (.call (.mem (.name x) "push") [e]) => do return [.append x (← e.lower)]
  | .expr _ => none
  | .augIdx x i op rhs =>
      if op == .add || op == .band || op == .bor then
        do return [.augIndex x (← i.lower) (← op.core) (← rhs.lower)]
      else none
  | .ret e => do return [.ret (← e.lower)]
def JS.lowerDecls : List (JPat × JE) → Option (List S)
  | [] => some []
  | (p, e) :: ds => do return .assign p.core (← e.lower) :: (← JS.lowerDecls ds)
def JS.lowerItems : List (Option Nat × JS) → Option (List S)
  | [] => some []
  | (_, s) :: rest => do return (← s.lower) ++ (← JS.lowerItems rest)
end

def JFun.lower (f : JFun) : Option Fn := (JS.lowerItems f.items).map (Fn.mk f.params)

/-! ## The extracted `bellman` of website `public/intervention-core.mjs` -/

/-- The exact lines of the uploaded `intervention-core.mjs`. -/
def interventionJs : List String :=
  source_lines% "../source_reference/proof-carrying-science-site/public/intervention-core.mjs.txt"

section
open JE
private def nm (s : String) : JE := .name s
private def ix (a : String) (i : Nat) : JE := .idx (nm a) (.num i)
private def tf (k : String) : JE := .idx (.mem (nm "t") k) (nm "n")
private def flipOr (x : JE) : JE := .paren (.cond (nm "flip") x (.num 0))

def bellmanCST : JFun where
  name := "bellman"
  params := ["nodes", "t"]
  items := [
    (some 1, .decl [(.n "cells", .arr [.null, .arr [.num 0, .num 1, .num 0, .num 0]]),
      (.n "choices", .arr [.null, .null]), (.n "names", .mem (.mem (nm "t") "problem") "variables")]),
    (some 1, .forOf ["v", "lo", "hi"] (nm "nodes") (.block [
      (none, .decl [(.n "n", .idx (nm "names") (nm "v")), (.n "bit", .bin .pow (.num 2) (nm "v")),
        (.n "branches", .arr [])]),
      (some 2, .forOf ["value", "child"] (.arr [.arr [.fls, nm "lo"], .arr [.tru, nm "hi"]]) (.block [
        (some 3, .ifS (.bin .and (.call (.mem (.mem (nm "t") "locked") "includes") [nm "n"])
            (.bin .sne (nm "value") (tf "baseline"))) .cont),
        (some 3, .decl [(.n "cell", .idx (nm "cells") (nm "child"))]),
        (none, .ifS (.bin .seq (nm "cell") .null) .cont),
        (none, .decl [(.n "flip", .bin .sne (nm "value") (tf "baseline"))]),
        (some 3, .expr (.call (.mem (nm "branches") "push") [.arr [nm "value", .arr [
          .bin .add (ix "cell" 0) (flipOr (tf "costs")), ix "cell" 1,
          .bin .bor (ix "cell" 2) (flipOr (nm "bit")), .bin .bor (ix "cell" 3) (flipOr (nm "bit"))]]]))]
        (some 2))),
      (some 2, .ifS (.not (.mem (nm "branches") "length")) (.block [
        (none, .expr (.call (.mem (nm "cells") "push") [.null])),
        (none, .expr (.call (.mem (nm "choices") "push") [.null])), (none, .cont)] none)),
      (some 2, .decl [
        (.n "best", .call (.mem (nm "Math") "min") [.spread (.call (.mem (nm "branches") "map")
          [.arrow ["", "c"] (ix "c" 0)])]),
        (.n "winners", .call (.mem (nm "branches") "filter") [.arrow ["", "c"] (.bin .seq (ix "c" 0) (nm "best"))]),
        (.n "cell", .arr [.spread (.idx (ix "winners" 0) (.num 1))])]),
      (some 2, .forOf ["", "other"] (.call (.mem (nm "winners") "slice") [.num 1]) (.block [
        (none, .augIdx "cell" (.num 1) .add (ix "other" 1)),
        (none, .augIdx "cell" (.num 2) .band (ix "other" 2)),
        (none, .augIdx "cell" (.num 3) .bor (ix "other" 3))] none)),
      (some 2, .expr (.call (.mem (nm "cells") "push") [nm "cell"])),
      (none, .expr (.call (.mem (nm "choices") "push") [.idx (ix "winners" 0) (.num 0)]))]
      (some 1))),
    (none, .ret (.objShort ["cells", "choices"]))]
  close := some 0
end

/-- **Source binding**: the extraction tree renders to exactly lines 14–27 of the uploaded
website `public/intervention-core.mjs` (byte-identical per line). -/
theorem javascript_bellman_source_bound :
    (interventionJs.drop 13).take 14 = bellmanCST.render := by decide +kernel

/-- Precedence / associativity discipline (unambiguous text). -/
theorem javascript_bellman_wf : bellmanCST.wf = true := by decide +kernel

/-- No declaration shadows a name in scope (block scoping = flat environment + block exit). -/
theorem javascript_bellman_scope : bellmanCST.scopeOK = true := by decide +kernel

/-! ## The extracted executable program -/

section
open E
private def v (x : String) : E := .var x
private def i (k : Int) : E := .lit (.int k)
private def at' (x : String) (k : Int) : E := .index (v x) (i k)
private def tfE (k : String) : E := .index (.field (v "t") k) (v "n")
private def flipOrE (x : E) : E := .cond (v "flip") x (i 0)

/-- The executable meaning of the JS `bellman` produced by extraction. -/
def bellmanCore : Fn where
  params := ["nodes", "t"]
  body := [
    .assign (.v "cells") (.list [.lit .none, .list [i 0, i 1, i 0, i 0]]),
    .assign (.v "choices") (.list [.lit .none, .lit .none]),
    .assign (.v "names") (.field (.field (v "t") "problem") "variables"),
    .forIn (.tup ["v", "lo", "hi"]) (v "nodes") [
      .assign (.v "n") (.index (v "names") (v "v")),
      .assign (.v "bit") (.bin .pow (i 2) (v "v")),
      .assign (.v "branches") (.list []),
      .forIn (.tup ["value", "child"]) (.list [.list [.lit (.bool false), v "lo"], .list [.lit (.bool true), v "hi"]]) [
        .ifThen (.and (.mem (v "n") (.field (v "t") "locked")) (.bin .ne (v "value") (tfE "baseline"))) [.cont],
        .assign (.v "cell") (.index (v "cells") (v "child")),
        .ifThen (.isNone (v "cell")) [.cont],
        .assign (.v "flip") (.bin .ne (v "value") (tfE "baseline")),
        .append "branches" (.list [v "value", .list [
          .bin .add (at' "cell" 0) (flipOrE (tfE "costs")), at' "cell" 1,
          .bin .bor (at' "cell" 2) (flipOrE (v "bit")), .bin .bor (at' "cell" 3) (flipOrE (v "bit"))]])],
      .ifThen (.not (.field (v "branches") "length")) [.append "cells" (.lit .none), .append "choices" (.lit .none), .cont],
      .assign (.v "best") (.min (.comp (at' "c" 0) (.tup ["", "c"]) (v "branches") none)),
      .assign (.v "winners") (.comp (v wholeName) (.whole wholeName ["", "c"]) (v "branches")
        (some (.bin .eq (at' "c" 0) (v "best")))),
      .assign (.v "cell") (.copy (.index (at' "winners" 0) (i 1))),
      .forIn (.tup ["", "other"]) (.sliceFrom (v "winners") (i 1)) [
        .augIndex "cell" (i 1) .add (at' "other" 1),
        .augIndex "cell" (i 2) .band (at' "other" 2),
        .augIndex "cell" (i 3) .bor (at' "other" 3)],
      .append "cells" (v "cell"),
      .append "choices" (.index (at' "winners" 0) (i 0))],
    .ret (.objLit ["cells", "choices"] [v "cells", v "choices"])]
end

/-- **Extraction certificate (lowering)**: the source-bound tree lowers to `bellmanCore`. -/
theorem javascript_bellman_lowers : bellmanCST.lower = some bellmanCore := rfl

end PCSRuntimeRefinement.Js
