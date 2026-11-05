import PCS.V2.Witnesses.Registry

/-!
# Witness domain 3: ML evaluation hygiene on the **unchanged production authority**

Domain claim `SplitClaim`: the committed train, validation and test tables are strict CSV
tables containing the key column, and their key sets are **pairwise disjoint** (no
train/validation/test leakage on that key).

Decomposition: root `.split c` is split by rule `"ml.pairwise"` into the three pairwise
leaves `.disjoint`, each discharged by the *existing verified built-in* `csv_disjoint`
checker (`PCS.V2.Csv`).  No new checker is registered, so this domain runs on the production
authority `acceptArchiveWithTranscript`, and `ml_archive_sound` follows from
`pcs_generic_domain_archive_acceptance_sound_builtin` with **`NoForgery` as the only
hypothesis**.

Scope: data-split disjointness of the committed tables; nothing about model quality.
-/

set_option autoImplicit false

namespace PCS.V2.Witnesses.MLEval

open PCS PCS.V2.Json PCS.V2.Replay PCS.V2.Checkers PCS.V2.Csv PCS.V2.Chemistry PCS.V2.Package
open PCS.V2.Index PCS.V2.DomainAuthority PCS.V2.DomainAdapter PCS.V2.ClaimGraph PCS.V2.Witnesses

/-- Disjointness of two committed tables on a key. -/
def TablesDisjoint (w : List (String × ByteArray)) (a b key : String) : Prop :=
  ∃ ba bb, lookup w a = some ba ∧ lookup w b = some bb ∧
    CsvDisjoint ba.data.toList bb.data.toList key.toUTF8.data.toList

structure SplitClaim where
  train : String
  valid : String
  test : String
  key : String
  deriving DecidableEq

def mlDomain : Domain :=
  { World := List (String × ByteArray), Claim := SplitClaim,
    Holds := fun w c => TablesDisjoint w c.train c.valid c.key ∧
      TablesDisjoint w c.train c.test c.key ∧ TablesDisjoint w c.valid c.test c.key }

inductive SplitIR where
  | split (c : SplitClaim)
  | disjoint (a b key : String)
  deriving DecidableEq

def splitSem (w : List (String × ByteArray)) : SplitIR → Prop
  | .split c => TablesDisjoint w c.train c.valid c.key ∧
      TablesDisjoint w c.train c.test c.key ∧ TablesDisjoint w c.valid c.test c.key
  | .disjoint a b k => TablesDisjoint w a b k

def splitRule (r : String) (p : SplitIR) (cs : List SplitIR) : Bool :=
  r == "ml.pairwise" &&
    match p with
    | .split c => decide (cs = [.disjoint c.train c.valid c.key, .disjoint c.train c.test c.key,
        .disjoint c.valid c.test c.key])
    | _ => false

def splitNodeOf (ev : JVal) : Option SplitIR :=
  if isCsvCheck ev then (csvSpec ev).map (fun x => .disjoint x.1 x.2.1 x.2.2) else none

def mlAdapter : DomainAdapter mlDomain :=
  { IR := SplitIR,
    decode := fun v => match predStr v "kind",
        predStr v "train", predStr v "validation",
        predStr v "test", predStr v "key" with
      | some "ml.split_disjoint", some a, some b, some c, some k => some ⟨a, b, c, k⟩
      | _, _, _, _, _ => none,
    compile := fun c => some (.split c),
    world := id,
    sem := splitSem,
    leafCheck := fun ev n => decide (splitNodeOf ev = some n),
    ruleCheck := splitRule }

theorem csvHolds_of_spec {req : ReplayRequest} {a b k : String}
    (hs : csvSpec req.evidence = some (a, b, k)) (h : CsvHolds req) :
    TablesDisjoint req.artifacts a b k := by
  obtain ⟨sp, l, r, k', bl, br, hsp, _, hl, hr, hk, hbl, hbr, hd⟩ := h
  unfold csvSpec at hs
  rw [hsp] at hs
  simp only [hl, hr, hk, Option.some.injEq, Prod.mk.injEq] at hs
  obtain ⟨rfl, rfl, rfl⟩ := hs
  exact ⟨bl, br, hbl, hbr, hd⟩

/-- The adapter contract w.r.t. the **production** authority's PASS-meaning, for any
    meaning `ExtHolds` of transcript reports (none is used). -/
theorem mlAdapter_sound (ExtHolds : ReplayRequest → Prop) :
    AdapterSound mlAdapter (BuiltinHolds ExtHolds) where
  compile_sound := by
    intro w c ir hc hsem
    cases hc; exact hsem
  rule_sound := by
    intro w r p cs h hcs
    simp only [mlAdapter, splitRule, Bool.and_eq_true] at h
    obtain ⟨_, h⟩ := h
    cases p with
    | split c =>
      simp only [decide_eq_true_eq] at h
      subst h
      exact ⟨hcs (.disjoint c.train c.valid c.key) (by simp),
        hcs (.disjoint c.train c.test c.key) (by simp), hcs (.disjoint c.valid c.test c.key) (by simp)⟩
    | disjoint _ _ _ => cases h
  leaf_sound := by
    intro req n hl hv
    simp only [mlAdapter, decide_eq_true_eq] at hl
    unfold splitNodeOf at hl
    split at hl
    · rename_i hc
      obtain ⟨x, hx, rfl⟩ := Option.map_eq_some_iff.mp hl
      exact csvHolds_of_spec hx (builtinHolds_csv hc hv)
    · cases hl

/-- **ML split-hygiene assurance from a raw signed archive accepted by the unchanged
    production authority.**  Sole hypothesis: `NoForgery`. -/
theorem ml_archive_sound {t : PCS.V2.Authority.AuthorityTranscript}
    {T : PCS.V2.EndToEnd.TrustAnchor} {signed : List UInt8 → Prop}
    (hB : PCS.V2.Signature.NoForgery PCS.V2.Ed25519.verify T.pk signed)
    {raw : ByteArray} {inp : PackageInput} {r : PCS.V2.EndToEnd.AcceptedResult}
    (h : PCS.V2.CanonicalArchive.acceptArchiveWithTranscript t T raw = some (inp, r))
    {cid : String} {g : Graph String SplitIR} {c : SplitClaim}
    (hd : domainAccepts mlAdapter r cid g = some c) :
    TablesDisjoint r.table c.train c.valid c.key ∧ TablesDisjoint r.table c.train c.test c.key ∧
      TablesDisjoint r.table c.valid c.test c.key :=
  ((pcs_generic_domain_archive_acceptance_sound_builtin hB h mlAdapter
    (mlAdapter_sound _) hd).2).holds

end PCS.V2.Witnesses.MLEval
