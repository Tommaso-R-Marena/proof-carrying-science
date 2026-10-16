import PCSConditionalRuntime.PyFront

/-!
# ECMAScript front end for the heap semantics: concrete syntax, exact rendering, precedence
# discipline and whole-file certificates

* `JE` / `JS` / `JItem` — a *concrete* syntax tree for the ECMAScript fragment of the current
  website module `public/conditional-core.mjs` (minified style, no optional spaces):
  `const` / `let` declarations with array patterns, `if`/`else` with statement or block bodies,
  `for…of`, `while`, `switch` with `default`, `try`/`catch`, `throw`, postfix `++`,
  destructuring assignment, member / index / call / `new`, arrow functions (expression and
  block bodies), object literals with shorthand properties, spread, `await`, classes with
  methods, `async` functions with a defaulted object-pattern parameter, and explicit line
  breaks (`JS.nl`) at the positions the source has them.
* `JItem.renderB` reproduces the source text byte for byte (as a list of lines).
* `JE.wf` / `JS.wf` — precedence / associativity discipline (ECMAScript levels), identifier and
  string-literal syntax: under it the rendered text has exactly the parse given by the tree.
* `JSeg` / `checkJSegs` — a **whole-file certificate**: every line belongs to exactly one segment,
  which is either a header line (comment / `import`), extracted code (rendered byte for byte)
  or an unextracted exported function / constant (`opaque`), whose first line starts with
  `export function NAME(`, `export async function NAME(` or `export const NAME=`, whose further
  lines are indented and whose last line closes it (`}` at column 0, or the one-line form ends
  with `}` / `;`).
-/

namespace PCSCR.Js

open PCSCR PCSCR.Py

inductive JOp where
  | add | sub | seq | sne | lt | gt | le | ge | and | or | inst
  deriving DecidableEq, Repr

def JOp.sym : JOp → String
  | .add => "+" | .sub => "-" | .seq => "===" | .sne => "!==" | .lt => "<" | .gt => ">"
  | .le => "<=" | .ge => ">=" | .and => "&&" | .or => "||" | .inst => " instanceof "

/-- ECMAScript precedence levels (higher binds tighter). -/
def JOp.prec : JOp → Nat
  | .add | .sub => 11 | .lt | .gt | .le | .ge | .inst => 9 | .seq | .sne => 8 | .and => 4 | .or => 3

mutual
inductive JE where
  | name (s : String)
  | num (n : Nat)
  | str (s : String)
  | tru | fls | null
  | paren (e : JE)
  | arr (es : List JE)
  | obj (ps : List JP)
  | mem (a : JE) (k : String)
  | idx (a i : JE)
  | call (f : JE) (args : List JE)
  | new (c : String) (args : List JE)
  /-- `p=>body` -/
  | arrow1 (p : String) (body : JE)
  /-- `(p,q,…)=>body` -/
  | arrowP (ps : List String) (body : JE)
  /-- `p=>{…}` -/
  | arrowB (p : String) (body : List JS)
  | bin (op : JOp) (l r : JE)
  | not (a : JE)
  | neg (a : JE)
  | cond (c t f : JE)
  | spread (e : JE)
  | await (e : JE)
inductive JP where
  | kv (k : String) (v : JE)
  | short (k : String)
inductive JD where
  | name (x : String) (init : Option JE)
  | arrPat (xs : List String) (init : JE)
inductive JS where
  | expr (e : JE)
  | decl (kind : String) (ds : List JD)
  | assign (t e : JE)
  | incr (t : JE)
  | ret (e : Option JE)
  | brk
  | throw (e : JE)
  /-- `if(c)t` with optional `else` (preceded by an optional line break). -/
  | ifS (c : JE) (t : JS) (elseNl : Option Nat) (els : Option JS)
  | block (ss : List JS)
  | forOf (kind x : String) (it : JE) (body : JS)
  | while (c : JE) (body : JS)
  | tryCatch (body : List JS) (x : String) (handler : List JS)
  | switch (e : JE) (cases : List (String × List JS)) (dflt : List JS)
  /-- Line break followed by `ind` spaces. -/
  | nl (ind : Nat)
end

instance : Inhabited JE := ⟨.null⟩
instance : Inhabited JS := ⟨.brk⟩

def nlDoc (ind : Nat) : Doc := ["", spaces ind]

mutual
def JE.render : JE → Doc
  | .name s => [s]
  | .num n => [natStr n]
  | .str s => ["'" ++ s ++ "'"]
  | .tru => ["true"]
  | .fls => ["false"]
  | .null => ["null"]
  | .paren e => Doc.cats [["("], e.render, [")"]]
  | .arr es => Doc.cats [["["], JE.renderL es, ["]"]]
  | .obj ps => Doc.cats [["{"], JP.renderL ps, ["}"]]
  | .mem a k => Doc.cat a.render ["." ++ k]
  | .idx a i => Doc.cats [a.render, ["["], i.render, ["]"]]
  | .call f args => Doc.cats [f.render, ["("], JE.renderL args, [")"]]
  | .new c args => Doc.cats [["new " ++ c ++ "("], JE.renderL args, [")"]]
  | .arrow1 p b => Doc.cat [p ++ "=>"] b.render
  | .arrowP ps b => Doc.cat ["(" ++ ",".intercalate ps ++ ")=>"] b.render
  | .arrowB p ss => Doc.cats [[p ++ "=>{"], JS.renderL ss, ["}"]]
  | .bin op l r => Doc.cats [l.render, [op.sym], r.render]
  | .not a => Doc.cat ["!"] a.render
  | .neg a => Doc.cat ["-"] a.render
  | .cond c t f => Doc.cats [c.render, ["?"], t.render, [":"], f.render]
  | .spread e => Doc.cat ["..."] e.render
  | .await e => Doc.cat ["await "] e.render
def JE.renderL : List JE → Doc
  | [] => [""]
  | [e] => e.render
  | e :: es => Doc.cats [e.render, [","], JE.renderL es]
def JP.render : JP → Doc
  | .kv k v => Doc.cat [k ++ ":"] v.render
  | .short k => [k]
def JP.renderL : List JP → Doc
  | [] => [""]
  | [p] => p.render
  | p :: ps => Doc.cats [p.render, [","], JP.renderL ps]
def JD.render : JD → Doc
  | .name x none => [x]
  | .name x (some e) => Doc.cat [x ++ "="] e.render
  | .arrPat xs e => Doc.cat ["[" ++ ",".intercalate xs ++ "]="] e.render
def JD.renderL : List JD → Doc
  | [] => [""]
  | [d] => d.render
  | d :: ds => Doc.cats [d.render, [","], JD.renderL ds]
def JS.render : JS → Doc
  | .expr e => Doc.cat e.render [";"]
  | .decl k ds => Doc.cats [[k ++ " "], JD.renderL ds, [";"]]
  | .assign t e => Doc.cats [t.render, ["="], e.render, [";"]]
  | .incr t => Doc.cat t.render ["++;"]
  | .ret none => ["return;"]
  | .ret (some e) => Doc.cats [["return "], e.render, [";"]]
  | .brk => ["break;"]
  | .throw e => Doc.cats [["throw "], e.render, [";"]]
  | .ifS c t enl els => Doc.cats [["if("], c.render, [")"], t.render, JS.renderElse enl els]
  | .block ss => Doc.cats [["{"], JS.renderL ss, ["}"]]
  | .forOf k x it b => Doc.cats [["for(" ++ k ++ " " ++ x ++ " of "], it.render, [")"], b.render]
  | .while c b => Doc.cats [["while("], c.render, [")"], b.render]
  | .tryCatch b x hd => Doc.cats [["try{"], JS.renderL b, ["}catch(" ++ x ++ "){"], JS.renderL hd, ["}"]]
  | .switch e cs d => Doc.cats [["switch("], e.render, ["){"], JS.renderCases cs, ["default:"], JS.renderL d, ["}"]]
  | .nl ind => nlDoc ind
def JS.renderElse : Option Nat → Option JS → Doc
  | _, none => [""]
  | none, some (.block ss) => Doc.cats [["else{"], JS.renderL ss, ["}"]]
  | none, some e => Doc.cat ["else "] e.render
  | some ind, some (.block ss) => Doc.cats [nlDoc ind, ["else{"], JS.renderL ss, ["}"]]
  | some ind, some e => Doc.cats [nlDoc ind, ["else "], e.render]
def JS.renderL : List JS → Doc
  | [] => [""]
  | s :: ss => Doc.cat s.render (JS.renderL ss)
def JS.renderCases : List (String × List JS) → Doc
  | [] => [""]
  | (l, ss) :: cs => Doc.cats [["case '" ++ l ++ "':"], JS.renderL ss, JS.renderCases cs]
end

/-! ## Precedence / syntax discipline -/

/-- Grammar level (`20` = primary / member / call). -/
def JE.prec : JE → Nat
  | .arrow1 .. | .arrowP .. | .arrowB .. => 2
  | .cond .. => 2
  | .bin op _ _ => op.prec
  | .not _ | .neg _ | .await _ => 15
  | .spread _ => 0
  | _ => 20

def reservedWords : List String :=
  ["break", "case", "catch", "class", "const", "continue", "default", "do", "else", "export",
   "extends", "false", "for", "function", "if", "import", "in", "instanceof", "let", "new",
   "null", "of", "return", "switch", "throw", "true", "try", "typeof", "var", "void", "while",
   "await", "async", "yield", "delete"]

def cIsIdStart (ch : Char) : Bool := cIsAlpha ch || ch == '_' || ch == '$'
def cIsIdPart (ch : Char) : Bool := cIsIdStart ch || cIsDigit ch

def validId (s : String) : Bool :=
  match s.toList with
  | [] => false
  | c :: cs => cIsIdStart c && cs.all cIsIdPart && !reservedWords.contains s

def validJStr (s : String) : Bool := sAll s (fun ch => ch != '\'' && ch != '\\' && ch != '\n' && ch != '\r')

/-- An expression that may start an expression statement (no `{`, no `function`/arrow). -/
def JE.stmtStart : JE → Bool
  | .obj _ | .arrow1 .. | .arrowP .. | .arrowB .. => false
  | .bin _ l _ => l.stmtStart
  | .cond c _ _ => c.stmtStart
  | .mem a _ | .idx a _ | .call a _ => a.stmtStart
  | _ => true

/-- A statement body of `if`/`for`/`while`: no declaration, no bare line break. -/
def JS.bodyOK : JS → Bool
  | .decl .. | .nl _ => false
  | _ => true

mutual
def JE.wf : JE → Bool
  | .name s => validId s
  | .num _ => true
  | .str s => validJStr s
  | .tru | .fls | .null => true
  | .paren e => e.wf
  | .arr es => JE.wfL es
  | .obj ps => JP.wfL ps
  | .mem a k => a.prec == 20 && a.wf && validId k
  | .idx a i => a.prec == 20 && a.wf && i.prec ≥ 2 && i.wf
  | .call f args => f.prec == 20 && f.wf && JE.wfL args
  | .new c args => validId c && JE.wfL args
  | .arrow1 p b => validId p && b.prec ≥ 2 && b.stmtStart && b.wf
  | .arrowP ps b => ps.all validId && b.prec ≥ 2 && b.stmtStart && b.wf
  | .arrowB p ss => validId p && JS.wfL ss
  | .bin op l r => l.prec ≥ op.prec && r.prec > op.prec && l.wf && r.wf
  | .not a => a.prec ≥ 15 && a.wf
  | .neg a => (a matches .num _) && a.wf
  | .cond c t f => c.prec ≥ 3 && t.prec ≥ 2 && f.prec ≥ 2 && c.wf && t.wf && f.wf
  | .spread _ => false
  | .await e => e.prec ≥ 15 && e.wf
/-- Array elements / call arguments: assignment expressions or spread elements. -/
def JE.wfL : List JE → Bool
  | [] => true
  | .spread e :: es => e.prec ≥ 2 && e.wf && JE.wfL es
  | e :: es => e.prec ≥ 2 && e.wf && JE.wfL es
def JP.wfL : List JP → Bool
  | [] => true
  | .kv k v :: ps => validId k && v.prec ≥ 2 && v.wf && JP.wfL ps
  | .short k :: ps => validId k && JP.wfL ps
def JD.wfL : List JD → Bool
  | [] => false
  | [d] => JD.wf1 d
  | d :: ds => JD.wf1 d && JD.wfL ds
def JD.wf1 : JD → Bool
  | .name x none => validId x
  | .name x (some e) => validId x && e.prec ≥ 2 && e.wf
  | .arrPat xs e => xs.all validId && e.prec ≥ 2 && e.wf
/-- Assignment targets: names, members, indexing, array patterns of names. -/
def JE.isTarget : JE → Bool
  | .name _ | .mem .. | .idx .. => true
  | .arr es => es.all (fun e => e matches .name _)
  | _ => false
def JS.wf : JS → Bool
  | .expr e => e.stmtStart && e.wf
  | .decl k ds => (k == "const" || k == "let") && JD.wfL ds
  | .assign t e => t.isTarget && t.wf && e.prec ≥ 2 && e.wf
  | .incr t => (t matches .name _ || t matches .mem ..) && t.wf
  | .ret none => true
  | .ret (some e) => e.wf
  | .brk => true
  | .throw e => e.wf
  | .ifS c t _ els => c.wf && (JS.bodyOK t && JS.wf t) && JS.wfElse els
  | .block ss => JS.wfL ss
  | .forOf k x it b => (k == "const") && validId x && it.prec ≥ 2 && it.wf && (JS.bodyOK b && JS.wf b)
  | .while c b => c.wf && (JS.bodyOK b && JS.wf b)
  | .tryCatch b x hd => JS.wfL b && validId x && JS.wfL hd
  | .switch e cs d => e.wf && JS.wfCases cs && JS.wfL d
  | .nl _ => true
def JS.wfElse : Option JS → Bool
  | none => true
  | some s => JS.bodyOK s && JS.wf s
def JS.wfL : List JS → Bool
  | [] => true
  | s :: ss => JS.wf s && JS.wfL ss
def JS.wfCases : List (String × List JS) → Bool
  | [] => true
  | (l, ss) :: cs => validJStr l && JS.wfL ss && JS.wfCases cs
end

/-! ## Top-level items -/

inductive JParam where
  | plain (x : String)
  /-- `{k=dflt}={}` -/
  | objDefault (k : String) (dflt : JE)

def JParam.render : JParam → Doc
  | .plain x => [x]
  | .objDefault k d => Doc.cats [["{" ++ k ++ "="], d.render, ["}={}"]]

def JParam.renderL : List JParam → Doc
  | [] => [""]
  | [p] => p.render
  | p :: ps => Doc.cats [p.render, [","], JParam.renderL ps]

def JParam.wf : JParam → Bool
  | .plain x => validId x
  | .objDefault k d => validId k && d.prec ≥ 2 && d.wf

structure JMethod where
  name : String
  params : List String
  body : List JS

def JMethod.render (m : JMethod) : Doc :=
  Doc.cats [[m.name ++ "(" ++ ",".intercalate m.params ++ "){"], JS.renderL m.body, ["}"]]

def JMethod.wf (m : JMethod) : Bool :=
  (validId m.name || m.name == "constructor") && m.params.all validId && JS.wfL m.body

inductive JItem where
  /-- A top-level statement, optionally exported (`export const …;`). -/
  | stmt (exp : Bool) (s : JS)
  | func (exp async : Bool) (name : String) (params : List JParam) (body : List JS)
  /-- `class C extends B{` members, each on a new line indented by one space, `}`. -/
  | cls (name : String) (ext : Option String) (members : List JMethod)

def JItem.render : JItem → Doc
  | .stmt e s => Doc.cat [if e then "export " else ""] s.render
  | .func e a n ps b => Doc.cats [[(if e then "export " else "") ++ (if a then "async " else "") ++ "function " ++ n ++ "("],
      JParam.renderL ps, ["){"], JS.renderL b, ["}"]]
  | .cls n ext ms => Doc.cats [["class " ++ n ++ (match ext with | some b => " extends " ++ b | none => "") ++ "{"],
      Doc.cats (ms.map fun m => Doc.cat (nlDoc 1) m.render), if ms.isEmpty then ["}"] else ["", "}"]]

def JItem.wf : JItem → Bool
  | .stmt _ s => (s matches .decl ..) && JS.wf s
  | .func _ _ n ps b => validId n && ps.all JParam.wf && JS.wfL b
  | .cls n ext ms => validId n && (match ext with | some b => validId b | none => true) && ms.all JMethod.wf

/-- Items, each starting on a new line. -/
def JItem.renderB : List JItem → List String
  | [] => []
  | i :: is => i.render ++ JItem.renderB is

/-! ## Whole-file certificates -/

inductive JSeg where
  /-- Comment lines. -/
  | header (lines : List String)
  /-- `import {a,b,…} from 'src';` (the imported names become externs). -/
  | imports (names : List String) (src : String)
  | code (items : List JItem)
  /-- An unextracted exported function or constant occupying `len` lines. -/
  | opaque (name : String) (len : Nat)

def jHeaderLineOK (l : String) : Bool := sStarts l "//"

def importLine (names : List String) (src : String) : String :=
  "import {" ++ ",".intercalate names ++ "} from '" ++ src ++ "';"

def opaqueStart (name l : String) : Bool :=
  sStarts l ("export function " ++ name ++ "(") || sStarts l ("export async function " ++ name ++ "(") ||
    sStarts l ("export const " ++ name ++ "=")

def checkJSegs : List String → List JSeg → Bool
  | [], [] => true
  | [""], [] => true
  | _, [] => false
  | file, .header ls :: rest => (file.take ls.length == ls) && ls.all jHeaderLineOK && checkJSegs (file.drop ls.length) rest
  | file, .imports names src :: rest =>
      (file.head? == some (importLine names src)) && names.all validId && validJStr src &&
        checkJSegs (file.drop 1) rest
  | file, .code items :: rest =>
      let r := JItem.renderB items
      (file.take r.length == r) && items.all JItem.wf && checkJSegs (file.drop r.length) rest
  | file, .opaque name len :: rest =>
      len ≥ 1 && (match file.head? with | some l => opaqueStart name l | none => false) &&
        (if len = 1 then (match file.head? with | some l => sEnds l "}" || sEnds l ";" | none => false)
         else ((file.take (len - 1)).drop 1).all (fun l => sStarts l " ") &&
           (match (file.drop (len - 1)).head? with | some l => l == "}" | none => false)) &&
        checkJSegs (file.drop len) rest

end PCSCR.Js
