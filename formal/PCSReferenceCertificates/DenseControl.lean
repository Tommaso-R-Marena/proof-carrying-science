import PCSReferenceCertificates.Dense
import PCSReferenceCertificates.Apply
open PCSOmega PCSDD
namespace StagedDense
set_option maxRecDepth 100000
set_option maxHeartbeats 0
abbrev f0 : BForm 12 := PCSOmega.BForm.or   (PCSOmega.BForm.or     (PCSOmega.BForm.and (PCSOmega.BForm.atom 0) (PCSOmega.BForm.atom 6))     (PCSOmega.BForm.or       (PCSOmega.BForm.and (PCSOmega.BForm.atom 1) (PCSOmega.BForm.atom 7))       (PCSOmega.BForm.and (PCSOmega.BForm.atom 2) (PCSOmega.BForm.atom 8))))   (PCSOmega.BForm.or     (PCSOmega.BForm.and (PCSOmega.BForm.atom 3) (PCSOmega.BForm.atom 9))     (PCSOmega.BForm.or       (PCSOmega.BForm.and (PCSOmega.BForm.atom 4) (PCSOmega.BForm.atom 10))       (PCSOmega.BForm.and (PCSOmega.BForm.atom 5) (PCSOmega.BForm.atom 11))))
abbrev i0 : Mgr := { nodes := #[], memo := [], ops := 0, visits := 0, wsteps := 0 }
abbrev f1 : BForm 12 := PCSOmega.BForm.or   (PCSOmega.BForm.and (PCSOmega.BForm.atom 0) (PCSOmega.BForm.atom 6))   (PCSOmega.BForm.or     (PCSOmega.BForm.and (PCSOmega.BForm.atom 1) (PCSOmega.BForm.atom 7))     (PCSOmega.BForm.and (PCSOmega.BForm.atom 2) (PCSOmega.BForm.atom 8)))
abbrev i1 : Mgr := { nodes := #[], memo := [], ops := 0, visits := 1, wsteps := 0 }
abbrev f2 : BForm 12 := PCSOmega.BForm.and (PCSOmega.BForm.atom 0) (PCSOmega.BForm.atom 6)
abbrev i2 : Mgr := { nodes := #[], memo := [], ops := 0, visits := 2, wsteps := 0 }
abbrev f3 : BForm 12 := PCSOmega.BForm.atom 0
abbrev i3 : Mgr := { nodes := #[], memo := [], ops := 0, visits := 3, wsteps := 0 }
abbrev o3 : Mgr := { nodes := #[{ var := 0, low := 0, high := 1 }], memo := [], ops := 0, visits := 4, wsteps := 0 }
theorem c3 : CompileCertificate 12 DEFAULT_LIMITS f3 i3 2 o3 := by
  exact CompileCertificate.atom (by rfl)
abbrev f4 : BForm 12 := PCSOmega.BForm.atom 6
abbrev i4 : Mgr := { nodes := #[{ var := 0, low := 0, high := 1 }], memo := [], ops := 0, visits := 4, wsteps := 0 }
abbrev o4 : Mgr := { nodes := #[{ var := 0, low := 0, high := 1 }, { var := 6, low := 0, high := 1 }],   memo := [],   ops := 0,   visits := 5,   wsteps := 0 }
theorem c4 : CompileCertificate 12 DEFAULT_LIMITS f4 i4 3 o4 := by
  exact CompileCertificate.atom (by rfl)
abbrev ai5 : Mgr := o4
abbrev ai6 : Mgr := {ai5 with ops := ai5.ops+1}
abbrev ai7 : Mgr := {ai6 with ops := ai6.ops+1}
abbrev ao7 : Mgr := {ai7 with ops := ai7.ops+1, memo := ((PCSDD.BOp.and,0,0),0)::ai7.memo}
theorem a7 : ApplyCertificate 12 DEFAULT_LIMITS 23 PCSDD.BOp.and 0 0 ai7 0 ao7 := by
  exact ApplyCertificate.terminal (fuel := 22) (a0 := 0) (b0 := 0) (op := PCSDD.BOp.and) (m := ai7) (by decide) (by rfl) (by decide)
abbrev ai8 : Mgr := ao7
abbrev ao8 : Mgr := {ai8 with ops := ai8.ops+1, memo := ((PCSDD.BOp.and,0,1),0)::ai8.memo}
theorem a8 : ApplyCertificate 12 DEFAULT_LIMITS 23 PCSDD.BOp.and 0 1 ai8 0 ao8 := by
  exact ApplyCertificate.terminal (fuel := 22) (a0 := 0) (b0 := 1) (op := PCSDD.BOp.and) (m := ai8) (by decide) (by rfl) (by decide)
abbrev an6 : Mgr := ao8
abbrev ao6 : Mgr := {an6 with memo := ((PCSDD.BOp.and,0,3),0)::an6.memo}
theorem a6 : ApplyCertificate 12 DEFAULT_LIMITS 24 PCSDD.BOp.and 0 3 ai6 0 ao6 := by
  exact ApplyCertificate.branch (fuel := 23) (a0 := 0) (b0 := 3) (lo := 0) (hi := 0) (r := 0) (op := PCSDD.BOp.and) (m := ai6) (m1 := ao7) (m2 := ao8) (m3 := an6) (by decide) (by rfl) (by decide) a7 a8 (by rfl)
abbrev ai9 : Mgr := ao6
abbrev ai10 : Mgr := {ai9 with ops := ai9.ops+1}
abbrev ao10 : Mgr := {ai10 with ops := ai10.ops+1}
theorem a10 : ApplyCertificate 12 DEFAULT_LIMITS 23 PCSDD.BOp.and 1 0 ai10 0 ao10 := by
  exact ApplyCertificate.hit (fuel := 22) (a0 := 1) (b0 := 0) (r := 0) (op := PCSDD.BOp.and) (m := ai10) (by decide) (by rfl)
abbrev ai11 : Mgr := ao10
abbrev ao11 : Mgr := {ai11 with ops := ai11.ops+1, memo := ((PCSDD.BOp.and,1,1),1)::ai11.memo}
theorem a11 : ApplyCertificate 12 DEFAULT_LIMITS 23 PCSDD.BOp.and 1 1 ai11 1 ao11 := by
  exact ApplyCertificate.terminal (fuel := 22) (a0 := 1) (b0 := 1) (op := PCSDD.BOp.and) (m := ai11) (by decide) (by rfl) (by decide)
abbrev an9 : Mgr := ao11
abbrev ao9 : Mgr := {an9 with memo := ((PCSDD.BOp.and,1,3),3)::an9.memo}
theorem a9 : ApplyCertificate 12 DEFAULT_LIMITS 24 PCSDD.BOp.and 1 3 ai9 3 ao9 := by
  exact ApplyCertificate.branch (fuel := 23) (a0 := 1) (b0 := 3) (lo := 0) (hi := 1) (r := 3) (op := PCSDD.BOp.and) (m := ai9) (m1 := ao10) (m2 := ao11) (m3 := an9) (by decide) (by rfl) (by decide) a10 a11 (by rfl)
abbrev an5 : Mgr := {ao9 with nodes := ao9.nodes.push ⟨0,0,3⟩}
abbrev ao5 : Mgr := {an5 with memo := ((PCSDD.BOp.and,2,3),4)::an5.memo}
theorem a5 : ApplyCertificate 12 DEFAULT_LIMITS 25 PCSDD.BOp.and 2 3 ai5 4 ao5 := by
  exact ApplyCertificate.branch (fuel := 24) (a0 := 2) (b0 := 3) (lo := 0) (hi := 3) (r := 4) (op := PCSDD.BOp.and) (m := ai5) (m1 := ao6) (m2 := ao9) (m3 := an5) (by decide) (by rfl) (by decide) a6 a9 (by rfl)
abbrev o2 : Mgr := ao5
theorem c2 : CompileCertificate 12 DEFAULT_LIMITS f2 i2 4 o2 := by
  exact CompileCertificate.and (fuel := 25) (m := i2) (ma := o3) (mb := o4) (out := o2) (x := 2) (y := 3) (r := 4) c3 c4 (ApplyCertificate.sound (m := o4) (out := ao5) a5) (by decide)
abbrev f12 : BForm 12 := PCSOmega.BForm.or   (PCSOmega.BForm.and (PCSOmega.BForm.atom 1) (PCSOmega.BForm.atom 7))   (PCSOmega.BForm.and (PCSOmega.BForm.atom 2) (PCSOmega.BForm.atom 8))
abbrev i12 : Mgr := { nodes := #[{ var := 0, low := 0, high := 1 }, { var := 6, low := 0, high := 1 }, { var := 0, low := 0, high := 3 }],   memo := [((PCSDD.BOp.and, 2, 3), 4),            ((PCSDD.BOp.and, 1, 3), 3),            ((PCSDD.BOp.and, 1, 1), 1),            ((PCSDD.BOp.and, 0, 3), 0),            ((PCSDD.BOp.and, 0, 1), 0),            ((PCSDD.BOp.and, 0, 0), 0)],   ops := 7,   visits := 5,   wsteps := 0 }
abbrev f13 : BForm 12 := PCSOmega.BForm.and (PCSOmega.BForm.atom 1) (PCSOmega.BForm.atom 7)
abbrev i13 : Mgr := { nodes := #[{ var := 0, low := 0, high := 1 }, { var := 6, low := 0, high := 1 }, { var := 0, low := 0, high := 3 }],   memo := [((PCSDD.BOp.and, 2, 3), 4),            ((PCSDD.BOp.and, 1, 3), 3),            ((PCSDD.BOp.and, 1, 1), 1),            ((PCSDD.BOp.and, 0, 3), 0),            ((PCSDD.BOp.and, 0, 1), 0),            ((PCSDD.BOp.and, 0, 0), 0)],   ops := 7,   visits := 6,   wsteps := 0 }
abbrev f14 : BForm 12 := PCSOmega.BForm.atom 1
abbrev i14 : Mgr := { nodes := #[{ var := 0, low := 0, high := 1 }, { var := 6, low := 0, high := 1 }, { var := 0, low := 0, high := 3 }],   memo := [((PCSDD.BOp.and, 2, 3), 4),            ((PCSDD.BOp.and, 1, 3), 3),            ((PCSDD.BOp.and, 1, 1), 1),            ((PCSDD.BOp.and, 0, 3), 0),            ((PCSDD.BOp.and, 0, 1), 0),            ((PCSDD.BOp.and, 0, 0), 0)],   ops := 7,   visits := 7,   wsteps := 0 }
abbrev o14 : Mgr := { nodes := #[{ var := 0, low := 0, high := 1 }, { var := 6, low := 0, high := 1 }, { var := 0, low := 0, high := 3 },              { var := 1, low := 0, high := 1 }],   memo := [((PCSDD.BOp.and, 2, 3), 4),            ((PCSDD.BOp.and, 1, 3), 3),            ((PCSDD.BOp.and, 1, 1), 1),            ((PCSDD.BOp.and, 0, 3), 0),            ((PCSDD.BOp.and, 0, 1), 0),            ((PCSDD.BOp.and, 0, 0), 0)],   ops := 7,   visits := 8,   wsteps := 0 }
theorem c14 : CompileCertificate 12 DEFAULT_LIMITS f14 i14 5 o14 := by
  exact CompileCertificate.atom (by rfl)
abbrev f15 : BForm 12 := PCSOmega.BForm.atom 7
abbrev i15 : Mgr := { nodes := #[{ var := 0, low := 0, high := 1 }, { var := 6, low := 0, high := 1 }, { var := 0, low := 0, high := 3 },              { var := 1, low := 0, high := 1 }],   memo := [((PCSDD.BOp.and, 2, 3), 4),            ((PCSDD.BOp.and, 1, 3), 3),            ((PCSDD.BOp.and, 1, 1), 1),            ((PCSDD.BOp.and, 0, 3), 0),            ((PCSDD.BOp.and, 0, 1), 0),            ((PCSDD.BOp.and, 0, 0), 0)],   ops := 7,   visits := 8,   wsteps := 0 }
abbrev o15 : Mgr := { nodes := #[{ var := 0, low := 0, high := 1 }, { var := 6, low := 0, high := 1 }, { var := 0, low := 0, high := 3 },              { var := 1, low := 0, high := 1 }, { var := 7, low := 0, high := 1 }],   memo := [((PCSDD.BOp.and, 2, 3), 4),            ((PCSDD.BOp.and, 1, 3), 3),            ((PCSDD.BOp.and, 1, 1), 1),            ((PCSDD.BOp.and, 0, 3), 0),            ((PCSDD.BOp.and, 0, 1), 0),            ((PCSDD.BOp.and, 0, 0), 0)],   ops := 7,   visits := 9,   wsteps := 0 }
theorem c15 : CompileCertificate 12 DEFAULT_LIMITS f15 i15 6 o15 := by
  exact CompileCertificate.atom (by rfl)
abbrev ai16 : Mgr := o15
abbrev ai17 : Mgr := {ai16 with ops := ai16.ops+1}
abbrev ai18 : Mgr := {ai17 with ops := ai17.ops+1}
abbrev ao18 : Mgr := {ai18 with ops := ai18.ops+1}
theorem a18 : ApplyCertificate 12 DEFAULT_LIMITS 23 PCSDD.BOp.and 0 0 ai18 0 ao18 := by
  exact ApplyCertificate.hit (fuel := 22) (a0 := 0) (b0 := 0) (r := 0) (op := PCSDD.BOp.and) (m := ai18) (by decide) (by rfl)
abbrev ai19 : Mgr := ao18
abbrev ao19 : Mgr := {ai19 with ops := ai19.ops+1}
theorem a19 : ApplyCertificate 12 DEFAULT_LIMITS 23 PCSDD.BOp.and 0 1 ai19 0 ao19 := by
  exact ApplyCertificate.hit (fuel := 22) (a0 := 0) (b0 := 1) (r := 0) (op := PCSDD.BOp.and) (m := ai19) (by decide) (by rfl)
abbrev an17 : Mgr := ao19
abbrev ao17 : Mgr := {an17 with memo := ((PCSDD.BOp.and,0,6),0)::an17.memo}
theorem a17 : ApplyCertificate 12 DEFAULT_LIMITS 24 PCSDD.BOp.and 0 6 ai17 0 ao17 := by
  exact ApplyCertificate.branch (fuel := 23) (a0 := 0) (b0 := 6) (lo := 0) (hi := 0) (r := 0) (op := PCSDD.BOp.and) (m := ai17) (m1 := ao18) (m2 := ao19) (m3 := an17) (by decide) (by rfl) (by decide) a18 a19 (by rfl)
abbrev ai20 : Mgr := ao17
abbrev ai21 : Mgr := {ai20 with ops := ai20.ops+1}
abbrev ao21 : Mgr := {ai21 with ops := ai21.ops+1}
theorem a21 : ApplyCertificate 12 DEFAULT_LIMITS 23 PCSDD.BOp.and 1 0 ai21 0 ao21 := by
  exact ApplyCertificate.hit (fuel := 22) (a0 := 1) (b0 := 0) (r := 0) (op := PCSDD.BOp.and) (m := ai21) (by decide) (by rfl)
abbrev ai22 : Mgr := ao21
abbrev ao22 : Mgr := {ai22 with ops := ai22.ops+1}
theorem a22 : ApplyCertificate 12 DEFAULT_LIMITS 23 PCSDD.BOp.and 1 1 ai22 1 ao22 := by
  exact ApplyCertificate.hit (fuel := 22) (a0 := 1) (b0 := 1) (r := 1) (op := PCSDD.BOp.and) (m := ai22) (by decide) (by rfl)
abbrev an20 : Mgr := ao22
abbrev ao20 : Mgr := {an20 with memo := ((PCSDD.BOp.and,1,6),6)::an20.memo}
theorem a20 : ApplyCertificate 12 DEFAULT_LIMITS 24 PCSDD.BOp.and 1 6 ai20 6 ao20 := by
  exact ApplyCertificate.branch (fuel := 23) (a0 := 1) (b0 := 6) (lo := 0) (hi := 1) (r := 6) (op := PCSDD.BOp.and) (m := ai20) (m1 := ao21) (m2 := ao22) (m3 := an20) (by decide) (by rfl) (by decide) a21 a22 (by rfl)
abbrev an16 : Mgr := {ao20 with nodes := ao20.nodes.push ⟨1,0,6⟩}
abbrev ao16 : Mgr := {an16 with memo := ((PCSDD.BOp.and,5,6),7)::an16.memo}
theorem a16 : ApplyCertificate 12 DEFAULT_LIMITS 25 PCSDD.BOp.and 5 6 ai16 7 ao16 := by
  exact ApplyCertificate.branch (fuel := 24) (a0 := 5) (b0 := 6) (lo := 0) (hi := 6) (r := 7) (op := PCSDD.BOp.and) (m := ai16) (m1 := ao17) (m2 := ao20) (m3 := an16) (by decide) (by rfl) (by decide) a17 a20 (by rfl)
abbrev o13 : Mgr := ao16
theorem c13 : CompileCertificate 12 DEFAULT_LIMITS f13 i13 7 o13 := by
  exact CompileCertificate.and (fuel := 25) (m := i13) (ma := o14) (mb := o15) (out := o13) (x := 5) (y := 6) (r := 7) c14 c15 (ApplyCertificate.sound (m := o15) (out := ao16) a16) (by decide)
abbrev f23 : BForm 12 := PCSOmega.BForm.and (PCSOmega.BForm.atom 2) (PCSOmega.BForm.atom 8)
abbrev i23 : Mgr := { nodes := #[{ var := 0, low := 0, high := 1 }, { var := 6, low := 0, high := 1 }, { var := 0, low := 0, high := 3 },              { var := 1, low := 0, high := 1 }, { var := 7, low := 0, high := 1 }, { var := 1, low := 0, high := 6 }],   memo := [((PCSDD.BOp.and, 5, 6), 7),            ((PCSDD.BOp.and, 1, 6), 6),            ((PCSDD.BOp.and, 0, 6), 0),            ((PCSDD.BOp.and, 2, 3), 4),            ((PCSDD.BOp.and, 1, 3), 3),            ((PCSDD.BOp.and, 1, 1), 1),            ((PCSDD.BOp.and, 0, 3), 0),            ((PCSDD.BOp.and, 0, 1), 0),            ((PCSDD.BOp.and, 0, 0), 0)],   ops := 14,   visits := 9,   wsteps := 0 }
abbrev f24 : BForm 12 := PCSOmega.BForm.atom 2
abbrev i24 : Mgr := { nodes := #[{ var := 0, low := 0, high := 1 }, { var := 6, low := 0, high := 1 }, { var := 0, low := 0, high := 3 },              { var := 1, low := 0, high := 1 }, { var := 7, low := 0, high := 1 }, { var := 1, low := 0, high := 6 }],   memo := [((PCSDD.BOp.and, 5, 6), 7),            ((PCSDD.BOp.and, 1, 6), 6),            ((PCSDD.BOp.and, 0, 6), 0),            ((PCSDD.BOp.and, 2, 3), 4),            ((PCSDD.BOp.and, 1, 3), 3),            ((PCSDD.BOp.and, 1, 1), 1),            ((PCSDD.BOp.and, 0, 3), 0),            ((PCSDD.BOp.and, 0, 1), 0),            ((PCSDD.BOp.and, 0, 0), 0)],   ops := 14,   visits := 10,   wsteps := 0 }
abbrev o24 : Mgr := { nodes := #[{ var := 0, low := 0, high := 1 }, { var := 6, low := 0, high := 1 }, { var := 0, low := 0, high := 3 },              { var := 1, low := 0, high := 1 }, { var := 7, low := 0, high := 1 }, { var := 1, low := 0, high := 6 },              { var := 2, low := 0, high := 1 }],   memo := [((PCSDD.BOp.and, 5, 6), 7),            ((PCSDD.BOp.and, 1, 6), 6),            ((PCSDD.BOp.and, 0, 6), 0),            ((PCSDD.BOp.and, 2, 3), 4),            ((PCSDD.BOp.and, 1, 3), 3),            ((PCSDD.BOp.and, 1, 1), 1),            ((PCSDD.BOp.and, 0, 3), 0),            ((PCSDD.BOp.and, 0, 1), 0),            ((PCSDD.BOp.and, 0, 0), 0)],   ops := 14,   visits := 11,   wsteps := 0 }
theorem c24 : CompileCertificate 12 DEFAULT_LIMITS f24 i24 8 o24 := by
  exact CompileCertificate.atom (by rfl)
abbrev f25 : BForm 12 := PCSOmega.BForm.atom 8
abbrev i25 : Mgr := { nodes := #[{ var := 0, low := 0, high := 1 }, { var := 6, low := 0, high := 1 }, { var := 0, low := 0, high := 3 },              { var := 1, low := 0, high := 1 }, { var := 7, low := 0, high := 1 }, { var := 1, low := 0, high := 6 },              { var := 2, low := 0, high := 1 }],   memo := [((PCSDD.BOp.and, 5, 6), 7),            ((PCSDD.BOp.and, 1, 6), 6),            ((PCSDD.BOp.and, 0, 6), 0),            ((PCSDD.BOp.and, 2, 3), 4),            ((PCSDD.BOp.and, 1, 3), 3),            ((PCSDD.BOp.and, 1, 1), 1),            ((PCSDD.BOp.and, 0, 3), 0),            ((PCSDD.BOp.and, 0, 1), 0),            ((PCSDD.BOp.and, 0, 0), 0)],   ops := 14,   visits := 11,   wsteps := 0 }
abbrev o25 : Mgr := { nodes := #[{ var := 0, low := 0, high := 1 }, { var := 6, low := 0, high := 1 }, { var := 0, low := 0, high := 3 },              { var := 1, low := 0, high := 1 }, { var := 7, low := 0, high := 1 }, { var := 1, low := 0, high := 6 },              { var := 2, low := 0, high := 1 }, { var := 8, low := 0, high := 1 }],   memo := [((PCSDD.BOp.and, 5, 6), 7),            ((PCSDD.BOp.and, 1, 6), 6),            ((PCSDD.BOp.and, 0, 6), 0),            ((PCSDD.BOp.and, 2, 3), 4),            ((PCSDD.BOp.and, 1, 3), 3),            ((PCSDD.BOp.and, 1, 1), 1),            ((PCSDD.BOp.and, 0, 3), 0),            ((PCSDD.BOp.and, 0, 1), 0),            ((PCSDD.BOp.and, 0, 0), 0)],   ops := 14,   visits := 12,   wsteps := 0 }
theorem c25 : CompileCertificate 12 DEFAULT_LIMITS f25 i25 9 o25 := by
  exact CompileCertificate.atom (by rfl)
abbrev ai26 : Mgr := o25
abbrev ai27 : Mgr := {ai26 with ops := ai26.ops+1}
abbrev ai28 : Mgr := {ai27 with ops := ai27.ops+1}
abbrev ao28 : Mgr := {ai28 with ops := ai28.ops+1}
theorem a28 : ApplyCertificate 12 DEFAULT_LIMITS 23 PCSDD.BOp.and 0 0 ai28 0 ao28 := by
  exact ApplyCertificate.hit (fuel := 22) (a0 := 0) (b0 := 0) (r := 0) (op := PCSDD.BOp.and) (m := ai28) (by decide) (by rfl)
abbrev ai29 : Mgr := ao28
abbrev ao29 : Mgr := {ai29 with ops := ai29.ops+1}
theorem a29 : ApplyCertificate 12 DEFAULT_LIMITS 23 PCSDD.BOp.and 0 1 ai29 0 ao29 := by
  exact ApplyCertificate.hit (fuel := 22) (a0 := 0) (b0 := 1) (r := 0) (op := PCSDD.BOp.and) (m := ai29) (by decide) (by rfl)
abbrev an27 : Mgr := ao29
abbrev ao27 : Mgr := {an27 with memo := ((PCSDD.BOp.and,0,9),0)::an27.memo}
theorem a27 : ApplyCertificate 12 DEFAULT_LIMITS 24 PCSDD.BOp.and 0 9 ai27 0 ao27 := by
  exact ApplyCertificate.branch (fuel := 23) (a0 := 0) (b0 := 9) (lo := 0) (hi := 0) (r := 0) (op := PCSDD.BOp.and) (m := ai27) (m1 := ao28) (m2 := ao29) (m3 := an27) (by decide) (by rfl) (by decide) a28 a29 (by rfl)
abbrev ai30 : Mgr := ao27
abbrev ai31 : Mgr := {ai30 with ops := ai30.ops+1}
abbrev ao31 : Mgr := {ai31 with ops := ai31.ops+1}
theorem a31 : ApplyCertificate 12 DEFAULT_LIMITS 23 PCSDD.BOp.and 1 0 ai31 0 ao31 := by
  exact ApplyCertificate.hit (fuel := 22) (a0 := 1) (b0 := 0) (r := 0) (op := PCSDD.BOp.and) (m := ai31) (by decide) (by rfl)
abbrev ai32 : Mgr := ao31
abbrev ao32 : Mgr := {ai32 with ops := ai32.ops+1}
theorem a32 : ApplyCertificate 12 DEFAULT_LIMITS 23 PCSDD.BOp.and 1 1 ai32 1 ao32 := by
  exact ApplyCertificate.hit (fuel := 22) (a0 := 1) (b0 := 1) (r := 1) (op := PCSDD.BOp.and) (m := ai32) (by decide) (by rfl)
abbrev an30 : Mgr := ao32
abbrev ao30 : Mgr := {an30 with memo := ((PCSDD.BOp.and,1,9),9)::an30.memo}
theorem a30 : ApplyCertificate 12 DEFAULT_LIMITS 24 PCSDD.BOp.and 1 9 ai30 9 ao30 := by
  exact ApplyCertificate.branch (fuel := 23) (a0 := 1) (b0 := 9) (lo := 0) (hi := 1) (r := 9) (op := PCSDD.BOp.and) (m := ai30) (m1 := ao31) (m2 := ao32) (m3 := an30) (by decide) (by rfl) (by decide) a31 a32 (by rfl)
abbrev an26 : Mgr := {ao30 with nodes := ao30.nodes.push ⟨2,0,9⟩}
abbrev ao26 : Mgr := {an26 with memo := ((PCSDD.BOp.and,8,9),10)::an26.memo}
theorem a26 : ApplyCertificate 12 DEFAULT_LIMITS 25 PCSDD.BOp.and 8 9 ai26 10 ao26 := by
  exact ApplyCertificate.branch (fuel := 24) (a0 := 8) (b0 := 9) (lo := 0) (hi := 9) (r := 10) (op := PCSDD.BOp.and) (m := ai26) (m1 := ao27) (m2 := ao30) (m3 := an26) (by decide) (by rfl) (by decide) a27 a30 (by rfl)
abbrev o23 : Mgr := ao26
theorem c23 : CompileCertificate 12 DEFAULT_LIMITS f23 i23 10 o23 := by
  exact CompileCertificate.and (fuel := 25) (m := i23) (ma := o24) (mb := o25) (out := o23) (x := 8) (y := 9) (r := 10) c24 c25 (ApplyCertificate.sound (m := o25) (out := ao26) a26) (by decide)
abbrev ai33 : Mgr := o23
abbrev ai34 : Mgr := {ai33 with ops := ai33.ops+1}
abbrev ai35 : Mgr := {ai34 with ops := ai34.ops+1}
abbrev ao35 : Mgr := {ai35 with ops := ai35.ops+1, memo := ((PCSDD.BOp.or,0,0),0)::ai35.memo}
theorem a35 : ApplyCertificate 12 DEFAULT_LIMITS 23 PCSDD.BOp.or 0 0 ai35 0 ao35 := by
  exact ApplyCertificate.terminal (fuel := 22) (a0 := 0) (b0 := 0) (op := PCSDD.BOp.or) (m := ai35) (by decide) (by rfl) (by decide)
abbrev ai36 : Mgr := ao35
abbrev ai37 : Mgr := {ai36 with ops := ai36.ops+1}
abbrev ao37 : Mgr := {ai37 with ops := ai37.ops+1}
theorem a37 : ApplyCertificate 12 DEFAULT_LIMITS 22 PCSDD.BOp.or 0 0 ai37 0 ao37 := by
  exact ApplyCertificate.hit (fuel := 21) (a0 := 0) (b0 := 0) (r := 0) (op := PCSDD.BOp.or) (m := ai37) (by decide) (by rfl)
abbrev ai38 : Mgr := ao37
abbrev ao38 : Mgr := {ai38 with ops := ai38.ops+1, memo := ((PCSDD.BOp.or,0,1),1)::ai38.memo}
theorem a38 : ApplyCertificate 12 DEFAULT_LIMITS 22 PCSDD.BOp.or 0 1 ai38 1 ao38 := by
  exact ApplyCertificate.terminal (fuel := 21) (a0 := 0) (b0 := 1) (op := PCSDD.BOp.or) (m := ai38) (by decide) (by rfl) (by decide)
abbrev an36 : Mgr := ao38
abbrev ao36 : Mgr := {an36 with memo := ((PCSDD.BOp.or,0,9),9)::an36.memo}
theorem a36 : ApplyCertificate 12 DEFAULT_LIMITS 23 PCSDD.BOp.or 0 9 ai36 9 ao36 := by
  exact ApplyCertificate.branch (fuel := 22) (a0 := 0) (b0 := 9) (lo := 0) (hi := 1) (r := 9) (op := PCSDD.BOp.or) (m := ai36) (m1 := ao37) (m2 := ao38) (m3 := an36) (by decide) (by rfl) (by decide) a37 a38 (by rfl)
abbrev an34 : Mgr := ao36
abbrev ao34 : Mgr := {an34 with memo := ((PCSDD.BOp.or,0,10),10)::an34.memo}
theorem a34 : ApplyCertificate 12 DEFAULT_LIMITS 24 PCSDD.BOp.or 0 10 ai34 10 ao34 := by
  exact ApplyCertificate.branch (fuel := 23) (a0 := 0) (b0 := 10) (lo := 0) (hi := 9) (r := 10) (op := PCSDD.BOp.or) (m := ai34) (m1 := ao35) (m2 := ao36) (m3 := an34) (by decide) (by rfl) (by decide) a35 a36 (by rfl)
abbrev ai39 : Mgr := ao34
abbrev ai40 : Mgr := {ai39 with ops := ai39.ops+1}
abbrev ai41 : Mgr := {ai40 with ops := ai40.ops+1}
abbrev ao41 : Mgr := {ai41 with ops := ai41.ops+1}
theorem a41 : ApplyCertificate 12 DEFAULT_LIMITS 22 PCSDD.BOp.or 0 0 ai41 0 ao41 := by
  exact ApplyCertificate.hit (fuel := 21) (a0 := 0) (b0 := 0) (r := 0) (op := PCSDD.BOp.or) (m := ai41) (by decide) (by rfl)
abbrev ai42 : Mgr := ao41
abbrev ao42 : Mgr := {ai42 with ops := ai42.ops+1}
theorem a42 : ApplyCertificate 12 DEFAULT_LIMITS 22 PCSDD.BOp.or 0 1 ai42 1 ao42 := by
  exact ApplyCertificate.hit (fuel := 21) (a0 := 0) (b0 := 1) (r := 1) (op := PCSDD.BOp.or) (m := ai42) (by decide) (by rfl)
abbrev an40 : Mgr := ao42
abbrev ao40 : Mgr := {an40 with memo := ((PCSDD.BOp.or,0,6),6)::an40.memo}
theorem a40 : ApplyCertificate 12 DEFAULT_LIMITS 23 PCSDD.BOp.or 6 0 ai40 6 ao40 := by
  exact ApplyCertificate.branch (fuel := 22) (a0 := 6) (b0 := 0) (lo := 0) (hi := 1) (r := 6) (op := PCSDD.BOp.or) (m := ai40) (m1 := ao41) (m2 := ao42) (m3 := an40) (by decide) (by rfl) (by decide) a41 a42 (by rfl)
abbrev ai43 : Mgr := ao40
abbrev ai44 : Mgr := {ai43 with ops := ai43.ops+1}
abbrev ao44 : Mgr := {ai44 with ops := ai44.ops+1}
theorem a44 : ApplyCertificate 12 DEFAULT_LIMITS 22 PCSDD.BOp.or 0 9 ai44 9 ao44 := by
  exact ApplyCertificate.hit (fuel := 21) (a0 := 0) (b0 := 9) (r := 9) (op := PCSDD.BOp.or) (m := ai44) (by decide) (by rfl)
abbrev ai45 : Mgr := ao44
abbrev ai46 : Mgr := {ai45 with ops := ai45.ops+1}
abbrev ao46 : Mgr := {ai46 with ops := ai46.ops+1}
theorem a46 : ApplyCertificate 12 DEFAULT_LIMITS 21 PCSDD.BOp.or 1 0 ai46 1 ao46 := by
  exact ApplyCertificate.hit (fuel := 20) (a0 := 1) (b0 := 0) (r := 1) (op := PCSDD.BOp.or) (m := ai46) (by decide) (by rfl)
abbrev ai47 : Mgr := ao46
abbrev ao47 : Mgr := {ai47 with ops := ai47.ops+1, memo := ((PCSDD.BOp.or,1,1),1)::ai47.memo}
theorem a47 : ApplyCertificate 12 DEFAULT_LIMITS 21 PCSDD.BOp.or 1 1 ai47 1 ao47 := by
  exact ApplyCertificate.terminal (fuel := 20) (a0 := 1) (b0 := 1) (op := PCSDD.BOp.or) (m := ai47) (by decide) (by rfl) (by decide)
abbrev an45 : Mgr := ao47
abbrev ao45 : Mgr := {an45 with memo := ((PCSDD.BOp.or,1,9),1)::an45.memo}
theorem a45 : ApplyCertificate 12 DEFAULT_LIMITS 22 PCSDD.BOp.or 1 9 ai45 1 ao45 := by
  exact ApplyCertificate.branch (fuel := 21) (a0 := 1) (b0 := 9) (lo := 1) (hi := 1) (r := 1) (op := PCSDD.BOp.or) (m := ai45) (m1 := ao46) (m2 := ao47) (m3 := an45) (by decide) (by rfl) (by decide) a46 a47 (by rfl)
abbrev an43 : Mgr := {ao45 with nodes := ao45.nodes.push ⟨7,9,1⟩}
abbrev ao43 : Mgr := {an43 with memo := ((PCSDD.BOp.or,6,9),11)::an43.memo}
theorem a43 : ApplyCertificate 12 DEFAULT_LIMITS 23 PCSDD.BOp.or 6 9 ai43 11 ao43 := by
  exact ApplyCertificate.branch (fuel := 22) (a0 := 6) (b0 := 9) (lo := 9) (hi := 1) (r := 11) (op := PCSDD.BOp.or) (m := ai43) (m1 := ao44) (m2 := ao45) (m3 := an43) (by decide) (by rfl) (by decide) a44 a45 (by rfl)
abbrev an39 : Mgr := {ao43 with nodes := ao43.nodes.push ⟨2,6,11⟩}
abbrev ao39 : Mgr := {an39 with memo := ((PCSDD.BOp.or,6,10),12)::an39.memo}
theorem a39 : ApplyCertificate 12 DEFAULT_LIMITS 24 PCSDD.BOp.or 6 10 ai39 12 ao39 := by
  exact ApplyCertificate.branch (fuel := 23) (a0 := 6) (b0 := 10) (lo := 6) (hi := 11) (r := 12) (op := PCSDD.BOp.or) (m := ai39) (m1 := ao40) (m2 := ao43) (m3 := an39) (by decide) (by rfl) (by decide) a40 a43 (by rfl)
abbrev an33 : Mgr := {ao39 with nodes := ao39.nodes.push ⟨1,10,12⟩}
abbrev ao33 : Mgr := {an33 with memo := ((PCSDD.BOp.or,7,10),13)::an33.memo}
theorem a33 : ApplyCertificate 12 DEFAULT_LIMITS 25 PCSDD.BOp.or 7 10 ai33 13 ao33 := by
  exact ApplyCertificate.branch (fuel := 24) (a0 := 7) (b0 := 10) (lo := 10) (hi := 12) (r := 13) (op := PCSDD.BOp.or) (m := ai33) (m1 := ao34) (m2 := ao39) (m3 := an33) (by decide) (by rfl) (by decide) a34 a39 (by rfl)
abbrev o12 : Mgr := ao33
theorem c12 : CompileCertificate 12 DEFAULT_LIMITS f12 i12 13 o12 := by
  exact CompileCertificate.or (fuel := 25) (m := i12) (ma := o13) (mb := o23) (out := o12) (x := 7) (y := 10) (r := 13) c13 c23 (ApplyCertificate.sound (m := o23) (out := ao33) a33) (by decide)
abbrev ai48 : Mgr := o12
abbrev ai49 : Mgr := {ai48 with ops := ai48.ops+1}
abbrev ai50 : Mgr := {ai49 with ops := ai49.ops+1}
abbrev ao50 : Mgr := {ai50 with ops := ai50.ops+1}
theorem a50 : ApplyCertificate 12 DEFAULT_LIMITS 23 PCSDD.BOp.or 0 10 ai50 10 ao50 := by
  exact ApplyCertificate.hit (fuel := 22) (a0 := 0) (b0 := 10) (r := 10) (op := PCSDD.BOp.or) (m := ai50) (by decide) (by rfl)
abbrev ai51 : Mgr := ao50
abbrev ai52 : Mgr := {ai51 with ops := ai51.ops+1}
abbrev ao52 : Mgr := {ai52 with ops := ai52.ops+1}
theorem a52 : ApplyCertificate 12 DEFAULT_LIMITS 22 PCSDD.BOp.or 0 6 ai52 6 ao52 := by
  exact ApplyCertificate.hit (fuel := 21) (a0 := 0) (b0 := 6) (r := 6) (op := PCSDD.BOp.or) (m := ai52) (by decide) (by rfl)
abbrev ai53 : Mgr := ao52
abbrev ai54 : Mgr := {ai53 with ops := ai53.ops+1}
abbrev ao54 : Mgr := {ai54 with ops := ai54.ops+1}
theorem a54 : ApplyCertificate 12 DEFAULT_LIMITS 21 PCSDD.BOp.or 0 9 ai54 9 ao54 := by
  exact ApplyCertificate.hit (fuel := 20) (a0 := 0) (b0 := 9) (r := 9) (op := PCSDD.BOp.or) (m := ai54) (by decide) (by rfl)
abbrev ai55 : Mgr := ao54
abbrev ao55 : Mgr := {ai55 with ops := ai55.ops+1}
theorem a55 : ApplyCertificate 12 DEFAULT_LIMITS 21 PCSDD.BOp.or 0 1 ai55 1 ao55 := by
  exact ApplyCertificate.hit (fuel := 20) (a0 := 0) (b0 := 1) (r := 1) (op := PCSDD.BOp.or) (m := ai55) (by decide) (by rfl)
abbrev an53 : Mgr := ao55
abbrev ao53 : Mgr := {an53 with memo := ((PCSDD.BOp.or,0,11),11)::an53.memo}
theorem a53 : ApplyCertificate 12 DEFAULT_LIMITS 22 PCSDD.BOp.or 0 11 ai53 11 ao53 := by
  exact ApplyCertificate.branch (fuel := 21) (a0 := 0) (b0 := 11) (lo := 9) (hi := 1) (r := 11) (op := PCSDD.BOp.or) (m := ai53) (m1 := ao54) (m2 := ao55) (m3 := an53) (by decide) (by rfl) (by decide) a54 a55 (by rfl)
abbrev an51 : Mgr := ao53
abbrev ao51 : Mgr := {an51 with memo := ((PCSDD.BOp.or,0,12),12)::an51.memo}
theorem a51 : ApplyCertificate 12 DEFAULT_LIMITS 23 PCSDD.BOp.or 0 12 ai51 12 ao51 := by
  exact ApplyCertificate.branch (fuel := 22) (a0 := 0) (b0 := 12) (lo := 6) (hi := 11) (r := 12) (op := PCSDD.BOp.or) (m := ai51) (m1 := ao52) (m2 := ao53) (m3 := an51) (by decide) (by rfl) (by decide) a52 a53 (by rfl)
abbrev an49 : Mgr := ao51
abbrev ao49 : Mgr := {an49 with memo := ((PCSDD.BOp.or,0,13),13)::an49.memo}
theorem a49 : ApplyCertificate 12 DEFAULT_LIMITS 24 PCSDD.BOp.or 0 13 ai49 13 ao49 := by
  exact ApplyCertificate.branch (fuel := 23) (a0 := 0) (b0 := 13) (lo := 10) (hi := 12) (r := 13) (op := PCSDD.BOp.or) (m := ai49) (m1 := ao50) (m2 := ao51) (m3 := an49) (by decide) (by rfl) (by decide) a50 a51 (by rfl)
abbrev ai56 : Mgr := ao49
abbrev ai57 : Mgr := {ai56 with ops := ai56.ops+1}
abbrev ai58 : Mgr := {ai57 with ops := ai57.ops+1}
abbrev ai59 : Mgr := {ai58 with ops := ai58.ops+1}
abbrev ao59 : Mgr := {ai59 with ops := ai59.ops+1}
theorem a59 : ApplyCertificate 12 DEFAULT_LIMITS 21 PCSDD.BOp.or 0 0 ai59 0 ao59 := by
  exact ApplyCertificate.hit (fuel := 20) (a0 := 0) (b0 := 0) (r := 0) (op := PCSDD.BOp.or) (m := ai59) (by decide) (by rfl)
abbrev ai60 : Mgr := ao59
abbrev ao60 : Mgr := {ai60 with ops := ai60.ops+1}
theorem a60 : ApplyCertificate 12 DEFAULT_LIMITS 21 PCSDD.BOp.or 0 1 ai60 1 ao60 := by
  exact ApplyCertificate.hit (fuel := 20) (a0 := 0) (b0 := 1) (r := 1) (op := PCSDD.BOp.or) (m := ai60) (by decide) (by rfl)
abbrev an58 : Mgr := ao60
abbrev ao58 : Mgr := {an58 with memo := ((PCSDD.BOp.or,0,3),3)::an58.memo}
theorem a58 : ApplyCertificate 12 DEFAULT_LIMITS 22 PCSDD.BOp.or 3 0 ai58 3 ao58 := by
  exact ApplyCertificate.branch (fuel := 21) (a0 := 3) (b0 := 0) (lo := 0) (hi := 1) (r := 3) (op := PCSDD.BOp.or) (m := ai58) (m1 := ao59) (m2 := ao60) (m3 := an58) (by decide) (by rfl) (by decide) a59 a60 (by rfl)
abbrev ai61 : Mgr := ao58
abbrev ai62 : Mgr := {ai61 with ops := ai61.ops+1}
abbrev ao62 : Mgr := {ai62 with ops := ai62.ops+1}
theorem a62 : ApplyCertificate 12 DEFAULT_LIMITS 21 PCSDD.BOp.or 0 9 ai62 9 ao62 := by
  exact ApplyCertificate.hit (fuel := 20) (a0 := 0) (b0 := 9) (r := 9) (op := PCSDD.BOp.or) (m := ai62) (by decide) (by rfl)
abbrev ai63 : Mgr := ao62
abbrev ao63 : Mgr := {ai63 with ops := ai63.ops+1}
theorem a63 : ApplyCertificate 12 DEFAULT_LIMITS 21 PCSDD.BOp.or 1 9 ai63 1 ao63 := by
  exact ApplyCertificate.hit (fuel := 20) (a0 := 1) (b0 := 9) (r := 1) (op := PCSDD.BOp.or) (m := ai63) (by decide) (by rfl)
abbrev an61 : Mgr := {ao63 with nodes := ao63.nodes.push ⟨6,9,1⟩}
abbrev ao61 : Mgr := {an61 with memo := ((PCSDD.BOp.or,3,9),14)::an61.memo}
theorem a61 : ApplyCertificate 12 DEFAULT_LIMITS 22 PCSDD.BOp.or 3 9 ai61 14 ao61 := by
  exact ApplyCertificate.branch (fuel := 21) (a0 := 3) (b0 := 9) (lo := 9) (hi := 1) (r := 14) (op := PCSDD.BOp.or) (m := ai61) (m1 := ao62) (m2 := ao63) (m3 := an61) (by decide) (by rfl) (by decide) a62 a63 (by rfl)
abbrev an57 : Mgr := {ao61 with nodes := ao61.nodes.push ⟨2,3,14⟩}
abbrev ao57 : Mgr := {an57 with memo := ((PCSDD.BOp.or,3,10),15)::an57.memo}
theorem a57 : ApplyCertificate 12 DEFAULT_LIMITS 23 PCSDD.BOp.or 3 10 ai57 15 ao57 := by
  exact ApplyCertificate.branch (fuel := 22) (a0 := 3) (b0 := 10) (lo := 3) (hi := 14) (r := 15) (op := PCSDD.BOp.or) (m := ai57) (m1 := ao58) (m2 := ao61) (m3 := an57) (by decide) (by rfl) (by decide) a58 a61 (by rfl)
abbrev ai64 : Mgr := ao57
abbrev ai65 : Mgr := {ai64 with ops := ai64.ops+1}
abbrev ai66 : Mgr := {ai65 with ops := ai65.ops+1}
abbrev ao66 : Mgr := {ai66 with ops := ai66.ops+1}
theorem a66 : ApplyCertificate 12 DEFAULT_LIMITS 21 PCSDD.BOp.or 0 6 ai66 6 ao66 := by
  exact ApplyCertificate.hit (fuel := 20) (a0 := 0) (b0 := 6) (r := 6) (op := PCSDD.BOp.or) (m := ai66) (by decide) (by rfl)
abbrev ai67 : Mgr := ao66
abbrev ai68 : Mgr := {ai67 with ops := ai67.ops+1}
abbrev ao68 : Mgr := {ai68 with ops := ai68.ops+1}
theorem a68 : ApplyCertificate 12 DEFAULT_LIMITS 20 PCSDD.BOp.or 1 0 ai68 1 ao68 := by
  exact ApplyCertificate.hit (fuel := 19) (a0 := 1) (b0 := 0) (r := 1) (op := PCSDD.BOp.or) (m := ai68) (by decide) (by rfl)
abbrev ai69 : Mgr := ao68
abbrev ao69 : Mgr := {ai69 with ops := ai69.ops+1}
theorem a69 : ApplyCertificate 12 DEFAULT_LIMITS 20 PCSDD.BOp.or 1 1 ai69 1 ao69 := by
  exact ApplyCertificate.hit (fuel := 19) (a0 := 1) (b0 := 1) (r := 1) (op := PCSDD.BOp.or) (m := ai69) (by decide) (by rfl)
abbrev an67 : Mgr := ao69
abbrev ao67 : Mgr := {an67 with memo := ((PCSDD.BOp.or,1,6),1)::an67.memo}
theorem a67 : ApplyCertificate 12 DEFAULT_LIMITS 21 PCSDD.BOp.or 1 6 ai67 1 ao67 := by
  exact ApplyCertificate.branch (fuel := 20) (a0 := 1) (b0 := 6) (lo := 1) (hi := 1) (r := 1) (op := PCSDD.BOp.or) (m := ai67) (m1 := ao68) (m2 := ao69) (m3 := an67) (by decide) (by rfl) (by decide) a68 a69 (by rfl)
abbrev an65 : Mgr := {ao67 with nodes := ao67.nodes.push ⟨6,6,1⟩}
abbrev ao65 : Mgr := {an65 with memo := ((PCSDD.BOp.or,3,6),16)::an65.memo}
theorem a65 : ApplyCertificate 12 DEFAULT_LIMITS 22 PCSDD.BOp.or 3 6 ai65 16 ao65 := by
  exact ApplyCertificate.branch (fuel := 21) (a0 := 3) (b0 := 6) (lo := 6) (hi := 1) (r := 16) (op := PCSDD.BOp.or) (m := ai65) (m1 := ao66) (m2 := ao67) (m3 := an65) (by decide) (by rfl) (by decide) a66 a67 (by rfl)
abbrev ai70 : Mgr := ao65
abbrev ai71 : Mgr := {ai70 with ops := ai70.ops+1}
abbrev ao71 : Mgr := {ai71 with ops := ai71.ops+1}
theorem a71 : ApplyCertificate 12 DEFAULT_LIMITS 21 PCSDD.BOp.or 0 11 ai71 11 ao71 := by
  exact ApplyCertificate.hit (fuel := 20) (a0 := 0) (b0 := 11) (r := 11) (op := PCSDD.BOp.or) (m := ai71) (by decide) (by rfl)
abbrev ai72 : Mgr := ao71
abbrev ai73 : Mgr := {ai72 with ops := ai72.ops+1}
abbrev ao73 : Mgr := {ai73 with ops := ai73.ops+1}
theorem a73 : ApplyCertificate 12 DEFAULT_LIMITS 20 PCSDD.BOp.or 1 9 ai73 1 ao73 := by
  exact ApplyCertificate.hit (fuel := 19) (a0 := 1) (b0 := 9) (r := 1) (op := PCSDD.BOp.or) (m := ai73) (by decide) (by rfl)
abbrev ai74 : Mgr := ao73
abbrev ao74 : Mgr := {ai74 with ops := ai74.ops+1}
theorem a74 : ApplyCertificate 12 DEFAULT_LIMITS 20 PCSDD.BOp.or 1 1 ai74 1 ao74 := by
  exact ApplyCertificate.hit (fuel := 19) (a0 := 1) (b0 := 1) (r := 1) (op := PCSDD.BOp.or) (m := ai74) (by decide) (by rfl)
abbrev an72 : Mgr := ao74
abbrev ao72 : Mgr := {an72 with memo := ((PCSDD.BOp.or,1,11),1)::an72.memo}
theorem a72 : ApplyCertificate 12 DEFAULT_LIMITS 21 PCSDD.BOp.or 1 11 ai72 1 ao72 := by
  exact ApplyCertificate.branch (fuel := 20) (a0 := 1) (b0 := 11) (lo := 1) (hi := 1) (r := 1) (op := PCSDD.BOp.or) (m := ai72) (m1 := ao73) (m2 := ao74) (m3 := an72) (by decide) (by rfl) (by decide) a73 a74 (by rfl)
abbrev an70 : Mgr := {ao72 with nodes := ao72.nodes.push ⟨6,11,1⟩}
abbrev ao70 : Mgr := {an70 with memo := ((PCSDD.BOp.or,3,11),17)::an70.memo}
theorem a70 : ApplyCertificate 12 DEFAULT_LIMITS 22 PCSDD.BOp.or 3 11 ai70 17 ao70 := by
  exact ApplyCertificate.branch (fuel := 21) (a0 := 3) (b0 := 11) (lo := 11) (hi := 1) (r := 17) (op := PCSDD.BOp.or) (m := ai70) (m1 := ao71) (m2 := ao72) (m3 := an70) (by decide) (by rfl) (by decide) a71 a72 (by rfl)
abbrev an64 : Mgr := {ao70 with nodes := ao70.nodes.push ⟨2,16,17⟩}
abbrev ao64 : Mgr := {an64 with memo := ((PCSDD.BOp.or,3,12),18)::an64.memo}
theorem a64 : ApplyCertificate 12 DEFAULT_LIMITS 23 PCSDD.BOp.or 3 12 ai64 18 ao64 := by
  exact ApplyCertificate.branch (fuel := 22) (a0 := 3) (b0 := 12) (lo := 16) (hi := 17) (r := 18) (op := PCSDD.BOp.or) (m := ai64) (m1 := ao65) (m2 := ao70) (m3 := an64) (by decide) (by rfl) (by decide) a65 a70 (by rfl)
abbrev an56 : Mgr := {ao64 with nodes := ao64.nodes.push ⟨1,15,18⟩}
abbrev ao56 : Mgr := {an56 with memo := ((PCSDD.BOp.or,3,13),19)::an56.memo}
theorem a56 : ApplyCertificate 12 DEFAULT_LIMITS 24 PCSDD.BOp.or 3 13 ai56 19 ao56 := by
  exact ApplyCertificate.branch (fuel := 23) (a0 := 3) (b0 := 13) (lo := 15) (hi := 18) (r := 19) (op := PCSDD.BOp.or) (m := ai56) (m1 := ao57) (m2 := ao64) (m3 := an56) (by decide) (by rfl) (by decide) a57 a64 (by rfl)
abbrev an48 : Mgr := {ao56 with nodes := ao56.nodes.push ⟨0,13,19⟩}
abbrev ao48 : Mgr := {an48 with memo := ((PCSDD.BOp.or,4,13),20)::an48.memo}
theorem a48 : ApplyCertificate 12 DEFAULT_LIMITS 25 PCSDD.BOp.or 4 13 ai48 20 ao48 := by
  exact ApplyCertificate.branch (fuel := 24) (a0 := 4) (b0 := 13) (lo := 13) (hi := 19) (r := 20) (op := PCSDD.BOp.or) (m := ai48) (m1 := ao49) (m2 := ao56) (m3 := an48) (by decide) (by rfl) (by decide) a49 a56 (by rfl)
abbrev o1 : Mgr := ao48
theorem c1 : CompileCertificate 12 DEFAULT_LIMITS f1 i1 20 o1 := by
  exact CompileCertificate.or (fuel := 25) (m := i1) (ma := o2) (mb := o12) (out := o1) (x := 4) (y := 13) (r := 20) c2 c12 (ApplyCertificate.sound (m := o12) (out := ao48) a48) (by decide)
abbrev f75 : BForm 12 := PCSOmega.BForm.or   (PCSOmega.BForm.and (PCSOmega.BForm.atom 3) (PCSOmega.BForm.atom 9))   (PCSOmega.BForm.or     (PCSOmega.BForm.and (PCSOmega.BForm.atom 4) (PCSOmega.BForm.atom 10))     (PCSOmega.BForm.and (PCSOmega.BForm.atom 5) (PCSOmega.BForm.atom 11)))
abbrev i75 : Mgr := { nodes := #[{ var := 0, low := 0, high := 1 }, { var := 6, low := 0, high := 1 }, { var := 0, low := 0, high := 3 },              { var := 1, low := 0, high := 1 }, { var := 7, low := 0, high := 1 }, { var := 1, low := 0, high := 6 },              { var := 2, low := 0, high := 1 }, { var := 8, low := 0, high := 1 }, { var := 2, low := 0, high := 9 },              { var := 7, low := 9, high := 1 }, { var := 2, low := 6, high := 11 }, { var := 1, low := 10, high := 12 },              { var := 6, low := 9, high := 1 }, { var := 2, low := 3, high := 14 }, { var := 6, low := 6, high := 1 },              { var := 6, low := 11, high := 1 }, { var := 2, low := 16, high := 17 },              { var := 1, low := 15, high := 18 }, { var := 0, low := 13, high := 19 }],   memo := [((PCSDD.BOp.or, 4, 13), 20),            ((PCSDD.BOp.or, 3, 13), 19),            ((PCSDD.BOp.or, 3, 12), 18),            ((PCSDD.BOp.or, 3, 11), 17),            ((PCSDD.BOp.or, 1, 11), 1),            ((PCSDD.BOp.or, 3, 6), 16),            ((PCSDD.BOp.or, 1, 6), 1),            ((PCSDD.BOp.or, 3, 10), 15),            ((PCSDD.BOp.or, 3, 9), 14),            ((PCSDD.BOp.or, 0, 3), 3),            ((PCSDD.BOp.or, 0, 13), 13),            ((PCSDD.BOp.or, 0, 12), 12),            ((PCSDD.BOp.or, 0, 11), 11),            ((PCSDD.BOp.or, 7, 10), 13),            ((PCSDD.BOp.or, 6, 10), 12),            ((PCSDD.BOp.or, 6, 9), 11),            ((PCSDD.BOp.or, 1, 9), 1),            ((PCSDD.BOp.or, 1, 1), 1),            ((PCSDD.BOp.or, 0, 6), 6),            ((PCSDD.BOp.or, 0, 10), 10),            ((PCSDD.BOp.or, 0, 9), 9),            ((PCSDD.BOp.or, 0, 1), 1),            ((PCSDD.BOp.or, 0, 0), 0),            ((PCSDD.BOp.and, 8, 9), 10),            ((PCSDD.BOp.and, 1, 9), 9),            ((PCSDD.BOp.and, 0, 9), 0),            ((PCSDD.BOp.and, 5, 6), 7),            ((PCSDD.BOp.and, 1, 6), 6),            ((PCSDD.BOp.and, 0, 6), 0),            ((PCSDD.BOp.and, 2, 3), 4),            ((PCSDD.BOp.and, 1, 3), 3),            ((PCSDD.BOp.and, 1, 1), 1),            ((PCSDD.BOp.and, 0, 3), 0),            ((PCSDD.BOp.and, 0, 1), 0),            ((PCSDD.BOp.and, 0, 0), 0)],   ops := 63,   visits := 12,   wsteps := 0 }
abbrev f76 : BForm 12 := PCSOmega.BForm.and (PCSOmega.BForm.atom 3) (PCSOmega.BForm.atom 9)
abbrev i76 : Mgr := { nodes := #[{ var := 0, low := 0, high := 1 }, { var := 6, low := 0, high := 1 }, { var := 0, low := 0, high := 3 },              { var := 1, low := 0, high := 1 }, { var := 7, low := 0, high := 1 }, { var := 1, low := 0, high := 6 },              { var := 2, low := 0, high := 1 }, { var := 8, low := 0, high := 1 }, { var := 2, low := 0, high := 9 },              { var := 7, low := 9, high := 1 }, { var := 2, low := 6, high := 11 }, { var := 1, low := 10, high := 12 },              { var := 6, low := 9, high := 1 }, { var := 2, low := 3, high := 14 }, { var := 6, low := 6, high := 1 },              { var := 6, low := 11, high := 1 }, { var := 2, low := 16, high := 17 },              { var := 1, low := 15, high := 18 }, { var := 0, low := 13, high := 19 }],   memo := [((PCSDD.BOp.or, 4, 13), 20),            ((PCSDD.BOp.or, 3, 13), 19),            ((PCSDD.BOp.or, 3, 12), 18),            ((PCSDD.BOp.or, 3, 11), 17),            ((PCSDD.BOp.or, 1, 11), 1),            ((PCSDD.BOp.or, 3, 6), 16),            ((PCSDD.BOp.or, 1, 6), 1),            ((PCSDD.BOp.or, 3, 10), 15),            ((PCSDD.BOp.or, 3, 9), 14),            ((PCSDD.BOp.or, 0, 3), 3),            ((PCSDD.BOp.or, 0, 13), 13),            ((PCSDD.BOp.or, 0, 12), 12),            ((PCSDD.BOp.or, 0, 11), 11),            ((PCSDD.BOp.or, 7, 10), 13),            ((PCSDD.BOp.or, 6, 10), 12),            ((PCSDD.BOp.or, 6, 9), 11),            ((PCSDD.BOp.or, 1, 9), 1),            ((PCSDD.BOp.or, 1, 1), 1),            ((PCSDD.BOp.or, 0, 6), 6),            ((PCSDD.BOp.or, 0, 10), 10),            ((PCSDD.BOp.or, 0, 9), 9),            ((PCSDD.BOp.or, 0, 1), 1),            ((PCSDD.BOp.or, 0, 0), 0),            ((PCSDD.BOp.and, 8, 9), 10),            ((PCSDD.BOp.and, 1, 9), 9),            ((PCSDD.BOp.and, 0, 9), 0),            ((PCSDD.BOp.and, 5, 6), 7),            ((PCSDD.BOp.and, 1, 6), 6),            ((PCSDD.BOp.and, 0, 6), 0),            ((PCSDD.BOp.and, 2, 3), 4),            ((PCSDD.BOp.and, 1, 3), 3),            ((PCSDD.BOp.and, 1, 1), 1),            ((PCSDD.BOp.and, 0, 3), 0),            ((PCSDD.BOp.and, 0, 1), 0),            ((PCSDD.BOp.and, 0, 0), 0)],   ops := 63,   visits := 13,   wsteps := 0 }
abbrev f77 : BForm 12 := PCSOmega.BForm.atom 3
abbrev i77 : Mgr := { nodes := #[{ var := 0, low := 0, high := 1 }, { var := 6, low := 0, high := 1 }, { var := 0, low := 0, high := 3 },              { var := 1, low := 0, high := 1 }, { var := 7, low := 0, high := 1 }, { var := 1, low := 0, high := 6 },              { var := 2, low := 0, high := 1 }, { var := 8, low := 0, high := 1 }, { var := 2, low := 0, high := 9 },              { var := 7, low := 9, high := 1 }, { var := 2, low := 6, high := 11 }, { var := 1, low := 10, high := 12 },              { var := 6, low := 9, high := 1 }, { var := 2, low := 3, high := 14 }, { var := 6, low := 6, high := 1 },              { var := 6, low := 11, high := 1 }, { var := 2, low := 16, high := 17 },              { var := 1, low := 15, high := 18 }, { var := 0, low := 13, high := 19 }],   memo := [((PCSDD.BOp.or, 4, 13), 20),            ((PCSDD.BOp.or, 3, 13), 19),            ((PCSDD.BOp.or, 3, 12), 18),            ((PCSDD.BOp.or, 3, 11), 17),            ((PCSDD.BOp.or, 1, 11), 1),            ((PCSDD.BOp.or, 3, 6), 16),            ((PCSDD.BOp.or, 1, 6), 1),            ((PCSDD.BOp.or, 3, 10), 15),            ((PCSDD.BOp.or, 3, 9), 14),            ((PCSDD.BOp.or, 0, 3), 3),            ((PCSDD.BOp.or, 0, 13), 13),            ((PCSDD.BOp.or, 0, 12), 12),            ((PCSDD.BOp.or, 0, 11), 11),            ((PCSDD.BOp.or, 7, 10), 13),            ((PCSDD.BOp.or, 6, 10), 12),            ((PCSDD.BOp.or, 6, 9), 11),            ((PCSDD.BOp.or, 1, 9), 1),            ((PCSDD.BOp.or, 1, 1), 1),            ((PCSDD.BOp.or, 0, 6), 6),            ((PCSDD.BOp.or, 0, 10), 10),            ((PCSDD.BOp.or, 0, 9), 9),            ((PCSDD.BOp.or, 0, 1), 1),            ((PCSDD.BOp.or, 0, 0), 0),            ((PCSDD.BOp.and, 8, 9), 10),            ((PCSDD.BOp.and, 1, 9), 9),            ((PCSDD.BOp.and, 0, 9), 0),            ((PCSDD.BOp.and, 5, 6), 7),            ((PCSDD.BOp.and, 1, 6), 6),            ((PCSDD.BOp.and, 0, 6), 0),            ((PCSDD.BOp.and, 2, 3), 4),            ((PCSDD.BOp.and, 1, 3), 3),            ((PCSDD.BOp.and, 1, 1), 1),            ((PCSDD.BOp.and, 0, 3), 0),            ((PCSDD.BOp.and, 0, 1), 0),            ((PCSDD.BOp.and, 0, 0), 0)],   ops := 63,   visits := 14,   wsteps := 0 }
abbrev o77 : Mgr := { nodes := #[{ var := 0, low := 0, high := 1 }, { var := 6, low := 0, high := 1 }, { var := 0, low := 0, high := 3 },              { var := 1, low := 0, high := 1 }, { var := 7, low := 0, high := 1 }, { var := 1, low := 0, high := 6 },              { var := 2, low := 0, high := 1 }, { var := 8, low := 0, high := 1 }, { var := 2, low := 0, high := 9 },              { var := 7, low := 9, high := 1 }, { var := 2, low := 6, high := 11 }, { var := 1, low := 10, high := 12 },              { var := 6, low := 9, high := 1 }, { var := 2, low := 3, high := 14 }, { var := 6, low := 6, high := 1 },              { var := 6, low := 11, high := 1 }, { var := 2, low := 16, high := 17 },              { var := 1, low := 15, high := 18 }, { var := 0, low := 13, high := 19 },              { var := 3, low := 0, high := 1 }],   memo := [((PCSDD.BOp.or, 4, 13), 20),            ((PCSDD.BOp.or, 3, 13), 19),            ((PCSDD.BOp.or, 3, 12), 18),            ((PCSDD.BOp.or, 3, 11), 17),            ((PCSDD.BOp.or, 1, 11), 1),            ((PCSDD.BOp.or, 3, 6), 16),            ((PCSDD.BOp.or, 1, 6), 1),            ((PCSDD.BOp.or, 3, 10), 15),            ((PCSDD.BOp.or, 3, 9), 14),            ((PCSDD.BOp.or, 0, 3), 3),            ((PCSDD.BOp.or, 0, 13), 13),            ((PCSDD.BOp.or, 0, 12), 12),            ((PCSDD.BOp.or, 0, 11), 11),            ((PCSDD.BOp.or, 7, 10), 13),            ((PCSDD.BOp.or, 6, 10), 12),            ((PCSDD.BOp.or, 6, 9), 11),            ((PCSDD.BOp.or, 1, 9), 1),            ((PCSDD.BOp.or, 1, 1), 1),            ((PCSDD.BOp.or, 0, 6), 6),            ((PCSDD.BOp.or, 0, 10), 10),            ((PCSDD.BOp.or, 0, 9), 9),            ((PCSDD.BOp.or, 0, 1), 1),            ((PCSDD.BOp.or, 0, 0), 0),            ((PCSDD.BOp.and, 8, 9), 10),            ((PCSDD.BOp.and, 1, 9), 9),            ((PCSDD.BOp.and, 0, 9), 0),            ((PCSDD.BOp.and, 5, 6), 7),            ((PCSDD.BOp.and, 1, 6), 6),            ((PCSDD.BOp.and, 0, 6), 0),            ((PCSDD.BOp.and, 2, 3), 4),            ((PCSDD.BOp.and, 1, 3), 3),            ((PCSDD.BOp.and, 1, 1), 1),            ((PCSDD.BOp.and, 0, 3), 0),            ((PCSDD.BOp.and, 0, 1), 0),            ((PCSDD.BOp.and, 0, 0), 0)],   ops := 63,   visits := 15,   wsteps := 0 }
theorem c77 : CompileCertificate 12 DEFAULT_LIMITS f77 i77 21 o77 := by
  exact CompileCertificate.atom (by rfl)
abbrev f78 : BForm 12 := PCSOmega.BForm.atom 9
abbrev i78 : Mgr := { nodes := #[{ var := 0, low := 0, high := 1 }, { var := 6, low := 0, high := 1 }, { var := 0, low := 0, high := 3 },              { var := 1, low := 0, high := 1 }, { var := 7, low := 0, high := 1 }, { var := 1, low := 0, high := 6 },              { var := 2, low := 0, high := 1 }, { var := 8, low := 0, high := 1 }, { var := 2, low := 0, high := 9 },              { var := 7, low := 9, high := 1 }, { var := 2, low := 6, high := 11 }, { var := 1, low := 10, high := 12 },              { var := 6, low := 9, high := 1 }, { var := 2, low := 3, high := 14 }, { var := 6, low := 6, high := 1 },              { var := 6, low := 11, high := 1 }, { var := 2, low := 16, high := 17 },              { var := 1, low := 15, high := 18 }, { var := 0, low := 13, high := 19 },              { var := 3, low := 0, high := 1 }],   memo := [((PCSDD.BOp.or, 4, 13), 20),            ((PCSDD.BOp.or, 3, 13), 19),            ((PCSDD.BOp.or, 3, 12), 18),            ((PCSDD.BOp.or, 3, 11), 17),            ((PCSDD.BOp.or, 1, 11), 1),            ((PCSDD.BOp.or, 3, 6), 16),            ((PCSDD.BOp.or, 1, 6), 1),            ((PCSDD.BOp.or, 3, 10), 15),            ((PCSDD.BOp.or, 3, 9), 14),            ((PCSDD.BOp.or, 0, 3), 3),            ((PCSDD.BOp.or, 0, 13), 13),            ((PCSDD.BOp.or, 0, 12), 12),            ((PCSDD.BOp.or, 0, 11), 11),            ((PCSDD.BOp.or, 7, 10), 13),            ((PCSDD.BOp.or, 6, 10), 12),            ((PCSDD.BOp.or, 6, 9), 11),            ((PCSDD.BOp.or, 1, 9), 1),            ((PCSDD.BOp.or, 1, 1), 1),            ((PCSDD.BOp.or, 0, 6), 6),            ((PCSDD.BOp.or, 0, 10), 10),            ((PCSDD.BOp.or, 0, 9), 9),            ((PCSDD.BOp.or, 0, 1), 1),            ((PCSDD.BOp.or, 0, 0), 0),            ((PCSDD.BOp.and, 8, 9), 10),            ((PCSDD.BOp.and, 1, 9), 9),            ((PCSDD.BOp.and, 0, 9), 0),            ((PCSDD.BOp.and, 5, 6), 7),            ((PCSDD.BOp.and, 1, 6), 6),            ((PCSDD.BOp.and, 0, 6), 0),            ((PCSDD.BOp.and, 2, 3), 4),            ((PCSDD.BOp.and, 1, 3), 3),            ((PCSDD.BOp.and, 1, 1), 1),            ((PCSDD.BOp.and, 0, 3), 0),            ((PCSDD.BOp.and, 0, 1), 0),            ((PCSDD.BOp.and, 0, 0), 0)],   ops := 63,   visits := 15,   wsteps := 0 }
abbrev o78 : Mgr := { nodes := #[{ var := 0, low := 0, high := 1 }, { var := 6, low := 0, high := 1 }, { var := 0, low := 0, high := 3 },              { var := 1, low := 0, high := 1 }, { var := 7, low := 0, high := 1 }, { var := 1, low := 0, high := 6 },              { var := 2, low := 0, high := 1 }, { var := 8, low := 0, high := 1 }, { var := 2, low := 0, high := 9 },              { var := 7, low := 9, high := 1 }, { var := 2, low := 6, high := 11 }, { var := 1, low := 10, high := 12 },              { var := 6, low := 9, high := 1 }, { var := 2, low := 3, high := 14 }, { var := 6, low := 6, high := 1 },              { var := 6, low := 11, high := 1 }, { var := 2, low := 16, high := 17 },              { var := 1, low := 15, high := 18 }, { var := 0, low := 13, high := 19 },              { var := 3, low := 0, high := 1 }, { var := 9, low := 0, high := 1 }],   memo := [((PCSDD.BOp.or, 4, 13), 20),            ((PCSDD.BOp.or, 3, 13), 19),            ((PCSDD.BOp.or, 3, 12), 18),            ((PCSDD.BOp.or, 3, 11), 17),            ((PCSDD.BOp.or, 1, 11), 1),            ((PCSDD.BOp.or, 3, 6), 16),            ((PCSDD.BOp.or, 1, 6), 1),            ((PCSDD.BOp.or, 3, 10), 15),            ((PCSDD.BOp.or, 3, 9), 14),            ((PCSDD.BOp.or, 0, 3), 3),            ((PCSDD.BOp.or, 0, 13), 13),            ((PCSDD.BOp.or, 0, 12), 12),            ((PCSDD.BOp.or, 0, 11), 11),            ((PCSDD.BOp.or, 7, 10), 13),            ((PCSDD.BOp.or, 6, 10), 12),            ((PCSDD.BOp.or, 6, 9), 11),            ((PCSDD.BOp.or, 1, 9), 1),            ((PCSDD.BOp.or, 1, 1), 1),            ((PCSDD.BOp.or, 0, 6), 6),            ((PCSDD.BOp.or, 0, 10), 10),            ((PCSDD.BOp.or, 0, 9), 9),            ((PCSDD.BOp.or, 0, 1), 1),            ((PCSDD.BOp.or, 0, 0), 0),            ((PCSDD.BOp.and, 8, 9), 10),            ((PCSDD.BOp.and, 1, 9), 9),            ((PCSDD.BOp.and, 0, 9), 0),            ((PCSDD.BOp.and, 5, 6), 7),            ((PCSDD.BOp.and, 1, 6), 6),            ((PCSDD.BOp.and, 0, 6), 0),            ((PCSDD.BOp.and, 2, 3), 4),            ((PCSDD.BOp.and, 1, 3), 3),            ((PCSDD.BOp.and, 1, 1), 1),            ((PCSDD.BOp.and, 0, 3), 0),            ((PCSDD.BOp.and, 0, 1), 0),            ((PCSDD.BOp.and, 0, 0), 0)],   ops := 63,   visits := 16,   wsteps := 0 }
theorem c78 : CompileCertificate 12 DEFAULT_LIMITS f78 i78 22 o78 := by
  exact CompileCertificate.atom (by rfl)
abbrev ai79 : Mgr := o78
abbrev ai80 : Mgr := {ai79 with ops := ai79.ops+1}
abbrev ai81 : Mgr := {ai80 with ops := ai80.ops+1}
abbrev ao81 : Mgr := {ai81 with ops := ai81.ops+1}
theorem a81 : ApplyCertificate 12 DEFAULT_LIMITS 23 PCSDD.BOp.and 0 0 ai81 0 ao81 := by
  exact ApplyCertificate.hit (fuel := 22) (a0 := 0) (b0 := 0) (r := 0) (op := PCSDD.BOp.and) (m := ai81) (by decide) (by rfl)
abbrev ai82 : Mgr := ao81
abbrev ao82 : Mgr := {ai82 with ops := ai82.ops+1}
theorem a82 : ApplyCertificate 12 DEFAULT_LIMITS 23 PCSDD.BOp.and 0 1 ai82 0 ao82 := by
  exact ApplyCertificate.hit (fuel := 22) (a0 := 0) (b0 := 1) (r := 0) (op := PCSDD.BOp.and) (m := ai82) (by decide) (by rfl)
abbrev an80 : Mgr := ao82
abbrev ao80 : Mgr := {an80 with memo := ((PCSDD.BOp.and,0,22),0)::an80.memo}
theorem a80 : ApplyCertificate 12 DEFAULT_LIMITS 24 PCSDD.BOp.and 0 22 ai80 0 ao80 := by
  exact ApplyCertificate.branch (fuel := 23) (a0 := 0) (b0 := 22) (lo := 0) (hi := 0) (r := 0) (op := PCSDD.BOp.and) (m := ai80) (m1 := ao81) (m2 := ao82) (m3 := an80) (by decide) (by rfl) (by decide) a81 a82 (by rfl)
abbrev ai83 : Mgr := ao80
abbrev ai84 : Mgr := {ai83 with ops := ai83.ops+1}
abbrev ao84 : Mgr := {ai84 with ops := ai84.ops+1}
theorem a84 : ApplyCertificate 12 DEFAULT_LIMITS 23 PCSDD.BOp.and 1 0 ai84 0 ao84 := by
  exact ApplyCertificate.hit (fuel := 22) (a0 := 1) (b0 := 0) (r := 0) (op := PCSDD.BOp.and) (m := ai84) (by decide) (by rfl)
abbrev ai85 : Mgr := ao84
abbrev ao85 : Mgr := {ai85 with ops := ai85.ops+1}
theorem a85 : ApplyCertificate 12 DEFAULT_LIMITS 23 PCSDD.BOp.and 1 1 ai85 1 ao85 := by
  exact ApplyCertificate.hit (fuel := 22) (a0 := 1) (b0 := 1) (r := 1) (op := PCSDD.BOp.and) (m := ai85) (by decide) (by rfl)
abbrev an83 : Mgr := ao85
abbrev ao83 : Mgr := {an83 with memo := ((PCSDD.BOp.and,1,22),22)::an83.memo}
theorem a83 : ApplyCertificate 12 DEFAULT_LIMITS 24 PCSDD.BOp.and 1 22 ai83 22 ao83 := by
  exact ApplyCertificate.branch (fuel := 23) (a0 := 1) (b0 := 22) (lo := 0) (hi := 1) (r := 22) (op := PCSDD.BOp.and) (m := ai83) (m1 := ao84) (m2 := ao85) (m3 := an83) (by decide) (by rfl) (by decide) a84 a85 (by rfl)
abbrev an79 : Mgr := {ao83 with nodes := ao83.nodes.push ⟨3,0,22⟩}
abbrev ao79 : Mgr := {an79 with memo := ((PCSDD.BOp.and,21,22),23)::an79.memo}
theorem a79 : ApplyCertificate 12 DEFAULT_LIMITS 25 PCSDD.BOp.and 21 22 ai79 23 ao79 := by
  exact ApplyCertificate.branch (fuel := 24) (a0 := 21) (b0 := 22) (lo := 0) (hi := 22) (r := 23) (op := PCSDD.BOp.and) (m := ai79) (m1 := ao80) (m2 := ao83) (m3 := an79) (by decide) (by rfl) (by decide) a80 a83 (by rfl)
abbrev o76 : Mgr := ao79
theorem c76 : CompileCertificate 12 DEFAULT_LIMITS f76 i76 23 o76 := by
  exact CompileCertificate.and (fuel := 25) (m := i76) (ma := o77) (mb := o78) (out := o76) (x := 21) (y := 22) (r := 23) c77 c78 (ApplyCertificate.sound (m := o78) (out := ao79) a79) (by decide)
abbrev f86 : BForm 12 := PCSOmega.BForm.or   (PCSOmega.BForm.and (PCSOmega.BForm.atom 4) (PCSOmega.BForm.atom 10))   (PCSOmega.BForm.and (PCSOmega.BForm.atom 5) (PCSOmega.BForm.atom 11))
abbrev i86 : Mgr := { nodes := #[{ var := 0, low := 0, high := 1 }, { var := 6, low := 0, high := 1 }, { var := 0, low := 0, high := 3 },              { var := 1, low := 0, high := 1 }, { var := 7, low := 0, high := 1 }, { var := 1, low := 0, high := 6 },              { var := 2, low := 0, high := 1 }, { var := 8, low := 0, high := 1 }, { var := 2, low := 0, high := 9 },              { var := 7, low := 9, high := 1 }, { var := 2, low := 6, high := 11 }, { var := 1, low := 10, high := 12 },              { var := 6, low := 9, high := 1 }, { var := 2, low := 3, high := 14 }, { var := 6, low := 6, high := 1 },              { var := 6, low := 11, high := 1 }, { var := 2, low := 16, high := 17 },              { var := 1, low := 15, high := 18 }, { var := 0, low := 13, high := 19 },              { var := 3, low := 0, high := 1 }, { var := 9, low := 0, high := 1 }, { var := 3, low := 0, high := 22 }],   memo := [((PCSDD.BOp.and, 21, 22), 23),            ((PCSDD.BOp.and, 1, 22), 22),            ((PCSDD.BOp.and, 0, 22), 0),            ((PCSDD.BOp.or, 4, 13), 20),            ((PCSDD.BOp.or, 3, 13), 19),            ((PCSDD.BOp.or, 3, 12), 18),            ((PCSDD.BOp.or, 3, 11), 17),            ((PCSDD.BOp.or, 1, 11), 1),            ((PCSDD.BOp.or, 3, 6), 16),            ((PCSDD.BOp.or, 1, 6), 1),            ((PCSDD.BOp.or, 3, 10), 15),            ((PCSDD.BOp.or, 3, 9), 14),            ((PCSDD.BOp.or, 0, 3), 3),            ((PCSDD.BOp.or, 0, 13), 13),            ((PCSDD.BOp.or, 0, 12), 12),            ((PCSDD.BOp.or, 0, 11), 11),            ((PCSDD.BOp.or, 7, 10), 13),            ((PCSDD.BOp.or, 6, 10), 12),            ((PCSDD.BOp.or, 6, 9), 11),            ((PCSDD.BOp.or, 1, 9), 1),            ((PCSDD.BOp.or, 1, 1), 1),            ((PCSDD.BOp.or, 0, 6), 6),            ((PCSDD.BOp.or, 0, 10), 10),            ((PCSDD.BOp.or, 0, 9), 9),            ((PCSDD.BOp.or, 0, 1), 1),            ((PCSDD.BOp.or, 0, 0), 0),            ((PCSDD.BOp.and, 8, 9), 10),            ((PCSDD.BOp.and, 1, 9), 9),            ((PCSDD.BOp.and, 0, 9), 0),            ((PCSDD.BOp.and, 5, 6), 7),            ((PCSDD.BOp.and, 1, 6), 6),            ((PCSDD.BOp.and, 0, 6), 0),            ((PCSDD.BOp.and, 2, 3), 4),            ((PCSDD.BOp.and, 1, 3), 3),            ((PCSDD.BOp.and, 1, 1), 1),            ((PCSDD.BOp.and, 0, 3), 0),            ((PCSDD.BOp.and, 0, 1), 0),            ((PCSDD.BOp.and, 0, 0), 0)],   ops := 70,   visits := 16,   wsteps := 0 }
abbrev f87 : BForm 12 := PCSOmega.BForm.and (PCSOmega.BForm.atom 4) (PCSOmega.BForm.atom 10)
abbrev i87 : Mgr := { nodes := #[{ var := 0, low := 0, high := 1 }, { var := 6, low := 0, high := 1 }, { var := 0, low := 0, high := 3 },              { var := 1, low := 0, high := 1 }, { var := 7, low := 0, high := 1 }, { var := 1, low := 0, high := 6 },              { var := 2, low := 0, high := 1 }, { var := 8, low := 0, high := 1 }, { var := 2, low := 0, high := 9 },              { var := 7, low := 9, high := 1 }, { var := 2, low := 6, high := 11 }, { var := 1, low := 10, high := 12 },              { var := 6, low := 9, high := 1 }, { var := 2, low := 3, high := 14 }, { var := 6, low := 6, high := 1 },              { var := 6, low := 11, high := 1 }, { var := 2, low := 16, high := 17 },              { var := 1, low := 15, high := 18 }, { var := 0, low := 13, high := 19 },              { var := 3, low := 0, high := 1 }, { var := 9, low := 0, high := 1 }, { var := 3, low := 0, high := 22 }],   memo := [((PCSDD.BOp.and, 21, 22), 23),            ((PCSDD.BOp.and, 1, 22), 22),            ((PCSDD.BOp.and, 0, 22), 0),            ((PCSDD.BOp.or, 4, 13), 20),            ((PCSDD.BOp.or, 3, 13), 19),            ((PCSDD.BOp.or, 3, 12), 18),            ((PCSDD.BOp.or, 3, 11), 17),            ((PCSDD.BOp.or, 1, 11), 1),            ((PCSDD.BOp.or, 3, 6), 16),            ((PCSDD.BOp.or, 1, 6), 1),            ((PCSDD.BOp.or, 3, 10), 15),            ((PCSDD.BOp.or, 3, 9), 14),            ((PCSDD.BOp.or, 0, 3), 3),            ((PCSDD.BOp.or, 0, 13), 13),            ((PCSDD.BOp.or, 0, 12), 12),            ((PCSDD.BOp.or, 0, 11), 11),            ((PCSDD.BOp.or, 7, 10), 13),            ((PCSDD.BOp.or, 6, 10), 12),            ((PCSDD.BOp.or, 6, 9), 11),            ((PCSDD.BOp.or, 1, 9), 1),            ((PCSDD.BOp.or, 1, 1), 1),            ((PCSDD.BOp.or, 0, 6), 6),            ((PCSDD.BOp.or, 0, 10), 10),            ((PCSDD.BOp.or, 0, 9), 9),            ((PCSDD.BOp.or, 0, 1), 1),            ((PCSDD.BOp.or, 0, 0), 0),            ((PCSDD.BOp.and, 8, 9), 10),            ((PCSDD.BOp.and, 1, 9), 9),            ((PCSDD.BOp.and, 0, 9), 0),            ((PCSDD.BOp.and, 5, 6), 7),            ((PCSDD.BOp.and, 1, 6), 6),            ((PCSDD.BOp.and, 0, 6), 0),            ((PCSDD.BOp.and, 2, 3), 4),            ((PCSDD.BOp.and, 1, 3), 3),            ((PCSDD.BOp.and, 1, 1), 1),            ((PCSDD.BOp.and, 0, 3), 0),            ((PCSDD.BOp.and, 0, 1), 0),            ((PCSDD.BOp.and, 0, 0), 0)],   ops := 70,   visits := 17,   wsteps := 0 }
abbrev f88 : BForm 12 := PCSOmega.BForm.atom 4
abbrev i88 : Mgr := { nodes := #[{ var := 0, low := 0, high := 1 }, { var := 6, low := 0, high := 1 }, { var := 0, low := 0, high := 3 },              { var := 1, low := 0, high := 1 }, { var := 7, low := 0, high := 1 }, { var := 1, low := 0, high := 6 },              { var := 2, low := 0, high := 1 }, { var := 8, low := 0, high := 1 }, { var := 2, low := 0, high := 9 },              { var := 7, low := 9, high := 1 }, { var := 2, low := 6, high := 11 }, { var := 1, low := 10, high := 12 },              { var := 6, low := 9, high := 1 }, { var := 2, low := 3, high := 14 }, { var := 6, low := 6, high := 1 },              { var := 6, low := 11, high := 1 }, { var := 2, low := 16, high := 17 },              { var := 1, low := 15, high := 18 }, { var := 0, low := 13, high := 19 },              { var := 3, low := 0, high := 1 }, { var := 9, low := 0, high := 1 }, { var := 3, low := 0, high := 22 }],   memo := [((PCSDD.BOp.and, 21, 22), 23),            ((PCSDD.BOp.and, 1, 22), 22),            ((PCSDD.BOp.and, 0, 22), 0),            ((PCSDD.BOp.or, 4, 13), 20),            ((PCSDD.BOp.or, 3, 13), 19),            ((PCSDD.BOp.or, 3, 12), 18),            ((PCSDD.BOp.or, 3, 11), 17),            ((PCSDD.BOp.or, 1, 11), 1),            ((PCSDD.BOp.or, 3, 6), 16),            ((PCSDD.BOp.or, 1, 6), 1),            ((PCSDD.BOp.or, 3, 10), 15),            ((PCSDD.BOp.or, 3, 9), 14),            ((PCSDD.BOp.or, 0, 3), 3),            ((PCSDD.BOp.or, 0, 13), 13),            ((PCSDD.BOp.or, 0, 12), 12),            ((PCSDD.BOp.or, 0, 11), 11),            ((PCSDD.BOp.or, 7, 10), 13),            ((PCSDD.BOp.or, 6, 10), 12),            ((PCSDD.BOp.or, 6, 9), 11),            ((PCSDD.BOp.or, 1, 9), 1),            ((PCSDD.BOp.or, 1, 1), 1),            ((PCSDD.BOp.or, 0, 6), 6),            ((PCSDD.BOp.or, 0, 10), 10),            ((PCSDD.BOp.or, 0, 9), 9),            ((PCSDD.BOp.or, 0, 1), 1),            ((PCSDD.BOp.or, 0, 0), 0),            ((PCSDD.BOp.and, 8, 9), 10),            ((PCSDD.BOp.and, 1, 9), 9),            ((PCSDD.BOp.and, 0, 9), 0),            ((PCSDD.BOp.and, 5, 6), 7),            ((PCSDD.BOp.and, 1, 6), 6),            ((PCSDD.BOp.and, 0, 6), 0),            ((PCSDD.BOp.and, 2, 3), 4),            ((PCSDD.BOp.and, 1, 3), 3),            ((PCSDD.BOp.and, 1, 1), 1),            ((PCSDD.BOp.and, 0, 3), 0),            ((PCSDD.BOp.and, 0, 1), 0),            ((PCSDD.BOp.and, 0, 0), 0)],   ops := 70,   visits := 18,   wsteps := 0 }
abbrev o88 : Mgr := { nodes := #[{ var := 0, low := 0, high := 1 }, { var := 6, low := 0, high := 1 }, { var := 0, low := 0, high := 3 },              { var := 1, low := 0, high := 1 }, { var := 7, low := 0, high := 1 }, { var := 1, low := 0, high := 6 },              { var := 2, low := 0, high := 1 }, { var := 8, low := 0, high := 1 }, { var := 2, low := 0, high := 9 },              { var := 7, low := 9, high := 1 }, { var := 2, low := 6, high := 11 }, { var := 1, low := 10, high := 12 },              { var := 6, low := 9, high := 1 }, { var := 2, low := 3, high := 14 }, { var := 6, low := 6, high := 1 },              { var := 6, low := 11, high := 1 }, { var := 2, low := 16, high := 17 },              { var := 1, low := 15, high := 18 }, { var := 0, low := 13, high := 19 },              { var := 3, low := 0, high := 1 }, { var := 9, low := 0, high := 1 }, { var := 3, low := 0, high := 22 },              { var := 4, low := 0, high := 1 }],   memo := [((PCSDD.BOp.and, 21, 22), 23),            ((PCSDD.BOp.and, 1, 22), 22),            ((PCSDD.BOp.and, 0, 22), 0),            ((PCSDD.BOp.or, 4, 13), 20),            ((PCSDD.BOp.or, 3, 13), 19),            ((PCSDD.BOp.or, 3, 12), 18),            ((PCSDD.BOp.or, 3, 11), 17),            ((PCSDD.BOp.or, 1, 11), 1),            ((PCSDD.BOp.or, 3, 6), 16),            ((PCSDD.BOp.or, 1, 6), 1),            ((PCSDD.BOp.or, 3, 10), 15),            ((PCSDD.BOp.or, 3, 9), 14),            ((PCSDD.BOp.or, 0, 3), 3),            ((PCSDD.BOp.or, 0, 13), 13),            ((PCSDD.BOp.or, 0, 12), 12),            ((PCSDD.BOp.or, 0, 11), 11),            ((PCSDD.BOp.or, 7, 10), 13),            ((PCSDD.BOp.or, 6, 10), 12),            ((PCSDD.BOp.or, 6, 9), 11),            ((PCSDD.BOp.or, 1, 9), 1),            ((PCSDD.BOp.or, 1, 1), 1),            ((PCSDD.BOp.or, 0, 6), 6),            ((PCSDD.BOp.or, 0, 10), 10),            ((PCSDD.BOp.or, 0, 9), 9),            ((PCSDD.BOp.or, 0, 1), 1),            ((PCSDD.BOp.or, 0, 0), 0),            ((PCSDD.BOp.and, 8, 9), 10),            ((PCSDD.BOp.and, 1, 9), 9),            ((PCSDD.BOp.and, 0, 9), 0),            ((PCSDD.BOp.and, 5, 6), 7),            ((PCSDD.BOp.and, 1, 6), 6),            ((PCSDD.BOp.and, 0, 6), 0),            ((PCSDD.BOp.and, 2, 3), 4),            ((PCSDD.BOp.and, 1, 3), 3),            ((PCSDD.BOp.and, 1, 1), 1),            ((PCSDD.BOp.and, 0, 3), 0),            ((PCSDD.BOp.and, 0, 1), 0),            ((PCSDD.BOp.and, 0, 0), 0)],   ops := 70,   visits := 19,   wsteps := 0 }
theorem c88 : CompileCertificate 12 DEFAULT_LIMITS f88 i88 24 o88 := by
  exact CompileCertificate.atom (by rfl)
abbrev f89 : BForm 12 := PCSOmega.BForm.atom 10
abbrev i89 : Mgr := { nodes := #[{ var := 0, low := 0, high := 1 }, { var := 6, low := 0, high := 1 }, { var := 0, low := 0, high := 3 },              { var := 1, low := 0, high := 1 }, { var := 7, low := 0, high := 1 }, { var := 1, low := 0, high := 6 },              { var := 2, low := 0, high := 1 }, { var := 8, low := 0, high := 1 }, { var := 2, low := 0, high := 9 },              { var := 7, low := 9, high := 1 }, { var := 2, low := 6, high := 11 }, { var := 1, low := 10, high := 12 },              { var := 6, low := 9, high := 1 }, { var := 2, low := 3, high := 14 }, { var := 6, low := 6, high := 1 },              { var := 6, low := 11, high := 1 }, { var := 2, low := 16, high := 17 },              { var := 1, low := 15, high := 18 }, { var := 0, low := 13, high := 19 },              { var := 3, low := 0, high := 1 }, { var := 9, low := 0, high := 1 }, { var := 3, low := 0, high := 22 },              { var := 4, low := 0, high := 1 }],   memo := [((PCSDD.BOp.and, 21, 22), 23),            ((PCSDD.BOp.and, 1, 22), 22),            ((PCSDD.BOp.and, 0, 22), 0),            ((PCSDD.BOp.or, 4, 13), 20),            ((PCSDD.BOp.or, 3, 13), 19),            ((PCSDD.BOp.or, 3, 12), 18),            ((PCSDD.BOp.or, 3, 11), 17),            ((PCSDD.BOp.or, 1, 11), 1),            ((PCSDD.BOp.or, 3, 6), 16),            ((PCSDD.BOp.or, 1, 6), 1),            ((PCSDD.BOp.or, 3, 10), 15),            ((PCSDD.BOp.or, 3, 9), 14),            ((PCSDD.BOp.or, 0, 3), 3),            ((PCSDD.BOp.or, 0, 13), 13),            ((PCSDD.BOp.or, 0, 12), 12),            ((PCSDD.BOp.or, 0, 11), 11),            ((PCSDD.BOp.or, 7, 10), 13),            ((PCSDD.BOp.or, 6, 10), 12),            ((PCSDD.BOp.or, 6, 9), 11),            ((PCSDD.BOp.or, 1, 9), 1),            ((PCSDD.BOp.or, 1, 1), 1),            ((PCSDD.BOp.or, 0, 6), 6),            ((PCSDD.BOp.or, 0, 10), 10),            ((PCSDD.BOp.or, 0, 9), 9),            ((PCSDD.BOp.or, 0, 1), 1),            ((PCSDD.BOp.or, 0, 0), 0),            ((PCSDD.BOp.and, 8, 9), 10),            ((PCSDD.BOp.and, 1, 9), 9),            ((PCSDD.BOp.and, 0, 9), 0),            ((PCSDD.BOp.and, 5, 6), 7),            ((PCSDD.BOp.and, 1, 6), 6),            ((PCSDD.BOp.and, 0, 6), 0),            ((PCSDD.BOp.and, 2, 3), 4),            ((PCSDD.BOp.and, 1, 3), 3),            ((PCSDD.BOp.and, 1, 1), 1),            ((PCSDD.BOp.and, 0, 3), 0),            ((PCSDD.BOp.and, 0, 1), 0),            ((PCSDD.BOp.and, 0, 0), 0)],   ops := 70,   visits := 19,   wsteps := 0 }
abbrev o89 : Mgr := { nodes := #[{ var := 0, low := 0, high := 1 }, { var := 6, low := 0, high := 1 }, { var := 0, low := 0, high := 3 },              { var := 1, low := 0, high := 1 }, { var := 7, low := 0, high := 1 }, { var := 1, low := 0, high := 6 },              { var := 2, low := 0, high := 1 }, { var := 8, low := 0, high := 1 }, { var := 2, low := 0, high := 9 },              { var := 7, low := 9, high := 1 }, { var := 2, low := 6, high := 11 }, { var := 1, low := 10, high := 12 },              { var := 6, low := 9, high := 1 }, { var := 2, low := 3, high := 14 }, { var := 6, low := 6, high := 1 },              { var := 6, low := 11, high := 1 }, { var := 2, low := 16, high := 17 },              { var := 1, low := 15, high := 18 }, { var := 0, low := 13, high := 19 },              { var := 3, low := 0, high := 1 }, { var := 9, low := 0, high := 1 }, { var := 3, low := 0, high := 22 },              { var := 4, low := 0, high := 1 }, { var := 10, low := 0, high := 1 }],   memo := [((PCSDD.BOp.and, 21, 22), 23),            ((PCSDD.BOp.and, 1, 22), 22),            ((PCSDD.BOp.and, 0, 22), 0),            ((PCSDD.BOp.or, 4, 13), 20),            ((PCSDD.BOp.or, 3, 13), 19),            ((PCSDD.BOp.or, 3, 12), 18),            ((PCSDD.BOp.or, 3, 11), 17),            ((PCSDD.BOp.or, 1, 11), 1),            ((PCSDD.BOp.or, 3, 6), 16),            ((PCSDD.BOp.or, 1, 6), 1),            ((PCSDD.BOp.or, 3, 10), 15),            ((PCSDD.BOp.or, 3, 9), 14),            ((PCSDD.BOp.or, 0, 3), 3),            ((PCSDD.BOp.or, 0, 13), 13),            ((PCSDD.BOp.or, 0, 12), 12),            ((PCSDD.BOp.or, 0, 11), 11),            ((PCSDD.BOp.or, 7, 10), 13),            ((PCSDD.BOp.or, 6, 10), 12),            ((PCSDD.BOp.or, 6, 9), 11),            ((PCSDD.BOp.or, 1, 9), 1),            ((PCSDD.BOp.or, 1, 1), 1),            ((PCSDD.BOp.or, 0, 6), 6),            ((PCSDD.BOp.or, 0, 10), 10),            ((PCSDD.BOp.or, 0, 9), 9),            ((PCSDD.BOp.or, 0, 1), 1),            ((PCSDD.BOp.or, 0, 0), 0),            ((PCSDD.BOp.and, 8, 9), 10),            ((PCSDD.BOp.and, 1, 9), 9),            ((PCSDD.BOp.and, 0, 9), 0),            ((PCSDD.BOp.and, 5, 6), 7),            ((PCSDD.BOp.and, 1, 6), 6),            ((PCSDD.BOp.and, 0, 6), 0),            ((PCSDD.BOp.and, 2, 3), 4),            ((PCSDD.BOp.and, 1, 3), 3),            ((PCSDD.BOp.and, 1, 1), 1),            ((PCSDD.BOp.and, 0, 3), 0),            ((PCSDD.BOp.and, 0, 1), 0),            ((PCSDD.BOp.and, 0, 0), 0)],   ops := 70,   visits := 20,   wsteps := 0 }
theorem c89 : CompileCertificate 12 DEFAULT_LIMITS f89 i89 25 o89 := by
  exact CompileCertificate.atom (by rfl)
abbrev ai90 : Mgr := o89
abbrev ai91 : Mgr := {ai90 with ops := ai90.ops+1}
abbrev ai92 : Mgr := {ai91 with ops := ai91.ops+1}
abbrev ao92 : Mgr := {ai92 with ops := ai92.ops+1}
theorem a92 : ApplyCertificate 12 DEFAULT_LIMITS 23 PCSDD.BOp.and 0 0 ai92 0 ao92 := by
  exact ApplyCertificate.hit (fuel := 22) (a0 := 0) (b0 := 0) (r := 0) (op := PCSDD.BOp.and) (m := ai92) (by decide) (by rfl)
abbrev ai93 : Mgr := ao92
abbrev ao93 : Mgr := {ai93 with ops := ai93.ops+1}
theorem a93 : ApplyCertificate 12 DEFAULT_LIMITS 23 PCSDD.BOp.and 0 1 ai93 0 ao93 := by
  exact ApplyCertificate.hit (fuel := 22) (a0 := 0) (b0 := 1) (r := 0) (op := PCSDD.BOp.and) (m := ai93) (by decide) (by rfl)
abbrev an91 : Mgr := ao93
abbrev ao91 : Mgr := {an91 with memo := ((PCSDD.BOp.and,0,25),0)::an91.memo}
theorem a91 : ApplyCertificate 12 DEFAULT_LIMITS 24 PCSDD.BOp.and 0 25 ai91 0 ao91 := by
  exact ApplyCertificate.branch (fuel := 23) (a0 := 0) (b0 := 25) (lo := 0) (hi := 0) (r := 0) (op := PCSDD.BOp.and) (m := ai91) (m1 := ao92) (m2 := ao93) (m3 := an91) (by decide) (by rfl) (by decide) a92 a93 (by rfl)
abbrev ai94 : Mgr := ao91
abbrev ai95 : Mgr := {ai94 with ops := ai94.ops+1}
abbrev ao95 : Mgr := {ai95 with ops := ai95.ops+1}
theorem a95 : ApplyCertificate 12 DEFAULT_LIMITS 23 PCSDD.BOp.and 1 0 ai95 0 ao95 := by
  exact ApplyCertificate.hit (fuel := 22) (a0 := 1) (b0 := 0) (r := 0) (op := PCSDD.BOp.and) (m := ai95) (by decide) (by rfl)
abbrev ai96 : Mgr := ao95
abbrev ao96 : Mgr := {ai96 with ops := ai96.ops+1}
theorem a96 : ApplyCertificate 12 DEFAULT_LIMITS 23 PCSDD.BOp.and 1 1 ai96 1 ao96 := by
  exact ApplyCertificate.hit (fuel := 22) (a0 := 1) (b0 := 1) (r := 1) (op := PCSDD.BOp.and) (m := ai96) (by decide) (by rfl)
abbrev an94 : Mgr := ao96
abbrev ao94 : Mgr := {an94 with memo := ((PCSDD.BOp.and,1,25),25)::an94.memo}
theorem a94 : ApplyCertificate 12 DEFAULT_LIMITS 24 PCSDD.BOp.and 1 25 ai94 25 ao94 := by
  exact ApplyCertificate.branch (fuel := 23) (a0 := 1) (b0 := 25) (lo := 0) (hi := 1) (r := 25) (op := PCSDD.BOp.and) (m := ai94) (m1 := ao95) (m2 := ao96) (m3 := an94) (by decide) (by rfl) (by decide) a95 a96 (by rfl)
abbrev an90 : Mgr := {ao94 with nodes := ao94.nodes.push ⟨4,0,25⟩}
abbrev ao90 : Mgr := {an90 with memo := ((PCSDD.BOp.and,24,25),26)::an90.memo}
theorem a90 : ApplyCertificate 12 DEFAULT_LIMITS 25 PCSDD.BOp.and 24 25 ai90 26 ao90 := by
  exact ApplyCertificate.branch (fuel := 24) (a0 := 24) (b0 := 25) (lo := 0) (hi := 25) (r := 26) (op := PCSDD.BOp.and) (m := ai90) (m1 := ao91) (m2 := ao94) (m3 := an90) (by decide) (by rfl) (by decide) a91 a94 (by rfl)
abbrev o87 : Mgr := ao90
theorem c87 : CompileCertificate 12 DEFAULT_LIMITS f87 i87 26 o87 := by
  exact CompileCertificate.and (fuel := 25) (m := i87) (ma := o88) (mb := o89) (out := o87) (x := 24) (y := 25) (r := 26) c88 c89 (ApplyCertificate.sound (m := o89) (out := ao90) a90) (by decide)
abbrev f97 : BForm 12 := PCSOmega.BForm.and (PCSOmega.BForm.atom 5) (PCSOmega.BForm.atom 11)
abbrev i97 : Mgr := { nodes := #[{ var := 0, low := 0, high := 1 }, { var := 6, low := 0, high := 1 }, { var := 0, low := 0, high := 3 },              { var := 1, low := 0, high := 1 }, { var := 7, low := 0, high := 1 }, { var := 1, low := 0, high := 6 },              { var := 2, low := 0, high := 1 }, { var := 8, low := 0, high := 1 }, { var := 2, low := 0, high := 9 },              { var := 7, low := 9, high := 1 }, { var := 2, low := 6, high := 11 }, { var := 1, low := 10, high := 12 },              { var := 6, low := 9, high := 1 }, { var := 2, low := 3, high := 14 }, { var := 6, low := 6, high := 1 },              { var := 6, low := 11, high := 1 }, { var := 2, low := 16, high := 17 },              { var := 1, low := 15, high := 18 }, { var := 0, low := 13, high := 19 },              { var := 3, low := 0, high := 1 }, { var := 9, low := 0, high := 1 }, { var := 3, low := 0, high := 22 },              { var := 4, low := 0, high := 1 }, { var := 10, low := 0, high := 1 }, { var := 4, low := 0, high := 25 }],   memo := [((PCSDD.BOp.and, 24, 25), 26),            ((PCSDD.BOp.and, 1, 25), 25),            ((PCSDD.BOp.and, 0, 25), 0),            ((PCSDD.BOp.and, 21, 22), 23),            ((PCSDD.BOp.and, 1, 22), 22),            ((PCSDD.BOp.and, 0, 22), 0),            ((PCSDD.BOp.or, 4, 13), 20),            ((PCSDD.BOp.or, 3, 13), 19),            ((PCSDD.BOp.or, 3, 12), 18),            ((PCSDD.BOp.or, 3, 11), 17),            ((PCSDD.BOp.or, 1, 11), 1),            ((PCSDD.BOp.or, 3, 6), 16),            ((PCSDD.BOp.or, 1, 6), 1),            ((PCSDD.BOp.or, 3, 10), 15),            ((PCSDD.BOp.or, 3, 9), 14),            ((PCSDD.BOp.or, 0, 3), 3),            ((PCSDD.BOp.or, 0, 13), 13),            ((PCSDD.BOp.or, 0, 12), 12),            ((PCSDD.BOp.or, 0, 11), 11),            ((PCSDD.BOp.or, 7, 10), 13),            ((PCSDD.BOp.or, 6, 10), 12),            ((PCSDD.BOp.or, 6, 9), 11),            ((PCSDD.BOp.or, 1, 9), 1),            ((PCSDD.BOp.or, 1, 1), 1),            ((PCSDD.BOp.or, 0, 6), 6),            ((PCSDD.BOp.or, 0, 10), 10),            ((PCSDD.BOp.or, 0, 9), 9),            ((PCSDD.BOp.or, 0, 1), 1),            ((PCSDD.BOp.or, 0, 0), 0),            ((PCSDD.BOp.and, 8, 9), 10),            ((PCSDD.BOp.and, 1, 9), 9),            ((PCSDD.BOp.and, 0, 9), 0),            ((PCSDD.BOp.and, 5, 6), 7),            ((PCSDD.BOp.and, 1, 6), 6),            ((PCSDD.BOp.and, 0, 6), 0),            ((PCSDD.BOp.and, 2, 3), 4),            ((PCSDD.BOp.and, 1, 3), 3),            ((PCSDD.BOp.and, 1, 1), 1),            ((PCSDD.BOp.and, 0, 3), 0),            ((PCSDD.BOp.and, 0, 1), 0),            ((PCSDD.BOp.and, 0, 0), 0)],   ops := 77,   visits := 20,   wsteps := 0 }
abbrev f98 : BForm 12 := PCSOmega.BForm.atom 5
abbrev i98 : Mgr := { nodes := #[{ var := 0, low := 0, high := 1 }, { var := 6, low := 0, high := 1 }, { var := 0, low := 0, high := 3 },              { var := 1, low := 0, high := 1 }, { var := 7, low := 0, high := 1 }, { var := 1, low := 0, high := 6 },              { var := 2, low := 0, high := 1 }, { var := 8, low := 0, high := 1 }, { var := 2, low := 0, high := 9 },              { var := 7, low := 9, high := 1 }, { var := 2, low := 6, high := 11 }, { var := 1, low := 10, high := 12 },              { var := 6, low := 9, high := 1 }, { var := 2, low := 3, high := 14 }, { var := 6, low := 6, high := 1 },              { var := 6, low := 11, high := 1 }, { var := 2, low := 16, high := 17 },              { var := 1, low := 15, high := 18 }, { var := 0, low := 13, high := 19 },              { var := 3, low := 0, high := 1 }, { var := 9, low := 0, high := 1 }, { var := 3, low := 0, high := 22 },              { var := 4, low := 0, high := 1 }, { var := 10, low := 0, high := 1 }, { var := 4, low := 0, high := 25 }],   memo := [((PCSDD.BOp.and, 24, 25), 26),            ((PCSDD.BOp.and, 1, 25), 25),            ((PCSDD.BOp.and, 0, 25), 0),            ((PCSDD.BOp.and, 21, 22), 23),            ((PCSDD.BOp.and, 1, 22), 22),            ((PCSDD.BOp.and, 0, 22), 0),            ((PCSDD.BOp.or, 4, 13), 20),            ((PCSDD.BOp.or, 3, 13), 19),            ((PCSDD.BOp.or, 3, 12), 18),            ((PCSDD.BOp.or, 3, 11), 17),            ((PCSDD.BOp.or, 1, 11), 1),            ((PCSDD.BOp.or, 3, 6), 16),            ((PCSDD.BOp.or, 1, 6), 1),            ((PCSDD.BOp.or, 3, 10), 15),            ((PCSDD.BOp.or, 3, 9), 14),            ((PCSDD.BOp.or, 0, 3), 3),            ((PCSDD.BOp.or, 0, 13), 13),            ((PCSDD.BOp.or, 0, 12), 12),            ((PCSDD.BOp.or, 0, 11), 11),            ((PCSDD.BOp.or, 7, 10), 13),            ((PCSDD.BOp.or, 6, 10), 12),            ((PCSDD.BOp.or, 6, 9), 11),            ((PCSDD.BOp.or, 1, 9), 1),            ((PCSDD.BOp.or, 1, 1), 1),            ((PCSDD.BOp.or, 0, 6), 6),            ((PCSDD.BOp.or, 0, 10), 10),            ((PCSDD.BOp.or, 0, 9), 9),            ((PCSDD.BOp.or, 0, 1), 1),            ((PCSDD.BOp.or, 0, 0), 0),            ((PCSDD.BOp.and, 8, 9), 10),            ((PCSDD.BOp.and, 1, 9), 9),            ((PCSDD.BOp.and, 0, 9), 0),            ((PCSDD.BOp.and, 5, 6), 7),            ((PCSDD.BOp.and, 1, 6), 6),            ((PCSDD.BOp.and, 0, 6), 0),            ((PCSDD.BOp.and, 2, 3), 4),            ((PCSDD.BOp.and, 1, 3), 3),            ((PCSDD.BOp.and, 1, 1), 1),            ((PCSDD.BOp.and, 0, 3), 0),            ((PCSDD.BOp.and, 0, 1), 0),            ((PCSDD.BOp.and, 0, 0), 0)],   ops := 77,   visits := 21,   wsteps := 0 }
abbrev o98 : Mgr := { nodes := #[{ var := 0, low := 0, high := 1 }, { var := 6, low := 0, high := 1 }, { var := 0, low := 0, high := 3 },              { var := 1, low := 0, high := 1 }, { var := 7, low := 0, high := 1 }, { var := 1, low := 0, high := 6 },              { var := 2, low := 0, high := 1 }, { var := 8, low := 0, high := 1 }, { var := 2, low := 0, high := 9 },              { var := 7, low := 9, high := 1 }, { var := 2, low := 6, high := 11 }, { var := 1, low := 10, high := 12 },              { var := 6, low := 9, high := 1 }, { var := 2, low := 3, high := 14 }, { var := 6, low := 6, high := 1 },              { var := 6, low := 11, high := 1 }, { var := 2, low := 16, high := 17 },              { var := 1, low := 15, high := 18 }, { var := 0, low := 13, high := 19 },              { var := 3, low := 0, high := 1 }, { var := 9, low := 0, high := 1 }, { var := 3, low := 0, high := 22 },              { var := 4, low := 0, high := 1 }, { var := 10, low := 0, high := 1 }, { var := 4, low := 0, high := 25 },              { var := 5, low := 0, high := 1 }],   memo := [((PCSDD.BOp.and, 24, 25), 26),            ((PCSDD.BOp.and, 1, 25), 25),            ((PCSDD.BOp.and, 0, 25), 0),            ((PCSDD.BOp.and, 21, 22), 23),            ((PCSDD.BOp.and, 1, 22), 22),            ((PCSDD.BOp.and, 0, 22), 0),            ((PCSDD.BOp.or, 4, 13), 20),            ((PCSDD.BOp.or, 3, 13), 19),            ((PCSDD.BOp.or, 3, 12), 18),            ((PCSDD.BOp.or, 3, 11), 17),            ((PCSDD.BOp.or, 1, 11), 1),            ((PCSDD.BOp.or, 3, 6), 16),            ((PCSDD.BOp.or, 1, 6), 1),            ((PCSDD.BOp.or, 3, 10), 15),            ((PCSDD.BOp.or, 3, 9), 14),            ((PCSDD.BOp.or, 0, 3), 3),            ((PCSDD.BOp.or, 0, 13), 13),            ((PCSDD.BOp.or, 0, 12), 12),            ((PCSDD.BOp.or, 0, 11), 11),            ((PCSDD.BOp.or, 7, 10), 13),            ((PCSDD.BOp.or, 6, 10), 12),            ((PCSDD.BOp.or, 6, 9), 11),            ((PCSDD.BOp.or, 1, 9), 1),            ((PCSDD.BOp.or, 1, 1), 1),            ((PCSDD.BOp.or, 0, 6), 6),            ((PCSDD.BOp.or, 0, 10), 10),            ((PCSDD.BOp.or, 0, 9), 9),            ((PCSDD.BOp.or, 0, 1), 1),            ((PCSDD.BOp.or, 0, 0), 0),            ((PCSDD.BOp.and, 8, 9), 10),            ((PCSDD.BOp.and, 1, 9), 9),            ((PCSDD.BOp.and, 0, 9), 0),            ((PCSDD.BOp.and, 5, 6), 7),            ((PCSDD.BOp.and, 1, 6), 6),            ((PCSDD.BOp.and, 0, 6), 0),            ((PCSDD.BOp.and, 2, 3), 4),            ((PCSDD.BOp.and, 1, 3), 3),            ((PCSDD.BOp.and, 1, 1), 1),            ((PCSDD.BOp.and, 0, 3), 0),            ((PCSDD.BOp.and, 0, 1), 0),            ((PCSDD.BOp.and, 0, 0), 0)],   ops := 77,   visits := 22,   wsteps := 0 }
theorem c98 : CompileCertificate 12 DEFAULT_LIMITS f98 i98 27 o98 := by
  exact CompileCertificate.atom (by rfl)
abbrev f99 : BForm 12 := PCSOmega.BForm.atom 11
abbrev i99 : Mgr := { nodes := #[{ var := 0, low := 0, high := 1 }, { var := 6, low := 0, high := 1 }, { var := 0, low := 0, high := 3 },              { var := 1, low := 0, high := 1 }, { var := 7, low := 0, high := 1 }, { var := 1, low := 0, high := 6 },              { var := 2, low := 0, high := 1 }, { var := 8, low := 0, high := 1 }, { var := 2, low := 0, high := 9 },              { var := 7, low := 9, high := 1 }, { var := 2, low := 6, high := 11 }, { var := 1, low := 10, high := 12 },              { var := 6, low := 9, high := 1 }, { var := 2, low := 3, high := 14 }, { var := 6, low := 6, high := 1 },              { var := 6, low := 11, high := 1 }, { var := 2, low := 16, high := 17 },              { var := 1, low := 15, high := 18 }, { var := 0, low := 13, high := 19 },              { var := 3, low := 0, high := 1 }, { var := 9, low := 0, high := 1 }, { var := 3, low := 0, high := 22 },              { var := 4, low := 0, high := 1 }, { var := 10, low := 0, high := 1 }, { var := 4, low := 0, high := 25 },              { var := 5, low := 0, high := 1 }],   memo := [((PCSDD.BOp.and, 24, 25), 26),            ((PCSDD.BOp.and, 1, 25), 25),            ((PCSDD.BOp.and, 0, 25), 0),            ((PCSDD.BOp.and, 21, 22), 23),            ((PCSDD.BOp.and, 1, 22), 22),            ((PCSDD.BOp.and, 0, 22), 0),            ((PCSDD.BOp.or, 4, 13), 20),            ((PCSDD.BOp.or, 3, 13), 19),            ((PCSDD.BOp.or, 3, 12), 18),            ((PCSDD.BOp.or, 3, 11), 17),            ((PCSDD.BOp.or, 1, 11), 1),            ((PCSDD.BOp.or, 3, 6), 16),            ((PCSDD.BOp.or, 1, 6), 1),            ((PCSDD.BOp.or, 3, 10), 15),            ((PCSDD.BOp.or, 3, 9), 14),            ((PCSDD.BOp.or, 0, 3), 3),            ((PCSDD.BOp.or, 0, 13), 13),            ((PCSDD.BOp.or, 0, 12), 12),            ((PCSDD.BOp.or, 0, 11), 11),            ((PCSDD.BOp.or, 7, 10), 13),            ((PCSDD.BOp.or, 6, 10), 12),            ((PCSDD.BOp.or, 6, 9), 11),            ((PCSDD.BOp.or, 1, 9), 1),            ((PCSDD.BOp.or, 1, 1), 1),            ((PCSDD.BOp.or, 0, 6), 6),            ((PCSDD.BOp.or, 0, 10), 10),            ((PCSDD.BOp.or, 0, 9), 9),            ((PCSDD.BOp.or, 0, 1), 1),            ((PCSDD.BOp.or, 0, 0), 0),            ((PCSDD.BOp.and, 8, 9), 10),            ((PCSDD.BOp.and, 1, 9), 9),            ((PCSDD.BOp.and, 0, 9), 0),            ((PCSDD.BOp.and, 5, 6), 7),            ((PCSDD.BOp.and, 1, 6), 6),            ((PCSDD.BOp.and, 0, 6), 0),            ((PCSDD.BOp.and, 2, 3), 4),            ((PCSDD.BOp.and, 1, 3), 3),            ((PCSDD.BOp.and, 1, 1), 1),            ((PCSDD.BOp.and, 0, 3), 0),            ((PCSDD.BOp.and, 0, 1), 0),            ((PCSDD.BOp.and, 0, 0), 0)],   ops := 77,   visits := 22,   wsteps := 0 }
abbrev o99 : Mgr := { nodes := #[{ var := 0, low := 0, high := 1 }, { var := 6, low := 0, high := 1 }, { var := 0, low := 0, high := 3 },              { var := 1, low := 0, high := 1 }, { var := 7, low := 0, high := 1 }, { var := 1, low := 0, high := 6 },              { var := 2, low := 0, high := 1 }, { var := 8, low := 0, high := 1 }, { var := 2, low := 0, high := 9 },              { var := 7, low := 9, high := 1 }, { var := 2, low := 6, high := 11 }, { var := 1, low := 10, high := 12 },              { var := 6, low := 9, high := 1 }, { var := 2, low := 3, high := 14 }, { var := 6, low := 6, high := 1 },              { var := 6, low := 11, high := 1 }, { var := 2, low := 16, high := 17 },              { var := 1, low := 15, high := 18 }, { var := 0, low := 13, high := 19 },              { var := 3, low := 0, high := 1 }, { var := 9, low := 0, high := 1 }, { var := 3, low := 0, high := 22 },              { var := 4, low := 0, high := 1 }, { var := 10, low := 0, high := 1 }, { var := 4, low := 0, high := 25 },              { var := 5, low := 0, high := 1 }, { var := 11, low := 0, high := 1 }],   memo := [((PCSDD.BOp.and, 24, 25), 26),            ((PCSDD.BOp.and, 1, 25), 25),            ((PCSDD.BOp.and, 0, 25), 0),            ((PCSDD.BOp.and, 21, 22), 23),            ((PCSDD.BOp.and, 1, 22), 22),            ((PCSDD.BOp.and, 0, 22), 0),            ((PCSDD.BOp.or, 4, 13), 20),            ((PCSDD.BOp.or, 3, 13), 19),            ((PCSDD.BOp.or, 3, 12), 18),            ((PCSDD.BOp.or, 3, 11), 17),            ((PCSDD.BOp.or, 1, 11), 1),            ((PCSDD.BOp.or, 3, 6), 16),            ((PCSDD.BOp.or, 1, 6), 1),            ((PCSDD.BOp.or, 3, 10), 15),            ((PCSDD.BOp.or, 3, 9), 14),            ((PCSDD.BOp.or, 0, 3), 3),            ((PCSDD.BOp.or, 0, 13), 13),            ((PCSDD.BOp.or, 0, 12), 12),            ((PCSDD.BOp.or, 0, 11), 11),            ((PCSDD.BOp.or, 7, 10), 13),            ((PCSDD.BOp.or, 6, 10), 12),            ((PCSDD.BOp.or, 6, 9), 11),            ((PCSDD.BOp.or, 1, 9), 1),            ((PCSDD.BOp.or, 1, 1), 1),            ((PCSDD.BOp.or, 0, 6), 6),            ((PCSDD.BOp.or, 0, 10), 10),            ((PCSDD.BOp.or, 0, 9), 9),            ((PCSDD.BOp.or, 0, 1), 1),            ((PCSDD.BOp.or, 0, 0), 0),            ((PCSDD.BOp.and, 8, 9), 10),            ((PCSDD.BOp.and, 1, 9), 9),            ((PCSDD.BOp.and, 0, 9), 0),            ((PCSDD.BOp.and, 5, 6), 7),            ((PCSDD.BOp.and, 1, 6), 6),            ((PCSDD.BOp.and, 0, 6), 0),            ((PCSDD.BOp.and, 2, 3), 4),            ((PCSDD.BOp.and, 1, 3), 3),            ((PCSDD.BOp.and, 1, 1), 1),            ((PCSDD.BOp.and, 0, 3), 0),            ((PCSDD.BOp.and, 0, 1), 0),            ((PCSDD.BOp.and, 0, 0), 0)],   ops := 77,   visits := 23,   wsteps := 0 }
theorem c99 : CompileCertificate 12 DEFAULT_LIMITS f99 i99 28 o99 := by
  exact CompileCertificate.atom (by rfl)
abbrev ai100 : Mgr := o99
abbrev ai101 : Mgr := {ai100 with ops := ai100.ops+1}
abbrev ai102 : Mgr := {ai101 with ops := ai101.ops+1}
abbrev ao102 : Mgr := {ai102 with ops := ai102.ops+1}
theorem a102 : ApplyCertificate 12 DEFAULT_LIMITS 23 PCSDD.BOp.and 0 0 ai102 0 ao102 := by
  exact ApplyCertificate.hit (fuel := 22) (a0 := 0) (b0 := 0) (r := 0) (op := PCSDD.BOp.and) (m := ai102) (by decide) (by rfl)
abbrev ai103 : Mgr := ao102
abbrev ao103 : Mgr := {ai103 with ops := ai103.ops+1}
theorem a103 : ApplyCertificate 12 DEFAULT_LIMITS 23 PCSDD.BOp.and 0 1 ai103 0 ao103 := by
  exact ApplyCertificate.hit (fuel := 22) (a0 := 0) (b0 := 1) (r := 0) (op := PCSDD.BOp.and) (m := ai103) (by decide) (by rfl)
abbrev an101 : Mgr := ao103
abbrev ao101 : Mgr := {an101 with memo := ((PCSDD.BOp.and,0,28),0)::an101.memo}
theorem a101 : ApplyCertificate 12 DEFAULT_LIMITS 24 PCSDD.BOp.and 0 28 ai101 0 ao101 := by
  exact ApplyCertificate.branch (fuel := 23) (a0 := 0) (b0 := 28) (lo := 0) (hi := 0) (r := 0) (op := PCSDD.BOp.and) (m := ai101) (m1 := ao102) (m2 := ao103) (m3 := an101) (by decide) (by rfl) (by decide) a102 a103 (by rfl)
abbrev ai104 : Mgr := ao101
abbrev ai105 : Mgr := {ai104 with ops := ai104.ops+1}
abbrev ao105 : Mgr := {ai105 with ops := ai105.ops+1}
theorem a105 : ApplyCertificate 12 DEFAULT_LIMITS 23 PCSDD.BOp.and 1 0 ai105 0 ao105 := by
  exact ApplyCertificate.hit (fuel := 22) (a0 := 1) (b0 := 0) (r := 0) (op := PCSDD.BOp.and) (m := ai105) (by decide) (by rfl)
abbrev ai106 : Mgr := ao105
abbrev ao106 : Mgr := {ai106 with ops := ai106.ops+1}
theorem a106 : ApplyCertificate 12 DEFAULT_LIMITS 23 PCSDD.BOp.and 1 1 ai106 1 ao106 := by
  exact ApplyCertificate.hit (fuel := 22) (a0 := 1) (b0 := 1) (r := 1) (op := PCSDD.BOp.and) (m := ai106) (by decide) (by rfl)
abbrev an104 : Mgr := ao106
abbrev ao104 : Mgr := {an104 with memo := ((PCSDD.BOp.and,1,28),28)::an104.memo}
theorem a104 : ApplyCertificate 12 DEFAULT_LIMITS 24 PCSDD.BOp.and 1 28 ai104 28 ao104 := by
  exact ApplyCertificate.branch (fuel := 23) (a0 := 1) (b0 := 28) (lo := 0) (hi := 1) (r := 28) (op := PCSDD.BOp.and) (m := ai104) (m1 := ao105) (m2 := ao106) (m3 := an104) (by decide) (by rfl) (by decide) a105 a106 (by rfl)
abbrev an100 : Mgr := {ao104 with nodes := ao104.nodes.push ⟨5,0,28⟩}
abbrev ao100 : Mgr := {an100 with memo := ((PCSDD.BOp.and,27,28),29)::an100.memo}
theorem a100 : ApplyCertificate 12 DEFAULT_LIMITS 25 PCSDD.BOp.and 27 28 ai100 29 ao100 := by
  exact ApplyCertificate.branch (fuel := 24) (a0 := 27) (b0 := 28) (lo := 0) (hi := 28) (r := 29) (op := PCSDD.BOp.and) (m := ai100) (m1 := ao101) (m2 := ao104) (m3 := an100) (by decide) (by rfl) (by decide) a101 a104 (by rfl)
abbrev o97 : Mgr := ao100
theorem c97 : CompileCertificate 12 DEFAULT_LIMITS f97 i97 29 o97 := by
  exact CompileCertificate.and (fuel := 25) (m := i97) (ma := o98) (mb := o99) (out := o97) (x := 27) (y := 28) (r := 29) c98 c99 (ApplyCertificate.sound (m := o99) (out := ao100) a100) (by decide)
abbrev ai107 : Mgr := o97
abbrev ai108 : Mgr := {ai107 with ops := ai107.ops+1}
abbrev ai109 : Mgr := {ai108 with ops := ai108.ops+1}
abbrev ao109 : Mgr := {ai109 with ops := ai109.ops+1}
theorem a109 : ApplyCertificate 12 DEFAULT_LIMITS 23 PCSDD.BOp.or 0 0 ai109 0 ao109 := by
  exact ApplyCertificate.hit (fuel := 22) (a0 := 0) (b0 := 0) (r := 0) (op := PCSDD.BOp.or) (m := ai109) (by decide) (by rfl)
abbrev ai110 : Mgr := ao109
abbrev ai111 : Mgr := {ai110 with ops := ai110.ops+1}
abbrev ao111 : Mgr := {ai111 with ops := ai111.ops+1}
theorem a111 : ApplyCertificate 12 DEFAULT_LIMITS 22 PCSDD.BOp.or 0 0 ai111 0 ao111 := by
  exact ApplyCertificate.hit (fuel := 21) (a0 := 0) (b0 := 0) (r := 0) (op := PCSDD.BOp.or) (m := ai111) (by decide) (by rfl)
abbrev ai112 : Mgr := ao111
abbrev ao112 : Mgr := {ai112 with ops := ai112.ops+1}
theorem a112 : ApplyCertificate 12 DEFAULT_LIMITS 22 PCSDD.BOp.or 0 1 ai112 1 ao112 := by
  exact ApplyCertificate.hit (fuel := 21) (a0 := 0) (b0 := 1) (r := 1) (op := PCSDD.BOp.or) (m := ai112) (by decide) (by rfl)
abbrev an110 : Mgr := ao112
abbrev ao110 : Mgr := {an110 with memo := ((PCSDD.BOp.or,0,28),28)::an110.memo}
theorem a110 : ApplyCertificate 12 DEFAULT_LIMITS 23 PCSDD.BOp.or 0 28 ai110 28 ao110 := by
  exact ApplyCertificate.branch (fuel := 22) (a0 := 0) (b0 := 28) (lo := 0) (hi := 1) (r := 28) (op := PCSDD.BOp.or) (m := ai110) (m1 := ao111) (m2 := ao112) (m3 := an110) (by decide) (by rfl) (by decide) a111 a112 (by rfl)
abbrev an108 : Mgr := ao110
abbrev ao108 : Mgr := {an108 with memo := ((PCSDD.BOp.or,0,29),29)::an108.memo}
theorem a108 : ApplyCertificate 12 DEFAULT_LIMITS 24 PCSDD.BOp.or 0 29 ai108 29 ao108 := by
  exact ApplyCertificate.branch (fuel := 23) (a0 := 0) (b0 := 29) (lo := 0) (hi := 28) (r := 29) (op := PCSDD.BOp.or) (m := ai108) (m1 := ao109) (m2 := ao110) (m3 := an108) (by decide) (by rfl) (by decide) a109 a110 (by rfl)
abbrev ai113 : Mgr := ao108
abbrev ai114 : Mgr := {ai113 with ops := ai113.ops+1}
abbrev ai115 : Mgr := {ai114 with ops := ai114.ops+1}
abbrev ao115 : Mgr := {ai115 with ops := ai115.ops+1}
theorem a115 : ApplyCertificate 12 DEFAULT_LIMITS 22 PCSDD.BOp.or 0 0 ai115 0 ao115 := by
  exact ApplyCertificate.hit (fuel := 21) (a0 := 0) (b0 := 0) (r := 0) (op := PCSDD.BOp.or) (m := ai115) (by decide) (by rfl)
abbrev ai116 : Mgr := ao115
abbrev ao116 : Mgr := {ai116 with ops := ai116.ops+1}
theorem a116 : ApplyCertificate 12 DEFAULT_LIMITS 22 PCSDD.BOp.or 0 1 ai116 1 ao116 := by
  exact ApplyCertificate.hit (fuel := 21) (a0 := 0) (b0 := 1) (r := 1) (op := PCSDD.BOp.or) (m := ai116) (by decide) (by rfl)
abbrev an114 : Mgr := ao116
abbrev ao114 : Mgr := {an114 with memo := ((PCSDD.BOp.or,0,25),25)::an114.memo}
theorem a114 : ApplyCertificate 12 DEFAULT_LIMITS 23 PCSDD.BOp.or 25 0 ai114 25 ao114 := by
  exact ApplyCertificate.branch (fuel := 22) (a0 := 25) (b0 := 0) (lo := 0) (hi := 1) (r := 25) (op := PCSDD.BOp.or) (m := ai114) (m1 := ao115) (m2 := ao116) (m3 := an114) (by decide) (by rfl) (by decide) a115 a116 (by rfl)
abbrev ai117 : Mgr := ao114
abbrev ai118 : Mgr := {ai117 with ops := ai117.ops+1}
abbrev ao118 : Mgr := {ai118 with ops := ai118.ops+1}
theorem a118 : ApplyCertificate 12 DEFAULT_LIMITS 22 PCSDD.BOp.or 0 28 ai118 28 ao118 := by
  exact ApplyCertificate.hit (fuel := 21) (a0 := 0) (b0 := 28) (r := 28) (op := PCSDD.BOp.or) (m := ai118) (by decide) (by rfl)
abbrev ai119 : Mgr := ao118
abbrev ai120 : Mgr := {ai119 with ops := ai119.ops+1}
abbrev ao120 : Mgr := {ai120 with ops := ai120.ops+1}
theorem a120 : ApplyCertificate 12 DEFAULT_LIMITS 21 PCSDD.BOp.or 1 0 ai120 1 ao120 := by
  exact ApplyCertificate.hit (fuel := 20) (a0 := 1) (b0 := 0) (r := 1) (op := PCSDD.BOp.or) (m := ai120) (by decide) (by rfl)
abbrev ai121 : Mgr := ao120
abbrev ao121 : Mgr := {ai121 with ops := ai121.ops+1}
theorem a121 : ApplyCertificate 12 DEFAULT_LIMITS 21 PCSDD.BOp.or 1 1 ai121 1 ao121 := by
  exact ApplyCertificate.hit (fuel := 20) (a0 := 1) (b0 := 1) (r := 1) (op := PCSDD.BOp.or) (m := ai121) (by decide) (by rfl)
abbrev an119 : Mgr := ao121
abbrev ao119 : Mgr := {an119 with memo := ((PCSDD.BOp.or,1,28),1)::an119.memo}
theorem a119 : ApplyCertificate 12 DEFAULT_LIMITS 22 PCSDD.BOp.or 1 28 ai119 1 ao119 := by
  exact ApplyCertificate.branch (fuel := 21) (a0 := 1) (b0 := 28) (lo := 1) (hi := 1) (r := 1) (op := PCSDD.BOp.or) (m := ai119) (m1 := ao120) (m2 := ao121) (m3 := an119) (by decide) (by rfl) (by decide) a120 a121 (by rfl)
abbrev an117 : Mgr := {ao119 with nodes := ao119.nodes.push ⟨10,28,1⟩}
abbrev ao117 : Mgr := {an117 with memo := ((PCSDD.BOp.or,25,28),30)::an117.memo}
theorem a117 : ApplyCertificate 12 DEFAULT_LIMITS 23 PCSDD.BOp.or 25 28 ai117 30 ao117 := by
  exact ApplyCertificate.branch (fuel := 22) (a0 := 25) (b0 := 28) (lo := 28) (hi := 1) (r := 30) (op := PCSDD.BOp.or) (m := ai117) (m1 := ao118) (m2 := ao119) (m3 := an117) (by decide) (by rfl) (by decide) a118 a119 (by rfl)
abbrev an113 : Mgr := {ao117 with nodes := ao117.nodes.push ⟨5,25,30⟩}
abbrev ao113 : Mgr := {an113 with memo := ((PCSDD.BOp.or,25,29),31)::an113.memo}
theorem a113 : ApplyCertificate 12 DEFAULT_LIMITS 24 PCSDD.BOp.or 25 29 ai113 31 ao113 := by
  exact ApplyCertificate.branch (fuel := 23) (a0 := 25) (b0 := 29) (lo := 25) (hi := 30) (r := 31) (op := PCSDD.BOp.or) (m := ai113) (m1 := ao114) (m2 := ao117) (m3 := an113) (by decide) (by rfl) (by decide) a114 a117 (by rfl)
abbrev an107 : Mgr := {ao113 with nodes := ao113.nodes.push ⟨4,29,31⟩}
abbrev ao107 : Mgr := {an107 with memo := ((PCSDD.BOp.or,26,29),32)::an107.memo}
theorem a107 : ApplyCertificate 12 DEFAULT_LIMITS 25 PCSDD.BOp.or 26 29 ai107 32 ao107 := by
  exact ApplyCertificate.branch (fuel := 24) (a0 := 26) (b0 := 29) (lo := 29) (hi := 31) (r := 32) (op := PCSDD.BOp.or) (m := ai107) (m1 := ao108) (m2 := ao113) (m3 := an107) (by decide) (by rfl) (by decide) a108 a113 (by rfl)
abbrev o86 : Mgr := ao107
theorem c86 : CompileCertificate 12 DEFAULT_LIMITS f86 i86 32 o86 := by
  exact CompileCertificate.or (fuel := 25) (m := i86) (ma := o87) (mb := o97) (out := o86) (x := 26) (y := 29) (r := 32) c87 c97 (ApplyCertificate.sound (m := o97) (out := ao107) a107) (by decide)
abbrev ai122 : Mgr := o86
abbrev ai123 : Mgr := {ai122 with ops := ai122.ops+1}
abbrev ai124 : Mgr := {ai123 with ops := ai123.ops+1}
abbrev ao124 : Mgr := {ai124 with ops := ai124.ops+1}
theorem a124 : ApplyCertificate 12 DEFAULT_LIMITS 23 PCSDD.BOp.or 0 29 ai124 29 ao124 := by
  exact ApplyCertificate.hit (fuel := 22) (a0 := 0) (b0 := 29) (r := 29) (op := PCSDD.BOp.or) (m := ai124) (by decide) (by rfl)
abbrev ai125 : Mgr := ao124
abbrev ai126 : Mgr := {ai125 with ops := ai125.ops+1}
abbrev ao126 : Mgr := {ai126 with ops := ai126.ops+1}
theorem a126 : ApplyCertificate 12 DEFAULT_LIMITS 22 PCSDD.BOp.or 0 25 ai126 25 ao126 := by
  exact ApplyCertificate.hit (fuel := 21) (a0 := 0) (b0 := 25) (r := 25) (op := PCSDD.BOp.or) (m := ai126) (by decide) (by rfl)
abbrev ai127 : Mgr := ao126
abbrev ai128 : Mgr := {ai127 with ops := ai127.ops+1}
abbrev ao128 : Mgr := {ai128 with ops := ai128.ops+1}
theorem a128 : ApplyCertificate 12 DEFAULT_LIMITS 21 PCSDD.BOp.or 0 28 ai128 28 ao128 := by
  exact ApplyCertificate.hit (fuel := 20) (a0 := 0) (b0 := 28) (r := 28) (op := PCSDD.BOp.or) (m := ai128) (by decide) (by rfl)
abbrev ai129 : Mgr := ao128
abbrev ao129 : Mgr := {ai129 with ops := ai129.ops+1}
theorem a129 : ApplyCertificate 12 DEFAULT_LIMITS 21 PCSDD.BOp.or 0 1 ai129 1 ao129 := by
  exact ApplyCertificate.hit (fuel := 20) (a0 := 0) (b0 := 1) (r := 1) (op := PCSDD.BOp.or) (m := ai129) (by decide) (by rfl)
abbrev an127 : Mgr := ao129
abbrev ao127 : Mgr := {an127 with memo := ((PCSDD.BOp.or,0,30),30)::an127.memo}
theorem a127 : ApplyCertificate 12 DEFAULT_LIMITS 22 PCSDD.BOp.or 0 30 ai127 30 ao127 := by
  exact ApplyCertificate.branch (fuel := 21) (a0 := 0) (b0 := 30) (lo := 28) (hi := 1) (r := 30) (op := PCSDD.BOp.or) (m := ai127) (m1 := ao128) (m2 := ao129) (m3 := an127) (by decide) (by rfl) (by decide) a128 a129 (by rfl)
abbrev an125 : Mgr := ao127
abbrev ao125 : Mgr := {an125 with memo := ((PCSDD.BOp.or,0,31),31)::an125.memo}
theorem a125 : ApplyCertificate 12 DEFAULT_LIMITS 23 PCSDD.BOp.or 0 31 ai125 31 ao125 := by
  exact ApplyCertificate.branch (fuel := 22) (a0 := 0) (b0 := 31) (lo := 25) (hi := 30) (r := 31) (op := PCSDD.BOp.or) (m := ai125) (m1 := ao126) (m2 := ao127) (m3 := an125) (by decide) (by rfl) (by decide) a126 a127 (by rfl)
abbrev an123 : Mgr := ao125
abbrev ao123 : Mgr := {an123 with memo := ((PCSDD.BOp.or,0,32),32)::an123.memo}
theorem a123 : ApplyCertificate 12 DEFAULT_LIMITS 24 PCSDD.BOp.or 0 32 ai123 32 ao123 := by
  exact ApplyCertificate.branch (fuel := 23) (a0 := 0) (b0 := 32) (lo := 29) (hi := 31) (r := 32) (op := PCSDD.BOp.or) (m := ai123) (m1 := ao124) (m2 := ao125) (m3 := an123) (by decide) (by rfl) (by decide) a124 a125 (by rfl)
abbrev ai130 : Mgr := ao123
abbrev ai131 : Mgr := {ai130 with ops := ai130.ops+1}
abbrev ai132 : Mgr := {ai131 with ops := ai131.ops+1}
abbrev ai133 : Mgr := {ai132 with ops := ai132.ops+1}
abbrev ao133 : Mgr := {ai133 with ops := ai133.ops+1}
theorem a133 : ApplyCertificate 12 DEFAULT_LIMITS 21 PCSDD.BOp.or 0 0 ai133 0 ao133 := by
  exact ApplyCertificate.hit (fuel := 20) (a0 := 0) (b0 := 0) (r := 0) (op := PCSDD.BOp.or) (m := ai133) (by decide) (by rfl)
abbrev ai134 : Mgr := ao133
abbrev ao134 : Mgr := {ai134 with ops := ai134.ops+1}
theorem a134 : ApplyCertificate 12 DEFAULT_LIMITS 21 PCSDD.BOp.or 0 1 ai134 1 ao134 := by
  exact ApplyCertificate.hit (fuel := 20) (a0 := 0) (b0 := 1) (r := 1) (op := PCSDD.BOp.or) (m := ai134) (by decide) (by rfl)
abbrev an132 : Mgr := ao134
abbrev ao132 : Mgr := {an132 with memo := ((PCSDD.BOp.or,0,22),22)::an132.memo}
theorem a132 : ApplyCertificate 12 DEFAULT_LIMITS 22 PCSDD.BOp.or 22 0 ai132 22 ao132 := by
  exact ApplyCertificate.branch (fuel := 21) (a0 := 22) (b0 := 0) (lo := 0) (hi := 1) (r := 22) (op := PCSDD.BOp.or) (m := ai132) (m1 := ao133) (m2 := ao134) (m3 := an132) (by decide) (by rfl) (by decide) a133 a134 (by rfl)
abbrev ai135 : Mgr := ao132
abbrev ai136 : Mgr := {ai135 with ops := ai135.ops+1}
abbrev ao136 : Mgr := {ai136 with ops := ai136.ops+1}
theorem a136 : ApplyCertificate 12 DEFAULT_LIMITS 21 PCSDD.BOp.or 0 28 ai136 28 ao136 := by
  exact ApplyCertificate.hit (fuel := 20) (a0 := 0) (b0 := 28) (r := 28) (op := PCSDD.BOp.or) (m := ai136) (by decide) (by rfl)
abbrev ai137 : Mgr := ao136
abbrev ao137 : Mgr := {ai137 with ops := ai137.ops+1}
theorem a137 : ApplyCertificate 12 DEFAULT_LIMITS 21 PCSDD.BOp.or 1 28 ai137 1 ao137 := by
  exact ApplyCertificate.hit (fuel := 20) (a0 := 1) (b0 := 28) (r := 1) (op := PCSDD.BOp.or) (m := ai137) (by decide) (by rfl)
abbrev an135 : Mgr := {ao137 with nodes := ao137.nodes.push ⟨9,28,1⟩}
abbrev ao135 : Mgr := {an135 with memo := ((PCSDD.BOp.or,22,28),33)::an135.memo}
theorem a135 : ApplyCertificate 12 DEFAULT_LIMITS 22 PCSDD.BOp.or 22 28 ai135 33 ao135 := by
  exact ApplyCertificate.branch (fuel := 21) (a0 := 22) (b0 := 28) (lo := 28) (hi := 1) (r := 33) (op := PCSDD.BOp.or) (m := ai135) (m1 := ao136) (m2 := ao137) (m3 := an135) (by decide) (by rfl) (by decide) a136 a137 (by rfl)
abbrev an131 : Mgr := {ao135 with nodes := ao135.nodes.push ⟨5,22,33⟩}
abbrev ao131 : Mgr := {an131 with memo := ((PCSDD.BOp.or,22,29),34)::an131.memo}
theorem a131 : ApplyCertificate 12 DEFAULT_LIMITS 23 PCSDD.BOp.or 22 29 ai131 34 ao131 := by
  exact ApplyCertificate.branch (fuel := 22) (a0 := 22) (b0 := 29) (lo := 22) (hi := 33) (r := 34) (op := PCSDD.BOp.or) (m := ai131) (m1 := ao132) (m2 := ao135) (m3 := an131) (by decide) (by rfl) (by decide) a132 a135 (by rfl)
abbrev ai138 : Mgr := ao131
abbrev ai139 : Mgr := {ai138 with ops := ai138.ops+1}
abbrev ai140 : Mgr := {ai139 with ops := ai139.ops+1}
abbrev ao140 : Mgr := {ai140 with ops := ai140.ops+1}
theorem a140 : ApplyCertificate 12 DEFAULT_LIMITS 21 PCSDD.BOp.or 0 25 ai140 25 ao140 := by
  exact ApplyCertificate.hit (fuel := 20) (a0 := 0) (b0 := 25) (r := 25) (op := PCSDD.BOp.or) (m := ai140) (by decide) (by rfl)
abbrev ai141 : Mgr := ao140
abbrev ai142 : Mgr := {ai141 with ops := ai141.ops+1}
abbrev ao142 : Mgr := {ai142 with ops := ai142.ops+1}
theorem a142 : ApplyCertificate 12 DEFAULT_LIMITS 20 PCSDD.BOp.or 1 0 ai142 1 ao142 := by
  exact ApplyCertificate.hit (fuel := 19) (a0 := 1) (b0 := 0) (r := 1) (op := PCSDD.BOp.or) (m := ai142) (by decide) (by rfl)
abbrev ai143 : Mgr := ao142
abbrev ao143 : Mgr := {ai143 with ops := ai143.ops+1}
theorem a143 : ApplyCertificate 12 DEFAULT_LIMITS 20 PCSDD.BOp.or 1 1 ai143 1 ao143 := by
  exact ApplyCertificate.hit (fuel := 19) (a0 := 1) (b0 := 1) (r := 1) (op := PCSDD.BOp.or) (m := ai143) (by decide) (by rfl)
abbrev an141 : Mgr := ao143
abbrev ao141 : Mgr := {an141 with memo := ((PCSDD.BOp.or,1,25),1)::an141.memo}
theorem a141 : ApplyCertificate 12 DEFAULT_LIMITS 21 PCSDD.BOp.or 1 25 ai141 1 ao141 := by
  exact ApplyCertificate.branch (fuel := 20) (a0 := 1) (b0 := 25) (lo := 1) (hi := 1) (r := 1) (op := PCSDD.BOp.or) (m := ai141) (m1 := ao142) (m2 := ao143) (m3 := an141) (by decide) (by rfl) (by decide) a142 a143 (by rfl)
abbrev an139 : Mgr := {ao141 with nodes := ao141.nodes.push ⟨9,25,1⟩}
abbrev ao139 : Mgr := {an139 with memo := ((PCSDD.BOp.or,22,25),35)::an139.memo}
theorem a139 : ApplyCertificate 12 DEFAULT_LIMITS 22 PCSDD.BOp.or 22 25 ai139 35 ao139 := by
  exact ApplyCertificate.branch (fuel := 21) (a0 := 22) (b0 := 25) (lo := 25) (hi := 1) (r := 35) (op := PCSDD.BOp.or) (m := ai139) (m1 := ao140) (m2 := ao141) (m3 := an139) (by decide) (by rfl) (by decide) a140 a141 (by rfl)
abbrev ai144 : Mgr := ao139
abbrev ai145 : Mgr := {ai144 with ops := ai144.ops+1}
abbrev ao145 : Mgr := {ai145 with ops := ai145.ops+1}
theorem a145 : ApplyCertificate 12 DEFAULT_LIMITS 21 PCSDD.BOp.or 0 30 ai145 30 ao145 := by
  exact ApplyCertificate.hit (fuel := 20) (a0 := 0) (b0 := 30) (r := 30) (op := PCSDD.BOp.or) (m := ai145) (by decide) (by rfl)
abbrev ai146 : Mgr := ao145
abbrev ai147 : Mgr := {ai146 with ops := ai146.ops+1}
abbrev ao147 : Mgr := {ai147 with ops := ai147.ops+1}
theorem a147 : ApplyCertificate 12 DEFAULT_LIMITS 20 PCSDD.BOp.or 1 28 ai147 1 ao147 := by
  exact ApplyCertificate.hit (fuel := 19) (a0 := 1) (b0 := 28) (r := 1) (op := PCSDD.BOp.or) (m := ai147) (by decide) (by rfl)
abbrev ai148 : Mgr := ao147
abbrev ao148 : Mgr := {ai148 with ops := ai148.ops+1}
theorem a148 : ApplyCertificate 12 DEFAULT_LIMITS 20 PCSDD.BOp.or 1 1 ai148 1 ao148 := by
  exact ApplyCertificate.hit (fuel := 19) (a0 := 1) (b0 := 1) (r := 1) (op := PCSDD.BOp.or) (m := ai148) (by decide) (by rfl)
abbrev an146 : Mgr := ao148
abbrev ao146 : Mgr := {an146 with memo := ((PCSDD.BOp.or,1,30),1)::an146.memo}
theorem a146 : ApplyCertificate 12 DEFAULT_LIMITS 21 PCSDD.BOp.or 1 30 ai146 1 ao146 := by
  exact ApplyCertificate.branch (fuel := 20) (a0 := 1) (b0 := 30) (lo := 1) (hi := 1) (r := 1) (op := PCSDD.BOp.or) (m := ai146) (m1 := ao147) (m2 := ao148) (m3 := an146) (by decide) (by rfl) (by decide) a147 a148 (by rfl)
abbrev an144 : Mgr := {ao146 with nodes := ao146.nodes.push ⟨9,30,1⟩}
abbrev ao144 : Mgr := {an144 with memo := ((PCSDD.BOp.or,22,30),36)::an144.memo}
theorem a144 : ApplyCertificate 12 DEFAULT_LIMITS 22 PCSDD.BOp.or 22 30 ai144 36 ao144 := by
  exact ApplyCertificate.branch (fuel := 21) (a0 := 22) (b0 := 30) (lo := 30) (hi := 1) (r := 36) (op := PCSDD.BOp.or) (m := ai144) (m1 := ao145) (m2 := ao146) (m3 := an144) (by decide) (by rfl) (by decide) a145 a146 (by rfl)
abbrev an138 : Mgr := {ao144 with nodes := ao144.nodes.push ⟨5,35,36⟩}
abbrev ao138 : Mgr := {an138 with memo := ((PCSDD.BOp.or,22,31),37)::an138.memo}
theorem a138 : ApplyCertificate 12 DEFAULT_LIMITS 23 PCSDD.BOp.or 22 31 ai138 37 ao138 := by
  exact ApplyCertificate.branch (fuel := 22) (a0 := 22) (b0 := 31) (lo := 35) (hi := 36) (r := 37) (op := PCSDD.BOp.or) (m := ai138) (m1 := ao139) (m2 := ao144) (m3 := an138) (by decide) (by rfl) (by decide) a139 a144 (by rfl)
abbrev an130 : Mgr := {ao138 with nodes := ao138.nodes.push ⟨4,34,37⟩}
abbrev ao130 : Mgr := {an130 with memo := ((PCSDD.BOp.or,22,32),38)::an130.memo}
theorem a130 : ApplyCertificate 12 DEFAULT_LIMITS 24 PCSDD.BOp.or 22 32 ai130 38 ao130 := by
  exact ApplyCertificate.branch (fuel := 23) (a0 := 22) (b0 := 32) (lo := 34) (hi := 37) (r := 38) (op := PCSDD.BOp.or) (m := ai130) (m1 := ao131) (m2 := ao138) (m3 := an130) (by decide) (by rfl) (by decide) a131 a138 (by rfl)
abbrev an122 : Mgr := {ao130 with nodes := ao130.nodes.push ⟨3,32,38⟩}
abbrev ao122 : Mgr := {an122 with memo := ((PCSDD.BOp.or,23,32),39)::an122.memo}
theorem a122 : ApplyCertificate 12 DEFAULT_LIMITS 25 PCSDD.BOp.or 23 32 ai122 39 ao122 := by
  exact ApplyCertificate.branch (fuel := 24) (a0 := 23) (b0 := 32) (lo := 32) (hi := 38) (r := 39) (op := PCSDD.BOp.or) (m := ai122) (m1 := ao123) (m2 := ao130) (m3 := an122) (by decide) (by rfl) (by decide) a123 a130 (by rfl)
abbrev o75 : Mgr := ao122
theorem c75 : CompileCertificate 12 DEFAULT_LIMITS f75 i75 39 o75 := by
  exact CompileCertificate.or (fuel := 25) (m := i75) (ma := o76) (mb := o86) (out := o75) (x := 23) (y := 32) (r := 39) c76 c86 (ApplyCertificate.sound (m := o86) (out := ao122) a122) (by decide)
abbrev ai149 : Mgr := o75
abbrev ai150 : Mgr := {ai149 with ops := ai149.ops+1}
abbrev ai151 : Mgr := {ai150 with ops := ai150.ops+1}
abbrev ai152 : Mgr := {ai151 with ops := ai151.ops+1}
abbrev ai153 : Mgr := {ai152 with ops := ai152.ops+1}
abbrev ao153 : Mgr := {ai153 with ops := ai153.ops+1}
theorem a153 : ApplyCertificate 12 DEFAULT_LIMITS 21 PCSDD.BOp.or 0 32 ai153 32 ao153 := by
  exact ApplyCertificate.hit (fuel := 20) (a0 := 0) (b0 := 32) (r := 32) (op := PCSDD.BOp.or) (m := ai153) (by decide) (by rfl)
abbrev ai154 : Mgr := ao153
abbrev ai155 : Mgr := {ai154 with ops := ai154.ops+1}
abbrev ai156 : Mgr := {ai155 with ops := ai155.ops+1}
abbrev ao156 : Mgr := {ai156 with ops := ai156.ops+1}
theorem a156 : ApplyCertificate 12 DEFAULT_LIMITS 19 PCSDD.BOp.or 0 22 ai156 22 ao156 := by
  exact ApplyCertificate.hit (fuel := 18) (a0 := 0) (b0 := 22) (r := 22) (op := PCSDD.BOp.or) (m := ai156) (by decide) (by rfl)
abbrev ai157 : Mgr := ao156
abbrev ai158 : Mgr := {ai157 with ops := ai157.ops+1}
abbrev ao158 : Mgr := {ai158 with ops := ai158.ops+1}
theorem a158 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.or 0 28 ai158 28 ao158 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 0) (b0 := 28) (r := 28) (op := PCSDD.BOp.or) (m := ai158) (by decide) (by rfl)
abbrev ai159 : Mgr := ao158
abbrev ao159 : Mgr := {ai159 with ops := ai159.ops+1}
theorem a159 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.or 0 1 ai159 1 ao159 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 0) (b0 := 1) (r := 1) (op := PCSDD.BOp.or) (m := ai159) (by decide) (by rfl)
abbrev an157 : Mgr := ao159
abbrev ao157 : Mgr := {an157 with memo := ((PCSDD.BOp.or,0,33),33)::an157.memo}
theorem a157 : ApplyCertificate 12 DEFAULT_LIMITS 19 PCSDD.BOp.or 0 33 ai157 33 ao157 := by
  exact ApplyCertificate.branch (fuel := 18) (a0 := 0) (b0 := 33) (lo := 28) (hi := 1) (r := 33) (op := PCSDD.BOp.or) (m := ai157) (m1 := ao158) (m2 := ao159) (m3 := an157) (by decide) (by rfl) (by decide) a158 a159 (by rfl)
abbrev an155 : Mgr := ao157
abbrev ao155 : Mgr := {an155 with memo := ((PCSDD.BOp.or,0,34),34)::an155.memo}
theorem a155 : ApplyCertificate 12 DEFAULT_LIMITS 20 PCSDD.BOp.or 0 34 ai155 34 ao155 := by
  exact ApplyCertificate.branch (fuel := 19) (a0 := 0) (b0 := 34) (lo := 22) (hi := 33) (r := 34) (op := PCSDD.BOp.or) (m := ai155) (m1 := ao156) (m2 := ao157) (m3 := an155) (by decide) (by rfl) (by decide) a156 a157 (by rfl)
abbrev ai160 : Mgr := ao155
abbrev ai161 : Mgr := {ai160 with ops := ai160.ops+1}
abbrev ai162 : Mgr := {ai161 with ops := ai161.ops+1}
abbrev ao162 : Mgr := {ai162 with ops := ai162.ops+1}
theorem a162 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.or 0 25 ai162 25 ao162 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 0) (b0 := 25) (r := 25) (op := PCSDD.BOp.or) (m := ai162) (by decide) (by rfl)
abbrev ai163 : Mgr := ao162
abbrev ao163 : Mgr := {ai163 with ops := ai163.ops+1}
theorem a163 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.or 0 1 ai163 1 ao163 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 0) (b0 := 1) (r := 1) (op := PCSDD.BOp.or) (m := ai163) (by decide) (by rfl)
abbrev an161 : Mgr := ao163
abbrev ao161 : Mgr := {an161 with memo := ((PCSDD.BOp.or,0,35),35)::an161.memo}
theorem a161 : ApplyCertificate 12 DEFAULT_LIMITS 19 PCSDD.BOp.or 0 35 ai161 35 ao161 := by
  exact ApplyCertificate.branch (fuel := 18) (a0 := 0) (b0 := 35) (lo := 25) (hi := 1) (r := 35) (op := PCSDD.BOp.or) (m := ai161) (m1 := ao162) (m2 := ao163) (m3 := an161) (by decide) (by rfl) (by decide) a162 a163 (by rfl)
abbrev ai164 : Mgr := ao161
abbrev ai165 : Mgr := {ai164 with ops := ai164.ops+1}
abbrev ao165 : Mgr := {ai165 with ops := ai165.ops+1}
theorem a165 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.or 0 30 ai165 30 ao165 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 0) (b0 := 30) (r := 30) (op := PCSDD.BOp.or) (m := ai165) (by decide) (by rfl)
abbrev ai166 : Mgr := ao165
abbrev ao166 : Mgr := {ai166 with ops := ai166.ops+1}
theorem a166 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.or 0 1 ai166 1 ao166 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 0) (b0 := 1) (r := 1) (op := PCSDD.BOp.or) (m := ai166) (by decide) (by rfl)
abbrev an164 : Mgr := ao166
abbrev ao164 : Mgr := {an164 with memo := ((PCSDD.BOp.or,0,36),36)::an164.memo}
theorem a164 : ApplyCertificate 12 DEFAULT_LIMITS 19 PCSDD.BOp.or 0 36 ai164 36 ao164 := by
  exact ApplyCertificate.branch (fuel := 18) (a0 := 0) (b0 := 36) (lo := 30) (hi := 1) (r := 36) (op := PCSDD.BOp.or) (m := ai164) (m1 := ao165) (m2 := ao166) (m3 := an164) (by decide) (by rfl) (by decide) a165 a166 (by rfl)
abbrev an160 : Mgr := ao164
abbrev ao160 : Mgr := {an160 with memo := ((PCSDD.BOp.or,0,37),37)::an160.memo}
theorem a160 : ApplyCertificate 12 DEFAULT_LIMITS 20 PCSDD.BOp.or 0 37 ai160 37 ao160 := by
  exact ApplyCertificate.branch (fuel := 19) (a0 := 0) (b0 := 37) (lo := 35) (hi := 36) (r := 37) (op := PCSDD.BOp.or) (m := ai160) (m1 := ao161) (m2 := ao164) (m3 := an160) (by decide) (by rfl) (by decide) a161 a164 (by rfl)
abbrev an154 : Mgr := ao160
abbrev ao154 : Mgr := {an154 with memo := ((PCSDD.BOp.or,0,38),38)::an154.memo}
theorem a154 : ApplyCertificate 12 DEFAULT_LIMITS 21 PCSDD.BOp.or 0 38 ai154 38 ao154 := by
  exact ApplyCertificate.branch (fuel := 20) (a0 := 0) (b0 := 38) (lo := 34) (hi := 37) (r := 38) (op := PCSDD.BOp.or) (m := ai154) (m1 := ao155) (m2 := ao160) (m3 := an154) (by decide) (by rfl) (by decide) a155 a160 (by rfl)
abbrev an152 : Mgr := ao154
abbrev ao152 : Mgr := {an152 with memo := ((PCSDD.BOp.or,0,39),39)::an152.memo}
theorem a152 : ApplyCertificate 12 DEFAULT_LIMITS 22 PCSDD.BOp.or 0 39 ai152 39 ao152 := by
  exact ApplyCertificate.branch (fuel := 21) (a0 := 0) (b0 := 39) (lo := 32) (hi := 38) (r := 39) (op := PCSDD.BOp.or) (m := ai152) (m1 := ao153) (m2 := ao154) (m3 := an152) (by decide) (by rfl) (by decide) a153 a154 (by rfl)
abbrev ai167 : Mgr := ao152
abbrev ai168 : Mgr := {ai167 with ops := ai167.ops+1}
abbrev ai169 : Mgr := {ai168 with ops := ai168.ops+1}
abbrev ai170 : Mgr := {ai169 with ops := ai169.ops+1}
abbrev ao170 : Mgr := {ai170 with ops := ai170.ops+1}
theorem a170 : ApplyCertificate 12 DEFAULT_LIMITS 19 PCSDD.BOp.or 9 0 ai170 9 ao170 := by
  exact ApplyCertificate.hit (fuel := 18) (a0 := 9) (b0 := 0) (r := 9) (op := PCSDD.BOp.or) (m := ai170) (by decide) (by rfl)
abbrev ai171 : Mgr := ao170
abbrev ai172 : Mgr := {ai171 with ops := ai171.ops+1}
abbrev ao172 : Mgr := {ai172 with ops := ai172.ops+1}
theorem a172 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.or 0 28 ai172 28 ao172 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 0) (b0 := 28) (r := 28) (op := PCSDD.BOp.or) (m := ai172) (by decide) (by rfl)
abbrev ai173 : Mgr := ao172
abbrev ao173 : Mgr := {ai173 with ops := ai173.ops+1}
theorem a173 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.or 1 28 ai173 1 ao173 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 1) (b0 := 28) (r := 1) (op := PCSDD.BOp.or) (m := ai173) (by decide) (by rfl)
abbrev an171 : Mgr := {ao173 with nodes := ao173.nodes.push ⟨8,28,1⟩}
abbrev ao171 : Mgr := {an171 with memo := ((PCSDD.BOp.or,9,28),40)::an171.memo}
theorem a171 : ApplyCertificate 12 DEFAULT_LIMITS 19 PCSDD.BOp.or 9 28 ai171 40 ao171 := by
  exact ApplyCertificate.branch (fuel := 18) (a0 := 9) (b0 := 28) (lo := 28) (hi := 1) (r := 40) (op := PCSDD.BOp.or) (m := ai171) (m1 := ao172) (m2 := ao173) (m3 := an171) (by decide) (by rfl) (by decide) a172 a173 (by rfl)
abbrev an169 : Mgr := {ao171 with nodes := ao171.nodes.push ⟨5,9,40⟩}
abbrev ao169 : Mgr := {an169 with memo := ((PCSDD.BOp.or,9,29),41)::an169.memo}
theorem a169 : ApplyCertificate 12 DEFAULT_LIMITS 20 PCSDD.BOp.or 9 29 ai169 41 ao169 := by
  exact ApplyCertificate.branch (fuel := 19) (a0 := 9) (b0 := 29) (lo := 9) (hi := 40) (r := 41) (op := PCSDD.BOp.or) (m := ai169) (m1 := ao170) (m2 := ao171) (m3 := an169) (by decide) (by rfl) (by decide) a170 a171 (by rfl)
abbrev ai174 : Mgr := ao169
abbrev ai175 : Mgr := {ai174 with ops := ai174.ops+1}
abbrev ai176 : Mgr := {ai175 with ops := ai175.ops+1}
abbrev ao176 : Mgr := {ai176 with ops := ai176.ops+1}
theorem a176 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.or 0 25 ai176 25 ao176 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 0) (b0 := 25) (r := 25) (op := PCSDD.BOp.or) (m := ai176) (by decide) (by rfl)
abbrev ai177 : Mgr := ao176
abbrev ao177 : Mgr := {ai177 with ops := ai177.ops+1}
theorem a177 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.or 1 25 ai177 1 ao177 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 1) (b0 := 25) (r := 1) (op := PCSDD.BOp.or) (m := ai177) (by decide) (by rfl)
abbrev an175 : Mgr := {ao177 with nodes := ao177.nodes.push ⟨8,25,1⟩}
abbrev ao175 : Mgr := {an175 with memo := ((PCSDD.BOp.or,9,25),42)::an175.memo}
theorem a175 : ApplyCertificate 12 DEFAULT_LIMITS 19 PCSDD.BOp.or 9 25 ai175 42 ao175 := by
  exact ApplyCertificate.branch (fuel := 18) (a0 := 9) (b0 := 25) (lo := 25) (hi := 1) (r := 42) (op := PCSDD.BOp.or) (m := ai175) (m1 := ao176) (m2 := ao177) (m3 := an175) (by decide) (by rfl) (by decide) a176 a177 (by rfl)
abbrev ai178 : Mgr := ao175
abbrev ai179 : Mgr := {ai178 with ops := ai178.ops+1}
abbrev ao179 : Mgr := {ai179 with ops := ai179.ops+1}
theorem a179 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.or 0 30 ai179 30 ao179 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 0) (b0 := 30) (r := 30) (op := PCSDD.BOp.or) (m := ai179) (by decide) (by rfl)
abbrev ai180 : Mgr := ao179
abbrev ao180 : Mgr := {ai180 with ops := ai180.ops+1}
theorem a180 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.or 1 30 ai180 1 ao180 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 1) (b0 := 30) (r := 1) (op := PCSDD.BOp.or) (m := ai180) (by decide) (by rfl)
abbrev an178 : Mgr := {ao180 with nodes := ao180.nodes.push ⟨8,30,1⟩}
abbrev ao178 : Mgr := {an178 with memo := ((PCSDD.BOp.or,9,30),43)::an178.memo}
theorem a178 : ApplyCertificate 12 DEFAULT_LIMITS 19 PCSDD.BOp.or 9 30 ai178 43 ao178 := by
  exact ApplyCertificate.branch (fuel := 18) (a0 := 9) (b0 := 30) (lo := 30) (hi := 1) (r := 43) (op := PCSDD.BOp.or) (m := ai178) (m1 := ao179) (m2 := ao180) (m3 := an178) (by decide) (by rfl) (by decide) a179 a180 (by rfl)
abbrev an174 : Mgr := {ao178 with nodes := ao178.nodes.push ⟨5,42,43⟩}
abbrev ao174 : Mgr := {an174 with memo := ((PCSDD.BOp.or,9,31),44)::an174.memo}
theorem a174 : ApplyCertificate 12 DEFAULT_LIMITS 20 PCSDD.BOp.or 9 31 ai174 44 ao174 := by
  exact ApplyCertificate.branch (fuel := 19) (a0 := 9) (b0 := 31) (lo := 42) (hi := 43) (r := 44) (op := PCSDD.BOp.or) (m := ai174) (m1 := ao175) (m2 := ao178) (m3 := an174) (by decide) (by rfl) (by decide) a175 a178 (by rfl)
abbrev an168 : Mgr := {ao174 with nodes := ao174.nodes.push ⟨4,41,44⟩}
abbrev ao168 : Mgr := {an168 with memo := ((PCSDD.BOp.or,9,32),45)::an168.memo}
theorem a168 : ApplyCertificate 12 DEFAULT_LIMITS 21 PCSDD.BOp.or 9 32 ai168 45 ao168 := by
  exact ApplyCertificate.branch (fuel := 20) (a0 := 9) (b0 := 32) (lo := 41) (hi := 44) (r := 45) (op := PCSDD.BOp.or) (m := ai168) (m1 := ao169) (m2 := ao174) (m3 := an168) (by decide) (by rfl) (by decide) a169 a174 (by rfl)
abbrev ai181 : Mgr := ao168
abbrev ai182 : Mgr := {ai181 with ops := ai181.ops+1}
abbrev ai183 : Mgr := {ai182 with ops := ai182.ops+1}
abbrev ai184 : Mgr := {ai183 with ops := ai183.ops+1}
abbrev ao184 : Mgr := {ai184 with ops := ai184.ops+1}
theorem a184 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.or 0 22 ai184 22 ao184 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 0) (b0 := 22) (r := 22) (op := PCSDD.BOp.or) (m := ai184) (by decide) (by rfl)
abbrev ai185 : Mgr := ao184
abbrev ai186 : Mgr := {ai185 with ops := ai185.ops+1}
abbrev ao186 : Mgr := {ai186 with ops := ai186.ops+1}
theorem a186 : ApplyCertificate 12 DEFAULT_LIMITS 17 PCSDD.BOp.or 1 0 ai186 1 ao186 := by
  exact ApplyCertificate.hit (fuel := 16) (a0 := 1) (b0 := 0) (r := 1) (op := PCSDD.BOp.or) (m := ai186) (by decide) (by rfl)
abbrev ai187 : Mgr := ao186
abbrev ao187 : Mgr := {ai187 with ops := ai187.ops+1}
theorem a187 : ApplyCertificate 12 DEFAULT_LIMITS 17 PCSDD.BOp.or 1 1 ai187 1 ao187 := by
  exact ApplyCertificate.hit (fuel := 16) (a0 := 1) (b0 := 1) (r := 1) (op := PCSDD.BOp.or) (m := ai187) (by decide) (by rfl)
abbrev an185 : Mgr := ao187
abbrev ao185 : Mgr := {an185 with memo := ((PCSDD.BOp.or,1,22),1)::an185.memo}
theorem a185 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.or 1 22 ai185 1 ao185 := by
  exact ApplyCertificate.branch (fuel := 17) (a0 := 1) (b0 := 22) (lo := 1) (hi := 1) (r := 1) (op := PCSDD.BOp.or) (m := ai185) (m1 := ao186) (m2 := ao187) (m3 := an185) (by decide) (by rfl) (by decide) a186 a187 (by rfl)
abbrev an183 : Mgr := {ao185 with nodes := ao185.nodes.push ⟨8,22,1⟩}
abbrev ao183 : Mgr := {an183 with memo := ((PCSDD.BOp.or,9,22),46)::an183.memo}
theorem a183 : ApplyCertificate 12 DEFAULT_LIMITS 19 PCSDD.BOp.or 9 22 ai183 46 ao183 := by
  exact ApplyCertificate.branch (fuel := 18) (a0 := 9) (b0 := 22) (lo := 22) (hi := 1) (r := 46) (op := PCSDD.BOp.or) (m := ai183) (m1 := ao184) (m2 := ao185) (m3 := an183) (by decide) (by rfl) (by decide) a184 a185 (by rfl)
abbrev ai188 : Mgr := ao183
abbrev ai189 : Mgr := {ai188 with ops := ai188.ops+1}
abbrev ao189 : Mgr := {ai189 with ops := ai189.ops+1}
theorem a189 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.or 0 33 ai189 33 ao189 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 0) (b0 := 33) (r := 33) (op := PCSDD.BOp.or) (m := ai189) (by decide) (by rfl)
abbrev ai190 : Mgr := ao189
abbrev ai191 : Mgr := {ai190 with ops := ai190.ops+1}
abbrev ao191 : Mgr := {ai191 with ops := ai191.ops+1}
theorem a191 : ApplyCertificate 12 DEFAULT_LIMITS 17 PCSDD.BOp.or 1 28 ai191 1 ao191 := by
  exact ApplyCertificate.hit (fuel := 16) (a0 := 1) (b0 := 28) (r := 1) (op := PCSDD.BOp.or) (m := ai191) (by decide) (by rfl)
abbrev ai192 : Mgr := ao191
abbrev ao192 : Mgr := {ai192 with ops := ai192.ops+1}
theorem a192 : ApplyCertificate 12 DEFAULT_LIMITS 17 PCSDD.BOp.or 1 1 ai192 1 ao192 := by
  exact ApplyCertificate.hit (fuel := 16) (a0 := 1) (b0 := 1) (r := 1) (op := PCSDD.BOp.or) (m := ai192) (by decide) (by rfl)
abbrev an190 : Mgr := ao192
abbrev ao190 : Mgr := {an190 with memo := ((PCSDD.BOp.or,1,33),1)::an190.memo}
theorem a190 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.or 1 33 ai190 1 ao190 := by
  exact ApplyCertificate.branch (fuel := 17) (a0 := 1) (b0 := 33) (lo := 1) (hi := 1) (r := 1) (op := PCSDD.BOp.or) (m := ai190) (m1 := ao191) (m2 := ao192) (m3 := an190) (by decide) (by rfl) (by decide) a191 a192 (by rfl)
abbrev an188 : Mgr := {ao190 with nodes := ao190.nodes.push ⟨8,33,1⟩}
abbrev ao188 : Mgr := {an188 with memo := ((PCSDD.BOp.or,9,33),47)::an188.memo}
theorem a188 : ApplyCertificate 12 DEFAULT_LIMITS 19 PCSDD.BOp.or 9 33 ai188 47 ao188 := by
  exact ApplyCertificate.branch (fuel := 18) (a0 := 9) (b0 := 33) (lo := 33) (hi := 1) (r := 47) (op := PCSDD.BOp.or) (m := ai188) (m1 := ao189) (m2 := ao190) (m3 := an188) (by decide) (by rfl) (by decide) a189 a190 (by rfl)
abbrev an182 : Mgr := {ao188 with nodes := ao188.nodes.push ⟨5,46,47⟩}
abbrev ao182 : Mgr := {an182 with memo := ((PCSDD.BOp.or,9,34),48)::an182.memo}
theorem a182 : ApplyCertificate 12 DEFAULT_LIMITS 20 PCSDD.BOp.or 9 34 ai182 48 ao182 := by
  exact ApplyCertificate.branch (fuel := 19) (a0 := 9) (b0 := 34) (lo := 46) (hi := 47) (r := 48) (op := PCSDD.BOp.or) (m := ai182) (m1 := ao183) (m2 := ao188) (m3 := an182) (by decide) (by rfl) (by decide) a183 a188 (by rfl)
abbrev ai193 : Mgr := ao182
abbrev ai194 : Mgr := {ai193 with ops := ai193.ops+1}
abbrev ai195 : Mgr := {ai194 with ops := ai194.ops+1}
abbrev ao195 : Mgr := {ai195 with ops := ai195.ops+1}
theorem a195 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.or 0 35 ai195 35 ao195 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 0) (b0 := 35) (r := 35) (op := PCSDD.BOp.or) (m := ai195) (by decide) (by rfl)
abbrev ai196 : Mgr := ao195
abbrev ai197 : Mgr := {ai196 with ops := ai196.ops+1}
abbrev ao197 : Mgr := {ai197 with ops := ai197.ops+1}
theorem a197 : ApplyCertificate 12 DEFAULT_LIMITS 17 PCSDD.BOp.or 1 25 ai197 1 ao197 := by
  exact ApplyCertificate.hit (fuel := 16) (a0 := 1) (b0 := 25) (r := 1) (op := PCSDD.BOp.or) (m := ai197) (by decide) (by rfl)
abbrev ai198 : Mgr := ao197
abbrev ao198 : Mgr := {ai198 with ops := ai198.ops+1}
theorem a198 : ApplyCertificate 12 DEFAULT_LIMITS 17 PCSDD.BOp.or 1 1 ai198 1 ao198 := by
  exact ApplyCertificate.hit (fuel := 16) (a0 := 1) (b0 := 1) (r := 1) (op := PCSDD.BOp.or) (m := ai198) (by decide) (by rfl)
abbrev an196 : Mgr := ao198
abbrev ao196 : Mgr := {an196 with memo := ((PCSDD.BOp.or,1,35),1)::an196.memo}
theorem a196 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.or 1 35 ai196 1 ao196 := by
  exact ApplyCertificate.branch (fuel := 17) (a0 := 1) (b0 := 35) (lo := 1) (hi := 1) (r := 1) (op := PCSDD.BOp.or) (m := ai196) (m1 := ao197) (m2 := ao198) (m3 := an196) (by decide) (by rfl) (by decide) a197 a198 (by rfl)
abbrev an194 : Mgr := {ao196 with nodes := ao196.nodes.push ⟨8,35,1⟩}
abbrev ao194 : Mgr := {an194 with memo := ((PCSDD.BOp.or,9,35),49)::an194.memo}
theorem a194 : ApplyCertificate 12 DEFAULT_LIMITS 19 PCSDD.BOp.or 9 35 ai194 49 ao194 := by
  exact ApplyCertificate.branch (fuel := 18) (a0 := 9) (b0 := 35) (lo := 35) (hi := 1) (r := 49) (op := PCSDD.BOp.or) (m := ai194) (m1 := ao195) (m2 := ao196) (m3 := an194) (by decide) (by rfl) (by decide) a195 a196 (by rfl)
abbrev ai199 : Mgr := ao194
abbrev ai200 : Mgr := {ai199 with ops := ai199.ops+1}
abbrev ao200 : Mgr := {ai200 with ops := ai200.ops+1}
theorem a200 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.or 0 36 ai200 36 ao200 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 0) (b0 := 36) (r := 36) (op := PCSDD.BOp.or) (m := ai200) (by decide) (by rfl)
abbrev ai201 : Mgr := ao200
abbrev ai202 : Mgr := {ai201 with ops := ai201.ops+1}
abbrev ao202 : Mgr := {ai202 with ops := ai202.ops+1}
theorem a202 : ApplyCertificate 12 DEFAULT_LIMITS 17 PCSDD.BOp.or 1 30 ai202 1 ao202 := by
  exact ApplyCertificate.hit (fuel := 16) (a0 := 1) (b0 := 30) (r := 1) (op := PCSDD.BOp.or) (m := ai202) (by decide) (by rfl)
abbrev ai203 : Mgr := ao202
abbrev ao203 : Mgr := {ai203 with ops := ai203.ops+1}
theorem a203 : ApplyCertificate 12 DEFAULT_LIMITS 17 PCSDD.BOp.or 1 1 ai203 1 ao203 := by
  exact ApplyCertificate.hit (fuel := 16) (a0 := 1) (b0 := 1) (r := 1) (op := PCSDD.BOp.or) (m := ai203) (by decide) (by rfl)
abbrev an201 : Mgr := ao203
abbrev ao201 : Mgr := {an201 with memo := ((PCSDD.BOp.or,1,36),1)::an201.memo}
theorem a201 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.or 1 36 ai201 1 ao201 := by
  exact ApplyCertificate.branch (fuel := 17) (a0 := 1) (b0 := 36) (lo := 1) (hi := 1) (r := 1) (op := PCSDD.BOp.or) (m := ai201) (m1 := ao202) (m2 := ao203) (m3 := an201) (by decide) (by rfl) (by decide) a202 a203 (by rfl)
abbrev an199 : Mgr := {ao201 with nodes := ao201.nodes.push ⟨8,36,1⟩}
abbrev ao199 : Mgr := {an199 with memo := ((PCSDD.BOp.or,9,36),50)::an199.memo}
theorem a199 : ApplyCertificate 12 DEFAULT_LIMITS 19 PCSDD.BOp.or 9 36 ai199 50 ao199 := by
  exact ApplyCertificate.branch (fuel := 18) (a0 := 9) (b0 := 36) (lo := 36) (hi := 1) (r := 50) (op := PCSDD.BOp.or) (m := ai199) (m1 := ao200) (m2 := ao201) (m3 := an199) (by decide) (by rfl) (by decide) a200 a201 (by rfl)
abbrev an193 : Mgr := {ao199 with nodes := ao199.nodes.push ⟨5,49,50⟩}
abbrev ao193 : Mgr := {an193 with memo := ((PCSDD.BOp.or,9,37),51)::an193.memo}
theorem a193 : ApplyCertificate 12 DEFAULT_LIMITS 20 PCSDD.BOp.or 9 37 ai193 51 ao193 := by
  exact ApplyCertificate.branch (fuel := 19) (a0 := 9) (b0 := 37) (lo := 49) (hi := 50) (r := 51) (op := PCSDD.BOp.or) (m := ai193) (m1 := ao194) (m2 := ao199) (m3 := an193) (by decide) (by rfl) (by decide) a194 a199 (by rfl)
abbrev an181 : Mgr := {ao193 with nodes := ao193.nodes.push ⟨4,48,51⟩}
abbrev ao181 : Mgr := {an181 with memo := ((PCSDD.BOp.or,9,38),52)::an181.memo}
theorem a181 : ApplyCertificate 12 DEFAULT_LIMITS 21 PCSDD.BOp.or 9 38 ai181 52 ao181 := by
  exact ApplyCertificate.branch (fuel := 20) (a0 := 9) (b0 := 38) (lo := 48) (hi := 51) (r := 52) (op := PCSDD.BOp.or) (m := ai181) (m1 := ao182) (m2 := ao193) (m3 := an181) (by decide) (by rfl) (by decide) a182 a193 (by rfl)
abbrev an167 : Mgr := {ao181 with nodes := ao181.nodes.push ⟨3,45,52⟩}
abbrev ao167 : Mgr := {an167 with memo := ((PCSDD.BOp.or,9,39),53)::an167.memo}
theorem a167 : ApplyCertificate 12 DEFAULT_LIMITS 22 PCSDD.BOp.or 9 39 ai167 53 ao167 := by
  exact ApplyCertificate.branch (fuel := 21) (a0 := 9) (b0 := 39) (lo := 45) (hi := 52) (r := 53) (op := PCSDD.BOp.or) (m := ai167) (m1 := ao168) (m2 := ao181) (m3 := an167) (by decide) (by rfl) (by decide) a168 a181 (by rfl)
abbrev an151 : Mgr := {ao167 with nodes := ao167.nodes.push ⟨2,39,53⟩}
abbrev ao151 : Mgr := {an151 with memo := ((PCSDD.BOp.or,10,39),54)::an151.memo}
theorem a151 : ApplyCertificate 12 DEFAULT_LIMITS 23 PCSDD.BOp.or 10 39 ai151 54 ao151 := by
  exact ApplyCertificate.branch (fuel := 22) (a0 := 10) (b0 := 39) (lo := 39) (hi := 53) (r := 54) (op := PCSDD.BOp.or) (m := ai151) (m1 := ao152) (m2 := ao167) (m3 := an151) (by decide) (by rfl) (by decide) a152 a167 (by rfl)
abbrev ai204 : Mgr := ao151
abbrev ai205 : Mgr := {ai204 with ops := ai204.ops+1}
abbrev ai206 : Mgr := {ai205 with ops := ai205.ops+1}
abbrev ai207 : Mgr := {ai206 with ops := ai206.ops+1}
abbrev ai208 : Mgr := {ai207 with ops := ai207.ops+1}
abbrev ao208 : Mgr := {ai208 with ops := ai208.ops+1}
theorem a208 : ApplyCertificate 12 DEFAULT_LIMITS 19 PCSDD.BOp.or 6 0 ai208 6 ao208 := by
  exact ApplyCertificate.hit (fuel := 18) (a0 := 6) (b0 := 0) (r := 6) (op := PCSDD.BOp.or) (m := ai208) (by decide) (by rfl)
abbrev ai209 : Mgr := ao208
abbrev ai210 : Mgr := {ai209 with ops := ai209.ops+1}
abbrev ao210 : Mgr := {ai210 with ops := ai210.ops+1}
theorem a210 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.or 0 28 ai210 28 ao210 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 0) (b0 := 28) (r := 28) (op := PCSDD.BOp.or) (m := ai210) (by decide) (by rfl)
abbrev ai211 : Mgr := ao210
abbrev ao211 : Mgr := {ai211 with ops := ai211.ops+1}
theorem a211 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.or 1 28 ai211 1 ao211 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 1) (b0 := 28) (r := 1) (op := PCSDD.BOp.or) (m := ai211) (by decide) (by rfl)
abbrev an209 : Mgr := {ao211 with nodes := ao211.nodes.push ⟨7,28,1⟩}
abbrev ao209 : Mgr := {an209 with memo := ((PCSDD.BOp.or,6,28),55)::an209.memo}
theorem a209 : ApplyCertificate 12 DEFAULT_LIMITS 19 PCSDD.BOp.or 6 28 ai209 55 ao209 := by
  exact ApplyCertificate.branch (fuel := 18) (a0 := 6) (b0 := 28) (lo := 28) (hi := 1) (r := 55) (op := PCSDD.BOp.or) (m := ai209) (m1 := ao210) (m2 := ao211) (m3 := an209) (by decide) (by rfl) (by decide) a210 a211 (by rfl)
abbrev an207 : Mgr := {ao209 with nodes := ao209.nodes.push ⟨5,6,55⟩}
abbrev ao207 : Mgr := {an207 with memo := ((PCSDD.BOp.or,6,29),56)::an207.memo}
theorem a207 : ApplyCertificate 12 DEFAULT_LIMITS 20 PCSDD.BOp.or 6 29 ai207 56 ao207 := by
  exact ApplyCertificate.branch (fuel := 19) (a0 := 6) (b0 := 29) (lo := 6) (hi := 55) (r := 56) (op := PCSDD.BOp.or) (m := ai207) (m1 := ao208) (m2 := ao209) (m3 := an207) (by decide) (by rfl) (by decide) a208 a209 (by rfl)
abbrev ai212 : Mgr := ao207
abbrev ai213 : Mgr := {ai212 with ops := ai212.ops+1}
abbrev ai214 : Mgr := {ai213 with ops := ai213.ops+1}
abbrev ao214 : Mgr := {ai214 with ops := ai214.ops+1}
theorem a214 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.or 0 25 ai214 25 ao214 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 0) (b0 := 25) (r := 25) (op := PCSDD.BOp.or) (m := ai214) (by decide) (by rfl)
abbrev ai215 : Mgr := ao214
abbrev ao215 : Mgr := {ai215 with ops := ai215.ops+1}
theorem a215 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.or 1 25 ai215 1 ao215 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 1) (b0 := 25) (r := 1) (op := PCSDD.BOp.or) (m := ai215) (by decide) (by rfl)
abbrev an213 : Mgr := {ao215 with nodes := ao215.nodes.push ⟨7,25,1⟩}
abbrev ao213 : Mgr := {an213 with memo := ((PCSDD.BOp.or,6,25),57)::an213.memo}
theorem a213 : ApplyCertificate 12 DEFAULT_LIMITS 19 PCSDD.BOp.or 6 25 ai213 57 ao213 := by
  exact ApplyCertificate.branch (fuel := 18) (a0 := 6) (b0 := 25) (lo := 25) (hi := 1) (r := 57) (op := PCSDD.BOp.or) (m := ai213) (m1 := ao214) (m2 := ao215) (m3 := an213) (by decide) (by rfl) (by decide) a214 a215 (by rfl)
abbrev ai216 : Mgr := ao213
abbrev ai217 : Mgr := {ai216 with ops := ai216.ops+1}
abbrev ao217 : Mgr := {ai217 with ops := ai217.ops+1}
theorem a217 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.or 0 30 ai217 30 ao217 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 0) (b0 := 30) (r := 30) (op := PCSDD.BOp.or) (m := ai217) (by decide) (by rfl)
abbrev ai218 : Mgr := ao217
abbrev ao218 : Mgr := {ai218 with ops := ai218.ops+1}
theorem a218 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.or 1 30 ai218 1 ao218 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 1) (b0 := 30) (r := 1) (op := PCSDD.BOp.or) (m := ai218) (by decide) (by rfl)
abbrev an216 : Mgr := {ao218 with nodes := ao218.nodes.push ⟨7,30,1⟩}
abbrev ao216 : Mgr := {an216 with memo := ((PCSDD.BOp.or,6,30),58)::an216.memo}
theorem a216 : ApplyCertificate 12 DEFAULT_LIMITS 19 PCSDD.BOp.or 6 30 ai216 58 ao216 := by
  exact ApplyCertificate.branch (fuel := 18) (a0 := 6) (b0 := 30) (lo := 30) (hi := 1) (r := 58) (op := PCSDD.BOp.or) (m := ai216) (m1 := ao217) (m2 := ao218) (m3 := an216) (by decide) (by rfl) (by decide) a217 a218 (by rfl)
abbrev an212 : Mgr := {ao216 with nodes := ao216.nodes.push ⟨5,57,58⟩}
abbrev ao212 : Mgr := {an212 with memo := ((PCSDD.BOp.or,6,31),59)::an212.memo}
theorem a212 : ApplyCertificate 12 DEFAULT_LIMITS 20 PCSDD.BOp.or 6 31 ai212 59 ao212 := by
  exact ApplyCertificate.branch (fuel := 19) (a0 := 6) (b0 := 31) (lo := 57) (hi := 58) (r := 59) (op := PCSDD.BOp.or) (m := ai212) (m1 := ao213) (m2 := ao216) (m3 := an212) (by decide) (by rfl) (by decide) a213 a216 (by rfl)
abbrev an206 : Mgr := {ao212 with nodes := ao212.nodes.push ⟨4,56,59⟩}
abbrev ao206 : Mgr := {an206 with memo := ((PCSDD.BOp.or,6,32),60)::an206.memo}
theorem a206 : ApplyCertificate 12 DEFAULT_LIMITS 21 PCSDD.BOp.or 6 32 ai206 60 ao206 := by
  exact ApplyCertificate.branch (fuel := 20) (a0 := 6) (b0 := 32) (lo := 56) (hi := 59) (r := 60) (op := PCSDD.BOp.or) (m := ai206) (m1 := ao207) (m2 := ao212) (m3 := an206) (by decide) (by rfl) (by decide) a207 a212 (by rfl)
abbrev ai219 : Mgr := ao206
abbrev ai220 : Mgr := {ai219 with ops := ai219.ops+1}
abbrev ai221 : Mgr := {ai220 with ops := ai220.ops+1}
abbrev ai222 : Mgr := {ai221 with ops := ai221.ops+1}
abbrev ao222 : Mgr := {ai222 with ops := ai222.ops+1}
theorem a222 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.or 0 22 ai222 22 ao222 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 0) (b0 := 22) (r := 22) (op := PCSDD.BOp.or) (m := ai222) (by decide) (by rfl)
abbrev ai223 : Mgr := ao222
abbrev ao223 : Mgr := {ai223 with ops := ai223.ops+1}
theorem a223 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.or 1 22 ai223 1 ao223 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 1) (b0 := 22) (r := 1) (op := PCSDD.BOp.or) (m := ai223) (by decide) (by rfl)
abbrev an221 : Mgr := {ao223 with nodes := ao223.nodes.push ⟨7,22,1⟩}
abbrev ao221 : Mgr := {an221 with memo := ((PCSDD.BOp.or,6,22),61)::an221.memo}
theorem a221 : ApplyCertificate 12 DEFAULT_LIMITS 19 PCSDD.BOp.or 6 22 ai221 61 ao221 := by
  exact ApplyCertificate.branch (fuel := 18) (a0 := 6) (b0 := 22) (lo := 22) (hi := 1) (r := 61) (op := PCSDD.BOp.or) (m := ai221) (m1 := ao222) (m2 := ao223) (m3 := an221) (by decide) (by rfl) (by decide) a222 a223 (by rfl)
abbrev ai224 : Mgr := ao221
abbrev ai225 : Mgr := {ai224 with ops := ai224.ops+1}
abbrev ao225 : Mgr := {ai225 with ops := ai225.ops+1}
theorem a225 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.or 0 33 ai225 33 ao225 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 0) (b0 := 33) (r := 33) (op := PCSDD.BOp.or) (m := ai225) (by decide) (by rfl)
abbrev ai226 : Mgr := ao225
abbrev ao226 : Mgr := {ai226 with ops := ai226.ops+1}
theorem a226 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.or 1 33 ai226 1 ao226 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 1) (b0 := 33) (r := 1) (op := PCSDD.BOp.or) (m := ai226) (by decide) (by rfl)
abbrev an224 : Mgr := {ao226 with nodes := ao226.nodes.push ⟨7,33,1⟩}
abbrev ao224 : Mgr := {an224 with memo := ((PCSDD.BOp.or,6,33),62)::an224.memo}
theorem a224 : ApplyCertificate 12 DEFAULT_LIMITS 19 PCSDD.BOp.or 6 33 ai224 62 ao224 := by
  exact ApplyCertificate.branch (fuel := 18) (a0 := 6) (b0 := 33) (lo := 33) (hi := 1) (r := 62) (op := PCSDD.BOp.or) (m := ai224) (m1 := ao225) (m2 := ao226) (m3 := an224) (by decide) (by rfl) (by decide) a225 a226 (by rfl)
abbrev an220 : Mgr := {ao224 with nodes := ao224.nodes.push ⟨5,61,62⟩}
abbrev ao220 : Mgr := {an220 with memo := ((PCSDD.BOp.or,6,34),63)::an220.memo}
theorem a220 : ApplyCertificate 12 DEFAULT_LIMITS 20 PCSDD.BOp.or 6 34 ai220 63 ao220 := by
  exact ApplyCertificate.branch (fuel := 19) (a0 := 6) (b0 := 34) (lo := 61) (hi := 62) (r := 63) (op := PCSDD.BOp.or) (m := ai220) (m1 := ao221) (m2 := ao224) (m3 := an220) (by decide) (by rfl) (by decide) a221 a224 (by rfl)
abbrev ai227 : Mgr := ao220
abbrev ai228 : Mgr := {ai227 with ops := ai227.ops+1}
abbrev ai229 : Mgr := {ai228 with ops := ai228.ops+1}
abbrev ao229 : Mgr := {ai229 with ops := ai229.ops+1}
theorem a229 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.or 0 35 ai229 35 ao229 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 0) (b0 := 35) (r := 35) (op := PCSDD.BOp.or) (m := ai229) (by decide) (by rfl)
abbrev ai230 : Mgr := ao229
abbrev ao230 : Mgr := {ai230 with ops := ai230.ops+1}
theorem a230 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.or 1 35 ai230 1 ao230 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 1) (b0 := 35) (r := 1) (op := PCSDD.BOp.or) (m := ai230) (by decide) (by rfl)
abbrev an228 : Mgr := {ao230 with nodes := ao230.nodes.push ⟨7,35,1⟩}
abbrev ao228 : Mgr := {an228 with memo := ((PCSDD.BOp.or,6,35),64)::an228.memo}
theorem a228 : ApplyCertificate 12 DEFAULT_LIMITS 19 PCSDD.BOp.or 6 35 ai228 64 ao228 := by
  exact ApplyCertificate.branch (fuel := 18) (a0 := 6) (b0 := 35) (lo := 35) (hi := 1) (r := 64) (op := PCSDD.BOp.or) (m := ai228) (m1 := ao229) (m2 := ao230) (m3 := an228) (by decide) (by rfl) (by decide) a229 a230 (by rfl)
abbrev ai231 : Mgr := ao228
abbrev ai232 : Mgr := {ai231 with ops := ai231.ops+1}
abbrev ao232 : Mgr := {ai232 with ops := ai232.ops+1}
theorem a232 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.or 0 36 ai232 36 ao232 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 0) (b0 := 36) (r := 36) (op := PCSDD.BOp.or) (m := ai232) (by decide) (by rfl)
abbrev ai233 : Mgr := ao232
abbrev ao233 : Mgr := {ai233 with ops := ai233.ops+1}
theorem a233 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.or 1 36 ai233 1 ao233 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 1) (b0 := 36) (r := 1) (op := PCSDD.BOp.or) (m := ai233) (by decide) (by rfl)
abbrev an231 : Mgr := {ao233 with nodes := ao233.nodes.push ⟨7,36,1⟩}
abbrev ao231 : Mgr := {an231 with memo := ((PCSDD.BOp.or,6,36),65)::an231.memo}
theorem a231 : ApplyCertificate 12 DEFAULT_LIMITS 19 PCSDD.BOp.or 6 36 ai231 65 ao231 := by
  exact ApplyCertificate.branch (fuel := 18) (a0 := 6) (b0 := 36) (lo := 36) (hi := 1) (r := 65) (op := PCSDD.BOp.or) (m := ai231) (m1 := ao232) (m2 := ao233) (m3 := an231) (by decide) (by rfl) (by decide) a232 a233 (by rfl)
abbrev an227 : Mgr := {ao231 with nodes := ao231.nodes.push ⟨5,64,65⟩}
abbrev ao227 : Mgr := {an227 with memo := ((PCSDD.BOp.or,6,37),66)::an227.memo}
theorem a227 : ApplyCertificate 12 DEFAULT_LIMITS 20 PCSDD.BOp.or 6 37 ai227 66 ao227 := by
  exact ApplyCertificate.branch (fuel := 19) (a0 := 6) (b0 := 37) (lo := 64) (hi := 65) (r := 66) (op := PCSDD.BOp.or) (m := ai227) (m1 := ao228) (m2 := ao231) (m3 := an227) (by decide) (by rfl) (by decide) a228 a231 (by rfl)
abbrev an219 : Mgr := {ao227 with nodes := ao227.nodes.push ⟨4,63,66⟩}
abbrev ao219 : Mgr := {an219 with memo := ((PCSDD.BOp.or,6,38),67)::an219.memo}
theorem a219 : ApplyCertificate 12 DEFAULT_LIMITS 21 PCSDD.BOp.or 6 38 ai219 67 ao219 := by
  exact ApplyCertificate.branch (fuel := 20) (a0 := 6) (b0 := 38) (lo := 63) (hi := 66) (r := 67) (op := PCSDD.BOp.or) (m := ai219) (m1 := ao220) (m2 := ao227) (m3 := an219) (by decide) (by rfl) (by decide) a220 a227 (by rfl)
abbrev an205 : Mgr := {ao219 with nodes := ao219.nodes.push ⟨3,60,67⟩}
abbrev ao205 : Mgr := {an205 with memo := ((PCSDD.BOp.or,6,39),68)::an205.memo}
theorem a205 : ApplyCertificate 12 DEFAULT_LIMITS 22 PCSDD.BOp.or 6 39 ai205 68 ao205 := by
  exact ApplyCertificate.branch (fuel := 21) (a0 := 6) (b0 := 39) (lo := 60) (hi := 67) (r := 68) (op := PCSDD.BOp.or) (m := ai205) (m1 := ao206) (m2 := ao219) (m3 := an205) (by decide) (by rfl) (by decide) a206 a219 (by rfl)
abbrev ai234 : Mgr := ao205
abbrev ai235 : Mgr := {ai234 with ops := ai234.ops+1}
abbrev ai236 : Mgr := {ai235 with ops := ai235.ops+1}
abbrev ai237 : Mgr := {ai236 with ops := ai236.ops+1}
abbrev ao237 : Mgr := {ai237 with ops := ai237.ops+1}
theorem a237 : ApplyCertificate 12 DEFAULT_LIMITS 19 PCSDD.BOp.or 11 0 ai237 11 ao237 := by
  exact ApplyCertificate.hit (fuel := 18) (a0 := 11) (b0 := 0) (r := 11) (op := PCSDD.BOp.or) (m := ai237) (by decide) (by rfl)
abbrev ai238 : Mgr := ao237
abbrev ai239 : Mgr := {ai238 with ops := ai238.ops+1}
abbrev ao239 : Mgr := {ai239 with ops := ai239.ops+1}
theorem a239 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.or 9 28 ai239 40 ao239 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 9) (b0 := 28) (r := 40) (op := PCSDD.BOp.or) (m := ai239) (by decide) (by rfl)
abbrev ai240 : Mgr := ao239
abbrev ao240 : Mgr := {ai240 with ops := ai240.ops+1}
theorem a240 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.or 1 28 ai240 1 ao240 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 1) (b0 := 28) (r := 1) (op := PCSDD.BOp.or) (m := ai240) (by decide) (by rfl)
abbrev an238 : Mgr := {ao240 with nodes := ao240.nodes.push ⟨7,40,1⟩}
abbrev ao238 : Mgr := {an238 with memo := ((PCSDD.BOp.or,11,28),69)::an238.memo}
theorem a238 : ApplyCertificate 12 DEFAULT_LIMITS 19 PCSDD.BOp.or 11 28 ai238 69 ao238 := by
  exact ApplyCertificate.branch (fuel := 18) (a0 := 11) (b0 := 28) (lo := 40) (hi := 1) (r := 69) (op := PCSDD.BOp.or) (m := ai238) (m1 := ao239) (m2 := ao240) (m3 := an238) (by decide) (by rfl) (by decide) a239 a240 (by rfl)
abbrev an236 : Mgr := {ao238 with nodes := ao238.nodes.push ⟨5,11,69⟩}
abbrev ao236 : Mgr := {an236 with memo := ((PCSDD.BOp.or,11,29),70)::an236.memo}
theorem a236 : ApplyCertificate 12 DEFAULT_LIMITS 20 PCSDD.BOp.or 11 29 ai236 70 ao236 := by
  exact ApplyCertificate.branch (fuel := 19) (a0 := 11) (b0 := 29) (lo := 11) (hi := 69) (r := 70) (op := PCSDD.BOp.or) (m := ai236) (m1 := ao237) (m2 := ao238) (m3 := an236) (by decide) (by rfl) (by decide) a237 a238 (by rfl)
abbrev ai241 : Mgr := ao236
abbrev ai242 : Mgr := {ai241 with ops := ai241.ops+1}
abbrev ai243 : Mgr := {ai242 with ops := ai242.ops+1}
abbrev ao243 : Mgr := {ai243 with ops := ai243.ops+1}
theorem a243 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.or 9 25 ai243 42 ao243 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 9) (b0 := 25) (r := 42) (op := PCSDD.BOp.or) (m := ai243) (by decide) (by rfl)
abbrev ai244 : Mgr := ao243
abbrev ao244 : Mgr := {ai244 with ops := ai244.ops+1}
theorem a244 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.or 1 25 ai244 1 ao244 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 1) (b0 := 25) (r := 1) (op := PCSDD.BOp.or) (m := ai244) (by decide) (by rfl)
abbrev an242 : Mgr := {ao244 with nodes := ao244.nodes.push ⟨7,42,1⟩}
abbrev ao242 : Mgr := {an242 with memo := ((PCSDD.BOp.or,11,25),71)::an242.memo}
theorem a242 : ApplyCertificate 12 DEFAULT_LIMITS 19 PCSDD.BOp.or 11 25 ai242 71 ao242 := by
  exact ApplyCertificate.branch (fuel := 18) (a0 := 11) (b0 := 25) (lo := 42) (hi := 1) (r := 71) (op := PCSDD.BOp.or) (m := ai242) (m1 := ao243) (m2 := ao244) (m3 := an242) (by decide) (by rfl) (by decide) a243 a244 (by rfl)
abbrev ai245 : Mgr := ao242
abbrev ai246 : Mgr := {ai245 with ops := ai245.ops+1}
abbrev ao246 : Mgr := {ai246 with ops := ai246.ops+1}
theorem a246 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.or 9 30 ai246 43 ao246 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 9) (b0 := 30) (r := 43) (op := PCSDD.BOp.or) (m := ai246) (by decide) (by rfl)
abbrev ai247 : Mgr := ao246
abbrev ao247 : Mgr := {ai247 with ops := ai247.ops+1}
theorem a247 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.or 1 30 ai247 1 ao247 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 1) (b0 := 30) (r := 1) (op := PCSDD.BOp.or) (m := ai247) (by decide) (by rfl)
abbrev an245 : Mgr := {ao247 with nodes := ao247.nodes.push ⟨7,43,1⟩}
abbrev ao245 : Mgr := {an245 with memo := ((PCSDD.BOp.or,11,30),72)::an245.memo}
theorem a245 : ApplyCertificate 12 DEFAULT_LIMITS 19 PCSDD.BOp.or 11 30 ai245 72 ao245 := by
  exact ApplyCertificate.branch (fuel := 18) (a0 := 11) (b0 := 30) (lo := 43) (hi := 1) (r := 72) (op := PCSDD.BOp.or) (m := ai245) (m1 := ao246) (m2 := ao247) (m3 := an245) (by decide) (by rfl) (by decide) a246 a247 (by rfl)
abbrev an241 : Mgr := {ao245 with nodes := ao245.nodes.push ⟨5,71,72⟩}
abbrev ao241 : Mgr := {an241 with memo := ((PCSDD.BOp.or,11,31),73)::an241.memo}
theorem a241 : ApplyCertificate 12 DEFAULT_LIMITS 20 PCSDD.BOp.or 11 31 ai241 73 ao241 := by
  exact ApplyCertificate.branch (fuel := 19) (a0 := 11) (b0 := 31) (lo := 71) (hi := 72) (r := 73) (op := PCSDD.BOp.or) (m := ai241) (m1 := ao242) (m2 := ao245) (m3 := an241) (by decide) (by rfl) (by decide) a242 a245 (by rfl)
abbrev an235 : Mgr := {ao241 with nodes := ao241.nodes.push ⟨4,70,73⟩}
abbrev ao235 : Mgr := {an235 with memo := ((PCSDD.BOp.or,11,32),74)::an235.memo}
theorem a235 : ApplyCertificate 12 DEFAULT_LIMITS 21 PCSDD.BOp.or 11 32 ai235 74 ao235 := by
  exact ApplyCertificate.branch (fuel := 20) (a0 := 11) (b0 := 32) (lo := 70) (hi := 73) (r := 74) (op := PCSDD.BOp.or) (m := ai235) (m1 := ao236) (m2 := ao241) (m3 := an235) (by decide) (by rfl) (by decide) a236 a241 (by rfl)
abbrev ai248 : Mgr := ao235
abbrev ai249 : Mgr := {ai248 with ops := ai248.ops+1}
abbrev ai250 : Mgr := {ai249 with ops := ai249.ops+1}
abbrev ai251 : Mgr := {ai250 with ops := ai250.ops+1}
abbrev ao251 : Mgr := {ai251 with ops := ai251.ops+1}
theorem a251 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.or 9 22 ai251 46 ao251 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 9) (b0 := 22) (r := 46) (op := PCSDD.BOp.or) (m := ai251) (by decide) (by rfl)
abbrev ai252 : Mgr := ao251
abbrev ao252 : Mgr := {ai252 with ops := ai252.ops+1}
theorem a252 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.or 1 22 ai252 1 ao252 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 1) (b0 := 22) (r := 1) (op := PCSDD.BOp.or) (m := ai252) (by decide) (by rfl)
abbrev an250 : Mgr := {ao252 with nodes := ao252.nodes.push ⟨7,46,1⟩}
abbrev ao250 : Mgr := {an250 with memo := ((PCSDD.BOp.or,11,22),75)::an250.memo}
theorem a250 : ApplyCertificate 12 DEFAULT_LIMITS 19 PCSDD.BOp.or 11 22 ai250 75 ao250 := by
  exact ApplyCertificate.branch (fuel := 18) (a0 := 11) (b0 := 22) (lo := 46) (hi := 1) (r := 75) (op := PCSDD.BOp.or) (m := ai250) (m1 := ao251) (m2 := ao252) (m3 := an250) (by decide) (by rfl) (by decide) a251 a252 (by rfl)
abbrev ai253 : Mgr := ao250
abbrev ai254 : Mgr := {ai253 with ops := ai253.ops+1}
abbrev ao254 : Mgr := {ai254 with ops := ai254.ops+1}
theorem a254 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.or 9 33 ai254 47 ao254 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 9) (b0 := 33) (r := 47) (op := PCSDD.BOp.or) (m := ai254) (by decide) (by rfl)
abbrev ai255 : Mgr := ao254
abbrev ao255 : Mgr := {ai255 with ops := ai255.ops+1}
theorem a255 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.or 1 33 ai255 1 ao255 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 1) (b0 := 33) (r := 1) (op := PCSDD.BOp.or) (m := ai255) (by decide) (by rfl)
abbrev an253 : Mgr := {ao255 with nodes := ao255.nodes.push ⟨7,47,1⟩}
abbrev ao253 : Mgr := {an253 with memo := ((PCSDD.BOp.or,11,33),76)::an253.memo}
theorem a253 : ApplyCertificate 12 DEFAULT_LIMITS 19 PCSDD.BOp.or 11 33 ai253 76 ao253 := by
  exact ApplyCertificate.branch (fuel := 18) (a0 := 11) (b0 := 33) (lo := 47) (hi := 1) (r := 76) (op := PCSDD.BOp.or) (m := ai253) (m1 := ao254) (m2 := ao255) (m3 := an253) (by decide) (by rfl) (by decide) a254 a255 (by rfl)
abbrev an249 : Mgr := {ao253 with nodes := ao253.nodes.push ⟨5,75,76⟩}
abbrev ao249 : Mgr := {an249 with memo := ((PCSDD.BOp.or,11,34),77)::an249.memo}
theorem a249 : ApplyCertificate 12 DEFAULT_LIMITS 20 PCSDD.BOp.or 11 34 ai249 77 ao249 := by
  exact ApplyCertificate.branch (fuel := 19) (a0 := 11) (b0 := 34) (lo := 75) (hi := 76) (r := 77) (op := PCSDD.BOp.or) (m := ai249) (m1 := ao250) (m2 := ao253) (m3 := an249) (by decide) (by rfl) (by decide) a250 a253 (by rfl)
abbrev ai256 : Mgr := ao249
abbrev ai257 : Mgr := {ai256 with ops := ai256.ops+1}
abbrev ai258 : Mgr := {ai257 with ops := ai257.ops+1}
abbrev ao258 : Mgr := {ai258 with ops := ai258.ops+1}
theorem a258 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.or 9 35 ai258 49 ao258 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 9) (b0 := 35) (r := 49) (op := PCSDD.BOp.or) (m := ai258) (by decide) (by rfl)
abbrev ai259 : Mgr := ao258
abbrev ao259 : Mgr := {ai259 with ops := ai259.ops+1}
theorem a259 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.or 1 35 ai259 1 ao259 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 1) (b0 := 35) (r := 1) (op := PCSDD.BOp.or) (m := ai259) (by decide) (by rfl)
abbrev an257 : Mgr := {ao259 with nodes := ao259.nodes.push ⟨7,49,1⟩}
abbrev ao257 : Mgr := {an257 with memo := ((PCSDD.BOp.or,11,35),78)::an257.memo}
theorem a257 : ApplyCertificate 12 DEFAULT_LIMITS 19 PCSDD.BOp.or 11 35 ai257 78 ao257 := by
  exact ApplyCertificate.branch (fuel := 18) (a0 := 11) (b0 := 35) (lo := 49) (hi := 1) (r := 78) (op := PCSDD.BOp.or) (m := ai257) (m1 := ao258) (m2 := ao259) (m3 := an257) (by decide) (by rfl) (by decide) a258 a259 (by rfl)
abbrev ai260 : Mgr := ao257
abbrev ai261 : Mgr := {ai260 with ops := ai260.ops+1}
abbrev ao261 : Mgr := {ai261 with ops := ai261.ops+1}
theorem a261 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.or 9 36 ai261 50 ao261 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 9) (b0 := 36) (r := 50) (op := PCSDD.BOp.or) (m := ai261) (by decide) (by rfl)
abbrev ai262 : Mgr := ao261
abbrev ao262 : Mgr := {ai262 with ops := ai262.ops+1}
theorem a262 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.or 1 36 ai262 1 ao262 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 1) (b0 := 36) (r := 1) (op := PCSDD.BOp.or) (m := ai262) (by decide) (by rfl)
abbrev an260 : Mgr := {ao262 with nodes := ao262.nodes.push ⟨7,50,1⟩}
abbrev ao260 : Mgr := {an260 with memo := ((PCSDD.BOp.or,11,36),79)::an260.memo}
theorem a260 : ApplyCertificate 12 DEFAULT_LIMITS 19 PCSDD.BOp.or 11 36 ai260 79 ao260 := by
  exact ApplyCertificate.branch (fuel := 18) (a0 := 11) (b0 := 36) (lo := 50) (hi := 1) (r := 79) (op := PCSDD.BOp.or) (m := ai260) (m1 := ao261) (m2 := ao262) (m3 := an260) (by decide) (by rfl) (by decide) a261 a262 (by rfl)
abbrev an256 : Mgr := {ao260 with nodes := ao260.nodes.push ⟨5,78,79⟩}
abbrev ao256 : Mgr := {an256 with memo := ((PCSDD.BOp.or,11,37),80)::an256.memo}
theorem a256 : ApplyCertificate 12 DEFAULT_LIMITS 20 PCSDD.BOp.or 11 37 ai256 80 ao256 := by
  exact ApplyCertificate.branch (fuel := 19) (a0 := 11) (b0 := 37) (lo := 78) (hi := 79) (r := 80) (op := PCSDD.BOp.or) (m := ai256) (m1 := ao257) (m2 := ao260) (m3 := an256) (by decide) (by rfl) (by decide) a257 a260 (by rfl)
abbrev an248 : Mgr := {ao256 with nodes := ao256.nodes.push ⟨4,77,80⟩}
abbrev ao248 : Mgr := {an248 with memo := ((PCSDD.BOp.or,11,38),81)::an248.memo}
theorem a248 : ApplyCertificate 12 DEFAULT_LIMITS 21 PCSDD.BOp.or 11 38 ai248 81 ao248 := by
  exact ApplyCertificate.branch (fuel := 20) (a0 := 11) (b0 := 38) (lo := 77) (hi := 80) (r := 81) (op := PCSDD.BOp.or) (m := ai248) (m1 := ao249) (m2 := ao256) (m3 := an248) (by decide) (by rfl) (by decide) a249 a256 (by rfl)
abbrev an234 : Mgr := {ao248 with nodes := ao248.nodes.push ⟨3,74,81⟩}
abbrev ao234 : Mgr := {an234 with memo := ((PCSDD.BOp.or,11,39),82)::an234.memo}
theorem a234 : ApplyCertificate 12 DEFAULT_LIMITS 22 PCSDD.BOp.or 11 39 ai234 82 ao234 := by
  exact ApplyCertificate.branch (fuel := 21) (a0 := 11) (b0 := 39) (lo := 74) (hi := 81) (r := 82) (op := PCSDD.BOp.or) (m := ai234) (m1 := ao235) (m2 := ao248) (m3 := an234) (by decide) (by rfl) (by decide) a235 a248 (by rfl)
abbrev an204 : Mgr := {ao234 with nodes := ao234.nodes.push ⟨2,68,82⟩}
abbrev ao204 : Mgr := {an204 with memo := ((PCSDD.BOp.or,12,39),83)::an204.memo}
theorem a204 : ApplyCertificate 12 DEFAULT_LIMITS 23 PCSDD.BOp.or 12 39 ai204 83 ao204 := by
  exact ApplyCertificate.branch (fuel := 22) (a0 := 12) (b0 := 39) (lo := 68) (hi := 82) (r := 83) (op := PCSDD.BOp.or) (m := ai204) (m1 := ao205) (m2 := ao234) (m3 := an204) (by decide) (by rfl) (by decide) a205 a234 (by rfl)
abbrev an150 : Mgr := {ao204 with nodes := ao204.nodes.push ⟨1,54,83⟩}
abbrev ao150 : Mgr := {an150 with memo := ((PCSDD.BOp.or,13,39),84)::an150.memo}
theorem a150 : ApplyCertificate 12 DEFAULT_LIMITS 24 PCSDD.BOp.or 13 39 ai150 84 ao150 := by
  exact ApplyCertificate.branch (fuel := 23) (a0 := 13) (b0 := 39) (lo := 54) (hi := 83) (r := 84) (op := PCSDD.BOp.or) (m := ai150) (m1 := ao151) (m2 := ao204) (m3 := an150) (by decide) (by rfl) (by decide) a151 a204 (by rfl)
abbrev ai263 : Mgr := ao150
abbrev ai264 : Mgr := {ai263 with ops := ai263.ops+1}
abbrev ai265 : Mgr := {ai264 with ops := ai264.ops+1}
abbrev ai266 : Mgr := {ai265 with ops := ai265.ops+1}
abbrev ai267 : Mgr := {ai266 with ops := ai266.ops+1}
abbrev ai268 : Mgr := {ai267 with ops := ai267.ops+1}
abbrev ao268 : Mgr := {ai268 with ops := ai268.ops+1}
theorem a268 : ApplyCertificate 12 DEFAULT_LIMITS 19 PCSDD.BOp.or 3 0 ai268 3 ao268 := by
  exact ApplyCertificate.hit (fuel := 18) (a0 := 3) (b0 := 0) (r := 3) (op := PCSDD.BOp.or) (m := ai268) (by decide) (by rfl)
abbrev ai269 : Mgr := ao268
abbrev ai270 : Mgr := {ai269 with ops := ai269.ops+1}
abbrev ao270 : Mgr := {ai270 with ops := ai270.ops+1}
theorem a270 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.or 0 28 ai270 28 ao270 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 0) (b0 := 28) (r := 28) (op := PCSDD.BOp.or) (m := ai270) (by decide) (by rfl)
abbrev ai271 : Mgr := ao270
abbrev ao271 : Mgr := {ai271 with ops := ai271.ops+1}
theorem a271 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.or 1 28 ai271 1 ao271 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 1) (b0 := 28) (r := 1) (op := PCSDD.BOp.or) (m := ai271) (by decide) (by rfl)
abbrev an269 : Mgr := {ao271 with nodes := ao271.nodes.push ⟨6,28,1⟩}
abbrev ao269 : Mgr := {an269 with memo := ((PCSDD.BOp.or,3,28),85)::an269.memo}
theorem a269 : ApplyCertificate 12 DEFAULT_LIMITS 19 PCSDD.BOp.or 3 28 ai269 85 ao269 := by
  exact ApplyCertificate.branch (fuel := 18) (a0 := 3) (b0 := 28) (lo := 28) (hi := 1) (r := 85) (op := PCSDD.BOp.or) (m := ai269) (m1 := ao270) (m2 := ao271) (m3 := an269) (by decide) (by rfl) (by decide) a270 a271 (by rfl)
abbrev an267 : Mgr := {ao269 with nodes := ao269.nodes.push ⟨5,3,85⟩}
abbrev ao267 : Mgr := {an267 with memo := ((PCSDD.BOp.or,3,29),86)::an267.memo}
theorem a267 : ApplyCertificate 12 DEFAULT_LIMITS 20 PCSDD.BOp.or 3 29 ai267 86 ao267 := by
  exact ApplyCertificate.branch (fuel := 19) (a0 := 3) (b0 := 29) (lo := 3) (hi := 85) (r := 86) (op := PCSDD.BOp.or) (m := ai267) (m1 := ao268) (m2 := ao269) (m3 := an267) (by decide) (by rfl) (by decide) a268 a269 (by rfl)
abbrev ai272 : Mgr := ao267
abbrev ai273 : Mgr := {ai272 with ops := ai272.ops+1}
abbrev ai274 : Mgr := {ai273 with ops := ai273.ops+1}
abbrev ao274 : Mgr := {ai274 with ops := ai274.ops+1}
theorem a274 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.or 0 25 ai274 25 ao274 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 0) (b0 := 25) (r := 25) (op := PCSDD.BOp.or) (m := ai274) (by decide) (by rfl)
abbrev ai275 : Mgr := ao274
abbrev ao275 : Mgr := {ai275 with ops := ai275.ops+1}
theorem a275 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.or 1 25 ai275 1 ao275 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 1) (b0 := 25) (r := 1) (op := PCSDD.BOp.or) (m := ai275) (by decide) (by rfl)
abbrev an273 : Mgr := {ao275 with nodes := ao275.nodes.push ⟨6,25,1⟩}
abbrev ao273 : Mgr := {an273 with memo := ((PCSDD.BOp.or,3,25),87)::an273.memo}
theorem a273 : ApplyCertificate 12 DEFAULT_LIMITS 19 PCSDD.BOp.or 3 25 ai273 87 ao273 := by
  exact ApplyCertificate.branch (fuel := 18) (a0 := 3) (b0 := 25) (lo := 25) (hi := 1) (r := 87) (op := PCSDD.BOp.or) (m := ai273) (m1 := ao274) (m2 := ao275) (m3 := an273) (by decide) (by rfl) (by decide) a274 a275 (by rfl)
abbrev ai276 : Mgr := ao273
abbrev ai277 : Mgr := {ai276 with ops := ai276.ops+1}
abbrev ao277 : Mgr := {ai277 with ops := ai277.ops+1}
theorem a277 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.or 0 30 ai277 30 ao277 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 0) (b0 := 30) (r := 30) (op := PCSDD.BOp.or) (m := ai277) (by decide) (by rfl)
abbrev ai278 : Mgr := ao277
abbrev ao278 : Mgr := {ai278 with ops := ai278.ops+1}
theorem a278 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.or 1 30 ai278 1 ao278 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 1) (b0 := 30) (r := 1) (op := PCSDD.BOp.or) (m := ai278) (by decide) (by rfl)
abbrev an276 : Mgr := {ao278 with nodes := ao278.nodes.push ⟨6,30,1⟩}
abbrev ao276 : Mgr := {an276 with memo := ((PCSDD.BOp.or,3,30),88)::an276.memo}
theorem a276 : ApplyCertificate 12 DEFAULT_LIMITS 19 PCSDD.BOp.or 3 30 ai276 88 ao276 := by
  exact ApplyCertificate.branch (fuel := 18) (a0 := 3) (b0 := 30) (lo := 30) (hi := 1) (r := 88) (op := PCSDD.BOp.or) (m := ai276) (m1 := ao277) (m2 := ao278) (m3 := an276) (by decide) (by rfl) (by decide) a277 a278 (by rfl)
abbrev an272 : Mgr := {ao276 with nodes := ao276.nodes.push ⟨5,87,88⟩}
abbrev ao272 : Mgr := {an272 with memo := ((PCSDD.BOp.or,3,31),89)::an272.memo}
theorem a272 : ApplyCertificate 12 DEFAULT_LIMITS 20 PCSDD.BOp.or 3 31 ai272 89 ao272 := by
  exact ApplyCertificate.branch (fuel := 19) (a0 := 3) (b0 := 31) (lo := 87) (hi := 88) (r := 89) (op := PCSDD.BOp.or) (m := ai272) (m1 := ao273) (m2 := ao276) (m3 := an272) (by decide) (by rfl) (by decide) a273 a276 (by rfl)
abbrev an266 : Mgr := {ao272 with nodes := ao272.nodes.push ⟨4,86,89⟩}
abbrev ao266 : Mgr := {an266 with memo := ((PCSDD.BOp.or,3,32),90)::an266.memo}
theorem a266 : ApplyCertificate 12 DEFAULT_LIMITS 21 PCSDD.BOp.or 3 32 ai266 90 ao266 := by
  exact ApplyCertificate.branch (fuel := 20) (a0 := 3) (b0 := 32) (lo := 86) (hi := 89) (r := 90) (op := PCSDD.BOp.or) (m := ai266) (m1 := ao267) (m2 := ao272) (m3 := an266) (by decide) (by rfl) (by decide) a267 a272 (by rfl)
abbrev ai279 : Mgr := ao266
abbrev ai280 : Mgr := {ai279 with ops := ai279.ops+1}
abbrev ai281 : Mgr := {ai280 with ops := ai280.ops+1}
abbrev ai282 : Mgr := {ai281 with ops := ai281.ops+1}
abbrev ao282 : Mgr := {ai282 with ops := ai282.ops+1}
theorem a282 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.or 0 22 ai282 22 ao282 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 0) (b0 := 22) (r := 22) (op := PCSDD.BOp.or) (m := ai282) (by decide) (by rfl)
abbrev ai283 : Mgr := ao282
abbrev ao283 : Mgr := {ai283 with ops := ai283.ops+1}
theorem a283 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.or 1 22 ai283 1 ao283 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 1) (b0 := 22) (r := 1) (op := PCSDD.BOp.or) (m := ai283) (by decide) (by rfl)
abbrev an281 : Mgr := {ao283 with nodes := ao283.nodes.push ⟨6,22,1⟩}
abbrev ao281 : Mgr := {an281 with memo := ((PCSDD.BOp.or,3,22),91)::an281.memo}
theorem a281 : ApplyCertificate 12 DEFAULT_LIMITS 19 PCSDD.BOp.or 3 22 ai281 91 ao281 := by
  exact ApplyCertificate.branch (fuel := 18) (a0 := 3) (b0 := 22) (lo := 22) (hi := 1) (r := 91) (op := PCSDD.BOp.or) (m := ai281) (m1 := ao282) (m2 := ao283) (m3 := an281) (by decide) (by rfl) (by decide) a282 a283 (by rfl)
abbrev ai284 : Mgr := ao281
abbrev ai285 : Mgr := {ai284 with ops := ai284.ops+1}
abbrev ao285 : Mgr := {ai285 with ops := ai285.ops+1}
theorem a285 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.or 0 33 ai285 33 ao285 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 0) (b0 := 33) (r := 33) (op := PCSDD.BOp.or) (m := ai285) (by decide) (by rfl)
abbrev ai286 : Mgr := ao285
abbrev ao286 : Mgr := {ai286 with ops := ai286.ops+1}
theorem a286 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.or 1 33 ai286 1 ao286 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 1) (b0 := 33) (r := 1) (op := PCSDD.BOp.or) (m := ai286) (by decide) (by rfl)
abbrev an284 : Mgr := {ao286 with nodes := ao286.nodes.push ⟨6,33,1⟩}
abbrev ao284 : Mgr := {an284 with memo := ((PCSDD.BOp.or,3,33),92)::an284.memo}
theorem a284 : ApplyCertificate 12 DEFAULT_LIMITS 19 PCSDD.BOp.or 3 33 ai284 92 ao284 := by
  exact ApplyCertificate.branch (fuel := 18) (a0 := 3) (b0 := 33) (lo := 33) (hi := 1) (r := 92) (op := PCSDD.BOp.or) (m := ai284) (m1 := ao285) (m2 := ao286) (m3 := an284) (by decide) (by rfl) (by decide) a285 a286 (by rfl)
abbrev an280 : Mgr := {ao284 with nodes := ao284.nodes.push ⟨5,91,92⟩}
abbrev ao280 : Mgr := {an280 with memo := ((PCSDD.BOp.or,3,34),93)::an280.memo}
theorem a280 : ApplyCertificate 12 DEFAULT_LIMITS 20 PCSDD.BOp.or 3 34 ai280 93 ao280 := by
  exact ApplyCertificate.branch (fuel := 19) (a0 := 3) (b0 := 34) (lo := 91) (hi := 92) (r := 93) (op := PCSDD.BOp.or) (m := ai280) (m1 := ao281) (m2 := ao284) (m3 := an280) (by decide) (by rfl) (by decide) a281 a284 (by rfl)
abbrev ai287 : Mgr := ao280
abbrev ai288 : Mgr := {ai287 with ops := ai287.ops+1}
abbrev ai289 : Mgr := {ai288 with ops := ai288.ops+1}
abbrev ao289 : Mgr := {ai289 with ops := ai289.ops+1}
theorem a289 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.or 0 35 ai289 35 ao289 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 0) (b0 := 35) (r := 35) (op := PCSDD.BOp.or) (m := ai289) (by decide) (by rfl)
abbrev ai290 : Mgr := ao289
abbrev ao290 : Mgr := {ai290 with ops := ai290.ops+1}
theorem a290 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.or 1 35 ai290 1 ao290 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 1) (b0 := 35) (r := 1) (op := PCSDD.BOp.or) (m := ai290) (by decide) (by rfl)
abbrev an288 : Mgr := {ao290 with nodes := ao290.nodes.push ⟨6,35,1⟩}
abbrev ao288 : Mgr := {an288 with memo := ((PCSDD.BOp.or,3,35),94)::an288.memo}
theorem a288 : ApplyCertificate 12 DEFAULT_LIMITS 19 PCSDD.BOp.or 3 35 ai288 94 ao288 := by
  exact ApplyCertificate.branch (fuel := 18) (a0 := 3) (b0 := 35) (lo := 35) (hi := 1) (r := 94) (op := PCSDD.BOp.or) (m := ai288) (m1 := ao289) (m2 := ao290) (m3 := an288) (by decide) (by rfl) (by decide) a289 a290 (by rfl)
abbrev ai291 : Mgr := ao288
abbrev ai292 : Mgr := {ai291 with ops := ai291.ops+1}
abbrev ao292 : Mgr := {ai292 with ops := ai292.ops+1}
theorem a292 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.or 0 36 ai292 36 ao292 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 0) (b0 := 36) (r := 36) (op := PCSDD.BOp.or) (m := ai292) (by decide) (by rfl)
abbrev ai293 : Mgr := ao292
abbrev ao293 : Mgr := {ai293 with ops := ai293.ops+1}
theorem a293 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.or 1 36 ai293 1 ao293 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 1) (b0 := 36) (r := 1) (op := PCSDD.BOp.or) (m := ai293) (by decide) (by rfl)
abbrev an291 : Mgr := {ao293 with nodes := ao293.nodes.push ⟨6,36,1⟩}
abbrev ao291 : Mgr := {an291 with memo := ((PCSDD.BOp.or,3,36),95)::an291.memo}
theorem a291 : ApplyCertificate 12 DEFAULT_LIMITS 19 PCSDD.BOp.or 3 36 ai291 95 ao291 := by
  exact ApplyCertificate.branch (fuel := 18) (a0 := 3) (b0 := 36) (lo := 36) (hi := 1) (r := 95) (op := PCSDD.BOp.or) (m := ai291) (m1 := ao292) (m2 := ao293) (m3 := an291) (by decide) (by rfl) (by decide) a292 a293 (by rfl)
abbrev an287 : Mgr := {ao291 with nodes := ao291.nodes.push ⟨5,94,95⟩}
abbrev ao287 : Mgr := {an287 with memo := ((PCSDD.BOp.or,3,37),96)::an287.memo}
theorem a287 : ApplyCertificate 12 DEFAULT_LIMITS 20 PCSDD.BOp.or 3 37 ai287 96 ao287 := by
  exact ApplyCertificate.branch (fuel := 19) (a0 := 3) (b0 := 37) (lo := 94) (hi := 95) (r := 96) (op := PCSDD.BOp.or) (m := ai287) (m1 := ao288) (m2 := ao291) (m3 := an287) (by decide) (by rfl) (by decide) a288 a291 (by rfl)
abbrev an279 : Mgr := {ao287 with nodes := ao287.nodes.push ⟨4,93,96⟩}
abbrev ao279 : Mgr := {an279 with memo := ((PCSDD.BOp.or,3,38),97)::an279.memo}
theorem a279 : ApplyCertificate 12 DEFAULT_LIMITS 21 PCSDD.BOp.or 3 38 ai279 97 ao279 := by
  exact ApplyCertificate.branch (fuel := 20) (a0 := 3) (b0 := 38) (lo := 93) (hi := 96) (r := 97) (op := PCSDD.BOp.or) (m := ai279) (m1 := ao280) (m2 := ao287) (m3 := an279) (by decide) (by rfl) (by decide) a280 a287 (by rfl)
abbrev an265 : Mgr := {ao279 with nodes := ao279.nodes.push ⟨3,90,97⟩}
abbrev ao265 : Mgr := {an265 with memo := ((PCSDD.BOp.or,3,39),98)::an265.memo}
theorem a265 : ApplyCertificate 12 DEFAULT_LIMITS 22 PCSDD.BOp.or 3 39 ai265 98 ao265 := by
  exact ApplyCertificate.branch (fuel := 21) (a0 := 3) (b0 := 39) (lo := 90) (hi := 97) (r := 98) (op := PCSDD.BOp.or) (m := ai265) (m1 := ao266) (m2 := ao279) (m3 := an265) (by decide) (by rfl) (by decide) a266 a279 (by rfl)
abbrev ai294 : Mgr := ao265
abbrev ai295 : Mgr := {ai294 with ops := ai294.ops+1}
abbrev ai296 : Mgr := {ai295 with ops := ai295.ops+1}
abbrev ai297 : Mgr := {ai296 with ops := ai296.ops+1}
abbrev ai298 : Mgr := {ai297 with ops := ai297.ops+1}
abbrev ao298 : Mgr := {ai298 with ops := ai298.ops+1}
theorem a298 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.or 0 9 ai298 9 ao298 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 0) (b0 := 9) (r := 9) (op := PCSDD.BOp.or) (m := ai298) (by decide) (by rfl)
abbrev ai299 : Mgr := ao298
abbrev ao299 : Mgr := {ai299 with ops := ai299.ops+1}
theorem a299 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.or 0 1 ai299 1 ao299 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 0) (b0 := 1) (r := 1) (op := PCSDD.BOp.or) (m := ai299) (by decide) (by rfl)
abbrev an297 : Mgr := ao299
abbrev ao297 : Mgr := {an297 with memo := ((PCSDD.BOp.or,0,14),14)::an297.memo}
theorem a297 : ApplyCertificate 12 DEFAULT_LIMITS 19 PCSDD.BOp.or 14 0 ai297 14 ao297 := by
  exact ApplyCertificate.branch (fuel := 18) (a0 := 14) (b0 := 0) (lo := 9) (hi := 1) (r := 14) (op := PCSDD.BOp.or) (m := ai297) (m1 := ao298) (m2 := ao299) (m3 := an297) (by decide) (by rfl) (by decide) a298 a299 (by rfl)
abbrev ai300 : Mgr := ao297
abbrev ai301 : Mgr := {ai300 with ops := ai300.ops+1}
abbrev ao301 : Mgr := {ai301 with ops := ai301.ops+1}
theorem a301 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.or 9 28 ai301 40 ao301 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 9) (b0 := 28) (r := 40) (op := PCSDD.BOp.or) (m := ai301) (by decide) (by rfl)
abbrev ai302 : Mgr := ao301
abbrev ao302 : Mgr := {ai302 with ops := ai302.ops+1}
theorem a302 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.or 1 28 ai302 1 ao302 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 1) (b0 := 28) (r := 1) (op := PCSDD.BOp.or) (m := ai302) (by decide) (by rfl)
abbrev an300 : Mgr := {ao302 with nodes := ao302.nodes.push ⟨6,40,1⟩}
abbrev ao300 : Mgr := {an300 with memo := ((PCSDD.BOp.or,14,28),99)::an300.memo}
theorem a300 : ApplyCertificate 12 DEFAULT_LIMITS 19 PCSDD.BOp.or 14 28 ai300 99 ao300 := by
  exact ApplyCertificate.branch (fuel := 18) (a0 := 14) (b0 := 28) (lo := 40) (hi := 1) (r := 99) (op := PCSDD.BOp.or) (m := ai300) (m1 := ao301) (m2 := ao302) (m3 := an300) (by decide) (by rfl) (by decide) a301 a302 (by rfl)
abbrev an296 : Mgr := {ao300 with nodes := ao300.nodes.push ⟨5,14,99⟩}
abbrev ao296 : Mgr := {an296 with memo := ((PCSDD.BOp.or,14,29),100)::an296.memo}
theorem a296 : ApplyCertificate 12 DEFAULT_LIMITS 20 PCSDD.BOp.or 14 29 ai296 100 ao296 := by
  exact ApplyCertificate.branch (fuel := 19) (a0 := 14) (b0 := 29) (lo := 14) (hi := 99) (r := 100) (op := PCSDD.BOp.or) (m := ai296) (m1 := ao297) (m2 := ao300) (m3 := an296) (by decide) (by rfl) (by decide) a297 a300 (by rfl)
abbrev ai303 : Mgr := ao296
abbrev ai304 : Mgr := {ai303 with ops := ai303.ops+1}
abbrev ai305 : Mgr := {ai304 with ops := ai304.ops+1}
abbrev ao305 : Mgr := {ai305 with ops := ai305.ops+1}
theorem a305 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.or 9 25 ai305 42 ao305 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 9) (b0 := 25) (r := 42) (op := PCSDD.BOp.or) (m := ai305) (by decide) (by rfl)
abbrev ai306 : Mgr := ao305
abbrev ao306 : Mgr := {ai306 with ops := ai306.ops+1}
theorem a306 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.or 1 25 ai306 1 ao306 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 1) (b0 := 25) (r := 1) (op := PCSDD.BOp.or) (m := ai306) (by decide) (by rfl)
abbrev an304 : Mgr := {ao306 with nodes := ao306.nodes.push ⟨6,42,1⟩}
abbrev ao304 : Mgr := {an304 with memo := ((PCSDD.BOp.or,14,25),101)::an304.memo}
theorem a304 : ApplyCertificate 12 DEFAULT_LIMITS 19 PCSDD.BOp.or 14 25 ai304 101 ao304 := by
  exact ApplyCertificate.branch (fuel := 18) (a0 := 14) (b0 := 25) (lo := 42) (hi := 1) (r := 101) (op := PCSDD.BOp.or) (m := ai304) (m1 := ao305) (m2 := ao306) (m3 := an304) (by decide) (by rfl) (by decide) a305 a306 (by rfl)
abbrev ai307 : Mgr := ao304
abbrev ai308 : Mgr := {ai307 with ops := ai307.ops+1}
abbrev ao308 : Mgr := {ai308 with ops := ai308.ops+1}
theorem a308 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.or 9 30 ai308 43 ao308 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 9) (b0 := 30) (r := 43) (op := PCSDD.BOp.or) (m := ai308) (by decide) (by rfl)
abbrev ai309 : Mgr := ao308
abbrev ao309 : Mgr := {ai309 with ops := ai309.ops+1}
theorem a309 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.or 1 30 ai309 1 ao309 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 1) (b0 := 30) (r := 1) (op := PCSDD.BOp.or) (m := ai309) (by decide) (by rfl)
abbrev an307 : Mgr := {ao309 with nodes := ao309.nodes.push ⟨6,43,1⟩}
abbrev ao307 : Mgr := {an307 with memo := ((PCSDD.BOp.or,14,30),102)::an307.memo}
theorem a307 : ApplyCertificate 12 DEFAULT_LIMITS 19 PCSDD.BOp.or 14 30 ai307 102 ao307 := by
  exact ApplyCertificate.branch (fuel := 18) (a0 := 14) (b0 := 30) (lo := 43) (hi := 1) (r := 102) (op := PCSDD.BOp.or) (m := ai307) (m1 := ao308) (m2 := ao309) (m3 := an307) (by decide) (by rfl) (by decide) a308 a309 (by rfl)
abbrev an303 : Mgr := {ao307 with nodes := ao307.nodes.push ⟨5,101,102⟩}
abbrev ao303 : Mgr := {an303 with memo := ((PCSDD.BOp.or,14,31),103)::an303.memo}
theorem a303 : ApplyCertificate 12 DEFAULT_LIMITS 20 PCSDD.BOp.or 14 31 ai303 103 ao303 := by
  exact ApplyCertificate.branch (fuel := 19) (a0 := 14) (b0 := 31) (lo := 101) (hi := 102) (r := 103) (op := PCSDD.BOp.or) (m := ai303) (m1 := ao304) (m2 := ao307) (m3 := an303) (by decide) (by rfl) (by decide) a304 a307 (by rfl)
abbrev an295 : Mgr := {ao303 with nodes := ao303.nodes.push ⟨4,100,103⟩}
abbrev ao295 : Mgr := {an295 with memo := ((PCSDD.BOp.or,14,32),104)::an295.memo}
theorem a295 : ApplyCertificate 12 DEFAULT_LIMITS 21 PCSDD.BOp.or 14 32 ai295 104 ao295 := by
  exact ApplyCertificate.branch (fuel := 20) (a0 := 14) (b0 := 32) (lo := 100) (hi := 103) (r := 104) (op := PCSDD.BOp.or) (m := ai295) (m1 := ao296) (m2 := ao303) (m3 := an295) (by decide) (by rfl) (by decide) a296 a303 (by rfl)
abbrev ai310 : Mgr := ao295
abbrev ai311 : Mgr := {ai310 with ops := ai310.ops+1}
abbrev ai312 : Mgr := {ai311 with ops := ai311.ops+1}
abbrev ai313 : Mgr := {ai312 with ops := ai312.ops+1}
abbrev ao313 : Mgr := {ai313 with ops := ai313.ops+1}
theorem a313 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.or 9 22 ai313 46 ao313 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 9) (b0 := 22) (r := 46) (op := PCSDD.BOp.or) (m := ai313) (by decide) (by rfl)
abbrev ai314 : Mgr := ao313
abbrev ao314 : Mgr := {ai314 with ops := ai314.ops+1}
theorem a314 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.or 1 22 ai314 1 ao314 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 1) (b0 := 22) (r := 1) (op := PCSDD.BOp.or) (m := ai314) (by decide) (by rfl)
abbrev an312 : Mgr := {ao314 with nodes := ao314.nodes.push ⟨6,46,1⟩}
abbrev ao312 : Mgr := {an312 with memo := ((PCSDD.BOp.or,14,22),105)::an312.memo}
theorem a312 : ApplyCertificate 12 DEFAULT_LIMITS 19 PCSDD.BOp.or 14 22 ai312 105 ao312 := by
  exact ApplyCertificate.branch (fuel := 18) (a0 := 14) (b0 := 22) (lo := 46) (hi := 1) (r := 105) (op := PCSDD.BOp.or) (m := ai312) (m1 := ao313) (m2 := ao314) (m3 := an312) (by decide) (by rfl) (by decide) a313 a314 (by rfl)
abbrev ai315 : Mgr := ao312
abbrev ai316 : Mgr := {ai315 with ops := ai315.ops+1}
abbrev ao316 : Mgr := {ai316 with ops := ai316.ops+1}
theorem a316 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.or 9 33 ai316 47 ao316 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 9) (b0 := 33) (r := 47) (op := PCSDD.BOp.or) (m := ai316) (by decide) (by rfl)
abbrev ai317 : Mgr := ao316
abbrev ao317 : Mgr := {ai317 with ops := ai317.ops+1}
theorem a317 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.or 1 33 ai317 1 ao317 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 1) (b0 := 33) (r := 1) (op := PCSDD.BOp.or) (m := ai317) (by decide) (by rfl)
abbrev an315 : Mgr := {ao317 with nodes := ao317.nodes.push ⟨6,47,1⟩}
abbrev ao315 : Mgr := {an315 with memo := ((PCSDD.BOp.or,14,33),106)::an315.memo}
theorem a315 : ApplyCertificate 12 DEFAULT_LIMITS 19 PCSDD.BOp.or 14 33 ai315 106 ao315 := by
  exact ApplyCertificate.branch (fuel := 18) (a0 := 14) (b0 := 33) (lo := 47) (hi := 1) (r := 106) (op := PCSDD.BOp.or) (m := ai315) (m1 := ao316) (m2 := ao317) (m3 := an315) (by decide) (by rfl) (by decide) a316 a317 (by rfl)
abbrev an311 : Mgr := {ao315 with nodes := ao315.nodes.push ⟨5,105,106⟩}
abbrev ao311 : Mgr := {an311 with memo := ((PCSDD.BOp.or,14,34),107)::an311.memo}
theorem a311 : ApplyCertificate 12 DEFAULT_LIMITS 20 PCSDD.BOp.or 14 34 ai311 107 ao311 := by
  exact ApplyCertificate.branch (fuel := 19) (a0 := 14) (b0 := 34) (lo := 105) (hi := 106) (r := 107) (op := PCSDD.BOp.or) (m := ai311) (m1 := ao312) (m2 := ao315) (m3 := an311) (by decide) (by rfl) (by decide) a312 a315 (by rfl)
abbrev ai318 : Mgr := ao311
abbrev ai319 : Mgr := {ai318 with ops := ai318.ops+1}
abbrev ai320 : Mgr := {ai319 with ops := ai319.ops+1}
abbrev ao320 : Mgr := {ai320 with ops := ai320.ops+1}
theorem a320 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.or 9 35 ai320 49 ao320 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 9) (b0 := 35) (r := 49) (op := PCSDD.BOp.or) (m := ai320) (by decide) (by rfl)
abbrev ai321 : Mgr := ao320
abbrev ao321 : Mgr := {ai321 with ops := ai321.ops+1}
theorem a321 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.or 1 35 ai321 1 ao321 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 1) (b0 := 35) (r := 1) (op := PCSDD.BOp.or) (m := ai321) (by decide) (by rfl)
abbrev an319 : Mgr := {ao321 with nodes := ao321.nodes.push ⟨6,49,1⟩}
abbrev ao319 : Mgr := {an319 with memo := ((PCSDD.BOp.or,14,35),108)::an319.memo}
theorem a319 : ApplyCertificate 12 DEFAULT_LIMITS 19 PCSDD.BOp.or 14 35 ai319 108 ao319 := by
  exact ApplyCertificate.branch (fuel := 18) (a0 := 14) (b0 := 35) (lo := 49) (hi := 1) (r := 108) (op := PCSDD.BOp.or) (m := ai319) (m1 := ao320) (m2 := ao321) (m3 := an319) (by decide) (by rfl) (by decide) a320 a321 (by rfl)
abbrev ai322 : Mgr := ao319
abbrev ai323 : Mgr := {ai322 with ops := ai322.ops+1}
abbrev ao323 : Mgr := {ai323 with ops := ai323.ops+1}
theorem a323 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.or 9 36 ai323 50 ao323 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 9) (b0 := 36) (r := 50) (op := PCSDD.BOp.or) (m := ai323) (by decide) (by rfl)
abbrev ai324 : Mgr := ao323
abbrev ao324 : Mgr := {ai324 with ops := ai324.ops+1}
theorem a324 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.or 1 36 ai324 1 ao324 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 1) (b0 := 36) (r := 1) (op := PCSDD.BOp.or) (m := ai324) (by decide) (by rfl)
abbrev an322 : Mgr := {ao324 with nodes := ao324.nodes.push ⟨6,50,1⟩}
abbrev ao322 : Mgr := {an322 with memo := ((PCSDD.BOp.or,14,36),109)::an322.memo}
theorem a322 : ApplyCertificate 12 DEFAULT_LIMITS 19 PCSDD.BOp.or 14 36 ai322 109 ao322 := by
  exact ApplyCertificate.branch (fuel := 18) (a0 := 14) (b0 := 36) (lo := 50) (hi := 1) (r := 109) (op := PCSDD.BOp.or) (m := ai322) (m1 := ao323) (m2 := ao324) (m3 := an322) (by decide) (by rfl) (by decide) a323 a324 (by rfl)
abbrev an318 : Mgr := {ao322 with nodes := ao322.nodes.push ⟨5,108,109⟩}
abbrev ao318 : Mgr := {an318 with memo := ((PCSDD.BOp.or,14,37),110)::an318.memo}
theorem a318 : ApplyCertificate 12 DEFAULT_LIMITS 20 PCSDD.BOp.or 14 37 ai318 110 ao318 := by
  exact ApplyCertificate.branch (fuel := 19) (a0 := 14) (b0 := 37) (lo := 108) (hi := 109) (r := 110) (op := PCSDD.BOp.or) (m := ai318) (m1 := ao319) (m2 := ao322) (m3 := an318) (by decide) (by rfl) (by decide) a319 a322 (by rfl)
abbrev an310 : Mgr := {ao318 with nodes := ao318.nodes.push ⟨4,107,110⟩}
abbrev ao310 : Mgr := {an310 with memo := ((PCSDD.BOp.or,14,38),111)::an310.memo}
theorem a310 : ApplyCertificate 12 DEFAULT_LIMITS 21 PCSDD.BOp.or 14 38 ai310 111 ao310 := by
  exact ApplyCertificate.branch (fuel := 20) (a0 := 14) (b0 := 38) (lo := 107) (hi := 110) (r := 111) (op := PCSDD.BOp.or) (m := ai310) (m1 := ao311) (m2 := ao318) (m3 := an310) (by decide) (by rfl) (by decide) a311 a318 (by rfl)
abbrev an294 : Mgr := {ao310 with nodes := ao310.nodes.push ⟨3,104,111⟩}
abbrev ao294 : Mgr := {an294 with memo := ((PCSDD.BOp.or,14,39),112)::an294.memo}
theorem a294 : ApplyCertificate 12 DEFAULT_LIMITS 22 PCSDD.BOp.or 14 39 ai294 112 ao294 := by
  exact ApplyCertificate.branch (fuel := 21) (a0 := 14) (b0 := 39) (lo := 104) (hi := 111) (r := 112) (op := PCSDD.BOp.or) (m := ai294) (m1 := ao295) (m2 := ao310) (m3 := an294) (by decide) (by rfl) (by decide) a295 a310 (by rfl)
abbrev an264 : Mgr := {ao294 with nodes := ao294.nodes.push ⟨2,98,112⟩}
abbrev ao264 : Mgr := {an264 with memo := ((PCSDD.BOp.or,15,39),113)::an264.memo}
theorem a264 : ApplyCertificate 12 DEFAULT_LIMITS 23 PCSDD.BOp.or 15 39 ai264 113 ao264 := by
  exact ApplyCertificate.branch (fuel := 22) (a0 := 15) (b0 := 39) (lo := 98) (hi := 112) (r := 113) (op := PCSDD.BOp.or) (m := ai264) (m1 := ao265) (m2 := ao294) (m3 := an264) (by decide) (by rfl) (by decide) a265 a294 (by rfl)
abbrev ai325 : Mgr := ao264
abbrev ai326 : Mgr := {ai325 with ops := ai325.ops+1}
abbrev ai327 : Mgr := {ai326 with ops := ai326.ops+1}
abbrev ai328 : Mgr := {ai327 with ops := ai327.ops+1}
abbrev ai329 : Mgr := {ai328 with ops := ai328.ops+1}
abbrev ai330 : Mgr := {ai329 with ops := ai329.ops+1}
abbrev ao330 : Mgr := {ai330 with ops := ai330.ops+1}
theorem a330 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.or 0 6 ai330 6 ao330 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 0) (b0 := 6) (r := 6) (op := PCSDD.BOp.or) (m := ai330) (by decide) (by rfl)
abbrev ai331 : Mgr := ao330
abbrev ao331 : Mgr := {ai331 with ops := ai331.ops+1}
theorem a331 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.or 0 1 ai331 1 ao331 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 0) (b0 := 1) (r := 1) (op := PCSDD.BOp.or) (m := ai331) (by decide) (by rfl)
abbrev an329 : Mgr := ao331
abbrev ao329 : Mgr := {an329 with memo := ((PCSDD.BOp.or,0,16),16)::an329.memo}
theorem a329 : ApplyCertificate 12 DEFAULT_LIMITS 19 PCSDD.BOp.or 16 0 ai329 16 ao329 := by
  exact ApplyCertificate.branch (fuel := 18) (a0 := 16) (b0 := 0) (lo := 6) (hi := 1) (r := 16) (op := PCSDD.BOp.or) (m := ai329) (m1 := ao330) (m2 := ao331) (m3 := an329) (by decide) (by rfl) (by decide) a330 a331 (by rfl)
abbrev ai332 : Mgr := ao329
abbrev ai333 : Mgr := {ai332 with ops := ai332.ops+1}
abbrev ao333 : Mgr := {ai333 with ops := ai333.ops+1}
theorem a333 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.or 6 28 ai333 55 ao333 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 6) (b0 := 28) (r := 55) (op := PCSDD.BOp.or) (m := ai333) (by decide) (by rfl)
abbrev ai334 : Mgr := ao333
abbrev ao334 : Mgr := {ai334 with ops := ai334.ops+1}
theorem a334 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.or 1 28 ai334 1 ao334 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 1) (b0 := 28) (r := 1) (op := PCSDD.BOp.or) (m := ai334) (by decide) (by rfl)
abbrev an332 : Mgr := {ao334 with nodes := ao334.nodes.push ⟨6,55,1⟩}
abbrev ao332 : Mgr := {an332 with memo := ((PCSDD.BOp.or,16,28),114)::an332.memo}
theorem a332 : ApplyCertificate 12 DEFAULT_LIMITS 19 PCSDD.BOp.or 16 28 ai332 114 ao332 := by
  exact ApplyCertificate.branch (fuel := 18) (a0 := 16) (b0 := 28) (lo := 55) (hi := 1) (r := 114) (op := PCSDD.BOp.or) (m := ai332) (m1 := ao333) (m2 := ao334) (m3 := an332) (by decide) (by rfl) (by decide) a333 a334 (by rfl)
abbrev an328 : Mgr := {ao332 with nodes := ao332.nodes.push ⟨5,16,114⟩}
abbrev ao328 : Mgr := {an328 with memo := ((PCSDD.BOp.or,16,29),115)::an328.memo}
theorem a328 : ApplyCertificate 12 DEFAULT_LIMITS 20 PCSDD.BOp.or 16 29 ai328 115 ao328 := by
  exact ApplyCertificate.branch (fuel := 19) (a0 := 16) (b0 := 29) (lo := 16) (hi := 114) (r := 115) (op := PCSDD.BOp.or) (m := ai328) (m1 := ao329) (m2 := ao332) (m3 := an328) (by decide) (by rfl) (by decide) a329 a332 (by rfl)
abbrev ai335 : Mgr := ao328
abbrev ai336 : Mgr := {ai335 with ops := ai335.ops+1}
abbrev ai337 : Mgr := {ai336 with ops := ai336.ops+1}
abbrev ao337 : Mgr := {ai337 with ops := ai337.ops+1}
theorem a337 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.or 6 25 ai337 57 ao337 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 6) (b0 := 25) (r := 57) (op := PCSDD.BOp.or) (m := ai337) (by decide) (by rfl)
abbrev ai338 : Mgr := ao337
abbrev ao338 : Mgr := {ai338 with ops := ai338.ops+1}
theorem a338 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.or 1 25 ai338 1 ao338 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 1) (b0 := 25) (r := 1) (op := PCSDD.BOp.or) (m := ai338) (by decide) (by rfl)
abbrev an336 : Mgr := {ao338 with nodes := ao338.nodes.push ⟨6,57,1⟩}
abbrev ao336 : Mgr := {an336 with memo := ((PCSDD.BOp.or,16,25),116)::an336.memo}
theorem a336 : ApplyCertificate 12 DEFAULT_LIMITS 19 PCSDD.BOp.or 16 25 ai336 116 ao336 := by
  exact ApplyCertificate.branch (fuel := 18) (a0 := 16) (b0 := 25) (lo := 57) (hi := 1) (r := 116) (op := PCSDD.BOp.or) (m := ai336) (m1 := ao337) (m2 := ao338) (m3 := an336) (by decide) (by rfl) (by decide) a337 a338 (by rfl)
abbrev ai339 : Mgr := ao336
abbrev ai340 : Mgr := {ai339 with ops := ai339.ops+1}
abbrev ao340 : Mgr := {ai340 with ops := ai340.ops+1}
theorem a340 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.or 6 30 ai340 58 ao340 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 6) (b0 := 30) (r := 58) (op := PCSDD.BOp.or) (m := ai340) (by decide) (by rfl)
abbrev ai341 : Mgr := ao340
abbrev ao341 : Mgr := {ai341 with ops := ai341.ops+1}
theorem a341 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.or 1 30 ai341 1 ao341 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 1) (b0 := 30) (r := 1) (op := PCSDD.BOp.or) (m := ai341) (by decide) (by rfl)
abbrev an339 : Mgr := {ao341 with nodes := ao341.nodes.push ⟨6,58,1⟩}
abbrev ao339 : Mgr := {an339 with memo := ((PCSDD.BOp.or,16,30),117)::an339.memo}
theorem a339 : ApplyCertificate 12 DEFAULT_LIMITS 19 PCSDD.BOp.or 16 30 ai339 117 ao339 := by
  exact ApplyCertificate.branch (fuel := 18) (a0 := 16) (b0 := 30) (lo := 58) (hi := 1) (r := 117) (op := PCSDD.BOp.or) (m := ai339) (m1 := ao340) (m2 := ao341) (m3 := an339) (by decide) (by rfl) (by decide) a340 a341 (by rfl)
abbrev an335 : Mgr := {ao339 with nodes := ao339.nodes.push ⟨5,116,117⟩}
abbrev ao335 : Mgr := {an335 with memo := ((PCSDD.BOp.or,16,31),118)::an335.memo}
theorem a335 : ApplyCertificate 12 DEFAULT_LIMITS 20 PCSDD.BOp.or 16 31 ai335 118 ao335 := by
  exact ApplyCertificate.branch (fuel := 19) (a0 := 16) (b0 := 31) (lo := 116) (hi := 117) (r := 118) (op := PCSDD.BOp.or) (m := ai335) (m1 := ao336) (m2 := ao339) (m3 := an335) (by decide) (by rfl) (by decide) a336 a339 (by rfl)
abbrev an327 : Mgr := {ao335 with nodes := ao335.nodes.push ⟨4,115,118⟩}
abbrev ao327 : Mgr := {an327 with memo := ((PCSDD.BOp.or,16,32),119)::an327.memo}
theorem a327 : ApplyCertificate 12 DEFAULT_LIMITS 21 PCSDD.BOp.or 16 32 ai327 119 ao327 := by
  exact ApplyCertificate.branch (fuel := 20) (a0 := 16) (b0 := 32) (lo := 115) (hi := 118) (r := 119) (op := PCSDD.BOp.or) (m := ai327) (m1 := ao328) (m2 := ao335) (m3 := an327) (by decide) (by rfl) (by decide) a328 a335 (by rfl)
abbrev ai342 : Mgr := ao327
abbrev ai343 : Mgr := {ai342 with ops := ai342.ops+1}
abbrev ai344 : Mgr := {ai343 with ops := ai343.ops+1}
abbrev ai345 : Mgr := {ai344 with ops := ai344.ops+1}
abbrev ao345 : Mgr := {ai345 with ops := ai345.ops+1}
theorem a345 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.or 6 22 ai345 61 ao345 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 6) (b0 := 22) (r := 61) (op := PCSDD.BOp.or) (m := ai345) (by decide) (by rfl)
abbrev ai346 : Mgr := ao345
abbrev ao346 : Mgr := {ai346 with ops := ai346.ops+1}
theorem a346 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.or 1 22 ai346 1 ao346 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 1) (b0 := 22) (r := 1) (op := PCSDD.BOp.or) (m := ai346) (by decide) (by rfl)
abbrev an344 : Mgr := {ao346 with nodes := ao346.nodes.push ⟨6,61,1⟩}
abbrev ao344 : Mgr := {an344 with memo := ((PCSDD.BOp.or,16,22),120)::an344.memo}
theorem a344 : ApplyCertificate 12 DEFAULT_LIMITS 19 PCSDD.BOp.or 16 22 ai344 120 ao344 := by
  exact ApplyCertificate.branch (fuel := 18) (a0 := 16) (b0 := 22) (lo := 61) (hi := 1) (r := 120) (op := PCSDD.BOp.or) (m := ai344) (m1 := ao345) (m2 := ao346) (m3 := an344) (by decide) (by rfl) (by decide) a345 a346 (by rfl)
abbrev ai347 : Mgr := ao344
abbrev ai348 : Mgr := {ai347 with ops := ai347.ops+1}
abbrev ao348 : Mgr := {ai348 with ops := ai348.ops+1}
theorem a348 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.or 6 33 ai348 62 ao348 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 6) (b0 := 33) (r := 62) (op := PCSDD.BOp.or) (m := ai348) (by decide) (by rfl)
abbrev ai349 : Mgr := ao348
abbrev ao349 : Mgr := {ai349 with ops := ai349.ops+1}
theorem a349 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.or 1 33 ai349 1 ao349 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 1) (b0 := 33) (r := 1) (op := PCSDD.BOp.or) (m := ai349) (by decide) (by rfl)
abbrev an347 : Mgr := {ao349 with nodes := ao349.nodes.push ⟨6,62,1⟩}
abbrev ao347 : Mgr := {an347 with memo := ((PCSDD.BOp.or,16,33),121)::an347.memo}
theorem a347 : ApplyCertificate 12 DEFAULT_LIMITS 19 PCSDD.BOp.or 16 33 ai347 121 ao347 := by
  exact ApplyCertificate.branch (fuel := 18) (a0 := 16) (b0 := 33) (lo := 62) (hi := 1) (r := 121) (op := PCSDD.BOp.or) (m := ai347) (m1 := ao348) (m2 := ao349) (m3 := an347) (by decide) (by rfl) (by decide) a348 a349 (by rfl)
abbrev an343 : Mgr := {ao347 with nodes := ao347.nodes.push ⟨5,120,121⟩}
abbrev ao343 : Mgr := {an343 with memo := ((PCSDD.BOp.or,16,34),122)::an343.memo}
theorem a343 : ApplyCertificate 12 DEFAULT_LIMITS 20 PCSDD.BOp.or 16 34 ai343 122 ao343 := by
  exact ApplyCertificate.branch (fuel := 19) (a0 := 16) (b0 := 34) (lo := 120) (hi := 121) (r := 122) (op := PCSDD.BOp.or) (m := ai343) (m1 := ao344) (m2 := ao347) (m3 := an343) (by decide) (by rfl) (by decide) a344 a347 (by rfl)
abbrev ai350 : Mgr := ao343
abbrev ai351 : Mgr := {ai350 with ops := ai350.ops+1}
abbrev ai352 : Mgr := {ai351 with ops := ai351.ops+1}
abbrev ao352 : Mgr := {ai352 with ops := ai352.ops+1}
theorem a352 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.or 6 35 ai352 64 ao352 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 6) (b0 := 35) (r := 64) (op := PCSDD.BOp.or) (m := ai352) (by decide) (by rfl)
abbrev ai353 : Mgr := ao352
abbrev ao353 : Mgr := {ai353 with ops := ai353.ops+1}
theorem a353 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.or 1 35 ai353 1 ao353 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 1) (b0 := 35) (r := 1) (op := PCSDD.BOp.or) (m := ai353) (by decide) (by rfl)
abbrev an351 : Mgr := {ao353 with nodes := ao353.nodes.push ⟨6,64,1⟩}
abbrev ao351 : Mgr := {an351 with memo := ((PCSDD.BOp.or,16,35),123)::an351.memo}
theorem a351 : ApplyCertificate 12 DEFAULT_LIMITS 19 PCSDD.BOp.or 16 35 ai351 123 ao351 := by
  exact ApplyCertificate.branch (fuel := 18) (a0 := 16) (b0 := 35) (lo := 64) (hi := 1) (r := 123) (op := PCSDD.BOp.or) (m := ai351) (m1 := ao352) (m2 := ao353) (m3 := an351) (by decide) (by rfl) (by decide) a352 a353 (by rfl)
abbrev ai354 : Mgr := ao351
abbrev ai355 : Mgr := {ai354 with ops := ai354.ops+1}
abbrev ao355 : Mgr := {ai355 with ops := ai355.ops+1}
theorem a355 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.or 6 36 ai355 65 ao355 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 6) (b0 := 36) (r := 65) (op := PCSDD.BOp.or) (m := ai355) (by decide) (by rfl)
abbrev ai356 : Mgr := ao355
abbrev ao356 : Mgr := {ai356 with ops := ai356.ops+1}
theorem a356 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.or 1 36 ai356 1 ao356 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 1) (b0 := 36) (r := 1) (op := PCSDD.BOp.or) (m := ai356) (by decide) (by rfl)
abbrev an354 : Mgr := {ao356 with nodes := ao356.nodes.push ⟨6,65,1⟩}
abbrev ao354 : Mgr := {an354 with memo := ((PCSDD.BOp.or,16,36),124)::an354.memo}
theorem a354 : ApplyCertificate 12 DEFAULT_LIMITS 19 PCSDD.BOp.or 16 36 ai354 124 ao354 := by
  exact ApplyCertificate.branch (fuel := 18) (a0 := 16) (b0 := 36) (lo := 65) (hi := 1) (r := 124) (op := PCSDD.BOp.or) (m := ai354) (m1 := ao355) (m2 := ao356) (m3 := an354) (by decide) (by rfl) (by decide) a355 a356 (by rfl)
abbrev an350 : Mgr := {ao354 with nodes := ao354.nodes.push ⟨5,123,124⟩}
abbrev ao350 : Mgr := {an350 with memo := ((PCSDD.BOp.or,16,37),125)::an350.memo}
theorem a350 : ApplyCertificate 12 DEFAULT_LIMITS 20 PCSDD.BOp.or 16 37 ai350 125 ao350 := by
  exact ApplyCertificate.branch (fuel := 19) (a0 := 16) (b0 := 37) (lo := 123) (hi := 124) (r := 125) (op := PCSDD.BOp.or) (m := ai350) (m1 := ao351) (m2 := ao354) (m3 := an350) (by decide) (by rfl) (by decide) a351 a354 (by rfl)
abbrev an342 : Mgr := {ao350 with nodes := ao350.nodes.push ⟨4,122,125⟩}
abbrev ao342 : Mgr := {an342 with memo := ((PCSDD.BOp.or,16,38),126)::an342.memo}
theorem a342 : ApplyCertificate 12 DEFAULT_LIMITS 21 PCSDD.BOp.or 16 38 ai342 126 ao342 := by
  exact ApplyCertificate.branch (fuel := 20) (a0 := 16) (b0 := 38) (lo := 122) (hi := 125) (r := 126) (op := PCSDD.BOp.or) (m := ai342) (m1 := ao343) (m2 := ao350) (m3 := an342) (by decide) (by rfl) (by decide) a343 a350 (by rfl)
abbrev an326 : Mgr := {ao342 with nodes := ao342.nodes.push ⟨3,119,126⟩}
abbrev ao326 : Mgr := {an326 with memo := ((PCSDD.BOp.or,16,39),127)::an326.memo}
theorem a326 : ApplyCertificate 12 DEFAULT_LIMITS 22 PCSDD.BOp.or 16 39 ai326 127 ao326 := by
  exact ApplyCertificate.branch (fuel := 21) (a0 := 16) (b0 := 39) (lo := 119) (hi := 126) (r := 127) (op := PCSDD.BOp.or) (m := ai326) (m1 := ao327) (m2 := ao342) (m3 := an326) (by decide) (by rfl) (by decide) a327 a342 (by rfl)
abbrev ai357 : Mgr := ao326
abbrev ai358 : Mgr := {ai357 with ops := ai357.ops+1}
abbrev ai359 : Mgr := {ai358 with ops := ai358.ops+1}
abbrev ai360 : Mgr := {ai359 with ops := ai359.ops+1}
abbrev ai361 : Mgr := {ai360 with ops := ai360.ops+1}
abbrev ao361 : Mgr := {ai361 with ops := ai361.ops+1}
theorem a361 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.or 0 11 ai361 11 ao361 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 0) (b0 := 11) (r := 11) (op := PCSDD.BOp.or) (m := ai361) (by decide) (by rfl)
abbrev ai362 : Mgr := ao361
abbrev ao362 : Mgr := {ai362 with ops := ai362.ops+1}
theorem a362 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.or 0 1 ai362 1 ao362 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 0) (b0 := 1) (r := 1) (op := PCSDD.BOp.or) (m := ai362) (by decide) (by rfl)
abbrev an360 : Mgr := ao362
abbrev ao360 : Mgr := {an360 with memo := ((PCSDD.BOp.or,0,17),17)::an360.memo}
theorem a360 : ApplyCertificate 12 DEFAULT_LIMITS 19 PCSDD.BOp.or 17 0 ai360 17 ao360 := by
  exact ApplyCertificate.branch (fuel := 18) (a0 := 17) (b0 := 0) (lo := 11) (hi := 1) (r := 17) (op := PCSDD.BOp.or) (m := ai360) (m1 := ao361) (m2 := ao362) (m3 := an360) (by decide) (by rfl) (by decide) a361 a362 (by rfl)
abbrev ai363 : Mgr := ao360
abbrev ai364 : Mgr := {ai363 with ops := ai363.ops+1}
abbrev ao364 : Mgr := {ai364 with ops := ai364.ops+1}
theorem a364 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.or 11 28 ai364 69 ao364 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 11) (b0 := 28) (r := 69) (op := PCSDD.BOp.or) (m := ai364) (by decide) (by rfl)
abbrev ai365 : Mgr := ao364
abbrev ao365 : Mgr := {ai365 with ops := ai365.ops+1}
theorem a365 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.or 1 28 ai365 1 ao365 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 1) (b0 := 28) (r := 1) (op := PCSDD.BOp.or) (m := ai365) (by decide) (by rfl)
abbrev an363 : Mgr := {ao365 with nodes := ao365.nodes.push ⟨6,69,1⟩}
abbrev ao363 : Mgr := {an363 with memo := ((PCSDD.BOp.or,17,28),128)::an363.memo}
theorem a363 : ApplyCertificate 12 DEFAULT_LIMITS 19 PCSDD.BOp.or 17 28 ai363 128 ao363 := by
  exact ApplyCertificate.branch (fuel := 18) (a0 := 17) (b0 := 28) (lo := 69) (hi := 1) (r := 128) (op := PCSDD.BOp.or) (m := ai363) (m1 := ao364) (m2 := ao365) (m3 := an363) (by decide) (by rfl) (by decide) a364 a365 (by rfl)
abbrev an359 : Mgr := {ao363 with nodes := ao363.nodes.push ⟨5,17,128⟩}
abbrev ao359 : Mgr := {an359 with memo := ((PCSDD.BOp.or,17,29),129)::an359.memo}
theorem a359 : ApplyCertificate 12 DEFAULT_LIMITS 20 PCSDD.BOp.or 17 29 ai359 129 ao359 := by
  exact ApplyCertificate.branch (fuel := 19) (a0 := 17) (b0 := 29) (lo := 17) (hi := 128) (r := 129) (op := PCSDD.BOp.or) (m := ai359) (m1 := ao360) (m2 := ao363) (m3 := an359) (by decide) (by rfl) (by decide) a360 a363 (by rfl)
abbrev ai366 : Mgr := ao359
abbrev ai367 : Mgr := {ai366 with ops := ai366.ops+1}
abbrev ai368 : Mgr := {ai367 with ops := ai367.ops+1}
abbrev ao368 : Mgr := {ai368 with ops := ai368.ops+1}
theorem a368 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.or 11 25 ai368 71 ao368 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 11) (b0 := 25) (r := 71) (op := PCSDD.BOp.or) (m := ai368) (by decide) (by rfl)
abbrev ai369 : Mgr := ao368
abbrev ao369 : Mgr := {ai369 with ops := ai369.ops+1}
theorem a369 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.or 1 25 ai369 1 ao369 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 1) (b0 := 25) (r := 1) (op := PCSDD.BOp.or) (m := ai369) (by decide) (by rfl)
abbrev an367 : Mgr := {ao369 with nodes := ao369.nodes.push ⟨6,71,1⟩}
abbrev ao367 : Mgr := {an367 with memo := ((PCSDD.BOp.or,17,25),130)::an367.memo}
theorem a367 : ApplyCertificate 12 DEFAULT_LIMITS 19 PCSDD.BOp.or 17 25 ai367 130 ao367 := by
  exact ApplyCertificate.branch (fuel := 18) (a0 := 17) (b0 := 25) (lo := 71) (hi := 1) (r := 130) (op := PCSDD.BOp.or) (m := ai367) (m1 := ao368) (m2 := ao369) (m3 := an367) (by decide) (by rfl) (by decide) a368 a369 (by rfl)
abbrev ai370 : Mgr := ao367
abbrev ai371 : Mgr := {ai370 with ops := ai370.ops+1}
abbrev ao371 : Mgr := {ai371 with ops := ai371.ops+1}
theorem a371 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.or 11 30 ai371 72 ao371 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 11) (b0 := 30) (r := 72) (op := PCSDD.BOp.or) (m := ai371) (by decide) (by rfl)
abbrev ai372 : Mgr := ao371
abbrev ao372 : Mgr := {ai372 with ops := ai372.ops+1}
theorem a372 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.or 1 30 ai372 1 ao372 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 1) (b0 := 30) (r := 1) (op := PCSDD.BOp.or) (m := ai372) (by decide) (by rfl)
abbrev an370 : Mgr := {ao372 with nodes := ao372.nodes.push ⟨6,72,1⟩}
abbrev ao370 : Mgr := {an370 with memo := ((PCSDD.BOp.or,17,30),131)::an370.memo}
theorem a370 : ApplyCertificate 12 DEFAULT_LIMITS 19 PCSDD.BOp.or 17 30 ai370 131 ao370 := by
  exact ApplyCertificate.branch (fuel := 18) (a0 := 17) (b0 := 30) (lo := 72) (hi := 1) (r := 131) (op := PCSDD.BOp.or) (m := ai370) (m1 := ao371) (m2 := ao372) (m3 := an370) (by decide) (by rfl) (by decide) a371 a372 (by rfl)
abbrev an366 : Mgr := {ao370 with nodes := ao370.nodes.push ⟨5,130,131⟩}
abbrev ao366 : Mgr := {an366 with memo := ((PCSDD.BOp.or,17,31),132)::an366.memo}
theorem a366 : ApplyCertificate 12 DEFAULT_LIMITS 20 PCSDD.BOp.or 17 31 ai366 132 ao366 := by
  exact ApplyCertificate.branch (fuel := 19) (a0 := 17) (b0 := 31) (lo := 130) (hi := 131) (r := 132) (op := PCSDD.BOp.or) (m := ai366) (m1 := ao367) (m2 := ao370) (m3 := an366) (by decide) (by rfl) (by decide) a367 a370 (by rfl)
abbrev an358 : Mgr := {ao366 with nodes := ao366.nodes.push ⟨4,129,132⟩}
abbrev ao358 : Mgr := {an358 with memo := ((PCSDD.BOp.or,17,32),133)::an358.memo}
theorem a358 : ApplyCertificate 12 DEFAULT_LIMITS 21 PCSDD.BOp.or 17 32 ai358 133 ao358 := by
  exact ApplyCertificate.branch (fuel := 20) (a0 := 17) (b0 := 32) (lo := 129) (hi := 132) (r := 133) (op := PCSDD.BOp.or) (m := ai358) (m1 := ao359) (m2 := ao366) (m3 := an358) (by decide) (by rfl) (by decide) a359 a366 (by rfl)
abbrev ai373 : Mgr := ao358
abbrev ai374 : Mgr := {ai373 with ops := ai373.ops+1}
abbrev ai375 : Mgr := {ai374 with ops := ai374.ops+1}
abbrev ai376 : Mgr := {ai375 with ops := ai375.ops+1}
abbrev ao376 : Mgr := {ai376 with ops := ai376.ops+1}
theorem a376 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.or 11 22 ai376 75 ao376 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 11) (b0 := 22) (r := 75) (op := PCSDD.BOp.or) (m := ai376) (by decide) (by rfl)
abbrev ai377 : Mgr := ao376
abbrev ao377 : Mgr := {ai377 with ops := ai377.ops+1}
theorem a377 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.or 1 22 ai377 1 ao377 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 1) (b0 := 22) (r := 1) (op := PCSDD.BOp.or) (m := ai377) (by decide) (by rfl)
abbrev an375 : Mgr := {ao377 with nodes := ao377.nodes.push ⟨6,75,1⟩}
abbrev ao375 : Mgr := {an375 with memo := ((PCSDD.BOp.or,17,22),134)::an375.memo}
theorem a375 : ApplyCertificate 12 DEFAULT_LIMITS 19 PCSDD.BOp.or 17 22 ai375 134 ao375 := by
  exact ApplyCertificate.branch (fuel := 18) (a0 := 17) (b0 := 22) (lo := 75) (hi := 1) (r := 134) (op := PCSDD.BOp.or) (m := ai375) (m1 := ao376) (m2 := ao377) (m3 := an375) (by decide) (by rfl) (by decide) a376 a377 (by rfl)
abbrev ai378 : Mgr := ao375
abbrev ai379 : Mgr := {ai378 with ops := ai378.ops+1}
abbrev ao379 : Mgr := {ai379 with ops := ai379.ops+1}
theorem a379 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.or 11 33 ai379 76 ao379 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 11) (b0 := 33) (r := 76) (op := PCSDD.BOp.or) (m := ai379) (by decide) (by rfl)
abbrev ai380 : Mgr := ao379
abbrev ao380 : Mgr := {ai380 with ops := ai380.ops+1}
theorem a380 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.or 1 33 ai380 1 ao380 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 1) (b0 := 33) (r := 1) (op := PCSDD.BOp.or) (m := ai380) (by decide) (by rfl)
abbrev an378 : Mgr := {ao380 with nodes := ao380.nodes.push ⟨6,76,1⟩}
abbrev ao378 : Mgr := {an378 with memo := ((PCSDD.BOp.or,17,33),135)::an378.memo}
theorem a378 : ApplyCertificate 12 DEFAULT_LIMITS 19 PCSDD.BOp.or 17 33 ai378 135 ao378 := by
  exact ApplyCertificate.branch (fuel := 18) (a0 := 17) (b0 := 33) (lo := 76) (hi := 1) (r := 135) (op := PCSDD.BOp.or) (m := ai378) (m1 := ao379) (m2 := ao380) (m3 := an378) (by decide) (by rfl) (by decide) a379 a380 (by rfl)
abbrev an374 : Mgr := {ao378 with nodes := ao378.nodes.push ⟨5,134,135⟩}
abbrev ao374 : Mgr := {an374 with memo := ((PCSDD.BOp.or,17,34),136)::an374.memo}
theorem a374 : ApplyCertificate 12 DEFAULT_LIMITS 20 PCSDD.BOp.or 17 34 ai374 136 ao374 := by
  exact ApplyCertificate.branch (fuel := 19) (a0 := 17) (b0 := 34) (lo := 134) (hi := 135) (r := 136) (op := PCSDD.BOp.or) (m := ai374) (m1 := ao375) (m2 := ao378) (m3 := an374) (by decide) (by rfl) (by decide) a375 a378 (by rfl)
abbrev ai381 : Mgr := ao374
abbrev ai382 : Mgr := {ai381 with ops := ai381.ops+1}
abbrev ai383 : Mgr := {ai382 with ops := ai382.ops+1}
abbrev ao383 : Mgr := {ai383 with ops := ai383.ops+1}
theorem a383 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.or 11 35 ai383 78 ao383 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 11) (b0 := 35) (r := 78) (op := PCSDD.BOp.or) (m := ai383) (by decide) (by rfl)
abbrev ai384 : Mgr := ao383
abbrev ao384 : Mgr := {ai384 with ops := ai384.ops+1}
theorem a384 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.or 1 35 ai384 1 ao384 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 1) (b0 := 35) (r := 1) (op := PCSDD.BOp.or) (m := ai384) (by decide) (by rfl)
abbrev an382 : Mgr := {ao384 with nodes := ao384.nodes.push ⟨6,78,1⟩}
abbrev ao382 : Mgr := {an382 with memo := ((PCSDD.BOp.or,17,35),137)::an382.memo}
theorem a382 : ApplyCertificate 12 DEFAULT_LIMITS 19 PCSDD.BOp.or 17 35 ai382 137 ao382 := by
  exact ApplyCertificate.branch (fuel := 18) (a0 := 17) (b0 := 35) (lo := 78) (hi := 1) (r := 137) (op := PCSDD.BOp.or) (m := ai382) (m1 := ao383) (m2 := ao384) (m3 := an382) (by decide) (by rfl) (by decide) a383 a384 (by rfl)
abbrev ai385 : Mgr := ao382
abbrev ai386 : Mgr := {ai385 with ops := ai385.ops+1}
abbrev ao386 : Mgr := {ai386 with ops := ai386.ops+1}
theorem a386 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.or 11 36 ai386 79 ao386 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 11) (b0 := 36) (r := 79) (op := PCSDD.BOp.or) (m := ai386) (by decide) (by rfl)
abbrev ai387 : Mgr := ao386
abbrev ao387 : Mgr := {ai387 with ops := ai387.ops+1}
theorem a387 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.or 1 36 ai387 1 ao387 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 1) (b0 := 36) (r := 1) (op := PCSDD.BOp.or) (m := ai387) (by decide) (by rfl)
abbrev an385 : Mgr := {ao387 with nodes := ao387.nodes.push ⟨6,79,1⟩}
abbrev ao385 : Mgr := {an385 with memo := ((PCSDD.BOp.or,17,36),138)::an385.memo}
theorem a385 : ApplyCertificate 12 DEFAULT_LIMITS 19 PCSDD.BOp.or 17 36 ai385 138 ao385 := by
  exact ApplyCertificate.branch (fuel := 18) (a0 := 17) (b0 := 36) (lo := 79) (hi := 1) (r := 138) (op := PCSDD.BOp.or) (m := ai385) (m1 := ao386) (m2 := ao387) (m3 := an385) (by decide) (by rfl) (by decide) a386 a387 (by rfl)
abbrev an381 : Mgr := {ao385 with nodes := ao385.nodes.push ⟨5,137,138⟩}
abbrev ao381 : Mgr := {an381 with memo := ((PCSDD.BOp.or,17,37),139)::an381.memo}
theorem a381 : ApplyCertificate 12 DEFAULT_LIMITS 20 PCSDD.BOp.or 17 37 ai381 139 ao381 := by
  exact ApplyCertificate.branch (fuel := 19) (a0 := 17) (b0 := 37) (lo := 137) (hi := 138) (r := 139) (op := PCSDD.BOp.or) (m := ai381) (m1 := ao382) (m2 := ao385) (m3 := an381) (by decide) (by rfl) (by decide) a382 a385 (by rfl)
abbrev an373 : Mgr := {ao381 with nodes := ao381.nodes.push ⟨4,136,139⟩}
abbrev ao373 : Mgr := {an373 with memo := ((PCSDD.BOp.or,17,38),140)::an373.memo}
theorem a373 : ApplyCertificate 12 DEFAULT_LIMITS 21 PCSDD.BOp.or 17 38 ai373 140 ao373 := by
  exact ApplyCertificate.branch (fuel := 20) (a0 := 17) (b0 := 38) (lo := 136) (hi := 139) (r := 140) (op := PCSDD.BOp.or) (m := ai373) (m1 := ao374) (m2 := ao381) (m3 := an373) (by decide) (by rfl) (by decide) a374 a381 (by rfl)
abbrev an357 : Mgr := {ao373 with nodes := ao373.nodes.push ⟨3,133,140⟩}
abbrev ao357 : Mgr := {an357 with memo := ((PCSDD.BOp.or,17,39),141)::an357.memo}
theorem a357 : ApplyCertificate 12 DEFAULT_LIMITS 22 PCSDD.BOp.or 17 39 ai357 141 ao357 := by
  exact ApplyCertificate.branch (fuel := 21) (a0 := 17) (b0 := 39) (lo := 133) (hi := 140) (r := 141) (op := PCSDD.BOp.or) (m := ai357) (m1 := ao358) (m2 := ao373) (m3 := an357) (by decide) (by rfl) (by decide) a358 a373 (by rfl)
abbrev an325 : Mgr := {ao357 with nodes := ao357.nodes.push ⟨2,127,141⟩}
abbrev ao325 : Mgr := {an325 with memo := ((PCSDD.BOp.or,18,39),142)::an325.memo}
theorem a325 : ApplyCertificate 12 DEFAULT_LIMITS 23 PCSDD.BOp.or 18 39 ai325 142 ao325 := by
  exact ApplyCertificate.branch (fuel := 22) (a0 := 18) (b0 := 39) (lo := 127) (hi := 141) (r := 142) (op := PCSDD.BOp.or) (m := ai325) (m1 := ao326) (m2 := ao357) (m3 := an325) (by decide) (by rfl) (by decide) a326 a357 (by rfl)
abbrev an263 : Mgr := {ao325 with nodes := ao325.nodes.push ⟨1,113,142⟩}
abbrev ao263 : Mgr := {an263 with memo := ((PCSDD.BOp.or,19,39),143)::an263.memo}
theorem a263 : ApplyCertificate 12 DEFAULT_LIMITS 24 PCSDD.BOp.or 19 39 ai263 143 ao263 := by
  exact ApplyCertificate.branch (fuel := 23) (a0 := 19) (b0 := 39) (lo := 113) (hi := 142) (r := 143) (op := PCSDD.BOp.or) (m := ai263) (m1 := ao264) (m2 := ao325) (m3 := an263) (by decide) (by rfl) (by decide) a264 a325 (by rfl)
abbrev an149 : Mgr := {ao263 with nodes := ao263.nodes.push ⟨0,84,143⟩}
abbrev ao149 : Mgr := {an149 with memo := ((PCSDD.BOp.or,20,39),144)::an149.memo}
theorem a149 : ApplyCertificate 12 DEFAULT_LIMITS 25 PCSDD.BOp.or 20 39 ai149 144 ao149 := by
  exact ApplyCertificate.branch (fuel := 24) (a0 := 20) (b0 := 39) (lo := 84) (hi := 143) (r := 144) (op := PCSDD.BOp.or) (m := ai149) (m1 := ao150) (m2 := ao263) (m3 := an149) (by decide) (by rfl) (by decide) a150 a263 (by rfl)
abbrev o0 : Mgr := ao149
theorem c0 : CompileCertificate 12 DEFAULT_LIMITS f0 i0 144 o0 := by
  exact CompileCertificate.or (fuel := 25) (m := i0) (ma := o1) (mb := o75) (out := o0) (x := 20) (y := 39) (r := 144) c1 c75 (ApplyCertificate.sound (m := o75) (out := ao149) a149) (by decide)
abbrev f388 : BForm 12 := PCSOmega.BForm.ff
abbrev i388 : Mgr := { nodes := #[{ var := 0, low := 0, high := 1 }, { var := 6, low := 0, high := 1 }, { var := 0, low := 0, high := 3 },              { var := 1, low := 0, high := 1 }, { var := 7, low := 0, high := 1 }, { var := 1, low := 0, high := 6 },              { var := 2, low := 0, high := 1 }, { var := 8, low := 0, high := 1 }, { var := 2, low := 0, high := 9 },              { var := 7, low := 9, high := 1 }, { var := 2, low := 6, high := 11 }, { var := 1, low := 10, high := 12 },              { var := 6, low := 9, high := 1 }, { var := 2, low := 3, high := 14 }, { var := 6, low := 6, high := 1 },              { var := 6, low := 11, high := 1 }, { var := 2, low := 16, high := 17 },              { var := 1, low := 15, high := 18 }, { var := 0, low := 13, high := 19 },              { var := 3, low := 0, high := 1 }, { var := 9, low := 0, high := 1 }, { var := 3, low := 0, high := 22 },              { var := 4, low := 0, high := 1 }, { var := 10, low := 0, high := 1 }, { var := 4, low := 0, high := 25 },              { var := 5, low := 0, high := 1 }, { var := 11, low := 0, high := 1 }, { var := 5, low := 0, high := 28 },              { var := 10, low := 28, high := 1 }, { var := 5, low := 25, high := 30 },              { var := 4, low := 29, high := 31 }, { var := 9, low := 28, high := 1 },              { var := 5, low := 22, high := 33 }, { var := 9, low := 25, high := 1 },              { var := 9, low := 30, high := 1 }, { var := 5, low := 35, high := 36 },              { var := 4, low := 34, high := 37 }, { var := 3, low := 32, high := 38 },              { var := 8, low := 28, high := 1 }, { var := 5, low := 9, high := 40 }, { var := 8, low := 25, high := 1 },              { var := 8, low := 30, high := 1 }, { var := 5, low := 42, high := 43 },              { var := 4, low := 41, high := 44 }, { var := 8, low := 22, high := 1 },              { var := 8, low := 33, high := 1 }, { var := 5, low := 46, high := 47 },              { var := 8, low := 35, high := 1 }, { var := 8, low := 36, high := 1 },              { var := 5, low := 49, high := 50 }, { var := 4, low := 48, high := 51 },              { var := 3, low := 45, high := 52 }, { var := 2, low := 39, high := 53 },              { var := 7, low := 28, high := 1 }, { var := 5, low := 6, high := 55 }, { var := 7, low := 25, high := 1 },              { var := 7, low := 30, high := 1 }, { var := 5, low := 57, high := 58 },              { var := 4, low := 56, high := 59 }, { var := 7, low := 22, high := 1 },              { var := 7, low := 33, high := 1 }, { var := 5, low := 61, high := 62 },              { var := 7, low := 35, high := 1 }, { var := 7, low := 36, high := 1 },              { var := 5, low := 64, high := 65 }, { var := 4, low := 63, high := 66 },              { var := 3, low := 60, high := 67 }, { var := 7, low := 40, high := 1 },              { var := 5, low := 11, high := 69 }, { var := 7, low := 42, high := 1 },              { var := 7, low := 43, high := 1 }, { var := 5, low := 71, high := 72 },              { var := 4, low := 70, high := 73 }, { var := 7, low := 46, high := 1 },              { var := 7, low := 47, high := 1 }, { var := 5, low := 75, high := 76 },              { var := 7, low := 49, high := 1 }, { var := 7, low := 50, high := 1 },              { var := 5, low := 78, high := 79 }, { var := 4, low := 77, high := 80 },              { var := 3, low := 74, high := 81 }, { var := 2, low := 68, high := 82 },              { var := 1, low := 54, high := 83 }, { var := 6, low := 28, high := 1 },              { var := 5, low := 3, high := 85 }, { var := 6, low := 25, high := 1 }, { var := 6, low := 30, high := 1 },              { var := 5, low := 87, high := 88 }, { var := 4, low := 86, high := 89 },              { var := 6, low := 22, high := 1 }, { var := 6, low := 33, high := 1 },              { var := 5, low := 91, high := 92 }, { var := 6, low := 35, high := 1 },              { var := 6, low := 36, high := 1 }, { var := 5, low := 94, high := 95 },              { var := 4, low := 93, high := 96 }, { var := 3, low := 90, high := 97 },              { var := 6, low := 40, high := 1 }, { var := 5, low := 14, high := 99 },              { var := 6, low := 42, high := 1 }, { var := 6, low := 43, high := 1 },              { var := 5, low := 101, high := 102 }, { var := 4, low := 100, high := 103 },              { var := 6, low := 46, high := 1 }, { var := 6, low := 47, high := 1 },              { var := 5, low := 105, high := 106 }, { var := 6, low := 49, high := 1 },              { var := 6, low := 50, high := 1 }, { var := 5, low := 108, high := 109 },              { var := 4, low := 107, high := 110 }, { var := 3, low := 104, high := 111 },              { var := 2, low := 98, high := 112 }, { var := 6, low := 55, high := 1 },              { var := 5, low := 16, high := 114 }, { var := 6, low := 57, high := 1 },              { var := 6, low := 58, high := 1 }, { var := 5, low := 116, high := 117 },              { var := 4, low := 115, high := 118 }, { var := 6, low := 61, high := 1 },              { var := 6, low := 62, high := 1 }, { var := 5, low := 120, high := 121 },              { var := 6, low := 64, high := 1 }, { var := 6, low := 65, high := 1 },              { var := 5, low := 123, high := 124 }, { var := 4, low := 122, high := 125 },              { var := 3, low := 119, high := 126 }, { var := 6, low := 69, high := 1 },              { var := 5, low := 17, high := 128 }, { var := 6, low := 71, high := 1 },              { var := 6, low := 72, high := 1 }, { var := 5, low := 130, high := 131 },              { var := 4, low := 129, high := 132 }, { var := 6, low := 75, high := 1 },              { var := 6, low := 76, high := 1 }, { var := 5, low := 134, high := 135 },              { var := 6, low := 78, high := 1 }, { var := 6, low := 79, high := 1 },              { var := 5, low := 137, high := 138 }, { var := 4, low := 136, high := 139 },              { var := 3, low := 133, high := 140 }, { var := 2, low := 127, high := 141 },              { var := 1, low := 113, high := 142 }, { var := 0, low := 84, high := 143 }],   memo := [((PCSDD.BOp.or, 20, 39), 144),            ((PCSDD.BOp.or, 19, 39), 143),            ((PCSDD.BOp.or, 18, 39), 142),            ((PCSDD.BOp.or, 17, 39), 141),            ((PCSDD.BOp.or, 17, 38), 140),            ((PCSDD.BOp.or, 17, 37), 139),            ((PCSDD.BOp.or, 17, 36), 138),            ((PCSDD.BOp.or, 17, 35), 137),            ((PCSDD.BOp.or, 17, 34), 136),            ((PCSDD.BOp.or, 17, 33), 135),            ((PCSDD.BOp.or, 17, 22), 134),            ((PCSDD.BOp.or, 17, 32), 133),            ((PCSDD.BOp.or, 17, 31), 132),            ((PCSDD.BOp.or, 17, 30), 131),            ((PCSDD.BOp.or, 17, 25), 130),            ((PCSDD.BOp.or, 17, 29), 129),            ((PCSDD.BOp.or, 17, 28), 128),            ((PCSDD.BOp.or, 0, 17), 17),            ((PCSDD.BOp.or, 16, 39), 127),            ((PCSDD.BOp.or, 16, 38), 126),            ((PCSDD.BOp.or, 16, 37), 125),            ((PCSDD.BOp.or, 16, 36), 124),            ((PCSDD.BOp.or, 16, 35), 123),            ((PCSDD.BOp.or, 16, 34), 122),            ((PCSDD.BOp.or, 16, 33), 121),            ((PCSDD.BOp.or, 16, 22), 120),            ((PCSDD.BOp.or, 16, 32), 119),            ((PCSDD.BOp.or, 16, 31), 118),            ((PCSDD.BOp.or, 16, 30), 117),            ((PCSDD.BOp.or, 16, 25), 116),            ((PCSDD.BOp.or, 16, 29), 115),            ((PCSDD.BOp.or, 16, 28), 114),            ((PCSDD.BOp.or, 0, 16), 16),            ((PCSDD.BOp.or, 15, 39), 113),            ((PCSDD.BOp.or, 14, 39), 112),            ((PCSDD.BOp.or, 14, 38), 111),            ((PCSDD.BOp.or, 14, 37), 110),            ((PCSDD.BOp.or, 14, 36), 109),            ((PCSDD.BOp.or, 14, 35), 108),            ((PCSDD.BOp.or, 14, 34), 107),            ((PCSDD.BOp.or, 14, 33), 106),            ((PCSDD.BOp.or, 14, 22), 105),            ((PCSDD.BOp.or, 14, 32), 104),            ((PCSDD.BOp.or, 14, 31), 103),            ((PCSDD.BOp.or, 14, 30), 102),            ((PCSDD.BOp.or, 14, 25), 101),            ((PCSDD.BOp.or, 14, 29), 100),            ((PCSDD.BOp.or, 14, 28), 99),            ((PCSDD.BOp.or, 0, 14), 14),            ((PCSDD.BOp.or, 3, 39), 98),            ((PCSDD.BOp.or, 3, 38), 97),            ((PCSDD.BOp.or, 3, 37), 96),            ((PCSDD.BOp.or, 3, 36), 95),            ((PCSDD.BOp.or, 3, 35), 94),            ((PCSDD.BOp.or, 3, 34), 93),            ((PCSDD.BOp.or, 3, 33), 92),            ((PCSDD.BOp.or, 3, 22), 91),            ((PCSDD.BOp.or, 3, 32), 90),            ((PCSDD.BOp.or, 3, 31), 89),            ((PCSDD.BOp.or, 3, 30), 88),            ((PCSDD.BOp.or, 3, 25), 87),            ((PCSDD.BOp.or, 3, 29), 86),            ((PCSDD.BOp.or, 3, 28), 85),            ((PCSDD.BOp.or, 13, 39), 84),            ((PCSDD.BOp.or, 12, 39), 83),            ((PCSDD.BOp.or, 11, 39), 82),            ((PCSDD.BOp.or, 11, 38), 81),            ((PCSDD.BOp.or, 11, 37), 80),            ((PCSDD.BOp.or, 11, 36), 79),            ((PCSDD.BOp.or, 11, 35), 78),            ((PCSDD.BOp.or, 11, 34), 77),            ((PCSDD.BOp.or, 11, 33), 76),            ((PCSDD.BOp.or, 11, 22), 75),            ((PCSDD.BOp.or, 11, 32), 74),            ((PCSDD.BOp.or, 11, 31), 73),            ((PCSDD.BOp.or, 11, 30), 72),            ((PCSDD.BOp.or, 11, 25), 71),            ((PCSDD.BOp.or, 11, 29), 70),            ((PCSDD.BOp.or, 11, 28), 69),            ((PCSDD.BOp.or, 6, 39), 68),            ((PCSDD.BOp.or, 6, 38), 67),            ((PCSDD.BOp.or, 6, 37), 66),            ((PCSDD.BOp.or, 6, 36), 65),            ((PCSDD.BOp.or, 6, 35), 64),            ((PCSDD.BOp.or, 6, 34), 63),            ((PCSDD.BOp.or, 6, 33), 62),            ((PCSDD.BOp.or, 6, 22), 61),            ((PCSDD.BOp.or, 6, 32), 60),            ((PCSDD.BOp.or, 6, 31), 59),            ((PCSDD.BOp.or, 6, 30), 58),            ((PCSDD.BOp.or, 6, 25), 57),            ((PCSDD.BOp.or, 6, 29), 56),            ((PCSDD.BOp.or, 6, 28), 55),            ((PCSDD.BOp.or, 10, 39), 54),            ((PCSDD.BOp.or, 9, 39), 53),            ((PCSDD.BOp.or, 9, 38), 52),            ((PCSDD.BOp.or, 9, 37), 51),            ((PCSDD.BOp.or, 9, 36), 50),            ((PCSDD.BOp.or, 1, 36), 1),            ((PCSDD.BOp.or, 9, 35), 49),            ((PCSDD.BOp.or, 1, 35), 1),            ((PCSDD.BOp.or, 9, 34), 48),            ((PCSDD.BOp.or, 9, 33), 47),            ((PCSDD.BOp.or, 1, 33), 1),            ((PCSDD.BOp.or, 9, 22), 46),            ((PCSDD.BOp.or, 1, 22), 1),            ((PCSDD.BOp.or, 9, 32), 45),            ((PCSDD.BOp.or, 9, 31), 44),            ((PCSDD.BOp.or, 9, 30), 43),            ((PCSDD.BOp.or, 9, 25), 42),            ((PCSDD.BOp.or, 9, 29), 41),            ((PCSDD.BOp.or, 9, 28), 40),            ((PCSDD.BOp.or, 0, 39), 39),            ((PCSDD.BOp.or, 0, 38), 38),            ((PCSDD.BOp.or, 0, 37), 37),            ((PCSDD.BOp.or, 0, 36), 36),            ((PCSDD.BOp.or, 0, 35), 35),            ((PCSDD.BOp.or, 0, 34), 34),            ((PCSDD.BOp.or, 0, 33), 33),            ((PCSDD.BOp.or, 23, 32), 39),            ((PCSDD.BOp.or, 22, 32), 38),            ((PCSDD.BOp.or, 22, 31), 37),            ((PCSDD.BOp.or, 22, 30), 36),            ((PCSDD.BOp.or, 1, 30), 1),            ((PCSDD.BOp.or, 22, 25), 35),            ((PCSDD.BOp.or, 1, 25), 1),            ((PCSDD.BOp.or, 22, 29), 34),            ((PCSDD.BOp.or, 22, 28), 33),            ((PCSDD.BOp.or, 0, 22), 22),            ((PCSDD.BOp.or, 0, 32), 32),            ((PCSDD.BOp.or, 0, 31), 31),            ((PCSDD.BOp.or, 0, 30), 30),            ((PCSDD.BOp.or, 26, 29), 32),            ((PCSDD.BOp.or, 25, 29), 31),            ((PCSDD.BOp.or, 25, 28), 30),            ((PCSDD.BOp.or, 1, 28), 1),            ((PCSDD.BOp.or, 0, 25), 25),            ((PCSDD.BOp.or, 0, 29), 29),            ((PCSDD.BOp.or, 0, 28), 28),            ((PCSDD.BOp.and, 27, 28), 29),            ((PCSDD.BOp.and, 1, 28), 28),            ((PCSDD.BOp.and, 0, 28), 0),            ((PCSDD.BOp.and, 24, 25), 26),            ((PCSDD.BOp.and, 1, 25), 25),            ((PCSDD.BOp.and, 0, 25), 0),            ((PCSDD.BOp.and, 21, 22), 23),            ((PCSDD.BOp.and, 1, 22), 22),            ((PCSDD.BOp.and, 0, 22), 0),            ((PCSDD.BOp.or, 4, 13), 20),            ((PCSDD.BOp.or, 3, 13), 19),            ((PCSDD.BOp.or, 3, 12), 18),            ((PCSDD.BOp.or, 3, 11), 17),            ((PCSDD.BOp.or, 1, 11), 1),            ((PCSDD.BOp.or, 3, 6), 16),            ((PCSDD.BOp.or, 1, 6), 1),            ((PCSDD.BOp.or, 3, 10), 15),            ((PCSDD.BOp.or, 3, 9), 14),            ((PCSDD.BOp.or, 0, 3), 3),            ((PCSDD.BOp.or, 0, 13), 13),            ((PCSDD.BOp.or, 0, 12), 12),            ((PCSDD.BOp.or, 0, 11), 11),            ((PCSDD.BOp.or, 7, 10), 13),            ((PCSDD.BOp.or, 6, 10), 12),            ((PCSDD.BOp.or, 6, 9), 11),            ((PCSDD.BOp.or, 1, 9), 1),            ((PCSDD.BOp.or, 1, 1), 1),            ((PCSDD.BOp.or, 0, 6), 6),            ((PCSDD.BOp.or, 0, 10), 10),            ((PCSDD.BOp.or, 0, 9), 9),            ((PCSDD.BOp.or, 0, 1), 1),            ((PCSDD.BOp.or, 0, 0), 0),            ((PCSDD.BOp.and, 8, 9), 10),            ((PCSDD.BOp.and, 1, 9), 9),            ((PCSDD.BOp.and, 0, 9), 0),            ((PCSDD.BOp.and, 5, 6), 7),            ((PCSDD.BOp.and, 1, 6), 6),            ((PCSDD.BOp.and, 0, 6), 0),            ((PCSDD.BOp.and, 2, 3), 4),            ((PCSDD.BOp.and, 1, 3), 3),            ((PCSDD.BOp.and, 1, 1), 1),            ((PCSDD.BOp.and, 0, 3), 0),            ((PCSDD.BOp.and, 0, 1), 0),            ((PCSDD.BOp.and, 0, 0), 0)],   ops := 365,   visits := 23,   wsteps := 0 }
abbrev o388 : Mgr := {i388 with visits := i388.visits+1}
theorem c388 : CompileCertificate 12 DEFAULT_LIMITS f388 i388 0 o388 := by
  exact CompileCertificate.ff _
abbrev ai389 : Mgr := o388
abbrev ai390 : Mgr := {ai389 with ops := ai389.ops+1}
abbrev ai391 : Mgr := {ai390 with ops := ai390.ops+1}
abbrev ai392 : Mgr := {ai391 with ops := ai391.ops+1}
abbrev ai393 : Mgr := {ai392 with ops := ai392.ops+1}
abbrev ai394 : Mgr := {ai393 with ops := ai393.ops+1}
abbrev ai395 : Mgr := {ai394 with ops := ai394.ops+1}
abbrev ao395 : Mgr := {ai395 with ops := ai395.ops+1, memo := ((PCSDD.BOp.xor,0,0),0)::ai395.memo}
theorem a395 : ApplyCertificate 12 DEFAULT_LIMITS 19 PCSDD.BOp.xor 0 0 ai395 0 ao395 := by
  exact ApplyCertificate.terminal (fuel := 18) (a0 := 0) (b0 := 0) (op := PCSDD.BOp.xor) (m := ai395) (by decide) (by rfl) (by decide)
abbrev ai396 : Mgr := ao395
abbrev ai397 : Mgr := {ai396 with ops := ai396.ops+1}
abbrev ao397 : Mgr := {ai397 with ops := ai397.ops+1}
theorem a397 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.xor 0 0 ai397 0 ao397 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 0) (b0 := 0) (r := 0) (op := PCSDD.BOp.xor) (m := ai397) (by decide) (by rfl)
abbrev ai398 : Mgr := ao397
abbrev ao398 : Mgr := {ai398 with ops := ai398.ops+1, memo := ((PCSDD.BOp.xor,0,1),1)::ai398.memo}
theorem a398 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.xor 0 1 ai398 1 ao398 := by
  exact ApplyCertificate.terminal (fuel := 17) (a0 := 0) (b0 := 1) (op := PCSDD.BOp.xor) (m := ai398) (by decide) (by rfl) (by decide)
abbrev an396 : Mgr := ao398
abbrev ao396 : Mgr := {an396 with memo := ((PCSDD.BOp.xor,0,28),28)::an396.memo}
theorem a396 : ApplyCertificate 12 DEFAULT_LIMITS 19 PCSDD.BOp.xor 0 28 ai396 28 ao396 := by
  exact ApplyCertificate.branch (fuel := 18) (a0 := 0) (b0 := 28) (lo := 0) (hi := 1) (r := 28) (op := PCSDD.BOp.xor) (m := ai396) (m1 := ao397) (m2 := ao398) (m3 := an396) (by decide) (by rfl) (by decide) a397 a398 (by rfl)
abbrev an394 : Mgr := ao396
abbrev ao394 : Mgr := {an394 with memo := ((PCSDD.BOp.xor,0,29),29)::an394.memo}
theorem a394 : ApplyCertificate 12 DEFAULT_LIMITS 20 PCSDD.BOp.xor 0 29 ai394 29 ao394 := by
  exact ApplyCertificate.branch (fuel := 19) (a0 := 0) (b0 := 29) (lo := 0) (hi := 28) (r := 29) (op := PCSDD.BOp.xor) (m := ai394) (m1 := ao395) (m2 := ao396) (m3 := an394) (by decide) (by rfl) (by decide) a395 a396 (by rfl)
abbrev ai399 : Mgr := ao394
abbrev ai400 : Mgr := {ai399 with ops := ai399.ops+1}
abbrev ai401 : Mgr := {ai400 with ops := ai400.ops+1}
abbrev ao401 : Mgr := {ai401 with ops := ai401.ops+1}
theorem a401 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.xor 0 0 ai401 0 ao401 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 0) (b0 := 0) (r := 0) (op := PCSDD.BOp.xor) (m := ai401) (by decide) (by rfl)
abbrev ai402 : Mgr := ao401
abbrev ao402 : Mgr := {ai402 with ops := ai402.ops+1}
theorem a402 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.xor 0 1 ai402 1 ao402 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 0) (b0 := 1) (r := 1) (op := PCSDD.BOp.xor) (m := ai402) (by decide) (by rfl)
abbrev an400 : Mgr := ao402
abbrev ao400 : Mgr := {an400 with memo := ((PCSDD.BOp.xor,0,25),25)::an400.memo}
theorem a400 : ApplyCertificate 12 DEFAULT_LIMITS 19 PCSDD.BOp.xor 0 25 ai400 25 ao400 := by
  exact ApplyCertificate.branch (fuel := 18) (a0 := 0) (b0 := 25) (lo := 0) (hi := 1) (r := 25) (op := PCSDD.BOp.xor) (m := ai400) (m1 := ao401) (m2 := ao402) (m3 := an400) (by decide) (by rfl) (by decide) a401 a402 (by rfl)
abbrev ai403 : Mgr := ao400
abbrev ai404 : Mgr := {ai403 with ops := ai403.ops+1}
abbrev ao404 : Mgr := {ai404 with ops := ai404.ops+1}
theorem a404 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.xor 0 28 ai404 28 ao404 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 0) (b0 := 28) (r := 28) (op := PCSDD.BOp.xor) (m := ai404) (by decide) (by rfl)
abbrev ai405 : Mgr := ao404
abbrev ao405 : Mgr := {ai405 with ops := ai405.ops+1}
theorem a405 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.xor 0 1 ai405 1 ao405 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 0) (b0 := 1) (r := 1) (op := PCSDD.BOp.xor) (m := ai405) (by decide) (by rfl)
abbrev an403 : Mgr := ao405
abbrev ao403 : Mgr := {an403 with memo := ((PCSDD.BOp.xor,0,30),30)::an403.memo}
theorem a403 : ApplyCertificate 12 DEFAULT_LIMITS 19 PCSDD.BOp.xor 0 30 ai403 30 ao403 := by
  exact ApplyCertificate.branch (fuel := 18) (a0 := 0) (b0 := 30) (lo := 28) (hi := 1) (r := 30) (op := PCSDD.BOp.xor) (m := ai403) (m1 := ao404) (m2 := ao405) (m3 := an403) (by decide) (by rfl) (by decide) a404 a405 (by rfl)
abbrev an399 : Mgr := ao403
abbrev ao399 : Mgr := {an399 with memo := ((PCSDD.BOp.xor,0,31),31)::an399.memo}
theorem a399 : ApplyCertificate 12 DEFAULT_LIMITS 20 PCSDD.BOp.xor 0 31 ai399 31 ao399 := by
  exact ApplyCertificate.branch (fuel := 19) (a0 := 0) (b0 := 31) (lo := 25) (hi := 30) (r := 31) (op := PCSDD.BOp.xor) (m := ai399) (m1 := ao400) (m2 := ao403) (m3 := an399) (by decide) (by rfl) (by decide) a400 a403 (by rfl)
abbrev an393 : Mgr := ao399
abbrev ao393 : Mgr := {an393 with memo := ((PCSDD.BOp.xor,0,32),32)::an393.memo}
theorem a393 : ApplyCertificate 12 DEFAULT_LIMITS 21 PCSDD.BOp.xor 0 32 ai393 32 ao393 := by
  exact ApplyCertificate.branch (fuel := 20) (a0 := 0) (b0 := 32) (lo := 29) (hi := 31) (r := 32) (op := PCSDD.BOp.xor) (m := ai393) (m1 := ao394) (m2 := ao399) (m3 := an393) (by decide) (by rfl) (by decide) a394 a399 (by rfl)
abbrev ai406 : Mgr := ao393
abbrev ai407 : Mgr := {ai406 with ops := ai406.ops+1}
abbrev ai408 : Mgr := {ai407 with ops := ai407.ops+1}
abbrev ai409 : Mgr := {ai408 with ops := ai408.ops+1}
abbrev ao409 : Mgr := {ai409 with ops := ai409.ops+1}
theorem a409 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.xor 0 0 ai409 0 ao409 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 0) (b0 := 0) (r := 0) (op := PCSDD.BOp.xor) (m := ai409) (by decide) (by rfl)
abbrev ai410 : Mgr := ao409
abbrev ao410 : Mgr := {ai410 with ops := ai410.ops+1}
theorem a410 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.xor 0 1 ai410 1 ao410 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 0) (b0 := 1) (r := 1) (op := PCSDD.BOp.xor) (m := ai410) (by decide) (by rfl)
abbrev an408 : Mgr := ao410
abbrev ao408 : Mgr := {an408 with memo := ((PCSDD.BOp.xor,0,22),22)::an408.memo}
theorem a408 : ApplyCertificate 12 DEFAULT_LIMITS 19 PCSDD.BOp.xor 0 22 ai408 22 ao408 := by
  exact ApplyCertificate.branch (fuel := 18) (a0 := 0) (b0 := 22) (lo := 0) (hi := 1) (r := 22) (op := PCSDD.BOp.xor) (m := ai408) (m1 := ao409) (m2 := ao410) (m3 := an408) (by decide) (by rfl) (by decide) a409 a410 (by rfl)
abbrev ai411 : Mgr := ao408
abbrev ai412 : Mgr := {ai411 with ops := ai411.ops+1}
abbrev ao412 : Mgr := {ai412 with ops := ai412.ops+1}
theorem a412 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.xor 0 28 ai412 28 ao412 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 0) (b0 := 28) (r := 28) (op := PCSDD.BOp.xor) (m := ai412) (by decide) (by rfl)
abbrev ai413 : Mgr := ao412
abbrev ao413 : Mgr := {ai413 with ops := ai413.ops+1}
theorem a413 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.xor 0 1 ai413 1 ao413 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 0) (b0 := 1) (r := 1) (op := PCSDD.BOp.xor) (m := ai413) (by decide) (by rfl)
abbrev an411 : Mgr := ao413
abbrev ao411 : Mgr := {an411 with memo := ((PCSDD.BOp.xor,0,33),33)::an411.memo}
theorem a411 : ApplyCertificate 12 DEFAULT_LIMITS 19 PCSDD.BOp.xor 0 33 ai411 33 ao411 := by
  exact ApplyCertificate.branch (fuel := 18) (a0 := 0) (b0 := 33) (lo := 28) (hi := 1) (r := 33) (op := PCSDD.BOp.xor) (m := ai411) (m1 := ao412) (m2 := ao413) (m3 := an411) (by decide) (by rfl) (by decide) a412 a413 (by rfl)
abbrev an407 : Mgr := ao411
abbrev ao407 : Mgr := {an407 with memo := ((PCSDD.BOp.xor,0,34),34)::an407.memo}
theorem a407 : ApplyCertificate 12 DEFAULT_LIMITS 20 PCSDD.BOp.xor 0 34 ai407 34 ao407 := by
  exact ApplyCertificate.branch (fuel := 19) (a0 := 0) (b0 := 34) (lo := 22) (hi := 33) (r := 34) (op := PCSDD.BOp.xor) (m := ai407) (m1 := ao408) (m2 := ao411) (m3 := an407) (by decide) (by rfl) (by decide) a408 a411 (by rfl)
abbrev ai414 : Mgr := ao407
abbrev ai415 : Mgr := {ai414 with ops := ai414.ops+1}
abbrev ai416 : Mgr := {ai415 with ops := ai415.ops+1}
abbrev ao416 : Mgr := {ai416 with ops := ai416.ops+1}
theorem a416 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.xor 0 25 ai416 25 ao416 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 0) (b0 := 25) (r := 25) (op := PCSDD.BOp.xor) (m := ai416) (by decide) (by rfl)
abbrev ai417 : Mgr := ao416
abbrev ao417 : Mgr := {ai417 with ops := ai417.ops+1}
theorem a417 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.xor 0 1 ai417 1 ao417 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 0) (b0 := 1) (r := 1) (op := PCSDD.BOp.xor) (m := ai417) (by decide) (by rfl)
abbrev an415 : Mgr := ao417
abbrev ao415 : Mgr := {an415 with memo := ((PCSDD.BOp.xor,0,35),35)::an415.memo}
theorem a415 : ApplyCertificate 12 DEFAULT_LIMITS 19 PCSDD.BOp.xor 0 35 ai415 35 ao415 := by
  exact ApplyCertificate.branch (fuel := 18) (a0 := 0) (b0 := 35) (lo := 25) (hi := 1) (r := 35) (op := PCSDD.BOp.xor) (m := ai415) (m1 := ao416) (m2 := ao417) (m3 := an415) (by decide) (by rfl) (by decide) a416 a417 (by rfl)
abbrev ai418 : Mgr := ao415
abbrev ai419 : Mgr := {ai418 with ops := ai418.ops+1}
abbrev ao419 : Mgr := {ai419 with ops := ai419.ops+1}
theorem a419 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.xor 0 30 ai419 30 ao419 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 0) (b0 := 30) (r := 30) (op := PCSDD.BOp.xor) (m := ai419) (by decide) (by rfl)
abbrev ai420 : Mgr := ao419
abbrev ao420 : Mgr := {ai420 with ops := ai420.ops+1}
theorem a420 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.xor 0 1 ai420 1 ao420 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 0) (b0 := 1) (r := 1) (op := PCSDD.BOp.xor) (m := ai420) (by decide) (by rfl)
abbrev an418 : Mgr := ao420
abbrev ao418 : Mgr := {an418 with memo := ((PCSDD.BOp.xor,0,36),36)::an418.memo}
theorem a418 : ApplyCertificate 12 DEFAULT_LIMITS 19 PCSDD.BOp.xor 0 36 ai418 36 ao418 := by
  exact ApplyCertificate.branch (fuel := 18) (a0 := 0) (b0 := 36) (lo := 30) (hi := 1) (r := 36) (op := PCSDD.BOp.xor) (m := ai418) (m1 := ao419) (m2 := ao420) (m3 := an418) (by decide) (by rfl) (by decide) a419 a420 (by rfl)
abbrev an414 : Mgr := ao418
abbrev ao414 : Mgr := {an414 with memo := ((PCSDD.BOp.xor,0,37),37)::an414.memo}
theorem a414 : ApplyCertificate 12 DEFAULT_LIMITS 20 PCSDD.BOp.xor 0 37 ai414 37 ao414 := by
  exact ApplyCertificate.branch (fuel := 19) (a0 := 0) (b0 := 37) (lo := 35) (hi := 36) (r := 37) (op := PCSDD.BOp.xor) (m := ai414) (m1 := ao415) (m2 := ao418) (m3 := an414) (by decide) (by rfl) (by decide) a415 a418 (by rfl)
abbrev an406 : Mgr := ao414
abbrev ao406 : Mgr := {an406 with memo := ((PCSDD.BOp.xor,0,38),38)::an406.memo}
theorem a406 : ApplyCertificate 12 DEFAULT_LIMITS 21 PCSDD.BOp.xor 0 38 ai406 38 ao406 := by
  exact ApplyCertificate.branch (fuel := 20) (a0 := 0) (b0 := 38) (lo := 34) (hi := 37) (r := 38) (op := PCSDD.BOp.xor) (m := ai406) (m1 := ao407) (m2 := ao414) (m3 := an406) (by decide) (by rfl) (by decide) a407 a414 (by rfl)
abbrev an392 : Mgr := ao406
abbrev ao392 : Mgr := {an392 with memo := ((PCSDD.BOp.xor,0,39),39)::an392.memo}
theorem a392 : ApplyCertificate 12 DEFAULT_LIMITS 22 PCSDD.BOp.xor 0 39 ai392 39 ao392 := by
  exact ApplyCertificate.branch (fuel := 21) (a0 := 0) (b0 := 39) (lo := 32) (hi := 38) (r := 39) (op := PCSDD.BOp.xor) (m := ai392) (m1 := ao393) (m2 := ao406) (m3 := an392) (by decide) (by rfl) (by decide) a393 a406 (by rfl)
abbrev ai421 : Mgr := ao392
abbrev ai422 : Mgr := {ai421 with ops := ai421.ops+1}
abbrev ai423 : Mgr := {ai422 with ops := ai422.ops+1}
abbrev ai424 : Mgr := {ai423 with ops := ai423.ops+1}
abbrev ai425 : Mgr := {ai424 with ops := ai424.ops+1}
abbrev ao425 : Mgr := {ai425 with ops := ai425.ops+1}
theorem a425 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.xor 0 0 ai425 0 ao425 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 0) (b0 := 0) (r := 0) (op := PCSDD.BOp.xor) (m := ai425) (by decide) (by rfl)
abbrev ai426 : Mgr := ao425
abbrev ao426 : Mgr := {ai426 with ops := ai426.ops+1}
theorem a426 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.xor 0 1 ai426 1 ao426 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 0) (b0 := 1) (r := 1) (op := PCSDD.BOp.xor) (m := ai426) (by decide) (by rfl)
abbrev an424 : Mgr := ao426
abbrev ao424 : Mgr := {an424 with memo := ((PCSDD.BOp.xor,0,9),9)::an424.memo}
theorem a424 : ApplyCertificate 12 DEFAULT_LIMITS 19 PCSDD.BOp.xor 0 9 ai424 9 ao424 := by
  exact ApplyCertificate.branch (fuel := 18) (a0 := 0) (b0 := 9) (lo := 0) (hi := 1) (r := 9) (op := PCSDD.BOp.xor) (m := ai424) (m1 := ao425) (m2 := ao426) (m3 := an424) (by decide) (by rfl) (by decide) a425 a426 (by rfl)
abbrev ai427 : Mgr := ao424
abbrev ai428 : Mgr := {ai427 with ops := ai427.ops+1}
abbrev ao428 : Mgr := {ai428 with ops := ai428.ops+1}
theorem a428 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.xor 0 28 ai428 28 ao428 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 0) (b0 := 28) (r := 28) (op := PCSDD.BOp.xor) (m := ai428) (by decide) (by rfl)
abbrev ai429 : Mgr := ao428
abbrev ao429 : Mgr := {ai429 with ops := ai429.ops+1}
theorem a429 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.xor 0 1 ai429 1 ao429 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 0) (b0 := 1) (r := 1) (op := PCSDD.BOp.xor) (m := ai429) (by decide) (by rfl)
abbrev an427 : Mgr := ao429
abbrev ao427 : Mgr := {an427 with memo := ((PCSDD.BOp.xor,0,40),40)::an427.memo}
theorem a427 : ApplyCertificate 12 DEFAULT_LIMITS 19 PCSDD.BOp.xor 0 40 ai427 40 ao427 := by
  exact ApplyCertificate.branch (fuel := 18) (a0 := 0) (b0 := 40) (lo := 28) (hi := 1) (r := 40) (op := PCSDD.BOp.xor) (m := ai427) (m1 := ao428) (m2 := ao429) (m3 := an427) (by decide) (by rfl) (by decide) a428 a429 (by rfl)
abbrev an423 : Mgr := ao427
abbrev ao423 : Mgr := {an423 with memo := ((PCSDD.BOp.xor,0,41),41)::an423.memo}
theorem a423 : ApplyCertificate 12 DEFAULT_LIMITS 20 PCSDD.BOp.xor 0 41 ai423 41 ao423 := by
  exact ApplyCertificate.branch (fuel := 19) (a0 := 0) (b0 := 41) (lo := 9) (hi := 40) (r := 41) (op := PCSDD.BOp.xor) (m := ai423) (m1 := ao424) (m2 := ao427) (m3 := an423) (by decide) (by rfl) (by decide) a424 a427 (by rfl)
abbrev ai430 : Mgr := ao423
abbrev ai431 : Mgr := {ai430 with ops := ai430.ops+1}
abbrev ai432 : Mgr := {ai431 with ops := ai431.ops+1}
abbrev ao432 : Mgr := {ai432 with ops := ai432.ops+1}
theorem a432 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.xor 0 25 ai432 25 ao432 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 0) (b0 := 25) (r := 25) (op := PCSDD.BOp.xor) (m := ai432) (by decide) (by rfl)
abbrev ai433 : Mgr := ao432
abbrev ao433 : Mgr := {ai433 with ops := ai433.ops+1}
theorem a433 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.xor 0 1 ai433 1 ao433 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 0) (b0 := 1) (r := 1) (op := PCSDD.BOp.xor) (m := ai433) (by decide) (by rfl)
abbrev an431 : Mgr := ao433
abbrev ao431 : Mgr := {an431 with memo := ((PCSDD.BOp.xor,0,42),42)::an431.memo}
theorem a431 : ApplyCertificate 12 DEFAULT_LIMITS 19 PCSDD.BOp.xor 0 42 ai431 42 ao431 := by
  exact ApplyCertificate.branch (fuel := 18) (a0 := 0) (b0 := 42) (lo := 25) (hi := 1) (r := 42) (op := PCSDD.BOp.xor) (m := ai431) (m1 := ao432) (m2 := ao433) (m3 := an431) (by decide) (by rfl) (by decide) a432 a433 (by rfl)
abbrev ai434 : Mgr := ao431
abbrev ai435 : Mgr := {ai434 with ops := ai434.ops+1}
abbrev ao435 : Mgr := {ai435 with ops := ai435.ops+1}
theorem a435 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.xor 0 30 ai435 30 ao435 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 0) (b0 := 30) (r := 30) (op := PCSDD.BOp.xor) (m := ai435) (by decide) (by rfl)
abbrev ai436 : Mgr := ao435
abbrev ao436 : Mgr := {ai436 with ops := ai436.ops+1}
theorem a436 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.xor 0 1 ai436 1 ao436 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 0) (b0 := 1) (r := 1) (op := PCSDD.BOp.xor) (m := ai436) (by decide) (by rfl)
abbrev an434 : Mgr := ao436
abbrev ao434 : Mgr := {an434 with memo := ((PCSDD.BOp.xor,0,43),43)::an434.memo}
theorem a434 : ApplyCertificate 12 DEFAULT_LIMITS 19 PCSDD.BOp.xor 0 43 ai434 43 ao434 := by
  exact ApplyCertificate.branch (fuel := 18) (a0 := 0) (b0 := 43) (lo := 30) (hi := 1) (r := 43) (op := PCSDD.BOp.xor) (m := ai434) (m1 := ao435) (m2 := ao436) (m3 := an434) (by decide) (by rfl) (by decide) a435 a436 (by rfl)
abbrev an430 : Mgr := ao434
abbrev ao430 : Mgr := {an430 with memo := ((PCSDD.BOp.xor,0,44),44)::an430.memo}
theorem a430 : ApplyCertificate 12 DEFAULT_LIMITS 20 PCSDD.BOp.xor 0 44 ai430 44 ao430 := by
  exact ApplyCertificate.branch (fuel := 19) (a0 := 0) (b0 := 44) (lo := 42) (hi := 43) (r := 44) (op := PCSDD.BOp.xor) (m := ai430) (m1 := ao431) (m2 := ao434) (m3 := an430) (by decide) (by rfl) (by decide) a431 a434 (by rfl)
abbrev an422 : Mgr := ao430
abbrev ao422 : Mgr := {an422 with memo := ((PCSDD.BOp.xor,0,45),45)::an422.memo}
theorem a422 : ApplyCertificate 12 DEFAULT_LIMITS 21 PCSDD.BOp.xor 0 45 ai422 45 ao422 := by
  exact ApplyCertificate.branch (fuel := 20) (a0 := 0) (b0 := 45) (lo := 41) (hi := 44) (r := 45) (op := PCSDD.BOp.xor) (m := ai422) (m1 := ao423) (m2 := ao430) (m3 := an422) (by decide) (by rfl) (by decide) a423 a430 (by rfl)
abbrev ai437 : Mgr := ao422
abbrev ai438 : Mgr := {ai437 with ops := ai437.ops+1}
abbrev ai439 : Mgr := {ai438 with ops := ai438.ops+1}
abbrev ai440 : Mgr := {ai439 with ops := ai439.ops+1}
abbrev ao440 : Mgr := {ai440 with ops := ai440.ops+1}
theorem a440 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.xor 0 22 ai440 22 ao440 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 0) (b0 := 22) (r := 22) (op := PCSDD.BOp.xor) (m := ai440) (by decide) (by rfl)
abbrev ai441 : Mgr := ao440
abbrev ao441 : Mgr := {ai441 with ops := ai441.ops+1}
theorem a441 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.xor 0 1 ai441 1 ao441 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 0) (b0 := 1) (r := 1) (op := PCSDD.BOp.xor) (m := ai441) (by decide) (by rfl)
abbrev an439 : Mgr := ao441
abbrev ao439 : Mgr := {an439 with memo := ((PCSDD.BOp.xor,0,46),46)::an439.memo}
theorem a439 : ApplyCertificate 12 DEFAULT_LIMITS 19 PCSDD.BOp.xor 0 46 ai439 46 ao439 := by
  exact ApplyCertificate.branch (fuel := 18) (a0 := 0) (b0 := 46) (lo := 22) (hi := 1) (r := 46) (op := PCSDD.BOp.xor) (m := ai439) (m1 := ao440) (m2 := ao441) (m3 := an439) (by decide) (by rfl) (by decide) a440 a441 (by rfl)
abbrev ai442 : Mgr := ao439
abbrev ai443 : Mgr := {ai442 with ops := ai442.ops+1}
abbrev ao443 : Mgr := {ai443 with ops := ai443.ops+1}
theorem a443 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.xor 0 33 ai443 33 ao443 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 0) (b0 := 33) (r := 33) (op := PCSDD.BOp.xor) (m := ai443) (by decide) (by rfl)
abbrev ai444 : Mgr := ao443
abbrev ao444 : Mgr := {ai444 with ops := ai444.ops+1}
theorem a444 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.xor 0 1 ai444 1 ao444 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 0) (b0 := 1) (r := 1) (op := PCSDD.BOp.xor) (m := ai444) (by decide) (by rfl)
abbrev an442 : Mgr := ao444
abbrev ao442 : Mgr := {an442 with memo := ((PCSDD.BOp.xor,0,47),47)::an442.memo}
theorem a442 : ApplyCertificate 12 DEFAULT_LIMITS 19 PCSDD.BOp.xor 0 47 ai442 47 ao442 := by
  exact ApplyCertificate.branch (fuel := 18) (a0 := 0) (b0 := 47) (lo := 33) (hi := 1) (r := 47) (op := PCSDD.BOp.xor) (m := ai442) (m1 := ao443) (m2 := ao444) (m3 := an442) (by decide) (by rfl) (by decide) a443 a444 (by rfl)
abbrev an438 : Mgr := ao442
abbrev ao438 : Mgr := {an438 with memo := ((PCSDD.BOp.xor,0,48),48)::an438.memo}
theorem a438 : ApplyCertificate 12 DEFAULT_LIMITS 20 PCSDD.BOp.xor 0 48 ai438 48 ao438 := by
  exact ApplyCertificate.branch (fuel := 19) (a0 := 0) (b0 := 48) (lo := 46) (hi := 47) (r := 48) (op := PCSDD.BOp.xor) (m := ai438) (m1 := ao439) (m2 := ao442) (m3 := an438) (by decide) (by rfl) (by decide) a439 a442 (by rfl)
abbrev ai445 : Mgr := ao438
abbrev ai446 : Mgr := {ai445 with ops := ai445.ops+1}
abbrev ai447 : Mgr := {ai446 with ops := ai446.ops+1}
abbrev ao447 : Mgr := {ai447 with ops := ai447.ops+1}
theorem a447 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.xor 0 35 ai447 35 ao447 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 0) (b0 := 35) (r := 35) (op := PCSDD.BOp.xor) (m := ai447) (by decide) (by rfl)
abbrev ai448 : Mgr := ao447
abbrev ao448 : Mgr := {ai448 with ops := ai448.ops+1}
theorem a448 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.xor 0 1 ai448 1 ao448 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 0) (b0 := 1) (r := 1) (op := PCSDD.BOp.xor) (m := ai448) (by decide) (by rfl)
abbrev an446 : Mgr := ao448
abbrev ao446 : Mgr := {an446 with memo := ((PCSDD.BOp.xor,0,49),49)::an446.memo}
theorem a446 : ApplyCertificate 12 DEFAULT_LIMITS 19 PCSDD.BOp.xor 0 49 ai446 49 ao446 := by
  exact ApplyCertificate.branch (fuel := 18) (a0 := 0) (b0 := 49) (lo := 35) (hi := 1) (r := 49) (op := PCSDD.BOp.xor) (m := ai446) (m1 := ao447) (m2 := ao448) (m3 := an446) (by decide) (by rfl) (by decide) a447 a448 (by rfl)
abbrev ai449 : Mgr := ao446
abbrev ai450 : Mgr := {ai449 with ops := ai449.ops+1}
abbrev ao450 : Mgr := {ai450 with ops := ai450.ops+1}
theorem a450 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.xor 0 36 ai450 36 ao450 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 0) (b0 := 36) (r := 36) (op := PCSDD.BOp.xor) (m := ai450) (by decide) (by rfl)
abbrev ai451 : Mgr := ao450
abbrev ao451 : Mgr := {ai451 with ops := ai451.ops+1}
theorem a451 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.xor 0 1 ai451 1 ao451 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 0) (b0 := 1) (r := 1) (op := PCSDD.BOp.xor) (m := ai451) (by decide) (by rfl)
abbrev an449 : Mgr := ao451
abbrev ao449 : Mgr := {an449 with memo := ((PCSDD.BOp.xor,0,50),50)::an449.memo}
theorem a449 : ApplyCertificate 12 DEFAULT_LIMITS 19 PCSDD.BOp.xor 0 50 ai449 50 ao449 := by
  exact ApplyCertificate.branch (fuel := 18) (a0 := 0) (b0 := 50) (lo := 36) (hi := 1) (r := 50) (op := PCSDD.BOp.xor) (m := ai449) (m1 := ao450) (m2 := ao451) (m3 := an449) (by decide) (by rfl) (by decide) a450 a451 (by rfl)
abbrev an445 : Mgr := ao449
abbrev ao445 : Mgr := {an445 with memo := ((PCSDD.BOp.xor,0,51),51)::an445.memo}
theorem a445 : ApplyCertificate 12 DEFAULT_LIMITS 20 PCSDD.BOp.xor 0 51 ai445 51 ao445 := by
  exact ApplyCertificate.branch (fuel := 19) (a0 := 0) (b0 := 51) (lo := 49) (hi := 50) (r := 51) (op := PCSDD.BOp.xor) (m := ai445) (m1 := ao446) (m2 := ao449) (m3 := an445) (by decide) (by rfl) (by decide) a446 a449 (by rfl)
abbrev an437 : Mgr := ao445
abbrev ao437 : Mgr := {an437 with memo := ((PCSDD.BOp.xor,0,52),52)::an437.memo}
theorem a437 : ApplyCertificate 12 DEFAULT_LIMITS 21 PCSDD.BOp.xor 0 52 ai437 52 ao437 := by
  exact ApplyCertificate.branch (fuel := 20) (a0 := 0) (b0 := 52) (lo := 48) (hi := 51) (r := 52) (op := PCSDD.BOp.xor) (m := ai437) (m1 := ao438) (m2 := ao445) (m3 := an437) (by decide) (by rfl) (by decide) a438 a445 (by rfl)
abbrev an421 : Mgr := ao437
abbrev ao421 : Mgr := {an421 with memo := ((PCSDD.BOp.xor,0,53),53)::an421.memo}
theorem a421 : ApplyCertificate 12 DEFAULT_LIMITS 22 PCSDD.BOp.xor 0 53 ai421 53 ao421 := by
  exact ApplyCertificate.branch (fuel := 21) (a0 := 0) (b0 := 53) (lo := 45) (hi := 52) (r := 53) (op := PCSDD.BOp.xor) (m := ai421) (m1 := ao422) (m2 := ao437) (m3 := an421) (by decide) (by rfl) (by decide) a422 a437 (by rfl)
abbrev an391 : Mgr := ao421
abbrev ao391 : Mgr := {an391 with memo := ((PCSDD.BOp.xor,0,54),54)::an391.memo}
theorem a391 : ApplyCertificate 12 DEFAULT_LIMITS 23 PCSDD.BOp.xor 0 54 ai391 54 ao391 := by
  exact ApplyCertificate.branch (fuel := 22) (a0 := 0) (b0 := 54) (lo := 39) (hi := 53) (r := 54) (op := PCSDD.BOp.xor) (m := ai391) (m1 := ao392) (m2 := ao421) (m3 := an391) (by decide) (by rfl) (by decide) a392 a421 (by rfl)
abbrev ai452 : Mgr := ao391
abbrev ai453 : Mgr := {ai452 with ops := ai452.ops+1}
abbrev ai454 : Mgr := {ai453 with ops := ai453.ops+1}
abbrev ai455 : Mgr := {ai454 with ops := ai454.ops+1}
abbrev ai456 : Mgr := {ai455 with ops := ai455.ops+1}
abbrev ai457 : Mgr := {ai456 with ops := ai456.ops+1}
abbrev ao457 : Mgr := {ai457 with ops := ai457.ops+1}
theorem a457 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.xor 0 0 ai457 0 ao457 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 0) (b0 := 0) (r := 0) (op := PCSDD.BOp.xor) (m := ai457) (by decide) (by rfl)
abbrev ai458 : Mgr := ao457
abbrev ao458 : Mgr := {ai458 with ops := ai458.ops+1}
theorem a458 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.xor 0 1 ai458 1 ao458 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 0) (b0 := 1) (r := 1) (op := PCSDD.BOp.xor) (m := ai458) (by decide) (by rfl)
abbrev an456 : Mgr := ao458
abbrev ao456 : Mgr := {an456 with memo := ((PCSDD.BOp.xor,0,6),6)::an456.memo}
theorem a456 : ApplyCertificate 12 DEFAULT_LIMITS 19 PCSDD.BOp.xor 0 6 ai456 6 ao456 := by
  exact ApplyCertificate.branch (fuel := 18) (a0 := 0) (b0 := 6) (lo := 0) (hi := 1) (r := 6) (op := PCSDD.BOp.xor) (m := ai456) (m1 := ao457) (m2 := ao458) (m3 := an456) (by decide) (by rfl) (by decide) a457 a458 (by rfl)
abbrev ai459 : Mgr := ao456
abbrev ai460 : Mgr := {ai459 with ops := ai459.ops+1}
abbrev ao460 : Mgr := {ai460 with ops := ai460.ops+1}
theorem a460 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.xor 0 28 ai460 28 ao460 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 0) (b0 := 28) (r := 28) (op := PCSDD.BOp.xor) (m := ai460) (by decide) (by rfl)
abbrev ai461 : Mgr := ao460
abbrev ao461 : Mgr := {ai461 with ops := ai461.ops+1}
theorem a461 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.xor 0 1 ai461 1 ao461 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 0) (b0 := 1) (r := 1) (op := PCSDD.BOp.xor) (m := ai461) (by decide) (by rfl)
abbrev an459 : Mgr := ao461
abbrev ao459 : Mgr := {an459 with memo := ((PCSDD.BOp.xor,0,55),55)::an459.memo}
theorem a459 : ApplyCertificate 12 DEFAULT_LIMITS 19 PCSDD.BOp.xor 0 55 ai459 55 ao459 := by
  exact ApplyCertificate.branch (fuel := 18) (a0 := 0) (b0 := 55) (lo := 28) (hi := 1) (r := 55) (op := PCSDD.BOp.xor) (m := ai459) (m1 := ao460) (m2 := ao461) (m3 := an459) (by decide) (by rfl) (by decide) a460 a461 (by rfl)
abbrev an455 : Mgr := ao459
abbrev ao455 : Mgr := {an455 with memo := ((PCSDD.BOp.xor,0,56),56)::an455.memo}
theorem a455 : ApplyCertificate 12 DEFAULT_LIMITS 20 PCSDD.BOp.xor 0 56 ai455 56 ao455 := by
  exact ApplyCertificate.branch (fuel := 19) (a0 := 0) (b0 := 56) (lo := 6) (hi := 55) (r := 56) (op := PCSDD.BOp.xor) (m := ai455) (m1 := ao456) (m2 := ao459) (m3 := an455) (by decide) (by rfl) (by decide) a456 a459 (by rfl)
abbrev ai462 : Mgr := ao455
abbrev ai463 : Mgr := {ai462 with ops := ai462.ops+1}
abbrev ai464 : Mgr := {ai463 with ops := ai463.ops+1}
abbrev ao464 : Mgr := {ai464 with ops := ai464.ops+1}
theorem a464 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.xor 0 25 ai464 25 ao464 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 0) (b0 := 25) (r := 25) (op := PCSDD.BOp.xor) (m := ai464) (by decide) (by rfl)
abbrev ai465 : Mgr := ao464
abbrev ao465 : Mgr := {ai465 with ops := ai465.ops+1}
theorem a465 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.xor 0 1 ai465 1 ao465 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 0) (b0 := 1) (r := 1) (op := PCSDD.BOp.xor) (m := ai465) (by decide) (by rfl)
abbrev an463 : Mgr := ao465
abbrev ao463 : Mgr := {an463 with memo := ((PCSDD.BOp.xor,0,57),57)::an463.memo}
theorem a463 : ApplyCertificate 12 DEFAULT_LIMITS 19 PCSDD.BOp.xor 0 57 ai463 57 ao463 := by
  exact ApplyCertificate.branch (fuel := 18) (a0 := 0) (b0 := 57) (lo := 25) (hi := 1) (r := 57) (op := PCSDD.BOp.xor) (m := ai463) (m1 := ao464) (m2 := ao465) (m3 := an463) (by decide) (by rfl) (by decide) a464 a465 (by rfl)
abbrev ai466 : Mgr := ao463
abbrev ai467 : Mgr := {ai466 with ops := ai466.ops+1}
abbrev ao467 : Mgr := {ai467 with ops := ai467.ops+1}
theorem a467 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.xor 0 30 ai467 30 ao467 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 0) (b0 := 30) (r := 30) (op := PCSDD.BOp.xor) (m := ai467) (by decide) (by rfl)
abbrev ai468 : Mgr := ao467
abbrev ao468 : Mgr := {ai468 with ops := ai468.ops+1}
theorem a468 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.xor 0 1 ai468 1 ao468 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 0) (b0 := 1) (r := 1) (op := PCSDD.BOp.xor) (m := ai468) (by decide) (by rfl)
abbrev an466 : Mgr := ao468
abbrev ao466 : Mgr := {an466 with memo := ((PCSDD.BOp.xor,0,58),58)::an466.memo}
theorem a466 : ApplyCertificate 12 DEFAULT_LIMITS 19 PCSDD.BOp.xor 0 58 ai466 58 ao466 := by
  exact ApplyCertificate.branch (fuel := 18) (a0 := 0) (b0 := 58) (lo := 30) (hi := 1) (r := 58) (op := PCSDD.BOp.xor) (m := ai466) (m1 := ao467) (m2 := ao468) (m3 := an466) (by decide) (by rfl) (by decide) a467 a468 (by rfl)
abbrev an462 : Mgr := ao466
abbrev ao462 : Mgr := {an462 with memo := ((PCSDD.BOp.xor,0,59),59)::an462.memo}
theorem a462 : ApplyCertificate 12 DEFAULT_LIMITS 20 PCSDD.BOp.xor 0 59 ai462 59 ao462 := by
  exact ApplyCertificate.branch (fuel := 19) (a0 := 0) (b0 := 59) (lo := 57) (hi := 58) (r := 59) (op := PCSDD.BOp.xor) (m := ai462) (m1 := ao463) (m2 := ao466) (m3 := an462) (by decide) (by rfl) (by decide) a463 a466 (by rfl)
abbrev an454 : Mgr := ao462
abbrev ao454 : Mgr := {an454 with memo := ((PCSDD.BOp.xor,0,60),60)::an454.memo}
theorem a454 : ApplyCertificate 12 DEFAULT_LIMITS 21 PCSDD.BOp.xor 0 60 ai454 60 ao454 := by
  exact ApplyCertificate.branch (fuel := 20) (a0 := 0) (b0 := 60) (lo := 56) (hi := 59) (r := 60) (op := PCSDD.BOp.xor) (m := ai454) (m1 := ao455) (m2 := ao462) (m3 := an454) (by decide) (by rfl) (by decide) a455 a462 (by rfl)
abbrev ai469 : Mgr := ao454
abbrev ai470 : Mgr := {ai469 with ops := ai469.ops+1}
abbrev ai471 : Mgr := {ai470 with ops := ai470.ops+1}
abbrev ai472 : Mgr := {ai471 with ops := ai471.ops+1}
abbrev ao472 : Mgr := {ai472 with ops := ai472.ops+1}
theorem a472 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.xor 0 22 ai472 22 ao472 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 0) (b0 := 22) (r := 22) (op := PCSDD.BOp.xor) (m := ai472) (by decide) (by rfl)
abbrev ai473 : Mgr := ao472
abbrev ao473 : Mgr := {ai473 with ops := ai473.ops+1}
theorem a473 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.xor 0 1 ai473 1 ao473 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 0) (b0 := 1) (r := 1) (op := PCSDD.BOp.xor) (m := ai473) (by decide) (by rfl)
abbrev an471 : Mgr := ao473
abbrev ao471 : Mgr := {an471 with memo := ((PCSDD.BOp.xor,0,61),61)::an471.memo}
theorem a471 : ApplyCertificate 12 DEFAULT_LIMITS 19 PCSDD.BOp.xor 0 61 ai471 61 ao471 := by
  exact ApplyCertificate.branch (fuel := 18) (a0 := 0) (b0 := 61) (lo := 22) (hi := 1) (r := 61) (op := PCSDD.BOp.xor) (m := ai471) (m1 := ao472) (m2 := ao473) (m3 := an471) (by decide) (by rfl) (by decide) a472 a473 (by rfl)
abbrev ai474 : Mgr := ao471
abbrev ai475 : Mgr := {ai474 with ops := ai474.ops+1}
abbrev ao475 : Mgr := {ai475 with ops := ai475.ops+1}
theorem a475 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.xor 0 33 ai475 33 ao475 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 0) (b0 := 33) (r := 33) (op := PCSDD.BOp.xor) (m := ai475) (by decide) (by rfl)
abbrev ai476 : Mgr := ao475
abbrev ao476 : Mgr := {ai476 with ops := ai476.ops+1}
theorem a476 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.xor 0 1 ai476 1 ao476 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 0) (b0 := 1) (r := 1) (op := PCSDD.BOp.xor) (m := ai476) (by decide) (by rfl)
abbrev an474 : Mgr := ao476
abbrev ao474 : Mgr := {an474 with memo := ((PCSDD.BOp.xor,0,62),62)::an474.memo}
theorem a474 : ApplyCertificate 12 DEFAULT_LIMITS 19 PCSDD.BOp.xor 0 62 ai474 62 ao474 := by
  exact ApplyCertificate.branch (fuel := 18) (a0 := 0) (b0 := 62) (lo := 33) (hi := 1) (r := 62) (op := PCSDD.BOp.xor) (m := ai474) (m1 := ao475) (m2 := ao476) (m3 := an474) (by decide) (by rfl) (by decide) a475 a476 (by rfl)
abbrev an470 : Mgr := ao474
abbrev ao470 : Mgr := {an470 with memo := ((PCSDD.BOp.xor,0,63),63)::an470.memo}
theorem a470 : ApplyCertificate 12 DEFAULT_LIMITS 20 PCSDD.BOp.xor 0 63 ai470 63 ao470 := by
  exact ApplyCertificate.branch (fuel := 19) (a0 := 0) (b0 := 63) (lo := 61) (hi := 62) (r := 63) (op := PCSDD.BOp.xor) (m := ai470) (m1 := ao471) (m2 := ao474) (m3 := an470) (by decide) (by rfl) (by decide) a471 a474 (by rfl)
abbrev ai477 : Mgr := ao470
abbrev ai478 : Mgr := {ai477 with ops := ai477.ops+1}
abbrev ai479 : Mgr := {ai478 with ops := ai478.ops+1}
abbrev ao479 : Mgr := {ai479 with ops := ai479.ops+1}
theorem a479 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.xor 0 35 ai479 35 ao479 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 0) (b0 := 35) (r := 35) (op := PCSDD.BOp.xor) (m := ai479) (by decide) (by rfl)
abbrev ai480 : Mgr := ao479
abbrev ao480 : Mgr := {ai480 with ops := ai480.ops+1}
theorem a480 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.xor 0 1 ai480 1 ao480 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 0) (b0 := 1) (r := 1) (op := PCSDD.BOp.xor) (m := ai480) (by decide) (by rfl)
abbrev an478 : Mgr := ao480
abbrev ao478 : Mgr := {an478 with memo := ((PCSDD.BOp.xor,0,64),64)::an478.memo}
theorem a478 : ApplyCertificate 12 DEFAULT_LIMITS 19 PCSDD.BOp.xor 0 64 ai478 64 ao478 := by
  exact ApplyCertificate.branch (fuel := 18) (a0 := 0) (b0 := 64) (lo := 35) (hi := 1) (r := 64) (op := PCSDD.BOp.xor) (m := ai478) (m1 := ao479) (m2 := ao480) (m3 := an478) (by decide) (by rfl) (by decide) a479 a480 (by rfl)
abbrev ai481 : Mgr := ao478
abbrev ai482 : Mgr := {ai481 with ops := ai481.ops+1}
abbrev ao482 : Mgr := {ai482 with ops := ai482.ops+1}
theorem a482 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.xor 0 36 ai482 36 ao482 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 0) (b0 := 36) (r := 36) (op := PCSDD.BOp.xor) (m := ai482) (by decide) (by rfl)
abbrev ai483 : Mgr := ao482
abbrev ao483 : Mgr := {ai483 with ops := ai483.ops+1}
theorem a483 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.xor 0 1 ai483 1 ao483 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 0) (b0 := 1) (r := 1) (op := PCSDD.BOp.xor) (m := ai483) (by decide) (by rfl)
abbrev an481 : Mgr := ao483
abbrev ao481 : Mgr := {an481 with memo := ((PCSDD.BOp.xor,0,65),65)::an481.memo}
theorem a481 : ApplyCertificate 12 DEFAULT_LIMITS 19 PCSDD.BOp.xor 0 65 ai481 65 ao481 := by
  exact ApplyCertificate.branch (fuel := 18) (a0 := 0) (b0 := 65) (lo := 36) (hi := 1) (r := 65) (op := PCSDD.BOp.xor) (m := ai481) (m1 := ao482) (m2 := ao483) (m3 := an481) (by decide) (by rfl) (by decide) a482 a483 (by rfl)
abbrev an477 : Mgr := ao481
abbrev ao477 : Mgr := {an477 with memo := ((PCSDD.BOp.xor,0,66),66)::an477.memo}
theorem a477 : ApplyCertificate 12 DEFAULT_LIMITS 20 PCSDD.BOp.xor 0 66 ai477 66 ao477 := by
  exact ApplyCertificate.branch (fuel := 19) (a0 := 0) (b0 := 66) (lo := 64) (hi := 65) (r := 66) (op := PCSDD.BOp.xor) (m := ai477) (m1 := ao478) (m2 := ao481) (m3 := an477) (by decide) (by rfl) (by decide) a478 a481 (by rfl)
abbrev an469 : Mgr := ao477
abbrev ao469 : Mgr := {an469 with memo := ((PCSDD.BOp.xor,0,67),67)::an469.memo}
theorem a469 : ApplyCertificate 12 DEFAULT_LIMITS 21 PCSDD.BOp.xor 0 67 ai469 67 ao469 := by
  exact ApplyCertificate.branch (fuel := 20) (a0 := 0) (b0 := 67) (lo := 63) (hi := 66) (r := 67) (op := PCSDD.BOp.xor) (m := ai469) (m1 := ao470) (m2 := ao477) (m3 := an469) (by decide) (by rfl) (by decide) a470 a477 (by rfl)
abbrev an453 : Mgr := ao469
abbrev ao453 : Mgr := {an453 with memo := ((PCSDD.BOp.xor,0,68),68)::an453.memo}
theorem a453 : ApplyCertificate 12 DEFAULT_LIMITS 22 PCSDD.BOp.xor 0 68 ai453 68 ao453 := by
  exact ApplyCertificate.branch (fuel := 21) (a0 := 0) (b0 := 68) (lo := 60) (hi := 67) (r := 68) (op := PCSDD.BOp.xor) (m := ai453) (m1 := ao454) (m2 := ao469) (m3 := an453) (by decide) (by rfl) (by decide) a454 a469 (by rfl)
abbrev ai484 : Mgr := ao453
abbrev ai485 : Mgr := {ai484 with ops := ai484.ops+1}
abbrev ai486 : Mgr := {ai485 with ops := ai485.ops+1}
abbrev ai487 : Mgr := {ai486 with ops := ai486.ops+1}
abbrev ai488 : Mgr := {ai487 with ops := ai487.ops+1}
abbrev ao488 : Mgr := {ai488 with ops := ai488.ops+1}
theorem a488 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.xor 0 9 ai488 9 ao488 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 0) (b0 := 9) (r := 9) (op := PCSDD.BOp.xor) (m := ai488) (by decide) (by rfl)
abbrev ai489 : Mgr := ao488
abbrev ao489 : Mgr := {ai489 with ops := ai489.ops+1}
theorem a489 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.xor 0 1 ai489 1 ao489 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 0) (b0 := 1) (r := 1) (op := PCSDD.BOp.xor) (m := ai489) (by decide) (by rfl)
abbrev an487 : Mgr := ao489
abbrev ao487 : Mgr := {an487 with memo := ((PCSDD.BOp.xor,0,11),11)::an487.memo}
theorem a487 : ApplyCertificate 12 DEFAULT_LIMITS 19 PCSDD.BOp.xor 0 11 ai487 11 ao487 := by
  exact ApplyCertificate.branch (fuel := 18) (a0 := 0) (b0 := 11) (lo := 9) (hi := 1) (r := 11) (op := PCSDD.BOp.xor) (m := ai487) (m1 := ao488) (m2 := ao489) (m3 := an487) (by decide) (by rfl) (by decide) a488 a489 (by rfl)
abbrev ai490 : Mgr := ao487
abbrev ai491 : Mgr := {ai490 with ops := ai490.ops+1}
abbrev ao491 : Mgr := {ai491 with ops := ai491.ops+1}
theorem a491 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.xor 0 40 ai491 40 ao491 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 0) (b0 := 40) (r := 40) (op := PCSDD.BOp.xor) (m := ai491) (by decide) (by rfl)
abbrev ai492 : Mgr := ao491
abbrev ao492 : Mgr := {ai492 with ops := ai492.ops+1}
theorem a492 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.xor 0 1 ai492 1 ao492 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 0) (b0 := 1) (r := 1) (op := PCSDD.BOp.xor) (m := ai492) (by decide) (by rfl)
abbrev an490 : Mgr := ao492
abbrev ao490 : Mgr := {an490 with memo := ((PCSDD.BOp.xor,0,69),69)::an490.memo}
theorem a490 : ApplyCertificate 12 DEFAULT_LIMITS 19 PCSDD.BOp.xor 0 69 ai490 69 ao490 := by
  exact ApplyCertificate.branch (fuel := 18) (a0 := 0) (b0 := 69) (lo := 40) (hi := 1) (r := 69) (op := PCSDD.BOp.xor) (m := ai490) (m1 := ao491) (m2 := ao492) (m3 := an490) (by decide) (by rfl) (by decide) a491 a492 (by rfl)
abbrev an486 : Mgr := ao490
abbrev ao486 : Mgr := {an486 with memo := ((PCSDD.BOp.xor,0,70),70)::an486.memo}
theorem a486 : ApplyCertificate 12 DEFAULT_LIMITS 20 PCSDD.BOp.xor 0 70 ai486 70 ao486 := by
  exact ApplyCertificate.branch (fuel := 19) (a0 := 0) (b0 := 70) (lo := 11) (hi := 69) (r := 70) (op := PCSDD.BOp.xor) (m := ai486) (m1 := ao487) (m2 := ao490) (m3 := an486) (by decide) (by rfl) (by decide) a487 a490 (by rfl)
abbrev ai493 : Mgr := ao486
abbrev ai494 : Mgr := {ai493 with ops := ai493.ops+1}
abbrev ai495 : Mgr := {ai494 with ops := ai494.ops+1}
abbrev ao495 : Mgr := {ai495 with ops := ai495.ops+1}
theorem a495 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.xor 0 42 ai495 42 ao495 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 0) (b0 := 42) (r := 42) (op := PCSDD.BOp.xor) (m := ai495) (by decide) (by rfl)
abbrev ai496 : Mgr := ao495
abbrev ao496 : Mgr := {ai496 with ops := ai496.ops+1}
theorem a496 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.xor 0 1 ai496 1 ao496 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 0) (b0 := 1) (r := 1) (op := PCSDD.BOp.xor) (m := ai496) (by decide) (by rfl)
abbrev an494 : Mgr := ao496
abbrev ao494 : Mgr := {an494 with memo := ((PCSDD.BOp.xor,0,71),71)::an494.memo}
theorem a494 : ApplyCertificate 12 DEFAULT_LIMITS 19 PCSDD.BOp.xor 0 71 ai494 71 ao494 := by
  exact ApplyCertificate.branch (fuel := 18) (a0 := 0) (b0 := 71) (lo := 42) (hi := 1) (r := 71) (op := PCSDD.BOp.xor) (m := ai494) (m1 := ao495) (m2 := ao496) (m3 := an494) (by decide) (by rfl) (by decide) a495 a496 (by rfl)
abbrev ai497 : Mgr := ao494
abbrev ai498 : Mgr := {ai497 with ops := ai497.ops+1}
abbrev ao498 : Mgr := {ai498 with ops := ai498.ops+1}
theorem a498 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.xor 0 43 ai498 43 ao498 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 0) (b0 := 43) (r := 43) (op := PCSDD.BOp.xor) (m := ai498) (by decide) (by rfl)
abbrev ai499 : Mgr := ao498
abbrev ao499 : Mgr := {ai499 with ops := ai499.ops+1}
theorem a499 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.xor 0 1 ai499 1 ao499 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 0) (b0 := 1) (r := 1) (op := PCSDD.BOp.xor) (m := ai499) (by decide) (by rfl)
abbrev an497 : Mgr := ao499
abbrev ao497 : Mgr := {an497 with memo := ((PCSDD.BOp.xor,0,72),72)::an497.memo}
theorem a497 : ApplyCertificate 12 DEFAULT_LIMITS 19 PCSDD.BOp.xor 0 72 ai497 72 ao497 := by
  exact ApplyCertificate.branch (fuel := 18) (a0 := 0) (b0 := 72) (lo := 43) (hi := 1) (r := 72) (op := PCSDD.BOp.xor) (m := ai497) (m1 := ao498) (m2 := ao499) (m3 := an497) (by decide) (by rfl) (by decide) a498 a499 (by rfl)
abbrev an493 : Mgr := ao497
abbrev ao493 : Mgr := {an493 with memo := ((PCSDD.BOp.xor,0,73),73)::an493.memo}
theorem a493 : ApplyCertificate 12 DEFAULT_LIMITS 20 PCSDD.BOp.xor 0 73 ai493 73 ao493 := by
  exact ApplyCertificate.branch (fuel := 19) (a0 := 0) (b0 := 73) (lo := 71) (hi := 72) (r := 73) (op := PCSDD.BOp.xor) (m := ai493) (m1 := ao494) (m2 := ao497) (m3 := an493) (by decide) (by rfl) (by decide) a494 a497 (by rfl)
abbrev an485 : Mgr := ao493
abbrev ao485 : Mgr := {an485 with memo := ((PCSDD.BOp.xor,0,74),74)::an485.memo}
theorem a485 : ApplyCertificate 12 DEFAULT_LIMITS 21 PCSDD.BOp.xor 0 74 ai485 74 ao485 := by
  exact ApplyCertificate.branch (fuel := 20) (a0 := 0) (b0 := 74) (lo := 70) (hi := 73) (r := 74) (op := PCSDD.BOp.xor) (m := ai485) (m1 := ao486) (m2 := ao493) (m3 := an485) (by decide) (by rfl) (by decide) a486 a493 (by rfl)
abbrev ai500 : Mgr := ao485
abbrev ai501 : Mgr := {ai500 with ops := ai500.ops+1}
abbrev ai502 : Mgr := {ai501 with ops := ai501.ops+1}
abbrev ai503 : Mgr := {ai502 with ops := ai502.ops+1}
abbrev ao503 : Mgr := {ai503 with ops := ai503.ops+1}
theorem a503 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.xor 0 46 ai503 46 ao503 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 0) (b0 := 46) (r := 46) (op := PCSDD.BOp.xor) (m := ai503) (by decide) (by rfl)
abbrev ai504 : Mgr := ao503
abbrev ao504 : Mgr := {ai504 with ops := ai504.ops+1}
theorem a504 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.xor 0 1 ai504 1 ao504 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 0) (b0 := 1) (r := 1) (op := PCSDD.BOp.xor) (m := ai504) (by decide) (by rfl)
abbrev an502 : Mgr := ao504
abbrev ao502 : Mgr := {an502 with memo := ((PCSDD.BOp.xor,0,75),75)::an502.memo}
theorem a502 : ApplyCertificate 12 DEFAULT_LIMITS 19 PCSDD.BOp.xor 0 75 ai502 75 ao502 := by
  exact ApplyCertificate.branch (fuel := 18) (a0 := 0) (b0 := 75) (lo := 46) (hi := 1) (r := 75) (op := PCSDD.BOp.xor) (m := ai502) (m1 := ao503) (m2 := ao504) (m3 := an502) (by decide) (by rfl) (by decide) a503 a504 (by rfl)
abbrev ai505 : Mgr := ao502
abbrev ai506 : Mgr := {ai505 with ops := ai505.ops+1}
abbrev ao506 : Mgr := {ai506 with ops := ai506.ops+1}
theorem a506 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.xor 0 47 ai506 47 ao506 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 0) (b0 := 47) (r := 47) (op := PCSDD.BOp.xor) (m := ai506) (by decide) (by rfl)
abbrev ai507 : Mgr := ao506
abbrev ao507 : Mgr := {ai507 with ops := ai507.ops+1}
theorem a507 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.xor 0 1 ai507 1 ao507 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 0) (b0 := 1) (r := 1) (op := PCSDD.BOp.xor) (m := ai507) (by decide) (by rfl)
abbrev an505 : Mgr := ao507
abbrev ao505 : Mgr := {an505 with memo := ((PCSDD.BOp.xor,0,76),76)::an505.memo}
theorem a505 : ApplyCertificate 12 DEFAULT_LIMITS 19 PCSDD.BOp.xor 0 76 ai505 76 ao505 := by
  exact ApplyCertificate.branch (fuel := 18) (a0 := 0) (b0 := 76) (lo := 47) (hi := 1) (r := 76) (op := PCSDD.BOp.xor) (m := ai505) (m1 := ao506) (m2 := ao507) (m3 := an505) (by decide) (by rfl) (by decide) a506 a507 (by rfl)
abbrev an501 : Mgr := ao505
abbrev ao501 : Mgr := {an501 with memo := ((PCSDD.BOp.xor,0,77),77)::an501.memo}
theorem a501 : ApplyCertificate 12 DEFAULT_LIMITS 20 PCSDD.BOp.xor 0 77 ai501 77 ao501 := by
  exact ApplyCertificate.branch (fuel := 19) (a0 := 0) (b0 := 77) (lo := 75) (hi := 76) (r := 77) (op := PCSDD.BOp.xor) (m := ai501) (m1 := ao502) (m2 := ao505) (m3 := an501) (by decide) (by rfl) (by decide) a502 a505 (by rfl)
abbrev ai508 : Mgr := ao501
abbrev ai509 : Mgr := {ai508 with ops := ai508.ops+1}
abbrev ai510 : Mgr := {ai509 with ops := ai509.ops+1}
abbrev ao510 : Mgr := {ai510 with ops := ai510.ops+1}
theorem a510 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.xor 0 49 ai510 49 ao510 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 0) (b0 := 49) (r := 49) (op := PCSDD.BOp.xor) (m := ai510) (by decide) (by rfl)
abbrev ai511 : Mgr := ao510
abbrev ao511 : Mgr := {ai511 with ops := ai511.ops+1}
theorem a511 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.xor 0 1 ai511 1 ao511 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 0) (b0 := 1) (r := 1) (op := PCSDD.BOp.xor) (m := ai511) (by decide) (by rfl)
abbrev an509 : Mgr := ao511
abbrev ao509 : Mgr := {an509 with memo := ((PCSDD.BOp.xor,0,78),78)::an509.memo}
theorem a509 : ApplyCertificate 12 DEFAULT_LIMITS 19 PCSDD.BOp.xor 0 78 ai509 78 ao509 := by
  exact ApplyCertificate.branch (fuel := 18) (a0 := 0) (b0 := 78) (lo := 49) (hi := 1) (r := 78) (op := PCSDD.BOp.xor) (m := ai509) (m1 := ao510) (m2 := ao511) (m3 := an509) (by decide) (by rfl) (by decide) a510 a511 (by rfl)
abbrev ai512 : Mgr := ao509
abbrev ai513 : Mgr := {ai512 with ops := ai512.ops+1}
abbrev ao513 : Mgr := {ai513 with ops := ai513.ops+1}
theorem a513 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.xor 0 50 ai513 50 ao513 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 0) (b0 := 50) (r := 50) (op := PCSDD.BOp.xor) (m := ai513) (by decide) (by rfl)
abbrev ai514 : Mgr := ao513
abbrev ao514 : Mgr := {ai514 with ops := ai514.ops+1}
theorem a514 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.xor 0 1 ai514 1 ao514 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 0) (b0 := 1) (r := 1) (op := PCSDD.BOp.xor) (m := ai514) (by decide) (by rfl)
abbrev an512 : Mgr := ao514
abbrev ao512 : Mgr := {an512 with memo := ((PCSDD.BOp.xor,0,79),79)::an512.memo}
theorem a512 : ApplyCertificate 12 DEFAULT_LIMITS 19 PCSDD.BOp.xor 0 79 ai512 79 ao512 := by
  exact ApplyCertificate.branch (fuel := 18) (a0 := 0) (b0 := 79) (lo := 50) (hi := 1) (r := 79) (op := PCSDD.BOp.xor) (m := ai512) (m1 := ao513) (m2 := ao514) (m3 := an512) (by decide) (by rfl) (by decide) a513 a514 (by rfl)
abbrev an508 : Mgr := ao512
abbrev ao508 : Mgr := {an508 with memo := ((PCSDD.BOp.xor,0,80),80)::an508.memo}
theorem a508 : ApplyCertificate 12 DEFAULT_LIMITS 20 PCSDD.BOp.xor 0 80 ai508 80 ao508 := by
  exact ApplyCertificate.branch (fuel := 19) (a0 := 0) (b0 := 80) (lo := 78) (hi := 79) (r := 80) (op := PCSDD.BOp.xor) (m := ai508) (m1 := ao509) (m2 := ao512) (m3 := an508) (by decide) (by rfl) (by decide) a509 a512 (by rfl)
abbrev an500 : Mgr := ao508
abbrev ao500 : Mgr := {an500 with memo := ((PCSDD.BOp.xor,0,81),81)::an500.memo}
theorem a500 : ApplyCertificate 12 DEFAULT_LIMITS 21 PCSDD.BOp.xor 0 81 ai500 81 ao500 := by
  exact ApplyCertificate.branch (fuel := 20) (a0 := 0) (b0 := 81) (lo := 77) (hi := 80) (r := 81) (op := PCSDD.BOp.xor) (m := ai500) (m1 := ao501) (m2 := ao508) (m3 := an500) (by decide) (by rfl) (by decide) a501 a508 (by rfl)
abbrev an484 : Mgr := ao500
abbrev ao484 : Mgr := {an484 with memo := ((PCSDD.BOp.xor,0,82),82)::an484.memo}
theorem a484 : ApplyCertificate 12 DEFAULT_LIMITS 22 PCSDD.BOp.xor 0 82 ai484 82 ao484 := by
  exact ApplyCertificate.branch (fuel := 21) (a0 := 0) (b0 := 82) (lo := 74) (hi := 81) (r := 82) (op := PCSDD.BOp.xor) (m := ai484) (m1 := ao485) (m2 := ao500) (m3 := an484) (by decide) (by rfl) (by decide) a485 a500 (by rfl)
abbrev an452 : Mgr := ao484
abbrev ao452 : Mgr := {an452 with memo := ((PCSDD.BOp.xor,0,83),83)::an452.memo}
theorem a452 : ApplyCertificate 12 DEFAULT_LIMITS 23 PCSDD.BOp.xor 0 83 ai452 83 ao452 := by
  exact ApplyCertificate.branch (fuel := 22) (a0 := 0) (b0 := 83) (lo := 68) (hi := 82) (r := 83) (op := PCSDD.BOp.xor) (m := ai452) (m1 := ao453) (m2 := ao484) (m3 := an452) (by decide) (by rfl) (by decide) a453 a484 (by rfl)
abbrev an390 : Mgr := ao452
abbrev ao390 : Mgr := {an390 with memo := ((PCSDD.BOp.xor,0,84),84)::an390.memo}
theorem a390 : ApplyCertificate 12 DEFAULT_LIMITS 24 PCSDD.BOp.xor 0 84 ai390 84 ao390 := by
  exact ApplyCertificate.branch (fuel := 23) (a0 := 0) (b0 := 84) (lo := 54) (hi := 83) (r := 84) (op := PCSDD.BOp.xor) (m := ai390) (m1 := ao391) (m2 := ao452) (m3 := an390) (by decide) (by rfl) (by decide) a391 a452 (by rfl)
abbrev ai515 : Mgr := ao390
abbrev ai516 : Mgr := {ai515 with ops := ai515.ops+1}
abbrev ai517 : Mgr := {ai516 with ops := ai516.ops+1}
abbrev ai518 : Mgr := {ai517 with ops := ai517.ops+1}
abbrev ai519 : Mgr := {ai518 with ops := ai518.ops+1}
abbrev ai520 : Mgr := {ai519 with ops := ai519.ops+1}
abbrev ai521 : Mgr := {ai520 with ops := ai520.ops+1}
abbrev ao521 : Mgr := {ai521 with ops := ai521.ops+1}
theorem a521 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.xor 0 0 ai521 0 ao521 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 0) (b0 := 0) (r := 0) (op := PCSDD.BOp.xor) (m := ai521) (by decide) (by rfl)
abbrev ai522 : Mgr := ao521
abbrev ao522 : Mgr := {ai522 with ops := ai522.ops+1}
theorem a522 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.xor 0 1 ai522 1 ao522 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 0) (b0 := 1) (r := 1) (op := PCSDD.BOp.xor) (m := ai522) (by decide) (by rfl)
abbrev an520 : Mgr := ao522
abbrev ao520 : Mgr := {an520 with memo := ((PCSDD.BOp.xor,0,3),3)::an520.memo}
theorem a520 : ApplyCertificate 12 DEFAULT_LIMITS 19 PCSDD.BOp.xor 0 3 ai520 3 ao520 := by
  exact ApplyCertificate.branch (fuel := 18) (a0 := 0) (b0 := 3) (lo := 0) (hi := 1) (r := 3) (op := PCSDD.BOp.xor) (m := ai520) (m1 := ao521) (m2 := ao522) (m3 := an520) (by decide) (by rfl) (by decide) a521 a522 (by rfl)
abbrev ai523 : Mgr := ao520
abbrev ai524 : Mgr := {ai523 with ops := ai523.ops+1}
abbrev ao524 : Mgr := {ai524 with ops := ai524.ops+1}
theorem a524 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.xor 0 28 ai524 28 ao524 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 0) (b0 := 28) (r := 28) (op := PCSDD.BOp.xor) (m := ai524) (by decide) (by rfl)
abbrev ai525 : Mgr := ao524
abbrev ao525 : Mgr := {ai525 with ops := ai525.ops+1}
theorem a525 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.xor 0 1 ai525 1 ao525 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 0) (b0 := 1) (r := 1) (op := PCSDD.BOp.xor) (m := ai525) (by decide) (by rfl)
abbrev an523 : Mgr := ao525
abbrev ao523 : Mgr := {an523 with memo := ((PCSDD.BOp.xor,0,85),85)::an523.memo}
theorem a523 : ApplyCertificate 12 DEFAULT_LIMITS 19 PCSDD.BOp.xor 0 85 ai523 85 ao523 := by
  exact ApplyCertificate.branch (fuel := 18) (a0 := 0) (b0 := 85) (lo := 28) (hi := 1) (r := 85) (op := PCSDD.BOp.xor) (m := ai523) (m1 := ao524) (m2 := ao525) (m3 := an523) (by decide) (by rfl) (by decide) a524 a525 (by rfl)
abbrev an519 : Mgr := ao523
abbrev ao519 : Mgr := {an519 with memo := ((PCSDD.BOp.xor,0,86),86)::an519.memo}
theorem a519 : ApplyCertificate 12 DEFAULT_LIMITS 20 PCSDD.BOp.xor 0 86 ai519 86 ao519 := by
  exact ApplyCertificate.branch (fuel := 19) (a0 := 0) (b0 := 86) (lo := 3) (hi := 85) (r := 86) (op := PCSDD.BOp.xor) (m := ai519) (m1 := ao520) (m2 := ao523) (m3 := an519) (by decide) (by rfl) (by decide) a520 a523 (by rfl)
abbrev ai526 : Mgr := ao519
abbrev ai527 : Mgr := {ai526 with ops := ai526.ops+1}
abbrev ai528 : Mgr := {ai527 with ops := ai527.ops+1}
abbrev ao528 : Mgr := {ai528 with ops := ai528.ops+1}
theorem a528 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.xor 0 25 ai528 25 ao528 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 0) (b0 := 25) (r := 25) (op := PCSDD.BOp.xor) (m := ai528) (by decide) (by rfl)
abbrev ai529 : Mgr := ao528
abbrev ao529 : Mgr := {ai529 with ops := ai529.ops+1}
theorem a529 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.xor 0 1 ai529 1 ao529 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 0) (b0 := 1) (r := 1) (op := PCSDD.BOp.xor) (m := ai529) (by decide) (by rfl)
abbrev an527 : Mgr := ao529
abbrev ao527 : Mgr := {an527 with memo := ((PCSDD.BOp.xor,0,87),87)::an527.memo}
theorem a527 : ApplyCertificate 12 DEFAULT_LIMITS 19 PCSDD.BOp.xor 0 87 ai527 87 ao527 := by
  exact ApplyCertificate.branch (fuel := 18) (a0 := 0) (b0 := 87) (lo := 25) (hi := 1) (r := 87) (op := PCSDD.BOp.xor) (m := ai527) (m1 := ao528) (m2 := ao529) (m3 := an527) (by decide) (by rfl) (by decide) a528 a529 (by rfl)
abbrev ai530 : Mgr := ao527
abbrev ai531 : Mgr := {ai530 with ops := ai530.ops+1}
abbrev ao531 : Mgr := {ai531 with ops := ai531.ops+1}
theorem a531 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.xor 0 30 ai531 30 ao531 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 0) (b0 := 30) (r := 30) (op := PCSDD.BOp.xor) (m := ai531) (by decide) (by rfl)
abbrev ai532 : Mgr := ao531
abbrev ao532 : Mgr := {ai532 with ops := ai532.ops+1}
theorem a532 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.xor 0 1 ai532 1 ao532 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 0) (b0 := 1) (r := 1) (op := PCSDD.BOp.xor) (m := ai532) (by decide) (by rfl)
abbrev an530 : Mgr := ao532
abbrev ao530 : Mgr := {an530 with memo := ((PCSDD.BOp.xor,0,88),88)::an530.memo}
theorem a530 : ApplyCertificate 12 DEFAULT_LIMITS 19 PCSDD.BOp.xor 0 88 ai530 88 ao530 := by
  exact ApplyCertificate.branch (fuel := 18) (a0 := 0) (b0 := 88) (lo := 30) (hi := 1) (r := 88) (op := PCSDD.BOp.xor) (m := ai530) (m1 := ao531) (m2 := ao532) (m3 := an530) (by decide) (by rfl) (by decide) a531 a532 (by rfl)
abbrev an526 : Mgr := ao530
abbrev ao526 : Mgr := {an526 with memo := ((PCSDD.BOp.xor,0,89),89)::an526.memo}
theorem a526 : ApplyCertificate 12 DEFAULT_LIMITS 20 PCSDD.BOp.xor 0 89 ai526 89 ao526 := by
  exact ApplyCertificate.branch (fuel := 19) (a0 := 0) (b0 := 89) (lo := 87) (hi := 88) (r := 89) (op := PCSDD.BOp.xor) (m := ai526) (m1 := ao527) (m2 := ao530) (m3 := an526) (by decide) (by rfl) (by decide) a527 a530 (by rfl)
abbrev an518 : Mgr := ao526
abbrev ao518 : Mgr := {an518 with memo := ((PCSDD.BOp.xor,0,90),90)::an518.memo}
theorem a518 : ApplyCertificate 12 DEFAULT_LIMITS 21 PCSDD.BOp.xor 0 90 ai518 90 ao518 := by
  exact ApplyCertificate.branch (fuel := 20) (a0 := 0) (b0 := 90) (lo := 86) (hi := 89) (r := 90) (op := PCSDD.BOp.xor) (m := ai518) (m1 := ao519) (m2 := ao526) (m3 := an518) (by decide) (by rfl) (by decide) a519 a526 (by rfl)
abbrev ai533 : Mgr := ao518
abbrev ai534 : Mgr := {ai533 with ops := ai533.ops+1}
abbrev ai535 : Mgr := {ai534 with ops := ai534.ops+1}
abbrev ai536 : Mgr := {ai535 with ops := ai535.ops+1}
abbrev ao536 : Mgr := {ai536 with ops := ai536.ops+1}
theorem a536 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.xor 0 22 ai536 22 ao536 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 0) (b0 := 22) (r := 22) (op := PCSDD.BOp.xor) (m := ai536) (by decide) (by rfl)
abbrev ai537 : Mgr := ao536
abbrev ao537 : Mgr := {ai537 with ops := ai537.ops+1}
theorem a537 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.xor 0 1 ai537 1 ao537 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 0) (b0 := 1) (r := 1) (op := PCSDD.BOp.xor) (m := ai537) (by decide) (by rfl)
abbrev an535 : Mgr := ao537
abbrev ao535 : Mgr := {an535 with memo := ((PCSDD.BOp.xor,0,91),91)::an535.memo}
theorem a535 : ApplyCertificate 12 DEFAULT_LIMITS 19 PCSDD.BOp.xor 0 91 ai535 91 ao535 := by
  exact ApplyCertificate.branch (fuel := 18) (a0 := 0) (b0 := 91) (lo := 22) (hi := 1) (r := 91) (op := PCSDD.BOp.xor) (m := ai535) (m1 := ao536) (m2 := ao537) (m3 := an535) (by decide) (by rfl) (by decide) a536 a537 (by rfl)
abbrev ai538 : Mgr := ao535
abbrev ai539 : Mgr := {ai538 with ops := ai538.ops+1}
abbrev ao539 : Mgr := {ai539 with ops := ai539.ops+1}
theorem a539 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.xor 0 33 ai539 33 ao539 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 0) (b0 := 33) (r := 33) (op := PCSDD.BOp.xor) (m := ai539) (by decide) (by rfl)
abbrev ai540 : Mgr := ao539
abbrev ao540 : Mgr := {ai540 with ops := ai540.ops+1}
theorem a540 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.xor 0 1 ai540 1 ao540 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 0) (b0 := 1) (r := 1) (op := PCSDD.BOp.xor) (m := ai540) (by decide) (by rfl)
abbrev an538 : Mgr := ao540
abbrev ao538 : Mgr := {an538 with memo := ((PCSDD.BOp.xor,0,92),92)::an538.memo}
theorem a538 : ApplyCertificate 12 DEFAULT_LIMITS 19 PCSDD.BOp.xor 0 92 ai538 92 ao538 := by
  exact ApplyCertificate.branch (fuel := 18) (a0 := 0) (b0 := 92) (lo := 33) (hi := 1) (r := 92) (op := PCSDD.BOp.xor) (m := ai538) (m1 := ao539) (m2 := ao540) (m3 := an538) (by decide) (by rfl) (by decide) a539 a540 (by rfl)
abbrev an534 : Mgr := ao538
abbrev ao534 : Mgr := {an534 with memo := ((PCSDD.BOp.xor,0,93),93)::an534.memo}
theorem a534 : ApplyCertificate 12 DEFAULT_LIMITS 20 PCSDD.BOp.xor 0 93 ai534 93 ao534 := by
  exact ApplyCertificate.branch (fuel := 19) (a0 := 0) (b0 := 93) (lo := 91) (hi := 92) (r := 93) (op := PCSDD.BOp.xor) (m := ai534) (m1 := ao535) (m2 := ao538) (m3 := an534) (by decide) (by rfl) (by decide) a535 a538 (by rfl)
abbrev ai541 : Mgr := ao534
abbrev ai542 : Mgr := {ai541 with ops := ai541.ops+1}
abbrev ai543 : Mgr := {ai542 with ops := ai542.ops+1}
abbrev ao543 : Mgr := {ai543 with ops := ai543.ops+1}
theorem a543 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.xor 0 35 ai543 35 ao543 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 0) (b0 := 35) (r := 35) (op := PCSDD.BOp.xor) (m := ai543) (by decide) (by rfl)
abbrev ai544 : Mgr := ao543
abbrev ao544 : Mgr := {ai544 with ops := ai544.ops+1}
theorem a544 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.xor 0 1 ai544 1 ao544 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 0) (b0 := 1) (r := 1) (op := PCSDD.BOp.xor) (m := ai544) (by decide) (by rfl)
abbrev an542 : Mgr := ao544
abbrev ao542 : Mgr := {an542 with memo := ((PCSDD.BOp.xor,0,94),94)::an542.memo}
theorem a542 : ApplyCertificate 12 DEFAULT_LIMITS 19 PCSDD.BOp.xor 0 94 ai542 94 ao542 := by
  exact ApplyCertificate.branch (fuel := 18) (a0 := 0) (b0 := 94) (lo := 35) (hi := 1) (r := 94) (op := PCSDD.BOp.xor) (m := ai542) (m1 := ao543) (m2 := ao544) (m3 := an542) (by decide) (by rfl) (by decide) a543 a544 (by rfl)
abbrev ai545 : Mgr := ao542
abbrev ai546 : Mgr := {ai545 with ops := ai545.ops+1}
abbrev ao546 : Mgr := {ai546 with ops := ai546.ops+1}
theorem a546 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.xor 0 36 ai546 36 ao546 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 0) (b0 := 36) (r := 36) (op := PCSDD.BOp.xor) (m := ai546) (by decide) (by rfl)
abbrev ai547 : Mgr := ao546
abbrev ao547 : Mgr := {ai547 with ops := ai547.ops+1}
theorem a547 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.xor 0 1 ai547 1 ao547 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 0) (b0 := 1) (r := 1) (op := PCSDD.BOp.xor) (m := ai547) (by decide) (by rfl)
abbrev an545 : Mgr := ao547
abbrev ao545 : Mgr := {an545 with memo := ((PCSDD.BOp.xor,0,95),95)::an545.memo}
theorem a545 : ApplyCertificate 12 DEFAULT_LIMITS 19 PCSDD.BOp.xor 0 95 ai545 95 ao545 := by
  exact ApplyCertificate.branch (fuel := 18) (a0 := 0) (b0 := 95) (lo := 36) (hi := 1) (r := 95) (op := PCSDD.BOp.xor) (m := ai545) (m1 := ao546) (m2 := ao547) (m3 := an545) (by decide) (by rfl) (by decide) a546 a547 (by rfl)
abbrev an541 : Mgr := ao545
abbrev ao541 : Mgr := {an541 with memo := ((PCSDD.BOp.xor,0,96),96)::an541.memo}
theorem a541 : ApplyCertificate 12 DEFAULT_LIMITS 20 PCSDD.BOp.xor 0 96 ai541 96 ao541 := by
  exact ApplyCertificate.branch (fuel := 19) (a0 := 0) (b0 := 96) (lo := 94) (hi := 95) (r := 96) (op := PCSDD.BOp.xor) (m := ai541) (m1 := ao542) (m2 := ao545) (m3 := an541) (by decide) (by rfl) (by decide) a542 a545 (by rfl)
abbrev an533 : Mgr := ao541
abbrev ao533 : Mgr := {an533 with memo := ((PCSDD.BOp.xor,0,97),97)::an533.memo}
theorem a533 : ApplyCertificate 12 DEFAULT_LIMITS 21 PCSDD.BOp.xor 0 97 ai533 97 ao533 := by
  exact ApplyCertificate.branch (fuel := 20) (a0 := 0) (b0 := 97) (lo := 93) (hi := 96) (r := 97) (op := PCSDD.BOp.xor) (m := ai533) (m1 := ao534) (m2 := ao541) (m3 := an533) (by decide) (by rfl) (by decide) a534 a541 (by rfl)
abbrev an517 : Mgr := ao533
abbrev ao517 : Mgr := {an517 with memo := ((PCSDD.BOp.xor,0,98),98)::an517.memo}
theorem a517 : ApplyCertificate 12 DEFAULT_LIMITS 22 PCSDD.BOp.xor 0 98 ai517 98 ao517 := by
  exact ApplyCertificate.branch (fuel := 21) (a0 := 0) (b0 := 98) (lo := 90) (hi := 97) (r := 98) (op := PCSDD.BOp.xor) (m := ai517) (m1 := ao518) (m2 := ao533) (m3 := an517) (by decide) (by rfl) (by decide) a518 a533 (by rfl)
abbrev ai548 : Mgr := ao517
abbrev ai549 : Mgr := {ai548 with ops := ai548.ops+1}
abbrev ai550 : Mgr := {ai549 with ops := ai549.ops+1}
abbrev ai551 : Mgr := {ai550 with ops := ai550.ops+1}
abbrev ai552 : Mgr := {ai551 with ops := ai551.ops+1}
abbrev ao552 : Mgr := {ai552 with ops := ai552.ops+1}
theorem a552 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.xor 0 9 ai552 9 ao552 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 0) (b0 := 9) (r := 9) (op := PCSDD.BOp.xor) (m := ai552) (by decide) (by rfl)
abbrev ai553 : Mgr := ao552
abbrev ao553 : Mgr := {ai553 with ops := ai553.ops+1}
theorem a553 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.xor 0 1 ai553 1 ao553 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 0) (b0 := 1) (r := 1) (op := PCSDD.BOp.xor) (m := ai553) (by decide) (by rfl)
abbrev an551 : Mgr := ao553
abbrev ao551 : Mgr := {an551 with memo := ((PCSDD.BOp.xor,0,14),14)::an551.memo}
theorem a551 : ApplyCertificate 12 DEFAULT_LIMITS 19 PCSDD.BOp.xor 0 14 ai551 14 ao551 := by
  exact ApplyCertificate.branch (fuel := 18) (a0 := 0) (b0 := 14) (lo := 9) (hi := 1) (r := 14) (op := PCSDD.BOp.xor) (m := ai551) (m1 := ao552) (m2 := ao553) (m3 := an551) (by decide) (by rfl) (by decide) a552 a553 (by rfl)
abbrev ai554 : Mgr := ao551
abbrev ai555 : Mgr := {ai554 with ops := ai554.ops+1}
abbrev ao555 : Mgr := {ai555 with ops := ai555.ops+1}
theorem a555 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.xor 0 40 ai555 40 ao555 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 0) (b0 := 40) (r := 40) (op := PCSDD.BOp.xor) (m := ai555) (by decide) (by rfl)
abbrev ai556 : Mgr := ao555
abbrev ao556 : Mgr := {ai556 with ops := ai556.ops+1}
theorem a556 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.xor 0 1 ai556 1 ao556 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 0) (b0 := 1) (r := 1) (op := PCSDD.BOp.xor) (m := ai556) (by decide) (by rfl)
abbrev an554 : Mgr := ao556
abbrev ao554 : Mgr := {an554 with memo := ((PCSDD.BOp.xor,0,99),99)::an554.memo}
theorem a554 : ApplyCertificate 12 DEFAULT_LIMITS 19 PCSDD.BOp.xor 0 99 ai554 99 ao554 := by
  exact ApplyCertificate.branch (fuel := 18) (a0 := 0) (b0 := 99) (lo := 40) (hi := 1) (r := 99) (op := PCSDD.BOp.xor) (m := ai554) (m1 := ao555) (m2 := ao556) (m3 := an554) (by decide) (by rfl) (by decide) a555 a556 (by rfl)
abbrev an550 : Mgr := ao554
abbrev ao550 : Mgr := {an550 with memo := ((PCSDD.BOp.xor,0,100),100)::an550.memo}
theorem a550 : ApplyCertificate 12 DEFAULT_LIMITS 20 PCSDD.BOp.xor 0 100 ai550 100 ao550 := by
  exact ApplyCertificate.branch (fuel := 19) (a0 := 0) (b0 := 100) (lo := 14) (hi := 99) (r := 100) (op := PCSDD.BOp.xor) (m := ai550) (m1 := ao551) (m2 := ao554) (m3 := an550) (by decide) (by rfl) (by decide) a551 a554 (by rfl)
abbrev ai557 : Mgr := ao550
abbrev ai558 : Mgr := {ai557 with ops := ai557.ops+1}
abbrev ai559 : Mgr := {ai558 with ops := ai558.ops+1}
abbrev ao559 : Mgr := {ai559 with ops := ai559.ops+1}
theorem a559 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.xor 0 42 ai559 42 ao559 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 0) (b0 := 42) (r := 42) (op := PCSDD.BOp.xor) (m := ai559) (by decide) (by rfl)
abbrev ai560 : Mgr := ao559
abbrev ao560 : Mgr := {ai560 with ops := ai560.ops+1}
theorem a560 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.xor 0 1 ai560 1 ao560 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 0) (b0 := 1) (r := 1) (op := PCSDD.BOp.xor) (m := ai560) (by decide) (by rfl)
abbrev an558 : Mgr := ao560
abbrev ao558 : Mgr := {an558 with memo := ((PCSDD.BOp.xor,0,101),101)::an558.memo}
theorem a558 : ApplyCertificate 12 DEFAULT_LIMITS 19 PCSDD.BOp.xor 0 101 ai558 101 ao558 := by
  exact ApplyCertificate.branch (fuel := 18) (a0 := 0) (b0 := 101) (lo := 42) (hi := 1) (r := 101) (op := PCSDD.BOp.xor) (m := ai558) (m1 := ao559) (m2 := ao560) (m3 := an558) (by decide) (by rfl) (by decide) a559 a560 (by rfl)
abbrev ai561 : Mgr := ao558
abbrev ai562 : Mgr := {ai561 with ops := ai561.ops+1}
abbrev ao562 : Mgr := {ai562 with ops := ai562.ops+1}
theorem a562 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.xor 0 43 ai562 43 ao562 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 0) (b0 := 43) (r := 43) (op := PCSDD.BOp.xor) (m := ai562) (by decide) (by rfl)
abbrev ai563 : Mgr := ao562
abbrev ao563 : Mgr := {ai563 with ops := ai563.ops+1}
theorem a563 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.xor 0 1 ai563 1 ao563 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 0) (b0 := 1) (r := 1) (op := PCSDD.BOp.xor) (m := ai563) (by decide) (by rfl)
abbrev an561 : Mgr := ao563
abbrev ao561 : Mgr := {an561 with memo := ((PCSDD.BOp.xor,0,102),102)::an561.memo}
theorem a561 : ApplyCertificate 12 DEFAULT_LIMITS 19 PCSDD.BOp.xor 0 102 ai561 102 ao561 := by
  exact ApplyCertificate.branch (fuel := 18) (a0 := 0) (b0 := 102) (lo := 43) (hi := 1) (r := 102) (op := PCSDD.BOp.xor) (m := ai561) (m1 := ao562) (m2 := ao563) (m3 := an561) (by decide) (by rfl) (by decide) a562 a563 (by rfl)
abbrev an557 : Mgr := ao561
abbrev ao557 : Mgr := {an557 with memo := ((PCSDD.BOp.xor,0,103),103)::an557.memo}
theorem a557 : ApplyCertificate 12 DEFAULT_LIMITS 20 PCSDD.BOp.xor 0 103 ai557 103 ao557 := by
  exact ApplyCertificate.branch (fuel := 19) (a0 := 0) (b0 := 103) (lo := 101) (hi := 102) (r := 103) (op := PCSDD.BOp.xor) (m := ai557) (m1 := ao558) (m2 := ao561) (m3 := an557) (by decide) (by rfl) (by decide) a558 a561 (by rfl)
abbrev an549 : Mgr := ao557
abbrev ao549 : Mgr := {an549 with memo := ((PCSDD.BOp.xor,0,104),104)::an549.memo}
theorem a549 : ApplyCertificate 12 DEFAULT_LIMITS 21 PCSDD.BOp.xor 0 104 ai549 104 ao549 := by
  exact ApplyCertificate.branch (fuel := 20) (a0 := 0) (b0 := 104) (lo := 100) (hi := 103) (r := 104) (op := PCSDD.BOp.xor) (m := ai549) (m1 := ao550) (m2 := ao557) (m3 := an549) (by decide) (by rfl) (by decide) a550 a557 (by rfl)
abbrev ai564 : Mgr := ao549
abbrev ai565 : Mgr := {ai564 with ops := ai564.ops+1}
abbrev ai566 : Mgr := {ai565 with ops := ai565.ops+1}
abbrev ai567 : Mgr := {ai566 with ops := ai566.ops+1}
abbrev ao567 : Mgr := {ai567 with ops := ai567.ops+1}
theorem a567 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.xor 0 46 ai567 46 ao567 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 0) (b0 := 46) (r := 46) (op := PCSDD.BOp.xor) (m := ai567) (by decide) (by rfl)
abbrev ai568 : Mgr := ao567
abbrev ao568 : Mgr := {ai568 with ops := ai568.ops+1}
theorem a568 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.xor 0 1 ai568 1 ao568 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 0) (b0 := 1) (r := 1) (op := PCSDD.BOp.xor) (m := ai568) (by decide) (by rfl)
abbrev an566 : Mgr := ao568
abbrev ao566 : Mgr := {an566 with memo := ((PCSDD.BOp.xor,0,105),105)::an566.memo}
theorem a566 : ApplyCertificate 12 DEFAULT_LIMITS 19 PCSDD.BOp.xor 0 105 ai566 105 ao566 := by
  exact ApplyCertificate.branch (fuel := 18) (a0 := 0) (b0 := 105) (lo := 46) (hi := 1) (r := 105) (op := PCSDD.BOp.xor) (m := ai566) (m1 := ao567) (m2 := ao568) (m3 := an566) (by decide) (by rfl) (by decide) a567 a568 (by rfl)
abbrev ai569 : Mgr := ao566
abbrev ai570 : Mgr := {ai569 with ops := ai569.ops+1}
abbrev ao570 : Mgr := {ai570 with ops := ai570.ops+1}
theorem a570 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.xor 0 47 ai570 47 ao570 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 0) (b0 := 47) (r := 47) (op := PCSDD.BOp.xor) (m := ai570) (by decide) (by rfl)
abbrev ai571 : Mgr := ao570
abbrev ao571 : Mgr := {ai571 with ops := ai571.ops+1}
theorem a571 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.xor 0 1 ai571 1 ao571 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 0) (b0 := 1) (r := 1) (op := PCSDD.BOp.xor) (m := ai571) (by decide) (by rfl)
abbrev an569 : Mgr := ao571
abbrev ao569 : Mgr := {an569 with memo := ((PCSDD.BOp.xor,0,106),106)::an569.memo}
theorem a569 : ApplyCertificate 12 DEFAULT_LIMITS 19 PCSDD.BOp.xor 0 106 ai569 106 ao569 := by
  exact ApplyCertificate.branch (fuel := 18) (a0 := 0) (b0 := 106) (lo := 47) (hi := 1) (r := 106) (op := PCSDD.BOp.xor) (m := ai569) (m1 := ao570) (m2 := ao571) (m3 := an569) (by decide) (by rfl) (by decide) a570 a571 (by rfl)
abbrev an565 : Mgr := ao569
abbrev ao565 : Mgr := {an565 with memo := ((PCSDD.BOp.xor,0,107),107)::an565.memo}
theorem a565 : ApplyCertificate 12 DEFAULT_LIMITS 20 PCSDD.BOp.xor 0 107 ai565 107 ao565 := by
  exact ApplyCertificate.branch (fuel := 19) (a0 := 0) (b0 := 107) (lo := 105) (hi := 106) (r := 107) (op := PCSDD.BOp.xor) (m := ai565) (m1 := ao566) (m2 := ao569) (m3 := an565) (by decide) (by rfl) (by decide) a566 a569 (by rfl)
abbrev ai572 : Mgr := ao565
abbrev ai573 : Mgr := {ai572 with ops := ai572.ops+1}
abbrev ai574 : Mgr := {ai573 with ops := ai573.ops+1}
abbrev ao574 : Mgr := {ai574 with ops := ai574.ops+1}
theorem a574 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.xor 0 49 ai574 49 ao574 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 0) (b0 := 49) (r := 49) (op := PCSDD.BOp.xor) (m := ai574) (by decide) (by rfl)
abbrev ai575 : Mgr := ao574
abbrev ao575 : Mgr := {ai575 with ops := ai575.ops+1}
theorem a575 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.xor 0 1 ai575 1 ao575 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 0) (b0 := 1) (r := 1) (op := PCSDD.BOp.xor) (m := ai575) (by decide) (by rfl)
abbrev an573 : Mgr := ao575
abbrev ao573 : Mgr := {an573 with memo := ((PCSDD.BOp.xor,0,108),108)::an573.memo}
theorem a573 : ApplyCertificate 12 DEFAULT_LIMITS 19 PCSDD.BOp.xor 0 108 ai573 108 ao573 := by
  exact ApplyCertificate.branch (fuel := 18) (a0 := 0) (b0 := 108) (lo := 49) (hi := 1) (r := 108) (op := PCSDD.BOp.xor) (m := ai573) (m1 := ao574) (m2 := ao575) (m3 := an573) (by decide) (by rfl) (by decide) a574 a575 (by rfl)
abbrev ai576 : Mgr := ao573
abbrev ai577 : Mgr := {ai576 with ops := ai576.ops+1}
abbrev ao577 : Mgr := {ai577 with ops := ai577.ops+1}
theorem a577 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.xor 0 50 ai577 50 ao577 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 0) (b0 := 50) (r := 50) (op := PCSDD.BOp.xor) (m := ai577) (by decide) (by rfl)
abbrev ai578 : Mgr := ao577
abbrev ao578 : Mgr := {ai578 with ops := ai578.ops+1}
theorem a578 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.xor 0 1 ai578 1 ao578 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 0) (b0 := 1) (r := 1) (op := PCSDD.BOp.xor) (m := ai578) (by decide) (by rfl)
abbrev an576 : Mgr := ao578
abbrev ao576 : Mgr := {an576 with memo := ((PCSDD.BOp.xor,0,109),109)::an576.memo}
theorem a576 : ApplyCertificate 12 DEFAULT_LIMITS 19 PCSDD.BOp.xor 0 109 ai576 109 ao576 := by
  exact ApplyCertificate.branch (fuel := 18) (a0 := 0) (b0 := 109) (lo := 50) (hi := 1) (r := 109) (op := PCSDD.BOp.xor) (m := ai576) (m1 := ao577) (m2 := ao578) (m3 := an576) (by decide) (by rfl) (by decide) a577 a578 (by rfl)
abbrev an572 : Mgr := ao576
abbrev ao572 : Mgr := {an572 with memo := ((PCSDD.BOp.xor,0,110),110)::an572.memo}
theorem a572 : ApplyCertificate 12 DEFAULT_LIMITS 20 PCSDD.BOp.xor 0 110 ai572 110 ao572 := by
  exact ApplyCertificate.branch (fuel := 19) (a0 := 0) (b0 := 110) (lo := 108) (hi := 109) (r := 110) (op := PCSDD.BOp.xor) (m := ai572) (m1 := ao573) (m2 := ao576) (m3 := an572) (by decide) (by rfl) (by decide) a573 a576 (by rfl)
abbrev an564 : Mgr := ao572
abbrev ao564 : Mgr := {an564 with memo := ((PCSDD.BOp.xor,0,111),111)::an564.memo}
theorem a564 : ApplyCertificate 12 DEFAULT_LIMITS 21 PCSDD.BOp.xor 0 111 ai564 111 ao564 := by
  exact ApplyCertificate.branch (fuel := 20) (a0 := 0) (b0 := 111) (lo := 107) (hi := 110) (r := 111) (op := PCSDD.BOp.xor) (m := ai564) (m1 := ao565) (m2 := ao572) (m3 := an564) (by decide) (by rfl) (by decide) a565 a572 (by rfl)
abbrev an548 : Mgr := ao564
abbrev ao548 : Mgr := {an548 with memo := ((PCSDD.BOp.xor,0,112),112)::an548.memo}
theorem a548 : ApplyCertificate 12 DEFAULT_LIMITS 22 PCSDD.BOp.xor 0 112 ai548 112 ao548 := by
  exact ApplyCertificate.branch (fuel := 21) (a0 := 0) (b0 := 112) (lo := 104) (hi := 111) (r := 112) (op := PCSDD.BOp.xor) (m := ai548) (m1 := ao549) (m2 := ao564) (m3 := an548) (by decide) (by rfl) (by decide) a549 a564 (by rfl)
abbrev an516 : Mgr := ao548
abbrev ao516 : Mgr := {an516 with memo := ((PCSDD.BOp.xor,0,113),113)::an516.memo}
theorem a516 : ApplyCertificate 12 DEFAULT_LIMITS 23 PCSDD.BOp.xor 0 113 ai516 113 ao516 := by
  exact ApplyCertificate.branch (fuel := 22) (a0 := 0) (b0 := 113) (lo := 98) (hi := 112) (r := 113) (op := PCSDD.BOp.xor) (m := ai516) (m1 := ao517) (m2 := ao548) (m3 := an516) (by decide) (by rfl) (by decide) a517 a548 (by rfl)
abbrev ai579 : Mgr := ao516
abbrev ai580 : Mgr := {ai579 with ops := ai579.ops+1}
abbrev ai581 : Mgr := {ai580 with ops := ai580.ops+1}
abbrev ai582 : Mgr := {ai581 with ops := ai581.ops+1}
abbrev ai583 : Mgr := {ai582 with ops := ai582.ops+1}
abbrev ai584 : Mgr := {ai583 with ops := ai583.ops+1}
abbrev ao584 : Mgr := {ai584 with ops := ai584.ops+1}
theorem a584 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.xor 0 6 ai584 6 ao584 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 0) (b0 := 6) (r := 6) (op := PCSDD.BOp.xor) (m := ai584) (by decide) (by rfl)
abbrev ai585 : Mgr := ao584
abbrev ao585 : Mgr := {ai585 with ops := ai585.ops+1}
theorem a585 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.xor 0 1 ai585 1 ao585 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 0) (b0 := 1) (r := 1) (op := PCSDD.BOp.xor) (m := ai585) (by decide) (by rfl)
abbrev an583 : Mgr := ao585
abbrev ao583 : Mgr := {an583 with memo := ((PCSDD.BOp.xor,0,16),16)::an583.memo}
theorem a583 : ApplyCertificate 12 DEFAULT_LIMITS 19 PCSDD.BOp.xor 0 16 ai583 16 ao583 := by
  exact ApplyCertificate.branch (fuel := 18) (a0 := 0) (b0 := 16) (lo := 6) (hi := 1) (r := 16) (op := PCSDD.BOp.xor) (m := ai583) (m1 := ao584) (m2 := ao585) (m3 := an583) (by decide) (by rfl) (by decide) a584 a585 (by rfl)
abbrev ai586 : Mgr := ao583
abbrev ai587 : Mgr := {ai586 with ops := ai586.ops+1}
abbrev ao587 : Mgr := {ai587 with ops := ai587.ops+1}
theorem a587 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.xor 0 55 ai587 55 ao587 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 0) (b0 := 55) (r := 55) (op := PCSDD.BOp.xor) (m := ai587) (by decide) (by rfl)
abbrev ai588 : Mgr := ao587
abbrev ao588 : Mgr := {ai588 with ops := ai588.ops+1}
theorem a588 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.xor 0 1 ai588 1 ao588 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 0) (b0 := 1) (r := 1) (op := PCSDD.BOp.xor) (m := ai588) (by decide) (by rfl)
abbrev an586 : Mgr := ao588
abbrev ao586 : Mgr := {an586 with memo := ((PCSDD.BOp.xor,0,114),114)::an586.memo}
theorem a586 : ApplyCertificate 12 DEFAULT_LIMITS 19 PCSDD.BOp.xor 0 114 ai586 114 ao586 := by
  exact ApplyCertificate.branch (fuel := 18) (a0 := 0) (b0 := 114) (lo := 55) (hi := 1) (r := 114) (op := PCSDD.BOp.xor) (m := ai586) (m1 := ao587) (m2 := ao588) (m3 := an586) (by decide) (by rfl) (by decide) a587 a588 (by rfl)
abbrev an582 : Mgr := ao586
abbrev ao582 : Mgr := {an582 with memo := ((PCSDD.BOp.xor,0,115),115)::an582.memo}
theorem a582 : ApplyCertificate 12 DEFAULT_LIMITS 20 PCSDD.BOp.xor 0 115 ai582 115 ao582 := by
  exact ApplyCertificate.branch (fuel := 19) (a0 := 0) (b0 := 115) (lo := 16) (hi := 114) (r := 115) (op := PCSDD.BOp.xor) (m := ai582) (m1 := ao583) (m2 := ao586) (m3 := an582) (by decide) (by rfl) (by decide) a583 a586 (by rfl)
abbrev ai589 : Mgr := ao582
abbrev ai590 : Mgr := {ai589 with ops := ai589.ops+1}
abbrev ai591 : Mgr := {ai590 with ops := ai590.ops+1}
abbrev ao591 : Mgr := {ai591 with ops := ai591.ops+1}
theorem a591 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.xor 0 57 ai591 57 ao591 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 0) (b0 := 57) (r := 57) (op := PCSDD.BOp.xor) (m := ai591) (by decide) (by rfl)
abbrev ai592 : Mgr := ao591
abbrev ao592 : Mgr := {ai592 with ops := ai592.ops+1}
theorem a592 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.xor 0 1 ai592 1 ao592 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 0) (b0 := 1) (r := 1) (op := PCSDD.BOp.xor) (m := ai592) (by decide) (by rfl)
abbrev an590 : Mgr := ao592
abbrev ao590 : Mgr := {an590 with memo := ((PCSDD.BOp.xor,0,116),116)::an590.memo}
theorem a590 : ApplyCertificate 12 DEFAULT_LIMITS 19 PCSDD.BOp.xor 0 116 ai590 116 ao590 := by
  exact ApplyCertificate.branch (fuel := 18) (a0 := 0) (b0 := 116) (lo := 57) (hi := 1) (r := 116) (op := PCSDD.BOp.xor) (m := ai590) (m1 := ao591) (m2 := ao592) (m3 := an590) (by decide) (by rfl) (by decide) a591 a592 (by rfl)
abbrev ai593 : Mgr := ao590
abbrev ai594 : Mgr := {ai593 with ops := ai593.ops+1}
abbrev ao594 : Mgr := {ai594 with ops := ai594.ops+1}
theorem a594 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.xor 0 58 ai594 58 ao594 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 0) (b0 := 58) (r := 58) (op := PCSDD.BOp.xor) (m := ai594) (by decide) (by rfl)
abbrev ai595 : Mgr := ao594
abbrev ao595 : Mgr := {ai595 with ops := ai595.ops+1}
theorem a595 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.xor 0 1 ai595 1 ao595 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 0) (b0 := 1) (r := 1) (op := PCSDD.BOp.xor) (m := ai595) (by decide) (by rfl)
abbrev an593 : Mgr := ao595
abbrev ao593 : Mgr := {an593 with memo := ((PCSDD.BOp.xor,0,117),117)::an593.memo}
theorem a593 : ApplyCertificate 12 DEFAULT_LIMITS 19 PCSDD.BOp.xor 0 117 ai593 117 ao593 := by
  exact ApplyCertificate.branch (fuel := 18) (a0 := 0) (b0 := 117) (lo := 58) (hi := 1) (r := 117) (op := PCSDD.BOp.xor) (m := ai593) (m1 := ao594) (m2 := ao595) (m3 := an593) (by decide) (by rfl) (by decide) a594 a595 (by rfl)
abbrev an589 : Mgr := ao593
abbrev ao589 : Mgr := {an589 with memo := ((PCSDD.BOp.xor,0,118),118)::an589.memo}
theorem a589 : ApplyCertificate 12 DEFAULT_LIMITS 20 PCSDD.BOp.xor 0 118 ai589 118 ao589 := by
  exact ApplyCertificate.branch (fuel := 19) (a0 := 0) (b0 := 118) (lo := 116) (hi := 117) (r := 118) (op := PCSDD.BOp.xor) (m := ai589) (m1 := ao590) (m2 := ao593) (m3 := an589) (by decide) (by rfl) (by decide) a590 a593 (by rfl)
abbrev an581 : Mgr := ao589
abbrev ao581 : Mgr := {an581 with memo := ((PCSDD.BOp.xor,0,119),119)::an581.memo}
theorem a581 : ApplyCertificate 12 DEFAULT_LIMITS 21 PCSDD.BOp.xor 0 119 ai581 119 ao581 := by
  exact ApplyCertificate.branch (fuel := 20) (a0 := 0) (b0 := 119) (lo := 115) (hi := 118) (r := 119) (op := PCSDD.BOp.xor) (m := ai581) (m1 := ao582) (m2 := ao589) (m3 := an581) (by decide) (by rfl) (by decide) a582 a589 (by rfl)
abbrev ai596 : Mgr := ao581
abbrev ai597 : Mgr := {ai596 with ops := ai596.ops+1}
abbrev ai598 : Mgr := {ai597 with ops := ai597.ops+1}
abbrev ai599 : Mgr := {ai598 with ops := ai598.ops+1}
abbrev ao599 : Mgr := {ai599 with ops := ai599.ops+1}
theorem a599 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.xor 0 61 ai599 61 ao599 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 0) (b0 := 61) (r := 61) (op := PCSDD.BOp.xor) (m := ai599) (by decide) (by rfl)
abbrev ai600 : Mgr := ao599
abbrev ao600 : Mgr := {ai600 with ops := ai600.ops+1}
theorem a600 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.xor 0 1 ai600 1 ao600 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 0) (b0 := 1) (r := 1) (op := PCSDD.BOp.xor) (m := ai600) (by decide) (by rfl)
abbrev an598 : Mgr := ao600
abbrev ao598 : Mgr := {an598 with memo := ((PCSDD.BOp.xor,0,120),120)::an598.memo}
theorem a598 : ApplyCertificate 12 DEFAULT_LIMITS 19 PCSDD.BOp.xor 0 120 ai598 120 ao598 := by
  exact ApplyCertificate.branch (fuel := 18) (a0 := 0) (b0 := 120) (lo := 61) (hi := 1) (r := 120) (op := PCSDD.BOp.xor) (m := ai598) (m1 := ao599) (m2 := ao600) (m3 := an598) (by decide) (by rfl) (by decide) a599 a600 (by rfl)
abbrev ai601 : Mgr := ao598
abbrev ai602 : Mgr := {ai601 with ops := ai601.ops+1}
abbrev ao602 : Mgr := {ai602 with ops := ai602.ops+1}
theorem a602 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.xor 0 62 ai602 62 ao602 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 0) (b0 := 62) (r := 62) (op := PCSDD.BOp.xor) (m := ai602) (by decide) (by rfl)
abbrev ai603 : Mgr := ao602
abbrev ao603 : Mgr := {ai603 with ops := ai603.ops+1}
theorem a603 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.xor 0 1 ai603 1 ao603 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 0) (b0 := 1) (r := 1) (op := PCSDD.BOp.xor) (m := ai603) (by decide) (by rfl)
abbrev an601 : Mgr := ao603
abbrev ao601 : Mgr := {an601 with memo := ((PCSDD.BOp.xor,0,121),121)::an601.memo}
theorem a601 : ApplyCertificate 12 DEFAULT_LIMITS 19 PCSDD.BOp.xor 0 121 ai601 121 ao601 := by
  exact ApplyCertificate.branch (fuel := 18) (a0 := 0) (b0 := 121) (lo := 62) (hi := 1) (r := 121) (op := PCSDD.BOp.xor) (m := ai601) (m1 := ao602) (m2 := ao603) (m3 := an601) (by decide) (by rfl) (by decide) a602 a603 (by rfl)
abbrev an597 : Mgr := ao601
abbrev ao597 : Mgr := {an597 with memo := ((PCSDD.BOp.xor,0,122),122)::an597.memo}
theorem a597 : ApplyCertificate 12 DEFAULT_LIMITS 20 PCSDD.BOp.xor 0 122 ai597 122 ao597 := by
  exact ApplyCertificate.branch (fuel := 19) (a0 := 0) (b0 := 122) (lo := 120) (hi := 121) (r := 122) (op := PCSDD.BOp.xor) (m := ai597) (m1 := ao598) (m2 := ao601) (m3 := an597) (by decide) (by rfl) (by decide) a598 a601 (by rfl)
abbrev ai604 : Mgr := ao597
abbrev ai605 : Mgr := {ai604 with ops := ai604.ops+1}
abbrev ai606 : Mgr := {ai605 with ops := ai605.ops+1}
abbrev ao606 : Mgr := {ai606 with ops := ai606.ops+1}
theorem a606 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.xor 0 64 ai606 64 ao606 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 0) (b0 := 64) (r := 64) (op := PCSDD.BOp.xor) (m := ai606) (by decide) (by rfl)
abbrev ai607 : Mgr := ao606
abbrev ao607 : Mgr := {ai607 with ops := ai607.ops+1}
theorem a607 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.xor 0 1 ai607 1 ao607 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 0) (b0 := 1) (r := 1) (op := PCSDD.BOp.xor) (m := ai607) (by decide) (by rfl)
abbrev an605 : Mgr := ao607
abbrev ao605 : Mgr := {an605 with memo := ((PCSDD.BOp.xor,0,123),123)::an605.memo}
theorem a605 : ApplyCertificate 12 DEFAULT_LIMITS 19 PCSDD.BOp.xor 0 123 ai605 123 ao605 := by
  exact ApplyCertificate.branch (fuel := 18) (a0 := 0) (b0 := 123) (lo := 64) (hi := 1) (r := 123) (op := PCSDD.BOp.xor) (m := ai605) (m1 := ao606) (m2 := ao607) (m3 := an605) (by decide) (by rfl) (by decide) a606 a607 (by rfl)
abbrev ai608 : Mgr := ao605
abbrev ai609 : Mgr := {ai608 with ops := ai608.ops+1}
abbrev ao609 : Mgr := {ai609 with ops := ai609.ops+1}
theorem a609 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.xor 0 65 ai609 65 ao609 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 0) (b0 := 65) (r := 65) (op := PCSDD.BOp.xor) (m := ai609) (by decide) (by rfl)
abbrev ai610 : Mgr := ao609
abbrev ao610 : Mgr := {ai610 with ops := ai610.ops+1}
theorem a610 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.xor 0 1 ai610 1 ao610 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 0) (b0 := 1) (r := 1) (op := PCSDD.BOp.xor) (m := ai610) (by decide) (by rfl)
abbrev an608 : Mgr := ao610
abbrev ao608 : Mgr := {an608 with memo := ((PCSDD.BOp.xor,0,124),124)::an608.memo}
theorem a608 : ApplyCertificate 12 DEFAULT_LIMITS 19 PCSDD.BOp.xor 0 124 ai608 124 ao608 := by
  exact ApplyCertificate.branch (fuel := 18) (a0 := 0) (b0 := 124) (lo := 65) (hi := 1) (r := 124) (op := PCSDD.BOp.xor) (m := ai608) (m1 := ao609) (m2 := ao610) (m3 := an608) (by decide) (by rfl) (by decide) a609 a610 (by rfl)
abbrev an604 : Mgr := ao608
abbrev ao604 : Mgr := {an604 with memo := ((PCSDD.BOp.xor,0,125),125)::an604.memo}
theorem a604 : ApplyCertificate 12 DEFAULT_LIMITS 20 PCSDD.BOp.xor 0 125 ai604 125 ao604 := by
  exact ApplyCertificate.branch (fuel := 19) (a0 := 0) (b0 := 125) (lo := 123) (hi := 124) (r := 125) (op := PCSDD.BOp.xor) (m := ai604) (m1 := ao605) (m2 := ao608) (m3 := an604) (by decide) (by rfl) (by decide) a605 a608 (by rfl)
abbrev an596 : Mgr := ao604
abbrev ao596 : Mgr := {an596 with memo := ((PCSDD.BOp.xor,0,126),126)::an596.memo}
theorem a596 : ApplyCertificate 12 DEFAULT_LIMITS 21 PCSDD.BOp.xor 0 126 ai596 126 ao596 := by
  exact ApplyCertificate.branch (fuel := 20) (a0 := 0) (b0 := 126) (lo := 122) (hi := 125) (r := 126) (op := PCSDD.BOp.xor) (m := ai596) (m1 := ao597) (m2 := ao604) (m3 := an596) (by decide) (by rfl) (by decide) a597 a604 (by rfl)
abbrev an580 : Mgr := ao596
abbrev ao580 : Mgr := {an580 with memo := ((PCSDD.BOp.xor,0,127),127)::an580.memo}
theorem a580 : ApplyCertificate 12 DEFAULT_LIMITS 22 PCSDD.BOp.xor 0 127 ai580 127 ao580 := by
  exact ApplyCertificate.branch (fuel := 21) (a0 := 0) (b0 := 127) (lo := 119) (hi := 126) (r := 127) (op := PCSDD.BOp.xor) (m := ai580) (m1 := ao581) (m2 := ao596) (m3 := an580) (by decide) (by rfl) (by decide) a581 a596 (by rfl)
abbrev ai611 : Mgr := ao580
abbrev ai612 : Mgr := {ai611 with ops := ai611.ops+1}
abbrev ai613 : Mgr := {ai612 with ops := ai612.ops+1}
abbrev ai614 : Mgr := {ai613 with ops := ai613.ops+1}
abbrev ai615 : Mgr := {ai614 with ops := ai614.ops+1}
abbrev ao615 : Mgr := {ai615 with ops := ai615.ops+1}
theorem a615 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.xor 0 11 ai615 11 ao615 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 0) (b0 := 11) (r := 11) (op := PCSDD.BOp.xor) (m := ai615) (by decide) (by rfl)
abbrev ai616 : Mgr := ao615
abbrev ao616 : Mgr := {ai616 with ops := ai616.ops+1}
theorem a616 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.xor 0 1 ai616 1 ao616 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 0) (b0 := 1) (r := 1) (op := PCSDD.BOp.xor) (m := ai616) (by decide) (by rfl)
abbrev an614 : Mgr := ao616
abbrev ao614 : Mgr := {an614 with memo := ((PCSDD.BOp.xor,0,17),17)::an614.memo}
theorem a614 : ApplyCertificate 12 DEFAULT_LIMITS 19 PCSDD.BOp.xor 0 17 ai614 17 ao614 := by
  exact ApplyCertificate.branch (fuel := 18) (a0 := 0) (b0 := 17) (lo := 11) (hi := 1) (r := 17) (op := PCSDD.BOp.xor) (m := ai614) (m1 := ao615) (m2 := ao616) (m3 := an614) (by decide) (by rfl) (by decide) a615 a616 (by rfl)
abbrev ai617 : Mgr := ao614
abbrev ai618 : Mgr := {ai617 with ops := ai617.ops+1}
abbrev ao618 : Mgr := {ai618 with ops := ai618.ops+1}
theorem a618 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.xor 0 69 ai618 69 ao618 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 0) (b0 := 69) (r := 69) (op := PCSDD.BOp.xor) (m := ai618) (by decide) (by rfl)
abbrev ai619 : Mgr := ao618
abbrev ao619 : Mgr := {ai619 with ops := ai619.ops+1}
theorem a619 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.xor 0 1 ai619 1 ao619 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 0) (b0 := 1) (r := 1) (op := PCSDD.BOp.xor) (m := ai619) (by decide) (by rfl)
abbrev an617 : Mgr := ao619
abbrev ao617 : Mgr := {an617 with memo := ((PCSDD.BOp.xor,0,128),128)::an617.memo}
theorem a617 : ApplyCertificate 12 DEFAULT_LIMITS 19 PCSDD.BOp.xor 0 128 ai617 128 ao617 := by
  exact ApplyCertificate.branch (fuel := 18) (a0 := 0) (b0 := 128) (lo := 69) (hi := 1) (r := 128) (op := PCSDD.BOp.xor) (m := ai617) (m1 := ao618) (m2 := ao619) (m3 := an617) (by decide) (by rfl) (by decide) a618 a619 (by rfl)
abbrev an613 : Mgr := ao617
abbrev ao613 : Mgr := {an613 with memo := ((PCSDD.BOp.xor,0,129),129)::an613.memo}
theorem a613 : ApplyCertificate 12 DEFAULT_LIMITS 20 PCSDD.BOp.xor 0 129 ai613 129 ao613 := by
  exact ApplyCertificate.branch (fuel := 19) (a0 := 0) (b0 := 129) (lo := 17) (hi := 128) (r := 129) (op := PCSDD.BOp.xor) (m := ai613) (m1 := ao614) (m2 := ao617) (m3 := an613) (by decide) (by rfl) (by decide) a614 a617 (by rfl)
abbrev ai620 : Mgr := ao613
abbrev ai621 : Mgr := {ai620 with ops := ai620.ops+1}
abbrev ai622 : Mgr := {ai621 with ops := ai621.ops+1}
abbrev ao622 : Mgr := {ai622 with ops := ai622.ops+1}
theorem a622 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.xor 0 71 ai622 71 ao622 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 0) (b0 := 71) (r := 71) (op := PCSDD.BOp.xor) (m := ai622) (by decide) (by rfl)
abbrev ai623 : Mgr := ao622
abbrev ao623 : Mgr := {ai623 with ops := ai623.ops+1}
theorem a623 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.xor 0 1 ai623 1 ao623 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 0) (b0 := 1) (r := 1) (op := PCSDD.BOp.xor) (m := ai623) (by decide) (by rfl)
abbrev an621 : Mgr := ao623
abbrev ao621 : Mgr := {an621 with memo := ((PCSDD.BOp.xor,0,130),130)::an621.memo}
theorem a621 : ApplyCertificate 12 DEFAULT_LIMITS 19 PCSDD.BOp.xor 0 130 ai621 130 ao621 := by
  exact ApplyCertificate.branch (fuel := 18) (a0 := 0) (b0 := 130) (lo := 71) (hi := 1) (r := 130) (op := PCSDD.BOp.xor) (m := ai621) (m1 := ao622) (m2 := ao623) (m3 := an621) (by decide) (by rfl) (by decide) a622 a623 (by rfl)
abbrev ai624 : Mgr := ao621
abbrev ai625 : Mgr := {ai624 with ops := ai624.ops+1}
abbrev ao625 : Mgr := {ai625 with ops := ai625.ops+1}
theorem a625 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.xor 0 72 ai625 72 ao625 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 0) (b0 := 72) (r := 72) (op := PCSDD.BOp.xor) (m := ai625) (by decide) (by rfl)
abbrev ai626 : Mgr := ao625
abbrev ao626 : Mgr := {ai626 with ops := ai626.ops+1}
theorem a626 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.xor 0 1 ai626 1 ao626 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 0) (b0 := 1) (r := 1) (op := PCSDD.BOp.xor) (m := ai626) (by decide) (by rfl)
abbrev an624 : Mgr := ao626
abbrev ao624 : Mgr := {an624 with memo := ((PCSDD.BOp.xor,0,131),131)::an624.memo}
theorem a624 : ApplyCertificate 12 DEFAULT_LIMITS 19 PCSDD.BOp.xor 0 131 ai624 131 ao624 := by
  exact ApplyCertificate.branch (fuel := 18) (a0 := 0) (b0 := 131) (lo := 72) (hi := 1) (r := 131) (op := PCSDD.BOp.xor) (m := ai624) (m1 := ao625) (m2 := ao626) (m3 := an624) (by decide) (by rfl) (by decide) a625 a626 (by rfl)
abbrev an620 : Mgr := ao624
abbrev ao620 : Mgr := {an620 with memo := ((PCSDD.BOp.xor,0,132),132)::an620.memo}
theorem a620 : ApplyCertificate 12 DEFAULT_LIMITS 20 PCSDD.BOp.xor 0 132 ai620 132 ao620 := by
  exact ApplyCertificate.branch (fuel := 19) (a0 := 0) (b0 := 132) (lo := 130) (hi := 131) (r := 132) (op := PCSDD.BOp.xor) (m := ai620) (m1 := ao621) (m2 := ao624) (m3 := an620) (by decide) (by rfl) (by decide) a621 a624 (by rfl)
abbrev an612 : Mgr := ao620
abbrev ao612 : Mgr := {an612 with memo := ((PCSDD.BOp.xor,0,133),133)::an612.memo}
theorem a612 : ApplyCertificate 12 DEFAULT_LIMITS 21 PCSDD.BOp.xor 0 133 ai612 133 ao612 := by
  exact ApplyCertificate.branch (fuel := 20) (a0 := 0) (b0 := 133) (lo := 129) (hi := 132) (r := 133) (op := PCSDD.BOp.xor) (m := ai612) (m1 := ao613) (m2 := ao620) (m3 := an612) (by decide) (by rfl) (by decide) a613 a620 (by rfl)
abbrev ai627 : Mgr := ao612
abbrev ai628 : Mgr := {ai627 with ops := ai627.ops+1}
abbrev ai629 : Mgr := {ai628 with ops := ai628.ops+1}
abbrev ai630 : Mgr := {ai629 with ops := ai629.ops+1}
abbrev ao630 : Mgr := {ai630 with ops := ai630.ops+1}
theorem a630 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.xor 0 75 ai630 75 ao630 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 0) (b0 := 75) (r := 75) (op := PCSDD.BOp.xor) (m := ai630) (by decide) (by rfl)
abbrev ai631 : Mgr := ao630
abbrev ao631 : Mgr := {ai631 with ops := ai631.ops+1}
theorem a631 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.xor 0 1 ai631 1 ao631 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 0) (b0 := 1) (r := 1) (op := PCSDD.BOp.xor) (m := ai631) (by decide) (by rfl)
abbrev an629 : Mgr := ao631
abbrev ao629 : Mgr := {an629 with memo := ((PCSDD.BOp.xor,0,134),134)::an629.memo}
theorem a629 : ApplyCertificate 12 DEFAULT_LIMITS 19 PCSDD.BOp.xor 0 134 ai629 134 ao629 := by
  exact ApplyCertificate.branch (fuel := 18) (a0 := 0) (b0 := 134) (lo := 75) (hi := 1) (r := 134) (op := PCSDD.BOp.xor) (m := ai629) (m1 := ao630) (m2 := ao631) (m3 := an629) (by decide) (by rfl) (by decide) a630 a631 (by rfl)
abbrev ai632 : Mgr := ao629
abbrev ai633 : Mgr := {ai632 with ops := ai632.ops+1}
abbrev ao633 : Mgr := {ai633 with ops := ai633.ops+1}
theorem a633 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.xor 0 76 ai633 76 ao633 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 0) (b0 := 76) (r := 76) (op := PCSDD.BOp.xor) (m := ai633) (by decide) (by rfl)
abbrev ai634 : Mgr := ao633
abbrev ao634 : Mgr := {ai634 with ops := ai634.ops+1}
theorem a634 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.xor 0 1 ai634 1 ao634 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 0) (b0 := 1) (r := 1) (op := PCSDD.BOp.xor) (m := ai634) (by decide) (by rfl)
abbrev an632 : Mgr := ao634
abbrev ao632 : Mgr := {an632 with memo := ((PCSDD.BOp.xor,0,135),135)::an632.memo}
theorem a632 : ApplyCertificate 12 DEFAULT_LIMITS 19 PCSDD.BOp.xor 0 135 ai632 135 ao632 := by
  exact ApplyCertificate.branch (fuel := 18) (a0 := 0) (b0 := 135) (lo := 76) (hi := 1) (r := 135) (op := PCSDD.BOp.xor) (m := ai632) (m1 := ao633) (m2 := ao634) (m3 := an632) (by decide) (by rfl) (by decide) a633 a634 (by rfl)
abbrev an628 : Mgr := ao632
abbrev ao628 : Mgr := {an628 with memo := ((PCSDD.BOp.xor,0,136),136)::an628.memo}
theorem a628 : ApplyCertificate 12 DEFAULT_LIMITS 20 PCSDD.BOp.xor 0 136 ai628 136 ao628 := by
  exact ApplyCertificate.branch (fuel := 19) (a0 := 0) (b0 := 136) (lo := 134) (hi := 135) (r := 136) (op := PCSDD.BOp.xor) (m := ai628) (m1 := ao629) (m2 := ao632) (m3 := an628) (by decide) (by rfl) (by decide) a629 a632 (by rfl)
abbrev ai635 : Mgr := ao628
abbrev ai636 : Mgr := {ai635 with ops := ai635.ops+1}
abbrev ai637 : Mgr := {ai636 with ops := ai636.ops+1}
abbrev ao637 : Mgr := {ai637 with ops := ai637.ops+1}
theorem a637 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.xor 0 78 ai637 78 ao637 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 0) (b0 := 78) (r := 78) (op := PCSDD.BOp.xor) (m := ai637) (by decide) (by rfl)
abbrev ai638 : Mgr := ao637
abbrev ao638 : Mgr := {ai638 with ops := ai638.ops+1}
theorem a638 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.xor 0 1 ai638 1 ao638 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 0) (b0 := 1) (r := 1) (op := PCSDD.BOp.xor) (m := ai638) (by decide) (by rfl)
abbrev an636 : Mgr := ao638
abbrev ao636 : Mgr := {an636 with memo := ((PCSDD.BOp.xor,0,137),137)::an636.memo}
theorem a636 : ApplyCertificate 12 DEFAULT_LIMITS 19 PCSDD.BOp.xor 0 137 ai636 137 ao636 := by
  exact ApplyCertificate.branch (fuel := 18) (a0 := 0) (b0 := 137) (lo := 78) (hi := 1) (r := 137) (op := PCSDD.BOp.xor) (m := ai636) (m1 := ao637) (m2 := ao638) (m3 := an636) (by decide) (by rfl) (by decide) a637 a638 (by rfl)
abbrev ai639 : Mgr := ao636
abbrev ai640 : Mgr := {ai639 with ops := ai639.ops+1}
abbrev ao640 : Mgr := {ai640 with ops := ai640.ops+1}
theorem a640 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.xor 0 79 ai640 79 ao640 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 0) (b0 := 79) (r := 79) (op := PCSDD.BOp.xor) (m := ai640) (by decide) (by rfl)
abbrev ai641 : Mgr := ao640
abbrev ao641 : Mgr := {ai641 with ops := ai641.ops+1}
theorem a641 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.xor 0 1 ai641 1 ao641 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 0) (b0 := 1) (r := 1) (op := PCSDD.BOp.xor) (m := ai641) (by decide) (by rfl)
abbrev an639 : Mgr := ao641
abbrev ao639 : Mgr := {an639 with memo := ((PCSDD.BOp.xor,0,138),138)::an639.memo}
theorem a639 : ApplyCertificate 12 DEFAULT_LIMITS 19 PCSDD.BOp.xor 0 138 ai639 138 ao639 := by
  exact ApplyCertificate.branch (fuel := 18) (a0 := 0) (b0 := 138) (lo := 79) (hi := 1) (r := 138) (op := PCSDD.BOp.xor) (m := ai639) (m1 := ao640) (m2 := ao641) (m3 := an639) (by decide) (by rfl) (by decide) a640 a641 (by rfl)
abbrev an635 : Mgr := ao639
abbrev ao635 : Mgr := {an635 with memo := ((PCSDD.BOp.xor,0,139),139)::an635.memo}
theorem a635 : ApplyCertificate 12 DEFAULT_LIMITS 20 PCSDD.BOp.xor 0 139 ai635 139 ao635 := by
  exact ApplyCertificate.branch (fuel := 19) (a0 := 0) (b0 := 139) (lo := 137) (hi := 138) (r := 139) (op := PCSDD.BOp.xor) (m := ai635) (m1 := ao636) (m2 := ao639) (m3 := an635) (by decide) (by rfl) (by decide) a636 a639 (by rfl)
abbrev an627 : Mgr := ao635
abbrev ao627 : Mgr := {an627 with memo := ((PCSDD.BOp.xor,0,140),140)::an627.memo}
theorem a627 : ApplyCertificate 12 DEFAULT_LIMITS 21 PCSDD.BOp.xor 0 140 ai627 140 ao627 := by
  exact ApplyCertificate.branch (fuel := 20) (a0 := 0) (b0 := 140) (lo := 136) (hi := 139) (r := 140) (op := PCSDD.BOp.xor) (m := ai627) (m1 := ao628) (m2 := ao635) (m3 := an627) (by decide) (by rfl) (by decide) a628 a635 (by rfl)
abbrev an611 : Mgr := ao627
abbrev ao611 : Mgr := {an611 with memo := ((PCSDD.BOp.xor,0,141),141)::an611.memo}
theorem a611 : ApplyCertificate 12 DEFAULT_LIMITS 22 PCSDD.BOp.xor 0 141 ai611 141 ao611 := by
  exact ApplyCertificate.branch (fuel := 21) (a0 := 0) (b0 := 141) (lo := 133) (hi := 140) (r := 141) (op := PCSDD.BOp.xor) (m := ai611) (m1 := ao612) (m2 := ao627) (m3 := an611) (by decide) (by rfl) (by decide) a612 a627 (by rfl)
abbrev an579 : Mgr := ao611
abbrev ao579 : Mgr := {an579 with memo := ((PCSDD.BOp.xor,0,142),142)::an579.memo}
theorem a579 : ApplyCertificate 12 DEFAULT_LIMITS 23 PCSDD.BOp.xor 0 142 ai579 142 ao579 := by
  exact ApplyCertificate.branch (fuel := 22) (a0 := 0) (b0 := 142) (lo := 127) (hi := 141) (r := 142) (op := PCSDD.BOp.xor) (m := ai579) (m1 := ao580) (m2 := ao611) (m3 := an579) (by decide) (by rfl) (by decide) a580 a611 (by rfl)
abbrev an515 : Mgr := ao579
abbrev ao515 : Mgr := {an515 with memo := ((PCSDD.BOp.xor,0,143),143)::an515.memo}
theorem a515 : ApplyCertificate 12 DEFAULT_LIMITS 24 PCSDD.BOp.xor 0 143 ai515 143 ao515 := by
  exact ApplyCertificate.branch (fuel := 23) (a0 := 0) (b0 := 143) (lo := 113) (hi := 142) (r := 143) (op := PCSDD.BOp.xor) (m := ai515) (m1 := ao516) (m2 := ao579) (m3 := an515) (by decide) (by rfl) (by decide) a516 a579 (by rfl)
abbrev an389 : Mgr := ao515
abbrev ao389 : Mgr := {an389 with memo := ((PCSDD.BOp.xor,0,144),144)::an389.memo}
theorem a389 : ApplyCertificate 12 DEFAULT_LIMITS 25 PCSDD.BOp.xor 144 0 ai389 144 ao389 := by
  exact ApplyCertificate.branch (fuel := 24) (a0 := 144) (b0 := 0) (lo := 84) (hi := 143) (r := 144) (op := PCSDD.BOp.xor) (m := ai389) (m1 := ao390) (m2 := ao515) (m3 := an389) (by decide) (by rfl) (by decide) a390 a515 (by rfl)
abbrev ai642 : Mgr := ao389
abbrev ai643 : Mgr := {ai642 with ops := ai642.ops+1}
abbrev ai644 : Mgr := {ai643 with ops := ai643.ops+1}
abbrev ai645 : Mgr := {ai644 with ops := ai644.ops+1}
abbrev ai646 : Mgr := {ai645 with ops := ai645.ops+1}
abbrev ai647 : Mgr := {ai646 with ops := ai646.ops+1}
abbrev ai648 : Mgr := {ai647 with ops := ai647.ops+1}
abbrev ao648 : Mgr := {ai648 with ops := ai648.ops+1}
theorem a648 : ApplyCertificate 12 DEFAULT_LIMITS 19 PCSDD.BOp.and 1 0 ai648 0 ao648 := by
  exact ApplyCertificate.hit (fuel := 18) (a0 := 1) (b0 := 0) (r := 0) (op := PCSDD.BOp.and) (m := ai648) (by decide) (by rfl)
abbrev ai649 : Mgr := ao648
abbrev ao649 : Mgr := {ai649 with ops := ai649.ops+1}
theorem a649 : ApplyCertificate 12 DEFAULT_LIMITS 19 PCSDD.BOp.and 1 28 ai649 28 ao649 := by
  exact ApplyCertificate.hit (fuel := 18) (a0 := 1) (b0 := 28) (r := 28) (op := PCSDD.BOp.and) (m := ai649) (by decide) (by rfl)
abbrev an647 : Mgr := ao649
abbrev ao647 : Mgr := {an647 with memo := ((PCSDD.BOp.and,1,29),29)::an647.memo}
theorem a647 : ApplyCertificate 12 DEFAULT_LIMITS 20 PCSDD.BOp.and 1 29 ai647 29 ao647 := by
  exact ApplyCertificate.branch (fuel := 19) (a0 := 1) (b0 := 29) (lo := 0) (hi := 28) (r := 29) (op := PCSDD.BOp.and) (m := ai647) (m1 := ao648) (m2 := ao649) (m3 := an647) (by decide) (by rfl) (by decide) a648 a649 (by rfl)
abbrev ai650 : Mgr := ao647
abbrev ai651 : Mgr := {ai650 with ops := ai650.ops+1}
abbrev ao651 : Mgr := {ai651 with ops := ai651.ops+1}
theorem a651 : ApplyCertificate 12 DEFAULT_LIMITS 19 PCSDD.BOp.and 1 25 ai651 25 ao651 := by
  exact ApplyCertificate.hit (fuel := 18) (a0 := 1) (b0 := 25) (r := 25) (op := PCSDD.BOp.and) (m := ai651) (by decide) (by rfl)
abbrev ai652 : Mgr := ao651
abbrev ai653 : Mgr := {ai652 with ops := ai652.ops+1}
abbrev ao653 : Mgr := {ai653 with ops := ai653.ops+1}
theorem a653 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.and 1 28 ai653 28 ao653 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 1) (b0 := 28) (r := 28) (op := PCSDD.BOp.and) (m := ai653) (by decide) (by rfl)
abbrev ai654 : Mgr := ao653
abbrev ao654 : Mgr := {ai654 with ops := ai654.ops+1}
theorem a654 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.and 1 1 ai654 1 ao654 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 1) (b0 := 1) (r := 1) (op := PCSDD.BOp.and) (m := ai654) (by decide) (by rfl)
abbrev an652 : Mgr := ao654
abbrev ao652 : Mgr := {an652 with memo := ((PCSDD.BOp.and,1,30),30)::an652.memo}
theorem a652 : ApplyCertificate 12 DEFAULT_LIMITS 19 PCSDD.BOp.and 1 30 ai652 30 ao652 := by
  exact ApplyCertificate.branch (fuel := 18) (a0 := 1) (b0 := 30) (lo := 28) (hi := 1) (r := 30) (op := PCSDD.BOp.and) (m := ai652) (m1 := ao653) (m2 := ao654) (m3 := an652) (by decide) (by rfl) (by decide) a653 a654 (by rfl)
abbrev an650 : Mgr := ao652
abbrev ao650 : Mgr := {an650 with memo := ((PCSDD.BOp.and,1,31),31)::an650.memo}
theorem a650 : ApplyCertificate 12 DEFAULT_LIMITS 20 PCSDD.BOp.and 1 31 ai650 31 ao650 := by
  exact ApplyCertificate.branch (fuel := 19) (a0 := 1) (b0 := 31) (lo := 25) (hi := 30) (r := 31) (op := PCSDD.BOp.and) (m := ai650) (m1 := ao651) (m2 := ao652) (m3 := an650) (by decide) (by rfl) (by decide) a651 a652 (by rfl)
abbrev an646 : Mgr := ao650
abbrev ao646 : Mgr := {an646 with memo := ((PCSDD.BOp.and,1,32),32)::an646.memo}
theorem a646 : ApplyCertificate 12 DEFAULT_LIMITS 21 PCSDD.BOp.and 1 32 ai646 32 ao646 := by
  exact ApplyCertificate.branch (fuel := 20) (a0 := 1) (b0 := 32) (lo := 29) (hi := 31) (r := 32) (op := PCSDD.BOp.and) (m := ai646) (m1 := ao647) (m2 := ao650) (m3 := an646) (by decide) (by rfl) (by decide) a647 a650 (by rfl)
abbrev ai655 : Mgr := ao646
abbrev ai656 : Mgr := {ai655 with ops := ai655.ops+1}
abbrev ai657 : Mgr := {ai656 with ops := ai656.ops+1}
abbrev ao657 : Mgr := {ai657 with ops := ai657.ops+1}
theorem a657 : ApplyCertificate 12 DEFAULT_LIMITS 19 PCSDD.BOp.and 1 22 ai657 22 ao657 := by
  exact ApplyCertificate.hit (fuel := 18) (a0 := 1) (b0 := 22) (r := 22) (op := PCSDD.BOp.and) (m := ai657) (by decide) (by rfl)
abbrev ai658 : Mgr := ao657
abbrev ai659 : Mgr := {ai658 with ops := ai658.ops+1}
abbrev ao659 : Mgr := {ai659 with ops := ai659.ops+1}
theorem a659 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.and 1 28 ai659 28 ao659 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 1) (b0 := 28) (r := 28) (op := PCSDD.BOp.and) (m := ai659) (by decide) (by rfl)
abbrev ai660 : Mgr := ao659
abbrev ao660 : Mgr := {ai660 with ops := ai660.ops+1}
theorem a660 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.and 1 1 ai660 1 ao660 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 1) (b0 := 1) (r := 1) (op := PCSDD.BOp.and) (m := ai660) (by decide) (by rfl)
abbrev an658 : Mgr := ao660
abbrev ao658 : Mgr := {an658 with memo := ((PCSDD.BOp.and,1,33),33)::an658.memo}
theorem a658 : ApplyCertificate 12 DEFAULT_LIMITS 19 PCSDD.BOp.and 1 33 ai658 33 ao658 := by
  exact ApplyCertificate.branch (fuel := 18) (a0 := 1) (b0 := 33) (lo := 28) (hi := 1) (r := 33) (op := PCSDD.BOp.and) (m := ai658) (m1 := ao659) (m2 := ao660) (m3 := an658) (by decide) (by rfl) (by decide) a659 a660 (by rfl)
abbrev an656 : Mgr := ao658
abbrev ao656 : Mgr := {an656 with memo := ((PCSDD.BOp.and,1,34),34)::an656.memo}
theorem a656 : ApplyCertificate 12 DEFAULT_LIMITS 20 PCSDD.BOp.and 1 34 ai656 34 ao656 := by
  exact ApplyCertificate.branch (fuel := 19) (a0 := 1) (b0 := 34) (lo := 22) (hi := 33) (r := 34) (op := PCSDD.BOp.and) (m := ai656) (m1 := ao657) (m2 := ao658) (m3 := an656) (by decide) (by rfl) (by decide) a657 a658 (by rfl)
abbrev ai661 : Mgr := ao656
abbrev ai662 : Mgr := {ai661 with ops := ai661.ops+1}
abbrev ai663 : Mgr := {ai662 with ops := ai662.ops+1}
abbrev ao663 : Mgr := {ai663 with ops := ai663.ops+1}
theorem a663 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.and 1 25 ai663 25 ao663 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 1) (b0 := 25) (r := 25) (op := PCSDD.BOp.and) (m := ai663) (by decide) (by rfl)
abbrev ai664 : Mgr := ao663
abbrev ao664 : Mgr := {ai664 with ops := ai664.ops+1}
theorem a664 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.and 1 1 ai664 1 ao664 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 1) (b0 := 1) (r := 1) (op := PCSDD.BOp.and) (m := ai664) (by decide) (by rfl)
abbrev an662 : Mgr := ao664
abbrev ao662 : Mgr := {an662 with memo := ((PCSDD.BOp.and,1,35),35)::an662.memo}
theorem a662 : ApplyCertificate 12 DEFAULT_LIMITS 19 PCSDD.BOp.and 1 35 ai662 35 ao662 := by
  exact ApplyCertificate.branch (fuel := 18) (a0 := 1) (b0 := 35) (lo := 25) (hi := 1) (r := 35) (op := PCSDD.BOp.and) (m := ai662) (m1 := ao663) (m2 := ao664) (m3 := an662) (by decide) (by rfl) (by decide) a663 a664 (by rfl)
abbrev ai665 : Mgr := ao662
abbrev ai666 : Mgr := {ai665 with ops := ai665.ops+1}
abbrev ao666 : Mgr := {ai666 with ops := ai666.ops+1}
theorem a666 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.and 1 30 ai666 30 ao666 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 1) (b0 := 30) (r := 30) (op := PCSDD.BOp.and) (m := ai666) (by decide) (by rfl)
abbrev ai667 : Mgr := ao666
abbrev ao667 : Mgr := {ai667 with ops := ai667.ops+1}
theorem a667 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.and 1 1 ai667 1 ao667 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 1) (b0 := 1) (r := 1) (op := PCSDD.BOp.and) (m := ai667) (by decide) (by rfl)
abbrev an665 : Mgr := ao667
abbrev ao665 : Mgr := {an665 with memo := ((PCSDD.BOp.and,1,36),36)::an665.memo}
theorem a665 : ApplyCertificate 12 DEFAULT_LIMITS 19 PCSDD.BOp.and 1 36 ai665 36 ao665 := by
  exact ApplyCertificate.branch (fuel := 18) (a0 := 1) (b0 := 36) (lo := 30) (hi := 1) (r := 36) (op := PCSDD.BOp.and) (m := ai665) (m1 := ao666) (m2 := ao667) (m3 := an665) (by decide) (by rfl) (by decide) a666 a667 (by rfl)
abbrev an661 : Mgr := ao665
abbrev ao661 : Mgr := {an661 with memo := ((PCSDD.BOp.and,1,37),37)::an661.memo}
theorem a661 : ApplyCertificate 12 DEFAULT_LIMITS 20 PCSDD.BOp.and 1 37 ai661 37 ao661 := by
  exact ApplyCertificate.branch (fuel := 19) (a0 := 1) (b0 := 37) (lo := 35) (hi := 36) (r := 37) (op := PCSDD.BOp.and) (m := ai661) (m1 := ao662) (m2 := ao665) (m3 := an661) (by decide) (by rfl) (by decide) a662 a665 (by rfl)
abbrev an655 : Mgr := ao661
abbrev ao655 : Mgr := {an655 with memo := ((PCSDD.BOp.and,1,38),38)::an655.memo}
theorem a655 : ApplyCertificate 12 DEFAULT_LIMITS 21 PCSDD.BOp.and 1 38 ai655 38 ao655 := by
  exact ApplyCertificate.branch (fuel := 20) (a0 := 1) (b0 := 38) (lo := 34) (hi := 37) (r := 38) (op := PCSDD.BOp.and) (m := ai655) (m1 := ao656) (m2 := ao661) (m3 := an655) (by decide) (by rfl) (by decide) a656 a661 (by rfl)
abbrev an645 : Mgr := ao655
abbrev ao645 : Mgr := {an645 with memo := ((PCSDD.BOp.and,1,39),39)::an645.memo}
theorem a645 : ApplyCertificate 12 DEFAULT_LIMITS 22 PCSDD.BOp.and 1 39 ai645 39 ao645 := by
  exact ApplyCertificate.branch (fuel := 21) (a0 := 1) (b0 := 39) (lo := 32) (hi := 38) (r := 39) (op := PCSDD.BOp.and) (m := ai645) (m1 := ao646) (m2 := ao655) (m3 := an645) (by decide) (by rfl) (by decide) a646 a655 (by rfl)
abbrev ai668 : Mgr := ao645
abbrev ai669 : Mgr := {ai668 with ops := ai668.ops+1}
abbrev ai670 : Mgr := {ai669 with ops := ai669.ops+1}
abbrev ai671 : Mgr := {ai670 with ops := ai670.ops+1}
abbrev ao671 : Mgr := {ai671 with ops := ai671.ops+1}
theorem a671 : ApplyCertificate 12 DEFAULT_LIMITS 19 PCSDD.BOp.and 1 9 ai671 9 ao671 := by
  exact ApplyCertificate.hit (fuel := 18) (a0 := 1) (b0 := 9) (r := 9) (op := PCSDD.BOp.and) (m := ai671) (by decide) (by rfl)
abbrev ai672 : Mgr := ao671
abbrev ai673 : Mgr := {ai672 with ops := ai672.ops+1}
abbrev ao673 : Mgr := {ai673 with ops := ai673.ops+1}
theorem a673 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.and 1 28 ai673 28 ao673 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 1) (b0 := 28) (r := 28) (op := PCSDD.BOp.and) (m := ai673) (by decide) (by rfl)
abbrev ai674 : Mgr := ao673
abbrev ao674 : Mgr := {ai674 with ops := ai674.ops+1}
theorem a674 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.and 1 1 ai674 1 ao674 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 1) (b0 := 1) (r := 1) (op := PCSDD.BOp.and) (m := ai674) (by decide) (by rfl)
abbrev an672 : Mgr := ao674
abbrev ao672 : Mgr := {an672 with memo := ((PCSDD.BOp.and,1,40),40)::an672.memo}
theorem a672 : ApplyCertificate 12 DEFAULT_LIMITS 19 PCSDD.BOp.and 1 40 ai672 40 ao672 := by
  exact ApplyCertificate.branch (fuel := 18) (a0 := 1) (b0 := 40) (lo := 28) (hi := 1) (r := 40) (op := PCSDD.BOp.and) (m := ai672) (m1 := ao673) (m2 := ao674) (m3 := an672) (by decide) (by rfl) (by decide) a673 a674 (by rfl)
abbrev an670 : Mgr := ao672
abbrev ao670 : Mgr := {an670 with memo := ((PCSDD.BOp.and,1,41),41)::an670.memo}
theorem a670 : ApplyCertificate 12 DEFAULT_LIMITS 20 PCSDD.BOp.and 1 41 ai670 41 ao670 := by
  exact ApplyCertificate.branch (fuel := 19) (a0 := 1) (b0 := 41) (lo := 9) (hi := 40) (r := 41) (op := PCSDD.BOp.and) (m := ai670) (m1 := ao671) (m2 := ao672) (m3 := an670) (by decide) (by rfl) (by decide) a671 a672 (by rfl)
abbrev ai675 : Mgr := ao670
abbrev ai676 : Mgr := {ai675 with ops := ai675.ops+1}
abbrev ai677 : Mgr := {ai676 with ops := ai676.ops+1}
abbrev ao677 : Mgr := {ai677 with ops := ai677.ops+1}
theorem a677 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.and 1 25 ai677 25 ao677 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 1) (b0 := 25) (r := 25) (op := PCSDD.BOp.and) (m := ai677) (by decide) (by rfl)
abbrev ai678 : Mgr := ao677
abbrev ao678 : Mgr := {ai678 with ops := ai678.ops+1}
theorem a678 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.and 1 1 ai678 1 ao678 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 1) (b0 := 1) (r := 1) (op := PCSDD.BOp.and) (m := ai678) (by decide) (by rfl)
abbrev an676 : Mgr := ao678
abbrev ao676 : Mgr := {an676 with memo := ((PCSDD.BOp.and,1,42),42)::an676.memo}
theorem a676 : ApplyCertificate 12 DEFAULT_LIMITS 19 PCSDD.BOp.and 1 42 ai676 42 ao676 := by
  exact ApplyCertificate.branch (fuel := 18) (a0 := 1) (b0 := 42) (lo := 25) (hi := 1) (r := 42) (op := PCSDD.BOp.and) (m := ai676) (m1 := ao677) (m2 := ao678) (m3 := an676) (by decide) (by rfl) (by decide) a677 a678 (by rfl)
abbrev ai679 : Mgr := ao676
abbrev ai680 : Mgr := {ai679 with ops := ai679.ops+1}
abbrev ao680 : Mgr := {ai680 with ops := ai680.ops+1}
theorem a680 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.and 1 30 ai680 30 ao680 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 1) (b0 := 30) (r := 30) (op := PCSDD.BOp.and) (m := ai680) (by decide) (by rfl)
abbrev ai681 : Mgr := ao680
abbrev ao681 : Mgr := {ai681 with ops := ai681.ops+1}
theorem a681 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.and 1 1 ai681 1 ao681 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 1) (b0 := 1) (r := 1) (op := PCSDD.BOp.and) (m := ai681) (by decide) (by rfl)
abbrev an679 : Mgr := ao681
abbrev ao679 : Mgr := {an679 with memo := ((PCSDD.BOp.and,1,43),43)::an679.memo}
theorem a679 : ApplyCertificate 12 DEFAULT_LIMITS 19 PCSDD.BOp.and 1 43 ai679 43 ao679 := by
  exact ApplyCertificate.branch (fuel := 18) (a0 := 1) (b0 := 43) (lo := 30) (hi := 1) (r := 43) (op := PCSDD.BOp.and) (m := ai679) (m1 := ao680) (m2 := ao681) (m3 := an679) (by decide) (by rfl) (by decide) a680 a681 (by rfl)
abbrev an675 : Mgr := ao679
abbrev ao675 : Mgr := {an675 with memo := ((PCSDD.BOp.and,1,44),44)::an675.memo}
theorem a675 : ApplyCertificate 12 DEFAULT_LIMITS 20 PCSDD.BOp.and 1 44 ai675 44 ao675 := by
  exact ApplyCertificate.branch (fuel := 19) (a0 := 1) (b0 := 44) (lo := 42) (hi := 43) (r := 44) (op := PCSDD.BOp.and) (m := ai675) (m1 := ao676) (m2 := ao679) (m3 := an675) (by decide) (by rfl) (by decide) a676 a679 (by rfl)
abbrev an669 : Mgr := ao675
abbrev ao669 : Mgr := {an669 with memo := ((PCSDD.BOp.and,1,45),45)::an669.memo}
theorem a669 : ApplyCertificate 12 DEFAULT_LIMITS 21 PCSDD.BOp.and 1 45 ai669 45 ao669 := by
  exact ApplyCertificate.branch (fuel := 20) (a0 := 1) (b0 := 45) (lo := 41) (hi := 44) (r := 45) (op := PCSDD.BOp.and) (m := ai669) (m1 := ao670) (m2 := ao675) (m3 := an669) (by decide) (by rfl) (by decide) a670 a675 (by rfl)
abbrev ai682 : Mgr := ao669
abbrev ai683 : Mgr := {ai682 with ops := ai682.ops+1}
abbrev ai684 : Mgr := {ai683 with ops := ai683.ops+1}
abbrev ai685 : Mgr := {ai684 with ops := ai684.ops+1}
abbrev ao685 : Mgr := {ai685 with ops := ai685.ops+1}
theorem a685 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.and 1 22 ai685 22 ao685 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 1) (b0 := 22) (r := 22) (op := PCSDD.BOp.and) (m := ai685) (by decide) (by rfl)
abbrev ai686 : Mgr := ao685
abbrev ao686 : Mgr := {ai686 with ops := ai686.ops+1}
theorem a686 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.and 1 1 ai686 1 ao686 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 1) (b0 := 1) (r := 1) (op := PCSDD.BOp.and) (m := ai686) (by decide) (by rfl)
abbrev an684 : Mgr := ao686
abbrev ao684 : Mgr := {an684 with memo := ((PCSDD.BOp.and,1,46),46)::an684.memo}
theorem a684 : ApplyCertificate 12 DEFAULT_LIMITS 19 PCSDD.BOp.and 1 46 ai684 46 ao684 := by
  exact ApplyCertificate.branch (fuel := 18) (a0 := 1) (b0 := 46) (lo := 22) (hi := 1) (r := 46) (op := PCSDD.BOp.and) (m := ai684) (m1 := ao685) (m2 := ao686) (m3 := an684) (by decide) (by rfl) (by decide) a685 a686 (by rfl)
abbrev ai687 : Mgr := ao684
abbrev ai688 : Mgr := {ai687 with ops := ai687.ops+1}
abbrev ao688 : Mgr := {ai688 with ops := ai688.ops+1}
theorem a688 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.and 1 33 ai688 33 ao688 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 1) (b0 := 33) (r := 33) (op := PCSDD.BOp.and) (m := ai688) (by decide) (by rfl)
abbrev ai689 : Mgr := ao688
abbrev ao689 : Mgr := {ai689 with ops := ai689.ops+1}
theorem a689 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.and 1 1 ai689 1 ao689 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 1) (b0 := 1) (r := 1) (op := PCSDD.BOp.and) (m := ai689) (by decide) (by rfl)
abbrev an687 : Mgr := ao689
abbrev ao687 : Mgr := {an687 with memo := ((PCSDD.BOp.and,1,47),47)::an687.memo}
theorem a687 : ApplyCertificate 12 DEFAULT_LIMITS 19 PCSDD.BOp.and 1 47 ai687 47 ao687 := by
  exact ApplyCertificate.branch (fuel := 18) (a0 := 1) (b0 := 47) (lo := 33) (hi := 1) (r := 47) (op := PCSDD.BOp.and) (m := ai687) (m1 := ao688) (m2 := ao689) (m3 := an687) (by decide) (by rfl) (by decide) a688 a689 (by rfl)
abbrev an683 : Mgr := ao687
abbrev ao683 : Mgr := {an683 with memo := ((PCSDD.BOp.and,1,48),48)::an683.memo}
theorem a683 : ApplyCertificate 12 DEFAULT_LIMITS 20 PCSDD.BOp.and 1 48 ai683 48 ao683 := by
  exact ApplyCertificate.branch (fuel := 19) (a0 := 1) (b0 := 48) (lo := 46) (hi := 47) (r := 48) (op := PCSDD.BOp.and) (m := ai683) (m1 := ao684) (m2 := ao687) (m3 := an683) (by decide) (by rfl) (by decide) a684 a687 (by rfl)
abbrev ai690 : Mgr := ao683
abbrev ai691 : Mgr := {ai690 with ops := ai690.ops+1}
abbrev ai692 : Mgr := {ai691 with ops := ai691.ops+1}
abbrev ao692 : Mgr := {ai692 with ops := ai692.ops+1}
theorem a692 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.and 1 35 ai692 35 ao692 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 1) (b0 := 35) (r := 35) (op := PCSDD.BOp.and) (m := ai692) (by decide) (by rfl)
abbrev ai693 : Mgr := ao692
abbrev ao693 : Mgr := {ai693 with ops := ai693.ops+1}
theorem a693 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.and 1 1 ai693 1 ao693 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 1) (b0 := 1) (r := 1) (op := PCSDD.BOp.and) (m := ai693) (by decide) (by rfl)
abbrev an691 : Mgr := ao693
abbrev ao691 : Mgr := {an691 with memo := ((PCSDD.BOp.and,1,49),49)::an691.memo}
theorem a691 : ApplyCertificate 12 DEFAULT_LIMITS 19 PCSDD.BOp.and 1 49 ai691 49 ao691 := by
  exact ApplyCertificate.branch (fuel := 18) (a0 := 1) (b0 := 49) (lo := 35) (hi := 1) (r := 49) (op := PCSDD.BOp.and) (m := ai691) (m1 := ao692) (m2 := ao693) (m3 := an691) (by decide) (by rfl) (by decide) a692 a693 (by rfl)
abbrev ai694 : Mgr := ao691
abbrev ai695 : Mgr := {ai694 with ops := ai694.ops+1}
abbrev ao695 : Mgr := {ai695 with ops := ai695.ops+1}
theorem a695 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.and 1 36 ai695 36 ao695 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 1) (b0 := 36) (r := 36) (op := PCSDD.BOp.and) (m := ai695) (by decide) (by rfl)
abbrev ai696 : Mgr := ao695
abbrev ao696 : Mgr := {ai696 with ops := ai696.ops+1}
theorem a696 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.and 1 1 ai696 1 ao696 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 1) (b0 := 1) (r := 1) (op := PCSDD.BOp.and) (m := ai696) (by decide) (by rfl)
abbrev an694 : Mgr := ao696
abbrev ao694 : Mgr := {an694 with memo := ((PCSDD.BOp.and,1,50),50)::an694.memo}
theorem a694 : ApplyCertificate 12 DEFAULT_LIMITS 19 PCSDD.BOp.and 1 50 ai694 50 ao694 := by
  exact ApplyCertificate.branch (fuel := 18) (a0 := 1) (b0 := 50) (lo := 36) (hi := 1) (r := 50) (op := PCSDD.BOp.and) (m := ai694) (m1 := ao695) (m2 := ao696) (m3 := an694) (by decide) (by rfl) (by decide) a695 a696 (by rfl)
abbrev an690 : Mgr := ao694
abbrev ao690 : Mgr := {an690 with memo := ((PCSDD.BOp.and,1,51),51)::an690.memo}
theorem a690 : ApplyCertificate 12 DEFAULT_LIMITS 20 PCSDD.BOp.and 1 51 ai690 51 ao690 := by
  exact ApplyCertificate.branch (fuel := 19) (a0 := 1) (b0 := 51) (lo := 49) (hi := 50) (r := 51) (op := PCSDD.BOp.and) (m := ai690) (m1 := ao691) (m2 := ao694) (m3 := an690) (by decide) (by rfl) (by decide) a691 a694 (by rfl)
abbrev an682 : Mgr := ao690
abbrev ao682 : Mgr := {an682 with memo := ((PCSDD.BOp.and,1,52),52)::an682.memo}
theorem a682 : ApplyCertificate 12 DEFAULT_LIMITS 21 PCSDD.BOp.and 1 52 ai682 52 ao682 := by
  exact ApplyCertificate.branch (fuel := 20) (a0 := 1) (b0 := 52) (lo := 48) (hi := 51) (r := 52) (op := PCSDD.BOp.and) (m := ai682) (m1 := ao683) (m2 := ao690) (m3 := an682) (by decide) (by rfl) (by decide) a683 a690 (by rfl)
abbrev an668 : Mgr := ao682
abbrev ao668 : Mgr := {an668 with memo := ((PCSDD.BOp.and,1,53),53)::an668.memo}
theorem a668 : ApplyCertificate 12 DEFAULT_LIMITS 22 PCSDD.BOp.and 1 53 ai668 53 ao668 := by
  exact ApplyCertificate.branch (fuel := 21) (a0 := 1) (b0 := 53) (lo := 45) (hi := 52) (r := 53) (op := PCSDD.BOp.and) (m := ai668) (m1 := ao669) (m2 := ao682) (m3 := an668) (by decide) (by rfl) (by decide) a669 a682 (by rfl)
abbrev an644 : Mgr := ao668
abbrev ao644 : Mgr := {an644 with memo := ((PCSDD.BOp.and,1,54),54)::an644.memo}
theorem a644 : ApplyCertificate 12 DEFAULT_LIMITS 23 PCSDD.BOp.and 1 54 ai644 54 ao644 := by
  exact ApplyCertificate.branch (fuel := 22) (a0 := 1) (b0 := 54) (lo := 39) (hi := 53) (r := 54) (op := PCSDD.BOp.and) (m := ai644) (m1 := ao645) (m2 := ao668) (m3 := an644) (by decide) (by rfl) (by decide) a645 a668 (by rfl)
abbrev ai697 : Mgr := ao644
abbrev ai698 : Mgr := {ai697 with ops := ai697.ops+1}
abbrev ai699 : Mgr := {ai698 with ops := ai698.ops+1}
abbrev ai700 : Mgr := {ai699 with ops := ai699.ops+1}
abbrev ai701 : Mgr := {ai700 with ops := ai700.ops+1}
abbrev ao701 : Mgr := {ai701 with ops := ai701.ops+1}
theorem a701 : ApplyCertificate 12 DEFAULT_LIMITS 19 PCSDD.BOp.and 1 6 ai701 6 ao701 := by
  exact ApplyCertificate.hit (fuel := 18) (a0 := 1) (b0 := 6) (r := 6) (op := PCSDD.BOp.and) (m := ai701) (by decide) (by rfl)
abbrev ai702 : Mgr := ao701
abbrev ai703 : Mgr := {ai702 with ops := ai702.ops+1}
abbrev ao703 : Mgr := {ai703 with ops := ai703.ops+1}
theorem a703 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.and 1 28 ai703 28 ao703 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 1) (b0 := 28) (r := 28) (op := PCSDD.BOp.and) (m := ai703) (by decide) (by rfl)
abbrev ai704 : Mgr := ao703
abbrev ao704 : Mgr := {ai704 with ops := ai704.ops+1}
theorem a704 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.and 1 1 ai704 1 ao704 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 1) (b0 := 1) (r := 1) (op := PCSDD.BOp.and) (m := ai704) (by decide) (by rfl)
abbrev an702 : Mgr := ao704
abbrev ao702 : Mgr := {an702 with memo := ((PCSDD.BOp.and,1,55),55)::an702.memo}
theorem a702 : ApplyCertificate 12 DEFAULT_LIMITS 19 PCSDD.BOp.and 1 55 ai702 55 ao702 := by
  exact ApplyCertificate.branch (fuel := 18) (a0 := 1) (b0 := 55) (lo := 28) (hi := 1) (r := 55) (op := PCSDD.BOp.and) (m := ai702) (m1 := ao703) (m2 := ao704) (m3 := an702) (by decide) (by rfl) (by decide) a703 a704 (by rfl)
abbrev an700 : Mgr := ao702
abbrev ao700 : Mgr := {an700 with memo := ((PCSDD.BOp.and,1,56),56)::an700.memo}
theorem a700 : ApplyCertificate 12 DEFAULT_LIMITS 20 PCSDD.BOp.and 1 56 ai700 56 ao700 := by
  exact ApplyCertificate.branch (fuel := 19) (a0 := 1) (b0 := 56) (lo := 6) (hi := 55) (r := 56) (op := PCSDD.BOp.and) (m := ai700) (m1 := ao701) (m2 := ao702) (m3 := an700) (by decide) (by rfl) (by decide) a701 a702 (by rfl)
abbrev ai705 : Mgr := ao700
abbrev ai706 : Mgr := {ai705 with ops := ai705.ops+1}
abbrev ai707 : Mgr := {ai706 with ops := ai706.ops+1}
abbrev ao707 : Mgr := {ai707 with ops := ai707.ops+1}
theorem a707 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.and 1 25 ai707 25 ao707 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 1) (b0 := 25) (r := 25) (op := PCSDD.BOp.and) (m := ai707) (by decide) (by rfl)
abbrev ai708 : Mgr := ao707
abbrev ao708 : Mgr := {ai708 with ops := ai708.ops+1}
theorem a708 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.and 1 1 ai708 1 ao708 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 1) (b0 := 1) (r := 1) (op := PCSDD.BOp.and) (m := ai708) (by decide) (by rfl)
abbrev an706 : Mgr := ao708
abbrev ao706 : Mgr := {an706 with memo := ((PCSDD.BOp.and,1,57),57)::an706.memo}
theorem a706 : ApplyCertificate 12 DEFAULT_LIMITS 19 PCSDD.BOp.and 1 57 ai706 57 ao706 := by
  exact ApplyCertificate.branch (fuel := 18) (a0 := 1) (b0 := 57) (lo := 25) (hi := 1) (r := 57) (op := PCSDD.BOp.and) (m := ai706) (m1 := ao707) (m2 := ao708) (m3 := an706) (by decide) (by rfl) (by decide) a707 a708 (by rfl)
abbrev ai709 : Mgr := ao706
abbrev ai710 : Mgr := {ai709 with ops := ai709.ops+1}
abbrev ao710 : Mgr := {ai710 with ops := ai710.ops+1}
theorem a710 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.and 1 30 ai710 30 ao710 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 1) (b0 := 30) (r := 30) (op := PCSDD.BOp.and) (m := ai710) (by decide) (by rfl)
abbrev ai711 : Mgr := ao710
abbrev ao711 : Mgr := {ai711 with ops := ai711.ops+1}
theorem a711 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.and 1 1 ai711 1 ao711 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 1) (b0 := 1) (r := 1) (op := PCSDD.BOp.and) (m := ai711) (by decide) (by rfl)
abbrev an709 : Mgr := ao711
abbrev ao709 : Mgr := {an709 with memo := ((PCSDD.BOp.and,1,58),58)::an709.memo}
theorem a709 : ApplyCertificate 12 DEFAULT_LIMITS 19 PCSDD.BOp.and 1 58 ai709 58 ao709 := by
  exact ApplyCertificate.branch (fuel := 18) (a0 := 1) (b0 := 58) (lo := 30) (hi := 1) (r := 58) (op := PCSDD.BOp.and) (m := ai709) (m1 := ao710) (m2 := ao711) (m3 := an709) (by decide) (by rfl) (by decide) a710 a711 (by rfl)
abbrev an705 : Mgr := ao709
abbrev ao705 : Mgr := {an705 with memo := ((PCSDD.BOp.and,1,59),59)::an705.memo}
theorem a705 : ApplyCertificate 12 DEFAULT_LIMITS 20 PCSDD.BOp.and 1 59 ai705 59 ao705 := by
  exact ApplyCertificate.branch (fuel := 19) (a0 := 1) (b0 := 59) (lo := 57) (hi := 58) (r := 59) (op := PCSDD.BOp.and) (m := ai705) (m1 := ao706) (m2 := ao709) (m3 := an705) (by decide) (by rfl) (by decide) a706 a709 (by rfl)
abbrev an699 : Mgr := ao705
abbrev ao699 : Mgr := {an699 with memo := ((PCSDD.BOp.and,1,60),60)::an699.memo}
theorem a699 : ApplyCertificate 12 DEFAULT_LIMITS 21 PCSDD.BOp.and 1 60 ai699 60 ao699 := by
  exact ApplyCertificate.branch (fuel := 20) (a0 := 1) (b0 := 60) (lo := 56) (hi := 59) (r := 60) (op := PCSDD.BOp.and) (m := ai699) (m1 := ao700) (m2 := ao705) (m3 := an699) (by decide) (by rfl) (by decide) a700 a705 (by rfl)
abbrev ai712 : Mgr := ao699
abbrev ai713 : Mgr := {ai712 with ops := ai712.ops+1}
abbrev ai714 : Mgr := {ai713 with ops := ai713.ops+1}
abbrev ai715 : Mgr := {ai714 with ops := ai714.ops+1}
abbrev ao715 : Mgr := {ai715 with ops := ai715.ops+1}
theorem a715 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.and 1 22 ai715 22 ao715 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 1) (b0 := 22) (r := 22) (op := PCSDD.BOp.and) (m := ai715) (by decide) (by rfl)
abbrev ai716 : Mgr := ao715
abbrev ao716 : Mgr := {ai716 with ops := ai716.ops+1}
theorem a716 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.and 1 1 ai716 1 ao716 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 1) (b0 := 1) (r := 1) (op := PCSDD.BOp.and) (m := ai716) (by decide) (by rfl)
abbrev an714 : Mgr := ao716
abbrev ao714 : Mgr := {an714 with memo := ((PCSDD.BOp.and,1,61),61)::an714.memo}
theorem a714 : ApplyCertificate 12 DEFAULT_LIMITS 19 PCSDD.BOp.and 1 61 ai714 61 ao714 := by
  exact ApplyCertificate.branch (fuel := 18) (a0 := 1) (b0 := 61) (lo := 22) (hi := 1) (r := 61) (op := PCSDD.BOp.and) (m := ai714) (m1 := ao715) (m2 := ao716) (m3 := an714) (by decide) (by rfl) (by decide) a715 a716 (by rfl)
abbrev ai717 : Mgr := ao714
abbrev ai718 : Mgr := {ai717 with ops := ai717.ops+1}
abbrev ao718 : Mgr := {ai718 with ops := ai718.ops+1}
theorem a718 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.and 1 33 ai718 33 ao718 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 1) (b0 := 33) (r := 33) (op := PCSDD.BOp.and) (m := ai718) (by decide) (by rfl)
abbrev ai719 : Mgr := ao718
abbrev ao719 : Mgr := {ai719 with ops := ai719.ops+1}
theorem a719 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.and 1 1 ai719 1 ao719 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 1) (b0 := 1) (r := 1) (op := PCSDD.BOp.and) (m := ai719) (by decide) (by rfl)
abbrev an717 : Mgr := ao719
abbrev ao717 : Mgr := {an717 with memo := ((PCSDD.BOp.and,1,62),62)::an717.memo}
theorem a717 : ApplyCertificate 12 DEFAULT_LIMITS 19 PCSDD.BOp.and 1 62 ai717 62 ao717 := by
  exact ApplyCertificate.branch (fuel := 18) (a0 := 1) (b0 := 62) (lo := 33) (hi := 1) (r := 62) (op := PCSDD.BOp.and) (m := ai717) (m1 := ao718) (m2 := ao719) (m3 := an717) (by decide) (by rfl) (by decide) a718 a719 (by rfl)
abbrev an713 : Mgr := ao717
abbrev ao713 : Mgr := {an713 with memo := ((PCSDD.BOp.and,1,63),63)::an713.memo}
theorem a713 : ApplyCertificate 12 DEFAULT_LIMITS 20 PCSDD.BOp.and 1 63 ai713 63 ao713 := by
  exact ApplyCertificate.branch (fuel := 19) (a0 := 1) (b0 := 63) (lo := 61) (hi := 62) (r := 63) (op := PCSDD.BOp.and) (m := ai713) (m1 := ao714) (m2 := ao717) (m3 := an713) (by decide) (by rfl) (by decide) a714 a717 (by rfl)
abbrev ai720 : Mgr := ao713
abbrev ai721 : Mgr := {ai720 with ops := ai720.ops+1}
abbrev ai722 : Mgr := {ai721 with ops := ai721.ops+1}
abbrev ao722 : Mgr := {ai722 with ops := ai722.ops+1}
theorem a722 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.and 1 35 ai722 35 ao722 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 1) (b0 := 35) (r := 35) (op := PCSDD.BOp.and) (m := ai722) (by decide) (by rfl)
abbrev ai723 : Mgr := ao722
abbrev ao723 : Mgr := {ai723 with ops := ai723.ops+1}
theorem a723 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.and 1 1 ai723 1 ao723 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 1) (b0 := 1) (r := 1) (op := PCSDD.BOp.and) (m := ai723) (by decide) (by rfl)
abbrev an721 : Mgr := ao723
abbrev ao721 : Mgr := {an721 with memo := ((PCSDD.BOp.and,1,64),64)::an721.memo}
theorem a721 : ApplyCertificate 12 DEFAULT_LIMITS 19 PCSDD.BOp.and 1 64 ai721 64 ao721 := by
  exact ApplyCertificate.branch (fuel := 18) (a0 := 1) (b0 := 64) (lo := 35) (hi := 1) (r := 64) (op := PCSDD.BOp.and) (m := ai721) (m1 := ao722) (m2 := ao723) (m3 := an721) (by decide) (by rfl) (by decide) a722 a723 (by rfl)
abbrev ai724 : Mgr := ao721
abbrev ai725 : Mgr := {ai724 with ops := ai724.ops+1}
abbrev ao725 : Mgr := {ai725 with ops := ai725.ops+1}
theorem a725 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.and 1 36 ai725 36 ao725 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 1) (b0 := 36) (r := 36) (op := PCSDD.BOp.and) (m := ai725) (by decide) (by rfl)
abbrev ai726 : Mgr := ao725
abbrev ao726 : Mgr := {ai726 with ops := ai726.ops+1}
theorem a726 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.and 1 1 ai726 1 ao726 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 1) (b0 := 1) (r := 1) (op := PCSDD.BOp.and) (m := ai726) (by decide) (by rfl)
abbrev an724 : Mgr := ao726
abbrev ao724 : Mgr := {an724 with memo := ((PCSDD.BOp.and,1,65),65)::an724.memo}
theorem a724 : ApplyCertificate 12 DEFAULT_LIMITS 19 PCSDD.BOp.and 1 65 ai724 65 ao724 := by
  exact ApplyCertificate.branch (fuel := 18) (a0 := 1) (b0 := 65) (lo := 36) (hi := 1) (r := 65) (op := PCSDD.BOp.and) (m := ai724) (m1 := ao725) (m2 := ao726) (m3 := an724) (by decide) (by rfl) (by decide) a725 a726 (by rfl)
abbrev an720 : Mgr := ao724
abbrev ao720 : Mgr := {an720 with memo := ((PCSDD.BOp.and,1,66),66)::an720.memo}
theorem a720 : ApplyCertificate 12 DEFAULT_LIMITS 20 PCSDD.BOp.and 1 66 ai720 66 ao720 := by
  exact ApplyCertificate.branch (fuel := 19) (a0 := 1) (b0 := 66) (lo := 64) (hi := 65) (r := 66) (op := PCSDD.BOp.and) (m := ai720) (m1 := ao721) (m2 := ao724) (m3 := an720) (by decide) (by rfl) (by decide) a721 a724 (by rfl)
abbrev an712 : Mgr := ao720
abbrev ao712 : Mgr := {an712 with memo := ((PCSDD.BOp.and,1,67),67)::an712.memo}
theorem a712 : ApplyCertificate 12 DEFAULT_LIMITS 21 PCSDD.BOp.and 1 67 ai712 67 ao712 := by
  exact ApplyCertificate.branch (fuel := 20) (a0 := 1) (b0 := 67) (lo := 63) (hi := 66) (r := 67) (op := PCSDD.BOp.and) (m := ai712) (m1 := ao713) (m2 := ao720) (m3 := an712) (by decide) (by rfl) (by decide) a713 a720 (by rfl)
abbrev an698 : Mgr := ao712
abbrev ao698 : Mgr := {an698 with memo := ((PCSDD.BOp.and,1,68),68)::an698.memo}
theorem a698 : ApplyCertificate 12 DEFAULT_LIMITS 22 PCSDD.BOp.and 1 68 ai698 68 ao698 := by
  exact ApplyCertificate.branch (fuel := 21) (a0 := 1) (b0 := 68) (lo := 60) (hi := 67) (r := 68) (op := PCSDD.BOp.and) (m := ai698) (m1 := ao699) (m2 := ao712) (m3 := an698) (by decide) (by rfl) (by decide) a699 a712 (by rfl)
abbrev ai727 : Mgr := ao698
abbrev ai728 : Mgr := {ai727 with ops := ai727.ops+1}
abbrev ai729 : Mgr := {ai728 with ops := ai728.ops+1}
abbrev ai730 : Mgr := {ai729 with ops := ai729.ops+1}
abbrev ai731 : Mgr := {ai730 with ops := ai730.ops+1}
abbrev ao731 : Mgr := {ai731 with ops := ai731.ops+1}
theorem a731 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.and 1 9 ai731 9 ao731 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 1) (b0 := 9) (r := 9) (op := PCSDD.BOp.and) (m := ai731) (by decide) (by rfl)
abbrev ai732 : Mgr := ao731
abbrev ao732 : Mgr := {ai732 with ops := ai732.ops+1}
theorem a732 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.and 1 1 ai732 1 ao732 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 1) (b0 := 1) (r := 1) (op := PCSDD.BOp.and) (m := ai732) (by decide) (by rfl)
abbrev an730 : Mgr := ao732
abbrev ao730 : Mgr := {an730 with memo := ((PCSDD.BOp.and,1,11),11)::an730.memo}
theorem a730 : ApplyCertificate 12 DEFAULT_LIMITS 19 PCSDD.BOp.and 1 11 ai730 11 ao730 := by
  exact ApplyCertificate.branch (fuel := 18) (a0 := 1) (b0 := 11) (lo := 9) (hi := 1) (r := 11) (op := PCSDD.BOp.and) (m := ai730) (m1 := ao731) (m2 := ao732) (m3 := an730) (by decide) (by rfl) (by decide) a731 a732 (by rfl)
abbrev ai733 : Mgr := ao730
abbrev ai734 : Mgr := {ai733 with ops := ai733.ops+1}
abbrev ao734 : Mgr := {ai734 with ops := ai734.ops+1}
theorem a734 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.and 1 40 ai734 40 ao734 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 1) (b0 := 40) (r := 40) (op := PCSDD.BOp.and) (m := ai734) (by decide) (by rfl)
abbrev ai735 : Mgr := ao734
abbrev ao735 : Mgr := {ai735 with ops := ai735.ops+1}
theorem a735 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.and 1 1 ai735 1 ao735 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 1) (b0 := 1) (r := 1) (op := PCSDD.BOp.and) (m := ai735) (by decide) (by rfl)
abbrev an733 : Mgr := ao735
abbrev ao733 : Mgr := {an733 with memo := ((PCSDD.BOp.and,1,69),69)::an733.memo}
theorem a733 : ApplyCertificate 12 DEFAULT_LIMITS 19 PCSDD.BOp.and 1 69 ai733 69 ao733 := by
  exact ApplyCertificate.branch (fuel := 18) (a0 := 1) (b0 := 69) (lo := 40) (hi := 1) (r := 69) (op := PCSDD.BOp.and) (m := ai733) (m1 := ao734) (m2 := ao735) (m3 := an733) (by decide) (by rfl) (by decide) a734 a735 (by rfl)
abbrev an729 : Mgr := ao733
abbrev ao729 : Mgr := {an729 with memo := ((PCSDD.BOp.and,1,70),70)::an729.memo}
theorem a729 : ApplyCertificate 12 DEFAULT_LIMITS 20 PCSDD.BOp.and 1 70 ai729 70 ao729 := by
  exact ApplyCertificate.branch (fuel := 19) (a0 := 1) (b0 := 70) (lo := 11) (hi := 69) (r := 70) (op := PCSDD.BOp.and) (m := ai729) (m1 := ao730) (m2 := ao733) (m3 := an729) (by decide) (by rfl) (by decide) a730 a733 (by rfl)
abbrev ai736 : Mgr := ao729
abbrev ai737 : Mgr := {ai736 with ops := ai736.ops+1}
abbrev ai738 : Mgr := {ai737 with ops := ai737.ops+1}
abbrev ao738 : Mgr := {ai738 with ops := ai738.ops+1}
theorem a738 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.and 1 42 ai738 42 ao738 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 1) (b0 := 42) (r := 42) (op := PCSDD.BOp.and) (m := ai738) (by decide) (by rfl)
abbrev ai739 : Mgr := ao738
abbrev ao739 : Mgr := {ai739 with ops := ai739.ops+1}
theorem a739 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.and 1 1 ai739 1 ao739 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 1) (b0 := 1) (r := 1) (op := PCSDD.BOp.and) (m := ai739) (by decide) (by rfl)
abbrev an737 : Mgr := ao739
abbrev ao737 : Mgr := {an737 with memo := ((PCSDD.BOp.and,1,71),71)::an737.memo}
theorem a737 : ApplyCertificate 12 DEFAULT_LIMITS 19 PCSDD.BOp.and 1 71 ai737 71 ao737 := by
  exact ApplyCertificate.branch (fuel := 18) (a0 := 1) (b0 := 71) (lo := 42) (hi := 1) (r := 71) (op := PCSDD.BOp.and) (m := ai737) (m1 := ao738) (m2 := ao739) (m3 := an737) (by decide) (by rfl) (by decide) a738 a739 (by rfl)
abbrev ai740 : Mgr := ao737
abbrev ai741 : Mgr := {ai740 with ops := ai740.ops+1}
abbrev ao741 : Mgr := {ai741 with ops := ai741.ops+1}
theorem a741 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.and 1 43 ai741 43 ao741 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 1) (b0 := 43) (r := 43) (op := PCSDD.BOp.and) (m := ai741) (by decide) (by rfl)
abbrev ai742 : Mgr := ao741
abbrev ao742 : Mgr := {ai742 with ops := ai742.ops+1}
theorem a742 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.and 1 1 ai742 1 ao742 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 1) (b0 := 1) (r := 1) (op := PCSDD.BOp.and) (m := ai742) (by decide) (by rfl)
abbrev an740 : Mgr := ao742
abbrev ao740 : Mgr := {an740 with memo := ((PCSDD.BOp.and,1,72),72)::an740.memo}
theorem a740 : ApplyCertificate 12 DEFAULT_LIMITS 19 PCSDD.BOp.and 1 72 ai740 72 ao740 := by
  exact ApplyCertificate.branch (fuel := 18) (a0 := 1) (b0 := 72) (lo := 43) (hi := 1) (r := 72) (op := PCSDD.BOp.and) (m := ai740) (m1 := ao741) (m2 := ao742) (m3 := an740) (by decide) (by rfl) (by decide) a741 a742 (by rfl)
abbrev an736 : Mgr := ao740
abbrev ao736 : Mgr := {an736 with memo := ((PCSDD.BOp.and,1,73),73)::an736.memo}
theorem a736 : ApplyCertificate 12 DEFAULT_LIMITS 20 PCSDD.BOp.and 1 73 ai736 73 ao736 := by
  exact ApplyCertificate.branch (fuel := 19) (a0 := 1) (b0 := 73) (lo := 71) (hi := 72) (r := 73) (op := PCSDD.BOp.and) (m := ai736) (m1 := ao737) (m2 := ao740) (m3 := an736) (by decide) (by rfl) (by decide) a737 a740 (by rfl)
abbrev an728 : Mgr := ao736
abbrev ao728 : Mgr := {an728 with memo := ((PCSDD.BOp.and,1,74),74)::an728.memo}
theorem a728 : ApplyCertificate 12 DEFAULT_LIMITS 21 PCSDD.BOp.and 1 74 ai728 74 ao728 := by
  exact ApplyCertificate.branch (fuel := 20) (a0 := 1) (b0 := 74) (lo := 70) (hi := 73) (r := 74) (op := PCSDD.BOp.and) (m := ai728) (m1 := ao729) (m2 := ao736) (m3 := an728) (by decide) (by rfl) (by decide) a729 a736 (by rfl)
abbrev ai743 : Mgr := ao728
abbrev ai744 : Mgr := {ai743 with ops := ai743.ops+1}
abbrev ai745 : Mgr := {ai744 with ops := ai744.ops+1}
abbrev ai746 : Mgr := {ai745 with ops := ai745.ops+1}
abbrev ao746 : Mgr := {ai746 with ops := ai746.ops+1}
theorem a746 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.and 1 46 ai746 46 ao746 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 1) (b0 := 46) (r := 46) (op := PCSDD.BOp.and) (m := ai746) (by decide) (by rfl)
abbrev ai747 : Mgr := ao746
abbrev ao747 : Mgr := {ai747 with ops := ai747.ops+1}
theorem a747 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.and 1 1 ai747 1 ao747 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 1) (b0 := 1) (r := 1) (op := PCSDD.BOp.and) (m := ai747) (by decide) (by rfl)
abbrev an745 : Mgr := ao747
abbrev ao745 : Mgr := {an745 with memo := ((PCSDD.BOp.and,1,75),75)::an745.memo}
theorem a745 : ApplyCertificate 12 DEFAULT_LIMITS 19 PCSDD.BOp.and 1 75 ai745 75 ao745 := by
  exact ApplyCertificate.branch (fuel := 18) (a0 := 1) (b0 := 75) (lo := 46) (hi := 1) (r := 75) (op := PCSDD.BOp.and) (m := ai745) (m1 := ao746) (m2 := ao747) (m3 := an745) (by decide) (by rfl) (by decide) a746 a747 (by rfl)
abbrev ai748 : Mgr := ao745
abbrev ai749 : Mgr := {ai748 with ops := ai748.ops+1}
abbrev ao749 : Mgr := {ai749 with ops := ai749.ops+1}
theorem a749 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.and 1 47 ai749 47 ao749 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 1) (b0 := 47) (r := 47) (op := PCSDD.BOp.and) (m := ai749) (by decide) (by rfl)
abbrev ai750 : Mgr := ao749
abbrev ao750 : Mgr := {ai750 with ops := ai750.ops+1}
theorem a750 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.and 1 1 ai750 1 ao750 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 1) (b0 := 1) (r := 1) (op := PCSDD.BOp.and) (m := ai750) (by decide) (by rfl)
abbrev an748 : Mgr := ao750
abbrev ao748 : Mgr := {an748 with memo := ((PCSDD.BOp.and,1,76),76)::an748.memo}
theorem a748 : ApplyCertificate 12 DEFAULT_LIMITS 19 PCSDD.BOp.and 1 76 ai748 76 ao748 := by
  exact ApplyCertificate.branch (fuel := 18) (a0 := 1) (b0 := 76) (lo := 47) (hi := 1) (r := 76) (op := PCSDD.BOp.and) (m := ai748) (m1 := ao749) (m2 := ao750) (m3 := an748) (by decide) (by rfl) (by decide) a749 a750 (by rfl)
abbrev an744 : Mgr := ao748
abbrev ao744 : Mgr := {an744 with memo := ((PCSDD.BOp.and,1,77),77)::an744.memo}
theorem a744 : ApplyCertificate 12 DEFAULT_LIMITS 20 PCSDD.BOp.and 1 77 ai744 77 ao744 := by
  exact ApplyCertificate.branch (fuel := 19) (a0 := 1) (b0 := 77) (lo := 75) (hi := 76) (r := 77) (op := PCSDD.BOp.and) (m := ai744) (m1 := ao745) (m2 := ao748) (m3 := an744) (by decide) (by rfl) (by decide) a745 a748 (by rfl)
abbrev ai751 : Mgr := ao744
abbrev ai752 : Mgr := {ai751 with ops := ai751.ops+1}
abbrev ai753 : Mgr := {ai752 with ops := ai752.ops+1}
abbrev ao753 : Mgr := {ai753 with ops := ai753.ops+1}
theorem a753 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.and 1 49 ai753 49 ao753 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 1) (b0 := 49) (r := 49) (op := PCSDD.BOp.and) (m := ai753) (by decide) (by rfl)
abbrev ai754 : Mgr := ao753
abbrev ao754 : Mgr := {ai754 with ops := ai754.ops+1}
theorem a754 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.and 1 1 ai754 1 ao754 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 1) (b0 := 1) (r := 1) (op := PCSDD.BOp.and) (m := ai754) (by decide) (by rfl)
abbrev an752 : Mgr := ao754
abbrev ao752 : Mgr := {an752 with memo := ((PCSDD.BOp.and,1,78),78)::an752.memo}
theorem a752 : ApplyCertificate 12 DEFAULT_LIMITS 19 PCSDD.BOp.and 1 78 ai752 78 ao752 := by
  exact ApplyCertificate.branch (fuel := 18) (a0 := 1) (b0 := 78) (lo := 49) (hi := 1) (r := 78) (op := PCSDD.BOp.and) (m := ai752) (m1 := ao753) (m2 := ao754) (m3 := an752) (by decide) (by rfl) (by decide) a753 a754 (by rfl)
abbrev ai755 : Mgr := ao752
abbrev ai756 : Mgr := {ai755 with ops := ai755.ops+1}
abbrev ao756 : Mgr := {ai756 with ops := ai756.ops+1}
theorem a756 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.and 1 50 ai756 50 ao756 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 1) (b0 := 50) (r := 50) (op := PCSDD.BOp.and) (m := ai756) (by decide) (by rfl)
abbrev ai757 : Mgr := ao756
abbrev ao757 : Mgr := {ai757 with ops := ai757.ops+1}
theorem a757 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.and 1 1 ai757 1 ao757 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 1) (b0 := 1) (r := 1) (op := PCSDD.BOp.and) (m := ai757) (by decide) (by rfl)
abbrev an755 : Mgr := ao757
abbrev ao755 : Mgr := {an755 with memo := ((PCSDD.BOp.and,1,79),79)::an755.memo}
theorem a755 : ApplyCertificate 12 DEFAULT_LIMITS 19 PCSDD.BOp.and 1 79 ai755 79 ao755 := by
  exact ApplyCertificate.branch (fuel := 18) (a0 := 1) (b0 := 79) (lo := 50) (hi := 1) (r := 79) (op := PCSDD.BOp.and) (m := ai755) (m1 := ao756) (m2 := ao757) (m3 := an755) (by decide) (by rfl) (by decide) a756 a757 (by rfl)
abbrev an751 : Mgr := ao755
abbrev ao751 : Mgr := {an751 with memo := ((PCSDD.BOp.and,1,80),80)::an751.memo}
theorem a751 : ApplyCertificate 12 DEFAULT_LIMITS 20 PCSDD.BOp.and 1 80 ai751 80 ao751 := by
  exact ApplyCertificate.branch (fuel := 19) (a0 := 1) (b0 := 80) (lo := 78) (hi := 79) (r := 80) (op := PCSDD.BOp.and) (m := ai751) (m1 := ao752) (m2 := ao755) (m3 := an751) (by decide) (by rfl) (by decide) a752 a755 (by rfl)
abbrev an743 : Mgr := ao751
abbrev ao743 : Mgr := {an743 with memo := ((PCSDD.BOp.and,1,81),81)::an743.memo}
theorem a743 : ApplyCertificate 12 DEFAULT_LIMITS 21 PCSDD.BOp.and 1 81 ai743 81 ao743 := by
  exact ApplyCertificate.branch (fuel := 20) (a0 := 1) (b0 := 81) (lo := 77) (hi := 80) (r := 81) (op := PCSDD.BOp.and) (m := ai743) (m1 := ao744) (m2 := ao751) (m3 := an743) (by decide) (by rfl) (by decide) a744 a751 (by rfl)
abbrev an727 : Mgr := ao743
abbrev ao727 : Mgr := {an727 with memo := ((PCSDD.BOp.and,1,82),82)::an727.memo}
theorem a727 : ApplyCertificate 12 DEFAULT_LIMITS 22 PCSDD.BOp.and 1 82 ai727 82 ao727 := by
  exact ApplyCertificate.branch (fuel := 21) (a0 := 1) (b0 := 82) (lo := 74) (hi := 81) (r := 82) (op := PCSDD.BOp.and) (m := ai727) (m1 := ao728) (m2 := ao743) (m3 := an727) (by decide) (by rfl) (by decide) a728 a743 (by rfl)
abbrev an697 : Mgr := ao727
abbrev ao697 : Mgr := {an697 with memo := ((PCSDD.BOp.and,1,83),83)::an697.memo}
theorem a697 : ApplyCertificate 12 DEFAULT_LIMITS 23 PCSDD.BOp.and 1 83 ai697 83 ao697 := by
  exact ApplyCertificate.branch (fuel := 22) (a0 := 1) (b0 := 83) (lo := 68) (hi := 82) (r := 83) (op := PCSDD.BOp.and) (m := ai697) (m1 := ao698) (m2 := ao727) (m3 := an697) (by decide) (by rfl) (by decide) a698 a727 (by rfl)
abbrev an643 : Mgr := ao697
abbrev ao643 : Mgr := {an643 with memo := ((PCSDD.BOp.and,1,84),84)::an643.memo}
theorem a643 : ApplyCertificate 12 DEFAULT_LIMITS 24 PCSDD.BOp.and 1 84 ai643 84 ao643 := by
  exact ApplyCertificate.branch (fuel := 23) (a0 := 1) (b0 := 84) (lo := 54) (hi := 83) (r := 84) (op := PCSDD.BOp.and) (m := ai643) (m1 := ao644) (m2 := ao697) (m3 := an643) (by decide) (by rfl) (by decide) a644 a697 (by rfl)
abbrev ai758 : Mgr := ao643
abbrev ai759 : Mgr := {ai758 with ops := ai758.ops+1}
abbrev ai760 : Mgr := {ai759 with ops := ai759.ops+1}
abbrev ai761 : Mgr := {ai760 with ops := ai760.ops+1}
abbrev ai762 : Mgr := {ai761 with ops := ai761.ops+1}
abbrev ai763 : Mgr := {ai762 with ops := ai762.ops+1}
abbrev ao763 : Mgr := {ai763 with ops := ai763.ops+1}
theorem a763 : ApplyCertificate 12 DEFAULT_LIMITS 19 PCSDD.BOp.and 1 3 ai763 3 ao763 := by
  exact ApplyCertificate.hit (fuel := 18) (a0 := 1) (b0 := 3) (r := 3) (op := PCSDD.BOp.and) (m := ai763) (by decide) (by rfl)
abbrev ai764 : Mgr := ao763
abbrev ai765 : Mgr := {ai764 with ops := ai764.ops+1}
abbrev ao765 : Mgr := {ai765 with ops := ai765.ops+1}
theorem a765 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.and 1 28 ai765 28 ao765 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 1) (b0 := 28) (r := 28) (op := PCSDD.BOp.and) (m := ai765) (by decide) (by rfl)
abbrev ai766 : Mgr := ao765
abbrev ao766 : Mgr := {ai766 with ops := ai766.ops+1}
theorem a766 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.and 1 1 ai766 1 ao766 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 1) (b0 := 1) (r := 1) (op := PCSDD.BOp.and) (m := ai766) (by decide) (by rfl)
abbrev an764 : Mgr := ao766
abbrev ao764 : Mgr := {an764 with memo := ((PCSDD.BOp.and,1,85),85)::an764.memo}
theorem a764 : ApplyCertificate 12 DEFAULT_LIMITS 19 PCSDD.BOp.and 1 85 ai764 85 ao764 := by
  exact ApplyCertificate.branch (fuel := 18) (a0 := 1) (b0 := 85) (lo := 28) (hi := 1) (r := 85) (op := PCSDD.BOp.and) (m := ai764) (m1 := ao765) (m2 := ao766) (m3 := an764) (by decide) (by rfl) (by decide) a765 a766 (by rfl)
abbrev an762 : Mgr := ao764
abbrev ao762 : Mgr := {an762 with memo := ((PCSDD.BOp.and,1,86),86)::an762.memo}
theorem a762 : ApplyCertificate 12 DEFAULT_LIMITS 20 PCSDD.BOp.and 1 86 ai762 86 ao762 := by
  exact ApplyCertificate.branch (fuel := 19) (a0 := 1) (b0 := 86) (lo := 3) (hi := 85) (r := 86) (op := PCSDD.BOp.and) (m := ai762) (m1 := ao763) (m2 := ao764) (m3 := an762) (by decide) (by rfl) (by decide) a763 a764 (by rfl)
abbrev ai767 : Mgr := ao762
abbrev ai768 : Mgr := {ai767 with ops := ai767.ops+1}
abbrev ai769 : Mgr := {ai768 with ops := ai768.ops+1}
abbrev ao769 : Mgr := {ai769 with ops := ai769.ops+1}
theorem a769 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.and 1 25 ai769 25 ao769 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 1) (b0 := 25) (r := 25) (op := PCSDD.BOp.and) (m := ai769) (by decide) (by rfl)
abbrev ai770 : Mgr := ao769
abbrev ao770 : Mgr := {ai770 with ops := ai770.ops+1}
theorem a770 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.and 1 1 ai770 1 ao770 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 1) (b0 := 1) (r := 1) (op := PCSDD.BOp.and) (m := ai770) (by decide) (by rfl)
abbrev an768 : Mgr := ao770
abbrev ao768 : Mgr := {an768 with memo := ((PCSDD.BOp.and,1,87),87)::an768.memo}
theorem a768 : ApplyCertificate 12 DEFAULT_LIMITS 19 PCSDD.BOp.and 1 87 ai768 87 ao768 := by
  exact ApplyCertificate.branch (fuel := 18) (a0 := 1) (b0 := 87) (lo := 25) (hi := 1) (r := 87) (op := PCSDD.BOp.and) (m := ai768) (m1 := ao769) (m2 := ao770) (m3 := an768) (by decide) (by rfl) (by decide) a769 a770 (by rfl)
abbrev ai771 : Mgr := ao768
abbrev ai772 : Mgr := {ai771 with ops := ai771.ops+1}
abbrev ao772 : Mgr := {ai772 with ops := ai772.ops+1}
theorem a772 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.and 1 30 ai772 30 ao772 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 1) (b0 := 30) (r := 30) (op := PCSDD.BOp.and) (m := ai772) (by decide) (by rfl)
abbrev ai773 : Mgr := ao772
abbrev ao773 : Mgr := {ai773 with ops := ai773.ops+1}
theorem a773 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.and 1 1 ai773 1 ao773 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 1) (b0 := 1) (r := 1) (op := PCSDD.BOp.and) (m := ai773) (by decide) (by rfl)
abbrev an771 : Mgr := ao773
abbrev ao771 : Mgr := {an771 with memo := ((PCSDD.BOp.and,1,88),88)::an771.memo}
theorem a771 : ApplyCertificate 12 DEFAULT_LIMITS 19 PCSDD.BOp.and 1 88 ai771 88 ao771 := by
  exact ApplyCertificate.branch (fuel := 18) (a0 := 1) (b0 := 88) (lo := 30) (hi := 1) (r := 88) (op := PCSDD.BOp.and) (m := ai771) (m1 := ao772) (m2 := ao773) (m3 := an771) (by decide) (by rfl) (by decide) a772 a773 (by rfl)
abbrev an767 : Mgr := ao771
abbrev ao767 : Mgr := {an767 with memo := ((PCSDD.BOp.and,1,89),89)::an767.memo}
theorem a767 : ApplyCertificate 12 DEFAULT_LIMITS 20 PCSDD.BOp.and 1 89 ai767 89 ao767 := by
  exact ApplyCertificate.branch (fuel := 19) (a0 := 1) (b0 := 89) (lo := 87) (hi := 88) (r := 89) (op := PCSDD.BOp.and) (m := ai767) (m1 := ao768) (m2 := ao771) (m3 := an767) (by decide) (by rfl) (by decide) a768 a771 (by rfl)
abbrev an761 : Mgr := ao767
abbrev ao761 : Mgr := {an761 with memo := ((PCSDD.BOp.and,1,90),90)::an761.memo}
theorem a761 : ApplyCertificate 12 DEFAULT_LIMITS 21 PCSDD.BOp.and 1 90 ai761 90 ao761 := by
  exact ApplyCertificate.branch (fuel := 20) (a0 := 1) (b0 := 90) (lo := 86) (hi := 89) (r := 90) (op := PCSDD.BOp.and) (m := ai761) (m1 := ao762) (m2 := ao767) (m3 := an761) (by decide) (by rfl) (by decide) a762 a767 (by rfl)
abbrev ai774 : Mgr := ao761
abbrev ai775 : Mgr := {ai774 with ops := ai774.ops+1}
abbrev ai776 : Mgr := {ai775 with ops := ai775.ops+1}
abbrev ai777 : Mgr := {ai776 with ops := ai776.ops+1}
abbrev ao777 : Mgr := {ai777 with ops := ai777.ops+1}
theorem a777 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.and 1 22 ai777 22 ao777 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 1) (b0 := 22) (r := 22) (op := PCSDD.BOp.and) (m := ai777) (by decide) (by rfl)
abbrev ai778 : Mgr := ao777
abbrev ao778 : Mgr := {ai778 with ops := ai778.ops+1}
theorem a778 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.and 1 1 ai778 1 ao778 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 1) (b0 := 1) (r := 1) (op := PCSDD.BOp.and) (m := ai778) (by decide) (by rfl)
abbrev an776 : Mgr := ao778
abbrev ao776 : Mgr := {an776 with memo := ((PCSDD.BOp.and,1,91),91)::an776.memo}
theorem a776 : ApplyCertificate 12 DEFAULT_LIMITS 19 PCSDD.BOp.and 1 91 ai776 91 ao776 := by
  exact ApplyCertificate.branch (fuel := 18) (a0 := 1) (b0 := 91) (lo := 22) (hi := 1) (r := 91) (op := PCSDD.BOp.and) (m := ai776) (m1 := ao777) (m2 := ao778) (m3 := an776) (by decide) (by rfl) (by decide) a777 a778 (by rfl)
abbrev ai779 : Mgr := ao776
abbrev ai780 : Mgr := {ai779 with ops := ai779.ops+1}
abbrev ao780 : Mgr := {ai780 with ops := ai780.ops+1}
theorem a780 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.and 1 33 ai780 33 ao780 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 1) (b0 := 33) (r := 33) (op := PCSDD.BOp.and) (m := ai780) (by decide) (by rfl)
abbrev ai781 : Mgr := ao780
abbrev ao781 : Mgr := {ai781 with ops := ai781.ops+1}
theorem a781 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.and 1 1 ai781 1 ao781 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 1) (b0 := 1) (r := 1) (op := PCSDD.BOp.and) (m := ai781) (by decide) (by rfl)
abbrev an779 : Mgr := ao781
abbrev ao779 : Mgr := {an779 with memo := ((PCSDD.BOp.and,1,92),92)::an779.memo}
theorem a779 : ApplyCertificate 12 DEFAULT_LIMITS 19 PCSDD.BOp.and 1 92 ai779 92 ao779 := by
  exact ApplyCertificate.branch (fuel := 18) (a0 := 1) (b0 := 92) (lo := 33) (hi := 1) (r := 92) (op := PCSDD.BOp.and) (m := ai779) (m1 := ao780) (m2 := ao781) (m3 := an779) (by decide) (by rfl) (by decide) a780 a781 (by rfl)
abbrev an775 : Mgr := ao779
abbrev ao775 : Mgr := {an775 with memo := ((PCSDD.BOp.and,1,93),93)::an775.memo}
theorem a775 : ApplyCertificate 12 DEFAULT_LIMITS 20 PCSDD.BOp.and 1 93 ai775 93 ao775 := by
  exact ApplyCertificate.branch (fuel := 19) (a0 := 1) (b0 := 93) (lo := 91) (hi := 92) (r := 93) (op := PCSDD.BOp.and) (m := ai775) (m1 := ao776) (m2 := ao779) (m3 := an775) (by decide) (by rfl) (by decide) a776 a779 (by rfl)
abbrev ai782 : Mgr := ao775
abbrev ai783 : Mgr := {ai782 with ops := ai782.ops+1}
abbrev ai784 : Mgr := {ai783 with ops := ai783.ops+1}
abbrev ao784 : Mgr := {ai784 with ops := ai784.ops+1}
theorem a784 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.and 1 35 ai784 35 ao784 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 1) (b0 := 35) (r := 35) (op := PCSDD.BOp.and) (m := ai784) (by decide) (by rfl)
abbrev ai785 : Mgr := ao784
abbrev ao785 : Mgr := {ai785 with ops := ai785.ops+1}
theorem a785 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.and 1 1 ai785 1 ao785 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 1) (b0 := 1) (r := 1) (op := PCSDD.BOp.and) (m := ai785) (by decide) (by rfl)
abbrev an783 : Mgr := ao785
abbrev ao783 : Mgr := {an783 with memo := ((PCSDD.BOp.and,1,94),94)::an783.memo}
theorem a783 : ApplyCertificate 12 DEFAULT_LIMITS 19 PCSDD.BOp.and 1 94 ai783 94 ao783 := by
  exact ApplyCertificate.branch (fuel := 18) (a0 := 1) (b0 := 94) (lo := 35) (hi := 1) (r := 94) (op := PCSDD.BOp.and) (m := ai783) (m1 := ao784) (m2 := ao785) (m3 := an783) (by decide) (by rfl) (by decide) a784 a785 (by rfl)
abbrev ai786 : Mgr := ao783
abbrev ai787 : Mgr := {ai786 with ops := ai786.ops+1}
abbrev ao787 : Mgr := {ai787 with ops := ai787.ops+1}
theorem a787 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.and 1 36 ai787 36 ao787 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 1) (b0 := 36) (r := 36) (op := PCSDD.BOp.and) (m := ai787) (by decide) (by rfl)
abbrev ai788 : Mgr := ao787
abbrev ao788 : Mgr := {ai788 with ops := ai788.ops+1}
theorem a788 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.and 1 1 ai788 1 ao788 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 1) (b0 := 1) (r := 1) (op := PCSDD.BOp.and) (m := ai788) (by decide) (by rfl)
abbrev an786 : Mgr := ao788
abbrev ao786 : Mgr := {an786 with memo := ((PCSDD.BOp.and,1,95),95)::an786.memo}
theorem a786 : ApplyCertificate 12 DEFAULT_LIMITS 19 PCSDD.BOp.and 1 95 ai786 95 ao786 := by
  exact ApplyCertificate.branch (fuel := 18) (a0 := 1) (b0 := 95) (lo := 36) (hi := 1) (r := 95) (op := PCSDD.BOp.and) (m := ai786) (m1 := ao787) (m2 := ao788) (m3 := an786) (by decide) (by rfl) (by decide) a787 a788 (by rfl)
abbrev an782 : Mgr := ao786
abbrev ao782 : Mgr := {an782 with memo := ((PCSDD.BOp.and,1,96),96)::an782.memo}
theorem a782 : ApplyCertificate 12 DEFAULT_LIMITS 20 PCSDD.BOp.and 1 96 ai782 96 ao782 := by
  exact ApplyCertificate.branch (fuel := 19) (a0 := 1) (b0 := 96) (lo := 94) (hi := 95) (r := 96) (op := PCSDD.BOp.and) (m := ai782) (m1 := ao783) (m2 := ao786) (m3 := an782) (by decide) (by rfl) (by decide) a783 a786 (by rfl)
abbrev an774 : Mgr := ao782
abbrev ao774 : Mgr := {an774 with memo := ((PCSDD.BOp.and,1,97),97)::an774.memo}
theorem a774 : ApplyCertificate 12 DEFAULT_LIMITS 21 PCSDD.BOp.and 1 97 ai774 97 ao774 := by
  exact ApplyCertificate.branch (fuel := 20) (a0 := 1) (b0 := 97) (lo := 93) (hi := 96) (r := 97) (op := PCSDD.BOp.and) (m := ai774) (m1 := ao775) (m2 := ao782) (m3 := an774) (by decide) (by rfl) (by decide) a775 a782 (by rfl)
abbrev an760 : Mgr := ao774
abbrev ao760 : Mgr := {an760 with memo := ((PCSDD.BOp.and,1,98),98)::an760.memo}
theorem a760 : ApplyCertificate 12 DEFAULT_LIMITS 22 PCSDD.BOp.and 1 98 ai760 98 ao760 := by
  exact ApplyCertificate.branch (fuel := 21) (a0 := 1) (b0 := 98) (lo := 90) (hi := 97) (r := 98) (op := PCSDD.BOp.and) (m := ai760) (m1 := ao761) (m2 := ao774) (m3 := an760) (by decide) (by rfl) (by decide) a761 a774 (by rfl)
abbrev ai789 : Mgr := ao760
abbrev ai790 : Mgr := {ai789 with ops := ai789.ops+1}
abbrev ai791 : Mgr := {ai790 with ops := ai790.ops+1}
abbrev ai792 : Mgr := {ai791 with ops := ai791.ops+1}
abbrev ai793 : Mgr := {ai792 with ops := ai792.ops+1}
abbrev ao793 : Mgr := {ai793 with ops := ai793.ops+1}
theorem a793 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.and 1 9 ai793 9 ao793 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 1) (b0 := 9) (r := 9) (op := PCSDD.BOp.and) (m := ai793) (by decide) (by rfl)
abbrev ai794 : Mgr := ao793
abbrev ao794 : Mgr := {ai794 with ops := ai794.ops+1}
theorem a794 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.and 1 1 ai794 1 ao794 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 1) (b0 := 1) (r := 1) (op := PCSDD.BOp.and) (m := ai794) (by decide) (by rfl)
abbrev an792 : Mgr := ao794
abbrev ao792 : Mgr := {an792 with memo := ((PCSDD.BOp.and,1,14),14)::an792.memo}
theorem a792 : ApplyCertificate 12 DEFAULT_LIMITS 19 PCSDD.BOp.and 1 14 ai792 14 ao792 := by
  exact ApplyCertificate.branch (fuel := 18) (a0 := 1) (b0 := 14) (lo := 9) (hi := 1) (r := 14) (op := PCSDD.BOp.and) (m := ai792) (m1 := ao793) (m2 := ao794) (m3 := an792) (by decide) (by rfl) (by decide) a793 a794 (by rfl)
abbrev ai795 : Mgr := ao792
abbrev ai796 : Mgr := {ai795 with ops := ai795.ops+1}
abbrev ao796 : Mgr := {ai796 with ops := ai796.ops+1}
theorem a796 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.and 1 40 ai796 40 ao796 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 1) (b0 := 40) (r := 40) (op := PCSDD.BOp.and) (m := ai796) (by decide) (by rfl)
abbrev ai797 : Mgr := ao796
abbrev ao797 : Mgr := {ai797 with ops := ai797.ops+1}
theorem a797 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.and 1 1 ai797 1 ao797 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 1) (b0 := 1) (r := 1) (op := PCSDD.BOp.and) (m := ai797) (by decide) (by rfl)
abbrev an795 : Mgr := ao797
abbrev ao795 : Mgr := {an795 with memo := ((PCSDD.BOp.and,1,99),99)::an795.memo}
theorem a795 : ApplyCertificate 12 DEFAULT_LIMITS 19 PCSDD.BOp.and 1 99 ai795 99 ao795 := by
  exact ApplyCertificate.branch (fuel := 18) (a0 := 1) (b0 := 99) (lo := 40) (hi := 1) (r := 99) (op := PCSDD.BOp.and) (m := ai795) (m1 := ao796) (m2 := ao797) (m3 := an795) (by decide) (by rfl) (by decide) a796 a797 (by rfl)
abbrev an791 : Mgr := ao795
abbrev ao791 : Mgr := {an791 with memo := ((PCSDD.BOp.and,1,100),100)::an791.memo}
theorem a791 : ApplyCertificate 12 DEFAULT_LIMITS 20 PCSDD.BOp.and 1 100 ai791 100 ao791 := by
  exact ApplyCertificate.branch (fuel := 19) (a0 := 1) (b0 := 100) (lo := 14) (hi := 99) (r := 100) (op := PCSDD.BOp.and) (m := ai791) (m1 := ao792) (m2 := ao795) (m3 := an791) (by decide) (by rfl) (by decide) a792 a795 (by rfl)
abbrev ai798 : Mgr := ao791
abbrev ai799 : Mgr := {ai798 with ops := ai798.ops+1}
abbrev ai800 : Mgr := {ai799 with ops := ai799.ops+1}
abbrev ao800 : Mgr := {ai800 with ops := ai800.ops+1}
theorem a800 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.and 1 42 ai800 42 ao800 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 1) (b0 := 42) (r := 42) (op := PCSDD.BOp.and) (m := ai800) (by decide) (by rfl)
abbrev ai801 : Mgr := ao800
abbrev ao801 : Mgr := {ai801 with ops := ai801.ops+1}
theorem a801 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.and 1 1 ai801 1 ao801 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 1) (b0 := 1) (r := 1) (op := PCSDD.BOp.and) (m := ai801) (by decide) (by rfl)
abbrev an799 : Mgr := ao801
abbrev ao799 : Mgr := {an799 with memo := ((PCSDD.BOp.and,1,101),101)::an799.memo}
theorem a799 : ApplyCertificate 12 DEFAULT_LIMITS 19 PCSDD.BOp.and 1 101 ai799 101 ao799 := by
  exact ApplyCertificate.branch (fuel := 18) (a0 := 1) (b0 := 101) (lo := 42) (hi := 1) (r := 101) (op := PCSDD.BOp.and) (m := ai799) (m1 := ao800) (m2 := ao801) (m3 := an799) (by decide) (by rfl) (by decide) a800 a801 (by rfl)
abbrev ai802 : Mgr := ao799
abbrev ai803 : Mgr := {ai802 with ops := ai802.ops+1}
abbrev ao803 : Mgr := {ai803 with ops := ai803.ops+1}
theorem a803 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.and 1 43 ai803 43 ao803 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 1) (b0 := 43) (r := 43) (op := PCSDD.BOp.and) (m := ai803) (by decide) (by rfl)
abbrev ai804 : Mgr := ao803
abbrev ao804 : Mgr := {ai804 with ops := ai804.ops+1}
theorem a804 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.and 1 1 ai804 1 ao804 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 1) (b0 := 1) (r := 1) (op := PCSDD.BOp.and) (m := ai804) (by decide) (by rfl)
abbrev an802 : Mgr := ao804
abbrev ao802 : Mgr := {an802 with memo := ((PCSDD.BOp.and,1,102),102)::an802.memo}
theorem a802 : ApplyCertificate 12 DEFAULT_LIMITS 19 PCSDD.BOp.and 1 102 ai802 102 ao802 := by
  exact ApplyCertificate.branch (fuel := 18) (a0 := 1) (b0 := 102) (lo := 43) (hi := 1) (r := 102) (op := PCSDD.BOp.and) (m := ai802) (m1 := ao803) (m2 := ao804) (m3 := an802) (by decide) (by rfl) (by decide) a803 a804 (by rfl)
abbrev an798 : Mgr := ao802
abbrev ao798 : Mgr := {an798 with memo := ((PCSDD.BOp.and,1,103),103)::an798.memo}
theorem a798 : ApplyCertificate 12 DEFAULT_LIMITS 20 PCSDD.BOp.and 1 103 ai798 103 ao798 := by
  exact ApplyCertificate.branch (fuel := 19) (a0 := 1) (b0 := 103) (lo := 101) (hi := 102) (r := 103) (op := PCSDD.BOp.and) (m := ai798) (m1 := ao799) (m2 := ao802) (m3 := an798) (by decide) (by rfl) (by decide) a799 a802 (by rfl)
abbrev an790 : Mgr := ao798
abbrev ao790 : Mgr := {an790 with memo := ((PCSDD.BOp.and,1,104),104)::an790.memo}
theorem a790 : ApplyCertificate 12 DEFAULT_LIMITS 21 PCSDD.BOp.and 1 104 ai790 104 ao790 := by
  exact ApplyCertificate.branch (fuel := 20) (a0 := 1) (b0 := 104) (lo := 100) (hi := 103) (r := 104) (op := PCSDD.BOp.and) (m := ai790) (m1 := ao791) (m2 := ao798) (m3 := an790) (by decide) (by rfl) (by decide) a791 a798 (by rfl)
abbrev ai805 : Mgr := ao790
abbrev ai806 : Mgr := {ai805 with ops := ai805.ops+1}
abbrev ai807 : Mgr := {ai806 with ops := ai806.ops+1}
abbrev ai808 : Mgr := {ai807 with ops := ai807.ops+1}
abbrev ao808 : Mgr := {ai808 with ops := ai808.ops+1}
theorem a808 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.and 1 46 ai808 46 ao808 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 1) (b0 := 46) (r := 46) (op := PCSDD.BOp.and) (m := ai808) (by decide) (by rfl)
abbrev ai809 : Mgr := ao808
abbrev ao809 : Mgr := {ai809 with ops := ai809.ops+1}
theorem a809 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.and 1 1 ai809 1 ao809 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 1) (b0 := 1) (r := 1) (op := PCSDD.BOp.and) (m := ai809) (by decide) (by rfl)
abbrev an807 : Mgr := ao809
abbrev ao807 : Mgr := {an807 with memo := ((PCSDD.BOp.and,1,105),105)::an807.memo}
theorem a807 : ApplyCertificate 12 DEFAULT_LIMITS 19 PCSDD.BOp.and 1 105 ai807 105 ao807 := by
  exact ApplyCertificate.branch (fuel := 18) (a0 := 1) (b0 := 105) (lo := 46) (hi := 1) (r := 105) (op := PCSDD.BOp.and) (m := ai807) (m1 := ao808) (m2 := ao809) (m3 := an807) (by decide) (by rfl) (by decide) a808 a809 (by rfl)
abbrev ai810 : Mgr := ao807
abbrev ai811 : Mgr := {ai810 with ops := ai810.ops+1}
abbrev ao811 : Mgr := {ai811 with ops := ai811.ops+1}
theorem a811 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.and 1 47 ai811 47 ao811 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 1) (b0 := 47) (r := 47) (op := PCSDD.BOp.and) (m := ai811) (by decide) (by rfl)
abbrev ai812 : Mgr := ao811
abbrev ao812 : Mgr := {ai812 with ops := ai812.ops+1}
theorem a812 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.and 1 1 ai812 1 ao812 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 1) (b0 := 1) (r := 1) (op := PCSDD.BOp.and) (m := ai812) (by decide) (by rfl)
abbrev an810 : Mgr := ao812
abbrev ao810 : Mgr := {an810 with memo := ((PCSDD.BOp.and,1,106),106)::an810.memo}
theorem a810 : ApplyCertificate 12 DEFAULT_LIMITS 19 PCSDD.BOp.and 1 106 ai810 106 ao810 := by
  exact ApplyCertificate.branch (fuel := 18) (a0 := 1) (b0 := 106) (lo := 47) (hi := 1) (r := 106) (op := PCSDD.BOp.and) (m := ai810) (m1 := ao811) (m2 := ao812) (m3 := an810) (by decide) (by rfl) (by decide) a811 a812 (by rfl)
abbrev an806 : Mgr := ao810
abbrev ao806 : Mgr := {an806 with memo := ((PCSDD.BOp.and,1,107),107)::an806.memo}
theorem a806 : ApplyCertificate 12 DEFAULT_LIMITS 20 PCSDD.BOp.and 1 107 ai806 107 ao806 := by
  exact ApplyCertificate.branch (fuel := 19) (a0 := 1) (b0 := 107) (lo := 105) (hi := 106) (r := 107) (op := PCSDD.BOp.and) (m := ai806) (m1 := ao807) (m2 := ao810) (m3 := an806) (by decide) (by rfl) (by decide) a807 a810 (by rfl)
abbrev ai813 : Mgr := ao806
abbrev ai814 : Mgr := {ai813 with ops := ai813.ops+1}
abbrev ai815 : Mgr := {ai814 with ops := ai814.ops+1}
abbrev ao815 : Mgr := {ai815 with ops := ai815.ops+1}
theorem a815 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.and 1 49 ai815 49 ao815 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 1) (b0 := 49) (r := 49) (op := PCSDD.BOp.and) (m := ai815) (by decide) (by rfl)
abbrev ai816 : Mgr := ao815
abbrev ao816 : Mgr := {ai816 with ops := ai816.ops+1}
theorem a816 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.and 1 1 ai816 1 ao816 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 1) (b0 := 1) (r := 1) (op := PCSDD.BOp.and) (m := ai816) (by decide) (by rfl)
abbrev an814 : Mgr := ao816
abbrev ao814 : Mgr := {an814 with memo := ((PCSDD.BOp.and,1,108),108)::an814.memo}
theorem a814 : ApplyCertificate 12 DEFAULT_LIMITS 19 PCSDD.BOp.and 1 108 ai814 108 ao814 := by
  exact ApplyCertificate.branch (fuel := 18) (a0 := 1) (b0 := 108) (lo := 49) (hi := 1) (r := 108) (op := PCSDD.BOp.and) (m := ai814) (m1 := ao815) (m2 := ao816) (m3 := an814) (by decide) (by rfl) (by decide) a815 a816 (by rfl)
abbrev ai817 : Mgr := ao814
abbrev ai818 : Mgr := {ai817 with ops := ai817.ops+1}
abbrev ao818 : Mgr := {ai818 with ops := ai818.ops+1}
theorem a818 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.and 1 50 ai818 50 ao818 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 1) (b0 := 50) (r := 50) (op := PCSDD.BOp.and) (m := ai818) (by decide) (by rfl)
abbrev ai819 : Mgr := ao818
abbrev ao819 : Mgr := {ai819 with ops := ai819.ops+1}
theorem a819 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.and 1 1 ai819 1 ao819 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 1) (b0 := 1) (r := 1) (op := PCSDD.BOp.and) (m := ai819) (by decide) (by rfl)
abbrev an817 : Mgr := ao819
abbrev ao817 : Mgr := {an817 with memo := ((PCSDD.BOp.and,1,109),109)::an817.memo}
theorem a817 : ApplyCertificate 12 DEFAULT_LIMITS 19 PCSDD.BOp.and 1 109 ai817 109 ao817 := by
  exact ApplyCertificate.branch (fuel := 18) (a0 := 1) (b0 := 109) (lo := 50) (hi := 1) (r := 109) (op := PCSDD.BOp.and) (m := ai817) (m1 := ao818) (m2 := ao819) (m3 := an817) (by decide) (by rfl) (by decide) a818 a819 (by rfl)
abbrev an813 : Mgr := ao817
abbrev ao813 : Mgr := {an813 with memo := ((PCSDD.BOp.and,1,110),110)::an813.memo}
theorem a813 : ApplyCertificate 12 DEFAULT_LIMITS 20 PCSDD.BOp.and 1 110 ai813 110 ao813 := by
  exact ApplyCertificate.branch (fuel := 19) (a0 := 1) (b0 := 110) (lo := 108) (hi := 109) (r := 110) (op := PCSDD.BOp.and) (m := ai813) (m1 := ao814) (m2 := ao817) (m3 := an813) (by decide) (by rfl) (by decide) a814 a817 (by rfl)
abbrev an805 : Mgr := ao813
abbrev ao805 : Mgr := {an805 with memo := ((PCSDD.BOp.and,1,111),111)::an805.memo}
theorem a805 : ApplyCertificate 12 DEFAULT_LIMITS 21 PCSDD.BOp.and 1 111 ai805 111 ao805 := by
  exact ApplyCertificate.branch (fuel := 20) (a0 := 1) (b0 := 111) (lo := 107) (hi := 110) (r := 111) (op := PCSDD.BOp.and) (m := ai805) (m1 := ao806) (m2 := ao813) (m3 := an805) (by decide) (by rfl) (by decide) a806 a813 (by rfl)
abbrev an789 : Mgr := ao805
abbrev ao789 : Mgr := {an789 with memo := ((PCSDD.BOp.and,1,112),112)::an789.memo}
theorem a789 : ApplyCertificate 12 DEFAULT_LIMITS 22 PCSDD.BOp.and 1 112 ai789 112 ao789 := by
  exact ApplyCertificate.branch (fuel := 21) (a0 := 1) (b0 := 112) (lo := 104) (hi := 111) (r := 112) (op := PCSDD.BOp.and) (m := ai789) (m1 := ao790) (m2 := ao805) (m3 := an789) (by decide) (by rfl) (by decide) a790 a805 (by rfl)
abbrev an759 : Mgr := ao789
abbrev ao759 : Mgr := {an759 with memo := ((PCSDD.BOp.and,1,113),113)::an759.memo}
theorem a759 : ApplyCertificate 12 DEFAULT_LIMITS 23 PCSDD.BOp.and 1 113 ai759 113 ao759 := by
  exact ApplyCertificate.branch (fuel := 22) (a0 := 1) (b0 := 113) (lo := 98) (hi := 112) (r := 113) (op := PCSDD.BOp.and) (m := ai759) (m1 := ao760) (m2 := ao789) (m3 := an759) (by decide) (by rfl) (by decide) a760 a789 (by rfl)
abbrev ai820 : Mgr := ao759
abbrev ai821 : Mgr := {ai820 with ops := ai820.ops+1}
abbrev ai822 : Mgr := {ai821 with ops := ai821.ops+1}
abbrev ai823 : Mgr := {ai822 with ops := ai822.ops+1}
abbrev ai824 : Mgr := {ai823 with ops := ai823.ops+1}
abbrev ai825 : Mgr := {ai824 with ops := ai824.ops+1}
abbrev ao825 : Mgr := {ai825 with ops := ai825.ops+1}
theorem a825 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.and 1 6 ai825 6 ao825 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 1) (b0 := 6) (r := 6) (op := PCSDD.BOp.and) (m := ai825) (by decide) (by rfl)
abbrev ai826 : Mgr := ao825
abbrev ao826 : Mgr := {ai826 with ops := ai826.ops+1}
theorem a826 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.and 1 1 ai826 1 ao826 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 1) (b0 := 1) (r := 1) (op := PCSDD.BOp.and) (m := ai826) (by decide) (by rfl)
abbrev an824 : Mgr := ao826
abbrev ao824 : Mgr := {an824 with memo := ((PCSDD.BOp.and,1,16),16)::an824.memo}
theorem a824 : ApplyCertificate 12 DEFAULT_LIMITS 19 PCSDD.BOp.and 1 16 ai824 16 ao824 := by
  exact ApplyCertificate.branch (fuel := 18) (a0 := 1) (b0 := 16) (lo := 6) (hi := 1) (r := 16) (op := PCSDD.BOp.and) (m := ai824) (m1 := ao825) (m2 := ao826) (m3 := an824) (by decide) (by rfl) (by decide) a825 a826 (by rfl)
abbrev ai827 : Mgr := ao824
abbrev ai828 : Mgr := {ai827 with ops := ai827.ops+1}
abbrev ao828 : Mgr := {ai828 with ops := ai828.ops+1}
theorem a828 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.and 1 55 ai828 55 ao828 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 1) (b0 := 55) (r := 55) (op := PCSDD.BOp.and) (m := ai828) (by decide) (by rfl)
abbrev ai829 : Mgr := ao828
abbrev ao829 : Mgr := {ai829 with ops := ai829.ops+1}
theorem a829 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.and 1 1 ai829 1 ao829 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 1) (b0 := 1) (r := 1) (op := PCSDD.BOp.and) (m := ai829) (by decide) (by rfl)
abbrev an827 : Mgr := ao829
abbrev ao827 : Mgr := {an827 with memo := ((PCSDD.BOp.and,1,114),114)::an827.memo}
theorem a827 : ApplyCertificate 12 DEFAULT_LIMITS 19 PCSDD.BOp.and 1 114 ai827 114 ao827 := by
  exact ApplyCertificate.branch (fuel := 18) (a0 := 1) (b0 := 114) (lo := 55) (hi := 1) (r := 114) (op := PCSDD.BOp.and) (m := ai827) (m1 := ao828) (m2 := ao829) (m3 := an827) (by decide) (by rfl) (by decide) a828 a829 (by rfl)
abbrev an823 : Mgr := ao827
abbrev ao823 : Mgr := {an823 with memo := ((PCSDD.BOp.and,1,115),115)::an823.memo}
theorem a823 : ApplyCertificate 12 DEFAULT_LIMITS 20 PCSDD.BOp.and 1 115 ai823 115 ao823 := by
  exact ApplyCertificate.branch (fuel := 19) (a0 := 1) (b0 := 115) (lo := 16) (hi := 114) (r := 115) (op := PCSDD.BOp.and) (m := ai823) (m1 := ao824) (m2 := ao827) (m3 := an823) (by decide) (by rfl) (by decide) a824 a827 (by rfl)
abbrev ai830 : Mgr := ao823
abbrev ai831 : Mgr := {ai830 with ops := ai830.ops+1}
abbrev ai832 : Mgr := {ai831 with ops := ai831.ops+1}
abbrev ao832 : Mgr := {ai832 with ops := ai832.ops+1}
theorem a832 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.and 1 57 ai832 57 ao832 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 1) (b0 := 57) (r := 57) (op := PCSDD.BOp.and) (m := ai832) (by decide) (by rfl)
abbrev ai833 : Mgr := ao832
abbrev ao833 : Mgr := {ai833 with ops := ai833.ops+1}
theorem a833 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.and 1 1 ai833 1 ao833 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 1) (b0 := 1) (r := 1) (op := PCSDD.BOp.and) (m := ai833) (by decide) (by rfl)
abbrev an831 : Mgr := ao833
abbrev ao831 : Mgr := {an831 with memo := ((PCSDD.BOp.and,1,116),116)::an831.memo}
theorem a831 : ApplyCertificate 12 DEFAULT_LIMITS 19 PCSDD.BOp.and 1 116 ai831 116 ao831 := by
  exact ApplyCertificate.branch (fuel := 18) (a0 := 1) (b0 := 116) (lo := 57) (hi := 1) (r := 116) (op := PCSDD.BOp.and) (m := ai831) (m1 := ao832) (m2 := ao833) (m3 := an831) (by decide) (by rfl) (by decide) a832 a833 (by rfl)
abbrev ai834 : Mgr := ao831
abbrev ai835 : Mgr := {ai834 with ops := ai834.ops+1}
abbrev ao835 : Mgr := {ai835 with ops := ai835.ops+1}
theorem a835 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.and 1 58 ai835 58 ao835 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 1) (b0 := 58) (r := 58) (op := PCSDD.BOp.and) (m := ai835) (by decide) (by rfl)
abbrev ai836 : Mgr := ao835
abbrev ao836 : Mgr := {ai836 with ops := ai836.ops+1}
theorem a836 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.and 1 1 ai836 1 ao836 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 1) (b0 := 1) (r := 1) (op := PCSDD.BOp.and) (m := ai836) (by decide) (by rfl)
abbrev an834 : Mgr := ao836
abbrev ao834 : Mgr := {an834 with memo := ((PCSDD.BOp.and,1,117),117)::an834.memo}
theorem a834 : ApplyCertificate 12 DEFAULT_LIMITS 19 PCSDD.BOp.and 1 117 ai834 117 ao834 := by
  exact ApplyCertificate.branch (fuel := 18) (a0 := 1) (b0 := 117) (lo := 58) (hi := 1) (r := 117) (op := PCSDD.BOp.and) (m := ai834) (m1 := ao835) (m2 := ao836) (m3 := an834) (by decide) (by rfl) (by decide) a835 a836 (by rfl)
abbrev an830 : Mgr := ao834
abbrev ao830 : Mgr := {an830 with memo := ((PCSDD.BOp.and,1,118),118)::an830.memo}
theorem a830 : ApplyCertificate 12 DEFAULT_LIMITS 20 PCSDD.BOp.and 1 118 ai830 118 ao830 := by
  exact ApplyCertificate.branch (fuel := 19) (a0 := 1) (b0 := 118) (lo := 116) (hi := 117) (r := 118) (op := PCSDD.BOp.and) (m := ai830) (m1 := ao831) (m2 := ao834) (m3 := an830) (by decide) (by rfl) (by decide) a831 a834 (by rfl)
abbrev an822 : Mgr := ao830
abbrev ao822 : Mgr := {an822 with memo := ((PCSDD.BOp.and,1,119),119)::an822.memo}
theorem a822 : ApplyCertificate 12 DEFAULT_LIMITS 21 PCSDD.BOp.and 1 119 ai822 119 ao822 := by
  exact ApplyCertificate.branch (fuel := 20) (a0 := 1) (b0 := 119) (lo := 115) (hi := 118) (r := 119) (op := PCSDD.BOp.and) (m := ai822) (m1 := ao823) (m2 := ao830) (m3 := an822) (by decide) (by rfl) (by decide) a823 a830 (by rfl)
abbrev ai837 : Mgr := ao822
abbrev ai838 : Mgr := {ai837 with ops := ai837.ops+1}
abbrev ai839 : Mgr := {ai838 with ops := ai838.ops+1}
abbrev ai840 : Mgr := {ai839 with ops := ai839.ops+1}
abbrev ao840 : Mgr := {ai840 with ops := ai840.ops+1}
theorem a840 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.and 1 61 ai840 61 ao840 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 1) (b0 := 61) (r := 61) (op := PCSDD.BOp.and) (m := ai840) (by decide) (by rfl)
abbrev ai841 : Mgr := ao840
abbrev ao841 : Mgr := {ai841 with ops := ai841.ops+1}
theorem a841 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.and 1 1 ai841 1 ao841 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 1) (b0 := 1) (r := 1) (op := PCSDD.BOp.and) (m := ai841) (by decide) (by rfl)
abbrev an839 : Mgr := ao841
abbrev ao839 : Mgr := {an839 with memo := ((PCSDD.BOp.and,1,120),120)::an839.memo}
theorem a839 : ApplyCertificate 12 DEFAULT_LIMITS 19 PCSDD.BOp.and 1 120 ai839 120 ao839 := by
  exact ApplyCertificate.branch (fuel := 18) (a0 := 1) (b0 := 120) (lo := 61) (hi := 1) (r := 120) (op := PCSDD.BOp.and) (m := ai839) (m1 := ao840) (m2 := ao841) (m3 := an839) (by decide) (by rfl) (by decide) a840 a841 (by rfl)
abbrev ai842 : Mgr := ao839
abbrev ai843 : Mgr := {ai842 with ops := ai842.ops+1}
abbrev ao843 : Mgr := {ai843 with ops := ai843.ops+1}
theorem a843 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.and 1 62 ai843 62 ao843 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 1) (b0 := 62) (r := 62) (op := PCSDD.BOp.and) (m := ai843) (by decide) (by rfl)
abbrev ai844 : Mgr := ao843
abbrev ao844 : Mgr := {ai844 with ops := ai844.ops+1}
theorem a844 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.and 1 1 ai844 1 ao844 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 1) (b0 := 1) (r := 1) (op := PCSDD.BOp.and) (m := ai844) (by decide) (by rfl)
abbrev an842 : Mgr := ao844
abbrev ao842 : Mgr := {an842 with memo := ((PCSDD.BOp.and,1,121),121)::an842.memo}
theorem a842 : ApplyCertificate 12 DEFAULT_LIMITS 19 PCSDD.BOp.and 1 121 ai842 121 ao842 := by
  exact ApplyCertificate.branch (fuel := 18) (a0 := 1) (b0 := 121) (lo := 62) (hi := 1) (r := 121) (op := PCSDD.BOp.and) (m := ai842) (m1 := ao843) (m2 := ao844) (m3 := an842) (by decide) (by rfl) (by decide) a843 a844 (by rfl)
abbrev an838 : Mgr := ao842
abbrev ao838 : Mgr := {an838 with memo := ((PCSDD.BOp.and,1,122),122)::an838.memo}
theorem a838 : ApplyCertificate 12 DEFAULT_LIMITS 20 PCSDD.BOp.and 1 122 ai838 122 ao838 := by
  exact ApplyCertificate.branch (fuel := 19) (a0 := 1) (b0 := 122) (lo := 120) (hi := 121) (r := 122) (op := PCSDD.BOp.and) (m := ai838) (m1 := ao839) (m2 := ao842) (m3 := an838) (by decide) (by rfl) (by decide) a839 a842 (by rfl)
abbrev ai845 : Mgr := ao838
abbrev ai846 : Mgr := {ai845 with ops := ai845.ops+1}
abbrev ai847 : Mgr := {ai846 with ops := ai846.ops+1}
abbrev ao847 : Mgr := {ai847 with ops := ai847.ops+1}
theorem a847 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.and 1 64 ai847 64 ao847 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 1) (b0 := 64) (r := 64) (op := PCSDD.BOp.and) (m := ai847) (by decide) (by rfl)
abbrev ai848 : Mgr := ao847
abbrev ao848 : Mgr := {ai848 with ops := ai848.ops+1}
theorem a848 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.and 1 1 ai848 1 ao848 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 1) (b0 := 1) (r := 1) (op := PCSDD.BOp.and) (m := ai848) (by decide) (by rfl)
abbrev an846 : Mgr := ao848
abbrev ao846 : Mgr := {an846 with memo := ((PCSDD.BOp.and,1,123),123)::an846.memo}
theorem a846 : ApplyCertificate 12 DEFAULT_LIMITS 19 PCSDD.BOp.and 1 123 ai846 123 ao846 := by
  exact ApplyCertificate.branch (fuel := 18) (a0 := 1) (b0 := 123) (lo := 64) (hi := 1) (r := 123) (op := PCSDD.BOp.and) (m := ai846) (m1 := ao847) (m2 := ao848) (m3 := an846) (by decide) (by rfl) (by decide) a847 a848 (by rfl)
abbrev ai849 : Mgr := ao846
abbrev ai850 : Mgr := {ai849 with ops := ai849.ops+1}
abbrev ao850 : Mgr := {ai850 with ops := ai850.ops+1}
theorem a850 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.and 1 65 ai850 65 ao850 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 1) (b0 := 65) (r := 65) (op := PCSDD.BOp.and) (m := ai850) (by decide) (by rfl)
abbrev ai851 : Mgr := ao850
abbrev ao851 : Mgr := {ai851 with ops := ai851.ops+1}
theorem a851 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.and 1 1 ai851 1 ao851 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 1) (b0 := 1) (r := 1) (op := PCSDD.BOp.and) (m := ai851) (by decide) (by rfl)
abbrev an849 : Mgr := ao851
abbrev ao849 : Mgr := {an849 with memo := ((PCSDD.BOp.and,1,124),124)::an849.memo}
theorem a849 : ApplyCertificate 12 DEFAULT_LIMITS 19 PCSDD.BOp.and 1 124 ai849 124 ao849 := by
  exact ApplyCertificate.branch (fuel := 18) (a0 := 1) (b0 := 124) (lo := 65) (hi := 1) (r := 124) (op := PCSDD.BOp.and) (m := ai849) (m1 := ao850) (m2 := ao851) (m3 := an849) (by decide) (by rfl) (by decide) a850 a851 (by rfl)
abbrev an845 : Mgr := ao849
abbrev ao845 : Mgr := {an845 with memo := ((PCSDD.BOp.and,1,125),125)::an845.memo}
theorem a845 : ApplyCertificate 12 DEFAULT_LIMITS 20 PCSDD.BOp.and 1 125 ai845 125 ao845 := by
  exact ApplyCertificate.branch (fuel := 19) (a0 := 1) (b0 := 125) (lo := 123) (hi := 124) (r := 125) (op := PCSDD.BOp.and) (m := ai845) (m1 := ao846) (m2 := ao849) (m3 := an845) (by decide) (by rfl) (by decide) a846 a849 (by rfl)
abbrev an837 : Mgr := ao845
abbrev ao837 : Mgr := {an837 with memo := ((PCSDD.BOp.and,1,126),126)::an837.memo}
theorem a837 : ApplyCertificate 12 DEFAULT_LIMITS 21 PCSDD.BOp.and 1 126 ai837 126 ao837 := by
  exact ApplyCertificate.branch (fuel := 20) (a0 := 1) (b0 := 126) (lo := 122) (hi := 125) (r := 126) (op := PCSDD.BOp.and) (m := ai837) (m1 := ao838) (m2 := ao845) (m3 := an837) (by decide) (by rfl) (by decide) a838 a845 (by rfl)
abbrev an821 : Mgr := ao837
abbrev ao821 : Mgr := {an821 with memo := ((PCSDD.BOp.and,1,127),127)::an821.memo}
theorem a821 : ApplyCertificate 12 DEFAULT_LIMITS 22 PCSDD.BOp.and 1 127 ai821 127 ao821 := by
  exact ApplyCertificate.branch (fuel := 21) (a0 := 1) (b0 := 127) (lo := 119) (hi := 126) (r := 127) (op := PCSDD.BOp.and) (m := ai821) (m1 := ao822) (m2 := ao837) (m3 := an821) (by decide) (by rfl) (by decide) a822 a837 (by rfl)
abbrev ai852 : Mgr := ao821
abbrev ai853 : Mgr := {ai852 with ops := ai852.ops+1}
abbrev ai854 : Mgr := {ai853 with ops := ai853.ops+1}
abbrev ai855 : Mgr := {ai854 with ops := ai854.ops+1}
abbrev ai856 : Mgr := {ai855 with ops := ai855.ops+1}
abbrev ao856 : Mgr := {ai856 with ops := ai856.ops+1}
theorem a856 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.and 1 11 ai856 11 ao856 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 1) (b0 := 11) (r := 11) (op := PCSDD.BOp.and) (m := ai856) (by decide) (by rfl)
abbrev ai857 : Mgr := ao856
abbrev ao857 : Mgr := {ai857 with ops := ai857.ops+1}
theorem a857 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.and 1 1 ai857 1 ao857 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 1) (b0 := 1) (r := 1) (op := PCSDD.BOp.and) (m := ai857) (by decide) (by rfl)
abbrev an855 : Mgr := ao857
abbrev ao855 : Mgr := {an855 with memo := ((PCSDD.BOp.and,1,17),17)::an855.memo}
theorem a855 : ApplyCertificate 12 DEFAULT_LIMITS 19 PCSDD.BOp.and 1 17 ai855 17 ao855 := by
  exact ApplyCertificate.branch (fuel := 18) (a0 := 1) (b0 := 17) (lo := 11) (hi := 1) (r := 17) (op := PCSDD.BOp.and) (m := ai855) (m1 := ao856) (m2 := ao857) (m3 := an855) (by decide) (by rfl) (by decide) a856 a857 (by rfl)
abbrev ai858 : Mgr := ao855
abbrev ai859 : Mgr := {ai858 with ops := ai858.ops+1}
abbrev ao859 : Mgr := {ai859 with ops := ai859.ops+1}
theorem a859 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.and 1 69 ai859 69 ao859 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 1) (b0 := 69) (r := 69) (op := PCSDD.BOp.and) (m := ai859) (by decide) (by rfl)
abbrev ai860 : Mgr := ao859
abbrev ao860 : Mgr := {ai860 with ops := ai860.ops+1}
theorem a860 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.and 1 1 ai860 1 ao860 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 1) (b0 := 1) (r := 1) (op := PCSDD.BOp.and) (m := ai860) (by decide) (by rfl)
abbrev an858 : Mgr := ao860
abbrev ao858 : Mgr := {an858 with memo := ((PCSDD.BOp.and,1,128),128)::an858.memo}
theorem a858 : ApplyCertificate 12 DEFAULT_LIMITS 19 PCSDD.BOp.and 1 128 ai858 128 ao858 := by
  exact ApplyCertificate.branch (fuel := 18) (a0 := 1) (b0 := 128) (lo := 69) (hi := 1) (r := 128) (op := PCSDD.BOp.and) (m := ai858) (m1 := ao859) (m2 := ao860) (m3 := an858) (by decide) (by rfl) (by decide) a859 a860 (by rfl)
abbrev an854 : Mgr := ao858
abbrev ao854 : Mgr := {an854 with memo := ((PCSDD.BOp.and,1,129),129)::an854.memo}
theorem a854 : ApplyCertificate 12 DEFAULT_LIMITS 20 PCSDD.BOp.and 1 129 ai854 129 ao854 := by
  exact ApplyCertificate.branch (fuel := 19) (a0 := 1) (b0 := 129) (lo := 17) (hi := 128) (r := 129) (op := PCSDD.BOp.and) (m := ai854) (m1 := ao855) (m2 := ao858) (m3 := an854) (by decide) (by rfl) (by decide) a855 a858 (by rfl)
abbrev ai861 : Mgr := ao854
abbrev ai862 : Mgr := {ai861 with ops := ai861.ops+1}
abbrev ai863 : Mgr := {ai862 with ops := ai862.ops+1}
abbrev ao863 : Mgr := {ai863 with ops := ai863.ops+1}
theorem a863 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.and 1 71 ai863 71 ao863 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 1) (b0 := 71) (r := 71) (op := PCSDD.BOp.and) (m := ai863) (by decide) (by rfl)
abbrev ai864 : Mgr := ao863
abbrev ao864 : Mgr := {ai864 with ops := ai864.ops+1}
theorem a864 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.and 1 1 ai864 1 ao864 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 1) (b0 := 1) (r := 1) (op := PCSDD.BOp.and) (m := ai864) (by decide) (by rfl)
abbrev an862 : Mgr := ao864
abbrev ao862 : Mgr := {an862 with memo := ((PCSDD.BOp.and,1,130),130)::an862.memo}
theorem a862 : ApplyCertificate 12 DEFAULT_LIMITS 19 PCSDD.BOp.and 1 130 ai862 130 ao862 := by
  exact ApplyCertificate.branch (fuel := 18) (a0 := 1) (b0 := 130) (lo := 71) (hi := 1) (r := 130) (op := PCSDD.BOp.and) (m := ai862) (m1 := ao863) (m2 := ao864) (m3 := an862) (by decide) (by rfl) (by decide) a863 a864 (by rfl)
abbrev ai865 : Mgr := ao862
abbrev ai866 : Mgr := {ai865 with ops := ai865.ops+1}
abbrev ao866 : Mgr := {ai866 with ops := ai866.ops+1}
theorem a866 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.and 1 72 ai866 72 ao866 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 1) (b0 := 72) (r := 72) (op := PCSDD.BOp.and) (m := ai866) (by decide) (by rfl)
abbrev ai867 : Mgr := ao866
abbrev ao867 : Mgr := {ai867 with ops := ai867.ops+1}
theorem a867 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.and 1 1 ai867 1 ao867 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 1) (b0 := 1) (r := 1) (op := PCSDD.BOp.and) (m := ai867) (by decide) (by rfl)
abbrev an865 : Mgr := ao867
abbrev ao865 : Mgr := {an865 with memo := ((PCSDD.BOp.and,1,131),131)::an865.memo}
theorem a865 : ApplyCertificate 12 DEFAULT_LIMITS 19 PCSDD.BOp.and 1 131 ai865 131 ao865 := by
  exact ApplyCertificate.branch (fuel := 18) (a0 := 1) (b0 := 131) (lo := 72) (hi := 1) (r := 131) (op := PCSDD.BOp.and) (m := ai865) (m1 := ao866) (m2 := ao867) (m3 := an865) (by decide) (by rfl) (by decide) a866 a867 (by rfl)
abbrev an861 : Mgr := ao865
abbrev ao861 : Mgr := {an861 with memo := ((PCSDD.BOp.and,1,132),132)::an861.memo}
theorem a861 : ApplyCertificate 12 DEFAULT_LIMITS 20 PCSDD.BOp.and 1 132 ai861 132 ao861 := by
  exact ApplyCertificate.branch (fuel := 19) (a0 := 1) (b0 := 132) (lo := 130) (hi := 131) (r := 132) (op := PCSDD.BOp.and) (m := ai861) (m1 := ao862) (m2 := ao865) (m3 := an861) (by decide) (by rfl) (by decide) a862 a865 (by rfl)
abbrev an853 : Mgr := ao861
abbrev ao853 : Mgr := {an853 with memo := ((PCSDD.BOp.and,1,133),133)::an853.memo}
theorem a853 : ApplyCertificate 12 DEFAULT_LIMITS 21 PCSDD.BOp.and 1 133 ai853 133 ao853 := by
  exact ApplyCertificate.branch (fuel := 20) (a0 := 1) (b0 := 133) (lo := 129) (hi := 132) (r := 133) (op := PCSDD.BOp.and) (m := ai853) (m1 := ao854) (m2 := ao861) (m3 := an853) (by decide) (by rfl) (by decide) a854 a861 (by rfl)
abbrev ai868 : Mgr := ao853
abbrev ai869 : Mgr := {ai868 with ops := ai868.ops+1}
abbrev ai870 : Mgr := {ai869 with ops := ai869.ops+1}
abbrev ai871 : Mgr := {ai870 with ops := ai870.ops+1}
abbrev ao871 : Mgr := {ai871 with ops := ai871.ops+1}
theorem a871 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.and 1 75 ai871 75 ao871 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 1) (b0 := 75) (r := 75) (op := PCSDD.BOp.and) (m := ai871) (by decide) (by rfl)
abbrev ai872 : Mgr := ao871
abbrev ao872 : Mgr := {ai872 with ops := ai872.ops+1}
theorem a872 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.and 1 1 ai872 1 ao872 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 1) (b0 := 1) (r := 1) (op := PCSDD.BOp.and) (m := ai872) (by decide) (by rfl)
abbrev an870 : Mgr := ao872
abbrev ao870 : Mgr := {an870 with memo := ((PCSDD.BOp.and,1,134),134)::an870.memo}
theorem a870 : ApplyCertificate 12 DEFAULT_LIMITS 19 PCSDD.BOp.and 1 134 ai870 134 ao870 := by
  exact ApplyCertificate.branch (fuel := 18) (a0 := 1) (b0 := 134) (lo := 75) (hi := 1) (r := 134) (op := PCSDD.BOp.and) (m := ai870) (m1 := ao871) (m2 := ao872) (m3 := an870) (by decide) (by rfl) (by decide) a871 a872 (by rfl)
abbrev ai873 : Mgr := ao870
abbrev ai874 : Mgr := {ai873 with ops := ai873.ops+1}
abbrev ao874 : Mgr := {ai874 with ops := ai874.ops+1}
theorem a874 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.and 1 76 ai874 76 ao874 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 1) (b0 := 76) (r := 76) (op := PCSDD.BOp.and) (m := ai874) (by decide) (by rfl)
abbrev ai875 : Mgr := ao874
abbrev ao875 : Mgr := {ai875 with ops := ai875.ops+1}
theorem a875 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.and 1 1 ai875 1 ao875 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 1) (b0 := 1) (r := 1) (op := PCSDD.BOp.and) (m := ai875) (by decide) (by rfl)
abbrev an873 : Mgr := ao875
abbrev ao873 : Mgr := {an873 with memo := ((PCSDD.BOp.and,1,135),135)::an873.memo}
theorem a873 : ApplyCertificate 12 DEFAULT_LIMITS 19 PCSDD.BOp.and 1 135 ai873 135 ao873 := by
  exact ApplyCertificate.branch (fuel := 18) (a0 := 1) (b0 := 135) (lo := 76) (hi := 1) (r := 135) (op := PCSDD.BOp.and) (m := ai873) (m1 := ao874) (m2 := ao875) (m3 := an873) (by decide) (by rfl) (by decide) a874 a875 (by rfl)
abbrev an869 : Mgr := ao873
abbrev ao869 : Mgr := {an869 with memo := ((PCSDD.BOp.and,1,136),136)::an869.memo}
theorem a869 : ApplyCertificate 12 DEFAULT_LIMITS 20 PCSDD.BOp.and 1 136 ai869 136 ao869 := by
  exact ApplyCertificate.branch (fuel := 19) (a0 := 1) (b0 := 136) (lo := 134) (hi := 135) (r := 136) (op := PCSDD.BOp.and) (m := ai869) (m1 := ao870) (m2 := ao873) (m3 := an869) (by decide) (by rfl) (by decide) a870 a873 (by rfl)
abbrev ai876 : Mgr := ao869
abbrev ai877 : Mgr := {ai876 with ops := ai876.ops+1}
abbrev ai878 : Mgr := {ai877 with ops := ai877.ops+1}
abbrev ao878 : Mgr := {ai878 with ops := ai878.ops+1}
theorem a878 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.and 1 78 ai878 78 ao878 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 1) (b0 := 78) (r := 78) (op := PCSDD.BOp.and) (m := ai878) (by decide) (by rfl)
abbrev ai879 : Mgr := ao878
abbrev ao879 : Mgr := {ai879 with ops := ai879.ops+1}
theorem a879 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.and 1 1 ai879 1 ao879 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 1) (b0 := 1) (r := 1) (op := PCSDD.BOp.and) (m := ai879) (by decide) (by rfl)
abbrev an877 : Mgr := ao879
abbrev ao877 : Mgr := {an877 with memo := ((PCSDD.BOp.and,1,137),137)::an877.memo}
theorem a877 : ApplyCertificate 12 DEFAULT_LIMITS 19 PCSDD.BOp.and 1 137 ai877 137 ao877 := by
  exact ApplyCertificate.branch (fuel := 18) (a0 := 1) (b0 := 137) (lo := 78) (hi := 1) (r := 137) (op := PCSDD.BOp.and) (m := ai877) (m1 := ao878) (m2 := ao879) (m3 := an877) (by decide) (by rfl) (by decide) a878 a879 (by rfl)
abbrev ai880 : Mgr := ao877
abbrev ai881 : Mgr := {ai880 with ops := ai880.ops+1}
abbrev ao881 : Mgr := {ai881 with ops := ai881.ops+1}
theorem a881 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.and 1 79 ai881 79 ao881 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 1) (b0 := 79) (r := 79) (op := PCSDD.BOp.and) (m := ai881) (by decide) (by rfl)
abbrev ai882 : Mgr := ao881
abbrev ao882 : Mgr := {ai882 with ops := ai882.ops+1}
theorem a882 : ApplyCertificate 12 DEFAULT_LIMITS 18 PCSDD.BOp.and 1 1 ai882 1 ao882 := by
  exact ApplyCertificate.hit (fuel := 17) (a0 := 1) (b0 := 1) (r := 1) (op := PCSDD.BOp.and) (m := ai882) (by decide) (by rfl)
abbrev an880 : Mgr := ao882
abbrev ao880 : Mgr := {an880 with memo := ((PCSDD.BOp.and,1,138),138)::an880.memo}
theorem a880 : ApplyCertificate 12 DEFAULT_LIMITS 19 PCSDD.BOp.and 1 138 ai880 138 ao880 := by
  exact ApplyCertificate.branch (fuel := 18) (a0 := 1) (b0 := 138) (lo := 79) (hi := 1) (r := 138) (op := PCSDD.BOp.and) (m := ai880) (m1 := ao881) (m2 := ao882) (m3 := an880) (by decide) (by rfl) (by decide) a881 a882 (by rfl)
abbrev an876 : Mgr := ao880
abbrev ao876 : Mgr := {an876 with memo := ((PCSDD.BOp.and,1,139),139)::an876.memo}
theorem a876 : ApplyCertificate 12 DEFAULT_LIMITS 20 PCSDD.BOp.and 1 139 ai876 139 ao876 := by
  exact ApplyCertificate.branch (fuel := 19) (a0 := 1) (b0 := 139) (lo := 137) (hi := 138) (r := 139) (op := PCSDD.BOp.and) (m := ai876) (m1 := ao877) (m2 := ao880) (m3 := an876) (by decide) (by rfl) (by decide) a877 a880 (by rfl)
abbrev an868 : Mgr := ao876
abbrev ao868 : Mgr := {an868 with memo := ((PCSDD.BOp.and,1,140),140)::an868.memo}
theorem a868 : ApplyCertificate 12 DEFAULT_LIMITS 21 PCSDD.BOp.and 1 140 ai868 140 ao868 := by
  exact ApplyCertificate.branch (fuel := 20) (a0 := 1) (b0 := 140) (lo := 136) (hi := 139) (r := 140) (op := PCSDD.BOp.and) (m := ai868) (m1 := ao869) (m2 := ao876) (m3 := an868) (by decide) (by rfl) (by decide) a869 a876 (by rfl)
abbrev an852 : Mgr := ao868
abbrev ao852 : Mgr := {an852 with memo := ((PCSDD.BOp.and,1,141),141)::an852.memo}
theorem a852 : ApplyCertificate 12 DEFAULT_LIMITS 22 PCSDD.BOp.and 1 141 ai852 141 ao852 := by
  exact ApplyCertificate.branch (fuel := 21) (a0 := 1) (b0 := 141) (lo := 133) (hi := 140) (r := 141) (op := PCSDD.BOp.and) (m := ai852) (m1 := ao853) (m2 := ao868) (m3 := an852) (by decide) (by rfl) (by decide) a853 a868 (by rfl)
abbrev an820 : Mgr := ao852
abbrev ao820 : Mgr := {an820 with memo := ((PCSDD.BOp.and,1,142),142)::an820.memo}
theorem a820 : ApplyCertificate 12 DEFAULT_LIMITS 23 PCSDD.BOp.and 1 142 ai820 142 ao820 := by
  exact ApplyCertificate.branch (fuel := 22) (a0 := 1) (b0 := 142) (lo := 127) (hi := 141) (r := 142) (op := PCSDD.BOp.and) (m := ai820) (m1 := ao821) (m2 := ao852) (m3 := an820) (by decide) (by rfl) (by decide) a821 a852 (by rfl)
abbrev an758 : Mgr := ao820
abbrev ao758 : Mgr := {an758 with memo := ((PCSDD.BOp.and,1,143),143)::an758.memo}
theorem a758 : ApplyCertificate 12 DEFAULT_LIMITS 24 PCSDD.BOp.and 1 143 ai758 143 ao758 := by
  exact ApplyCertificate.branch (fuel := 23) (a0 := 1) (b0 := 143) (lo := 113) (hi := 142) (r := 143) (op := PCSDD.BOp.and) (m := ai758) (m1 := ao759) (m2 := ao820) (m3 := an758) (by decide) (by rfl) (by decide) a759 a820 (by rfl)
abbrev an642 : Mgr := ao758
abbrev ao642 : Mgr := {an642 with memo := ((PCSDD.BOp.and,1,144),144)::an642.memo}
theorem a642 : ApplyCertificate 12 DEFAULT_LIMITS 25 PCSDD.BOp.and 1 144 ai642 144 ao642 := by
  exact ApplyCertificate.branch (fuel := 24) (a0 := 1) (b0 := 144) (lo := 84) (hi := 143) (r := 144) (op := PCSDD.BOp.and) (m := ai642) (m1 := ao643) (m2 := ao758) (m3 := an642) (by decide) (by rfl) (by decide) a643 a758 (by rfl)
abbrev task : CTask 12 := ⟨PCSOmega.BForm.or   (PCSOmega.BForm.or     (PCSOmega.BForm.and (PCSOmega.BForm.atom 0) (PCSOmega.BForm.atom 6))     (PCSOmega.BForm.or       (PCSOmega.BForm.and (PCSOmega.BForm.atom 1) (PCSOmega.BForm.atom 7))       (PCSOmega.BForm.and (PCSOmega.BForm.atom 2) (PCSOmega.BForm.atom 8))))   (PCSOmega.BForm.or     (PCSOmega.BForm.and (PCSOmega.BForm.atom 3) (PCSOmega.BForm.atom 9))     (PCSOmega.BForm.or       (PCSOmega.BForm.and (PCSOmega.BForm.atom 4) (PCSOmega.BForm.atom 10))       (PCSOmega.BForm.and (PCSOmega.BForm.atom 5) (PCSOmega.BForm.atom 11)))),.ff,[]⟩
theorem pipe : pipeline task DEFAULT_LIMITS = .ok (.decided 1 144 0 144, {ao642 with wsteps := ao642.wsteps + witSteps 12 ao642.nodes 0 1 + witSteps 12 ao642.nodes 0 144}) := by
  exact pipeline_from_certificates (by rfl) c0 c388 (ApplyCertificate.sound a389) (ApplyCertificate.sound a642) (by decide)
theorem result : (check task DEFAULT_LIMITS).decision = .counterexample := by
  exact counterexample_from_pipeline pipe (by decide)
#print axioms result
end StagedDense
