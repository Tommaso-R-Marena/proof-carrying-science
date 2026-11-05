import PCSConditionalRuntime.PyCheckBase
import PCSConditionalRuntime.JsEval
import PCSConditionalRuntime.JsConj
import PCSConditionalRuntime.JsWorld

/-!
# Caller-owned addresses

`check` itself allocates and overwrites objects (the premise list, the result dictionary,
comprehension accumulators, …) between calls of `Diagram` methods.  They are recorded as
*owned* addresses `D.own`: the manager relation `JMRel` keeps them apart from the node objects,
so `check` may overwrite them (`JMRel.hsetOwn`), while the method simulations — applied a second
time with the owned set emptied (`Addrs.base`) — show that the methods themselves never touch
them (`JSimOut.both`).
-/

namespace PCSCR.Js

open PCSCR PCSDD PCSOmega PCSCR.Py

theorem jdiagramFields_base (D : Addrs) (m : Mgr) : jdiagramFields D.base m = jdiagramFields D m := rfl
theorem jdiagramFields_addOwn (D : Addrs) (a : Nat) (m : Mgr) :
    jdiagramFields (D.addOwn a) m = jdiagramFields D m := rfl

/-- Weakening the mutable set (same `Diagram` objects, fewer owned addresses). -/
theorem JMRel.weaken {names : List String} {lim : Limits} {D D' : Addrs} {h : Heap} {m : Mgr}
    (hR : JMRel names lim D h m) (e1 : D'.self = D.self) (e2 : D'.names = D.names) (e3 : D'.lim = D.lim)
    (e4 : D'.nodes = D.nodes) (e5 : D'.uniq = D.uniq) (e6 : D'.memo = D.memo)
    (hown : ∀ a ∈ D'.own, a ∈ D.own) : JMRel names lim D' h m := by
  have hm : ∀ b, ¬ D.mut b → ¬ D'.mut b := by
    intro b hnm hm'
    simp only [Addrs.mut, e1, e4, e5, e6] at hm' hnm
    rcases hm' with e | e | e | e | e
    · exact hnm (Or.inl e)
    · exact hnm (Or.inr (Or.inl e))
    · exact hnm (Or.inr (Or.inr (Or.inl e)))
    · exact hnm (Or.inr (Or.inr (Or.inr (Or.inl e))))
    · exact hnm (Or.inr (Or.inr (Or.inr (Or.inr (hown b e)))))
  obtain ⟨kl, hkl, hlr⟩ := hR.limK
  obtain ⟨p, hp, hpr⟩ := hR.nodes
  obtain ⟨u, hu, hur⟩ := hR.uniq
  obtain ⟨mm, hmm, hmr⟩ := hR.memo
  have hs := hR.self
  have hn := hR.names
  rw [← e1] at hs; rw [← e2] at hn; rw [← e3] at hkl; rw [← e4] at hp; rw [← e5] at hu; rw [← e6] at hmm
  have hdf : jdiagramFields D' m = jdiagramFields D m := by simp [jdiagramFields, e2, e3, e4, e5, e6]
  rw [← hdf] at hs
  have d1 := hR.d1; have d2 := hR.d2; have d3 := hR.d3; have d4 := hR.d4; have d5 := hR.d5
  have d6 := hR.d6
  rw [← e1, ← e4] at d1; rw [← e1, ← e5] at d2; rw [← e1, ← e6] at d3; rw [← e4, ← e5] at d4
  rw [← e4, ← e6] at d5; rw [← e5, ← e6] at d6
  have n1 := hm _ hR.names_nm; have n2 := hm _ hR.lim_nm
  rw [← e2] at n1; rw [← e3] at n2
  exact ⟨hs, hn, ⟨kl, hkl, hlr⟩,
    ⟨p, hp, hpr.1, fun i hi => by
      obtain ⟨b, hb, hnm, hg⟩ := hpr.2 i hi
      exact ⟨b, hb, hm b hnm, hg⟩⟩,
    ⟨u, hu, hur⟩, ⟨mm, hmm, hmr⟩, n1, n2, d1, d2, d3, d4, d5, d6,
    fun a ha => hR.own_lt a (hown a ha), hR.lv⟩

theorem JMRel.base {names : List String} {lim : Limits} {D : Addrs} {h : Heap} {m : Mgr}
    (hR : JMRel names lim D h m) : JMRel names lim D.base h m :=
  hR.weaken rfl rfl rfl rfl rfl rfl (by simp)

/-- A freshly allocated object can be owned. -/
theorem JMRel.addOwn {names : List String} {lim : Limits} {D : Addrs} {h : Heap} {m : Mgr}
    (hR : JMRel names lim D h m) (o : Obj) : JMRel names lim (D.addOwn h.length) (h ++ [o]) m := by
  have hm : ∀ b, b < h.length → ¬ D.mut b → ¬ (D.addOwn h.length).mut b := by
    intro b hb hnm hm'
    rcases Addrs.addOwn_mut hm' with e | e
    · exact hnm e
    · omega
  have hl := hR.addrs_lt
  obtain ⟨kl, hkl, hlr⟩ := hR.limK
  obtain ⟨p, hp, hpr⟩ := hR.nodes
  obtain ⟨u, hu, hur⟩ := hR.uniq
  obtain ⟨mm, hmm, hmr⟩ := hR.memo
  refine ⟨?_, ?_, ⟨kl, ?_, hlr⟩, ⟨p, ?_, hpr.1, fun i hi => ?_⟩, ⟨u, ?_, hur⟩, ⟨mm, ?_, hmr⟩,
    hm _ hl.2.1 hR.names_nm, hm _ hl.2.2.1 hR.lim_nm, hR.d1, hR.d2, hR.d3, hR.d4, hR.d5, hR.d6, ?_, hR.lv⟩
  · rw [jdiagramFields_addOwn]; simp only [Addrs.addOwn_self, hget_append_lt o hl.1]; exact hR.self
  · simp only [Addrs.addOwn_names, hget_append_lt o hl.2.1]; exact hR.names
  · simp only [Addrs.addOwn_lim, hget_append_lt o hl.2.2.1]; exact hkl
  · simp only [Addrs.addOwn_nodes, hget_append_lt o hl.2.2.2.1]; exact hp
  · obtain ⟨b, hb, hnm, hg⟩ := hpr.2 i hi
    exact ⟨b, hb, hm b (hget_lt hg) hnm, by rw [hget_append_lt o (hget_lt hg)]; exact hg⟩
  · simp only [Addrs.addOwn_uniq, hget_append_lt o hl.2.2.2.2.1]; exact hu
  · simp only [Addrs.addOwn_memo, hget_append_lt o hl.2.2.2.2.2]; exact hmm
  · intro a ha
    simp only [Addrs.addOwn_own, List.mem_cons] at ha
    rcases ha with rfl | ha
    · simp
    · have := hR.own_lt a ha; simp; omega

/-- `check` may overwrite an owned address (other than the `Diagram` objects). -/
theorem JMRel.hsetOwn {names : List String} {lim : Limits} {D : Addrs} {h : Heap} {m : Mgr}
    (hR : JMRel names lim D h m) {a : Nat} (ha : a ∈ D.own) (n1 : a ≠ D.self) (n2 : a ≠ D.nodes)
    (n3 : a ≠ D.uniq) (n4 : a ≠ D.memo) (o : Obj) :
    JMRel names lim D (hset h a o) m ∧ Frame D h (hset h a o) := by
  have hF : Frame D h (hset h a o) := Frame.hset _ _ (Or.inr (Or.inr (Or.inr (Or.inr ha))))
  obtain ⟨p, hp, hpr⟩ := hR.nodes
  obtain ⟨u, hu, hur⟩ := hR.uniq
  obtain ⟨mm, hmm, hmr⟩ := hR.memo
  refine ⟨hR.transport hF ?_ ⟨p, ?_, hpr.frame hF⟩ ⟨u, ?_, hur⟩ ⟨mm, ?_, hmr⟩, hF⟩
  · rw [hget_hset_ne _ n1]; exact hR.self
  · rw [hget_hset_ne _ n2]; exact hp
  · rw [hget_hset_ne _ n3]; exact hu
  · rw [hget_hset_ne _ n4]; exact hmm

/-! ## Formula trees under the same operations -/

theorem JFRel.weaken {D D' : Addrs} {h : Heap} {names : List String} {n : Nat}
    (hm : ∀ b, b < h.length → ¬ D.mut b → ¬ D'.mut b) :
    ∀ (f : BForm n) (v : V), JFRel D h names v f → JFRel D' h names v f := by
  intro f
  induction f with
  | atom i =>
    intro v hv; match v, hv with
    | .ref a, ⟨hma, kvs, hg, h1, h2⟩ => exact ⟨hm a (hget_lt hg) hma, kvs, hg, h1, h2⟩
  | tt =>
    intro v hv; match v, hv with
    | .ref a, ⟨hma, kvs, hg, h1⟩ => exact ⟨hm a (hget_lt hg) hma, kvs, hg, h1⟩
  | ff =>
    intro v hv; match v, hv with
    | .ref a, ⟨hma, kvs, hg, h1⟩ => exact ⟨hm a (hget_lt hg) hma, kvs, hg, h1⟩
  | not f ih =>
    intro v hv; match v, hv with
    | .ref a, ⟨hma, kvs, c, hg, h1, h2, h3⟩ => exact ⟨hm a (hget_lt hg) hma, kvs, c, hg, h1, h2, ih c h3⟩
  | and f g ih1 ih2 =>
    intro v hv; match v, hv with
    | .ref a, ⟨hma, kvs, c1, c2, hg, h1, h2, h3, h4, h5⟩ =>
      exact ⟨hm a (hget_lt hg) hma, kvs, c1, c2, hg, h1, h2, h3, ih1 c1 h4, ih2 c2 h5⟩
  | or f g ih1 ih2 =>
    intro v hv; match v, hv with
    | .ref a, ⟨hma, kvs, c1, c2, hg, h1, h2, h3, h4, h5⟩ =>
      exact ⟨hm a (hget_lt hg) hma, kvs, c1, c2, hg, h1, h2, h3, ih1 c1 h4, ih2 c2 h5⟩
  | imp f g ih1 ih2 =>
    intro v hv; match v, hv with
    | .ref a, ⟨hma, kvs, c1, c2, hg, h1, h2, h3, h4, h5⟩ =>
      exact ⟨hm a (hget_lt hg) hma, kvs, c1, c2, hg, h1, h2, h3, ih1 c1 h4, ih2 c2 h5⟩

theorem JFRel.base {D : Addrs} {h : Heap} {names : List String} {n : Nat} {f : BForm n} {v : V}
    (hf : JFRel D h names v f) : JFRel D.base h names v f :=
  JFRel.weaken (fun b _ hb hm => hb (Addrs.base_mut hm)) f v hf

theorem JFRel.addOwn {D : Addrs} {h : Heap} {names : List String} {n : Nat} {f : BForm n} {v : V}
    (hf : JFRel D h names v f) (o : Obj) : JFRel (D.addOwn h.length) (h ++ [o]) names v f := by
  have h1 := JFRel.weaken (D' := D.addOwn h.length) (fun b hb hnm hm => by
    rcases Addrs.addOwn_mut hm with e | e
    · exact hnm e
    · omega) f v hf
  exact JFRel.frame (Frame.append _ h o) f v h1

/-! ## Running a method simulation twice -/

/-- Outcome of a method call, with both frames: the full one (owned addresses may be
overwritten) and the base one (only the `Diagram` objects change). -/
def JSimOut2 (names : List String) (lim : Limits) (D : Addrs) (h : Heap) :
    Except (LimitReached × Mgr) (Nat × Mgr) → Out V → Prop
  | .ok (r, m'), o => ∃ h', o = .ok (iv r) h' ∧ JMRel names lim D h' m' ∧ Frame D.base h h'
  | .error (e, m'), o => ∃ h' a, o = .exc (.obj (.ref a)) h' ∧
      hget h' a = some (.inst "ResourceLimit" [("message", .str e.name)]) ∧
      JMRel names lim D h' m' ∧ Frame D.base h h'

theorem JSimOut.both {names : List String} {lim : Limits} {D : Addrs} {h : Heap}
    {r : Except (LimitReached × Mgr) (Nat × Mgr)} {o : Out V}
    (s1 : JSimOut names lim D h r o) (s2 : JSimOut names lim D.base h r o) : JSimOut2 names lim D h r o := by
  rcases r with ⟨e, m'⟩ | ⟨x, m'⟩
  · obtain ⟨h1, a1, e1, g1, R1, _⟩ := s1
    obtain ⟨h2, a2, e2, _, _, F2⟩ := s2
    rw [e1] at e2; cases e2
    exact ⟨h1, a1, e1, g1, R1, F2⟩
  · obtain ⟨h1, e1, R1, _⟩ := s1
    obtain ⟨h2, e2, _, F2⟩ := s2
    rw [e1] at e2; cases e2
    exact ⟨h1, e1, R1, F2⟩

end PCSCR.Js
