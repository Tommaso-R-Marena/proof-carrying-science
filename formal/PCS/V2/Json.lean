/-!
# PCS v0.6 canonical JSON (RFC 8785 / `pcs-jcs-rfc8785-v1`) — verified fragment

This module formalizes the exact canonical JSON byte representation that the
production Python implementation (`pcs/canonical_json.py`) produces and that every
v0.6 byte gate (`parse_*_bytes_v06`) requires:

* no insignificant whitespace;
* object members in strictly increasing UTF-16 code-unit key order
  (checked separately by `PCS.V2.Canonical`);
* strings written exactly as Python `json.dumps(s, ensure_ascii=False)` writes them
  (`\"`, `\\`, `\b`, `\t`, `\n`, `\f`, `\r`, other C0 controls as lower-case `\u00xx`,
  everything else raw UTF-8);
* `null`, `true`, `false`;
* integers written in plain decimal (the JCS/ECMAScript spelling of every *safe*
  integer, |n| ≤ 2^53).  Non-integral numbers are outside the verified fragment
  and are rejected by the Lean checker.  No v0.6 normalized-decision or
  normalized-index field admits a number at all.

Main results (see `PCS.V2.JsonRoundtrip`):

* `parseVal_ser` : the canonical parser inverts the serializer;
* `ser_injective` / `jcsBytes_injective` : distinct JSON values have distinct
  canonical character sequences / canonical UTF-8 byte strings.
-/

namespace PCS.V2.Json

/-- JSON values of the verified fragment.  Objects keep member order; canonical
    order is a separate decidable predicate. -/
inductive JVal where
  | null
  | bool (b : Bool)
  | num (i : Int)
  | str (s : String)
  | arr (xs : List JVal)
  | obj (ms : List (String × JVal))
  deriving Repr, Inhabited

/-! ## Decimal digits -/

def digitChar (d : Nat) : Char := Char.ofNat (48 + d)

/-- Most-significant-first decimal digits. -/
def decDigits (n : Nat) : List Char :=
  if n < 10 then [digitChar n] else decDigits (n / 10) ++ [digitChar (n % 10)]
termination_by n
decreasing_by omega

def digitVal (c : Char) : Nat := c.toNat - 48

def ofDigits (cs : List Char) : Nat := cs.foldl (fun a c => 10 * a + digitVal c) 0

/-! ## Strings -/

def hexDigit (d : Nat) : Char :=
  if d < 10 then Char.ofNat (48 + d) else Char.ofNat (87 + d)

/-- Exactly Python `json.dumps(..., ensure_ascii=False)` per-character escaping. -/
def escChar (c : Char) : List Char :=
  if c = '"' then ['\\', '"']
  else if c = '\\' then ['\\', '\\']
  else if c = '\x08' then ['\\', 'b']
  else if c = '\t' then ['\\', 't']
  else if c = '\n' then ['\\', 'n']
  else if c = '\x0c' then ['\\', 'f']
  else if c = '\r' then ['\\', 'r']
  else if c.toNat < 0x20 then
    ['\\', 'u', '0', '0', hexDigit (c.toNat / 16), hexDigit (c.toNat % 16)]
  else [c]

def escStr : List Char → List Char
  | [] => []
  | c :: cs => escChar c ++ escStr cs

def serStr (s : String) : List Char := '"' :: escStr s.toList ++ ['"']

/-! ## Serializer -/

def serNum (i : Int) : List Char :=
  if i < 0 then '-' :: decDigits i.natAbs else decDigits i.natAbs

mutual
def ser : JVal → List Char
  | .null => ['n', 'u', 'l', 'l']
  | .bool true => ['t', 'r', 'u', 'e']
  | .bool false => ['f', 'a', 'l', 's', 'e']
  | .num i => serNum i
  | .str s => serStr s
  | .arr [] => ['[', ']']
  | .arr (x :: xs) => '[' :: ser x ++ serElemsTail xs
  | .obj [] => ['{', '}']
  | .obj ((k, v) :: ms) => '{' :: serStr k ++ ':' :: ser v ++ serMembersTail ms

/-- `,x1,x2,...,xn]` -/
def serElemsTail : List JVal → List Char
  | [] => [']']
  | x :: xs => ',' :: ser x ++ serElemsTail xs

/-- `,"k1":v1,...}` -/
def serMembersTail : List (String × JVal) → List Char
  | [] => ['}']
  | (k, v) :: ms => ',' :: serStr k ++ ':' :: ser v ++ serMembersTail ms
end

/-- The canonical UTF-8 bytes of a JSON value. -/
def jcsBytes (v : JVal) : ByteArray := (ser v).utf8Encode

/-! ## Canonical parser -/

def hexVal (c : Char) : Option Nat :=
  if '0' ≤ c ∧ c ≤ '9' then some (c.toNat - 48)
  else if 'a' ≤ c ∧ c ≤ 'f' then some (c.toNat - 87)
  else none

/-- Parse the body of a string literal (after the opening quote), returning the
    decoded characters and the input after the closing quote. -/
def parseStrBody : List Char → Option (List Char × List Char)
  | [] => none
  | '"' :: r => some ([], r)
  | '\\' :: '"' :: r => (parseStrBody r).map fun p => ('"' :: p.1, p.2)
  | '\\' :: '\\' :: r => (parseStrBody r).map fun p => ('\\' :: p.1, p.2)
  | '\\' :: 'b' :: r => (parseStrBody r).map fun p => ('\x08' :: p.1, p.2)
  | '\\' :: 't' :: r => (parseStrBody r).map fun p => ('\t' :: p.1, p.2)
  | '\\' :: 'n' :: r => (parseStrBody r).map fun p => ('\n' :: p.1, p.2)
  | '\\' :: 'f' :: r => (parseStrBody r).map fun p => ('\x0c' :: p.1, p.2)
  | '\\' :: 'r' :: r => (parseStrBody r).map fun p => ('\r' :: p.1, p.2)
  | '\\' :: 'u' :: '0' :: '0' :: a :: b :: r =>
      match hexVal a, hexVal b with
      | some x, some y => (parseStrBody r).map fun p => (Char.ofNat (16 * x + y) :: p.1, p.2)
      | _, _ => none
  | '\\' :: _ => none
  | c :: r => (parseStrBody r).map fun p => (c :: p.1, p.2)

def spanDigits : List Char → List Char × List Char
  | [] => ([], [])
  | c :: r =>
      if c.isDigit then
        let p := spanDigits r
        (c :: p.1, p.2)
      else ([], c :: r)

def parseNat (cs : List Char) : Option (Nat × List Char) :=
  match spanDigits cs with
  | ([], _) => none
  | (ds, r) => some (ofDigits ds, r)

mutual
/-- Fuel-bounded canonical parser. -/
def parseVal : Nat → List Char → Option (JVal × List Char)
  | 0, _ => none
  | _ + 1, [] => none
  | n + 1, c :: r =>
    if c = 'n' then
      match r with
      | 'u' :: 'l' :: 'l' :: r' => some (.null, r')
      | _ => none
    else if c = 't' then
      match r with
      | 'r' :: 'u' :: 'e' :: r' => some (.bool true, r')
      | _ => none
    else if c = 'f' then
      match r with
      | 'a' :: 'l' :: 's' :: 'e' :: r' => some (.bool false, r')
      | _ => none
    else if c = '"' then
      (parseStrBody r).map fun p => (.str (String.ofList p.1), p.2)
    else if c = '[' then
      match r with
      | ']' :: r' => some (.arr [], r')
      | _ =>
        match parseVal n r with
        | some (x, r') =>
          match parseElemsTail n r' with
          | some (xs, r'') => some (.arr (x :: xs), r'')
          | none => none
        | none => none
    else if c = '{' then
      match r with
      | '}' :: r' => some (.obj [], r')
      | '"' :: r1 =>
        match parseStrBody r1 with
        | some (k, ':' :: r2) =>
          match parseVal n r2 with
          | some (v, r3) =>
            match parseMembersTail n r3 with
            | some (ms, r4) => some (.obj ((String.ofList k, v) :: ms), r4)
            | none => none
          | none => none
        | _ => none
      | _ => none
    else if c = '-' then
      (parseNat r).map fun p => (.num (-(p.1 : Int)), p.2)
    else if c.isDigit then
      (parseNat (c :: r)).map fun p => (.num (p.1 : Int), p.2)
    else none

def parseElemsTail : Nat → List Char → Option (List JVal × List Char)
  | 0, _ => none
  | _ + 1, ']' :: r => some ([], r)
  | n + 1, ',' :: r =>
    match parseVal n r with
    | some (x, r') =>
      match parseElemsTail n r' with
      | some (xs, r'') => some (x :: xs, r'')
      | none => none
    | none => none
  | _ + 1, _ => none

def parseMembersTail : Nat → List Char → Option (List (String × JVal) × List Char)
  | 0, _ => none
  | _ + 1, '}' :: r => some ([], r)
  | n + 1, ',' :: '"' :: r1 =>
    match parseStrBody r1 with
    | some (k, ':' :: r2) =>
      match parseVal n r2 with
      | some (v, r3) =>
        match parseMembersTail n r3 with
        | some (ms, r4) => some ((String.ofList k, v) :: ms, r4)
        | none => none
      | none => none
    | _ => none
  | _ + 1, _ => none
end

/-- Top-level canonical parse of a complete character sequence. -/
def parse (cs : List Char) : Option JVal :=
  match parseVal (cs.length + 1) cs with
  | some (v, []) => some v
  | _ => none

end PCS.V2.Json
