import PCS.V2.DomainAuthority

/-!
# Domain-checker registration discipline

A new domain contributes proof-carrying replay checkers keyed by a `check_spec.type` tag.
`registry ks` turns them into `CertifiedChecker`s for the extended authority
(`PCS.V2.DomainAuthority.acceptArchiveWithCheckers`).  Under the registration conditions

* tags are pairwise distinct (`(ks.map (·.tag)).Nodup`), and
* no tag is a built-in tag (`builtinTypes`),

`registry_valid` shows that the extended authority's PASS-meaning on a request of tag
`k.tag` is exactly `k.Holds` — so an adapter's `leaf_sound` obligation reduces to its own
checker's soundness theorem, independently of which other domains are registered.
-/

set_option autoImplicit false

namespace PCS.V2.Witnesses

open PCS PCS.V2.Json PCS.V2.Replay PCS.V2.Checkers PCS.V2.PKPDCheck PCS.V2.DomainAuthority

/-- A domain replay checker keyed by its `check_spec.type` tag. -/
structure DomainChecker where
  tag : String
  run : ReplayRequest → Observation
  Holds : ReplayRequest → Prop
  sound : ∀ req, isCheckType tag req.evidence = true → (run req).outcome = .pass → Holds req

def DomainChecker.toCertified (k : DomainChecker) : CertifiedChecker :=
  { name := k.tag, handles := fun req => isCheckType k.tag req.evidence, run := k.run,
    Holds := k.Holds, sound := k.sound }

def registry (ks : List DomainChecker) : List CertifiedChecker := ks.map DomainChecker.toCertified

def builtinTypes : List String :=
  ["reaction_balance", "unit_compatible", "csv_disjoint", "pkpd_contract",
   "pkpd_reference_match", "pkpd_peak_concentration_threshold"]

theorem isCheckType_eq {ev : JVal} {a b : String} (ha : isCheckType a ev = true)
    (hb : isCheckType b ev = true) : a = b := by
  unfold isCheckType at ha hb
  split at ha
  · rename_i sp hsp
    rw [hsp] at hb
    simp only [decide_eq_true_eq] at ha hb
    rw [ha] at hb
    exact Option.some.inj hb
  · cases ha

theorem builtin_not_handles {req : ReplayRequest} {ty : String} (hty : ty ∉ builtinTypes)
    (h : isCheckType ty req.evidence = true) : ∀ k ∈ builtinCheckers, k.handles req = false := by
  have key : ∀ b ∈ builtinTypes, isCheckType b req.evidence = false := by
    intro b hb
    cases hc : isCheckType b req.evidence with
    | false => rfl
    | true => exact absurd (isCheckType_eq h hc ▸ hb) hty
  intro k hk
  simp only [builtinCheckers, List.mem_cons, List.not_mem_nil, or_false] at hk
  rcases hk with rfl | rfl | rfl | rfl | rfl | rfl
  · exact key "reaction_balance" (by simp [builtinTypes])
  · exact key "unit_compatible" (by simp [builtinTypes])
  · exact key "csv_disjoint" (by simp [builtinTypes])
  · exact key "pkpd_contract" (by simp [builtinTypes])
  · exact key "pkpd_reference_match" (by simp [builtinTypes])
  · exact key "pkpd_peak_concentration_threshold" (by simp [builtinTypes])

theorem eq_of_mem_of_nodup_map {α β : Type} (f : α → β) :
    ∀ {l : List α}, (l.map f).Nodup → ∀ {x y : α}, x ∈ l → y ∈ l → f x = f y → x = y
  | [], _, _, _, hx, _, _ => by cases hx
  | a :: l, hnd, x, y, hx, hy, he => by
    simp only [List.map_cons, List.nodup_cons, List.mem_map, not_exists, not_and] at hnd
    simp only [List.mem_cons] at hx hy
    rcases hx with rfl | hx <;> rcases hy with rfl | hy
    · rfl
    · exact absurd he.symm (hnd.1 y hy)
    · exact absurd he (hnd.1 x hx)
    · exact eq_of_mem_of_nodup_map f hnd.2 hx hy he

/-- Registration conditions for a list of domain checkers. -/
structure Registered (ks : List DomainChecker) : Prop where
  nodup : (ks.map (·.tag)).Nodup
  notBuiltin : ∀ k ∈ ks, k.tag ∉ builtinTypes

/-- **Registered checkers keep their meaning in the extended authority.** -/
theorem registry_valid {ks : List DomainChecker} (hreg : Registered ks)
    {ExtHolds : ReplayRequest → Prop} {req : ReplayRequest} {k : DomainChecker}
    (hk : k ∈ ks) (ht : isCheckType k.tag req.evidence = true)
    (h : AuthorityValid (registry ks) ExtHolds req) : k.Holds req := by
  refine dispatchHolds_of_unique (k := k.toCertified) ?_ ?_ ht h
  · intro k' hk' hh hH
    rcases List.mem_append.mp hk' with hb | hr
    · rw [builtin_not_handles (hreg.notBuiltin k hk) ht k' hb] at hh; cases hh
    · obtain ⟨k'', hk'', rfl⟩ := List.mem_map.mp hr
      have htag : k''.tag = k.tag := isCheckType_eq hh ht
      have := eq_of_mem_of_nodup_map (·.tag) hreg.nodup hk'' hk htag
      subst this
      exact hH
  · exact List.mem_append_right _ (List.mem_map_of_mem hk)

/-! ## Spec-parameterised checkers

Most domain checkers parse parameters from the evidence `check_spec` and run a decidable
test on the committed artifacts.  `specChecker` builds such a checker from a test and a
declarative proposition together with the test's soundness theorem; its PASS-meaning is
"the spec parses to `x` and `Sem x` holds of the committed artifacts". -/

open PCS.V2.Package PCS.V2.Index PCS.V2.Chemistry

/-- A string parameter of the evidence `check_spec`. -/
def specStr (ev : JVal) (k : String) : Option String :=
  match checkSpec ev with
  | some sp => match field sp k with
    | some (.str s) => some s
    | _ => none
  | none => none

/-- A natural-number parameter of the evidence `check_spec`. -/
def specNat (ev : JVal) (k : String) : Option Nat :=
  match checkSpec ev with
  | some sp => match field sp k with
    | some (.num i) => if 0 ≤ i then some i.toNat else none
    | _ => none
  | none => none

/-- A string field of a certificate claim predicate object. -/
def predStr (v : JVal) (k : String) : Option String := specStr (.obj [("check_spec", v)]) k

/-- A natural-number field of a certificate claim predicate object. -/
def predNat (v : JVal) (k : String) : Option Nat := specNat (.obj [("check_spec", v)]) k

/-- The bytes of a committed artifact. -/
def artBytes (w : List (String × ByteArray)) (a : String) : Option (List UInt8) :=
  (lookup w a).map (·.data.toList)

def specChecker (tag : String) {σ : Type} (parse : JVal → Option σ)
    (test : σ → List (String × ByteArray) → Bool) (Sem : σ → List (String × ByteArray) → Prop)
    (hsound : ∀ x w, test x w = true → Sem x w) : DomainChecker :=
  { tag,
    run := fun req => match parse req.evidence with
      | some x => ⟨.computationalTest, if test x req.artifacts then .pass else .fail⟩
      | none => ⟨.computationalTest, .fail⟩,
    Holds := fun req => ∃ x, parse req.evidence = some x ∧ Sem x req.artifacts,
    sound := by
      intro req _ hp
      split at hp
      · rename_i x hx
        refine ⟨x, hx, hsound x _ ?_⟩
        cases ht : test x req.artifacts
        · rw [ht] at hp; cases hp
        · rfl
      · cases hp }

end PCS.V2.Witnesses
