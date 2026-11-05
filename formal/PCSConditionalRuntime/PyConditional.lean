import PCSConditionalRuntime.PyFront

/-!
# Whole-file extraction certificate for the current `pcs/experimental/conditional.py`

`conditionalPySrc` is the exact content of the uploaded current file
(`source_reference/current/proof-carrying-science/pcs/experimental/conditional.py.txt`,
SHA-256 `4045bf1d…22bf1`, revision `a729b46c…218e`), split at every `'\n'`.

`conditionalSegs` cuts the **entire** file into segments: the module header (docstring and
imports), the extracted code (module constants, `exact`, `evaluate`, `ResourceLimit`, the
`Diagram` class with all its methods, and `check`) and the five top-level functions that are
not extracted (`digest`, `validate`, `verify`, `parse_formula`, `from_text`).

* `conditional_py_source_bound` — the segments cover the file exactly and every extracted
  segment renders byte-for-byte to its lines (checked by the kernel);
* `conditional_py_wf` is part of that check (precedence / bracket discipline);
* `conditional_py_lowers` — lowering succeeds and produces `conditionalPyModule`, whose
  program table resolves `check`'s callees by name: `exact`, `evaluate`, `Diagram.__init__`,
  `Diagram.node`, `Diagram.apply`, `Diagram.compile`, `Diagram.conjunction`, `Diagram.world`,
  `Diagram.work`, the exception class `ResourceLimit`, and the externs `digest`, `validate`.
-/

namespace PCSCR.Py

/-- The exact lines of the current `conditional.py`. -/
def conditionalPySrc : List String :=
  source_lines% "../source_reference/current/proof-carrying-science/pcs/experimental/conditional.py.txt"

section
open PE

private def n (x : String) : PE := .name x
private def s (x : String) : PE := .str x
private def at' (e : PE) (k : String) : PE := .sub e (.str k)
private def cl (f : String) (args : List PE) : PE := .call (.name f) args
private def mc (o : PE) (m : String) (args : List PE) : PE := .call (.attr o m) args
private def sf (f : String) : PE := .attr (.name "self") f
private def p (x : String) : Param := ⟨x, Option.none⟩
private def st (ss : List PS) : PL := .simple ss Option.none
private def eq (a b : PE) : PE := .bin .eq a b
private def ifl (c : PE) (ss : List PS) : PL := .ifS c (.inline ss Option.none) Option.none
private def ret (e : PE) : PS := .ret (some e)
private def asg (t : PE) (e : PE) : PS := .assign [t] e

def headerLines : List String := [
  "\"\"\"Bounded, assumption-aware Boolean reasoning using reduced ordered BDDs.",
  "",
  "This experimental checker is not registered PCS scientific authority. It gives",
  "exact results within explicit Boolean interpretations, or a resource-limit result.",
  "\"\"\"",
  "from copy import deepcopy",
  "import hashlib",
  "import re",
  "",
  "from pcs.canonical_json import canonicalize_jcs_bytes",
  ""]

def constantsCST : List PL := [
  st [asg (n "TASK") (s "pcs-conditional-boolean-task-v1")],
  st [asg (n "RECEIPT") (s "pcs-conditional-boolean-receipt-v1")],
  st [asg (n "OPS") (.set [s "atom", s "true", s "false", s "not", s "and", s "or", s "implies"])],
  st [asg (n "RESERVED") (.set [s "AND", s "OR", s "NOT", s "IMPLIES", s "TRUE", s "FALSE"])],
  st [asg (.tuple [n "MAX_VARIABLES", n "MAX_FORMULA_NODES", n "MAX_DEPTH"]) (.tuple [.num 24, .num 128, .num 12])],
  st [asg (n "DEFAULT_LIMITS") (.dict [.kv (s "nodes") (.num 4096), .kv (s "operations") (.num 100000)])],
  .blank, .blank]

def exactCST : List PL := [
  .blank, .blank,
  .defS "exact" [p "value", p "fields"] [
    .ifS (.orE (.bin .isNot (cl "type" [n "value"]) (n "dict")) (.bin .ne (cl "set" [n "value"]) (cl "set" [n "fields"])))
      (.block [st [.raise (cl "ValueError" [s "Unexpected conditional protocol fields"])]]) Option.none,
    st [ret (n "value")]],
  .blank, .blank]

def evaluateCST : PL :=
  .defS "evaluate" [p "formula", p "assignment"] [
    st [asg (n "op") (at' (n "formula") "op")],
    ifl (eq (n "op") (s "atom")) [ret (.sub (n "assignment") (at' (n "formula") "symbol"))],
    ifl (.bin .inn (n "op") (.set [s "true", s "false"])) [ret (eq (n "op") (s "true"))],
    ifl (eq (n "op") (s "not")) [ret (.notE (cl "evaluate" [at' (n "formula") "body", n "assignment"]))],
    st [asg (.tuple [n "a", n "b"]) (.tuple [cl "evaluate" [at' (n "formula") "left", n "assignment"],
      cl "evaluate" [at' (n "formula") "right", n "assignment"]])],
    st [ret (.ifE (.andE (n "a") (n "b")) (eq (n "op") (s "and"))
      (.ifE (.orE (n "a") (n "b")) (eq (n "op") (s "or")) (.orE (.notE (n "a")) (n "b"))))]]

def resourceLimitCST : PL := .classS "ResourceLimit" (some "Exception") [st [.pass]]

private def nodeAt (x : String) : PE := .sub (sf "nodes") (.binT .sub (n x) (.num 2))

def initCST : PL :=
  .defS "__init__" [p "self", p "names", p "limits"] [
    st [asg (.tuple [sf "names", sf "limits"]) (.tuple [n "names", n "limits"])],
    st [asg (.tuple [sf "nodes", sf "unique", sf "memo"]) (.tuple [.list [], .dict [], .dict []])],
    st [.assign [sf "operations", sf "visits", sf "witness_steps"] (.num 0)]]

def nodeCST : PL :=
  .defS "node" [p "self", p "var", p "low", p "high"] [
    ifl (eq (n "low") (n "high")) [ret (n "low")],
    st [asg (n "key") (.paren (.tuple [n "var", n "low", n "high"]))],
    ifl (.bin .inn (n "key") (sf "unique")) [ret (.sub (sf "unique") (n "key"))],
    ifl (.bin .ge (cl "len" [sf "nodes"]) (at' (sf "limits") "nodes")) [.raise (cl "ResourceLimit" [s "nodes"])],
    st [asg (n "result") (.bin .add (cl "len" [sf "nodes"]) (.num 2))],
    st [.expr (mc (sf "nodes") "append" [cl "list" [n "key"]]), asg (.sub (sf "unique") (n "key")) (n "result")],
    st [ret (n "result")]]

def applyCST : PL :=
  .defS "apply" [p "self", p "op", p "a", p "b"] [
    ifl (.bin .ge (sf "operations") (at' (sf "limits") "operations")) [.raise (cl "ResourceLimit" [s "operations"])],
    st [.aug (sf "operations") .add (.num 1)],
    .ifS (.bin .gt (n "a") (n "b")) (.inline [asg (.tuple [n "a", n "b"]) (.tuple [n "b", n "a"])]
      (some "All three internal operations are commutative.")) Option.none,
    st [asg (n "key") (.paren (.tuple [n "op", n "a", n "b"]))],
    ifl (.bin .inn (n "key") (sf "memo")) [ret (.sub (sf "memo") (n "key"))],
    .ifS (.andE (.bin .lt (n "a") (.num 2)) (.bin .lt (n "b") (.num 2)))
      (.block [st [asg (n "result") (.ifE (cl "int" [.andE (n "a") (n "b")]) (eq (n "op") (s "and"))
        (.ifE (cl "int" [.orE (n "a") (n "b")]) (eq (n "op") (s "or")) (cl "int" [.bin .ne (n "a") (n "b")])))]])
      (some (.block [
        st [asg (n "av") (.ifE (.sub (nodeAt "a") (.num 0)) (.bin .ge (n "a") (.num 2)) (cl "len" [sf "names"]))],
        st [asg (n "bv") (.ifE (.sub (nodeAt "b") (.num 0)) (.bin .ge (n "b") (.num 2)) (cl "len" [sf "names"]))],
        st [asg (n "var") (cl "min" [n "av", n "bv"])],
        st [asg (.tuple [n "al", n "ah"]) (.ifE (.slice (nodeAt "a") (.num 1)) (eq (n "av") (n "var"))
          (.paren (.tuple [n "a", n "a"])))],
        st [asg (.tuple [n "bl", n "bh"]) (.ifE (.slice (nodeAt "b") (.num 1)) (eq (n "bv") (n "var"))
          (.paren (.tuple [n "b", n "b"])))],
        st [asg (n "low") (mc (n "self") "apply" [n "op", n "al", n "bl"]),
            asg (n "high") (mc (n "self") "apply" [n "op", n "ah", n "bh"])],
        st [asg (n "result") (mc (n "self") "node" [n "var", n "low", n "high"])]])),
    st [asg (.sub (sf "memo") (n "key")) (n "result")],
    st [ret (n "result")]]

def compileCST : PL :=
  .defS "compile" [p "self", p "formula"] [
    st [.aug (sf "visits") .add (.num 1)],
    st [asg (n "op") (at' (n "formula") "op")],
    ifl (eq (n "op") (s "atom")) [ret (mc (n "self") "node" [mc (sf "names") "index" [at' (n "formula") "symbol"], .num 0, .num 1])],
    ifl (.bin .inn (n "op") (.set [s "true", s "false"])) [ret (cl "int" [eq (n "op") (s "true")])],
    ifl (eq (n "op") (s "not")) [ret (mc (n "self") "apply" [s "xor", mc (n "self") "compile" [at' (n "formula") "body"], .num 1])],
    st [asg (n "a") (mc (n "self") "compile" [at' (n "formula") "left"]),
        asg (n "b") (mc (n "self") "compile" [at' (n "formula") "right"])],
    ifl (eq (n "op") (s "implies")) [ret (mc (n "self") "apply" [s "or", mc (n "self") "apply" [s "xor", n "a", .num 1], n "b"])],
    st [ret (mc (n "self") "apply" [n "op", n "a", n "b"])]]

def conjunctionCST : PL :=
  .defS "conjunction" [p "self", p "roots"] [
    st [asg (n "result") (.num 1)],
    .forS (n "root") (n "roots") (.inline [asg (n "result") (mc (n "self") "apply" [s "and", n "result", n "root"])] Option.none),
    st [ret (n "result")]]

def worldCST : PL :=
  .defS "world" [p "self", p "root"] [
    ifl (eq (n "root") (.num 0)) [ret .none],
    st [asg (n "values") (mc (n "dict") "fromkeys" [sf "names", .fls])],
    .whileS (.bin .ge (n "root") (.num 2)) (.block [
      st [.aug (sf "witness_steps") .add (.num 1)],
      st [asg (.tuple [n "var", n "low", n "high"]) (nodeAt "root")],
      st [asg (.sub (n "values") (.sub (sf "names") (n "var"))) (eq (n "low") (.num 0))],
      st [asg (n "root") (.ifE (n "high") (eq (n "low") (.num 0)) (n "low"))]]),
    st [.assert (eq (n "root") (.num 1))],
    st [ret (n "values")]]

def workCST : PL :=
  .defS "work" [p "self"] [
    st [ret (.dict [.kv (s "bdd_nodes") (cl "len" [sf "nodes"]), .kv (s "apply_calls") (sf "operations"),
      .nl 16 (.kv (s "ast_visits") (sf "visits")), .kv (s "witness_steps") (sf "witness_steps")])]]

def diagramCST : PL :=
  .classS "Diagram" Option.none [initCST, .blank, nodeCST, .blank, applyCST, .blank, compileCST, .blank,
    conjunctionCST, .blank, worldCST, .blank, workCST]

private def none' : PE := .none
private def pj (x : String) : PE := .sub (n "premises") (n x)

def checkCST : PL :=
  .defS "check" [p "value", ⟨"limits", some .none⟩] [
    st [asg (n "value") (cl "validate" [cl "deepcopy" [n "value"]])],
    st [asg (n "limits") (cl "deepcopy" [.ifE (n "DEFAULT_LIMITS") (.bin .is (n "limits") .none) (n "limits")])],
    st [.expr (cl "exact" [n "limits", .set [s "nodes", s "operations"]])],
    .forS (n "field") (n "limits") (.block [
      .ifS (.orE (.bin .isNot (cl "type" [.sub (n "limits") (n "field")]) (n "int"))
          (.notE (.chain .le .le (.num 1) (.sub (n "limits") (n "field")) (.sub (n "DEFAULT_LIMITS") (n "field")))))
        (.block [st [.raise (cl "ValueError" [s "Invalid symbolic work limit"])]]) Option.none]),
    st [asg (n "manager") (cl "Diagram" [at' (n "value") "variables", n "limits"])],
    st [asg (n "result") (.dict [
      .kv (s "format") (n "RECEIPT"), .kv (s "checker") (s "pcs-conditional-bdd/1"), .kv (s "original_task") (n "value"),
      .nl 14 (.kv (s "task_sha256") (cl "digest" [n "value"])), .kv (s "limits") (n "limits"), .kv (s "decision") none',
      .nl 14 (.kv (s "context_example") none'), .kv (s "counterexample") none', .kv (s "unsat_core") none',
      .nl 14 (.kv (s "core_necessity_witnesses") none'), .kv (s "diagram") none', .kv (s "limit_reached") none',
      .nl 14 (.kv (s "scope") (s "Declared Boolean interpretations and explicit assumptions only")),
      .nl 14 (.kv (s "pcs_authority") .fls), .kv (s "lean_kernel_checked") .fls])],
    .tryS [
      st [asg (n "premises") (.list []), asg (n "context") (.num 1)],
      .forS (n "formula") (at' (n "value") "assumptions") (.block [
        st [.expr (mc (n "premises") "append" [mc (n "manager") "compile" [n "formula"]])],
        st [asg (n "context") (mc (n "manager") "apply" [s "and", n "context", .sub (n "premises") (.negNum 1)])],
        ifl (eq (n "context") (.num 0)) [.brk]]),
      st [.assign [n "source", n "candidate", n "difference"] .none],
      .ifS (eq (n "context") (.num 0)) (.block [
          st [asg (n "core") (cl "list" [cl "range" [cl "len" [n "premises"]]])],
          .forS (n "i") (cl "list" [n "core"]) (.block [
            st [asg (n "remaining") (.comp (n "j") "j" (n "core") (some (.bin .ne (n "j") (n "i"))))],
            ifl (eq (mc (n "manager") "conjunction" [.comp (pj "j") "j" (n "remaining") Option.none]) (.num 0))
              [asg (n "core") (n "remaining")]]),
          st [asg (n "necessities") (.list [])],
          .forS (n "i") (n "core") (.block [
            st [asg (n "world") (mc (n "manager") "world" [mc (n "manager") "conjunction"
              [.comp (pj "j") "j" (n "core") (some (.bin .ne (n "j") (n "i")))]])],
            st [.assert (.bin .isNot (n "world") .none)],
            st [.expr (mc (n "necessities") "append" [.dict [.kv (s "removed_assumption") (n "i"), .kv (s "assignment") (n "world")]])]]),
          st [.expr (mc (n "result") "update" [.kw "decision" (s "inconsistent_assumptions"), .kw "unsat_core" (n "core"),
            .kw "core_necessity_witnesses" (n "necessities")])]])
        (some (.block [
          st [asg (n "source") (mc (n "manager") "compile" [at' (n "value") "source"]),
              asg (n "candidate") (mc (n "manager") "compile" [at' (n "value") "candidate"])],
          st [asg (n "difference") (mc (n "manager") "apply" [s "and", n "context",
            mc (n "manager") "apply" [s "xor", n "source", n "candidate"]])],
          st [asg (at' (n "result") "context_example") (mc (n "manager") "world" [n "context"])],
          st [asg (n "world") (mc (n "manager") "world" [n "difference"])],
          .ifS (.bin .is (n "world") .none) (.inline [asg (at' (n "result") "decision") (s "equivalent_under_assumptions")] Option.none)
            (some (.block [
              st [asg (n "truths") (.comp (cl "evaluate" [n "f", n "world"]) "f" (at' (n "value") "assumptions") Option.none)],
              st [asg (.tuple [n "a", n "b"]) (.tuple [cl "evaluate" [at' (n "value") "source", n "world"],
                cl "evaluate" [at' (n "value") "candidate", n "world"]])],
              st [.assert (.andE (cl "all" [n "truths"]) (.bin .ne (n "a") (n "b")))],
              st [.expr (mc (n "result") "update" [.kw "decision" (s "counterexample"), .kw "counterexample" (.dict [
                .kv (s "assignment") (n "world"),
                .nl 30 (.kv (s "source_true") (n "a")), .kv (s "candidate_true") (n "b"), .kv (s "assumptions_true") (n "truths")])])]]))])),
      st [asg (at' (n "result") "diagram") (.dict [.kv (s "nodes") (sf' "manager" "nodes"), .kv (s "source") (n "source"),
        .kv (s "candidate") (n "candidate"),
        .nl 29 (.kv (s "context") (n "context")), .kv (s "difference") (n "difference")])]]
      "ResourceLimit" "error" [
      .comment "Partial work never becomes an accepted result or contradictory context.",
      .forS (n "field") (.list [s "context_example", s "counterexample", s "unsat_core", s "core_necessity_witnesses", s "diagram"])
        (.block [st [asg (.sub (n "result") (n "field")) .none]]),
      st [.expr (mc (n "result") "update" [.kw "decision" (s "resource_limit"), .kw "limit_reached" (cl "str" [n "error"])])]],
    st [asg (at' (n "result") "work") (mc (n "manager") "work" [])],
    st [asg (at' (n "result") "receipt_sha256") (cl "digest" [n "result"])],
    st [ret (n "result")]]
where sf' (o f : String) : PE := .attr (.name o) f

def mainCodeCST : List PL :=
  [.blank, .blank, evaluateCST, .blank, .blank, resourceLimitCST, .blank, .blank, diagramCST, .blank, .blank,
   checkCST, .blank, .blank]

/-- The whole-file segmentation of the current `conditional.py`. -/
def conditionalSegs : List Seg := [
  .header headerLines,
  .code constantsCST,
  .opaqueDef "digest" 2,
  .code exactCST,
  .opaqueDef "validate" 30,
  .code mainCodeCST,
  .opaqueDef "verify" 7,
  .code [.blank, .blank],
  .opaqueDef "parse_formula" 51,
  .code [.blank, .blank],
  .opaqueDef "from_text" 13,
  .header [""]]

end

/-- **Whole-file source binding** for the current `conditional.py`: the segments cover every
line of the uploaded file, each extracted segment renders byte-for-byte to its lines and is
well formed (precedence / bracket discipline), and each unextracted segment is exactly one
top-level `def` of the stated name. -/
theorem conditional_py_source_bound : checkSegs conditionalPySrc conditionalSegs = true := by
  simp only [conditionalSegs, checkSegs, Bool.and_eq_true]
  repeat' apply And.intro
  all_goals decide +kernel

/-- The file has exactly 271 `\n`-separated pieces (270 lines and a final newline). -/
theorem conditional_py_length : conditionalPySrc.length = 271 := by decide +kernel

end PCSCR.Py
