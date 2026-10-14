import PCSConditionalRuntime.PyReceipt

/-!
# The deep copy of an accepted typed task

`input_facts`: after `value = validate(deepcopy(value))`, the heap copy of a JSON task denoting
the typed task `t` has the shape that the simulation of `check` consumes: a dictionary whose
`variables` entry is the list of declared names, whose `assumptions` entry is a list of heap
formula trees for the premises, and whose `source` / `candidate` entries are heap formula trees
for the query (`FRel`), on every heap extending the copy, for every manager placed after it.
-/

namespace PCSCR.Py

open PCSCR PCSDD PCSOmega

theorem allocKV_find : ∀ (h : Heap) (kvs : List (String × T)) (x : String) (t : T), tlook kvs x = some t →
    ∃ h', HAgree (allocT h' t).2 (allocKV h kvs).2 ∧ dictFind .py (allocKV h kvs).1 (.str x) = some (allocT h' t).1
  | _, [], _, _, ht => by simp [tlook] at ht
  | h, (k, t0) :: rest, x, t, ht => by
    simp only [tlook] at ht
    by_cases hk : k = x
    · subst hk
      simp only [if_true, Option.some.injEq] at ht
      subst ht
      refine ⟨h, ?_, ?_⟩
      · simpa [allocKV] using allocKV_agree (allocT h t0).2 rest
      · simp [allocKV, dictFind, keyEq_str]
    · simp only [hk, if_false] at ht
      obtain ⟨h', hag, hf⟩ := allocKV_find (allocT h t0).2 rest x t ht
      refine ⟨h', by simpa [allocKV] using hag, ?_⟩
      simp [allocKV, dictFind, keyEq_str, hk, hf]

theorem allocL_strs (h : Heap) : ∀ (names : List String), allocL h (names.map T.str) = (names.map V.str, h)
  | [] => rfl
  | x :: xs => by simp [allocL, allocT, allocL_strs h xs]

theorem allocL_length : ∀ (h : Heap) (ts : List T), (allocL h ts).1.length = ts.length
  | _, [] => rfl
  | h, t :: ts => by simp [allocL, allocL_length _ ts]

theorem HAgree.frameS {h h' : Heap} (hag : HAgree h h') (M : Nat → Prop) : FrameS M h h' :=
  ⟨hag.1, fun a ha _ => hag.2 a ha⟩

theorem mapM_zip_FRel {D : Addrs} {h : Heap} {names : List String} {n : Nat} {fu : Nat}
    (hnm : ∀ a, a < h.length → ¬ D.mut a) :
    ∀ (xs : List V) (ys : List T) (fs : List (BForm n)), xs.mapM (readback fu h) = some ys →
      ys.length = fs.length → (∀ p ∈ ys.zip fs, FDen names p.1 p.2) →
      ∀ p ∈ xs.zip fs, FRel D h names p.1 p.2
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
          · exact rb_FRel hnm f fu x y hx (hd (y, f) (by simp))
          · exact mapM_zip_FRel hnm xs ys' fs hr (by simpa using hl)
              (fun q hq => hd q (by simp [hq])) p hp

theorem input_facts {names : List String} {tj : T} {t : CTask names.length} (htask : TaskDen names tj t)
    (hin : Heap) :
    ∃ A vkvs NL AS as vs vc, (allocT hin tj).1 = .ref A ∧ A < (allocT hin tj).2.length ∧
      NL < (allocT hin tj).2.length ∧ AS < (allocT hin tj).2.length ∧
      dictFind .py vkvs (.str "variables") = some (.ref NL) ∧
      dictFind .py vkvs (.str "assumptions") = some (.ref AS) ∧
      dictFind .py vkvs (.str "source") = some vs ∧ dictFind .py vkvs (.str "candidate") = some vc ∧
      as.length = t.assumptions.length ∧
      ∀ H, HAgree (allocT hin tj).2 H →
        hget H A = some (.dict vkvs) ∧ hget H NL = some (.list (names.map V.str)) ∧
        hget H AS = some (.list as) ∧
        ∀ D : Addrs, (∀ a, D.mut a → (allocT hin tj).2.length ≤ a) →
          (∀ p ∈ as.zip t.assumptions, FRel D H names p.1 p.2) ∧
          FRel D H names vs t.source ∧ FRel D H names vc t.candidate := by
  obtain ⟨kvsT, sT, cT, asT, rfl, hvar, hsrc, hfs, hcand, hfc, hass, hlen, hzip⟩ := htask
  generalize hp : allocKV hin kvsT = p
  have hT : allocT hin (.obj kvsT) = (.ref p.2.length, p.2 ++ [.dict p.1]) := by simp [allocT, hp]
  rw [hT]
  simp only
  -- variables
  obtain ⟨h1, ag1, f1⟩ := allocKV_find hin kvsT _ _ hvar
  rw [hp] at ag1 f1
  simp only [allocT, allocL_strs] at ag1 f1
  -- assumptions
  obtain ⟨h2, ag2, f2⟩ := allocKV_find hin kvsT _ _ hass
  rw [hp] at ag2 f2
  simp only [allocT] at ag2 f2
  -- source / candidate
  obtain ⟨h3, ag3, f3⟩ := allocKV_find hin kvsT _ _ hsrc
  obtain ⟨h4, ag4, f4⟩ := allocKV_find hin kvsT _ _ hcand
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
  refine ⟨fun q hq => FRel.frame FrH _ _ (mapM_zip_FRel hnm _ asT t.assumptions rb2 hlen hzip q hq),
    FRel.frame FrH _ _ (rb_FRel hnm _ _ _ _ rb3 hfs), FRel.frame FrH _ _ (rb_FRel hnm _ _ _ _ rb4 hfc)⟩

end PCSCR.Py
