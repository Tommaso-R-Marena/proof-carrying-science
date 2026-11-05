import PCSReferenceCertificates.FuelStable
import PCSDecisionDiagram.Conditional
namespace PCSDD
open PCSOmega

inductive CompileCertificate (n : Nat) (lim : Limits) : BForm n → Mgr → Nat → Mgr → Prop where
  | atom {i : Fin n} {m : Mgr} {r : Nat} {out : Mgr}
      (h : mkNode lim {m with visits := m.visits+1} i.val 0 1 = .ok (r,out)) :
      CompileCertificate n lim (.atom i) m r out
  | tt (m : Mgr) : CompileCertificate n lim .tt m 1 {m with visits := m.visits+1}
  | ff (m : Mgr) : CompileCertificate n lim .ff m 0 {m with visits := m.visits+1}
  | not {f : BForm n} {m mid out : Mgr} {x r fuel : Nat}
      (cf : CompileCertificate n lim f {m with visits := m.visits+1} x mid)
      (h : apply n lim fuel .xor x 1 mid = .ok (r,out)) (bound : fuel ≤ applyFuel lim) :
      CompileCertificate n lim (.not f) m r out
  | and {f g : BForm n} {m ma mb out : Mgr} {x y r fuel : Nat}
      (cf : CompileCertificate n lim f {m with visits := m.visits+1} x ma)
      (cg : CompileCertificate n lim g ma y mb)
      (h : apply n lim fuel .and x y mb = .ok (r,out)) (bound : fuel ≤ applyFuel lim) :
      CompileCertificate n lim (.and f g) m r out
  | or {f g : BForm n} {m ma mb out : Mgr} {x y r fuel : Nat}
      (cf : CompileCertificate n lim f {m with visits := m.visits+1} x ma)
      (cg : CompileCertificate n lim g ma y mb)
      (h : apply n lim fuel .or x y mb = .ok (r,out)) (bound : fuel ≤ applyFuel lim) :
      CompileCertificate n lim (.or f g) m r out

theorem CompileCertificate.sound {n : Nat} {lim : Limits} {f : BForm n} {m out : Mgr} {r : Nat}
    (c : CompileCertificate n lim f m r out) : compile n lim f m = .ok (r,out) := by
  induction c with
  | atom h => exact h
  | tt m => rfl
  | ff m => rfl
  | not cf ha hb ih =>
    rw [compile, ih]
    dsimp only
    exact apply_ok_target ha hb
  | and cf cg ha hb ihf ihg =>
    rw [compile, ihf]
    dsimp only
    rw [ihg]
    dsimp only
    exact apply_ok_target ha hb
  | or cf cg ha hb ihf ihg =>
    rw [compile, ihf]
    dsimp only
    rw [ihg]
    dsimp only
    exact apply_ok_target ha hb

theorem pipeline_from_certificates {n : Nat} {lim : Limits} {t : CTask n}
    {s c x d fuel : Nat} {ms mc mx md : Mgr}
    (empty : t.assumptions = [])
    (cs : CompileCertificate n lim t.source Mgr.empty s ms)
    (cc : CompileCertificate n lim t.candidate ms c mc)
    (hx : apply n lim fuel .xor s c mc = .ok (x,mx))
    (ha : apply n lim fuel .and 1 x mx = .ok (d,md))
    (bound : fuel ≤ applyFuel lim) :
    pipeline t lim = .ok (.decided 1 s c d,
      {md with wsteps := md.wsteps + witSteps n md.nodes 0 1 + witSteps n md.nodes 0 d}) := by
  unfold pipeline
  rw [empty]
  simp only [premLoop, Nat.one_ne_zero, if_false]
  rw [cs.sound]
  dsimp only
  rw [cc.sound]
  dsimp only
  rw [apply_ok_target hx bound]
  dsimp only
  rw [apply_ok_target ha bound]

theorem equivalent_from_certificates {n : Nat} {lim : Limits} {t : CTask n}
    {s c x fuel : Nat} {ms mc mx md : Mgr}
    (empty : t.assumptions = [])
    (cs : CompileCertificate n lim t.source Mgr.empty s ms)
    (cc : CompileCertificate n lim t.candidate ms c mc)
    (hx : apply n lim fuel .xor s c mc = .ok (x,mx))
    (ha : apply n lim fuel .and 1 x mx = .ok (0,md))
    (bound : fuel ≤ applyFuel lim) :
    (check t lim).decision = .equivalentUnderAssumptions := by
  unfold check
  rw [pipeline_from_certificates empty cs cc hx ha bound]
  rfl
#print axioms CompileCertificate.sound
#print axioms pipeline_from_certificates
#print axioms equivalent_from_certificates
end PCSDD
