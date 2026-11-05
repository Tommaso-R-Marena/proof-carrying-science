import PCSConditionalRuntime.PyInput

/-!
# `python_conditional_refines_reference`

The extracted current `check(task, limits)` of `pcs/experimental/conditional.py`, run by the
heap semantics on freshly allocated JSON inputs (`pyRunCheck`), refines the Lean reference
checker `PCSDD.check`:

for every JSON task `tj` denoting a typed conditional task `t` over distinct declared names,
and every valid limit pair, given only the contracts of the two unextracted callees
(`validate` accepts the task and returns it; `digest` computes some function `dg` of the JSON
value), there is one outcome `ok v h` such that

* with every sufficiently large interpreter fuel the run returns exactly `ok v h`;
* with every fuel the run returns either `fuel` (resource exhaustion of the interpreter, which
  claims nothing) or exactly `ok v h`;
* `v` reads back to the JSON receipt `receiptT names tj dg (PCSDD.check t lim)`: decision,
  context example, counterexample, unsat core, core-necessity witnesses, diagram nodes and roots,
  the reached limit, the four work counters, flags and both digests.

Successful runs and `ResourceLimit` runs are both covered (they are the cases of
`PCSDD.pipeline`).
-/

namespace PCSCR.Py

open PCSCR PCSDD PCSOmega

/-- The fuel that suffices for `check`. -/
def checkFuel {names : List String} (t : CTask names.length) (lim : Limits) : Nat :=
  applyFuel lim + fdepthL t.assumptions + fdepth t.source + fdepth t.candidate +
    2 * t.assumptions.length + names.length + 10

theorem check_run (ext : Ext) (dg : T → String) {names : List String} (hnd : names.Nodup) (tj : T)
    (t : CTask names.length) (htask : TaskDen names tj t) (lim : Limits) (hlv : lim.valid = true)
    (hval : ValidateAccepts ext tj) (hdg : DigestOK ext dg) (k : Nat) (hk : checkFuel t lim ≤ k) :
    ∃ v H, pyRunCheck ext (k + 5) tj (limT lim) = .ok v H ∧
      ∃ fu, readback fu H v = some (receiptT names tj dg (check t lim)) := by
  unfold pyRunCheck
  simp only [allocT_limT]
  generalize hP : allocT pyHeap0 tj = P
  obtain ⟨V0, Hp⟩ := P
  simp only
  have hagP : HAgree pyHeap0 Hp := by have := alloc_agree pyHeap0 tj; rw [hP] at this; exact this
  generalize hin_def : Hp ++ [limObj lim] = hin
  generalize hQ : allocT hin tj = Q
  obtain ⟨VA, h1⟩ := Q
  have hagQ : HAgree hin h1 := by have := alloc_agree hin tj; rw [hQ] at this; exact this
  obtain ⟨A, vkvs, NL, AS, as, vs, vc, eVA, hAlt, hNLlt, hASlt, hvar, has, hs, hc, hl, hH⟩ :=
    input_facts htask hin
  rw [hQ] at eVA hAlt hNLlt hASlt hH
  simp only at eVA hAlt hNLlt hASlt hH
  have hdeep : readback (hin.length + 1) hin V0 = some tj := by
    have := alloc_rb pyHeap0 tj hin (hin.length + 1) (by rw [hP]; rw [← hin_def]; exact HAgree.append _ _)
      (by rw [hP]; simp; rw [← hin_def]; simp <;> omega)
    rw [hP] at this; exact this
  have hrbVA : ∀ H, HAgree h1 H → readback (h1.length + 1) H VA = some tj := fun H hag => by
    have := alloc_rb hin tj H (h1.length + 1) (by rw [hQ]; exact hag) (by rw [hQ]; simp <;> omega)
    rw [hQ] at this; exact this
  have hag1 : ∀ l, HAgree h1 (h1 ++ l) := fun l => HAgree.append _ _
  have hL0 : readback (h1.length + 1) h1 (.ref Hp.length) = some (limT lim) := by
    have := alloc_rb Hp (limT lim) h1 (h1.length + 1) (by rw [allocT_limT, hin_def]; exact hagQ)
      (by rw [allocT_limT]; have := hagQ.1; rw [← hin_def] at this; simp at this ⊢; omega)
    rw [allocT_limT] at this; exact this
  have h0 : hget h1 0 = some (.dict [(.str "nodes", .int 4096), (.str "operations", .int 100000)]) := by
    have a1 : HAgree pyHeap0 h1 := (hagP.trans (by rw [← hin_def]; exact HAgree.append _ _)).trans hagQ
    rw [a1.2 0 (by simp [pyHeap0])]; rfl
  have hval' : ext "validate" [VA] h1 = .ok VA h1 := hval h1 VA _ (hrbVA h1 (HAgree.refl _))
  obtain ⟨hA1, -, -, -⟩ := hH h1 (HAgree.refl _)
  have hlim1 : HAgree h1 (h1 ++ [limObj lim]) := hag1 _
  obtain ⟨-, hNL1, -, -⟩ := hH _ hlim1
  generalize hHI : initHeap (h1 ++ [limObj lim]) NL h1.length = HI
  have hagI : HAgree h1 HI := by rw [← hHI]; unfold initHeap; rw [List.append_assoc]; exact hag1 _
  have hdg' : ext "digest" [VA] HI = .ok (.str (dg tj)) HI := hdg HI VA _ tj (hrbVA HI hagI)
  rw [show k + 5 = (k + 4) + 1 from rfl]
  unfold run
  rw [interp_succ_call]
  simp only [callBody, show lookupFn (pyCtx ext).prog "check" = some py_check from rfl]
  simp only [show py_check.params = ["value", "limits"] from rfl, List.length, List.zip, List.zipWith,
    List.reverse_cons, List.reverse_nil, List.nil_append, List.cons_append, ne_eq, not_true, if_false]
  have pre := check_prefix ext k hin h1 V0 VA Hp.length A NL tj lim names vkvs (dg tj) hdeep hQ hval' hL0 hlv
    eVA hA1 hvar h0 (by rw [hHI]; exact hdg')
  rw [hHI] at pre
  have hHIlen : HI.length = h1.length + 5 := by rw [← hHI]; simp
  generalize hD : (initAddrs (h1 ++ [limObj lim]).length NL h1.length).addOwn HI.length = D
  have hR : MRel names lim D (HI ++ [Obj.dict (resultKVs VA (.ref h1.length) (dg tj))]) Mgr.empty := by
    have := (init_mrel (lim := lim) (L := h1.length) hNL1 (by simp [hget])).addOwn (Obj.dict (resultKVs VA (.ref h1.length) (dg tj)))
    rw [hHI, hD] at this; exact this
  have hDmut : ∀ a, D.mut a → h1.length + 1 ≤ a := fun a ha => by
    rw [← hD] at ha
    simp only [Addrs.mut, Addrs.addOwn, initAddrs, List.mem_cons, List.not_mem_nil, or_false,
      List.length_append, List.length_singleton] at ha
    omega
  have hDself : D.self = h1.length + 1 := by rw [← hD]; simp [Addrs.addOwn, initAddrs]
  have hDnodes : D.nodes = h1.length + 2 := by rw [← hD]; simp [Addrs.addOwn, initAddrs]
  have hDuniq : D.uniq = h1.length + 3 := by rw [← hD]; simp [Addrs.addOwn, initAddrs]
  have hDmemo : D.memo = h1.length + 4 := by rw [← hD]; simp [Addrs.addOwn, initAddrs]
  have hRo : HI.length ∈ D.own := by rw [← hD]; simp [Addrs.addOwn]
  generalize hHs : HI ++ [Obj.dict (resultKVs VA (.ref h1.length) (dg tj))] = Hs at hR
  have hagHs : HAgree h1 Hs := by rw [← hHs]; exact hagI.trans (HAgree.append _ _)
  have hHslen : Hs.length = h1.length + 6 := by rw [← hHs]; simp [hHIlen]
  obtain ⟨hA, -, hAS, hF⟩ := hH Hs hagHs
  obtain ⟨hz, hfs, hfc⟩ := hF D (fun a ha => by have := hDmut a ha; omega)
  have hRk : hget Hs HI.length = some (.dict (resultKVs VA (.ref h1.length) (dg tj))) := by
    rw [← hHs]; simp [hget]
  have hbig : ∀ a, Big D Hs.length a → h1.length ≤ a := fun a ha => by
    rcases ha with ha | ha
    · have := hDmut a ha; omega
    · omega
  have rVA : ReadsM (Big D Hs.length) Hs VA tj :=
    (ReadsM.of_readback (hrbVA h1 (HAgree.refl _)) hbig).frame (hagHs.frameS _)
  have hLs : hget Hs h1.length = some (limObj lim) := by
    rw [← hHs, ← hHI]; simp [initHeap, hget]
  have rLA : ReadsM (Big D Hs.length) Hs (.ref h1.length) (limT lim) := by
    simp only [limObj] at hLs
    have hnb : ¬ Big D Hs.length h1.length := fun ha => by
      rcases ha with ha | ha
      · have := hDmut _ ha; omega
      · omega
    refine ReadsM.dict hLs hnb ?_
    exact ReadsKV.cons (ReadsM.int _ _ _) (ReadsKV.cons (ReadsM.int _ _ _) (ReadsKV.nil _ _))
  have hkv : ReadsKV (Big D Hs.length) Hs (resultKVs VA (.ref h1.length) (dg tj)) (initKT tj (dg tj) lim) := by
    simp only [resultKVs, initKT]
    exact ReadsKV.cons (ReadsM.str _ _ _) (ReadsKV.cons (ReadsM.str _ _ _) (ReadsKV.cons rVA
      (ReadsKV.cons (ReadsM.str _ _ _) (ReadsKV.cons rLA (ReadsKV.cons (ReadsM.none _ _)
      (ReadsKV.cons (ReadsM.none _ _) (ReadsKV.cons (ReadsM.none _ _) (ReadsKV.cons (ReadsM.none _ _)
      (ReadsKV.cons (ReadsM.none _ _) (ReadsKV.cons (ReadsM.none _ _) (ReadsKV.cons (ReadsM.none _ _)
      (ReadsKV.cons (ReadsM.str _ _ _) (ReadsKV.cons (ReadsM.bool _ _ _) (ReadsKV.cons (ReadsM.bool _ _ _)
      (ReadsKV.nil _ _)))))))))))))))
  have hmA : ¬ D.mut A := fun e => by have := hDmut _ e; omega
  have hmAS : ¬ D.mut AS := fun e => by have := hDmut _ e; omega
  obtain ⟨env', h', kvs', etry, hmg', hres', hR', hkv', W', -⟩ :=
    trystmt_sim ext hnd t (k + 3) (prefixEnv Hp.length V0 VA h1.length) Hs A AS HI.length vkvs as vs vc
      (resultKVs VA (.ref h1.length) (dg tj)) (initKT tj (dg tj) lim) (by unfold checkFuel at hk; omega)
      (by simp [prefixEnv, Env.get_set, hDself]) (by simp [prefixEnv, Env.get_set, eVA])
      (by simp [prefixEnv, Env.get_set, hHIlen])
      hA hmA has hAS hmAS hl hz hs hc hfs hfc hR hRo (by omega) (by omega) (by omega) (by omega) hRk hkv
  obtain ⟨H, etail, fu, hrb⟩ := tail_sim ext dg hdg (k + 2) env' h' D (finMgr t lim) HI.length kvs'
    (finKT names t lim (initKT tj (dg tj) lim)) hmg' hres' hR' hkv' W'
  rw [pre, hHs, check_body_drop6, execB_cons', show k + 4 = k + 3 + 1 from rfl, etry]
  simp only [seqF_normal]
  rw [show k + 3 + 1 = k + 2 + 2 from rfl, etail]
  refine ⟨_, H, rfl, fu, ?_⟩
  rw [hrb, receipt_fields_eq]

end PCSCR.Py

namespace PCSCR.Py

open PCSCR PCSDD PCSOmega

/-- **Python conditional refinement.**  For every JSON task denoting a typed conditional task
over distinct declared names and every valid limit pair (given only the contracts of the
unextracted `validate` and `digest`), the extracted current `check` has a single outcome
`ok v h`: it is returned with all sufficiently large fuel, every other fuel gives only `fuel`
(resource exhaustion of the interpreter, which claims nothing), and `v` reads back to the JSON
receipt of the reference `PCSDD.check t lim` — successful and resource-limited runs alike. -/
theorem python_conditional_refines_reference (ext : Ext) (dg : T → String) {names : List String}
    (hnd : names.Nodup) (tj : T) (t : CTask names.length) (htask : TaskDen names tj t) (lim : Limits)
    (hlv : lim.valid = true) (hval : ValidateAccepts ext tj) (hdg : DigestOK ext dg) :
    ∃ v h, Eventually (fun k => pyRunCheck ext k tj (limT lim)) (.ok v h) ∧
      (∀ k, pyRunCheck ext k tj (limT lim) = .fuel ∨ pyRunCheck ext k tj (limT lim) = .ok v h) ∧
      ∃ fu, readback fu h v = some (receiptT names tj dg (check t lim)) := by
  obtain ⟨v, h, e, rb⟩ := check_run ext dg hnd tj t htask lim hlv hval hdg (checkFuel t lim) (Nat.le_refl _)
  have ev : Eventually (fun k => pyRunCheck ext k tj (limT lim)) (.ok v h) := by
    refine ⟨checkFuel t lim + 5, fun k hk => ?_⟩
    have := run_stable (pyCtx ext) hk "check" _ _ (by
      show pyRunCheck ext (checkFuel t lim + 5) tj (limT lim) ≠ .fuel
      rw [e]; intro hc; cases hc)
    show pyRunCheck ext k tj (limT lim) = _
    unfold pyRunCheck at e ⊢
    rw [this, e]
  exact ⟨v, h, ev, fun k => by
    have := run_fuel_or (pyCtx ext) (f := "check") ev k
    exact this, rb⟩

end PCSCR.Py
