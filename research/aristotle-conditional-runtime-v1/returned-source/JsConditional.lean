import PCSConditionalRuntime.JsFront

/-!
# Whole-file extraction certificate for the current website `public/conditional-core.mjs`

`conditionalJsSrc` is the exact content of the uploaded current file
(`source_reference/current/proof-carrying-science-site/public/conditional-core.mjs.txt`, bound by
`CURRENT_RUNTIME_SOURCES.json`), split at every `'\n'`.

`conditionalJsSegs` cuts the **entire** file into segments: the header comment, the `import` line (whose names become externs), the extracted code (module constants, `evaluateConditional`, `ResourceLimit`, the
`Diagram` class with all its methods, and `checkConditional`) and the exported functions /
constants that are not extracted (`validateConditional`, `verifyConditional`, `parseFormula`,
`conditionalFromText`, `formulaText`).

* `conditional_js_source_bound` — the segments cover the file exactly and every extracted
  segment renders byte-for-byte to its lines, under the precedence / syntax discipline
  (checked by the kernel).
-/

namespace PCSCR.Js

/-- The exact lines of the current `conditional-core.mjs`. -/
def conditionalJsSrc : List String :=
  source_lines% "../source_reference/current/proof-carrying-science-site/public/conditional-core.mjs.txt"

section
open JE

private def n (x : String) : JE := .name x
private def s (x : String) : JE := .str x
private def nm (k : Nat) : JE := .num k
private def mb (a : JE) (k : String) : JE := .mem a k
private def th (k : String) : JE := .mem (.name "this") k
private def cl (f : String) (args : List JE) : JE := .call (.name f) args
private def mc (o : JE) (meth : String) (args : List JE) : JE := .call (.mem o meth) args
private def seq (a b : JE) : JE := .bin .seq a b
private def ret (e : JE) : JS := .ret (some e)
private def asg (t e : JE) : JS := .assign t e
private def cst (ds : List JD) : JS := .decl "const" ds
private def dn (x : String) (e : JE) : JD := .name x (some e)
private def if1 (c : JE) (t : JS) : JS := .ifS c t none none
private def ev (a b : JE) : JE := cl "evaluateConditional" [a, b]

def jsHeader : List String := [
  "// Independent reduced ordered BDD engine. Partial work cannot establish a result."]

def jsConstants : List JItem := [
  .stmt true (cst [dn "TASK" (s "pcs-conditional-boolean-task-v1"),
    dn "RECEIPT" (s "pcs-conditional-boolean-receipt-v1")]),
  .stmt false (cst [dn "OPS" (.arr [s "atom", s "true", s "false", s "not", s "and", s "or", s "implies"]),
    dn "RESERVED" (.arr [s "AND", s "OR", s "NOT", s "IMPLIES", s "TRUE", s "FALSE"])]),
  .stmt true (cst [dn "DEFAULT_LIMITS" (mc (n "Object") "freeze"
    [.obj [.kv "nodes" (nm 4096), .kv "operations" (nm 100000)]])])]

def jsEvaluate : JItem :=
  .func true false "evaluateConditional" [.plain "f", .plain "a"] [
    .switch (mb (n "f") "op") [
      ("atom", [ret (.idx (n "a") (mb (n "f") "symbol"))]),
      ("true", [ret .tru]),
      ("false", [ret .fls]),
      ("not", [ret (.not (ev (mb (n "f") "body") (n "a")))]),
      ("and", [ret (.bin .and (ev (mb (n "f") "left") (n "a")) (ev (mb (n "f") "right") (n "a")))]),
      ("or", [ret (.bin .or (ev (mb (n "f") "left") (n "a")) (ev (mb (n "f") "right") (n "a")))]),
      ("implies", [ret (.bin .or (.not (ev (mb (n "f") "left") (n "a"))) (ev (mb (n "f") "right") (n "a")))])]
      [.throw (cl "Error" [s "Unsupported Boolean operator"])]]

def jsResourceLimit : JItem := .cls "ResourceLimit" (some "Error") []

def jsCtor : JMethod := ⟨"constructor", ["names", "limits"], [
  asg (th "names") (n "names"), asg (th "limits") (n "limits"), asg (th "nodes") (.arr []),
  asg (th "unique") (.new "Map" []), asg (th "memo") (.new "Map" []), asg (th "operations") (nm 0),
  asg (th "visits") (nm 0), asg (th "witnessSteps") (nm 0)]⟩

def jsNode : JMethod := ⟨"node", ["v", "lo", "hi"], [
  if1 (seq (n "lo") (n "hi")) (ret (n "lo")),
  cst [dn "key" (mc (.arr [n "v", n "lo", n "hi"]) "join" [s ","])],
  if1 (mc (th "unique") "has" [n "key"]) (ret (mc (th "unique") "get" [n "key"])),
  if1 (.bin .ge (mb (th "nodes") "length") (mb (th "limits") "nodes")) (.throw (.new "ResourceLimit" [s "nodes"])),
  cst [dn "id" (.bin .add (mb (th "nodes") "length") (nm 2))],
  .expr (mc (th "nodes") "push" [.arr [n "v", n "lo", n "hi"]]),
  .expr (mc (th "unique") "set" [n "key", n "id"]),
  ret (n "id")]⟩

private def nodeAt (x : String) : JE := .idx (th "nodes") (.bin .sub (n x) (nm 2))

def jsApply : JMethod := ⟨"apply", ["op", "a", "b"], [
  if1 (.bin .ge (th "operations") (mb (th "limits") "operations")) (.throw (.new "ResourceLimit" [s "operations"])),
  .incr (th "operations"),
  if1 (.bin .gt (n "a") (n "b")) (asg (.arr [n "a", n "b"]) (.arr [n "b", n "a"])),
  cst [dn "key" (mc (.arr [n "op", n "a", n "b"]) "join" [s ","])],
  if1 (mc (th "memo") "has" [n "key"]) (ret (mc (th "memo") "get" [n "key"])),
  .decl "let" [.name "result" none],
  .nl 2,
  .ifS (.bin .and (.bin .lt (n "a") (nm 2)) (.bin .lt (n "b") (nm 2)))
    (asg (n "result") (.cond (seq (n "op") (s "and")) (cl "Number" [cl "Boolean" [.bin .and (n "a") (n "b")]])
      (.cond (seq (n "op") (s "or")) (cl "Number" [cl "Boolean" [.bin .or (n "a") (n "b")]])
        (cl "Number" [.bin .sne (n "a") (n "b")]))))
    (some 2) (some (.block [
      cst [dn "av" (.cond (.bin .ge (n "a") (nm 2)) (.idx (nodeAt "a") (nm 0)) (mb (th "names") "length")),
        dn "bv" (.cond (.bin .ge (n "b") (nm 2)) (.idx (nodeAt "b") (nm 0)) (mb (th "names") "length")),
        dn "v" (mc (n "Math") "min" [n "av", n "bv"])],
      .nl 3,
      cst [.arrPat ["al", "ah"] (.cond (seq (n "av") (n "v")) (mc (nodeAt "a") "slice" [nm 1]) (.arr [n "a", n "a"])),
        .arrPat ["bl", "bh"] (.cond (seq (n "bv") (n "v")) (mc (nodeAt "b") "slice" [nm 1]) (.arr [n "b", n "b"]))],
      .nl 3,
      cst [dn "lo" (mc (n "this") "apply" [n "op", n "al", n "bl"]),
        dn "hi" (mc (n "this") "apply" [n "op", n "ah", n "bh"])],
      asg (n "result") (mc (n "this") "node" [n "v", n "lo", n "hi"]),
      .nl 2])),
  .expr (mc (th "memo") "set" [n "key", n "result"]),
  ret (n "result"),
  .nl 1]⟩

def jsCompile : JMethod := ⟨"compile", ["f"], [
  .incr (th "visits"),
  .switch (mb (n "f") "op") [
    ("atom", [ret (mc (n "this") "node" [mc (th "names") "indexOf" [mb (n "f") "symbol"], nm 0, nm 1])]),
    ("true", [ret (nm 1)]),
    ("false", [ret (nm 0)]),
    ("not", [ret (mc (n "this") "apply" [s "xor", mc (n "this") "compile" [mb (n "f") "body"], nm 1])])]
    [.block [
      cst [dn "a" (mc (n "this") "compile" [mb (n "f") "left"]), dn "b" (mc (n "this") "compile" [mb (n "f") "right"])],
      ret (.cond (seq (mb (n "f") "op") (s "implies"))
        (mc (n "this") "apply" [s "or", mc (n "this") "apply" [s "xor", n "a", nm 1], n "b"])
        (mc (n "this") "apply" [mb (n "f") "op", n "a", n "b"]))]]]⟩

def jsConjunction : JMethod := ⟨"conjunction", ["roots"], [
  .decl "let" [dn "r" (nm 1)],
  .forOf "const" "n" (n "roots") (asg (n "r") (mc (n "this") "apply" [s "and", n "r", n "n"])),
  ret (n "r")]⟩

def jsWorld : JMethod := ⟨"world", ["root"], [
  if1 (seq (n "root") (nm 0)) (ret .null),
  cst [dn "values" (mc (n "Object") "fromEntries" [mc (th "names") "map" [.arrow1 "n" (.arr [n "n", .fls])]])],
  .while (.bin .ge (n "root") (nm 2)) (.block [
    .incr (th "witnessSteps"),
    cst [.arrPat ["v", "lo", "hi"] (.idx (th "nodes") (.bin .sub (n "root") (nm 2)))],
    asg (.idx (n "values") (.idx (th "names") (n "v"))) (seq (n "lo") (nm 0)),
    asg (n "root") (.cond (seq (n "lo") (nm 0)) (n "hi") (n "lo"))]),
  if1 (.bin .sne (n "root") (nm 1)) (.throw (cl "Error" [s "Invalid diagram terminal"])),
  ret (n "values")]⟩

def jsWork : JMethod := ⟨"work", [], [
  ret (.obj [.kv "bdd_nodes" (mb (th "nodes") "length"), .kv "apply_calls" (th "operations"),
    .kv "ast_visits" (th "visits"), .kv "witness_steps" (th "witnessSteps")])]⟩

def jsDiagram : JItem := .cls "Diagram" none [jsCtor, jsNode, jsApply, jsCompile, jsConjunction, jsWorld, jsWork]

private def m' : JE := n "m"
private def r' : JE := n "r"
private def premAt (j : String) : JE := .idx (n "premises") (n j)

def jsCheck : JItem :=
  .func true true "checkConditional" [.plain "input", .objDefault "limits" (n "DEFAULT_LIMITS")] [
    .nl 1,
    cst [dn "t" (cl "validateConditional" [cl "structuredClone" [n "input"]])],
    asg (n "limits") (cl "structuredClone" [n "limits"]),
    .expr (cl "exact" [n "limits", .arr [s "nodes", s "operations"]]),
    .forOf "const" "k" (mc (n "Object") "keys" [n "limits"])
      (.expr (cl "integer" [.idx (n "limits") (n "k"), nm 1, .idx (n "DEFAULT_LIMITS") (n "k")])),
    cst [dn "m" (.new "Diagram" [mb (n "t") "variables", n "limits"])],
    .nl 1,
    cst [dn "r" (.obj [.kv "format" (n "RECEIPT"), .kv "checker" (s "pcs-conditional-bdd/1"),
      .kv "original_task" (n "t"), .kv "task_sha256" (.await (cl "digest" [n "t"])), .short "limits",
      .kv "decision" .null, .kv "context_example" .null, .kv "counterexample" .null, .kv "unsat_core" .null,
      .kv "core_necessity_witnesses" .null, .kv "diagram" .null, .kv "limit_reached" .null,
      .kv "scope" (s "Declared Boolean interpretations and explicit assumptions only"),
      .kv "pcs_authority" .fls, .kv "lean_kernel_checked" .fls])],
    .nl 1,
    .tryCatch [
      .nl 2,
      cst [dn "premises" (.arr [])],
      .decl "let" [dn "context" (nm 1), dn "source" .null, dn "candidate" .null, dn "difference" .null],
      .forOf "const" "f" (mb (n "t") "assumptions") (.block [
        .expr (mc (n "premises") "push" [mc m' "compile" [n "f"]]),
        asg (n "context") (mc m' "apply" [s "and", n "context", mc (n "premises") "at" [.neg (nm 1)]]),
        if1 (seq (n "context") (nm 0)) .brk]),
      .nl 2,
      .ifS (seq (n "context") (nm 0)) (.block [
        .decl "let" [dn "core" (mc (n "premises") "map" [.arrowP ["_", "i"] (n "i")])],
        .forOf "const" "i" (.arr [.spread (n "core")]) (.block [
          cst [dn "remaining" (mc (n "core") "filter" [.arrow1 "j" (.bin .sne (n "j") (n "i"))])],
          if1 (seq (mc m' "conjunction" [mc (n "remaining") "map" [.arrow1 "j" (premAt "j")]]) (nm 0))
            (asg (n "core") (n "remaining"))]),
        .nl 3,
        cst [dn "necessities" (mc (n "core") "map" [.arrowB "i" [
          cst [dn "assignment" (mc m' "world" [mc m' "conjunction"
            [mc (mc (n "core") "filter" [.arrow1 "j" (.bin .sne (n "j") (n "i"))]) "map" [.arrow1 "j" (premAt "j")]]])],
          if1 (seq (n "assignment") .null) (.throw (cl "Error" [s "Invalid minimal conflict"])),
          ret (.obj [.kv "removed_assumption" (n "i"), .short "assignment"])]])],
        .expr (mc (n "Object") "assign" [r', .obj [.kv "decision" (s "inconsistent_assumptions"),
          .kv "unsat_core" (n "core"), .kv "core_necessity_witnesses" (n "necessities")]]),
        .nl 2])
        none (some (.block [
          asg (n "source") (mc m' "compile" [mb (n "t") "source"]),
          asg (n "candidate") (mc m' "compile" [mb (n "t") "candidate"]),
          asg (n "difference") (mc m' "apply" [s "and", n "context", mc m' "apply" [s "xor", n "source", n "candidate"]]),
          asg (mb r' "context_example") (mc m' "world" [n "context"]),
          cst [dn "world" (mc m' "world" [n "difference"])],
          .ifS (seq (n "world") .null) (asg (mb r' "decision") (s "equivalent_under_assumptions")) none (some (.block [
            cst [dn "truths" (mc (mb (n "t") "assumptions") "map" [.arrow1 "f" (ev (n "f") (n "world"))]),
              dn "a" (ev (mb (n "t") "source") (n "world")), dn "b" (ev (mb (n "t") "candidate") (n "world"))],
            if1 (.bin .or (.not (mc (n "truths") "every" [n "Boolean"])) (seq (n "a") (n "b")))
              (.throw (cl "Error" [s "Invalid counterexample"])),
            .expr (mc (n "Object") "assign" [r', .obj [.kv "decision" (s "counterexample"),
              .kv "counterexample" (.obj [.kv "assignment" (n "world"), .kv "source_true" (n "a"),
                .kv "candidate_true" (n "b"), .kv "assumptions_true" (n "truths")])]])]))])),
      .nl 2,
      asg (mb r' "diagram") (.obj [.kv "nodes" (mb m' "nodes"), .short "source", .short "candidate",
        .short "context", .short "difference"]),
      .nl 1]
      "e" [
      if1 (.not (.paren (.bin .inst (n "e") (n "ResourceLimit")))) (.throw (n "e")),
      .forOf "const" "k" (.arr [s "context_example", s "counterexample", s "unsat_core",
        s "core_necessity_witnesses", s "diagram"]) (asg (.idx r' (n "k")) .null),
      .expr (mc (n "Object") "assign" [r', .obj [.kv "decision" (s "resource_limit"),
        .kv "limit_reached" (mb (n "e") "message")]])],
    .nl 1,
    asg (mb r' "work") (mc m' "work" []),
    asg (mb r' "receipt_sha256") (.await (cl "digest" [r'])),
    ret r',
    .nl 0]

end

def conditionalJsSegs : List JSeg := [
  .header jsHeader,
  .imports ["canonical", "digest", "exact", "integer"] "./omega-core.mjs",
  .code jsConstants,
  .opaque "validateConditional" 12,
  .code [jsEvaluate, jsResourceLimit, jsDiagram, jsCheck],
  .opaque "verifyConditional" 1,
  .opaque "parseFormula" 11,
  .opaque "conditionalFromText" 6,
  .opaque "formulaText" 1]

/-- **Source binding**: the segments cover the current file exactly; every extracted segment
renders byte-for-byte under the precedence / syntax discipline. -/
theorem conditional_js_source_bound : checkJSegs conditionalJsSrc conditionalJsSegs = true := by
  decide +kernel

theorem conditional_js_length : conditionalJsSrc.length = 66 := by decide +kernel

end PCSCR.Js
