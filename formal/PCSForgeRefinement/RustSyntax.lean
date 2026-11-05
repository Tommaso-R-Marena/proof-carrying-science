import PCSForgeRefinement.Syntax
import PCSRuntimeRefinement.SourceText

/-!
# Source-bound Rust front end for the CertiForge interpreter

* `lexLine` — a deterministic Rust lexer for the token classes occurring in the bound source
  windows (identifiers/keywords, integer literals with suffixes, string literals, two-character
  punctuators `:: => -> >= <= == != << >> .. || &&`, single-character punctuation; spaces
  separate tokens).
* `RExpr` / `RPat` / `RFn` — a syntax tree for the supported Rust subset: paths, literals,
  calls, method calls (including a single `||` closure argument), `*`, `!`, binary operators, parentheses, `?`, struct
  literals (with field shorthand), `if`/`else`, `match` with guards, blocks with `let`, and
  tuples.  Anything else (loops, `mut`, `return`, macros, generics in expressions, …) has no
  syntax tree, so source using it cannot be certified.
* `RFn.toks` — exact token rendering.  `RExpr.wf` — Rust's precedence/associativity discipline
  (operators `- / << >> / & / ^ / | / comparisons`, comparisons non-associative, unary and
  postfix operands are atoms), so the token stream has the tree as its Rust parse.
* **Source binding**: `certir_width_source_bound`, `interp_bitvec_source_bound`,
  `interp_eval_binop_source_bound`, `interp_eval_cmp_bv_source_bound`,
  `interp_eval_expr_source_bound` — the lexed exact lines of the uploaded
  `crates/certir/src/lib.rs` (lines 20–35) and `crates/certir-interpreter/src/lib.rs`
  (lines 14–19, 39–66, 68–77, 79–137) are exactly the token renderings of the extracted trees.
-/

namespace PCSForgeRefinement.Rust

/-! ## Lexer -/

def isIdChar (c : Char) : Bool := c.isAlphanum || c == '_'

def twoCharPuncts : List (List Char) :=
  [[':', ':'], ['=', '>'], ['-', '>'], ['>', '='], ['<', '='], ['=', '='], ['!', '='],
   ['<', '<'], ['>', '>'], ['.', '.'], ['|', '|'], ['&', '&']]

/-- Lex a list of characters (fuel = number of characters; every step consumes one). -/
def lexChars : Nat → List Char → List String
  | 0, _ => []
  | _, [] => []
  | f + 1, c :: cs =>
    if c == ' ' then lexChars f cs
    else if isIdChar c then
      String.ofList (c :: cs.takeWhile isIdChar) :: lexChars f (cs.dropWhile isIdChar)
    else if c == '"' then
      String.ofList ('"' :: cs.takeWhile (· != '"') ++ ['"']) ::
        lexChars f ((cs.dropWhile (· != '"')).drop 1)
    else match cs with
      | d :: ds =>
        if twoCharPuncts.contains [c, d] then String.ofList [c, d] :: lexChars f ds
        else String.ofList [c] :: lexChars f cs
      | [] => [String.ofList [c]]

def lexLine (s : String) : List String := lexChars s.length s.toList

def lexLines (ls : List String) : List String := (ls.map lexLine).flatten

/-! ## Syntax -/

mutual
inductive RPat where
  | wild
  | bind (x : String)
  | litBool (b : Bool)
  | path (p : List String)
  | tupleS (p : List String) (args : RPats)
  | structS (p : List String) (fields : RFPats) (rest trailing : Bool)
  | tuple (ps : RPats)
inductive RPats where
  | nil
  | cons (p : RPat) (ps : RPats)
inductive RFPats where
  | nil
  | cons (name : String) (p : RPat) (ps : RFPats)
end

mutual
inductive RExpr where
  | var (x : String)
  | path (p : List String)
  | lit (n : Nat) (suffix : String)
  | str (s : String)
  | call (f : List String) (args : RExprs)
  | mcall (recv : RExpr) (m : String) (args : RExprs)
  | mcallCl (recv : RExpr) (m : String) (body : RExpr)
  | deref (e : RExpr)
  | bang (e : RExpr)
  | bin (op : String) (l r : RExpr)
  | paren (e : RExpr)
  | question (e : RExpr)
  | structE (p : List String) (fields : RFields) (trailing : Bool)
  | ite (c t e : RExpr)
  | mtch (s : RExpr) (arms : RArms)
  | block (lets : RLets) (tail : RExpr)
  | tuple (es : RExprs)
inductive RExprs where
  | nil
  | cons (e : RExpr) (es : RExprs)
inductive RFields where
  | nil
  | cons (name : String) (e : RExpr) (fs : RFields)
inductive RArms where
  | nil
  | cons (p : RPat) (guard : RGuard) (body : RExpr) (comma : Bool) (arms : RArms)
inductive RGuard where
  | none
  | some (g : RExpr)
inductive RLets where
  | nil
  | cons (p : RPat) (e : RExpr) (ls : RLets)
end

/-- A function item: optional `pub`, path (`[Type, name]` for an inherent method/associated
function), parameters with their type tokens (empty for `self`), return-type tokens, body. -/
structure RFn where
  isPub : Bool
  path : List String
  params : List (String × List String)
  ret : List String
  body : RExpr

/-! ## Token rendering -/

def pathToks : List String → List String
  | [] => []
  | [x] => [x]
  | x :: xs => x :: "::" :: pathToks xs

/-- Decimal digits (structural, kernel-reducible). -/
def natDigits : Nat → Nat → List Char
  | 0, _ => []
  | fuel + 1, n =>
    if n < 10 then [Char.ofNat (48 + n)] else natDigits fuel (n / 10) ++ [Char.ofNat (48 + n % 10)]

def natStr (n : Nat) : String := String.ofList (natDigits (n + 1) n)

mutual
def RPat.toks : RPat → List String
  | .wild => ["_"]
  | .bind x => [x]
  | .litBool b => [if b then "true" else "false"]
  | .path p => pathToks p
  | .tupleS p args => pathToks p ++ ["("] ++ RPats.toks args ++ [")"]
  | .structS p fs rest tr =>
    pathToks p ++ ["{"] ++ RFPats.toks fs ++ (if rest then [",", ".."] else []) ++
      (if tr then [","] else []) ++ ["}"]
  | .tuple ps => ["("] ++ RPats.toks ps ++ [")"]
def RPats.toks : RPats → List String
  | .nil => []
  | .cons p .nil => RPat.toks p
  | .cons p ps => RPat.toks p ++ [","] ++ RPats.toks ps
def RFPats.toks : RFPats → List String
  | .nil => []
  | .cons n p ps =>
    (match p with
      | .bind x => if x == n then [n] else [n, ":", x]
      | _ => [n, ":"] ++ RPat.toks p) ++
    (match ps with
      | .nil => []
      | _ => [","] ++ RFPats.toks ps)
end

mutual
def RExpr.toks : RExpr → List String
  | .var x => [x]
  | .path p => pathToks p
  | .lit n suf => [natStr n ++ suf]
  | .str s => ["\"" ++ s ++ "\""]
  | .call f args => pathToks f ++ ["("] ++ RExprs.toks args ++ [")"]
  | .mcall r m args => RExpr.toks r ++ [".", m, "("] ++ RExprs.toks args ++ [")"]
  | .mcallCl r m b => RExpr.toks r ++ [".", m, "(", "||"] ++ RExpr.toks b ++ [")"]
  | .deref e => ["*"] ++ RExpr.toks e
  | .bang e => ["!"] ++ RExpr.toks e
  | .bin op l r => RExpr.toks l ++ [op] ++ RExpr.toks r
  | .paren e => ["("] ++ RExpr.toks e ++ [")"]
  | .question e => RExpr.toks e ++ ["?"]
  | .structE p fs tr => pathToks p ++ ["{"] ++ RFields.toks fs ++ (if tr then [","] else []) ++ ["}"]
  | .ite c t e => ["if"] ++ RExpr.toks c ++ RExpr.toks t ++ ["else"] ++ RExpr.toks e
  | .mtch s arms => ["match"] ++ RExpr.toks s ++ ["{"] ++ RArms.toks arms ++ ["}"]
  | .block ls tl => ["{"] ++ RLets.toks ls ++ RExpr.toks tl ++ ["}"]
  | .tuple es => ["("] ++ RExprs.toks es ++ [")"]
def RExprs.toks : RExprs → List String
  | .nil => []
  | .cons e .nil => RExpr.toks e
  | .cons e es => RExpr.toks e ++ [","] ++ RExprs.toks es
def RFields.toks : RFields → List String
  | .nil => []
  | .cons n e fs =>
    (match e with
      | .var x => if x == n then [n] else [n, ":", x]
      | _ => [n, ":"] ++ RExpr.toks e) ++
    (match fs with
      | .nil => []
      | _ => [","] ++ RFields.toks fs)
def RArms.toks : RArms → List String
  | .nil => []
  | .cons p g b comma rest =>
    RPat.toks p ++ RGuard.toks g ++ ["=>"] ++ RExpr.toks b ++ (if comma then [","] else []) ++
      RArms.toks rest
def RGuard.toks : RGuard → List String
  | .none => []
  | .some g => ["if"] ++ RExpr.toks g
def RLets.toks : RLets → List String
  | .nil => []
  | .cons p e ls => ["let"] ++ RPat.toks p ++ ["="] ++ RExpr.toks e ++ [";"] ++ RLets.toks ls
end

def paramToks : List (String × List String) → List String
  | [] => []
  | [(x, ty)] => if ty.isEmpty then [x] else x :: ":" :: ty
  | (x, ty) :: ps => (if ty.isEmpty then [x] else x :: ":" :: ty) ++ [","] ++ paramToks ps

def RFn.toks (f : RFn) : List String :=
  (if f.isPub then ["pub"] else []) ++ ["fn", f.path.getLast?.getD "", "("] ++ paramToks f.params ++
    [")", "->"] ++ f.ret ++ f.body.toks

/-! ## Precedence discipline -/

def binPrec : String → Nat
  | "*" => 11
  | "+" | "-" => 10
  | "<<" | ">>" => 9
  | "&" => 8
  | "^" => 7
  | "|" => 6
  | "==" | "!=" | "<" | "<=" | ">" | ">=" => 5
  | _ => 0

def isCmp (op : String) : Bool := binPrec op == 5

/-- Operand of a binary operator: what binds at least as tightly as `prec` (`left` allows equal
precedence for non-comparison operators, i.e. left associativity). -/
def operandOK (prec : Nat) (left : Bool) : RExpr → Bool
  | .bin op _ _ => binPrec op > prec || (left && binPrec op == prec && prec != 5)
  | .ite _ _ _ | .mtch _ _ | .block _ _ => false
  | _ => true

/-- Operand of a prefix/postfix operator or method receiver: no unparenthesised binary,
closure or block-like expression (and, for postfix, no prefix expression). -/
def atomOK (isPostfix : Bool) : RExpr → Bool
  | .bin _ _ _ | .ite _ _ _ | .mtch _ _ => false
  | .deref _ | .bang _ => !isPostfix
  | _ => true

def isBlock : RExpr → Bool
  | .block _ _ => true
  | _ => false

mutual
def RExpr.wf : RExpr → Bool
  | .var _ | .path _ | .lit _ _ | .str _ => true
  | .call _ args => RExprs.wf args
  | .mcall r _ args => atomOK true r && RExpr.wf r && RExprs.wf args
  | .mcallCl r _ b => atomOK true r && RExpr.wf r && RExpr.wf b
  | .deref e | .bang e => atomOK false e && RExpr.wf e
  | .bin op l r => binPrec op != 0 && operandOK (binPrec op) true l && operandOK (binPrec op) false r &&
      RExpr.wf l && RExpr.wf r
  | .paren e => RExpr.wf e
  | .question e => atomOK true e && RExpr.wf e
  | .structE _ fs _ => RFields.wf fs
  | .ite c t e => !(c matches .structE ..) && isBlock t && isBlock e &&
      RExpr.wf c && RExpr.wf t && RExpr.wf e
  | .mtch s arms => !(s matches .structE ..) && RExpr.wf s && RArms.wf arms
  | .block ls tl => RLets.wf ls && RExpr.wf tl
  | .tuple es => RExprs.wf es
def RExprs.wf : RExprs → Bool
  | .nil => true
  | .cons e es => RExpr.wf e && RExprs.wf es
def RFields.wf : RFields → Bool
  | .nil => true
  | .cons _ e fs => RExpr.wf e && RFields.wf fs
def RArms.wf : RArms → Bool
  | .nil => true
  | .cons _ g b comma rest =>
    -- a block-bodied arm may omit the comma; every other arm except the last needs it
    (comma || isBlock b || rest matches .nil) && RGuard.wf g && RExpr.wf b && RArms.wf rest
def RGuard.wf : RGuard → Bool
  | .none => true
  | .some g => RExpr.wf g
def RLets.wf : RLets → Bool
  | .nil => true
  | .cons _ e ls => RExpr.wf e && RLets.wf ls
end

def RFn.wf (f : RFn) : Bool := isBlock f.body && f.body.wf

/-! ## The extracted trees -/

section
open RExpr

/-- List notation helpers for the mutual list types. -/
def es : List RExpr → RExprs
  | [] => .nil
  | e :: rest => .cons e (es rest)
def ps : List RPat → RPats
  | [] => .nil
  | p :: rest => .cons p (ps rest)
def fps : List (String × RPat) → RFPats
  | [] => .nil
  | (n, p) :: rest => .cons n p (fps rest)
def fs : List (String × RExpr) → RFields
  | [] => .nil
  | (n, e) :: rest => .cons n e (fs rest)
/-- Arms: pattern, optional guard, body, trailing comma. -/
def arms : List (RPat × Option RExpr × RExpr × Bool) → RArms
  | [] => .nil
  | (p, g, b, c) :: rest => .cons p (match g with | Option.none => .none | Option.some g => .some g) b c (arms rest)
def lets : List (RPat × RExpr) → RLets
  | [] => .nil
  | (p, e) :: rest => .cons p e (lets rest)

def v (x : String) : RExpr := .var x
def blk (e : RExpr) : RExpr := .block .nil e
def mc (r : RExpr) (m : String) (args : List RExpr := []) : RExpr := .mcall r m (es args)
def cl (f : List String) (args : List RExpr) : RExpr := .call f (es args)
def errRt (msg : String) : RExpr := cl ["Err"] [cl ["EvalError", "Runtime"] [mc (.str msg) "into"]]
def bvPat (w b : String) : RPat := .structS ["Value", "BitVec"] (fps [("width", .bind w), ("bits", .bind b)]) false false

/-- `Width::bits` (`crates/certir/src/lib.rs` lines 20–27). -/
def widthBitsFn : RFn where
  isPub := true
  path := ["Width", "bits"]
  params := [("self", [])]
  ret := ["u32"]
  body := blk (.mtch (v "self") (arms [
    (.path ["Width", "U8"], none, .lit 8 "", true),
    (.path ["Width", "U16"], none, .lit 16 "", true),
    (.path ["Width", "U32"], none, .lit 32 "", true),
    (.path ["Width", "U64"], none, .lit 64 "", true)]))

/-- `Width::mask` (lines 29–35). -/
def widthMaskFn : RFn where
  isPub := true
  path := ["Width", "mask"]
  params := [("self", [])]
  ret := ["u64"]
  body := blk (.ite (.bin "==" (mc (v "self") "bits") (.lit 64 ""))
    (blk (.path ["u64", "MAX"]))
    (blk (.bin "-" (.paren (.bin "<<" (.lit 1 "u64") (mc (v "self") "bits"))) (.lit 1 ""))))

/-- `Value::bitvec` (`crates/certir-interpreter/src/lib.rs` lines 14–19). -/
def valueBitvecFn : RFn where
  isPub := true
  path := ["Value", "bitvec"]
  params := [("width", ["Width"]), ("bits", ["u64"])]
  ret := ["Self"]
  body := blk (.structE ["Value", "BitVec"]
    (fs [("width", v "width"), ("bits", .bin "&" (v "bits") (mc (v "width") "mask"))]) true)

def shiftArm (op : String) (rop : String) : RPat × Option RExpr × RExpr × Bool :=
  (.path ["BinOp", op], none,
    blk (.ite (.bin ">=" (v "b") (cl ["u64", "from"] [mc (v "width") "bits"]))
      (blk (.lit 0 "")) (blk (.bin rop (v "a") (v "b")))), false)

/-- `eval_binop` (lines 39–66). -/
def evalBinopFn : RFn where
  isPub := false
  path := ["eval_binop"]
  params := [("op", ["BinOp"]), ("width", ["Width"]), ("a", ["u64"]), ("b", ["u64"])]
  ret := ["u64"]
  body := .block (lets [
      (.bind "mask", mc (v "width") "mask"),
      (.bind "a", .bin "&" (v "a") (v "mask")),
      (.bind "b", .bin "&" (v "b") (v "mask")),
      (.bind "r", .mtch (v "op") (arms [
        (.path ["BinOp", "Add"], none, mc (v "a") "wrapping_add" [v "b"], true),
        (.path ["BinOp", "Sub"], none, mc (v "a") "wrapping_sub" [v "b"], true),
        (.path ["BinOp", "Mul"], none, mc (v "a") "wrapping_mul" [v "b"], true),
        (.path ["BinOp", "And"], none, .bin "&" (v "a") (v "b"), true),
        (.path ["BinOp", "Or"], none, .bin "|" (v "a") (v "b"), true),
        (.path ["BinOp", "Xor"], none, .bin "^" (v "a") (v "b"), true),
        shiftArm "Shl" "<<",
        shiftArm "Lshr" ">>"]))])
    (.bin "&" (v "r") (v "mask"))

/-- `eval_cmp_bv` (lines 68–77). -/
def evalCmpBvFn : RFn where
  isPub := false
  path := ["eval_cmp_bv"]
  params := [("op", ["CmpOp"]), ("a", ["u64"]), ("b", ["u64"])]
  ret := ["bool"]
  body := blk (.mtch (v "op") (arms [
    (.path ["CmpOp", "Eq"], none, .bin "==" (v "a") (v "b"), true),
    (.path ["CmpOp", "Ne"], none, .bin "!=" (v "a") (v "b"), true),
    (.path ["CmpOp", "Ult"], none, .bin "<" (v "a") (v "b"), true),
    (.path ["CmpOp", "Ule"], none, .bin "<=" (v "a") (v "b"), true),
    (.path ["CmpOp", "Ugt"], none, .bin ">" (v "a") (v "b"), true),
    (.path ["CmpOp", "Uge"], none, .bin ">=" (v "a") (v "b"), true)]))

def recEval (x : String) : RExpr := cl ["eval_expr"] [v "store", v x]

/-- `match (op, v) { … }` of the `Expr::UnOp` arm. -/
def unopMatchE : RExpr :=
  .mtch (.tuple (es [v "op", v "v"])) (arms [
    (.tuple (ps [.path ["UnOp", "Not"], .tupleS ["Value", "Bool"] (ps [.bind "b"])]), none,
      cl ["Ok"] [cl ["Value", "Bool"] [.bang (v "b")]], true),
    (.tuple (ps [.path ["UnOp", "Not"], bvPat "width" "bits"]), none,
      cl ["Ok"] [cl ["Value", "bitvec"] [v "width", .bang (v "bits")]], true),
    (.tuple (ps [.path ["UnOp", "Neg"], bvPat "width" "bits"]), none,
      blk (cl ["Ok"] [cl ["Value", "bitvec"] [v "width", mc (v "bits") "wrapping_neg"]]), false),
    (.wild, none, errRt "bad unop", true)])

/-- `Ok(Value::bitvec(w1, eval_binop(*op, w1, a, b)))`. -/
def binopOkE : RExpr :=
  cl ["Ok"] [cl ["Value", "bitvec"] [v "w1", cl ["eval_binop"] [.deref (v "op"), v "w1", v "a", v "b"]]]

/-- `match (l, r) { … }` of the `Expr::BinOp` arm. -/
def binopMatchE : RExpr :=
  .mtch (.tuple (es [v "l", v "r"])) (arms [
    (.tuple (ps [bvPat "w1" "a", bvPat "w2" "b"]), some (.bin "==" (v "w1") (v "w2")), blk binopOkE, false),
    (.wild, none, errRt "bad binop", true)])

/-- `match (l, r) { … }` of the `Expr::Cmp` arm. -/
def cmpMatchE : RExpr :=
  .mtch (.tuple (es [v "l", v "r"])) (arms [
    (.tuple (ps [bvPat "w1" "a", bvPat "w2" "b"]), some (.bin "==" (v "w1") (v "w2")),
      blk (cl ["Ok"] [cl ["Value", "Bool"] [cl ["eval_cmp_bv"] [.deref (v "op"), v "a", v "b"]]]), false),
    (.tuple (ps [.tupleS ["Value", "Bool"] (ps [.bind "a"]), .tupleS ["Value", "Bool"] (ps [.bind "b"])]),
      none,
      .mtch (v "op") (arms [
        (.path ["CmpOp", "Eq"], none, cl ["Ok"] [cl ["Value", "Bool"] [.bin "==" (v "a") (v "b")]], true),
        (.path ["CmpOp", "Ne"], none, cl ["Ok"] [cl ["Value", "Bool"] [.bin "!=" (v "a") (v "b")]], true),
        (.wild, none, errRt "bad bool cmp", true)]), true),
    (.wild, none, errRt "bad cmp", true)])

/-- The arms of `match eval_expr(store, cond)? { … }` of the `Expr::Select` arm. -/
def selectArmsE : RArms :=
  arms [
    (.tupleS ["Value", "Bool"] (ps [.litBool true]), none, recEval "then_expr", true),
    (.tupleS ["Value", "Bool"] (ps [.litBool false]), none, recEval "else_expr", true),
    (.wild, none, errRt "select cond not bool", true)]

/-- The arms of `eval_expr`'s outer `match expr { … }`. -/
def evalExprArms : RArms :=
  arms [
    (.structS ["Expr", "ConstBool"] (fps [("value", .bind "value")]) false false, none,
      cl ["Ok"] [cl ["Value", "Bool"] [.deref (v "value")]], true),
    (.structS ["Expr", "ConstBv"] (fps [("width", .bind "width"), ("value", .bind "value")]) false false, none,
      cl ["Ok"] [cl ["Value", "bitvec"] [.deref (v "width"), .deref (v "value")]], true),
    (.structS ["Expr", "Var"] (fps [("name", .bind "name")]) false false, none,
      .mcallCl (mc (mc (v "store") "get" [v "name"]) "copied") "ok_or_else"
        (cl ["EvalError", "UndefinedVar"] [mc (v "name") "clone"]), true),
    (.structS ["Expr", "UnOp"] (fps [("op", .bind "op"), ("expr", .bind "expr")]) false false, none,
      .block (lets [(.bind "v", .question (recEval "expr"))]) unopMatchE, false),
    (.structS ["Expr", "BinOp"] (fps [("op", .bind "op"), ("lhs", .bind "lhs"), ("rhs", .bind "rhs")]) false false,
      none,
      .block (lets [(.bind "l", .question (recEval "lhs")), (.bind "r", .question (recEval "rhs"))]) binopMatchE,
      false),
    (.structS ["Expr", "Cmp"] (fps [("op", .bind "op"), ("lhs", .bind "lhs"), ("rhs", .bind "rhs")]) false false,
      none,
      .block (lets [(.bind "l", .question (recEval "lhs")), (.bind "r", .question (recEval "rhs"))]) cmpMatchE,
      false),
    (.structS ["Expr", "Select"] (fps [("cond", .bind "cond"), ("then_expr", .bind "then_expr"),
        ("else_expr", .bind "else_expr")]) false true, none,
      .mtch (.question (recEval "cond")) selectArmsE, true)]

/-- `eval_expr` (lines 79–137). -/
def evalExprFn : RFn where
  isPub := true
  path := ["eval_expr"]
  params := [("store", ["&", "HashMap", "<", "String", ",", "Value", ">"]), ("expr", ["&", "Expr"])]
  ret := ["Result", "<", "Value", ",", "EvalError", ">"]
  body := blk (.mtch (v "expr") evalExprArms)

end

/-! ## Source binding -/

/-- The exact lines of the uploaded `crates/certir/src/lib.rs`. -/
def certirLib : List String :=
  source_lines% "../source_reference/certiforge/crates/certir/src/lib.rs.txt"

/-- The exact lines of the uploaded `crates/certir-interpreter/src/lib.rs`. -/
def interpLib : List String :=
  source_lines% "../source_reference/certiforge/crates/certir-interpreter/src/lib.rs.txt"

/-- Lines `a … b` (1-based, inclusive). -/
def window (ls : List String) (a b : Nat) : List String := (ls.drop (a - 1)).take (b + 1 - a)

theorem certir_width_source_bound :
    lexLines (window certirLib 20 35) = widthBitsFn.toks ++ widthMaskFn.toks := by decide +kernel

theorem interp_bitvec_source_bound :
    lexLines (window interpLib 14 19) = valueBitvecFn.toks := by decide +kernel

theorem interp_eval_binop_source_bound :
    lexLines (window interpLib 39 66) = evalBinopFn.toks := by decide +kernel

theorem interp_eval_cmp_bv_source_bound :
    lexLines (window interpLib 68 77) = evalCmpBvFn.toks := by decide +kernel

theorem interp_eval_expr_source_bound :
    lexLines (window interpLib 79 137) = evalExprFn.toks := by decide +kernel

/-- Every extracted tree satisfies the precedence discipline. -/
theorem extracted_fns_wf :
    [widthBitsFn, widthMaskFn, valueBitvecFn, evalBinopFn, evalCmpBvFn, evalExprFn].all RFn.wf = true := by
  decide +kernel

end PCSForgeRefinement.Rust
