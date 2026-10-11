import PCSMathLanguage.RoundTrip

/-!
# The controlled mathematical language (`pcs/experimental/prover/language.py`)

A transcription of the token-level language front end of `language.py`, with the precise
Python behaviours that matter for the meaning of a statement:

* `lex` — `TOKEN.findall` for `∀|∃|→|↔|∧|∨|¬|≤|[A-Za-z][A-Za-z0-9_]*|[0-9]+|[(),:+*=]`
  (ASCII letters/digits only; every other character is skipped by `findall`), and `lexOK` —
  the check `"".join(tokens) == re.sub(r"\s", "", source)` where `isPyWs` is exactly the set
  of code points matched by Python's Unicode `\s` (equivalently `str.isspace`): any skipped
  character that is not Unicode whitespace (e.g. `é`, `!`, `_` alone, `−`) rejects;
* `Vars` — the parser's variable dictionary with Python `dict` insertion order (used by the
  default numeral domain `next(v for v in variables.values() if v in {"Nat","Int"})`);
* `parseE` / `opLoop` / `bindersLoop` — `Parser.parse` (a precedence-climbing parser over the
  precedence table `P`, `→` right associative, `¬`/application binding at level 8, typed binder
  groups with the `Nat → Nat` / `Nat → Prop` domain expansion and shadowing rejection);
* `ambiguous` — the unparenthesised `∧`/`∨` mixing detector (groups of parentheses);
* `declCheck` — `theorem(obj)` / `declaration(names, body, domain)`: JSON size bound, at most
  12 binders, `NAME`, `RESERVED`, duplicate binders, body type `Prop`, and the rendered Lean
  statement;
* `tryTable` / `formalizeCore` — the candidate loop of `formalize`: one candidate per
  precedence table (two tables exactly when the body is ambiguous), first error rejects the
  whole statement, duplicates removed by rendered Lean text, untrusted ranking only reorders.

**Recursion bound (counterexample and patch).**  The original `Parser.parse` has no depth
bound; CPython's default recursion limit turns 995 nested parentheses — a 2015-character
statement, inside the 3000-character language bound — into an uncaught `RecursionError`
escaping `formalize` (which only catches `ValueError`).  The reproducer and the proposed
patch (`depth > 256` raises `ValueError`) are in `counterexamples/language_recursion/`.  The
parser here is the **patched** program: `parseE` carries the depth and fails with an ordinary
rejection beyond `PARSE_DEPTH_LIMIT`.

The principal theorem `language_candidates_exact` states the exact candidate set.
-/

namespace PCSMathLanguage
namespace Language

open RoundTrip

/-! ## Tokenisation -/

/-- Exactly the code points matched by Python's Unicode `\s` (checked against CPython 3.11:
`[c for c in range(0x110000) if chr(c).isspace()]`). -/
def isPyWs (c : Char) : Bool :=
  let n := c.toNat
  (9 ≤ n && n ≤ 13) || (28 ≤ n && n ≤ 32) || n == 0x85 || n == 0xA0 || n == 0x1680 ||
  (0x2000 ≤ n && n ≤ 0x200A) || n == 0x2028 || n == 0x2029 || n == 0x202F || n == 0x205F ||
  n == 0x3000

/-- Single-character tokens. -/
def isSingle (c : Char) : Bool :=
  c == '∀' || c == '∃' || c == '→' || c == '↔' || c == '∧' || c == '∨' || c == '¬' || c == '≤' ||
  c == '(' || c == ')' || c == ',' || c == ':' || c == '+' || c == '*' || c == '='

/-- Lexer modes: between tokens, inside an identifier, inside a numeral. -/
inductive LMode where
  | idle | ident | num

/-- `findall`, as a character-level state machine (structural on the input). -/
def lexAux : LMode → List Char → List Char → List String
  | .idle, _, [] => []
  | .ident, acc, [] => [String.ofList acc.reverse]
  | .num, acc, [] => [String.ofList acc.reverse]
  | .ident, acc, c :: cs =>
    if isAN c then lexAux .ident (c :: acc) cs
    else String.ofList acc.reverse ::
      (if isSingle c then String.ofList [c] :: lexAux .idle [] cs
       else if isAsciiLetter c then lexAux .ident [c] cs
       else if isD c then lexAux .num [c] cs
       else lexAux .idle [] cs)
  | .num, acc, c :: cs =>
    if isD c then lexAux .num (c :: acc) cs
    else String.ofList acc.reverse ::
      (if isSingle c then String.ofList [c] :: lexAux .idle [] cs
       else if isAsciiLetter c then lexAux .ident [c] cs
       else if isD c then lexAux .num [c] cs
       else lexAux .idle [] cs)
  | .idle, _, c :: cs =>
    if isSingle c then String.ofList [c] :: lexAux .idle [] cs
    else if isAsciiLetter c then lexAux .ident [c] cs
    else if isD c then lexAux .num [c] cs
    else lexAux .idle [] cs

def lex (src : List Char) : List String := lexAux .idle [] src

/-- `"".join(self.tokens) == re.sub(r"\s", "", source)`. -/
def lexOK (src : List Char) : Bool :=
  String.join (lex src) == String.ofList (src.filter (fun c => !isPyWs c))

/-! ## The variable dictionary (insertion ordered) -/

abbrev Vars := List (String × Ty)

def Vars.get? (v : Vars) (k : String) : Option Ty := (v.find? (·.1 == k)).map (·.2)

def Vars.mem (v : Vars) (k : String) : Bool := (v.get? k).isSome

/-- `del variables[k]`. -/
def Vars.del (v : Vars) (k : String) : Vars := v.filter (·.1 != k)

/-- `{n: domain for n in names}` — later duplicates keep the first position. -/
def initVars (names : List String) (t : Ty) : Vars :=
  names.foldl (fun v n => if v.mem n then v else v ++ [(n, t)]) []

/-- `TYPES` keys. -/
def tyOfKey (s : String) : Option Ty :=
  if s = "Prop" then some .prop else if s = "Nat" then some .nat else if s = "Int" then some .int
  else if s = "NatFn" then some .natFn else if s = "NatPred" then some .natPred else none

/-! ## Precedence tables -/

abbrev Prec := String → Option Nat

def PRECEDENCE : Prec := fun s =>
  if s = "↔" then some 1 else if s = "→" then some 2 else if s = "∨" then some 3
  else if s = "∧" then some 4 else if s = "=" then some 5 else if s = "≤" then some 5
  else if s = "+" then some 6 else if s = "*" then some 7 else none

/-- `{**PRECEDENCE, "∧": 3, "∨": 4}`. -/
def SWAPPED : Prec := fun s =>
  if s = "∧" then some 3 else if s = "∨" then some 4 else PRECEDENCE s

/-- `SYMBOLS = {symbol: op}`. -/
def symOp (s : String) : Option Op :=
  if s = "∧" then some .and else if s = "∨" then some .or else if s = "→" then some .implies
  else if s = "↔" then some .iff else if s = "+" then some .add else if s = "*" then some .mul
  else if s = "=" then some .eq else if s = "≤" then some .le else none

/-! ## The parser -/

/-- Parser state: remaining tokens and the variable dictionary. -/
structure St where
  toks : List String
  vars : Vars

/-- Outcome: success with the new state, an ordinary rejection (`ValueError`), or fuel
exhaustion of the termination device (never reached with the fuel used below). -/
inductive Out (α : Type) where
  | ok (a : α) (st : St)
  | err
  | fuel

def St.peek (st : St) : String := st.toks.headD ""

/-- `take()` -/
def St.take (st : St) : Option (String × St) :=
  match st.toks with
  | [] => none
  | t :: ts => some (t, { st with toks := ts })

/-- `take(expected)` -/
def St.expect (st : St) (e : String) : Option St :=
  match st.take with
  | some (t, st') => if t = e then some st' else none
  | none => none

/-- Patched recursion bound: `if depth > 256: raise ValueError(...)`. -/
def PARSE_DEPTH_LIMIT : Nat := 256

def isDigitTok (s : String) : Bool := !s.isEmpty && s.toList.all isD

/-- The binder groups `(name : domain)` of a quantifier. -/
def bindersLoop : Nat → St → List (String × Ty) → Out (List (String × Ty))
  | 0, _, _ => .fuel
  | f + 1, st, acc =>
    if st.peek = "(" then
      match st.expect "(" with
      | none => .err
      | some st1 =>
        match st1.take with
        | none => .err
        | some (name, st2) =>
          match st2.expect ":" with
          | none => .err
          | some st3 =>
            match st3.take with
            | none => .err
            | some (dom, st4) =>
              let r : Option (String × St) :=
                if dom = "Nat" ∧ st4.peek = "→" then
                  match st4.expect "→" with
                  | none => none
                  | some st5 =>
                    match st5.take with
                    | none => none
                    | some (cod, st6) =>
                      if cod = "Nat" then some ("NatFn", st6)
                      else if cod = "Prop" then some ("NatPred", st6) else none
                else some (dom, st4)
              match r with
              | none => .err
              | some (dom', st6) =>
                match st6.expect ")" with
                | none => .err
                | some st7 =>
                  match tyOfKey dom' with
                  | none => .err
                  | some t =>
                    if st7.vars.mem name then .err
                    else bindersLoop f { st7 with vars := st7.vars ++ [(name, t)] } (acc ++ [(name, t)])
    else .ok acc st

/-- Wrap `for name, domain in reversed(binders): del variables[name]; left = {...}`. -/
def wrapBinders (q : Q) : List (String × Ty) → Expr → Expr
  | [], e => e
  | (n, t) :: bs, e => .quant q n t (wrapBinders q bs e)

mutual
/-- `Parser.parse(minimum)` at recursion depth `d`. -/
def parseE : Nat → Nat → Prec → Nat → St → Out Expr
  | 0, _, _, _, _ => .fuel
  | f + 1, d, P, m, st =>
    if d > PARSE_DEPTH_LIMIT then .err else
    match st.take with
    | none => .err
    | some (tok, st1) =>
      if tok = "(" then
        match parseE f (d + 1) P 0 st1 with
        | .ok left st2 =>
          match st2.expect ")" with
          | some st3 => opLoop f d P m left st3
          | none => .err
        | .err => .err
        | .fuel => .fuel
      else if tok = "∀" ∨ tok = "∃" then
        match bindersLoop (st1.toks.length + 1) st1 [] with
        | .ok bs st2 =>
          if bs = [] then .err else
          match st2.expect "," with
          | none => .err
          | some st3 =>
            match parseE f (d + 1) P 0 st3 with
            | .ok body st4 =>
              let st5 := { st4 with vars := bs.foldl (fun v b => v.del b.1) st4.vars }
              opLoop f d P m (wrapBinders (if tok = "∀" then .all else .ex) bs body) st5
            | .err => .err
            | .fuel => .fuel
        | .err => .err
        | .fuel => .fuel
      else if tok = "¬" then
        match parseE f (d + 1) P 8 st1 with
        | .ok a st2 => opLoop f d P m (.not a) st2
        | .err => .err
        | .fuel => .fuel
      else if tok = "True" then opLoop f d P m .tt st1
      else if tok = "False" then opLoop f d P m .ff st1
      else if isDigitTok tok then
        let dflt : Ty := ((st1.vars.find? (fun p => p.2 == .nat || p.2 == .int)).map (·.2)).getD .nat
        if st1.peek = ":" then
          match st1.expect ":" with
          | none => .err
          | some st2 =>
            match st2.take with
            | none => .err
            | some (dom, st3) =>
              match tyOfKey dom with
              | some t => opLoop f d P m (.num (digVal tok.toList) t) st3
              | none => .err
        else opLoop f d P m (.num (digVal tok.toList) dflt) st1
      else
        match st1.vars.get? tok with
        | some ty =>
          if (ty == .natFn || ty == .natPred) && st1.peek != "" &&
              (st1.peek == "(" || st1.vars.mem st1.peek) then
            match parseE f (d + 1) P 8 st1 with
            | .ok a st2 => opLoop f d P m (.apply (.var tok) a) st2
            | .err => .err
            | .fuel => .fuel
          else opLoop f d P m (.var tok) st1
        | none => .err

/-- `while peek in precedence and precedence[peek] >= minimum: …` -/
def opLoop : Nat → Nat → Prec → Nat → Expr → St → Out Expr
  | 0, _, _, _, _, _ => .fuel
  | f + 1, d, P, m, left, st =>
    match P st.peek, symOp st.peek with
    | some p, some op =>
      if p ≥ m then
        match st.take with
        | none => .err
        | some (sym, st1) =>
          match parseE f (d + 1) P (if sym = "→" then p else p + 1) st1 with
          | .ok right st2 => opLoop f d P m (.bin op left right) st2
          | .err => .err
          | .fuel => .fuel
      else .ok left st
    | _, _ => .ok left st
end

/-! ## Ambiguity detection -/

/-- One `set()` of the detector: does it contain `∧`, `∨`. -/
abbrev G := Bool × Bool

/-- The `groups, current` loop.  (Python appends the *alias* `current[0]` when an unmatched
`)` is met; the set only grows and is itself checked at the end, so the snapshot here gives
the same `any`.) -/
def ambAux : List G → List G → List Char → List G × List G
  | groups, cur, [] => (groups, cur)
  | groups, cur, c :: cs =>
    if c = '(' then ambAux groups (cur ++ [(false, false)]) cs
    else if c = ')' then
      if cur.length > 1 then ambAux (groups ++ [cur.getLastD (false, false)]) cur.dropLast cs
      else ambAux (groups ++ [cur.headD (false, false)]) cur cs
    else if c = '∧' then ambAux groups (cur.dropLast ++ [((cur.getLastD (false, false)).1 || true, (cur.getLastD (false, false)).2)]) cs
    else if c = '∨' then ambAux groups (cur.dropLast ++ [((cur.getLastD (false, false)).1, (cur.getLastD (false, false)).2 || true)]) cs
    else ambAux groups cur cs

def ambiguous (body : String) : Bool :=
  let r := ambAux [] [(false, false)] body.toList
  (r.1 ++ r.2).any (fun g => g.1 && g.2)

/-- The precedence tables tried by `formalize`. -/
def tables (body : String) : List Prec :=
  if ambiguous body then [PRECEDENCE, SWAPPED] else [PRECEDENCE]

/-! ## `theorem(obj)`: declaration checking and rendering -/

def _root_.PCSMathLanguage.Op.name : Op → String
  | .and => "and" | .or => "or" | .implies => "implies" | .iff => "iff"
  | .add => "add" | .mul => "mul" | .eq => "eq" | .le => "le"

/-- Length of `json.dumps` of a string (`ensure_ascii=True`). -/
def jsonStrLen (s : String) : Nat :=
  2 + (s.toList.map fun c =>
    if c = '"' ∨ c = '\\' ∨ c = '\n' ∨ c = '\r' ∨ c = '\t' ∨ c.toNat = 8 ∨ c.toNat = 12 then 2
    else if 32 ≤ c.toNat ∧ c.toNat ≤ 126 then 1
    else if c.toNat < 0x10000 then 6 else 12).sum

/-- `json.dumps` length of a dict with the given (key, value-length) entries, default
separators `", "` and `": "`. -/
def jsonObjLen (kvs : List (String × Nat)) : Nat :=
  2 + (kvs.map fun kv => jsonStrLen kv.1 + 2 + kv.2).sum + 2 * (kvs.length - 1)

def jsonListLen (xs : List Nat) : Nat :=
  2 + xs.sum + 2 * (xs.length - 1)

/-- `json.dumps` length of a parser-built expression dict (keys in construction order). -/
def jsonExprLen : Expr → Nat
  | .var n => jsonObjLen [("op", jsonStrLen "var"), ("name", jsonStrLen n)]
  | .num v t => jsonObjLen [("op", jsonStrLen "number"), ("value", (toString v).length),
      ("type", jsonStrLen t.key)]
  | .tt => jsonObjLen [("op", jsonStrLen "true")]
  | .ff => jsonObjLen [("op", jsonStrLen "false")]
  | .not a => jsonObjLen [("op", jsonStrLen "not"), ("arg", jsonExprLen a)]
  | .apply f a => jsonObjLen [("op", jsonStrLen "apply"), ("fn", jsonExprLen f), ("arg", jsonExprLen a)]
  | .quant q n t b => jsonObjLen [("op", jsonStrLen (if q = .all then "forall" else "exists")),
      ("name", jsonStrLen n), ("type", jsonStrLen t.key), ("body", jsonExprLen b)]
  | .bin op l r => jsonObjLen [("op", jsonStrLen op.name), ("left", jsonExprLen l), ("right", jsonExprLen r)]

def jsonDeclLen (d : Decl) : Nat :=
  jsonObjLen [("format", jsonStrLen "pcs-math-ir-v1"),
    ("binders", jsonListLen (d.binders.map fun b =>
      jsonObjLen [("name", jsonStrLen b.1), ("type", jsonStrLen b.2.key)])),
    ("body", jsonExprLen d.body)]

/-- The binder loop of `theorem`: `NAME`, not `RESERVED`, not duplicate. Newest first. -/
def binderVars : List (String × Ty) → Vars → Option Vars
  | [], v => some v
  | (n, t) :: bs, v =>
    if validName n && !RESERVED.contains n && !(lookupTy v n).isSome then binderVars bs ((n, t) :: v)
    else none

/-- `theorem(obj)`: `some lean` iff accepted. -/
def declCheck (d : Decl) : Option String :=
  if jsonDeclLen d > 16000 ∨ d.binders.length > 12 then none else
  match binderVars d.binders [] with
  | none => none
  | some v =>
    match check v 0 d.body with
    | some (.prop, b) =>
      some (if d.binders = [] then b
        else "∀ " ++ " ".intercalate (d.binders.map fun p => "(" ++ p.1 ++ " : " ++ p.2.lean ++ ")")
          ++ ", " ++ b)
    | _ => none

/-! ## Candidates -/

structure Cand where
  ir : Decl
  lean : String
  deriving DecidableEq, Repr

/-- One iteration of the candidate loop for table `P`: `none` is a `ValueError`. -/
def tryTable (names : List String) (domain : Ty) (body : String) (P : Prec) : Option Cand :=
  if body.length > 3000 then none else
  if !lexOK body.toList then none else
  let toks := lex body.toList
  match parseE (2 * toks.length + 2) 0 P 0 ⟨toks, initVars names domain⟩ with
  | .ok e st =>
    if st.toks ≠ [] then none else
    match check st.vars 0 e with
    | none => none
    | some _ =>
      let ir : Decl := ⟨names.map (·, domain), e⟩
      (declCheck ir).map fun l => ⟨ir, l⟩
  | _ => none

/-- The candidate loop: the first `ValueError` rejects; duplicates by Lean text dropped. -/
def collect (names : List String) (domain : Ty) (body : String) :
    List Prec → List Cand → Option (List Cand)
  | [], acc => some acc
  | P :: Ps, acc =>
    match tryTable names domain body P with
    | none => none
    | some c => collect names domain body Ps (if acc.any (·.lean == c.lean) then acc else acc ++ [c])

/-- Untrusted ranking: `candidates.sort(key=lambda c: -c["score"])` (stable). -/
def rank (ranker : Option (Decl → Int)) (cs : List Cand) : List Cand :=
  match ranker with
  | none => cs
  | some r => cs.mergeSort (fun a b => decide (r b.ir ≤ r a.ir))

/-- The body-level core of `formalize`: `none` is status `unsupported`; otherwise the
candidate list (status `ambiguous` iff it has more than one element). -/
def formalizeCore (names : List String) (domain : Ty) (body : String)
    (ranker : Option (Decl → Int)) : Option (List Cand) :=
  (collect names domain body (tables body) []).map (rank ranker)

/-- Status reported by `formalize` for a successful candidate list. -/
def status (cs : List Cand) : String := if cs.length > 1 then "ambiguous" else "supported"

end Language
end PCSMathLanguage

