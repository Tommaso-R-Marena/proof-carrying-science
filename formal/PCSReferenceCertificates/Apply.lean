import PCSReferenceCertificates.FuelStable
namespace PCSDD
inductive ApplyCertificate (n : Nat) (lim : Limits) : Nat → BOp → Nat → Nat → Mgr → Nat → Mgr → Prop where
 | hit {fuel a0 b0 r : Nat} {op : BOp} {m : Mgr}
     (hb : ¬ m.ops ≥ lim.operations)
     (hl : memoLookup m.memo op (min a0 b0) (max a0 b0) = some r) :
     ApplyCertificate n lim (fuel+1) op a0 b0 m r {m with ops := m.ops+1}
 | terminal {fuel a0 b0 : Nat} {op : BOp} {m : Mgr}
     (hb : ¬ m.ops ≥ lim.operations)
     (hl : memoLookup m.memo op (min a0 b0) (max a0 b0) = none)
     (ht : min a0 b0 < 2 ∧ max a0 b0 < 2) :
     ApplyCertificate n lim (fuel+1) op a0 b0 m (termOp op (min a0 b0) (max a0 b0))
       {m with ops := m.ops+1, memo := ((op,min a0 b0,max a0 b0),termOp op (min a0 b0) (max a0 b0))::m.memo}
 | branch {fuel a0 b0 lo hi r : Nat} {op : BOp} {m m1 m2 m3 : Mgr}
     (hb : ¬ m.ops ≥ lim.operations)
     (hl : memoLookup m.memo op (min a0 b0) (max a0 b0) = none)
     (ht : ¬ (min a0 b0 < 2 ∧ max a0 b0 < 2))
     (cl : ApplyCertificate n lim fuel op
       (cof m.nodes (min (topVar n m.nodes (min a0 b0)) (topVar n m.nodes (max a0 b0))) (min a0 b0)).1
       (cof m.nodes (min (topVar n m.nodes (min a0 b0)) (topVar n m.nodes (max a0 b0))) (max a0 b0)).1
       {m with ops := m.ops+1} lo m1)
     (ch : ApplyCertificate n lim fuel op
       (cof m.nodes (min (topVar n m.nodes (min a0 b0)) (topVar n m.nodes (max a0 b0))) (min a0 b0)).2
       (cof m.nodes (min (topVar n m.nodes (min a0 b0)) (topVar n m.nodes (max a0 b0))) (max a0 b0)).2 m1 hi m2)
     (hn : mkNode lim m2 (min (topVar n m.nodes (min a0 b0)) (topVar n m.nodes (max a0 b0))) lo hi = .ok (r,m3)) :
     ApplyCertificate n lim (fuel+1) op a0 b0 m r
       {m3 with memo := ((op,min a0 b0,max a0 b0),r)::m3.memo}
theorem ApplyCertificate.sound {n : Nat} {lim : Limits} {fuel a b r : Nat} {op : BOp} {m out : Mgr}
    (c : ApplyCertificate n lim fuel op a b m r out) : apply n lim fuel op a b m = .ok (r,out) := by
  induction c with
  | hit hb hl =>
    unfold apply
    simp only [if_neg hb, hl]
  | terminal hb hl ht =>
    unfold apply
    simp only [if_neg hb, hl, if_pos ht]
  | branch hb hl ht cl ch hn ihl ihh =>
    unfold apply
    simp only [if_neg hb, hl, if_neg ht]
    rw [ihl]
    dsimp only
    rw [ihh]
    dsimp only
    rw [hn]
#print axioms ApplyCertificate.sound
end PCSDD
