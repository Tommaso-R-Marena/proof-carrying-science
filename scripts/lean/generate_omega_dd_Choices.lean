import PCSDecisionDiagram.Intervention
open PCSOmega PCSDD
def flatRepr {α : Type} [Repr α] (a : α) : String := (reprStr a).replace "\n" " "
abbrev Gen := StateT Nat IO

def emit (s : String) : Gen Unit := do IO.println (s.replace "def " "abbrev ")

def next : Gen Nat := do let k ← get; set (k+1); return k

partial def trace (f : BForm 24) (m : Mgr) : Gen (Nat × Mgr × String) := do
  let k ← next
  let mut subs : List String := []
  match f with
  | .not a =>
    let (_,_,h) ← trace a {m with visits := m.visits + 1}
    subs := [h]
  | .and a b | .or a b | .imp a b =>
    let (_,ma,ha) ← trace a {m with visits := m.visits + 1}
    let (_,_,hb) ← trace b ma
    subs := [ha,hb]
  | _ => pure ()
  match compile 24 DEFAULT_LIMITS f m with
  | .error _ => throw (IO.userError "Unexpected compile limit in fixed control")
  | .ok (r,mout) =>
    let h := s!"c{k}"
    emit s!"def f{k} : BForm 24 := {flatRepr f}\ndef i{k} : Mgr := {flatRepr m}\ndef o{k} : Mgr := {flatRepr mout}"
    emit s!"theorem {h} : CompileCertificate 24 DEFAULT_LIMITS f{k} i{k} {r} o{k} := by"
    match f with
    | .atom _ => emit "  exact CompileCertificate.atom (by rfl)"
    | .tt => emit "  exact CompileCertificate.tt _"
    | .ff => emit "  exact CompileCertificate.ff _"
    | .not _ => emit s!"  exact CompileCertificate.not (fuel := 25) {subs[0]!} (by rfl) (by decide)"
    | .and _ _ => emit s!"  exact CompileCertificate.and (fuel := 25) {subs[0]!} {subs[1]!} (by rfl) (by decide)"
    | .or _ _ => emit s!"  exact CompileCertificate.or (fuel := 25) {subs[0]!} {subs[1]!} (by rfl) (by decide)"
    | .imp _ _ => throw (IO.userError "Implication is outside this fixed-control generator")
    return (r,mout,h)

def vr (i : Nat) : BForm 24 := .atom ⟨i%24, Nat.mod_lt _ (by decide)⟩
def bal (leaf : Nat → BForm 24) (op : BForm 24 → BForm 24 → BForm 24) : Nat → Nat → Nat → BForm 24
 | 0, lo, _ => leaf lo
 | f+1, lo, len => if len≤1 then leaf lo else op (bal leaf op f lo (len/2)) (bal leaf op f (lo+len/2) (len-len/2))

def main : IO Unit := do
  discard <| (do
    emit "import PCSDecisionDiagram.Intervention\nimport PCSReferenceCertificates.Plan\nopen PCSOmega PCSDD\nnamespace StagedChoices\nset_option maxRecDepth 100000\nset_option maxHeartbeats 0"
    let fs := bal (fun k => BForm.or (vr (2*k)) (vr (2*k+1))) .and 5 0 12
    let fc : BForm 24 := .ff
    let (s,ms,hs) ← trace fs Mgr.empty
    let (c,mc,hc) ← trace fc ms
    let .ok (x,mx) := apply 24 DEFAULT_LIMITS 25 .xor s c mc | throw (IO.userError "xor failed")
    let .ok (d,md) := apply 24 DEFAULT_LIMITS 25 .and 1 x mx | throw (IO.userError "and failed")
    emit s!"def mx : Mgr := {flatRepr mx}\ndef md : Mgr := {flatRepr md}"
    let oc := "o" ++ (hc.drop 1).toString
    emit s!"theorem hx : apply 24 DEFAULT_LIMITS 25 .xor {s} {c} {oc} = .ok ({x},mx) := by rfl"
    emit s!"theorem ha : apply 24 DEFAULT_LIMITS 25 .and 1 {x} mx = .ok ({d},md) := by rfl"
    emit s!"def task : CTask 24 := ⟨{flatRepr fs},{flatRepr fc},[]⟩"
    emit (s!"theorem pipe : pipeline task DEFAULT_LIMITS = .ok (.decided 1 {s} {c} {d}, " ++ "{md with wsteps := md.wsteps + witSteps 24 md.nodes 0 1 + witSteps 24 md.nodes 0 " ++ s!"{d}" ++ "}) := by")
    emit s!"  exact pipeline_from_certificates (by rfl) {hs} {hc} hx ha (by decide)"
    let itask : ITask 24 := ⟨⟨fs,fc,[]⟩,List.replicate 24 false,List.replicate 24 1,[]⟩
    let .ok receipt := plan itask DEFAULT_LIMITS | throw (IO.userError "plan failed")
    emit "def itask : ITask 24 := ⟨task,List.replicate 24 false,List.replicate 24 1,[]⟩"
    emit s!"def receipt : IReceipt 24 := {flatRepr receipt}"
    let cr := check (⟨fs,fc,[]⟩ : CTask 24) DEFAULT_LIMITS
    emit s!"def checked : CReceipt 24 := {flatRepr cr}"
    emit "theorem result : plan itask DEFAULT_LIMITS = .ok receipt := by\n  exact plan_from_pipeline pipe (by rfl)\n#print axioms result"
    emit "end StagedChoices"
  ).run 0
