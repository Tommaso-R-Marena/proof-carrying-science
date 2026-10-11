import PCSVerifiedLearning.Episode

/-!
# Capability-separated exports, label noninterference and the experiment state machine

* `Record` carries a hidden evaluation proof label; `PubRecord` is the capability-separated
  public view, which has no field for hidden labels.  Every training/export computation,
  retrieval step and feedback intake is typed over `PubRecord` (or the trusted verifier).
* `training_export_label_noninterference` — for **every** pipeline over public views (export,
  retrieval, feedback), datasets differing only in hidden evaluation labels give identical
  results.
* `exportTrain` — keeps only train-split records with cleared provenance, a family disjoint
  from every evaluation family, and a training trajectory re-verified by the trusted verifier;
  each exported row carries a dependency/taint certificate (`deps`) checked to exclude hidden
  fields, with `row_depends_only_on_deps`.
* `GenState`/`genStep` — frozen sources/checker/model, collection, independent label checking,
  training, evaluation, promotion/rejection and versioned research memory;
  `generation_preserves_verifier_authority`, `rejected_never_certified`,
  `registry_grants_no_authority`.
-/

namespace PCSVerifiedLearning

inductive Split where
  | train | eval
  deriving DecidableEq, Repr

inductive Field where
  | id | family | split | goal | trainProof | provenance | hiddenEvalProof
  deriving DecidableEq, Repr

structure Provenance where
  license : String
  sourceRevision : String
  deriving DecidableEq, Repr

structure Record (G A : Type) where
  id : String
  family : String
  split : Split
  goal : G
  trainProof : Option (List A)
  provenance : Provenance
  hiddenEvalProof : Option (List A)

/-- The public capability: no hidden evaluation label. -/
structure PubRecord (G A : Type) where
  id : String
  family : String
  split : Split
  goal : G
  trainProof : Option (List A)
  provenance : Provenance

def Record.pub {G A : Type} (r : Record G A) : PubRecord G A :=
  ⟨r.id, r.family, r.split, r.goal, r.trainProof, r.provenance⟩

/-- Two datasets that differ at most in hidden evaluation labels. -/
def SameUpToHidden {G A : Type} (D D' : List (Record G A)) : Prop := D.map Record.pub = D'.map Record.pub

/-- **Label noninterference**: any computation over the public capability (export, retrieval,
feedback intake, training) is unaffected by hidden evaluation labels. -/
theorem training_export_label_noninterference {G A X : Type}
    (pipeline : List (PubRecord G A) → X) (D D' : List (Record G A)) (h : SameUpToHidden D D') :
    pipeline (D.map Record.pub) = pipeline (D'.map Record.pub) := by
  unfold SameUpToHidden at h; rw [h]

def LICENSES : List String := ["Apache-2.0", "MIT", "BSD-3-Clause", "CC0-1.0"]

structure TrainRow (G A : Type) where
  id : String
  family : String
  goal : G
  proof : List A
  checker : String
  deps : List Field

/-- Fields an exported row is computed from: its taint certificate. -/
def ROW_DEPS : List Field := [.id, .family, .goal, .trainProof]

def rowOf {G A : Type} (V : Verifier G A) (r : PubRecord G A) (p : List A) : TrainRow G A :=
  ⟨r.id, r.family, r.goal, p, V.revision, ROW_DEPS⟩

def evalFamilies {G A : Type} (D : List (PubRecord G A)) : List String :=
  (D.filter (·.split == .eval)).map (·.family)

def eligible {G A : Type} (V : Verifier G A) (D : List (PubRecord G A)) (r : PubRecord G A) :
    Option (TrainRow G A) :=
  match r.split, r.trainProof with
  | .train, some p =>
    if r.provenance.license ∈ LICENSES && r.provenance.sourceRevision != "" &&
        !(evalFamilies D).contains r.family && V.check r.goal p then some (rowOf V r p)
    else none
  | _, _ => none

/-- Training export, typed over the public capability only. -/
def exportTrain {G A : Type} (V : Verifier G A) (D : List (PubRecord G A)) : List (TrainRow G A) :=
  D.filterMap (eligible V D)

/-- Independent taint check of an exported row. -/
def taintOK {G A : Type} (row : TrainRow G A) : Bool :=
  !row.deps.contains .hiddenEvalProof && row.deps.all (· ∈ ROW_DEPS)

theorem exportTrain_sound {G A : Type} (V : Verifier G A) (D : List (PubRecord G A))
    (row : TrainRow G A) (h : row ∈ exportTrain V D) :
    V.check row.goal row.proof = true ∧ V.Sem row.goal ∧ row.family ∉ evalFamilies D ∧
      taintOK row = true ∧ row.checker = V.revision ∧
      ∃ r ∈ D, r.split = .train ∧ r.provenance.license ∈ LICENSES ∧ r.id = row.id := by
  simp only [exportTrain, List.mem_filterMap] at h
  obtain ⟨r, hr, he⟩ := h
  unfold eligible at he
  split at he
  · rename_i p hs hp
    split at he
    · rename_i hc
      cases he
      simp only [Bool.and_eq_true, bne_iff_ne, ne_eq, Bool.not_eq_true', decide_eq_true_eq,
        List.contains_eq_mem, decide_eq_false_iff_not] at hc
      refine ⟨hc.2, V.sound _ _ hc.2, ?_, by simp only [taintOK, rowOf]; decide, rfl, r, hr, hs, hc.1.1.1, rfl⟩
      exact hc.1.2
    · cases he
  · cases he

/-- The row is a function of its certified dependency fields only. -/
theorem row_depends_only_on_deps {G A : Type} (V : Verifier G A) (r r' : PubRecord G A) (p : List A)
    (hid : r.id = r'.id) (hf : r.family = r'.family) (hg : r.goal = r'.goal) :
    rowOf V r p = rowOf V r' p := by
  simp [rowOf, hid, hf, hg]

/-- Retrieval and feedback over research memory are public-capability computations. -/
def retrieve {G A : Type} (score : PubRecord G A → Nat) (k : Nat) (mem : List (PubRecord G A)) :
    List (PubRecord G A) :=
  (mem.filter (·.split == .train)).take k |>.filter (fun r => score r > 0)

theorem retrieval_noninterference {G A : Type} (score : PubRecord G A → Nat) (k : Nat)
    (D D' : List (Record G A)) (h : SameUpToHidden D D') :
    retrieve score k (D.map Record.pub) = retrieve score k (D'.map Record.pub) :=
  training_export_label_noninterference (retrieve score k) D D' h

theorem export_noninterference {G A : Type} (V : Verifier G A) (D D' : List (Record G A))
    (h : SameUpToHidden D D') :
    exportTrain V (D.map Record.pub) = exportTrain V (D'.map Record.pub) :=
  training_export_label_noninterference (exportTrain V) D D' h

/-! ## The iterative experiment state machine -/

inductive MemStatus where
  | claimedProved | unknown | rejected
  deriving DecidableEq, Repr

structure Frozen where
  sources : String
  checker : String
  model : String
  deriving DecidableEq, Repr

structure GenState (G A : Type) where
  generation : Nat
  frozen : Frozen
  facts : List (G × List A)            -- certified facts, each with its checked proof
  memory : List (Nat × G × MemStatus)  -- versioned, unverified research memory
  registry : List String               -- trained model registry
  promoted : Option String

inductive Event (G A : Type) where
  | submit (g : G) (as : List A) (claimedVerified : Bool)
  | note (g : G) (status : MemStatus)
  | train (model : String)
  | promote (model : String)
  | nextGeneration (f : Frozen)

/-- One transition.  `gate` is the statistical promotion gate (exposure-ledger protected). -/
def genStep {G A : Type} (V : Verifier G A) (gate : String → Bool) (s : GenState G A) :
    Event G A → GenState G A
  | .submit g as _ =>
    if V.check g as then { s with facts := (g, as) :: s.facts }
    else { s with memory := (s.generation, g, .rejected) :: s.memory }
  | .note g st => { s with memory := (s.generation, g, st) :: s.memory }
  | .train m => { s with registry := m :: s.registry }
  | .promote m => if s.registry.contains m && gate m then { s with promoted := some m } else s
  | .nextGeneration f => { s with generation := s.generation + 1, frozen := f }

def genRun {G A : Type} (V : Verifier G A) (gate : String → Bool) :
    GenState G A → List (Event G A) → GenState G A
  | s, [] => s
  | s, e :: es => genRun V gate (genStep V gate s e) es

def Authority {G A : Type} (V : Verifier G A) (s : GenState G A) : Prop :=
  ∀ f ∈ s.facts, V.check f.1 f.2 = true

/-- **Every generation preserves the verifier's acceptance boundary.** -/
theorem generation_preserves_verifier_authority {G A : Type} (V : Verifier G A)
    (gate : String → Bool) : ∀ (es : List (Event G A)) (s : GenState G A), Authority V s →
      Authority V (genRun V gate s es) ∧ ∀ f ∈ (genRun V gate s es).facts, V.Sem f.1 := by
  intro es
  induction es with
  | nil => intro s h; exact ⟨h, fun f hf => V.sound _ _ (h f hf)⟩
  | cons e es ih =>
      intro s h
      apply ih
      intro f hf
      cases e with
      | submit g as c =>
          simp only [genStep] at hf
          split at hf
          · rename_i hc
            rcases List.mem_cons.1 hf with rfl | hf
            · exact hc
            · exact h f hf
          · exact h f hf
      | note g st => exact h f hf
      | train m => exact h f hf
      | promote m => simp only [genStep] at hf; split at hf <;> exact h f hf
      | nextGeneration fr => exact h f hf

/-- A rejected (or merely noted, unknown, claimed) item never becomes a certified fact. -/
theorem rejected_never_certified {G A : Type} (V : Verifier G A) (gate : String → Bool)
    (s : GenState G A) (g : G) (as : List A) (c : Bool) (h : V.check g as = false) :
    (genStep V gate s (.submit g as c)).facts = s.facts := by
  simp [genStep, h]

theorem note_never_certified {G A : Type} (V : Verifier G A) (gate : String → Bool)
    (s : GenState G A) (g : G) (st : MemStatus) :
    (genStep V gate s (.note g st)).facts = s.facts := rfl

/-- **Registry membership grants no production authority**: promotion requires the gate. -/
theorem registry_grants_no_authority {G A : Type} (V : Verifier G A) (gate : String → Bool) :
    ∀ (es : List (Event G A)) (s : GenState G A) (m : String),
      (s.promoted = some m → gate m = true) →
      (genRun V gate s es).promoted = some m → gate m = true := by
  intro es
  induction es with
  | nil => intro s m h hp; exact h hp
  | cons e es ih =>
      intro s m h hp
      apply ih _ m _ hp
      intro hp'
      cases e with
      | promote m' =>
          simp only [genStep] at hp'
          split at hp'
          · rename_i hc
            simp only [Option.some.injEq] at hp'; subst hp'
            simp only [Bool.and_eq_true] at hc; exact hc.2
          · exact h hp'
      | submit g as c => simp only [genStep] at hp'; split at hp' <;> exact h hp'
      | note g st => exact h hp'
      | train m' => exact h hp'
      | nextGeneration f => exact h hp'

end PCSVerifiedLearning
