import PCS.V2.Csv
import PCS.V2.PKPDCheck

/-!
# Proof-carrying replay checkers

A `CertifiedChecker` is a built-in evidence kind whose replay runs **inside Lean** and
carries a machine-checked soundness theorem:

* `handles` — which replay requests it claims (by `check_spec.type`);
* `run` — the executable Lean replay;
* `Holds` — the declarative scientific proposition a `PASS` stands for;
* `sound` — `handles req → (run req).outcome = PASS → Holds req`.

`dispatch cs fallback` runs the first checker that handles a request and delegates
every other request to `fallback` (e.g. the production transcript).  `dispatch_faithful`
shows that only the fallback's faithfulness remains an assumption, and only for the
requests no certified checker handles.  New checkers are added by appending to the
list; the dispatcher and its theorem do not change.

`builtinCheckers` registers the five verified built-ins:
`reaction_balance` (`PCS.V2.Chemistry`), `unit_compatible` (`PCS.V2.Units`),
`csv_disjoint` (`PCS.V2.Csv`), `pkpd_contract` and `pkpd_reference_match`
(`PCS.V2.PKPDCheck`).
-/

namespace PCS.V2.Checkers

open PCS PCS.V2.Json PCS.V2.Common PCS.V2.Package PCS.V2.Replay PCS.V2.Flagship
open PCS.V2.Chemistry PCS.V2.Units PCS.V2.Csv PCS.V2.PKPDCheck

/-- A proof-carrying replay checker. -/
structure CertifiedChecker where
  name : String
  handles : ReplayRequest → Bool
  run : ReplayRequest → Observation
  Holds : ReplayRequest → Prop
  sound : ∀ req, handles req = true → (run req).outcome = .pass → Holds req

/-- Run the first certified checker that handles the request, else the fallback. -/
def dispatch (cs : List CertifiedChecker) (fallback : Executor) : Executor := fun req =>
  match cs.find? (·.handles req) with
  | some c => c.run req
  | none => fallback req

/-- What a `PASS` of the dispatched executor means. -/
def DispatchHolds (cs : List CertifiedChecker) (fallbackHolds : ReplayRequest → Prop)
    (req : ReplayRequest) : Prop :=
  match cs.find? (·.handles req) with
  | some c => c.Holds req
  | none => fallbackHolds req

/-- **Compositional soundness**: the dispatched executor is faithful as soon as the
    fallback is faithful (the certified checkers need no hypothesis). -/
theorem dispatch_faithful (cs : List CertifiedChecker) {fallback : Executor}
    {fallbackHolds : ReplayRequest → Prop} (hfb : ReplayFaithful fallback fallbackHolds) :
    ReplayFaithful (dispatch cs fallback) (DispatchHolds cs fallbackHolds) := by
  intro req hp
  unfold dispatch at hp
  unfold DispatchHolds
  split
  · rename_i c hc
    rw [hc] at hp
    have hh := List.find?_some hc
    exact c.sound req hh hp
  · rename_i hc
    rw [hc] at hp
    exact hfb req hp

/-- Every executor is faithful to "the executor reported `PASS`".  Used to state
    assurance theorems that make **no** assumption about uncertified evidence kinds. -/
theorem replayFaithful_reported (exec : Executor) :
    ReplayFaithful exec (fun req => (exec req).outcome = .pass) := fun _ h => h

/-! ## The verified built-ins -/

theorem chem_sound (req : ReplayRequest) (hc : isReactionCheck req.evidence = true)
    (hp : (chemExecWith unverifiedExec req).outcome = .pass) : ReactionHolds req.evidence :=
  (chemExec_faithful req hp).1 hc

def reactionChecker : CertifiedChecker :=
  { name := "reaction_balance", handles := fun req => isReactionCheck req.evidence,
    run := chemExecWith unverifiedExec, Holds := fun req => ReactionHolds req.evidence,
    sound := chem_sound }

def unitChecker : CertifiedChecker :=
  { name := "unit_compatible", handles := fun req => isUnitCheck req.evidence,
    run := unitRun, Holds := fun req => UnitHolds req.evidence, sound := unitRun_sound }

def csvChecker : CertifiedChecker :=
  { name := "csv_disjoint", handles := fun req => isCsvCheck req.evidence,
    run := csvRun, Holds := CsvHolds, sound := csvRun_sound }

def pkpdContractChecker : CertifiedChecker :=
  { name := "pkpd_contract", handles := fun req => isPkpdContract req.evidence,
    run := pkpdContractRun, Holds := PkpdContractHolds, sound := pkpdContractRun_sound }

def pkpdMatchChecker : CertifiedChecker :=
  { name := "pkpd_reference_match", handles := fun req => isPkpdMatch req.evidence,
    run := pkpdMatchRun, Holds := PkpdMatchHolds, sound := pkpdMatchRun_sound }

def builtinCheckers : List CertifiedChecker :=
  [reactionChecker, unitChecker, csvChecker, pkpdContractChecker, pkpdMatchChecker]

/-- The Lean replay executor for all verified built-ins, delegating everything else. -/
def builtinExecWith (fallback : Executor) : Executor := dispatch builtinCheckers fallback

def BuiltinHolds (fallbackHolds : ReplayRequest → Prop) : ReplayRequest → Prop :=
  DispatchHolds builtinCheckers fallbackHolds

theorem builtinExecWith_faithful {fallback : Executor} {fallbackHolds : ReplayRequest → Prop}
    (hfb : ReplayFaithful fallback fallbackHolds) :
    ReplayFaithful (builtinExecWith fallback) (BuiltinHolds fallbackHolds) :=
  dispatch_faithful builtinCheckers hfb

/-! ### Check types are mutually exclusive -/

theorem checkType_excl {ev : JVal} {a b : String} (hab : a ≠ b)
    (ha : (match checkSpec ev with
      | some sp => decide (strField sp "type" = some a) | none => false) = true) :
    (match checkSpec ev with
      | some sp => decide (strField sp "type" = some b) | none => false) = false := by
  split at ha
  · rename_i sp hsp
    simp only [decide_eq_true_eq] at ha
    simp only [decide_eq_false_iff_not, ha, Option.some.injEq]
    exact hab
  · simp_all

theorem unit_not_reaction {ev : JVal} (h : isUnitCheck ev = true) : isReactionCheck ev = false :=
  checkType_excl (by decide) h
theorem csv_not_reaction {ev : JVal} (h : isCsvCheck ev = true) : isReactionCheck ev = false :=
  checkType_excl (by decide) h
theorem csv_not_unit {ev : JVal} (h : isCsvCheck ev = true) : isUnitCheck ev = false :=
  checkType_excl (by decide) h
theorem pc_not_reaction {ev : JVal} (h : isPkpdContract ev = true) : isReactionCheck ev = false :=
  checkType_excl (by decide) h
theorem pc_not_unit {ev : JVal} (h : isPkpdContract ev = true) : isUnitCheck ev = false :=
  checkType_excl (by decide) h
theorem pc_not_csv {ev : JVal} (h : isPkpdContract ev = true) : isCsvCheck ev = false :=
  checkType_excl (by decide) h
theorem pm_not_reaction {ev : JVal} (h : isPkpdMatch ev = true) : isReactionCheck ev = false :=
  checkType_excl (by decide) h
theorem pm_not_unit {ev : JVal} (h : isPkpdMatch ev = true) : isUnitCheck ev = false :=
  checkType_excl (by decide) h
theorem pm_not_csv {ev : JVal} (h : isPkpdMatch ev = true) : isCsvCheck ev = false :=
  checkType_excl (by decide) h
theorem pm_not_pc {ev : JVal} (h : isPkpdMatch ev = true) : isPkpdContract ev = false :=
  checkType_excl (by decide) h

/-! ### What a dispatched `PASS` means for each built-in -/

theorem builtinHolds_reaction {fb : ReplayRequest → Prop} {req : ReplayRequest}
    (hc : isReactionCheck req.evidence = true) (h : BuiltinHolds fb req) :
    ReactionHolds req.evidence := by
  unfold BuiltinHolds DispatchHolds builtinCheckers at h
  simp only [List.find?, reactionChecker, hc] at h
  exact h

theorem builtinHolds_unit {fb : ReplayRequest → Prop} {req : ReplayRequest}
    (hc : isUnitCheck req.evidence = true) (h : BuiltinHolds fb req) :
    UnitHolds req.evidence := by
  unfold BuiltinHolds DispatchHolds builtinCheckers at h
  simp only [List.find?, reactionChecker, unitChecker, hc, unit_not_reaction hc] at h
  exact h

theorem builtinHolds_csv {fb : ReplayRequest → Prop} {req : ReplayRequest}
    (hc : isCsvCheck req.evidence = true) (h : BuiltinHolds fb req) : CsvHolds req := by
  unfold BuiltinHolds DispatchHolds builtinCheckers at h
  simp only [List.find?, reactionChecker, unitChecker, csvChecker, hc, csv_not_reaction hc,
    csv_not_unit hc] at h
  exact h

theorem builtinHolds_pkpdContract {fb : ReplayRequest → Prop} {req : ReplayRequest}
    (hc : isPkpdContract req.evidence = true) (h : BuiltinHolds fb req) :
    PkpdContractHolds req := by
  unfold BuiltinHolds DispatchHolds builtinCheckers at h
  simp only [List.find?, reactionChecker, unitChecker, csvChecker, pkpdContractChecker, hc,
    pc_not_reaction hc, pc_not_unit hc, pc_not_csv hc] at h
  exact h

theorem builtinHolds_pkpdMatch {fb : ReplayRequest → Prop} {req : ReplayRequest}
    (hc : isPkpdMatch req.evidence = true) (h : BuiltinHolds fb req) : PkpdMatchHolds req := by
  unfold BuiltinHolds DispatchHolds builtinCheckers at h
  simp only [List.find?, reactionChecker, unitChecker, csvChecker, pkpdContractChecker,
    pkpdMatchChecker, hc, pm_not_reaction hc, pm_not_unit hc, pm_not_csv hc, pm_not_pc hc] at h
  exact h

/-- The semantic content of a passing built-in evidence item. -/
def BuiltinSemantics (req : ReplayRequest) : Prop :=
  (isReactionCheck req.evidence = true → ReactionHolds req.evidence) ∧
  (isUnitCheck req.evidence = true → UnitHolds req.evidence) ∧
  (isCsvCheck req.evidence = true → CsvHolds req) ∧
  (isPkpdContract req.evidence = true → PkpdContractHolds req) ∧
  (isPkpdMatch req.evidence = true → PkpdMatchHolds req)

theorem builtinHolds_semantics {fb : ReplayRequest → Prop} {req : ReplayRequest}
    (h : BuiltinHolds fb req) : BuiltinSemantics req :=
  ⟨fun hc => builtinHolds_reaction hc h, fun hc => builtinHolds_unit hc h,
    fun hc => builtinHolds_csv hc h, fun hc => builtinHolds_pkpdContract hc h,
    fun hc => builtinHolds_pkpdMatch hc h⟩

/-- **No-assumption replay soundness for the verified built-ins**: whatever the fallback
    executor is, every `PASS` of `builtinExecWith fallback` on a built-in check denotes the
    built-in's scientific proposition. -/
theorem builtinExecWith_pass_semantics (fallback : Executor) (req : ReplayRequest)
    (hp : (builtinExecWith fallback req).outcome = .pass) : BuiltinSemantics req :=
  builtinHolds_semantics (builtinExecWith_faithful (replayFaithful_reported fallback) req hp)

end PCS.V2.Checkers
