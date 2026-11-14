import ClaimCheck
import ClaimCheckAssurance.SourceBinding

/-!
# Authority non-escalation for the ClaimCheck verdict pipeline

An executable model of how ClaimCheck v1 and v1.1 turn kernel results and mechanical findings into
the verdict a user sees, and theorems that bound what that verdict can claim.

The model follows the code line by line (`research/claimcheck_v1/pipeline.py::_complete`,
`research/claimcheck_v1_1/policy.py::math_status`, `assess_document`, `_decide`):

* `Variant.status`, `mathStatus`   what the kernel results of the convention variants amount to;
* `outward`                         the decision table of `_decide`;
* `Rec.strongMatch`, `Doc.cor`      which records may support another one;
* `Doc.verdict`                     the verdict of record `i` of a document.

Two kinds of input are kept apart.

* **Kernel evidence** (`Variant.accepted`): the outcome `o` of a theorem `run src claim = o` that
  the Lean kernel accepted.  The only assumption made about the world is `KernelSound`: such an
  equation is true.  It is a hypothesis of the theorems that need it, never an axiom.
* **Everything else** (`Findings`, the sibling relations, the claims themselves): produced by
  untrusted code and by untrusted proposers.  Every theorem holds for arbitrary values of them.

What is proved (names of the main theorems):

1. `confirmation_sound`, `discrepancy_sound`  a decided verdict implies the corresponding statement
   about the real checker function `run` on the source, for every convention variant;
2. `verdict_unknown_of_unaccepted`           one variant without kernel acceptance forces UNKNOWN;
3. `conditional_never_decided`, `conditional_sound`  a result that holds under one convention and
   fails under the other is never a decided verdict;
4. `verdict_mono`                            withdrawing kernel results, findings or sibling links
   never raises any verdict of the document and never turns one decided verdict into the other;
5. `discrepancy_corroborated`                a discrepancy needs another record that is itself a
   kernel-proved CONFIRMATION;
6. `no_conflict`                             under a stated condition on the enumeration of
   readings, one printed number cannot be both confirmed and flagged;
7. `evidence_does_not_transfer`              kernel evidence for one file is not evidence for another;
8. `faithfulness_not_decidable_from_observables`  why no verdict asserts that the reading is the
   authors' meaning.

Negative controls at the end show that each hypothesis is needed and that the monotonicity theorem
fails for a plausible but wrong variant of the policy.

**Scope.** These are theorems about this Lean model.  That the Python code computes the same
function is tested (`conformance/`), not proved.  How the findings are computed from text and data
is outside the model.
-/

namespace PCS.ClaimCheck.Assurance

open PCS.ClaimCheck

/-! ## 1. Kernel evidence -/

def _root_.PCS.ClaimCheck.Outcome.isMatch : Outcome → Bool
  | .checked .consistent _ _ _ => true
  | _ => false

def _root_.PCS.ClaimCheck.Outcome.isMismatch : Outcome → Bool
  | .checked .inconsistent _ _ _ => true
  | _ => false

def _root_.PCS.ClaimCheck.Outcome.isUndefined : Outcome → Bool
  | .undefined _ => true
  | _ => false

/-- One convention variant of a reading (for example the standard deviation with `n − 1`): the
typed claim, and the outcome `o` of the theorem `run src claim = o` if the kernel accepted it. -/
structure Variant where
  claim : Claim
  accepted : Option Outcome

inductive VStatus where
  | proved | refuted | unknown
  deriving DecidableEq, Repr

/-- `pipeline._complete`: UNKNOWN unless the kernel accepted a defined outcome. -/
def Variant.status (v : Variant) : VStatus :=
  match v.accepted with
  | some o => if o.isMatch then .proved else if o.isMismatch then .refuted else .unknown
  | none => .unknown

inductive Math where
  | matchProved | mismatchProved | conditional | undefinedProved | notEstablished
  deriving DecidableEq, Repr

def firstUndefined : List Variant → Bool
  | v :: _ => match v.accepted with
    | some o => o.isUndefined
    | none => false
  | [] => false

def allProved (vs : List Variant) : Bool := vs.all (fun v => decide (v.status = .proved))
def allRefuted (vs : List Variant) : Bool := vs.all (fun v => decide (v.status = .refuted))
def anyUnknown (vs : List Variant) : Bool := vs.any (fun v => decide (v.status = .unknown))
/-- every variant was accepted by the kernel and the first one was accepted as undefined -/
def undefinedConfirmed (vs : List Variant) : Bool :=
  vs.all (fun v => v.accepted.isSome) && firstUndefined vs

/-- `pipeline._complete` followed by `policy.math_status`. -/
def mathStatus (vs : List Variant) : Math :=
  if vs.isEmpty then .notEstablished
  else if allProved vs then .matchProved
  else if allRefuted vs then .mismatchProved
  else if anyUnknown vs then (if undefinedConfirmed vs then .undefinedProved else .notEstablished)
  else .conditional

theorem allProved_iff (vs : List Variant) : allProved vs = true ↔ ∀ v ∈ vs, v.status = .proved := by
  simp [allProved]

theorem allRefuted_iff (vs : List Variant) : allRefuted vs = true ↔ ∀ v ∈ vs, v.status = .refuted := by
  simp [allRefuted]

theorem anyUnknown_iff (vs : List Variant) : anyUnknown vs = true ↔ ∃ v ∈ vs, v.status = .unknown := by
  simp [anyUnknown]

/-- **The assumption about the world.**  Whenever the kernel accepted `run src claim = o`, that
equation is true.  It stands for: the Lean kernel is sound, the proof file's text denotes that
equation, and the embedded numeral is the file (see `SourceBinding`). -/
def KernelSound (src : Source) (vs : List Variant) : Prop :=
  ∀ v ∈ vs, ∀ o, v.accepted = some o → run src v.claim = o

theorem status_proved_iff (v : Variant) :
    v.status = .proved ↔ ∃ o, v.accepted = some o ∧ o.isMatch = true := by
  unfold Variant.status
  cases h : v.accepted with
  | none => simp
  | some o => by_cases h1 : o.isMatch = true <;> by_cases h2 : o.isMismatch = true <;> simp [h1, h2]

theorem isMatch_not_isMismatch (o : Outcome) : o.isMatch = true → o.isMismatch = false := by
  cases o with
  | checked v _ _ _ => cases v <;> simp [Outcome.isMatch, Outcome.isMismatch]
  | undefined _ => simp [Outcome.isMatch]

theorem status_refuted_iff (v : Variant) :
    v.status = .refuted ↔ ∃ o, v.accepted = some o ∧ o.isMismatch = true := by
  unfold Variant.status
  cases h : v.accepted with
  | none => simp
  | some o =>
    by_cases h1 : o.isMatch = true
    · have := isMatch_not_isMismatch o h1; simp [h1, this]
    · by_cases h2 : o.isMismatch = true <;> simp [h1, h2]

theorem status_unknown_of_none (v : Variant) (h : v.accepted = none) : v.status = .unknown := by
  simp [Variant.status, h]

theorem mathStatus_matchProved {vs : List Variant} (h : mathStatus vs = .matchProved) :
    vs ≠ [] ∧ ∀ v ∈ vs, v.status = .proved := by
  cases h0 : vs.isEmpty <;> cases h1 : allProved vs <;> cases h2 : allRefuted vs <;>
    cases h3 : anyUnknown vs <;> cases h4 : undefinedConfirmed vs <;>
    simp [mathStatus, h0, h1, h2, h3, h4] at h
  all_goals exact ⟨by intro e; simp [e] at h0, (allProved_iff vs).mp h1⟩

theorem mathStatus_mismatchProved {vs : List Variant} (h : mathStatus vs = .mismatchProved) :
    vs ≠ [] ∧ ∀ v ∈ vs, v.status = .refuted := by
  cases h0 : vs.isEmpty <;> cases h1 : allProved vs <;> cases h2 : allRefuted vs <;>
    cases h3 : anyUnknown vs <;> cases h4 : undefinedConfirmed vs <;>
    simp [mathStatus, h0, h1, h2, h3, h4] at h
  all_goals exact ⟨by intro e; simp [e] at h0, (allRefuted_iff vs).mp h2⟩

/-- One variant without kernel acceptance: nothing is established. -/
theorem mathStatus_of_unaccepted {vs : List Variant} (h : ∃ v ∈ vs, v.accepted = none) :
    mathStatus vs = .notEstablished := by
  obtain ⟨v, hv, hnone⟩ := h
  have hu : v.status = .unknown := status_unknown_of_none v hnone
  have h0 : vs.isEmpty = false := by
    cases vs with
    | nil => cases hv
    | cons _ _ => rfl
  have h1 : allProved vs = false := by
    cases h : allProved vs with
    | false => rfl
    | true => have := (allProved_iff vs).mp h v hv; rw [hu] at this; cases this
  have h2 : allRefuted vs = false := by
    cases h : allRefuted vs with
    | false => rfl
    | true => have := (allRefuted_iff vs).mp h v hv; rw [hu] at this; cases this
  have h3 : anyUnknown vs = true := (anyUnknown_iff vs).mpr ⟨v, hv, hu⟩
  have h4 : undefinedConfirmed vs = false := by
    cases h : undefinedConfirmed vs with
    | false => rfl
    | true =>
      simp only [undefinedConfirmed, Bool.and_eq_true, List.all_eq_true] at h
      have := h.1 v hv
      simp [hnone] at this
  simp [mathStatus, h0, h1, h2, h3, h4]

theorem mathStatus_conditional {vs : List Variant} (h : mathStatus vs = .conditional) :
    (∃ v ∈ vs, v.status = .proved) ∧ (∃ v ∈ vs, v.status = .refuted) := by
  cases h0 : vs.isEmpty <;> cases h1 : allProved vs <;> cases h2 : allRefuted vs <;>
    cases h3 : anyUnknown vs <;> cases h4 : undefinedConfirmed vs <;>
    simp [mathStatus, h0, h1, h2, h3, h4] at h
  all_goals
    have hnu : ∀ v ∈ vs, v.status ≠ .unknown := by
      intro v hv hu
      have := (anyUnknown_iff vs).mpr ⟨v, hv, hu⟩
      rw [h3] at this; cases this
    have e1 : ∃ v ∈ vs, v.status ≠ .proved := by
      simpa [allProved] using h1
    have e2 : ∃ v ∈ vs, v.status ≠ .refuted := by
      simpa [allRefuted] using h2
    obtain ⟨a, ha, hap⟩ := e1
    obtain ⟨b, hb, hbr⟩ := e2
    have ha' : a.status = .refuted := by
      have := hnu a ha
      cases hs : a.status <;> simp_all
    have hb' : b.status = .proved := by
      have := hnu b hb
      cases hs : b.status <;> simp_all
    exact ⟨⟨b, hb, hb'⟩, ⟨a, ha, ha'⟩⟩

/-- A proved match is a true statement about the source, for every convention variant. -/
theorem matchProved_sound {src : Source} {vs : List Variant} (hk : KernelSound src vs)
    (h : mathStatus vs = .matchProved) :
    vs ≠ [] ∧ ∀ v ∈ vs, (run src v.claim).isMatch = true := by
  obtain ⟨hne, hall⟩ := mathStatus_matchProved h
  refine ⟨hne, fun v hv => ?_⟩
  obtain ⟨o, ho, hm⟩ := (status_proved_iff v).mp (hall v hv)
  rw [hk v hv o ho]; exact hm

theorem mismatchProved_sound {src : Source} {vs : List Variant} (hk : KernelSound src vs)
    (h : mathStatus vs = .mismatchProved) :
    vs ≠ [] ∧ ∀ v ∈ vs, (run src v.claim).isMismatch = true := by
  obtain ⟨hne, hall⟩ := mathStatus_mismatchProved h
  refine ⟨hne, fun v hv => ?_⟩
  obtain ⟨o, ho, hm⟩ := (status_refuted_iff v).mp (hall v hv)
  rw [hk v hv o ho]; exact hm

/-- A conditional result is genuinely conditional: the number matches under one convention and
does not match under another. -/
theorem conditional_sound {src : Source} {vs : List Variant} (hk : KernelSound src vs)
    (h : mathStatus vs = .conditional) :
    (∃ v ∈ vs, (run src v.claim).isMatch = true) ∧ (∃ v ∈ vs, (run src v.claim).isMismatch = true) := by
  obtain ⟨⟨a, ha, hap⟩, ⟨b, hb, hbr⟩⟩ := mathStatus_conditional h
  obtain ⟨o, ho, hm⟩ := (status_proved_iff a).mp hap
  obtain ⟨o', ho', hm'⟩ := (status_refuted_iff b).mp hbr
  exact ⟨⟨a, ha, by rw [hk a ha o ho]; exact hm⟩, ⟨b, hb, by rw [hk b hb o' ho']; exact hm'⟩⟩

/-! ## 2. The policy layer -/

/-- The mechanical findings about one reading, as the policy layer computes them from the source
text, the manifest and the data.  **Untrusted**: the theorems hold for arbitrary values. -/
structure Findings where
  /-- a sentence window and a number token were located for this receipt -/
  hasWindow : Bool
  /-- the quoted sentence is in the source and the number is printed in it -/
  quoteOk : Bool
  /-- every v1 lexical gate passed (then v1 reports PROVED or REFUTED) -/
  grounded : Bool
  /-- the rows the reading uses could be analysed -/
  identOk : Bool
  /-- plain number, eligible reading, wording attached to the number, unit fits -/
  basicOk : Bool
  /-- match: the readings bound to the number were enumerated completely -/
  boundedBound : Bool
  /-- match: no other statistic or column bound to the number reproduces it -/
  noCompeting : Bool
  /-- match: the decoy coincidence rate is at most the limit -/
  lowRate : Bool
  /-- match: within the readings pinned by a confirmed sibling: complete, no competitor, low rate -/
  pinnedOk : Bool
  /-- mismatch: the statistic is not a count -/
  notCount : Bool
  /-- mismatch: all eligible readings of the sentence were enumerated -/
  boundedAll : Bool
  /-- mismatch: no eligible reading of the sentence reproduces the number -/
  noEligible : Bool
  /-- mismatch: the difference exceeds one unit in the last printed digit -/
  beyondRounding : Bool
  /-- mismatch: a dispersion statistic is named explicitly (true for other statistics) -/
  dispersionNamed : Bool
  /-- mismatch: no wording for statistics the tool does not compute -/
  inGrammar : Bool
  /-- mismatch: a printed sample size equals the rows used -/
  sampleSizeOk : Bool
  deriving DecidableEq, Repr

def Findings.attached (f : Findings) : Bool := f.hasWindow && f.quoteOk

def Findings.matchGates (f : Findings) : Bool :=
  f.basicOk && f.boundedBound && f.noCompeting && f.lowRate

def Findings.mismatchGates (f : Findings) : Bool :=
  f.notCount && f.basicOk && f.boundedAll && f.noEligible && f.beyondRounding &&
    f.dispersionNamed && f.inGrammar && f.sampleSizeOk

inductive Verdict where
  | unknown | review | confirmation | discrepancy
  deriving DecidableEq, Repr

/-- The decision table of `_decide`, on five aggregated facts:
`att` attached, `gi` grounded and analysable, `strong` all match gates, `weak` supported by a
confirmed sibling, `disc` all mismatch gates and a confirmed sibling. -/
def core (m : Math) (att gi strong weak disc : Bool) : Verdict :=
  match m with
  | .notEstablished => .unknown
  | .undefinedProved => .unknown
  | .conditional => if att then .review else .unknown
  | .matchProved =>
      if !att then .unknown
      else if !gi then .review
      else if strong || weak then .confirmation
      else .review
  | .mismatchProved =>
      if !att then .unknown
      else if !gi then .review
      else if disc then .discrepancy
      else .review

/-- `policy._decide`.  `corM`, `corD`: a strongly confirmed sibling exists (for a match: same
sentence and rows; for a mismatch: also the same column). -/
def outward (m : Math) (f : Findings) (corM corD : Bool) : Verdict :=
  core m f.attached (f.grounded && f.identOk) f.matchGates (corM && f.basicOk && f.pinnedOk)
    (f.mismatchGates && corD)

/-- One v1 receipt as the policy sees it.  `note` stands for everything else attached to a
receipt (the proposer's name, a model's stated confidence, a person's statement that the reading
is right): it is carried along and never read. -/
structure Rec where
  variants : List Variant
  f : Findings
  note : String := ""

/-- `assess_document`: the records that may support another record. -/
def Rec.strongMatch (r : Rec) : Bool :=
  r.f.hasWindow && decide (mathStatus r.variants = .matchProved) && r.f.grounded && r.f.identOk &&
    r.f.matchGates

/-- The receipts about one source and one data file, and the two sibling relations
(`sibM i j`: `j` is another number of the same sentence computed from the same rows;
`sibD i j`: also from the same column).  The relations come from untrusted code. -/
structure Doc where
  n : Nat
  get : Nat → Rec
  sibM : Nat → Nat → Bool
  sibD : Nat → Nat → Bool

def Doc.cor (d : Doc) (rel : Nat → Nat → Bool) (i : Nat) : Bool :=
  decide (∃ j, j < d.n ∧ (rel i j = true ∧ (d.get j).strongMatch = true))

/-- The outward verdict of record `i`. -/
def Doc.verdict (d : Doc) (i : Nat) : Verdict :=
  outward (mathStatus (d.get i).variants) (d.get i).f (d.cor d.sibM i) (d.cor d.sibD i)

/-! ## 3. What a verdict implies -/

theorem core_confirmation {m : Math} {att gi strong weak disc : Bool}
    (h : core m att gi strong weak disc = .confirmation) :
    m = .matchProved ∧ att = true ∧ gi = true ∧ (strong = true ∨ weak = true) := by
  cases m <;> cases att <;> cases gi <;> cases strong <;> cases weak <;> cases disc <;>
    simp_all [core]

theorem core_discrepancy {m : Math} {att gi strong weak disc : Bool}
    (h : core m att gi strong weak disc = .discrepancy) :
    m = .mismatchProved ∧ att = true ∧ gi = true ∧ disc = true := by
  cases m <;> cases att <;> cases gi <;> cases strong <;> cases weak <;> cases disc <;>
    simp_all [core]

theorem core_review {m : Math} {att gi strong weak disc : Bool}
    (h : core m att gi strong weak disc = .review) :
    (m = .matchProved ∨ m = .mismatchProved ∨ m = .conditional) ∧ att = true := by
  cases m <;> cases att <;> cases gi <;> cases strong <;> cases weak <;> cases disc <;>
    simp_all [core]

/-- **Unknown stays unknown.**  If no mathematical result was established, or the statistic is
undefined, the verdict is UNKNOWN whatever the findings, the siblings and the notes say. -/
theorem outward_unknown (f : Findings) (corM corD : Bool) :
    outward .notEstablished f corM corD = .unknown ∧ outward .undefinedProved f corM corD = .unknown := by
  simp [outward, core]

/-- One variant the kernel did not accept forces UNKNOWN for the record. -/
theorem verdict_unknown_of_unaccepted (d : Doc) (i : Nat)
    (h : ∃ v ∈ (d.get i).variants, v.accepted = none) : d.verdict i = .unknown := by
  simp [Doc.verdict, mathStatus_of_unaccepted h, outward, core]

/-- **A conditional result is never decided.** -/
theorem conditional_never_decided (f : Findings) (corM corD : Bool) :
    outward .conditional f corM corD ≠ .confirmation ∧ outward .conditional f corM corD ≠ .discrepancy := by
  simp only [outward, core]
  cases f.attached <;> simp

theorem strongMatch_iff (r : Rec) :
    r.strongMatch = true ↔ r.f.hasWindow = true ∧ mathStatus r.variants = .matchProved ∧
      r.f.grounded = true ∧ r.f.identOk = true ∧ r.f.matchGates = true := by
  simp [Rec.strongMatch, and_assoc]

theorem cor_iff (d : Doc) (rel : Nat → Nat → Bool) (i : Nat) :
    d.cor rel i = true ↔ ∃ j, j < d.n ∧ rel i j = true ∧ (d.get j).strongMatch = true := by
  simp [Doc.cor]

/-- Input condition: a receipt whose lexical gates all passed has its quote and number in the
source.  (In the code, both are among those gates.) -/
def Doc.WellFormed (d : Doc) : Prop :=
  ∀ j, j < d.n → (d.get j).f.grounded = true → (d.get j).f.quoteOk = true

/-- A record that may support others is itself a CONFIRMATION. -/
theorem verdict_of_strongMatch (d : Doc) (hwf : d.WellFormed) (j : Nat) (hj : j < d.n)
    (h : (d.get j).strongMatch = true) : d.verdict j = .confirmation := by
  obtain ⟨hw, hm, hg, hi, hgates⟩ := (strongMatch_iff _).mp h
  have hq := hwf j hj hg
  simp [Doc.verdict, outward, core, hm, Findings.attached, hw, hq, hg, hi, hgates]

/-- **Mathematical authority requires kernel evidence (match).**  If record `i` is a CONFIRMATION
then, for every convention variant, the real checker function says the printed number matches the
source.  No finding, sibling relation, note or choice of claim can produce a CONFIRMATION otherwise. -/
theorem confirmation_sound (d : Doc) (src : Source) (i : Nat)
    (hk : KernelSound src (d.get i).variants) (h : d.verdict i = .confirmation) :
    (d.get i).variants ≠ [] ∧ ∀ v ∈ (d.get i).variants, (run src v.claim).isMatch = true := by
  have hm := (core_confirmation h).1
  exact matchProved_sound hk hm

/-- **Corroboration cannot be forged.**  A discrepancy flag needs another record of the same
document that the sibling relation links to it and that is itself a kernel-proved CONFIRMATION. -/
theorem discrepancy_corroborated (d : Doc) (hwf : d.WellFormed) (i : Nat)
    (h : d.verdict i = .discrepancy) :
    mathStatus (d.get i).variants = .mismatchProved ∧ (d.get i).f.mismatchGates = true ∧
      ∃ j, j < d.n ∧ j ≠ i ∧ d.sibD i j = true ∧ d.verdict j = .confirmation ∧
        mathStatus (d.get j).variants = .matchProved := by
  obtain ⟨hm, _, _, hdisc⟩ := core_discrepancy h
  have hd : (d.get i).f.mismatchGates = true ∧ d.cor d.sibD i = true := by
    simpa using hdisc
  obtain ⟨j, hj, hrel, hstrong⟩ := (cor_iff d d.sibD i).mp hd.2
  have hjm := ((strongMatch_iff _).mp hstrong).2.1
  refine ⟨hm, hd.1, j, hj, ?_, hrel, verdict_of_strongMatch d hwf j hj hstrong, hjm⟩
  intro e
  rw [e] at hjm
  rw [hjm] at hm
  cases hm

/-- **Mathematical authority requires kernel evidence (mismatch).**  A discrepancy flag implies that
the printed number does not match the source under any convention variant of this reading, and that
a different record matches the source under all of its variants. -/
theorem discrepancy_sound (d : Doc) (src : Source) (hwf : d.WellFormed) (i : Nat)
    (hk : ∀ j, j < d.n → KernelSound src (d.get j).variants) (hi : i < d.n)
    (h : d.verdict i = .discrepancy) :
    (∀ v ∈ (d.get i).variants, (run src v.claim).isMismatch = true) ∧
      ∃ j, j < d.n ∧ j ≠ i ∧ d.sibD i j = true ∧
        ∀ v ∈ (d.get j).variants, (run src v.claim).isMatch = true := by
  obtain ⟨hm, _, j, hj, hne, hrel, _, hjm⟩ := discrepancy_corroborated d hwf i h
  exact ⟨(mismatchProved_sound (hk i hi) hm).2, j, hj, hne, hrel, (matchProved_sound (hk j hj) hjm).2⟩

/-- The verdict does not read the notes attached to a receipt. -/
theorem verdict_ignores_notes (d : Doc) (notes : Nat → String) (i : Nat) :
    ({ d with get := fun j => { d.get j with note := notes j } } : Doc).verdict i = d.verdict i := by
  simp [Doc.verdict, Doc.cor, Rec.strongMatch]

/-! ## 4. Withholding never strengthens -/

/-- The order of claimed authority.  UNKNOWN claims nothing; REQUIRE_HUMAN_REVIEW keeps a
mathematical result; the two decided verdicts are above it and incomparable. -/
def Verdict.le : Verdict → Verdict → Bool
  | .unknown, _ => true
  | .review, .unknown => false
  | .review, _ => true
  | .confirmation, .confirmation => true
  | .discrepancy, .discrepancy => true
  | _, _ => false

/-- `v'` is `v` with its kernel acceptance possibly withdrawn. -/
def Variant.Withdrawn (v' v : Variant) : Prop :=
  v'.claim = v.claim ∧ (v'.accepted = none ∨ v'.accepted = v.accepted)

/-- Every finding of `f'` that passed also passed in `f`. -/
def Findings.Le (f' f : Findings) : Prop :=
  (f'.hasWindow = true → f.hasWindow = true) ∧ (f'.quoteOk = true → f.quoteOk = true) ∧
  (f'.grounded = true → f.grounded = true) ∧ (f'.identOk = true → f.identOk = true) ∧
  (f'.basicOk = true → f.basicOk = true) ∧ (f'.boundedBound = true → f.boundedBound = true) ∧
  (f'.noCompeting = true → f.noCompeting = true) ∧ (f'.lowRate = true → f.lowRate = true) ∧
  (f'.pinnedOk = true → f.pinnedOk = true) ∧ (f'.notCount = true → f.notCount = true) ∧
  (f'.boundedAll = true → f.boundedAll = true) ∧ (f'.noEligible = true → f.noEligible = true) ∧
  (f'.beyondRounding = true → f.beyondRounding = true) ∧
  (f'.dispersionNamed = true → f.dispersionNamed = true) ∧
  (f'.inGrammar = true → f.inGrammar = true) ∧ (f'.sampleSizeOk = true → f.sampleSizeOk = true)

/-- The same variants in the same order, each with its acceptance possibly withdrawn. -/
inductive WithdrawnList : List Variant → List Variant → Prop
  | nil : WithdrawnList [] []
  | cons {a b : Variant} {l₁ l₂ : List Variant} :
      Variant.Withdrawn a b → WithdrawnList l₁ l₂ → WithdrawnList (a :: l₁) (b :: l₂)

def Rec.Le (r' r : Rec) : Prop :=
  WithdrawnList r'.variants r.variants ∧ Findings.Le r'.f r.f

/-- `d'` is `d` with evidence withdrawn: kernel acceptances removed, findings turned from pass to
fail, sibling links removed. -/
def Doc.Le (d' d : Doc) : Prop :=
  d'.n = d.n ∧ (∀ i, i < d.n → Rec.Le (d'.get i) (d.get i)) ∧
    (∀ i j, d'.sibM i j = true → d.sibM i j = true) ∧ (∀ i j, d'.sibD i j = true → d.sibD i j = true)

theorem withdrawn_eq_or_unaccepted {vs' vs : List Variant}
    (h : WithdrawnList vs' vs) : vs' = vs ∨ ∃ v ∈ vs', v.accepted = none := by
  induction h with
  | nil => exact Or.inl rfl
  | @cons a b l₁ l₂ hab _ ih =>
    rcases hab with ⟨hc, hacc | hacc⟩
    · exact Or.inr ⟨a, by simp, hacc⟩
    · rcases ih with ih | ⟨v, hv, hn⟩
      · left
        have : a = b := by cases a; cases b; simp_all
        rw [this, ih]
      · exact Or.inr ⟨v, by simp [hv], hn⟩

/-- Withdrawing kernel acceptances keeps the mathematical status or drops it to "not established". -/
theorem mathStatus_withdrawn {vs' vs : List Variant} (h : WithdrawnList vs' vs) :
    mathStatus vs' = mathStatus vs ∨ mathStatus vs' = .notEstablished := by
  rcases withdrawn_eq_or_unaccepted h with e | hu
  · exact Or.inl (by rw [e])
  · exact Or.inr (mathStatus_of_unaccepted hu)

theorem Verdict.unknown_le (v : Verdict) : Verdict.le .unknown v = true := by cases v <;> rfl

/-- The decision table is monotone in each of its five facts. -/
theorem core_mono (m : Math) :
    ∀ a g s w c a' g' s' w' c' : Bool,
      (a' = true → a = true) → (g' = true → g = true) → (s' = true → s = true) →
      (w' = true → w = true) → (c' = true → c = true) →
      Verdict.le (core m a' g' s' w' c') (core m a g s w c) = true := by
  cases m <;> decide +kernel

theorem and_mono {a b a' b' : Bool} (h1 : a' = true → a = true) (h2 : b' = true → b = true) :
    (a' && b') = true → (a && b) = true := by
  cases a' <;> cases b' <;> simp_all

theorem Findings.Le.attached {f' f : Findings} (h : Findings.Le f' f) :
    f'.attached = true → f.attached = true :=
  and_mono h.1 h.2.1

theorem Findings.Le.matchGates {f' f : Findings} (h : Findings.Le f' f) :
    f'.matchGates = true → f.matchGates = true := by
  obtain ⟨_, _, _, _, h5, h6, h7, h8, _⟩ := h
  exact and_mono (and_mono (and_mono h5 h6) h7) h8

theorem Findings.Le.mismatchGates {f' f : Findings} (h : Findings.Le f' f) :
    f'.mismatchGates = true → f.mismatchGates = true := by
  obtain ⟨_, _, _, _, h5, _, _, _, _, h10, h11, h12, h13, h14, h15, h16⟩ := h
  exact and_mono (and_mono (and_mono (and_mono (and_mono (and_mono (and_mono h10 h5) h11) h12) h13) h14) h15) h16

theorem outward_mono {m' m : Math} {f' f : Findings} {cM' cM cD' cD : Bool}
    (hm : m' = m ∨ m' = .notEstablished) (hf : Findings.Le f' f)
    (hM : cM' = true → cM = true) (hD : cD' = true → cD = true) :
    Verdict.le (outward m' f' cM' cD') (outward m f cM cD) = true := by
  rcases hm with hm | hm
  · subst hm
    exact core_mono m' _ _ _ _ _ _ _ _ _ _ hf.attached (and_mono hf.2.2.1 hf.2.2.2.1) hf.matchGates
      (and_mono (and_mono hM hf.2.2.2.2.1) hf.2.2.2.2.2.2.2.2.1) (and_mono hf.mismatchGates hD)
  · subst hm
    simp [outward, core, Verdict.unknown_le]

theorem strongMatch_mono {r' r : Rec} (h : Rec.Le r' r) :
    r'.strongMatch = true → r.strongMatch = true := by
  intro hs
  obtain ⟨hw, hm, hg, hi, hgates⟩ := (strongMatch_iff r').mp hs
  have hm' : mathStatus r.variants = .matchProved := by
    rcases mathStatus_withdrawn h.1 with e | e
    · rw [← e]; exact hm
    · rw [e] at hm; cases hm
  exact (strongMatch_iff r).mpr ⟨h.2.1 hw, hm', h.2.2.2.1 hg, h.2.2.2.2.1 hi, h.2.matchGates hgates⟩

theorem cor_mono {d' d : Doc} (h : Doc.Le d' d) {rel' rel : Nat → Nat → Bool}
    (hrel : ∀ i j, rel' i j = true → rel i j = true) (i : Nat) :
    d'.cor rel' i = true → d.cor rel i = true := by
  intro hc
  obtain ⟨j, hj, hr, hs⟩ := (cor_iff d' rel' i).mp hc
  have hj' : j < d.n := h.1 ▸ hj
  exact (cor_iff d rel i).mpr ⟨j, hj', hrel i j hr, strongMatch_mono (h.2.1 j hj') hs⟩

/-- **Withholding never strengthens.**  If `d'` is `d` with evidence withdrawn anywhere in the
document, then no verdict of `d'` claims more than the corresponding verdict of `d`; in particular
no CONFIRMATION appears, no flag appears, and neither turns into the other. -/
theorem verdict_mono {d' d : Doc} (h : Doc.Le d' d) (i : Nat) (hi : i < d.n) :
    Verdict.le (d'.verdict i) (d.verdict i) = true :=
  outward_mono (mathStatus_withdrawn (h.2.1 i hi).1) (h.2.1 i hi).2
    (cor_mono h h.2.2.1 i) (cor_mono h h.2.2.2 i)

theorem Verdict.le_confirmation {v : Verdict} (h : Verdict.le .confirmation v = true) :
    v = .confirmation := by cases v <;> simp_all [Verdict.le]

theorem Verdict.le_discrepancy {v : Verdict} (h : Verdict.le .discrepancy v = true) :
    v = .discrepancy := by cases v <;> simp_all [Verdict.le]

/-- Corollary: a decided verdict of the weakened document was already that verdict before. -/
theorem decided_of_withdrawn {d' d : Doc} (h : Doc.Le d' d) (i : Nat) (hi : i < d.n) :
    (d'.verdict i = .confirmation → d.verdict i = .confirmation) ∧
      (d'.verdict i = .discrepancy → d.verdict i = .discrepancy) := by
  have hm := verdict_mono h i hi
  constructor
  · intro e; rw [e] at hm; exact Verdict.le_confirmation hm
  · intro e; rw [e] at hm; exact Verdict.le_discrepancy hm

/-! ## 5. Conflicting readings -/

/-- A condition on the untrusted enumeration of readings: if a kernel-proved, lexically grounded,
eligible reading of a printed number exists, then every complete enumeration for a receipt about
the same number has found a reading that reproduces it.  `tok i` names the number receipt `i` is about. -/
def Doc.EnumerationConsistent (d : Doc) (tok : Nat → Nat) : Prop :=
  ∀ i j, i < d.n → j < d.n → tok i = tok j →
    mathStatus (d.get i).variants = .matchProved → (d.get i).f.grounded = true →
    (d.get i).f.basicOk = true → (d.get j).f.boundedAll = true → (d.get j).f.noEligible = false

/-- **No contradictory authority about one number.**  Under `EnumerationConsistent`, a printed
number cannot be confirmed under one reading and flagged under another. -/
theorem no_conflict (d : Doc) (tok : Nat → Nat) (hc : d.EnumerationConsistent tok) (i j : Nat)
    (hi : i < d.n) (hj : j < d.n) (ht : tok i = tok j)
    (h1 : d.verdict i = .confirmation) (h2 : d.verdict j = .discrepancy) : False := by
  obtain ⟨hm, _, hgi, hsw⟩ := core_confirmation h1
  have hg : (d.get i).f.grounded = true := by
    have : ((d.get i).f.grounded && (d.get i).f.identOk) = true := hgi
    simp at this; exact this.1
  have hb : (d.get i).f.basicOk = true := by
    rcases hsw with hs | hw
    · have : (d.get i).f.matchGates = true := hs
      simp [Findings.matchGates] at this; exact this.1.1.1
    · have : (d.cor d.sibM i && (d.get i).f.basicOk && (d.get i).f.pinnedOk) = true := hw
      simp at this; exact this.1.2
  obtain ⟨_, _, _, hdisc⟩ := core_discrepancy h2
  have hmg : (d.get j).f.mismatchGates = true := by
    have : ((d.get j).f.mismatchGates && d.cor d.sibD j) = true := hdisc
    simp at this; exact this.1
  simp [Findings.mismatchGates] at hmg
  have hne := hc i j hi hj ht hm hg hb hmg.1.1.1.1.1.2
  rw [hmg.1.1.1.1.2] at hne
  cases hne

/-! ## 6. A proof is not an interpretation -/

/-- **Why no verdict asserts faithfulness.**  Let `obs` be everything a procedure can observe and
suppose every observation is compatible both with a world in which the reading is what the authors
meant and with one in which it is not.  Then a procedure that is never wrong about faithfulness
never asserts it.  The hypothesis is an assumption about the situation (a deposited column can
carry the same numbers under two meanings); it is not derived here. -/
theorem faithfulness_not_decidable_from_observables {World Obs : Type} (obs : World → Obs)
    (faithful : World → Prop)
    (underdetermined : ∀ w, ∃ w', obs w' = obs w ∧ ¬ faithful w')
    (asserts : Obs → Prop) (sound : ∀ w, asserts (obs w) → faithful w) :
    ∀ w, ¬ asserts (obs w) := by
  intro w ha
  obtain ⟨w', ho, hnf⟩ := underdetermined w
  exact hnf (sound w' (ho ▸ ha))

/-! ## 7. Negative controls -/

section Controls

/-- The file `a\n1\n`. -/
def srcOne : Source := ⟨0x610a310a, 4⟩
/-- The file `a\n2\n`. -/
def srcTwo : Source := ⟨0x610a320a, 4⟩

/-- "The mean of column `a` is 1." -/
def meanIsOne : Claim :=
  { column := some [97], filter := [], stat := .mean, naTokens := [[]], scale := 1, reported := [49] }

def allPass : Findings :=
  { hasWindow := true, quoteOk := true, grounded := true, identOk := true, basicOk := true,
    boundedBound := true, noCompeting := true, lowRate := true, pinnedOk := true, notCount := true,
    boundedAll := true, noEligible := true, beyondRounding := true, dispersionNamed := true,
    inGrammar := true, sampleSizeOk := true }

/-- The kernel result for `meanIsOne` on `srcOne`. -/
def acceptedOne : Variant := ⟨meanIsOne, some (run srcOne meanIsOne)⟩

def docOf (r : Rec) : Doc := { n := 1, get := fun _ => r, sibM := fun _ _ => false, sibD := fun _ _ => false }

example : (run srcOne meanIsOne).isMatch = true := by decide +kernel
example : (run srcTwo meanIsOne).isMismatch = true := by decide +kernel

/-- The model can confirm: the theorems are not about an empty set of verdicts. -/
example : (docOf ⟨[acceptedOne], allPass, ""⟩).verdict 0 = .confirmation := by decide +kernel

/-- **Evidence does not transfer between files.**  The same accepted result that is sound for
`srcOne` yields a CONFIRMATION that is false of `srcTwo`: `KernelSound` must be established for the
source in question, and a changed source needs a new kernel run. -/
theorem evidence_does_not_transfer :
    KernelSound srcOne [acceptedOne] ∧ ¬ KernelSound srcTwo [acceptedOne] ∧
      (docOf ⟨[acceptedOne], allPass, ""⟩).verdict 0 = .confirmation ∧
      (run srcTwo meanIsOne).isMatch = false := by
  refine ⟨?_, ?_, by decide +kernel, by decide +kernel⟩
  · intro v hv o ho
    simp at hv; subst hv
    simp [acceptedOne] at ho
    exact ho
  · intro hk
    have this : run srcTwo meanIsOne = run srcOne meanIsOne :=
      hk acceptedOne (by simp) (run srcOne meanIsOne) rfl
    have h1 : (run srcTwo meanIsOne).isMatch = false := by decide +kernel
    have h2 : (run srcOne meanIsOne).isMatch = true := by decide +kernel
    rw [this, h2] at h1
    cases h1

/-- A proved match with one failed gate is REQUIRE_HUMAN_REVIEW: the proof is kept, the reading is
not endorsed. -/
example : (docOf ⟨[acceptedOne], { allPass with lowRate := false }, ""⟩).verdict 0 = .review := by
  decide +kernel

/-- A proved mismatch with every gate passed and no confirmed sibling is not flagged. -/
example : (docOf ⟨[⟨meanIsOne, some (run srcTwo meanIsOne)⟩], allPass, ""⟩).verdict 0 = .review := by
  decide +kernel

/-- `WellFormed` is needed in `verdict_of_strongMatch`: without it a record can support others
while its own verdict is UNKNOWN. -/
example : (⟨[acceptedOne], { allPass with quoteOk := false }, ""⟩ : Rec).strongMatch = true ∧
    (docOf ⟨[acceptedOne], { allPass with quoteOk := false }, ""⟩).verdict 0 = .unknown := by
  decide +kernel

/-- `EnumerationConsistent` is needed in `no_conflict`: with inconsistent findings the same number
is confirmed by record 0 and flagged by record 1. -/
example :
    let d : Doc := { n := 2,
                     get := fun i => if i = 0 then ⟨[acceptedOne], allPass, ""⟩
                                     else ⟨[⟨meanIsOne, some (run srcTwo meanIsOne)⟩], allPass, ""⟩,
                     sibM := fun _ _ => true, sibD := fun _ _ => true }
    d.verdict 0 = .confirmation ∧ d.verdict 1 = .discrepancy := by
  decide +kernel

/-- A plausible but wrong policy: "a competing reading blocks a confirmation only if the kernel
accepted it".  `competitorAccepted = false` (evidence withdrawn) then *raises* the verdict. -/
def coreFlawed (m : Math) (att gi strong competitorAccepted : Bool) : Verdict :=
  match m with
  | .matchProved => if att && gi && strong && !competitorAccepted then .confirmation else .review
  | _ => .unknown

/-- The monotonicity theorem is not automatic: it fails for `coreFlawed`. -/
example : ¬ (∀ c' c : Bool, (c' = true → c = true) →
    Verdict.le (coreFlawed .matchProved true true true c') (coreFlawed .matchProved true true true c) = true) := by
  decide +kernel

end Controls

end PCS.ClaimCheck.Assurance
