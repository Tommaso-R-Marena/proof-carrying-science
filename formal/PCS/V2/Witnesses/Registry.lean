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
  have key : �M��x��Z�