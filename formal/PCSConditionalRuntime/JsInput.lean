import PCSConditionalRuntime.PyInput
import PCSConditionalRuntime.JsTail

/-!
# The structured clone of an accepted typed task (JavaScript)

`jinput_facts`: the JavaScript counterpart of `input_facts` — after
`t = validateConditional(structuredClone(input))`, the heap copy of a JSON task denoting the
typed task `t` is an object whose fields (looked up with `===` on string keys) are the declared
names, the premise trees and the query trees (`JFRel`), on every heap extending the copy.
-/

namespace PCSCR.Js

open PCSCR PCSDD PCSOmega PCSCR.Py

theorem jtlook_dictFind {fu : Nat} {h : Heap} :
    ∀ (kvs : List (V × V)) (kvs' : List (String × T)),
    kvs.mapM (fun (p : V × V) => match p.1 with
        | .str k => (readback fu h p.2).map fun t => (k, t)
        | _ => none) = some kvs' →
    ∀ (x : String) (t : T), tlook kvs' x = some t →
      ∃ v, dictFind .js kvs (.str x) = some v ∧ readback fu h v = some t
  | [], kvs', hm, x, t, ht => by
      simp at hm; subst hm; simp [tlook] at ht
  | (k, w) :: rest, kvs', hm, x, t, ht => by
      simp only [List.mapM_cons, Option.bind_eq_bind] at hm
      cases k with
      | str k =>
        simp only at hm
        cases hw : readback fu h w with
        | none => simp [hw] at hm
        | some tw =>
          rw [hw] at hm
          simp only [Option.map_some, Option.bind_some] at hm
          cases hr : rest.mapM (fun (p : V × V) => match p.1 with
              | .str k => (readback fu h p.2).map fun t => (k, t)
              | _ => none) with
          | none => simp [hr] at hm
          | some ys =>
            rw [hr] at hm
            simp only [Option.bind_some, Option.pure_def, Option.some.injEq] at hm
            subst hm
            simp only [tlook] at ht
            by_cases e : k = x
            · subst e
              simp at ht; subst ht
              exact ⟨w, by simp [dictFind, jkeyEq_str], hw⟩
            · simp only [e, if_false] at ht
              obtain ⟨v, h1, h2⟩ := jtlook_dictFind rest ys hr x t ht
              exact ⟨v, by simp [dictFind, jkeyEq_str, e, h1], h2⟩
      | _ => simp at hm

/-- A field of a read-back object. -/
theorem jrb_field {fu : Nat} {h : Heap} {v : V} {kvs' : List (String × T)}
    (hr : readback fu h v = some (.obj kvs')) {x : String} {t : T} (ht : tlook kvs' x = some t) :
    ∃ fu' a kvs w, fu = fu' + 1 ∧ v = .ref a ∧ hget h a = some (.dict kvs) ∧
      dictFind .js kvs (.str x) = some w ∧ readback fu' h w = some t := by
  obtain ⟨fu', a, kvs, e1, e2, hg, hm⟩ := rb_obj hr
  obtain ⟨w, h1, h2⟩ := jtlook_dictFind kvs kvs' hm x t ht
  exact ⟨fu', a, kvs, w, e1, e2, hg, h1, h2⟩

/-- **Read-back denotation gives a heap formula tree.** -/
theorem rb_JFRel {D : Addrs} {h : Heap} {names : List String} {n : Nat}
    (hnm : ∀ a, a < h.length → ¬ D.mut a) :
    ∀ (f : BForm n) (fu : Nat) (v : V) (tj : T), readback fu h v = some tj → FDen names tj f →
      JFRel D h names v f := by
  intro f
  induction f with
  | atom i =>
    intro fu v tj hr hd
    match tj, hd with
    | .obj kvs', ⟨hop, hsym⟩ =>
      obtain ⟨_, a, kvs, w1, -, rfl, hg, f1, r1⟩ := jrb_field hr hop
      obtain ⟨_, _, _, w2, -, e2, hg2, f2, r2⟩ := jrb_field hr hsym
      cases e2; rw [hg] at hg2; cases hg2
      exact ⟨hnm a (hget_lt hg), kvs, hg, by rw [f1, rb_str r1], by rw [f2, rb_str r2]⟩
  | tt =>
    intro fu v tj hr hd
    match tj, hd with
    | .obj kvs', hop =>
      obtain ⟨_, a, kvs, w1, -, rfl, hg, f1, r1⟩ := jrb_field hr hop
      exact ⟨hnm a (hget_lt hg), kvs, hg, by rw [f1, rb_str r1]⟩
  | ff =>
    intro fu v tj hr hd
    match tj, hd with
    | .obj kvs', hop =>
      obtain ⟨_, a, kvs, w1, -, rfl, hg, f1, r1⟩ := jrb_field hr hop
      exact ⟨hnm a (hget_lt hg), kvs, hg, by rw [f1, rb_str r1]⟩
  | not f ih =>
    intro fu v tj hr hd
    match tj, hd with
    | .obj kvs', ⟨hop, b, hb, hdb⟩ =>
      obtain ⟨_, a, kvs, w1, -, rfl, hg, f1, r1⟩ := jrb_field hr hop
      obtain ⟨_, _, _, w2, -, e2, hg2, f2, r2⟩ := jrb_field hr hb
      cases e2; rw [hg] at hg2; cases hg2
      exact ⟨hnm a (hget_lt hg), kvs, w2, hg, by rw [f1, rb_str r1], f2, ih _ w2 b r2 hdb⟩
  | and f g ih1 ih2 =>
    intro fu v tj hr hd
    match tj, hd with
    | .obj kvs', ⟨hop, l, r, hl, hrr, hdl, hdr⟩ =>
      obtain ⟨_, a, kvs, w1, -, rfl, hg, f1, r1⟩ := jrb_field hr hop
      obtain ⟨_, _, _, w2, -, e2, hg2, f2, r2⟩ := jrb_field hr hl
      obtain ⟨_, _, _, w3, -, e3, hg3, f3, r3⟩ := jrb_field hr hrr
      cases e2; cases e3; rw [hg] at hg2 hg3; cases hg2; cases hg3
      exact ⟨hnm a (hget_lt hg), kvs, w2, w3, hg, by rw [f1, rb_str r1], f2, f3,
        ih1 _ w2 l r2 hdl, ih2 _ w3 r r3 hdr⟩
  | or f g ih1 ih2 =>
    intro fu v tj hr hd
    match tj, hd with
    | .obj kvs', ⟨hop, l, r, hl, hrr, hdl, hdr⟩ =>
      obtain ⟨_, a, kvs, w1, -, rfl, hg, f1, r1⟩ := jrb_field hr hop
      obtain ⟨_, _, _, w2, -, e2, hg2, f2, r2⟩ := jrb_field hr hl
      obtain ⟨_, _, _, w3, -, e3, hg3, f3, r3⟩ := jrb_field hr hrr
      cases e2; cases e3; rw [hg] at hg2 hg3; cases hg2; cases hg3
      exact ⟨hnm a (hget_lt hg), kvs, w2, w3, hg, by rw [f1, rb_str r1], f2, f3,
        ih1 _ w2 l r2 hdl, ih2 _ w3 r r3 hdr⟩
  | imp f g ih1 ih2 =>
    intro fu v tj hr hd
    match tj, hd with
    | .obj kvs', ⟨hop, l, r, hl, hrr, hdl, hdr⟩ =>
      obtain ⟨_, a, kvs, w1, -, rfl, hg, f1, r1⟩ := jrb_field hr hop
      obtain ⟨_, _, _, w2, -, e2, hg2, f2, r2⟩ := jrb_field hr hl
      obtain ⟨_, _, _, w3, -, e3, hg3, f3, r3⟩ := jrb_field hr hrr
      cases e2; cases e3; rw [hg] at hg2 hg3; cases hg2; cases hg3
      exact ⟨hnm a (hget_lt hg), kvs, w2, w3, hg, by rw [f1, rb_str r1], f2, f3,
        ih1 _ w2 l r2 hdl, ih2 _ w3 r r3 hdr⟩





theorem jallocKV_find : ∀ (h : Heap) (kvs : List (String × T)) (x : String) (t : T), tlook kvs x = some t →
    ∃ h', HAgree (allocT h' t).2 (allocKV h kvs).2 ∧ dictFind .js (allocKV h kvs).1 (.str x) = some (allocT h' t).1
  | _, [], _, _, ht => by simp [tlook] at ht
  | h, (k, t0) :: rest, x, t, ht => by
    simp only [tlook] at ht
    by_cases hk : k = x
    · subst hk
      simp only [if_true, Option.some.injEq] at ht
      subst ht
      refine ⟨h, ?_, ?_⟩
      · simpa [allocKV] using allocKV_agree (allocT h t0).2 rest
      · simp [allocKV, dictFind, jkeyEq_str]
    · simp only [hk, if_false] at ht
      obtain ⟨h', hag, hf⟩ := jallocKV_find (allocT h t0).2 rest x t ht
      refine ⟨h', by simpa [allocKV] using hag, ?_⟩
      simp [allocKV, dictFind, jkeyEq_str, hk, hf]

theorem mapM_zip_JFRel {D : Addrs} {h : Heap} {names : List String} {n : Nat} {fu : Nat}
    (hnm : ∀ a, a < h.length → ¬ D.mut a) :
    ∀ (xs : List V) (ys : List T) (fs : List (BForm n)), xs.mapM (readback fu h) = some ys →
      ys.length = fs.length → (∀ p ∈ ys.zip fs, FDen names p.1 p.2) →
      ∀ p ∈ xs.zip fs, JFRel D h names p.1 p.2
  | [], _, _, _, _, _ => by simp
  | x :: xs, ys, fs, hm, hl, hd => by
    simp only [List.mapM_cons, Option.bind_eq_bind] at hm
    cases hx : readback fu h x with
    | none => simp [hx] at hm
    | some y =>
      rw [hx] at hm
      simp only [Option.bind_some] at hm
      cases hr : xs.mapM (readback fu h) with
      | none => simp [hr] at hm
      | some ys' =>
        rw [hr] at hm
        simp only [Option.bind_some, Option.pure_def, Option.some.injEq] at hm
        subst hm
        cases fs with
        | nil => simp
        | cons f fs =>
          intro p hp
          simp only [List.zip_cons_cons, List.mem_cons] at hp
          rcases hp with rfl | hp
          · exact rb_JFRel hnm f fu x y hx (hd (y, f) (by simp))
          · exact mapM_zip_JFRel hnm xs ys' fs hr (by simpa using hl)
              (fun q hq => hd q (by simp [hq])) p hp

theorem jinput_facts {names : List String} {tj : T} {t : CTask names.length} (htask : TaskDen names tj t)
    (hin : Heap) :
    ∃ A vkvs NL AS as vs vc, (allocT hin tj).1 = .ref A ∧ A < (allocT hin tj).2.length ∧
      NL < (allocT hin tj).2.length ∧ AS < (allocT hin tj).2.length ∧
      dictFind .js vkvs (.str "variables") = some (.ref NL) ∧
      dictFind .js vkvs (.str "assumptions") = some (.ref AS) ∧
      dictFind .js vkvs (.str "source") = some vs ∧ dictFind .js vkvs (.str "candidate") = some vc ∧
      as.length = t.assumptions.length ∧
      ∀ H, HAgree (allocT hin tj).2 H →
        hget H A = some (.dict vkvs) ∧ hget H NL = some (.list (names.map V.str)) ∧
        hget H AS = some (.list as) ∧
        ∀ D : Addrs, (∀ a, D.mut a → (allocT hin tj).2.length ≤ a) →
          (∀ p ∈ as.zip t.assumptions, JFRel D H names p.1 p.2) ∧
          JFRel D H names vs t.source ∧ JFRel D H names vc t.candidate := by
  obtain ⟨kvsT, sT, cT, asT, rfl, hvar, hsrc, hfs, hcand, hfc, hass, hlen, hzip⟩ := htask
  generalize hp : allocKV hin kvsT = p
  have hT : allocT hin (.obj kvsT) = (.ref p.2.length, p.2 ++ [.dict p.1]) := by simp [allocT, hp]
  rw [hT]
  simp only
  -- variables
  obtain ⟨h1, ag1, f1⟩ := jallocKV_find hin kvsT _ _ hvar
  rw [hp] at ag1 f1
  simp only [allocT, allocL_strs] at ag1 f1
  -- assumptions
  obtain ⟨h2, ag2, f2⟩ := jallocKV_find hin kvsT _ _ hass
  rw [hp] at ag2 f2
  simp only [allocT] at ag2 f2
  -- source / candidate
  obtain ⟨h3, ag3, f3⟩ := jallocKV_find hin kvsT _ _ hsrc
  obtain ⟨h4, ag4, f4⟩ := jallocKV_find hin kvsT _ _ hcand
  rw [hp] at ag3 f3 ag4 f4
  have ag3' : HAgree (allocT h3 sT).2 (p.2 ++ [Obj.dict p.1]) := ag3.trans (HAgree.append _ _)
  have ag4' : HAgree (allocT h4 cT).2 (p.2 ++ [Obj.dict p.1]) := ag4.trans (HAgree.append _ _)
  have rb3 := alloc_rb h3 sT _ ((p.2 ++ [Obj.dict p.1]).length + 1) ag3' (by have := ag3'.1; omega)
  have rb4 := alloc_rb h4 cT _ ((p.2 ++ [Obj.dict p.1]).length + 1) ag4' (by have := ag4'.1; omega)
  have ag2' : HAgree (allocL h2 asT).2 (p.2 ++ [Obj.dict p.1]) :=
    ((HAgree.append _ _).trans ag2).trans (HAgree.append _ _)
  have rb2 := allocL_rb h2 asT _ ((p.2 ++ [Obj.dict p.1]).length + 1) ag2' (by have := ag2'.1; omega)
  have l1 := ag1.1
  have l2 := ag2.1
  simp only [List.length_append, List.length_singleton] at l1 l2
  refine ⟨p.2.length, p.1, _, _, (allocL h2 asT).1, _, _, rfl, by simp, by simp; omega, by simp; omega,
    f1, f2, f3, f4, by rw [allocL_length, hlen], fun H hag => ?_⟩
  have hagp : HAgree p.2 H := (HAgree.append p.2 [.dict p.1]).trans hag
  refine ⟨?_, ?_, ?_, fun D hD => ?_⟩
  · rw [hag.2 _ (by simp)]; simp [hget]
  · rw [hagp.2 _ (by omega), ag1.2 _ (by simp)]; simp [hget]
  · rw [hagp.2 _ (by omega), ag2.2 _ (by simp)]; simp [hget]
  have hnm : ∀ a, a < (p.2 ++ [Obj.dict p.1]).length → ¬ D.mut a := fun a ha hm => by
    have := hD a hm; omega
  have FrH : Frame D (p.2 ++ [Obj.dict p.1]) H := hag.frame
  refine ⟨fun q hq => JFRel.frame FrH _ _ (mapM_zip_JFRel hnm _ asT t.assumptions rb2 hlen hzip q hq),
    JFRel.frame FrH _ _ (rb_JFRel hnm _ _ _ _ rb3 hfs), JFRel.frame FrH _ _ (rb_JFRel hnm _ _ _ _ rb4 hfc)⟩

end PCSCR.Js
