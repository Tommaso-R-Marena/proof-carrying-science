import PCSConditionalRuntime.Semantics
import PCSRuntimeRefinement.SourceText

/-!
# Python front end for the heap semantics: concrete syntax, exact rendering, precedence
# discipline, module certificates and lowering

* `PE` / `PS` / `PL` — a *concrete* syntax tree for the Python fragment of the current
  `conditional.py`: classes, methods, keyword arguments, dictionary / set / tuple displays,
  comprehensions, chained comparisons, `is` / `is not`, `while`, `try`/`except … as …`,
  `raise`, `assert`, inline suites (`if c: stmt`), `;`-separated statements, standalone and
  trailing comments, and line breaks inside brackets.  `PL.renderB` reproduces source text
  byte for byte.
* `PE.wf` — precedence / associativity / bracket discipline (Python grammar levels):
  every operand that is not parenthesised binds tighter than required, line breaks only occur
  inside brackets, `k: v` / `k=v` items only occur in dictionary displays / call argument
  lists.  Under `wf` the rendered text has exactly one Python parse, namely the tree.
* `Seg` / `checkModule` — a **whole-file certificate**: the file is cut into segments that
  are either extracted code (rendered byte-for-byte) or an unextracted top-level function
  (`opaqueDef name len`: the first line is `def name(` and every other line is blank or
  indented, so the segment is exactly that function's text).  Every line of the file belongs
  to exactly one segment.
* `lowerModule` — extraction into the heap semantics: top-level functions, classes with
  methods (`Cls.meth`), exception classes, module-level assignments (run once to build the
  globals) and the list of unextracted functions, whose behaviour becomes an explicit
  parameter of every theorem.  Names are resolved at run time through this table.
-/

namespace PCSCR.Py

open PCSCR

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

def natDigits : Nat → Nat → List Char
  | 0, _ => []
  | fuel + 1, n => if n < 10 then [Char.ofNat (48 + n)] else natDigits fuel (n / 10) ++ [Char.ofNat (48 + n % 10)]

def natStr (n : Nat) : String := String.ofList (natDigits (n + 1) n)

/-! ## Concrete syntax -/

inductive Op where
  | add | sub | eq | ne | lt | le | gt | ge | is | isNot | inn | notIn
  deriving DecidableEq, Repr

def Op.sym : Op → String
  | .add => "+" | .sub => "-" | .eq => "==" | .ne => "!=" | .lt => "<" | .le => "<=" | .gt => ">"
  | .ge => ">=" | .is => "is" | .isNot => "is not" | .inn => "in" | .notIn => "not in"

def Op.prec : Op → Nat
  | .add | .sub => 10
  | _ => 5

inductive PE where
  | name (s : String)
  | num (n : Nat)
  | str (s : String)
  | tru | fls | none
  | paren (e : PE)
  /-- Bare tuple `a, b` (no parentheses). -/
  | tuple (es : List PE)
  | list (es : List PE)
  /-- Dictionary display; items are `kv` (possibly preceded by a line break). -/
  | dict (items : List PE)
  | kv (k v : PE)
  /-- Keyword argument `k=v` (call arguments only). -/
  | kw (k : String) (v : PE)
  | set (es : List PE)
  | attr (e : PE) (f : String)
  | sub (a i : PE)
  /-- `a[i:]`. -/
  | slice (a i : PE)
  | call (f : PE) (args : List PE)
  | bin (op : Op) (l r : PE)
  /-- Binary arithmetic written without spaces (`a-2`). -/
  | binT (op : Op) (l r : PE)
  /-- Negative integer literal (`-1`, unary minus on a literal). -/
  | negNum (n : Nat)
  | chain (op1 op2 : Op) (a b c : PE)
  | notE (a : PE)
  | andE (l r : PE)
  | orE (l r : PE)
  | ifE (t c f : PE)
  | comp (elt : PE) (x : String) (it : PE) (cond : Option PE)
  /-- Line break followed by `col` spaces (inside brackets only). -/
  | nl (col : Nat) (e : PE)
  deriving Repr, Inhabited

def PE.isNl : PE → Bool
  | .nl _ _ => true
  | _ => false

mutual
def PE.render : PE → Doc
  | .name s => [s]
  | .num n => [natStr n]
  | .str s => ["'" ++ s ++ "'"]
  | .tru => ["True"]
  | .fls => ["False"]
  | .none => ["None"]
  | .paren e => Doc.cats [["("], e.render, [")"]]
  | .tuple es => PE.renderSeq es
  | .list es => Doc.cats [["["], PE.renderSeq es, ["]"]]
  | .dict items => Doc.cats [["{"], PE.renderSeq items, ["}"]]
  | .kv k v => Doc.cats [k.render, [": "], v.render]
  | .kw k v => Doc.cat [k ++ "="] v.render
  | .set es => Doc.cats [["{"], PE.renderSeq es, ["}"]]
  | .attr e f => Doc.cat e.render ["." ++ f]
  | .sub a i => Doc.cats [a.render, ["["], i.render, ["]"]]
  | .slice a i => Doc.cats [a.render, ["["], i.render, [":]"]]
  | .call f args => Doc.cats [f.render, ["("], PE.renderSeq args, [")"]]
  | .bin op l r => Doc.cats [l.render, [" " ++ op.sym ++ " "], r.render]
  | .binT op l r => Doc.cats [l.render, [op.sym], r.render]
  | .negNum n => ["-" ++ natStr n]
  | .chain op1 op2 a b c => Doc.cats [a.render, [" " ++ op1.sym ++ " "], b.render, [" " ++ op2.sym ++ " "], c.render]
  | .notE a => Doc.cat ["not "] a.render
  | .andE l r => Doc.cats [l.render, [" and "], r.render]
  | .orE l r => Doc.cats [l.render, [" or "], r.render]
  | .ifE t c f => Doc.cats [t.render, [" if "], c.render, [" else "], f.render]
  | .comp elt x it cond => Doc.cats [["["], elt.render, [" for " ++ x ++ " in "], it.render, PE.renderCond cond, ["]"]]
  | .nl col e => Doc.cat ["", spaces col] e.render
def PE.renderCond : Option PE → Doc
  | .none => [""]
  | .some c => Doc.cat [" if "] c.render
def PE.renderSeq : List PE → Doc
  | [] => [""]
  | e :: es => Doc.cat e.render (PE.renderTail es)
def PE.renderTail : List PE → Doc
  | [] => [""]
  | e :: es => Doc.cats [[if e.isNl then "," else ", "], e.render, PE.renderTail es]
end

/-- Grammar level (`20` = primary / atom). -/
def PE.prec : PE → Nat
  | .tuple _ => 0
  | .ifE .. => 1
  | .orE .. => 2
  | .andE .. => 3
  | .notE _ => 4
  | .chain .. => 5
  | .bin op _ _ => op.prec
  | .binT op _ _ => op.prec
  | .negNum _ => 12
  | .kv .. => 0
  | .kw .. => 0
  | .nl _ e => e.prec
  | _ => 20

/-! Kernel-reducible string predicates (everything goes through `String.toList`). -/

def cIsDigit (ch : Char) : Bool := 48 ≤ ch.toNat && ch.toNat ≤ 57
def cIsAlpha (ch : Char) : Bool := (65 ≤ ch.toNat && ch.toNat ≤ 90) || (97 ≤ ch.toNat && ch.toNat ≤ 122)
def sAll (s : String) (p : Char → Bool) : Bool := s.toList.all p
def sEmpty (s : String) : Bool := s.toList.isEmpty
def sStarts (s pre : String) : Bool := pre.toList.isPrefixOf s.toList
def sEnds (s suf : String) : Bool := suf.toList.reverse.isPrefixOf s.toList.reverse

def validName (s : String) : Bool :=
  match s.toList with
  | [] => false
  | c :: cs => (cIsAlpha c || c == '_') && cs.all (fun ch => cIsAlpha ch || cIsDigit ch || ch == '_')

def validStr (s : String) : Bool := sAll s (fun ch => ch != '\'' && ch != '\\' && ch != '\n')

def PE.isPrimaryBase : PE → Bool
  | .num _ => false
  | e => e.prec == 20

mutual
/-- Precedence / bracket well-formedness; `br` = inside brackets (line breaks allowed). -/
def PE.wf (br : Bool) : PE → Bool
  | .name s => validName s
  | .num _ | .tru | .fls | .none => true
  | .str s => validStr s
  | .paren e => decide (e.prec ≥ 0) && e.wf true
  | .tuple es => es.length ≥ 2 && PE.wfItems br es
  | .list es => PE.wfItems true es
  | .dict items => PE.wfKVs items
  | .kv _ _ => false
  | .kw _ _ => false
  | .set es => !es.isEmpty && PE.wfItems true es
  | .attr e f => e.isPrimaryBase && e.wf br && validName f
  | .sub a i => a.prec == 20 && a.wf br && decide (i.prec ≥ 1) && i.wf true
  | .slice a i => a.prec == 20 && a.wf br && decide (i.prec ≥ 1) && i.wf true
  | .call f args => f.isPrimaryBase && f.wf br && PE.wfArgs args
  | .bin op l r =>
      (if op.prec = 5 then decide (l.prec > 5) else decide (l.prec ≥ op.prec)) &&
        decide (r.prec > op.prec) && l.wf br && r.wf br
  | .binT op l r => op.prec == 10 && decide (l.prec ≥ op.prec) && decide (r.prec > op.prec) && l.wf br && r.wf br
  | .negNum _ => true
  | .chain op1 op2 a b c => op1.prec == 5 && op2.prec == 5 && decide (a.prec > 5) &&
      decide (b.prec > 5) && decide (c.prec > 5) && a.wf br && b.wf br && c.wf br
  | .notE a => decide (a.prec ≥ 4) && a.wf br
  | .andE l r => decide (l.prec ≥ 3) && decide (r.prec > 3) && l.wf br && r.wf br
  | .orE l r => decide (l.prec ≥ 2) && decide (r.prec > 2) && l.wf br && r.wf br
  | .ifE t c f => decide (t.prec > 1) && decide (c.prec > 1) && decide (f.prec ≥ 1) &&
      t.wf br && c.wf br && f.wf br
  | .comp elt x it cond => decide (elt.prec ≥ 1) && validName x && decide (it.prec > 1) &&
      elt.wf true && it.wf true && PE.wfCond cond
  | .nl _ e => br && !e.isNl && e.wf br
termination_by structural e => e
def PE.wfItems (br : Bool) : List PE → Bool
  | [] => true
  | e :: es => decide (e.prec ≥ 1) && e.wf br && PE.wfItems br es
termination_by structural es => es
def PE.wfArgs : List PE → Bool
  | [] => true
  | e :: es => (PE.kwOK e || (decide (e.prec ≥ 1) && e.wf true)) && PE.wfArgs es
termination_by structural es => es
def PE.kwOK : PE → Bool
  | .kw k v => validName k && decide (v.prec ≥ 1) && v.wf true
  | .nl _ e => !e.isNl && PE.kwOK e
  | _ => false
termination_by structural e => e
def PE.wfKVs : List PE → Bool
  | [] => true
  | e :: es => PE.kvOK e && PE.wfKVs es
termination_by structural es => es
def PE.kvOK : PE → Bool
  | .kv k v => decide (k.prec ≥ 1) && k.wf true && decide (v.prec ≥ 1) && v.wf true
  | .nl _ e => !e.isNl && PE.kvOK e
  | _ => false
termination_by structural e => e
def PE.wfCond : Option PE → Bool
  | .none => true
  | .some c => decide (c.prec > 1) && c.wf true
termination_by structural c => c
end

/-- Assignment targets. -/
def PE.isTarget : PE → Bool
  | .name s => validName s
  | .attr _ _ => true
  | .sub _ _ => true
  | .tuple es => es.all fun e => match e with
    | .name s => validName s
    | .attr _ _ => true
    | .sub _ _ => true
    | _ => false
  | _ => false

inductive PS where
  | assign (tgts : List PE) (rhs : PE)
  | aug (t : PE) (op : Op) (rhs : PE)
  | expr (e : PE)
  | ret (e : Option PE)
  | raise (e : PE)
  | pass
  | brk
  | assert (e : PE)
  deriving Repr, Inhabited

def PS.render : PS → Doc
  | .assign tgts rhs => Doc.cats (tgts.map (fun t => Doc.cat t.render [" = "]) ++ [rhs.render])
  | .aug t op rhs => Doc.cats [t.render, [" " ++ op.sym ++ "= "], rhs.render]
  | .expr e => e.render
  | .ret .none => ["return"]
  | .ret (.some e) => Doc.cat ["return "] e.render
  | .raise e => Doc.cat ["raise "] e.render
  | .pass => ["pass"]
  | .brk => ["break"]
  | .assert e => Doc.cat ["assert "] e.render

def PS.wf : PS → Bool
  | .assign tgts rhs => !tgts.isEmpty && tgts.all (fun t => t.isTarget && t.wf false) && rhs.wf false
  | .aug t op rhs => (op == .add || op == .sub) && (match t with | .name _ => true | .attr _ _ => true | _ => false) &&
      t.wf false && decide (rhs.prec ≥ 1) && rhs.wf false
  | .expr e => decide (e.prec ≥ 1) && e.wf false
  | .ret .none => true
  | .ret (.some e) => e.wf false
  | .raise e => decide (e.prec ≥ 1) && e.wf false
  | .pass | .brk => true
  | .assert e => decide (e.prec ≥ 1) && e.wf false

structure Param where
  name : String
  default : Option PE
  deriving Repr, Inhabited

def Param.render (p : Param) : String :=
  match p.default with
  | .none => p.name
  | .some d => p.name ++ "=" ++ String.join d.render

mutual
inductive PL where
  | simple (ss : List PS) (comment : Option String)
  | comment (text : String)
  | blank
  | ifS (c : PE) (t : Blk) (els : Option Blk)
  | forS (t : PE) (it : PE) (body : Blk)
  | whileS (c : PE) (body : Blk)
  | tryS (body : List PL) (cls : String) (x : String) (handler : List PL)
  | defS (name : String) (params : List Param) (body : List PL)
  | classS (name : String) (base : Option String) (body : List PL)
  /-- Verbatim lines (module docstring, imports): no executable content. -/
  | raw (lines : List String)
inductive Blk where
  | inline (ss : List PS) (comment : Option String)
  | block (ls : List PL)
end

instance : Inhabited PL := ⟨.blank⟩

def renderSimple (ss : List PS) : Doc :=
  match ss with
  | [] => [""]
  | s :: rest => rest.foldl (fun d t => Doc.cats [d, ["; "], t.render]) s.render

def commentText : Option String → String
  | .none => ""
  | .some t => "  # " ++ t

mutual
def PL.render (ind : Nat) : PL → List String
  | .simple ss c => Doc.cats [[spaces ind], renderSimple ss, [commentText c]]
  | .comment t => [spaces ind ++ "# " ++ t]
  | .blank => [""]
  | .ifS c t els => Blk.render ind (Doc.cats [[spaces ind ++ "if "], c.render, [":"]]) t ++
      (match els with
       | .none => []
       | .some b => Blk.render ind [spaces ind ++ "else:"] b)
  | .forS t it body => Blk.render ind (Doc.cats [[spaces ind ++ "for "], t.render, [" in "], it.render, [":"]]) body
  | .whileS c body => Blk.render ind (Doc.cats [[spaces ind ++ "while "], c.render, [":"]]) body
  | .tryS body cls x handler => (spaces ind ++ "try:") :: PL.renderB (ind + 4) body ++
      (spaces ind ++ "except " ++ cls ++ " as " ++ x ++ ":") :: PL.renderB (ind + 4) handler
  | .defS name params body =>
      (spaces ind ++ "def " ++ name ++ "(" ++ ", ".intercalate (params.map Param.render) ++ "):") ::
        PL.renderB (ind + 4) body
  | .classS name base body =>
      (spaces ind ++ "class " ++ name ++ (match base with | .none => "" | .some b => "(" ++ b ++ ")") ++ ":") ::
        PL.renderB (ind + 4) body
  | .raw lines => lines
def Blk.render (ind : Nat) (header : Doc) : Blk → List String
  | .inline ss c => Doc.cats [header, [" "], renderSimple ss, [commentText c]]
  | .block ls => header ++ PL.renderB (ind + 4) ls
def PL.renderB (ind : Nat) : List PL → List String
  | [] => []
  | l :: ls => PL.render ind l ++ PL.renderB ind ls
end

def isKeywordFree (t : String) : Bool := !sEmpty t && validStr t

mutual
def PL.wf : PL → Bool
  | .simple ss c => !ss.isEmpty && ss.all PS.wf && (match c with | .none => true | .some t => isKeywordFree t)
  | .comment t => isKeywordFree t
  | .blank => true
  | .ifS c t els => decide (c.prec ≥ 1) && c.wf false && Blk.wf t &&
      (match els with | .none => true | .some b => Blk.wf b)
  | .forS t it body => t.isTarget && t.wf false && decide (it.prec ≥ 1) && it.wf false && Blk.wf body
  | .whileS c body => decide (c.prec ≥ 1) && c.wf false && Blk.wf body
  | .tryS body cls x handler => PL.wfBody body && validName cls && validName x && PL.wfBody handler
  | .defS name params body => validName name && params.all (fun p => validName p.name &&
      (match p.default with | .none => true | .some d => d.prec == 20 && d.wf false)) && PL.wfBody body
  | .classS name base body => validName name && (match base with | .none => true | .some b => validName b) &&
      PL.wfBody body
  | .raw _ => false
def Blk.wf : Blk → Bool
  | .inline ss c => !ss.isEmpty && ss.all PS.wf && (match c with | .none => true | .some t => isKeywordFree t)
  | .block ls => PL.wfBody ls
/-- A suite: non-empty, starting with a statement (not a blank line), all items well formed. -/
def PL.wfBody : List PL → Bool
  | [] => false
  | l :: ls => (match l with | .blank => false | _ => true) && PL.wf l && PL.wfB ls
def PL.wfB : List PL → Bool
  | [] => true
  | l :: ls => PL.wf l && PL.wfB ls
end

/-! ## Whole-file certificates -/

inductive Seg where
  /-- Module docstring, imports and blank lines (no executable content). -/
  | header (lines : List String)
  /-- Extracted top-level items. -/
  | code (items : List PL)
  /-- An unextracted top-level function occupying `len` lines. -/
  | opaqueDef (name : String) (len : Nat)
  deriving Inhabited

def isIndentedOrBlank (l : String) : Bool := sEmpty l || sStarts l " "

def headerLineOK (l : String) : Bool :=
  sEmpty l || sStarts l "from " || sStarts l "import " || sStarts l "\"\"\"" ||
    sAll l (fun ch => ch != '"') || sEnds l "\"\"\""

/-- Check that the segments cover `file` exactly. -/
def checkSegs : List String → List Seg → Bool
  | [], [] => true
  | _, [] => false
  | file, .header ls :: rest => (file.take ls.length == ls) && ls.all headerLineOK && checkSegs (file.drop ls.length) rest
  | file, .code items :: rest =>
      let r := PL.renderB 0 items
      (file.take r.length == r) && PL.wfB items && checkSegs (file.drop r.length) rest
  | file, .opaqueDef name len :: rest =>
      len ≥ 1 && (match file.head? with | .some l => sStarts l ("def " ++ name ++ "(") | .none => false) &&
        ((file.take len).drop 1).all isIndentedOrBlank &&
        (match (file.drop len).head? with | .some l => !sStarts l " " | .none => true) &&
        checkSegs (file.drop len) rest

/-! ## Lowering -/

def Op.core : Op → Option BinOp
  | .add => some .add | .sub => some .sub | .eq => some .eq | .ne => some .ne
  | .lt => some .lt | .le => some .le | .gt => some .gt | .ge => some .ge
  | _ => none

def Op.augCore : Op → Option BinOp
  | .add => some .add
  | .sub => some .sub
  | _ => none

mutual
def PE.lower : PE → Option E
  | .name s => some (.var s)
  | .num n => some (.lit (.int n))
  | .str s => some (.lit (.str s))
  | .tru => some (.lit (.bool true))
  | .fls => some (.lit (.bool false))
  | .none => some (.lit .none)
  | .paren e => e.lower
  | .tuple es => (PE.lowerL es).map .tup
  | .list es => (PE.lowerL es).map .listD
  | .dict items => (PE.lowerKVs items).map .dictD
  | .kv _ _ => Option.none
  | .kw _ _ => Option.none
  | .set es => (PE.lowerL es).map .setD
  | .attr e f => (e.lower).map (.attr · f)
  | .sub a i => do return .sub (← a.lower) (← i.lower)
  | .slice a i => do return .sliceFrom (← a.lower) (← i.lower)
  | .call (.name f) args => (PE.lowerL args).map (.call f)
  | .call (.attr (.name "dict") "fromkeys") args => (PE.lowerL args).map (.call "dict.fromkeys")
  | .call (.attr o m) args =>
      match PE.lowerKws args with
      | .some (ks, vs) => if ks.isEmpty then (o.lower).map (.mcall · m []) else do return .kwcall (← o.lower) m ks vs
      | .none => do return .mcall (← o.lower) m (← PE.lowerL args)
  | .call _ _ => Option.none
  | .bin .is l .none => (l.lower).map (.isNone · false)
  | .bin .isNot l .none => (l.lower).map (.isNone · true)
  | .bin .is (.call (.name "type") [x]) (.name ty) => (x.lower).map (.typeIs · ty false)
  | .bin .isNot (.call (.name "type") [x]) (.name ty) => (x.lower).map (.typeIs · ty true)
  | .bin .inn l r => do return .mem (← l.lower) (← r.lower) false
  | .bin .notIn l r => do return .mem (← l.lower) (← r.lower) true
  | .bin op l r => do return .bin (← op.core) (← l.lower) (← r.lower)
  | .binT op l r => do return .bin (← op.augCore) (← l.lower) (← r.lower)
  | .negNum n => some (.lit (.int (-(n : Int))))
  | .chain op1 op2 a b c => do return .cmp2 (← op1.core) (← op2.core) (← a.lower) (← b.lower) (← c.lower)
  | .notE a => (a.lower).map .not
  | .andE l r => do return .and (← l.lower) (← r.lower)
  | .orE l r => do return .or (← l.lower) (← r.lower)
  | .ifE t c f => do return .cond (← c.lower) (← t.lower) (← f.lower)
  | .comp elt x it cond => do return .comp (← elt.lower) x (← it.lower) (← PE.lowerCond cond)
  | .nl _ e => e.lower
def PE.lowerL : List PE → Option (List E)
  | [] => some []
  | e :: es => do return (← e.lower) :: (← PE.lowerL es)
def PE.lowerKVs : List PE → Option (List E)
  | [] => some []
  | e :: es => do let (k, v) ← PE.lowerKV e; return k :: v :: (← PE.lowerKVs es)
def PE.lowerKV : PE → Option (E × E)
  | .kv k v => do return (← k.lower, ← v.lower)
  | .nl _ e => PE.lowerKV e
  | _ => Option.none
/-- All-keyword argument lists (`none` if some argument is positional). -/
def PE.lowerKws : List PE → Option (List String × List E)
  | [] => some ([], [])
  | e :: es => do
      let (k, v) ← PE.lowerKw e
      let (ks, vs) ← PE.lowerKws es
      return (k :: ks, v :: vs)
def PE.lowerKw : PE → Option (String × E)
  | .kw k v => (v.lower).map (k, ·)
  | .nl _ e => PE.lowerKw e
  | _ => Option.none
def PE.lowerCond : Option PE → Option (Option E)
  | .none => some Option.none
  | .some c => (c.lower).map some
end

def PE.toTgt1 : PE → Option Tgt
  | PE.name s => some (Tgt.name s)
  | PE.attr e f => (e.lower).map (Tgt.attr · f)
  | PE.sub a i => do return Tgt.sub (← a.lower) (← i.lower)
  | _ => Option.none

def PE.toTgt : PE → Option Tgt
  | PE.tuple es => (es.mapM PE.toTgt1).map Tgt.tup
  | e => e.toTgt1

def PS.lower : PS → Option S
  | .assign tgts rhs => do return .assign (← tgts.mapM PE.toTgt) (← rhs.lower)
  | .aug t op rhs => do return .aug (← t.toTgt) (← op.augCore) (← rhs.lower)
  | .expr e => (e.lower).map .expr
  | .ret .none => some (.ret (.lit .none))
  | .ret (.some e) => (e.lower).map .ret
  | .raise e => (e.lower).map .raise
  | .pass => some .pass
  | .brk => some .brk
  | .assert e => (e.lower).map .assert

mutual
def PL.lower : PL → Option (List S)
  | .simple ss _ => ss.mapM PS.lower
  | .comment _ => some []
  | .blank => some []
  | .ifS c t els => do
      let f ← match els with
        | .none => some []
        | .some b => Blk.lower b
      return [.ifte (← c.lower) (← Blk.lower t) f]
  | .forS t it body => do return [.forIn (← t.toTgt) (← it.lower) (← Blk.lower body)]
  | .whileS c body => do return [.while (← c.lower) (← Blk.lower body)]
  | .tryS body cls x handler => do return [.try (← PL.lowerB body) cls x (← PL.lowerB handler)]
  | .defS .. => Option.none
  | .classS .. => Option.none
  | .raw _ => Option.none
def Blk.lower : Blk → Option (List S)
  | .inline ss _ => ss.mapM PS.lower
  | .block ls => PL.lowerB ls
def PL.lowerB : List PL → Option (List S)
  | [] => some []
  | l :: ls => do return (← PL.lower l) ++ (← PL.lowerB ls)
end

def lowerDef (qual : String) (params : List Param) (body : List PL) : Option (String × Fn) :=
  (PL.lowerB body).map fun b => (qual, ⟨params.map (·.name), b⟩)

/-- Methods of a class body (blank lines allowed between them). -/
def lowerMethods (cls : String) : List PL → Option (List (String × Fn) × List String)
  | [] => some ([], [])
  | .blank :: rest => lowerMethods cls rest
  | .defS m params body :: rest => do
      let f ← lowerDef (cls ++ "." ++ m) params body
      let (fs, ms) ← lowerMethods cls rest
      return (f :: fs, m :: ms)
  | _ => none

/-- Extraction result of a module: functions, classes, externs and the module-level statements. -/
structure Module where
  funs : List (String × Fn)
  classes : List ClassDef
  externs : List String
  init : List S
  deriving Repr, Inhabited

def Module.empty : Module := ⟨[], [], [], []⟩

def Module.append (a b : Module) : Module :=
  ⟨a.funs ++ b.funs, a.classes ++ b.classes, a.externs ++ b.externs, a.init ++ b.init⟩

def lowerItem : PL → Option Module
  | .blank => some .empty
  | .comment _ => some .empty
  | .simple ss c => (PL.lower (.simple ss c)).map fun init => ⟨[], [], [], init⟩
  | .defS name params body => (lowerDef name params body).map fun f => ⟨[f], [], [], []⟩
  | .classS name (.some "Exception") [.simple [.pass] .none] => some ⟨[], [⟨name, [], true⟩], [], []⟩
  | .classS name .none body => (lowerMethods name body).map fun (fs, ms) => ⟨fs, [⟨name, ms, false⟩], [], []⟩
  | _ => none

def lowerItems : List PL → Option Module
  | [] => some .empty
  | l :: ls => do return (← lowerItem l).append (← lowerItems ls)

def lowerSegs : List Seg → Option Module
  | [] => some .empty
  | .header _ :: rest => lowerSegs rest
  | .code items :: rest => do return (← lowerItems items).append (← lowerSegs rest)
  | .opaqueDef name _ :: rest => (lowerSegs rest).map fun m => Module.append ⟨[], [], [name], []⟩ m

def Module.prog (m : Module) : Prog := ⟨m.funs, m.classes, m.externs⟩

end PCSCR.Py
