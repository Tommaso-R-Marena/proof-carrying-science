import Lean
import Lean.Replay
import PCS.V2.TranslationV3Json
import PCS.V2.LeanSyntaxV3

/-! # PCS v3 elaboration bridge checker (executable, meta level — NOT a Lean theorem)

Usage (from the project root, after `lake build`):

    lake env lean --run tools/CheckElaborationV3.lean fingerprint <authority-v3.json> [--env <Env.lean>]
    lake env lean --run tools/CheckElaborationV3.lean check <authority-v3.json> <request-v3.json> [--env <Env.lean>]
    lake env lean --run tools/CheckElaborationV3.lean prove <authority-v3.json> <request-v3.json> <Proof.lean> [--env <Env.lean>]

`<Env.lean>` is a Lean source file whose processing defines the environment (default: exactly the
three import lines `import PCS.Examples.Agent / Repro / Bio`).  Adversarial environments (extra
macros, notations, shadowing declarations) are supplied this way in the test suite.

## `fingerprint`

Prints `sha256:<hex>` over a canonical text consisting of: the Lean version string, the imported
module names, the SHA-256 of the full environment source text, and — for every registry sort and
symbol, sorted by Lean name — the constant's name, kind, universe parameters, printed type and the
SHA-256 of its printed value (for definitions/opaques).  Changing any registered definition, its
type, the toolchain, the import set or any extra command in the environment source changes the
fingerprint.

## `check`

Decodes the authority and request with the **same verified decoders** the authority uses
(`decAuthorityConfigV3`, `decRequestV3` on canonical bytes) and fails closed with one code:

* `MALFORMED_INPUT`          — either file does not decode canonically;
* `ENV_LOAD_FAILED`          — the environment source did not process without errors;
* `ENV_FINGERPRINT_MISMATCH` — the computed fingerprint differs from `context.env_fingerprint`;
* `NOT_GROUNDED`             — a registry entry is missing, an axiom/theorem, has universe
                               parameters, or has a signature different from the registry's;
* `GATE_FAILED`              — `leanSyntaxSafeB` (the proved anti-capture gate) rejects the claim
                               or the claim is not closed;
* `SOURCE_NOT_CANONICAL`     — `lean_source` is not `renderClaimLean registry claim`;
* `PARSE_ERROR` / `ELABORATION_ERROR` — Lean cannot parse/elaborate the text as a `Prop`;
* `STRUCTURE_MISMATCH`       — Lean elaborated the text to an expression **different** from the
                               expression built directly from the syntax tree
                               `PCS.V2.Semantic.LeanSyntax.readClaim registry claim`
                               (compared with `Expr.eqv`, i.e. up to binder names only);
* `UNSUPPORTED`              — the claim contains an unsupported construct.

On success it prints `ELABORATION_MATCHES <fingerprint>` and exits 0.  This checks, for one
request and one environment, the instance of the trust condition `LeanFrontendFaithful` used by
`pcs_v3_certified_wire_assurance`: Lean reads the printed text as exactly the formula
`LDecl.denote` describes.  Successful elaboration is **not** a proof of the proposition; a proof
is the separate kernel-check record.

## `prove`

Everything `check` does, then: processes `<Env.lean>` followed by the (untrusted) commands of
`<Proof.lean>` (which may not contain `import`), and fails closed with

* `DECL_NOT_FOUND` / `NOT_A_THEOREM` — `decl_name` is missing or not a `theorem`;
* `STATEMENT_MISMATCH` — the theorem's type is not `Expr.eqv` to the expression built from
  `readClaim` (so notation tricks in the proof file cannot change the proved statement);
* `KERNEL_REPLAY_FAILED` — re-adding **every** declaration the proof file created to the clean
  base environment with the Lean kernel (`Lean.Environment.replay`) fails; this defeats e.g.
  `set_option debug.skipKernelTC` in the proof file;
* `AXIOM_NOT_CLAIMED` — the theorem depends (in the replayed environment) on an axiom that is not
  in the request's `proof_axioms` (`sorryAx`, a declared `axiom`, `Lean.ofReduceBool`, …);
* `AXIOM_NOT_ALLOWED` — a claimed axiom is not in the authority's `allowed_axioms`.

On success it prints `KERNEL_CHECK_PASSED <fingerprint> <axioms>` and exits 0.  A *reference
proof issuer* (`python/pcs_semantic/issuer_v3.py`) signs a kernel-check record only after this
succeeds; the signature then attests that *this tool, run by the key holder,* passed — it is
evidence of a kernel check only to the extent that the key holder is honest and runs this tool.

**Trust boundary.**  Trusts the Lean frontend (`.olean` loading, parser, elaborator), the
compiled interpreter running this file, and the small `LDecl → Expr` translation below.
-/

open Lean Elab Meta
open PCS.V2.Json PCS.V2.Canonical PCS.V2.Semantic PCS.V2.Semantic.V3 PCS.V2.Semantic.LeanSyntax

def defaultEnvSource : String :=
  "import PCS.Examples.Agent\nimport PCS.Examples.Repro\nimport PCS.Examples.Bio\n"

def kindOf : ConstantInfo → String
  | .axiomInfo _ => "axiom"
  | .defnInfo _ => "def"
  | .thmInfo _ => "theorem"
  | .opaqueInfo _ => "opaque"
  | .quotInfo _ => "quot"
  | .inductInfo _ => "inductive"
  | .ctorInfo _ => "constructor"
  | .recInfo _ => "recursor"

def kindAllowed (k : String) : Bool := k == "def" || k == "opaque" || k == "inductive"

def sha (s : String) : String := PCS.V2.SHA256.sha256Hex s.toUTF8

def registryNames (R : Registry) : List String :=
  (R.sorts.map (·.leanType) ++ R.symbols.map (·.leanName)).mergeSort (· ≤ ·)

/-- The environment fingerprint (see the module documentation). -/
def fingerprintOf (env : Environment) (envSrc : String) (R : Registry) : String :=
  let mods := env.header.moduleNames.toList.map toString
  let entries := (registryNames R).map fun n =>
    match env.find? n.toName with
    | none => s!"{n}|missing"
    | some ci =>
      let v := match ci.value? (allowOpaque := true) with
        | some e => sha (toString e)
        | none => "-"
      s!"{n}|{kindOf ci}|{ci.levelParams}|{ci.type}|{v}"
  let text := String.intercalate "\n"
    ([s!"lean {Lean.versionString}", s!"modules {mods}", s!"envsrc {sha envSrc}"] ++ entries)
  "sha256:" ++ sha text

/-- Peel non-dependent arrows. -/
partial def arrows : Expr → Option (List Expr × Expr)
  | .forallE _ d b _ =>
    if b.hasLooseBVars then none
    else (arrows b).map (fun (ds, r) => (d :: ds, r))
  | e => some ([], e)

/-- Grounding of every registry entry (signature, kind, no universe parameters, injective). -/
def groundingFailures (env : Environment) (R : Registry) : List String := Id.run do
  let mut out : List String := []
  for e in R.sorts do
    match env.find? e.leanType.toName with
    | none => out := out ++ [s!"sort {e.id}: {e.leanType} missing"]
    | some ci =>
      unless ci.type == .sort (.succ .zero) && kindAllowed (kindOf ci) && ci.levelParams.isEmpty do
        out := out ++ [s!"sort {e.id}: {e.leanType} : {ci.type} ({kindOf ci})"]
  let sortTy : SortId → Option Expr := fun s =>
    (R.resolveSort s).map (fun se => .const se.leanType.toName [])
  let mut seen : List String := []
  for e in R.symbols do
    if seen.contains e.leanName then
      out := out ++ [s!"symbol {e.id}: {e.leanName} grounds more than one entry"]
    seen := e.leanName :: seen
    let (args, res) : List SortId × Option SortId := match e.kind with
      | .pred args => (args, none)
      | .fn args r => (args, some r)
    let expArgs := args.mapM sortTy
    let expRes : Option Expr := match res with
      | none => some (.sort .zero)
      | some r => sortTy r
    match env.find? e.leanName.toName with
    | none => out := out ++ [s!"symbol {e.id}: {e.leanName} missing"]
    | some ci =>
      let good := match arrows ci.type, expArgs, expRes with
        | some (ds, r), some eds, some er => ds == eds && r == er
        | _, _, _ => false
      unless good && kindAllowed (kindOf ci) && ci.levelParams.isEmpty do
        out := out ++ [s!"symbol {e.id}: {e.leanName} : {ci.type} ({kindOf ci})"]
  return out

/-! ## The trusted `LDecl → Expr` translation -/

def lookupBound (bs : List (String × Expr)) (n : String) : Option Expr :=
  (bs.find? (·.1 == n)).map (·.2)

mutual
partial def termExpr (bs : List (String × Expr)) : LTerm → MetaM Expr
  | .ident n => pure ((lookupBound bs n).getD (.const n.toName []))
  | .app h args => do
    let as ← args.mapM (termExpr bs)
    pure (mkAppN (.const h.toName []) as.toArray)
end

partial def propExpr (bs : List (String × Expr)) : LProp → MetaM Expr
  | .tt => pure (mkConst ``True)
  | .ff => pure (mkConst ``False)
  | .atom h args => do
    let as ← args.mapM (termExpr bs)
    pure (mkAppN (.const h.toName []) as.toArray)
  | .eq a b => do mkEq (← termExpr bs a) (← termExpr bs b)
  | .ne a b => do mkAppM ``Ne #[← termExpr bs a, ← termExpr bs b]
  | .not p => do pure (mkNot (← propExpr bs p))
  | .and p q => do pure (mkAnd (← propExpr bs p) (← propExpr bs q))
  | .or p q => do pure (mkOr (← propExpr bs p) (← propExpr bs q))
  | .imp p q => do mkArrow (← propExpr bs p) (← propExpr bs q)
  | .all x ty p =>
    withLocalDeclD x.toName (.const ty.toName []) fun fv => do
      mkForallFVars #[fv] (← propExpr ((x, fv) :: bs) p)
  | .ex x ty p =>
    withLocalDeclD x.toName (.const ty.toName []) fun fv => do
      mkAppM ``Exists #[← mkLambdaFVars #[fv] (← propExpr ((x, fv) :: bs) p)]
  | .unsupported t => throwError "unsupported construct {t}"

def declBody (bs : List (String × Expr)) (d : LDecl) : MetaM Expr := do
  let mut acc ← propExpr bs d.concl
  for h in d.hyps.reverse do
    acc ← mkArrow (← propExpr bs h) acc
  return acc

partial def declExpr (bs : List (String × Expr)) (d : LDecl) :
    List (String × String) → MetaM Expr
  | [] => declBody bs d
  | (x, ty) :: rest =>
    withLocalDeclD x.toName (.const ty.toName []) fun fv => do
      mkForallFVars #[fv] (← declExpr ((x, fv) :: bs) d rest)

/-! ## Running Lean -/

def runMeta {α : Type} (env : Environment) (x : MetaM α) : IO (Except String α) := do
  let ctx : Core.Context := { fileName := "<pcs-check-elaboration>", fileMap := default,
                              maxHeartbeats := 2000000 }
  let st : Core.State := { env }
  try
    let a ← (x.run' {} {}).toIO' ctx st
    pure (.ok a)
  catch e => pure (.error (toString e))

/-- Parse and elaborate `src` as a `Prop` at the root namespace with no `open`s. -/
def elabProp (env : Environment) (src : String) : IO (Except (String × String) Expr) := do
  match Parser.runParserCategory env `term src with
  | .error msg => pure (.error ("PARSE_ERROR", msg))
  | .ok stx =>
    let r ← runMeta env do
      let e ← (Term.elabTermAndSynthesize stx (some (mkSort .zero))).run'
      let e ← instantiateMVars e
      let ty ← inferType e
      let ty ← whnf ty
      pure (e, ty)
    match r with
    | .error msg => pure (.error ("ELABORATION_ERROR", msg))
    | .ok (e, ty) =>
      if e.hasMVar || e.hasSyntheticSorry || e.hasSorry then
        pure (.error ("ELABORATION_ERROR", s!"incomplete elaboration: {e}"))
      else if ty != mkSort .zero then
        pure (.error ("ELABORATION_ERROR", s!"not a proposition: {ty}"))
      else pure (.ok e)

def loadEnv (envSrc : String) : IO (Option Environment) := do
  initSearchPath (← findSysroot)
  Lean.Elab.runFrontend envSrc {} "<pcs-env>" `PCSCheckEnv

def decodeFile {α : Type} (path : String) (dec : JVal → Option α) : IO (Option α) := do
  let raw ← IO.FS.readBinFile path
  pure ((parseCanonicalBytes PCS.V2.Semantic.maxInputBytes raw).bind dec)

/-- Print exactly one final line `CODE message` (newlines in `message` are flattened). -/
def fail (code msg : String) : IO UInt32 := do
  IO.println s!"{code} {(msg.replace "\n" " ").replace "\r" " "}"
  return 1

def splitEnvArg : List String → List String × Option String
  | [] => ([], none)
  | "--env" :: p :: rest => let (a, _) := splitEnvArg rest; (a, some p)
  | x :: rest => let (a, e) := splitEnvArg rest; (x :: a, e)

/-- The `check` pipeline; returns the fingerprint and the expected expression. -/
def checkCore (env : Environment) (envSrc : String) (cfg : AuthorityConfigV3) (r : RequestV3) :
    IO (Except (String × String) (String × Expr)) := do
  let R := cfg.registry
  let fp := fingerprintOf env envSrc R
  if fp != cfg.context.envFingerprint then
    return .error ("ENV_FINGERPRINT_MISMATCH", s!"computed {fp} bound {cfg.context.envFingerprint}")
  let gf := groundingFailures env R
  unless gf.isEmpty do
    return .error ("NOT_GROUNDED", String.intercalate "; " gf)
  let c := r.core.base.candidate
  unless leanSyntaxSafeB R c.claim && c.claim.freeVars.isEmpty do
    return .error ("GATE_FAILED", "leanSyntaxSafeB rejects the claim or it is not closed")
  unless c.leanSource == renderClaimLean R c.claim do
    return .error ("SOURCE_NOT_CANONICAL", "lean_source is not the canonical rendering")
  let d := readClaim R c.claim
  let expected ← match ← runMeta env (declExpr [] d d.binders) with
    | .ok e => pure e
    | .error msg => return .error ("UNSUPPORTED", msg)
  match ← elabProp env c.leanSource with
  | .error e => return .error e
  | .ok e =>
    if e.eqv expected then return .ok (fp, expected)
    else return .error ("STRUCTURE_MISMATCH", s!"elaborated {e} expected {expected}")

def main (args : List String) : IO UInt32 := do
  let (pos, envPath) := splitEnvArg args
  let envSrc ← match envPath with
    | some p => IO.FS.readFile p
    | none => pure defaultEnvSource
  match pos with
  | ["fingerprint", aPath] =>
    let some cfg ← decodeFile aPath decAuthorityConfigV3 | fail "MALFORMED_INPUT" aPath
    let some env ← loadEnv envSrc | fail "ENV_LOAD_FAILED" (envPath.getD "<default>")
    IO.println (fingerprintOf env envSrc cfg.registry)
    return 0
  | ["check", aPath, rPath] =>
    let some cfg ← decodeFile aPath decAuthorityConfigV3 | fail "MALFORMED_INPUT" aPath
    let some r ← decodeFile rPath decRequestV3 | fail "MALFORMED_INPUT" rPath
    let some env ← loadEnv envSrc | fail "ENV_LOAD_FAILED" (envPath.getD "<default>")
    match ← checkCore env envSrc cfg r with
    | .error (code, msg) => fail code msg
    | .ok (fp, _) =>
      IO.println s!"ELABORATION_MATCHES {fp}"
      return 0
  | ["prove", aPath, rPath, pPath] =>
    let some cfg ← decodeFile aPath decAuthorityConfigV3 | fail "MALFORMED_INPUT" aPath
    let some r ← decodeFile rPath decRequestV3 | fail "MALFORMED_INPUT" rPath
    let proofSrc ← IO.FS.readFile pPath
    let some env ← loadEnv envSrc | fail "ENV_LOAD_FAILED" (envPath.getD "<default>")
    match ← checkCore env envSrc cfg r with
    | .error (code, msg) => fail code msg
    | .ok (fp, expected) =>
      let c := r.core.base.candidate
      -- the `section` command ends the header, so an `import` in the proof file is an error
      let some penv ← Lean.Elab.runFrontend
          (envSrc ++ "\nsection PCSProofFile\n" ++ proofSrc ++ "\n") {} "<pcs-proof>" `PCSCheckEnv
        | fail "ENV_LOAD_FAILED" "proof file did not process without errors"
      unless penv.header.moduleNames == env.header.moduleNames do
        return (← fail "ENV_LOAD_FAILED" "proof file changed the import set")
      let declN := c.declName.toName
      let some ci := penv.find? declN | fail "DECL_NOT_FOUND" c.declName
      let .thmInfo _ := ci | fail "NOT_A_THEOREM" s!"{c.declName} is a {kindOf ci}"
      unless ci.levelParams.isEmpty && ci.type.eqv expected do
        return (← fail "STATEMENT_MISMATCH" s!"theorem type {ci.type} expected {expected}")
      let newConsts : Std.HashMap Name ConstantInfo :=
        penv.constants.map₂.foldl (fun m n ci => m.insert n ci) {}
      let replayed ← try
          let e ← env.replay newConsts
          pure (some e)
        catch ex => do
          IO.println s!"replay error: {(toString ex).replace "\n" " "}"
          pure none
      let some renv := replayed | fail "KERNEL_REPLAY_FAILED" "the kernel rejected a declaration"
      let some rci := renv.find? declN | fail "KERNEL_REPLAY_FAILED" "theorem missing after replay"
      unless rci.type.eqv expected do
        return (← fail "STATEMENT_MISMATCH" "replayed type differs")
      let axs ← runMeta renv (collectAxioms declN)
      let axs ← match axs with
        | .ok a => pure (a.toList.map toString)
        | .error msg => return (← fail "KERNEL_REPLAY_FAILED" msg)
      for ax in axs do
        unless r.proofAxioms.contains ax do
          return (← fail "AXIOM_NOT_CLAIMED" ax)
      for ax in r.proofAxioms do
        unless cfg.allowedAxioms.contains ax do
          return (← fail "AXIOM_NOT_ALLOWED" ax)
      IO.println s!"KERNEL_CHECK_PASSED {fp} {axs}"
      return 0
  | _ =>
    IO.eprintln "usage: CheckElaborationV3 (fingerprint <authority> | check <authority> <request>) [--env <Env.lean>]"
    return 2
