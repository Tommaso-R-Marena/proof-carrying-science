import PCSRuntimeRefinement.Core
import PCSRuntimeRefinement.SourceText

/-!
# Python front end: concrete syntax, exact rendering, precedence check and lowering

* `PE` / `PS` / `PL` / `PFun` — a *concrete* syntax tree for the supported Python subset.  It
  records parentheses, line breaks inside brackets, docstrings, `;`-separated simple statements
  and trailing comments, so that `PFun.render` reproduces source text byte for byte.  Any
  construct outside the subset (classes, `try`, lambdas, keyword arguments, `while`, `/`, …)
  simply has no syntax tree; such source cannot be certified.
* `PE.wf` — the precedence/associativity check: every operator operand that is not
  parenthesised binds strictly tighter (or equally tight on the left of a left-associative
  operator) according to Python's grammar, comparisons are never chained, and generator /
  comprehension iterables are `or_test`s.  Under this check the rendered text has exactly one
  Python parse, namely the tree.
* `PFun.lower` — extraction into the shared executable semantics (`PCSRuntimeRefinement.Core`).
  It is partial: unsupported calls (anything but `list(·)`, `min(·)`, `x.append(·)`) are
  rejected.
* **Extraction certificate** for `bellman` of `pcs/experimental/intervention.py`:
  `python_bellman_source_bound` (the tree renders to the exact source lines 33–62 of the
  uploaded file), `python_bellman_wf` and `python_bellman_lowers`.
-/

namespace PCSRuntimeRefinement.Py

open PCSRuntimeRefinement

/-! ## Layout documents -/

/-- A document is a non-empty list of lines; `cat` glues the last line of the first to the
first line of the second. -/
abbrev Doc := List String

def Doc.cat (a b : Doc) : Doc :=
  match a.reverse, b with
  | [], _ => b
  | _, [] => a
  | l :: rest, b0 :: bs => rest.reverse ++ (l ++ b0) :: bs

def Doc.cats : List Doc → Doc
  | [] => [""]
  | [d] => d
  | d :: ds => Doc.cat d (Doc.cats ds)

def spaces (n : Nat) : String := String.ofList (List.replicate n ' ')

/-- Decimal digits (structural, kernel-reducible). -/
def natDigits : Nat → Nat → List Char
  | 0, _ => []
  | fuel + 1, n => if n < 10 then [Char.ofNat (48 + n)] else natDigits fuel (n / 10) ++ [Char.ofNat (48 + n % 10)]

/-- Python `str(n)` for a natural number literal. -/
def natStr (n : Nat) : String := String.ofList (natDigits (n + 1) n)

/-! ## Concrete syntax -/

inductive BinOp where
  | add | bor | band | shl | eq | ne
  deriving DecidableEq, Repr

def BinOp.sym : BinOp → String
  | .add => "+" | .bor => "|" | .band => "&" | .shl => "<<" | .eq => "==" | .ne => "!="

/-- Python grammar levels (higher binds tighter). -/
def BinOp.prec : BinOp → Nat
  | .eq | .ne => 5 | .bor => 6 | .band => 8 | .shl => 9 | .add => 10

def BinOp.core : BinOp → Op
  | .add => .add | .bor => .bor | .band => .band | .shl => .shl | .eq => .eq | .ne => .ne

inductive PE where
  | name (s : String)
  | num (n : Nat)
  | tru | fls | none
  | paren (e : PE)
  | tuple (es : List PE)
  | list (es : List PE)
  | sub (a i : PE)
  | sliceFrom (a i : PE)
  | bin (op : BinOp) (l r : PE)
  | notE (a : PE)
  | andE (l r : PE)
  | ifE (t c f : PE)
  | isNone (a : PE)
  | inE (l r : PE)
  | call (f : String) (args : List PE)
  | genCall (f : String) (elt : PE) (tgt : List String) (it : PE)
  | listComp (elt : PE) (tgt : List String) (it : PE) (cond : Option PE)
  /-- Line break followed by `col` spaces (layout inside brackets only). -/
  | nl (col : Nat) (e : PE)
  deriving Repr, Inhabited

def tgtText (xs : List String) : String := ", ".intercalate xs

def PE.isNl : PE → Bool
  | .nl _ _ => true
  | _ => false

mutual
def PE.render : PE → Doc
  | .name s => [s]
  | .num n => [natStr n]
  | .tru => ["True"]
  | .fls => ["False"]
  | .none => ["None"]
  | .paren e => Doc.cats [["("], e.render, [")"]]
  | .tuple es => PE.renderSeq es
  | .list es => Doc.cats [["["], PE.renderSeq es, ["]"]]
  | .sub a i => Doc.cats [a.render, ["["], i.render, ["]"]]
  | .sliceFrom a i => Doc.cats [a.render, ["["], i.render, [":]"]]
  | .bin op l r => Doc.cats [l.render, [" " ++ op.sym ++ " "], r.render]
  | .notE a => Doc.cat ["not "] a.render
  | .andE l r => Doc.cats [l.render, [" and "], r.render]
  | .ifE t c f => Doc.cats [t.render, [" if "], c.render, [" else "], f.render]
  | .isNone a => Doc.cat a.render [" is None"]
  | .inE l r => Doc.cats [l.render, [" in "], r.render]
  | .call f args => Doc.cats [[f ++ "("], PE.renderSeq args, [")"]]
  | .genCall f elt tgt it =>
      Doc.cats [[f ++ "("], elt.render, [" for " ++ tgtText tgt ++ " in "], it.render, [")"]]
  | .listComp elt tgt it cond =>
      Doc.cats [["["], elt.render, [" for " ++ tgtText tgt ++ " in "], it.render,
        PE.renderCond cond, ["]"]]
  | .nl col e => Doc.cat ["", spaces col] e.render
def PE.renderCond : Option PE → Doc
  | .none => [""]
  | .some c => Doc.cat [" if "] c.render
/-- Comma-separated items; an item that starts with a line break follows the comma directly. -/
def PE.renderSeq : List PE → Doc
  | [] => [""]
  | e :: es => Doc.cat e.render (PE.renderTail es)
def PE.renderTail : List PE → Doc
  | [] => [""]
  | e :: es => Doc.cats [[if e.isNl then "," else ", "], e.render, PE.renderTail es]
end

/-- Grammar level of an expression (`20` = atom / primary). -/
def PE.prec : PE → Nat
  | .tuple _ => 0
  | .ifE .. => 1
  | .andE .. => 3
  | .notE _ => 4
  | .isNone _ | .inE .. => 5
  | .bin op _ _ => op.prec
  | .nl _ e => e.prec
  | _ => 20

mutual
/-- Precedence / associativity well-formedness (unambiguous rendering). -/
def PE.wf : PE → Bool
  | .name s => !s.isEmpty
  | .num _ | .tru | .fls | .none => true
  | .paren e => e.wf
  | .tuple es => PE.wfItems es && es.length ≥ 2
  | .list es => PE.wfItems es
  | .sub a i => a.prec == 20 && a.wf && decide (i.prec ≥ 1) && i.wf
  | .sliceFrom a i => a.prec == 20 && a.wf && decide (i.prec ≥ 1) && i.wf
  | .bin op l r =>
      (if op.prec = 5 then decide (l.prec > 5) else decide (l.prec ≥ op.prec)) &&
        decide (r.prec > op.prec) && l.wf && r.wf
  | .notE a => decide (a.prec ≥ 4) && a.wf
  | .andE l r => decide (l.prec ≥ 3) && decide (r.prec > 3) && l.wf && r.wf
  | .ifE t c f => decide (t.prec > 1) && decide (c.prec > 1) && decide (f.prec ≥ 1) &&
      t.wf && c.wf && f.wf
  | .isNone a => decide (a.prec > 5) && a.wf
  | .inE l r => decide (l.prec > 5) && decide (r.prec > 5) && l.wf && r.wf
  | .call _ args => PE.wfItems args
  | .genCall _ elt _ it => decide (elt.prec ≥ 1) && decide (it.prec > 1) && elt.wf && it.wf
  | .listComp elt _ it c => decide (elt.prec ≥ 1) && decide (it.prec > 1) && elt.wf && it.wf &&
      PE.wfCond c
  | .nl _ e => e.wf
def PE.wfItems : List PE → Bool
  | [] => true
  | e :: es => decide (e.prec ≥ 1) && e.wf && PE.wfItems es
def PE.wfCond : Option PE → Bool
  | .none => true
  | .some c => decide (c.prec > 1) && c.wf
end

/-- Simple statements. -/
inductive PS where
  | assign (tgts : List String) (rhs : PE)
  | augSub (x : String) (i : PE) (op : BinOp) (rhs : PE)
  | append (x : String) (arg : PE)
  | cont
  | ret (e : PE)
  deriving Repr, Inhabited

def PS.render : PS → Doc
  | .assign tgts rhs => Doc.cat [tgtText tgts ++ " = "] rhs.render
  | .augSub x i op rhs => Doc.cats [[x ++ "["], i.render, ["] " ++ op.sym ++ "= "], rhs.render]
  | .append x arg => Doc.cats [[x ++ ".append("], arg.render, [")"]]
  | .cont => ["continue"]
  | .ret e => Doc.cat ["return "] e.render

def PS.wf : PS → Bool
  | .assign tgts rhs => !tgts.isEmpty && rhs.wf
  | .augSub _ i op rhs => decide (i.prec ≥ 1) && i.wf && rhs.wf && decide (rhs.prec ≥ 1) &&
      (op == .add || op == .bor || op == .band)
  | .append _ arg => decide (arg.prec ≥ 1) && arg.wf
  | .cont => true
  | .ret e => e.wf

/-- Logical lines and compound statements. -/
inductive PL where
  | simple (ss : List PS) (comment : Option String)
  | forS (tgt : List String) (it : PE) (body : List PL)
  | ifS (c : PE) (body : List PL)
  /-- A docstring: first line text, verbatim continuation lines, closing `"""` line. -/
  | doc (first : String) (rest : List String)
  deriving Repr, Inhabited

def renderSimple (ss : List PS) : Doc :=
  match ss with
  | [] => [""]
  | s :: rest => rest.foldl (fun d t => Doc.cats [d, ["; "], t.render]) s.render

mutual
def PL.render (ind : Nat) : PL → List String
  | .simple ss c => Doc.cats [[spaces ind], renderSimple ss,
      [match c with | .none => "" | .some t => "  # " ++ t]]
  | .forS tgt it body =>
      Doc.cats [[spaces ind ++ "for " ++ tgtText tgt ++ " in "], it.render, [":"]] ++
        PL.renderB (ind + 4) body
  | .ifS c body => Doc.cats [[spaces ind ++ "if "], c.render, [":"]] ++ PL.renderB (ind + 4) body
  | .doc first rest => (spaces ind ++ "\"\"\"" ++ first) :: rest ++ [spaces ind ++ "\"\"\""]
def PL.renderB (ind : Nat) : List PL → List String
  | [] => []
  | l :: ls => PL.render ind l ++ PL.renderB ind ls
end

/-- Whether a line contains `"""` (which would end the docstring early). -/
def hasTripleQuote : List Char → Bool
  | '"' :: '"' :: '"' :: _ => true
  | _ :: cs => hasTripleQuote cs
  | [] => false

mutual
def PL.wf : PL → Bool
  | .simple ss _ => !ss.isEmpty && ss.all PS.wf
  | .forS tgt it body => !tgt.isEmpty && decide (it.prec ≥ 1) && it.wf && !body.isEmpty &&
      PL.wfB body
  | .ifS c body => decide (c.prec ≥ 1) && c.wf && !body.isEmpty && PL.wfB body
  | .doc first rest => (first :: rest).all (fun l => !hasTripleQuote l.toList)
def PL.wfB : List PL → Bool
  | [] => true
  | l :: ls => PL.wf l && PL.wfB ls
end

structure PFun where
  name : String
  params : List String
  body : List PL
  deriving Repr

def PFun.render (f : PFun) : List String :=
  ("def " ++ f.name ++ "(" ++ tgtText f.params ++ "):") :: PL.renderB 4 f.body

def PFun.wf (f : PFun) : Bool := !f.params.isEmpty && PL.wfB f.body

/-! ## Lowering (extraction) into the executable semantics -/

def patOf : List String → Pat
  | [x] => .v x
  | xs => .tup xs

mutual
def PE.lower : PE → Option E
  | .name s => some (.var s)
  | .num n => some (.lit (.int n))
  | .tru => some (.lit (.bool true))
  | .fls => some (.lit (.bool false))
  | .none => some (.lit .none)
  | .paren e => e.lower
  | .tuple es => (PE.lowerL es).map .tuple
  | .list es => (PE.lowerL es).map .list
  | .sub a i => do return .index (← a.lower) (← i.lower)
  | .sliceFrom a i => do return .sliceFrom (← a.lower) (← i.lower)
  | .bin op l r => do return .bin op.core (← l.lower) (← r.lower)
  | .notE a => do return .not (← a.lower)
  | .andE l r => do return .and (← l.lower) (← r.lower)
  | .ifE t c f => do return .cond (← c.lower) (← t.lower) (← f.lower)
  | .isNone a => do return .isNone (← a.lower)
  | .inE l r => do return .mem (← l.lower) (← r.lower)
  | .call "list" [a] => do return .copy (← a.lower)
  | .call _ _ => Option.none
  | .genCall "min" elt tgt it => do
      return .min (.comp (← elt.lower) (patOf tgt) (← it.lower) Option.none)
  | .genCall _ _ _ _ => Option.none
  | .listComp elt tgt it c => do
      return .comp (← elt.lower) (patOf tgt) (← it.lower) (← PE.lowerCond c)
  | .nl _ e => e.lower
def PE.lowerL : List PE → Option (List E)
  | [] => some []
  | e :: es => do return (← e.lower) :: (← PE.lowerL es)
def PE.lowerCond : Option PE → Option (Option E)
  | .none => some Option.none
  | .some c => (c.lower).map some
end

def PS.lower : PS → Option S
  | .assign tgts rhs => (rhs.lower).map (.assign (patOf tgts))
  | .augSub x i op rhs => do return .augIndex x (← i.lower) op.core (← rhs.lower)
  | .append x arg => (arg.lower).map (.append x)
  | .cont => some .cont
  | .ret e => (e.lower).map .ret

mutual
def PL.lower : PL → Option (List S)
  | .simple ss _ => ss.mapM PS.lower
  | .forS tgt it body => do return [.forIn (patOf tgt) (← it.lower) (← PL.lowerB body)]
  | .ifS c body => do return [.ifThen (← c.lower) (← PL.lowerB body)]
  | .doc _ _ => some []
def PL.lowerB : List PL → Option (List S)
  | [] => some []
  | l :: ls => do return (← PL.lower l) ++ (← PL.lowerB ls)
end

def PFun.lower (f : PFun) : Option Fn := (PL.lowerB f.body).map (Fn.mk f.params)

/-! ## The extracted `bellman` of `pcs/experimental/intervention.py` -/

/-- The exact lines of the uploaded `intervention.py`. -/
def interventionPy : List String :=
  source_lines% "../source_reference/proof-carrying-science/pcs/experimental/intervention.py.txt"

section
open PE
private def n (s : String) : PE := .name s
private def ix (a : String) (i : Nat) : PE := .sub (n a) (.num i)

def bellmanCST : PFun where
  name := "bellman"
  params := ["nodes", "names", "baseline", "costs", "locked"]
  body := [
    .doc "One pass over append-ordered nodes; skipped variables retain baseline."
      ["", "    Strictly positive costs make that skipped-variable completion uniquely optimal.",
       "    Cells are null (infeasible) or [cost, count, mandatory-mask, possible-mask]."],
    .simple [.assign ["cells"] (.list [.none, .list [.num 0, .num 1, .num 0, .num 0]])] .none,
    .simple [.assign ["choices"] (.list [.none, .none])] .none,
    .forS ["var", "low", "high"] (n "nodes") [
      .simple [.assign ["name", "bit"] (.tuple [.sub (n "names") (n "var"), .bin .shl (.num 1) (n "var")])] .none,
      .simple [.assign ["branches"] (.list [])] .none,
      .forS ["value", "child"] (.paren (.tuple [.paren (.tuple [.fls, n "low"]), .paren (.tuple [.tru, n "high"])])) [
        .ifS (.andE (.inE (n "name") (n "locked")) (.bin .ne (n "value") (.sub (n "baseline") (n "name"))))
          [.simple [.cont] .none],
        .simple [.assign ["cell"] (.sub (n "cells") (n "child"))] .none,
        .ifS (.isNone (n "cell")) [.simple [.cont] .none],
        .simple [.assign ["flip"] (.bin .ne (n "value") (.sub (n "baseline") (n "name")))] .none,
        .simple [.append "branches" (.paren (.tuple [n "value", .list [
          .bin .add (ix "cell" 0) (.paren (.ifE (.sub (n "costs") (n "name")) (n "flip") (.num 0))),
          .nl 37 (ix "cell" 1),
          .bin .bor (ix "cell" 2) (.paren (.ifE (n "bit") (n "flip") (.num 0))),
          .nl 37 (.bin .bor (ix "cell" 3) (.paren (.ifE (n "bit") (n "flip") (.num 0))))]]))] .none],
      .ifS (.notE (n "branches"))
        [.simple [.append "cells" .none, .append "choices" .none, .cont] .none],
      .simple [.assign ["best"] (.genCall "min" (ix "cell" 0) ["_", "cell"] (n "branches"))] .none,
      .simple [.assign ["winners"] (.listComp (.paren (.tuple [n "value", n "cell"])) ["value", "cell"]
        (n "branches") (some (.bin .eq (ix "cell" 0) (n "best"))))] .none,
      .simple [.assign ["cell"] (.call "list" [.sub (ix "winners" 0) (.num 1)])] .none,
      .forS ["_", "other"] (.sliceFrom (n "winners") (.num 1)) [
        .simple [.augSub "cell" (.num 1) .add (ix "other" 1), .augSub "cell" (.num 2) .band (ix "other" 2),
          .augSub "cell" (.num 3) .bor (ix "other" 3)] .none],
      .simple [.append "cells" (n "cell"), .append "choices" (.sub (ix "winners" 0) (.num 0))]
        (some "False wins equal costs.")],
    .simple [.ret (.tuple [n "cells", n "choices"])] .none]
end

/-- **Source binding**: the extraction tree renders to exactly lines 33–62 of the uploaded
`pcs/experimental/intervention.py` (byte-identical per line). -/
theorem python_bellman_source_bound :
    (interventionPy.drop 32).take 30 = bellmanCST.render := by decide +kernel

/-- The tree satisfies Python's precedence/associativity discipline (unambiguous text). -/
theorem python_bellman_wf : bellmanCST.wf = true := by decide +kernel

/-! ## The extracted executable program -/

section
open E
private def v (x : String) : E := .var x
private def i (k : Int) : E := .lit (.int k)
private def at' (x : String) (k : Int) : E := .index (v x) (i k)
private def flipOr (x : String) : E := .cond (v "flip") (v x) (i 0)

/-- The executable meaning of `bellman` produced by extraction (statement by statement). -/
def bellmanCore : Fn where
  params := ["nodes", "names", "baseline", "costs", "locked"]
  body := [
    .assign (.v "cells") (.list [.lit .none, .list [i 0, i 1, i 0, i 0]]),
    .assign (.v "choices") (.list [.lit .none, .lit .none]),
    .forIn (.tup ["var", "low", "high"]) (v "nodes") [
      .assign (.tup ["name", "bit"]) (.tuple [.index (v "names") (v "var"), .bin .shl (i 1) (v "var")]),
      .assign (.v "branches") (.list []),
      .forIn (.tup ["value", "child"])
          (.tuple [.tuple [.lit (.bool false), v "low"], .tuple [.lit (.bool true), v "high"]]) [
        .ifThen (.and (.mem (v "name") (v "locked")) (.bin .ne (v "value") (.index (v "baseline") (v "name"))))
          [.cont],
        .assign (.v "cell") (.index (v "cells") (v "child")),
        .ifThen (.isNone (v "cell")) [.cont],
        .assign (.v "flip") (.bin .ne (v "value") (.index (v "baseline") (v "name"))),
        .append "branches" (.tuple [v "value", .list [
          .bin .add (at' "cell" 0) (.cond (v "flip") (.index (v "costs") (v "name")) (i 0)),
          at' "cell" 1,
          .bin .bor (at' "cell" 2) (flipOr "bit"),
          .bin .bor (at' "cell" 3) (flipOr "bit")]])],
      .ifThen (.not (v "branches")) [.append "cells" (.lit .none), .append "choices" (.lit .none), .cont],
      .assign (.v "best") (.min (.comp (at' "cell" 0) (.tup ["_", "cell"]) (v "branches") none)),
      .assign (.v "winners") (.comp (.tuple [v "value", v "cell"]) (.tup ["value", "cell"]) (v "branches")
        (some (.bin .eq (at' "cell" 0) (v "best")))),
      .assign (.v "cell") (.copy (.index (at' "winners" 0) (i 1))),
      .forIn (.tup ["_", "other"]) (.sliceFrom (v "winners") (i 1)) [
        .augIndex "cell" (i 1) .add (at' "other" 1),
        .augIndex "cell" (i 2) .band (at' "other" 2),
        .augIndex "cell" (i 3) .bor (at' "other" 3)],
      .append "cells" (v "cell"),
      .append "choices" (.index (at' "winners" 0) (i 0))],
    .ret (.tuple [v "cells", v "choices"])]
end

/-- **Extraction certificate (lowering)**: the source-bound tree lowers to `bellmanCore`. -/
theorem python_bellman_lowers : bellmanCST.lower = some bellmanCore := rfl

end PCSRuntimeRefinement.Py
