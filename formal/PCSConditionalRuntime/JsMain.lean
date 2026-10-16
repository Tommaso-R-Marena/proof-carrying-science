import PCSConditionalRuntime.JsCheckPrefix
import PCSConditionalRuntime.PyMain

/-!
# `javascript_conditional_refines_reference`

The extracted current `checkConditional(input, {limits})` of the website module
`public/conditional-core.mjs`, run by the heap semantics (dialect `js`: `===`, `undefined`,
`Map`/plain-object keys, exact safe-integer arithmetic) on freshly allocated JSON inputs
(`jsRunCheck`), refines the Lean reference checker `PCSDD.check`:

for every JSON task `tj` denoting a typed conditional task `t` over distinct declared names
within the bounds that `validateConditional` enforces (`JsTaskBounds`: at most 24 names, at most
8 assumptions, at most 128 nodes per formula), and every valid limit pair, given only the
contracts of the unextracted callees (`validateConditional` accepts the task and returns it;
`exact`, `integer` of `omega-core.mjs` behave as their source on the arguments used; `digest`
computes some function `dg` of the JSON value), there is one outcome `ok v h` such that

* with every sufficiently large interpreter fuel the run returns exactly `ok v h`;
* with every fuel the run returns either `fuel` (resource exhaustion, which claims nothing) or
  exactly `ok v h`;
* `v` reads back to the JSON receipt `receiptT names tj dg (PCSDD.check t lim)`.

Successful runs and `ResourceLimit` runs are both covered.  Every counter (`bdd_nodes`,
`apply_calls`, `ast_visits`, `witness_steps`) stays an exact safe integer along the run (the
semantics raises on unsafe JavaScript integers, which the simulation shows never happens).
-/

namespace PCSCR.Js

open PCSCR PCSDD PCSOmega PCSCR.Py

/-- The bounds enforced by the current `validateConditional` (`names.length>24`,
`t.assumptions.length>8`, `++count>128` reject). -/
def JsTaskBounds {names : List String} (t : CTask names.length) : Prop :=
  names.length ≤ 24 ∧ t.assumptions.length ≤ 8 ∧ t.source.size ≤ 128 ∧ t.candidate.size ≤ 128 ∧
    ∀ f ∈ t.assumptions, f.size ≤ 128

theorem fsizeL_le {n : Nat} : ∀ (fs : List (BForm n)), (∀ f ∈ fs, f.size ≤ 128) → fsizeL fs ≤ 128 * fs.length
  | [], _ => by simp [fsizeL]
  | f :: fs, h => by
    have h1 := h f (by simp)
    have h2 := fsizeL_le fs (fun g hg => h g (by simp [hg]))
    simp only [fsizeL, List.length_cons]
    omega

theorem JsTaskBounds.vis {names : List String} {t : CTask names.length} (hb : JsTaskBounds t) :
    fsizeL t.assumptions + t.source.size + t.candidate.size ≤ 9007199254740991 := by
  obtain ⟨-, h2, h3, h4, h5⟩ := hb
  have := fsizeL_le _ h5
  omega

theorem JsTaskBounds.ws {names : List String} {t : CTask names.length} (hb : JsTaskBounds t) :
    (t.assumptions.length + 2) * names.length ≤ 9007199254740991 := by
  obtain ⟨h1, h2, -, -, -⟩ := hb
  have := Nat.mul_le_mul (Nat.add_le_add_right h2 2) h1
  omega

theorem allocT_opts (h : Heap) (lim : Limits) :
    allocT h (.obj [("limits", limT lim)]) =
      (.ref (h.length + 1), h ++ [limObj lim, .dict [(.str "limits", .ref h.length)]]) := by
  simp [allocT, limT, allocKV, limObj]

theorem jcheck_run (ext : Ext) (dg : T → String) {names : List String} (hnd : names.Nodup) (tj : T)
    (t : CTask names.length) (htask : TaskDen names tj t) (hb : JsTaskBounds t) (lim : Limits)
    (hlv : lim.valid = true) (hval : JValidateAccepts ext tj) (hexact : JExactOK ext)
    (hint : JIntegerOK ext) (hdg : DigestOK ext dg) (k : Nat) (hk : checkFuel t lim ≤ k) :
    ∃ v H, jsRunCheck ext (k + 5) tj (limT lim) = .ok v H ∧
      ∃ fu, readback fu H v = some (receiptT names tj dg (check t lim)) := by
  unfold jsRunCheck
  simp only [allocT_opts]
  generalize hP : allocT jsHeap0 tj = P
  obtain ⟨V0, Hp⟩ := P
  simp only
  have hagP : HAgree jsHeap0 Hp := by have := alloc_agree jsHeap0 tj; rw [hP] at this; exact this
  generalize hin_def : Hp ++ [limObj lim, .dict [(.str "limits", .ref Hp.length)]] = hin
  generalize hQ : allocT hin tj = Q
  obtain ⟨VA, h1⟩ := Q
  have hagQ : HAgree hin h1 := by have := alloc_agree hin tj; rw [hQ] at this; exact this
  obtain ⟨A, vkvs, NL, AS, as, vs, vc, eVA, hAlt, hNLlt, hASlt, hvar, has, hs, hc, hl, hH⟩ :=
    jinput_facts htask hin
  rw [hQ] at eVA hAlt hNLlt hASlt hH
  simp only at eVA hAlt hNLlt hASlt hH
  have hdeep : readback (hin.length + 1) hin V0 = some tj := by
    have := alloc_rb jsHeap0 tj hin (hin.length + 1) (by rw [hP]; rw [← hin_def]; exact HAgree.append _ _)
      (by rw [hP]; simp; rw [← hin_def]; simp <;> omega)
    rw [hP] at this; exact this
  have hrbVA : ∀ H, HAgree h1 H → readback (h1.length + 1) H VA = some tj := fun H hag => by
    have := alloc_rb hin tj H (h1.length + 1) (by rw [hQ]; exact hag) (by rw [hQ]; simp <;> omega)
    rw [hQ] at this; exact this
  have hag1 : ∀ l, HAgree h1 (h1 ++ l) := fun l => HAgree.append _ _
  have hagLin : HAgree (Hp ++ [limObj lim]) hin := by
    rw [← hin_def, show [limObj lim, Obj.dict [(.str "limits", .ref Hp.length)]] =
      [limObj lim] ++ [Obj.dict [(.str "limits", .ref Hp.length)]] from rfl, ← List.append_assoc]
    exact HAgree.append _ _
  have hL0 : readback (h1.length + 1) h1 (.ref Hp.length) = some (limT lim) := by
    have := alloc_rb Hp (limT lim) h1 (h1.length + 1) (by rw [allocT_limT]; exact hagLin.trans hagQ)
      (by rw [allocT_limT]; have := hagQ.1; rw [← hin_def] at this; simp at this ⊢; omega)
    rw [allocT_limT] at this; exact this
  have hO : hget hin (Hp.length + 1) = some (.dict [(.str "limits", .ref Hp.length)]) := by
    rw [← hin_def]; simp [hget]
  have h2 : hget h1 2 = some (.dict [(.str "nodes", .int 4096), (.str "operations", .int 100000)]) := by
    have a1 : HAgree jsHeap0 h1 := (hagP.trans (by rw [← hin_def]; exact HAgree.append _ _)).trans hagQ
    rw [a1.2 2 (by simp [jsHeap0])]; rfl
  have hval' : ext "validateConditional" [VA] h1 = .ok VA h1 := hval h1 VA _ (hrbVA h1 (HAgree.refl _))
  obtain ⟨hA1, -, -, -⟩ := hH h1 (HAgree.refl _)
  have hpre1 : HAgree h1 (jpreHeap h1 lim) := hag1 _
  obtain ⟨-, hNL1, -, -⟩ := hH _ hpre1
  generalize hHI : jinitHeap (jpreHeap h1 lim) NL h1.length = HI
  have hagI : HAgree h1 HI := by
    rw [← hHI]; unfold jinitHeap jpreHeap; rw [List.append_assoc]; exact hag1 _
  have hdg' : ext "digest" [VA] HI = .ok (.str (dg tj)) HI := hdg HI VA _ tj (hrbVA HI hagI)
  rw [show k + 5 = (k + 4) + 1 from rfl]
  unfold run
  rw [interp_succ_call]
  simp only [callBody, show lookupFn (jsCtx ext).prog "checkConditional" = some js_checkConditional from rfl]
  simp only [show js_checkConditional.params = ["input", "%opts"] from rfl, List.length, List.zip,
    List.zipWith, List.reverse_cons, List.reverse_nil, List.nil_append, List.cons_append, ne_eq, not_true,
    if_false]
  obtain ⟨env0, e0t, e0m, e0r, pre⟩ := jcheck_prefix ext hint hexact k hin h1 V0 VA (Hp.length + 1) Hp.length
    A NL tj lim vkvs (dg tj) hO hdeep hQ hval' hL0 hlv eVA hA1 hvar h2 (by rw [hHI]; exact hdg')
  rw [hHI] at pre
  have hHIlen : HI.length = h1.length + 7 := by rw [← hHI]; simp [jpreHeap]
  have hprelen : (jpreHeap h1 lim).length = h1.length + 3 := by simp [jpreHeap]
  generalize hD : (initAddrs (jpreHeap h1 lim).length NL h1.length).addOwn HI.length = D
  have hR : JMRel names lim D (HI ++ [Obj.dict (resultKVs VA (.ref h1.length) (dg tj))]) Mgr.empty := by
    have := (jinit_mrel (lim := lim) (L := h1.length) hlv hNL1 (by simp [jpreHeap, hget])).addOwn
      (Obj.dict (resultKVs VA (.ref h1.length) (dg tj)))
    rw [hHI, hD] at this; exact this
  have hDmut : ∀ a, D.mut a → h1.length + 3 ≤ a := fun a ha => by
    rw [← hD] at ha
    simp only [Addrs.mut, Addrs.addOwn, initAddrs, List.mem_cons, List.not_mem_nil, or_false, hprelen] at ha
    omega
  have hDself : D.self = h1.length + 3 := by rw [← hD]; simp [Addrs.addOwn, initAddrs, hprelen]
  have hDnodes : D.nodes = h1.length + 4 := by rw [← hD]; simp [Addrs.addOwn, initAddrs, hprelen]
  have hDuniq : D.uniq = h1.length + 5 := by rw [← hD]; simp [Addrs.addOwn, initAddrs, hprelen]
  have hDmemo : D.memo = h1.length + 6 := by rw [← hD]; simp [Addrs.addOwn, initAddrs, hprelen]
  have hRo : HI.length ∈ D.own := by rw [← hD]; simp [Addrs.addOwn]
  generalize hHs : HI ++ [Obj.dict (resultKVs VA (.ref h1.length) (dg tj))] = Hs at hR
  have hagHs : HAgree h1 Hs := by rw [← hHs]; exact hagI.trans (HAgree.append _ _)
  have hHslen : Hs.length = h1.length + 8 := by rw [← hHs]; simp [hHIlen]
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
    rw [← hHs, ← hHI]; simp [jinitHeap, jpreHeap, hget]
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
    jtrystmt_sim ext hnd t (k + 3) env0 Hs A AS HI.length vkvs as vs vc
      (resultKVs VA (.ref h1.length) (dg tj)) (initKT tj (dg tj) lim) (by unfold checkFuel at hk; omega)
      (by rw [e0m, hDself]) (by rw [e0t, eVA])
      (by rw [e0r, hHIlen])
      hA hmA has hAS hmAS hl hz hs hc hfs hfc hR hRo (by omega) (by omega) (by omega) (by omega) hRk hkv
      hb.vis hb.ws
  obtain ⟨H, etail, fu, hrb⟩ := jtail_sim ext dg hdg (k + 2) env' h' D (finMgr t lim) HI.length kvs'
    (finKT names t lim (initKT tj (dg tj) lim)) hmg' hres' hR' hkv' W'
  rw [pre, hHs, check_body_drop9, execB_cons', show k + 4 = k + 3 + 1 from rfl, etry]
  simp only [seqF_normal]
  rw [show k + 3 + 1 = k + 2 + 2 from rfl, etail]
  refine ⟨_, H, rfl, fu, ?_⟩
  rw [hrb, receipt_fields_eq]

end PCSCR.Js

namespace PCSCR.Js

open PCSCR PCSDD PCSOmega PCSCR.Py

/-- **JavaScript conditional refinement.**  For every JSON task denoting a typed conditional
task over distinct declared names within the bounds enforced by `validateConditional`, and every
valid limit pair (given only the contracts of the unextracted `validateConditional`, `exact`,
`integer` and `digest`), the extracted current `checkConditional` has a single outcome `ok v h`:
it is returned with all sufficiently large fuel, every other fuel gives only `fuel` (resource
exhaustion of the interpreter, which claims nothing), and `v` reads back to the JSON receipt of
the reference `PCSDD.check t lim` — successful and resource-limited runs alike. -/
theorem javascript_conditional_refines_reference (ext : Ext) (dg : T → String) {names : List String}
    (hnd : names.Nodup) (tj : T) (t : CTask names.length) (htask : TaskDen names tj t)
    (hb : JsTaskBounds t) (lim : Limits) (hlv : lim.valid = true) (hval : JValidateAccepts ext tj)
    (hexact : JExactOK ext) (hint : JIntegerOK ext) (hdg : DigestOK ext dg) :
    ∃ v h, Eventually (fun k => jsRunCheck ext k tj (limT lim)) (.ok v h) ∧
      (∀ k, jsRunCheck ext k tj (limT lim) = .fuel ∨ jsRunCheck ext k tj (limT lim) = .ok v h) ∧
      ∃ fu, readback fu h v = some (receiptT names tj dg (check t lim)) := by
  obtain ⟨v, h, e, rb⟩ := jcheck_run ext dg hnd tj t htask hb lim hlv hval hexact hint hdg (checkFuel t lim)
    (Nat.le_refl _)
  have ev : Eventually (fun k => jsRunCheck ext k tj (limT lim)) (.ok v h) := by
    refine ⟨checkFuel t lim + 5, fun k hk => ?_⟩
    have := run_stable (jsCtx ext) hk "checkConditional" _ _ (by
      show jsRunCheck ext (checkFuel t lim + 5) tj (limT lim) ≠ .fuel
      rw [e]; intro hc; cases hc)
    show jsRunCheck ext k tj (limT lim) = _
    unfold jsRunCheck at e ⊢
    rw [this, e]
  exact ⟨v, h, ev, fun k => by
    have := run_fuel_or (jsCtx ext) (f := "checkConditional") ev k
    exact this, rb⟩

end PCSCR.Js
