import Lean

/-! # Grounding bridge: registry entries against the actual Lean environment

Usage (from the project root, after `lake build`):

    lake env lean --run tools/CheckRegistryGrounding.lean <authority.json> [Module ...]

(default modules: `PCS.Examples.Agent PCS.Examples.Repro PCS.Examples.Bio`).

For the registry inside an authority configuration, this tool imports the given modules into
a real Lean environment (the `.olean` files produced by `lake build`, i.e. declarations that
the Lean kernel has checked) and verifies, for every entry:

* **sorts**: `lean_type` names an existing constant whose type is exactly `Type`;
* **predicates** with argument sorts `s₁ … sₖ`: `lean_name` names an existing constant whose
  type is exactly the non-dependent arrow `T₁ → … → Tₖ → Prop`, where `Tᵢ` is the constant
  named by the `lean_type` of `sᵢ`;
* **functions** `s₁ … sₖ → r`: likewise with result `T_r`;
* the declaration is a definition, opaque constant or inductive type — **never an `axiom`
  or a theorem** (an axiom-backed symbol would smuggle an assumption into the registry);
* no two registry entries are grounded in the same Lean declaration.

It prints one canonical line per entry and exits with status 0 iff every entry is grounded.

**Trust boundary.**  This is executable meta-level checking, not a Lean theorem: it trusts the
Lean frontend's `.olean` loading and this tool's code.  It establishes that each registered
symbol is a real, kernel-checked declaration with exactly the registered signature.  It does
**not** establish that the declaration *means* what the registry's prose says (two
declarations with the same type — e.g. `inSite` and `inSiteLegacy` — are indistinguishable
here; see `registry_name_does_not_fix_meaning`). -/

open Lean

def jStr (j : Json) (k : String) : Option String :=
  (j.getObjValAs? String k).toOption

def jStrs (j : Json) (k : String) : List String :=
  match j.getObjValAs? (Array String) k with
  | .ok a => a.toList
  | .error _ => []

/-- Peel non-dependent arrows. -/
partial def arrows : Expr → Option (List Expr × Expr)
  | .forallE _ d b _ =>
    if b.hasLooseBVars then none
    else (arrows b).map (fun (ds, r) => (d :: ds, r))
  | e => some ([], e)

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

def main (args : List String) : IO UInt32 := do
  let some path := args.head? | IO.eprintln "usage: CheckRegistryGrounding <authority.json> [Module ...]"; return 2
  let mods := if args.tail.isEmpty then ["PCS.Examples.Agent", "PCS.Examples.Repro", "PCS.Examples.Bio"]
    else args.tail
  initSearchPath (← findSysroot)
  let env ← importModules (mods.toArray.map fun m => { module := m.toName }) {}
  let raw ← IO.FS.readFile path
  let some reg := (Json.parse raw).toOption.bind (fun j => (j.getObjVal? "registry").toOption)
    | IO.println "MALFORMED: no registry"; return 1
  let sorts := match reg.getObjValAs? (Array Json) "sorts" with | .ok a => a.toList | .error _ => []
  let syms := match reg.getObjValAs? (Array Json) "symbols" with | .ok a => a.toList | .error _ => []
  let sortType : String → Option Name := fun s =>
    (sorts.find? (fun e => jStr e "id" == some s)).bind (fun e => (jStr e "lean_type").map String.toName)
  let mut ok := true
  for e in sorts do
    let id := (jStr e "id").getD "?"
    let n := ((jStr e "lean_type").getD "").toName
    match env.find? n with
    | none => IO.println s!"FAIL sort {id}: {n} is not a declaration"; ok := false
    | some ci =>
      if ci.type == .sort (.succ .zero) && kindAllowed (kindOf ci) then
        IO.println s!"ok   sort {id} -> {n} : Type ({kindOf ci})"
      else
        IO.println s!"FAIL sort {id}: {n} has type {ci.type} ({kindOf ci})"; ok := false
  let mut seen : List Name := []
  for e in syms do
    let id := (jStr e "id").getD "?"
    let n := ((jStr e "lean_name").getD "").toName
    if seen.contains n then
      IO.println s!"FAIL symbol {id}: {n} grounds more than one registry entry"; ok := false
    seen := n :: seen
    let argTys := (jStrs e "args").map sortType
    let res : Option (Option Name) :=
      if jStr e "kind" == some "pred" then some none
      else (jStr e "result").map (fun r => sortType r |>.getD Name.anonymous)
    match env.find? n with
    | none => IO.println s!"FAIL symbol {id}: {n} is not a declaration"; ok := false
    | some ci =>
      let k := kindOf ci
      let expectedArgs : Option (List Expr) :=
        argTys.mapM (fun o => o.map (fun t => Expr.const t []))
      let expectedRes : Option Expr := match res with
        | some none => some (.sort .zero)
        | some (some t) => some (.const t [])
        | none => none
      let good := match arrows ci.type, expectedArgs, expectedRes with
        | some (ds, r), some eds, some er => ds == eds && r == er
        | _, _, _ => false
      if good && kindAllowed k then
        IO.println s!"ok   symbol {id} -> {n} : {ci.type} ({k})"
      else
        IO.println s!"FAIL symbol {id}: {n} has type {ci.type} ({k}); registry signature does not match"
        ok := false
  IO.println (if ok then "GROUNDED" else "NOT_GROUNDED")
  return (if ok then 0 else 1)
