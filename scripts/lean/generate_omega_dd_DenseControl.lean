import PCSDecisionDiagram.Intervention
open PCSOmega PCSDD
def flatRepr {α : Type} [Repr α] (a : α) : String := (reprStr a).replace "\n" " "
abbrev Gen := StateT Nat IO
def emit (s : String) : Gen Unit := IO.println s
def next : Gen Nat := do let k ← get; set (k+1); return k
partial def traceApply (fuel : Nat) (op : BOp) (a0 b0 : Nat) (m0 : Mgr) (input : String) : Gen (Nat × Mgr × String × String) := do
  let k ← next
  let i := s!"ai{k}"; let o := s!"ao{k}"; let p := s!"a{k}"
  emit s!"abbrev {i} : Mgr := {input}"
  if fuel = 0 || m0.ops ≥ DEFAULT_LIMITS.operations then throw (IO.userError "Unexpected exhausted apply")
  let m := {m0 with ops := m0.ops+1}
  let a := min a0 b0; let b := max a0 b0
  match memoLookup m.memo op a b with
  | some r =>
    emit (s!"abbrev {o} : Mgr := " ++ "{" ++ i ++ " with ops := " ++ i ++ ".ops+1}")
    emit s!"theorem {p} : ApplyCertificate 12 DEFAULT_LIMITS {fuel} {flatRepr op} {a0} {b0} {i} {r} {o} := by\n  exact ApplyCertificate.hit (fuel := {fuel-1}) (a0 := {a0}) (b0 := {b0}) (r := {r}) (op := {flatRepr op}) (m := {i}) (by decide) (by rfl)"
    return (r,m,p,o)
  | none =>
    if a<2 && b<2 then
      let r := termOp op a b
      let out := {m with memo := ((op,a,b),r)::m.memo}
      emit (s!"abbrev {o} : Mgr := " ++ "{" ++ i ++ " with ops := " ++ i ++ s!".ops+1, memo := (({flatRepr op},{a},{b}),{r})::" ++ i ++ ".memo}")
      emit s!"theorem {p} : ApplyCertificate 12 DEFAULT_LIMITS {fuel} {flatRepr op} {a0} {b0} {i} {r} {o} := by\n  exact ApplyCertificate.terminal (fuel := {fuel-1}) (a0 := {a0}) (b0 := {b0}) (op := {flatRepr op}) (m := {i}) (by decide) (by rfl) (by decide)"
      return (r,out,p,o)
    else
      let v := min (topVar 12 m.nodes a) (topVar 12 m.nodes b)
      let ca := cof m.nodes v a; let cb := cof m.nodes v b
      let inputLow := "{" ++ i ++ " with ops := " ++ i ++ ".ops+1}"
      let (lo,m1,pl,ol) ← traceApply (fuel-1) op ca.1 cb.1 m inputLow
      let (hi,m2,ph,oh) ← traceApply (fuel-1) op ca.2 cb.2 m1 ol
      let .ok (r,m3) := mkNode DEFAULT_LIMITS m2 v lo hi | throw (IO.userError "Unexpected mkNode limit")
      let n3 := s!"an{k}"
      if m3.nodes.size = m2.nodes.size then emit s!"abbrev {n3} : Mgr := {oh}"
      else emit (s!"abbrev {n3} : Mgr := " ++ "{" ++ oh ++ " with nodes := " ++ oh ++ s!".nodes.push ⟨{v},{lo},{hi}⟩" ++ "}")
      let out := {m3 with memo := ((op,a,b),r)::m3.memo}
      emit (s!"abbrev {o} : Mgr := " ++ "{" ++ n3 ++ s!" with memo := (({flatRepr op},{a},{b}),{r})::" ++ n3 ++ ".memo}")
      emit s!"theorem {p} : ApplyCertificate 12 DEFAULT_LIMITS {fuel} {flatRepr op} {a0} {b0} {i} {r} {o} := by\n  exact ApplyCertificate.branch (fuel := {fuel-1}) (a0 := {a0}) (b0 := {b0}) (lo := {lo}) (hi := {hi}) (r := {r}) (op := {flatRepr op}) (m := {i}) (m1 := {ol}) (m2 := {oh}) (m3 := {n3}) (by decide) (by rfl) (by decide) {pl} {ph} (by rfl)"
      return (r,out,p,o)
partial def trace (f : BForm 12) (m : Mgr) : Gen (Nat × Mgr × String × String) := do
  let k ← next; let p := s!"c{k}"; let o := s!"o{k}"
  emit s!"abbrev f{k} : BForm 12 := {flatRepr f}\nabbrev i{k} : Mgr := {flatRepr m}"
  match f with
  | .atom _ =>
    let .ok (r,out) := compile 12 DEFAULT_LIMITS f m | throw (IO.userError "Atom compile failed")
    emit s!"abbrev {o} : Mgr := {flatRepr out}"
    emit s!"theorem {p} : CompileCertificate 12 DEFAULT_LIMITS f{k} i{k} {r} {o} := by\n  exact CompileCertificate.atom (by rfl)"
    return (r,out,p,o)
  | .ff =>
    let out := {m with visits := m.visits+1}
    emit (s!"abbrev {o} : Mgr := " ++ "{" ++ s!"i{k} with visits := i{k}.visits+1" ++ "}")
    emit s!"theorem {p} : CompileCertificate 12 DEFAULT_LIMITS f{k} i{k} 0 {o} := by\n  exact CompileCertificate.ff _"
    return (0,out,p,o)
  | .and a b | .or a b =>
    let (x,ma,pa,oa) ← trace a {m with visits := m.visits+1}
    let (y,mb,pb,ob) ← trace b ma
    let op := match f with | .and _ _ => BOp.and | _ => BOp.or
    let (r,out,ap,ao) ← traceApply 25 op x y mb ob
    emit s!"abbrev {o} : Mgr := {ao}"
    let ctor := if op == BOp.and then "and" else "or"
    emit s!"theorem {p} : CompileCertificate 12 DEFAULT_LIMITS f{k} i{k} {r} {o} := by\n  exact CompileCertificate.{ctor} (fuel := 25) (m := i{k}) (ma := {oa}) (mb := {ob}) (out := {o}) (x := {x}) (y := {y}) (r := {r}) {pa} {pb} (ApplyCertificate.sound (m := {ob}) (out := {ao}) {ap}) (by decide)"
    return (r,out,p,o)
  | _ => throw (IO.userError "Outside fixed dense-control generator")
def vr (i : Nat) : BForm 12 := .atom ⟨i%12,Nat.mod_lt _ (by decide)⟩
def bal (leaf : Nat → BForm 12) (op : BForm 12 → BForm 12 → BForm 12) : Nat → Nat → Nat → BForm 12
 | 0, lo, _ => leaf lo
 | f+1, lo, len => if len≤1 then leaf lo else op (bal leaf op f lo (len/2)) (bal leaf op f (lo+len/2) (len-len/2))
def main : IO Unit := do
 discard <| (do
  emit "import PCSReferenceCertificates.Dense\nimport PCSReferenceCertificates.Apply\nopen PCSOmega PCSDD\nnamespace StagedDense\nset_option maxRecDepth 100000\nset_option maxHeartbeats 0"
  let fs := bal (fun i => BForm.and (vr i) (vr (i+6))) .or 4 0 6
  let (s,ms,ps,_) ← trace fs Mgr.empty
  let (c,mc,pc,oc) ← trace .ff ms
  let (x,mx,px,ox) ← traceApply 25 .xor s c mc oc
  let (d,_,pd,od) ← traceApply 25 .and 1 x mx ox
  emit s!"abbrev task : CTask 12 := ⟨{flatRepr fs},.ff,[]⟩"
  emit (s!"theorem pipe : pipeline task DEFAULT_LIMITS = .ok (.decided 1 {s} {c} {d}, " ++ "{" ++ od ++ " with wsteps := " ++ od ++ ".wsteps + witSteps 12 " ++ od ++ ".nodes 0 1 + witSteps 12 " ++ od ++ s!".nodes 0 {d}" ++ "}) := by")
  emit s!"  exact pipeline_from_certificates (by rfl) {ps} {pc} (ApplyCertificate.sound {px}) (ApplyCertificate.sound {pd}) (by decide)"
  emit "theorem result : (check task DEFAULT_LIMITS).decision = .counterexample := by\n  exact counterexample_from_pipeline pipe (by decide)\n#print axioms result\nend StagedDense"
 ).run 0
