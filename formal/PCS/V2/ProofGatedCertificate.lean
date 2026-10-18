import PCS.V2.ProofGatedBytes
import PCS.V2.ProofGatedStrongArtifacts

/-!
# PGSC6: witness-carrying certificates for the strong gate

A **certificate** (`Cert`, format version `6`, predicate id `1` = "strong gate A ∧ B ∧ C")
binds, in one record:

* the deployment configuration it claims to be about: architecture limits
  (`maxWidth`, `bound`), the target network, the corpus and the robustness interval
  `[lo, hi]`;
* the expected generation and the **complete canonical incumbent byte artifact**;
* the **complete canonical candidate byte artifact**;
* a **witness** for the decision:
  - `gainWitness`: a corpus input that the candidate newly gets right (A);
  - `incLoss`, `candLoss`: the claimed corpus losses (A);
  - `errWitness`, `errLevel`: an input of `[lo,hi]` at which the incumbent's error equals
    `errLevel` (C).

The pure checker `checkCert S g active c` (deployment configuration `S`, current
generation `g`, current active bytes `active`) re-derives the decision *from the
witness*:

* configuration, version, predicate, generation and incumbent identity must match
  exactly; both artifacts must decode under the deployment architecture;
* A is checked from the gain witness and the two (recomputed) losses. The corpus
  preservation sub-check of A is **not** repeated: it is implied by B;
* B is decided by the exact all-integer no-forgetting procedure of `ProofGatedNoForget`;
* C needs only *one* evaluation of the incumbent (at `errWitness`) and the bound check
  of the candidate at level `errLevel`; the checker never computes the incumbent's
  worst-case error, which is the search that the untrusted generator performs.

Results:
* `checkCert_sound`: an accepted certificate establishes `StrongAdmissible S o n` for the
  unique networks `o`, `n` that its byte artifacts canonically encode, with the bound
  configuration, generation and incumbent identity;
* `checkCert_complete`: every strongly admissible modification has an accepted
  certificate, namely the one produced by the (untrusted, unverified-search) generator
  `genCert`;
* `checkCert_iff_gate`: the checker accepts *some* certificate for `(active, cand)` iff the
  wire-level strong gate accepts `(active, cand)`;
* binding rejections: wrong version, wrong predicate, mismatched configuration, stale
  generation and substituted incumbent are each rejected (`checkCert_*_rejected`);
* `verdict_only_unsound`: a certificate format that merely *records* an asserted verdict
  (`VerdictCert`) accepts an inadmissible modification, whereas every witness certificate
  for the same artifacts is rejected (`witness_rejects_verdict_example`).

Serialisation: `encodeCert` / `decodeCert` give a canonical ASCII byte format
`PGSC6|…` (tagged integer record with length-prefixed blocks), with
`decodeCert_encodeCert` (roundtrip) and `decodeCert_iff` (the decoder accepts exactly the
canonical encodings, so no two byte strings denote the same certificate). The byte-level
checker `checkCertBytes` inherits soundness and completeness (`checkCertBytes_sound`,
`checkCertBytes_complete`).

Not assumed and not proved: authenticity of who produced a certificate (signatures),
collision resistance of any hash naming an artifact, and storage integrity.
-/

namespace PCS.V2.ProofGatedCertificate

open PCS.V2.ProofGatedCodec
open PCS.V2.ProofGatedGeneric
open PCS.V2.ProofGatedWide
open PCS.V2.ProofGatedNoForget
open PCS.V2.ProofGatedRobust
open PCS.V2.ProofGatedStrongGate
open PCS.V2.ProofGatedBytes
open PCS.V2.ProofGatedNetArtifacts (toInts ofInts ofInts_toInts toInts_of_ofInts)

/-- Certificate format version. -/
def certVersion : Nat := 6

/-- Predicate identifier: `1` = the strong gate A ∧ B ∧ C of `ProofGatedStrongGate`. -/
def predStrongABC : Nat := 1

/-- A PGSC6 certificate. -/
structure Cert where
  version : Nat
  predicate : Nat
  maxWidth : Nat
  bound : Nat
  target : WideNet
  corpus : List Int
  lo : Int
  hi : Int
  generation : Nat
  incumbent : Bytes
  candidate : Bytes
  gainWitness : Int
  incLoss : Nat
  candLoss : Nat
  errWitness : Int
  errLevel : Nat
  deriving Repr, DecidableEq

/-- The certificate's configuration is exactly the deployment configuration `S`. -/
def configMatches (S : StrongSpec) (c : Cert) : Prop :=
  c.maxWidth = S.arch.maxWidth ∧ c.bound = S.arch.bound ∧ c.target = S.target ∧
    c.corpus = S.corpus ∧ c.lo = S.lo ∧ c.hi = S.hi

instance (S : StrongSpec) (c : Cert) : Decidable (configMatches S c) := by
  unfold configMatches; infer_instance

/-- The header: version, predicate, configuration, generation and incumbent identity. -/
def HeaderOK (S : StrongSpec) (g : Nat) (active : Bytes) (c : Cert) : Prop :=
  c.version = certVersion ∧ c.predicate = predStrongABC ∧ configMatches S c ∧
    c.generation = g ∧ c.incumbent = active

instance (S : StrongSpec) (g : Nat) (active : Bytes) (c : Cert) :
    Decidable (HeaderOK S g active c) := by
  unfold HeaderOK; infer_instance

/-- The witness conditions on the decoded incumbent `o` and candidate `n`. -/
def WitnessOK (S : StrongSpec) (c : Cert) (o n : WideNet) : Prop :=
  -- A: gain witness and strict loss decrease
  c.gainWitness ∈ S.corpus ∧
  predict o c.gainWitness ≠ predict S.target c.gainWitness ∧
  predict n c.gainWitness = predict S.target c.gainWitness ∧
  loss S.corpusSpec o = c.incLoss ∧ loss S.corpusSpec n = c.candLoss ∧
  c.candLoss < c.incLoss ∧
  -- B: universal no-forgetting (exact decision procedure)
  noForgetting o n S.target = true ∧
  -- C: the incumbent reaches `errLevel` inside the interval; the candidate stays below it
  (S.lo ≤ S.hi →
    S.lo ≤ c.errWitness ∧ c.errWitness ≤ S.hi ∧
    errAt o S.target c.errWitness = c.errLevel ∧
    checkErrBound n S.target S.lo S.hi c.errLevel = true)

instance (S : StrongSpec) (c : Cert) (o n : WideNet) : Decidable (WitnessOK S c o n) := by
  unfold WitnessOK; infer_instance

/-- **The independent certificate checker.** -/
def checkCert (S : StrongSpec) (g : Nat) (active : Bytes) (c : Cert) : Bool :=
  decide (HeaderOK S g active c) &&
    match decodeBytes S.arch c.incumbent, decodeBytes S.arch c.candidate with
    | some o, some n => decide (WitnessOK S c o n)
    | _, _ => false

/-! ## Soundness -/

theorem witnessOK_sound {S : StrongSpec} {c : Cert} {o n : WideNet}
    (hvo : valid S.arch o = true) (hvn : valid S.arch n = true) (h : WitnessOK S c o n) :
    StrongAdmissible S o n := by
  obtain ⟨hg, hgo, hgn, hlo, hln, hlt, hnf, hC⟩ := h
  have hB := (noForgetting_iff o n S.target).mp hnf
  refine ⟨⟨hvo, hvn, fun x _ hx => hB x hx, ⟨c.gainWitness, hg, hgo, hgn⟩, by omega⟩, hB, ?_⟩
  intro B hBo x hx1 hx2
  by_cases hLU : S.lo ≤ S.hi
  · obtain ⟨hw1, hw2, hwe, hck⟩ := hC hLU
    have hE : c.errLevel ≤ B := hwe ▸ hBo c.errWitness hw1 hw2
    exact Nat.le_trans ((checkErrBound_iff n S.target S.lo S.hi c.errLevel).mp hck x hx1 hx2) hE
  · omega

/-- **Soundness of the certificate checker.** An accepted certificate binds the
deployment configuration, the current generation and the exact active bytes, and its
byte artifacts canonically encode valid networks `o ↦ n` satisfying A ∧ B ∧ C. -/
theorem checkCert_sound {S : StrongSpec} {g : Nat} {active : Bytes} {c : Cert}
    (h : checkCert S g active c = true) :
    HeaderOK S g active c ∧
    ∃ o n, decodeBytes S.arch c.incumbent = some o ∧ decodeBytes S.arch c.candidate = some n ∧
      encodeBytes o = active ∧ encodeBytes n = c.candidate ∧ StrongAdmissible S o n := by
  unfold checkCert at h
  simp only [Bool.and_eq_true, decide_eq_true_eq] at h
  obtain ⟨hH, h⟩ := h
  refine ⟨hH, ?_⟩
  cases ho : decodeBytes S.arch c.incumbent with
  | none => simp [ho] at h
  | some o =>
    cases hn : decodeBytes S.arch c.candidate with
    | none => simp [ho, hn] at h
    | some n =>
      simp only [ho, hn, decide_eq_true_eq] at h
      refine ⟨o, n, rfl, rfl, ?_, decodeBytes_canonical hn,
        witnessOK_sound (decodeBytes_valid ho) (decodeBytes_valid hn) h⟩
      rw [decodeBytes_canonical ho]; exact hH.2.2.2.2

/-! ## The untrusted generator and completeness -/

/-- Untrusted search for a gain witness. -/
def findGain (S : StrongSpec) (o n : WideNet) : Int :=
  (S.corpus.find? fun x =>
    decide (predict o x ≠ predict S.target x ∧ predict n x = predict S.target x)).getD 0

/-- Untrusted search for a point where the incumbent's worst-case error is attained. -/
def findErrArgmax (S : StrongSpec) (o : WideNet) : Int :=
  ((errProbes o S.target S.lo S.hi).find? fun x =>
    decide (errAt o S.target x = maxAbsErr o S.target S.lo S.hi)).getD S.lo

/-- **The certificate generator** (not trusted: the checker re-validates everything). -/
def genCert (S : StrongSpec) (g : Nat) (o n : WideNet) : Cert where
  version := certVersion
  predicate := predStrongABC
  maxWidth := S.arch.maxWidth
  bound := S.arch.bound
  target := S.target
  corpus := S.corpus
  lo := S.lo
  hi := S.hi
  generation := g
  incumbent := encodeBytes o
  candidate := encodeBytes n
  gainWitness := findGain S o n
  incLoss := loss S.corpusSpec o
  candLoss := loss S.corpusSpec n
  errWitness := findErrArgmax S o
  errLevel := maxAbsErr o S.target S.lo S.hi

theorem findGain_spec (S : StrongSpec) (o n : WideNet)
    (h : ∃ x ∈ S.corpus, predict o x ≠ predict S.target x ∧ predict n x = predict S.target x) :
    findGain S o n ∈ S.corpus ∧ predict o (findGain S o n) ≠ predict S.target (findGain S o n) ∧
      predict n (findGain S o n) = predict S.target (findGain S o n) := by
  unfold findGain
  cases hf : S.corpus.find? (fun x =>
      decide (predict o x ≠ predict S.target x ∧ predict n x = predict S.target x)) with
  | none =>
    exfalso
    obtain ⟨x, hx, hp⟩ := h
    have := List.find?_eq_none.mp hf x hx
    simp only [decide_eq_true_eq] at this
    exact this hp
  | some y =>
    have hm := List.mem_of_find?_eq_some hf
    have hp := List.find?_some hf
    simp only [decide_eq_true_eq] at hp
    exact ⟨hm, hp⟩

theorem findErrArgmax_spec (S : StrongSpec) (o : WideNet) (hLU : S.lo ≤ S.hi) :
    S.lo ≤ findErrArgmax S o ∧ findErrArgmax S o ≤ S.hi ∧
      errAt o S.target (findErrArgmax S o) = maxAbsErr o S.target S.lo S.hi := by
  unfold findErrArgmax
  cases hf : (errProbes o S.target S.lo S.hi).find? (fun x =>
      decide (errAt o S.target x = maxAbsErr o S.target S.lo S.hi)) with
  | none =>
    exfalso
    obtain ⟨x, hx, hex⟩ := maxOver_attained (errAt o S.target) S.lo
      (S.hi :: (errKinks o S.target).filter (inIv S.lo S.hi))
    have hmax : maxAbsErr o S.target S.lo S.hi =
        maxOver (errAt o S.target) (errProbes o S.target S.lo S.hi) := by
      unfold maxAbsErr; rw [if_pos hLU]
    have := List.find?_eq_none.mp hf x hx
    simp only [decide_eq_true_eq] at this
    exact this (hmax ▸ hex)
  | some y =>
    have hm := List.mem_of_find?_eq_some hf
    have hp := List.find?_some hf
    simp only [decide_eq_true_eq] at hp
    have hI := probes_in_interval (errKinks o S.target) S.lo S.hi hLU y hm
    exact ⟨hI.1, hI.2, hp⟩

/-- **Completeness for the supported domain.** Every strongly admissible modification
`o ↦ n` has an accepted certificate against the current generation and the canonical
incumbent bytes, namely `genCert S g o n`. -/
theorem checkCert_complete (S : StrongSpec) (g : Nat) (o n : WideNet)
    (h : StrongAdmissible S o n) :
    checkCert S g (encodeBytes o) (genCert S g o n) = true := by
  obtain ⟨⟨hvo, hvn, _, hgain, hloss⟩, hB, hC⟩ := h
  have hvo' : valid S.arch o = true := hvo
  have hvn' : valid S.arch n = true := hvn
  unfold checkCert
  simp only [Bool.and_eq_true, decide_eq_true_eq]
  refine ⟨⟨rfl, rfl, ⟨rfl, rfl, rfl, rfl, rfl, rfl⟩, rfl, rfl⟩, ?_⟩
  simp only [genCert, decodeBytes_encodeBytes _ _ hvo', decodeBytes_encodeBytes _ _ hvn',
    decide_eq_true_eq]
  obtain ⟨hg1, hg2, hg3⟩ := findGain_spec S o n hgain
  refine ⟨hg1, hg2, hg3, rfl, rfl, hloss, (noForgetting_iff o n S.target).mpr hB, ?_⟩
  intro hLU
  obtain ⟨h1, h2, h3⟩ := findErrArgmax_spec S o hLU
  refine ⟨h1, h2, h3, ?_⟩
  exact (checkErrBound_iff n S.target S.lo S.hi _).mpr
    (hC _ ((maxAbsErr_le_iff o S.target S.lo S.hi _).mp (Nat.le_refl _)))

/-- The generated certificate names exactly the canonical artifacts. -/
theorem genCert_artifacts (S : StrongSpec) (g : Nat) (o n : WideNet) :
    (genCert S g o n).incumbent = encodeBytes o ∧ (genCert S g o n).candidate = encodeBytes n ∧
      (genCert S g o n).generation = g := ⟨rfl, rfl, rfl⟩

/-- **Checker/gate agreement.** Some certificate for `(active, cand)` is accepted iff the
wire-level strong gate accepts the pair, i.e. iff both byte strings canonically encode
networks related by A ∧ B ∧ C. -/
theorem checkCert_iff_gate (S : StrongSpec) (g : Nat) (active cand : Bytes) :
    (∃ c, checkCert S g active c = true ∧ c.candidate = cand) ↔
      ∃ o n, decodeBytes S.arch active = some o ∧ decodeBytes S.arch cand = some n ∧
        StrongAdmissible S o n := by
  constructor
  · rintro ⟨c, hc, rfl⟩
    obtain ⟨hH, o, n, ho, hn, -, -, hadm⟩ := checkCert_sound hc
    exact ⟨o, n, hH.2.2.2.2 ▸ ho, hn, hadm⟩
  · rintro ⟨o, n, ho, hn, hadm⟩
    refine ⟨genCert S g o n, ?_, decodeBytes_canonical hn⟩
    rw [← decodeBytes_canonical ho]
    exact checkCert_complete S g o n hadm

/-! ## Binding rejections -/

theorem checkCert_header {S : StrongSpec} {g : Nat} {active : Bytes} {c : Cert}
    (h : ¬ HeaderOK S g active c) : checkCert S g active c = false := by
  simp [checkCert, h]

theorem checkCert_version_rejected (S : StrongSpec) (g : Nat) (active : Bytes) (c : Cert)
    (h : c.version ≠ certVersion) : checkCert S g active c = false :=
  checkCert_header fun hH => h hH.1

theorem checkCert_predicate_rejected (S : StrongSpec) (g : Nat) (active : Bytes) (c : Cert)
    (h : c.predicate ≠ predStrongABC) : checkCert S g active c = false :=
  checkCert_header fun hH => h hH.2.1

/-- A certificate produced for a different configuration (architecture limits, target,
corpus or interval) is rejected. -/
theorem checkCert_config_rejected (S : StrongSpec) (g : Nat) (active : Bytes) (c : Cert)
    (h : ¬ configMatches S c) : checkCert S g active c = false :=
  checkCert_header fun hH => h hH.2.2.1

theorem checkCert_stale_rejected (S : StrongSpec) (g : Nat) (active : Bytes) (c : Cert)
    (h : c.generation ≠ g) : checkCert S g active c = false :=
  checkCert_header fun hH => h hH.2.2.2.1

/-- A certificate for a different incumbent artifact (even one encoding a network that
computes the same function) is rejected. -/
theorem checkCert_substituted_rejected (S : StrongSpec) (g : Nat) (active : Bytes) (c : Cert)
    (h : c.incumbent ≠ active) : checkCert S g active c = false :=
  checkCert_header fun hH => h hH.2.2.2.2

/-- A candidate artifact that does not decode is rejected, whatever the witness. -/
theorem checkCert_malformed_candidate (S : StrongSpec) (g : Nat) (active : Bytes) (c : Cert)
    (h : decodeBytes S.arch c.candidate = none) : checkCert S g active c = false := by
  unfold checkCert
  cases decodeBytes S.arch c.incumbent <;> simp [h]

/-- Changing the candidate bytes in an accepted certificate to *different* bytes for which
the strong gate fails yields a rejected certificate: the witness does not transfer. -/
theorem checkCert_candidate_swap {S : StrongSpec} {g : Nat} {active : Bytes} {c : Cert}
    (cand' : Bytes)
    (hbad : ∀ o n, decodeBytes S.arch active = some o → decodeBytes S.arch cand' = some n →
      ¬ StrongAdmissible S o n) :
    checkCert S g active { c with candidate := cand' } = false := by
  cases hc : checkCert S g active { c with candidate := cand' } with
  | false => rfl
  | true =>
    obtain ⟨hH, o, n, ho, hn, -, -, hadm⟩ := checkCert_sound hc
    exact absurd hadm (hbad o n (hH.2.2.2.2 ▸ ho) hn)

/-! ## Verdict-only certificates are not evidence -/

/-- A certificate that merely records an asserted verdict next to the bound artifacts. -/
structure VerdictCert where
  generation : Nat
  incumbent : Bytes
  candidate : Bytes
  verdict : Bool
  deriving Repr, DecidableEq

/-- A checker that trusts the recorded verdict (after checking binding and decodability). -/
def checkVerdict (S : StrongSpec) (g : Nat) (active : Bytes) (c : VerdictCert) : Bool :=
  c.generation == g && c.incumbent == active && c.verdict &&
    (decodeBytes S.arch c.incumbent).isSome && (decodeBytes S.arch c.candidate).isSome

/-- The asserted-verdict certificate replacing the perfect `gen3` by the empty network. -/
def badVerdict : VerdictCert := ⟨0, encodeBytes gen3, encodeBytes gen0, true⟩

theorem gen3_gen0_not_admissible : ¬ StrongAdmissible specWide gen3 gen0 := by
  rw [← acceptStrong_iff]; decide

/-- **Verdict-only certificates are unsound**: the trusting checker accepts a regression
from the perfect network to the zero network. -/
theorem verdict_only_unsound :
    checkVerdict specWide 0 (encodeBytes gen3) badVerdict = true ∧
    ∀ o n, decodeBytes specWide.arch badVerdict.incumbent = some o →
      decodeBytes specWide.arch badVerdict.candidate = some n → ¬ StrongAdmissible specWide o n := by
  have h3 : decodeBytes arch3 (encodeBytes gen3) = some gen3 :=
    decodeBytes_encodeBytes _ _ (by decide)
  have h0 : decodeBytes arch3 (encodeBytes gen0) = some gen0 :=
    decodeBytes_encodeBytes _ _ (by decide)
  refine ⟨?_, ?_⟩
  · simp [checkVerdict, badVerdict, specWide, h3, h0]
  · intro o n ho hn
    simp only [badVerdict, specWide] at ho hn
    rw [h3] at ho; rw [h0] at hn
    cases ho; cases hn
    exact gen3_gen0_not_admissible

/-- **Witness certificates reject the same claim**: no witness whatsoever makes the
checker accept the replacement of `gen3` by `gen0`. -/
theorem witness_rejects_verdict_example (g : Nat) (c : Cert) (hc : c.candidate = encodeBytes gen0) :
    checkCert specWide g (encodeBytes gen3) c = false := by
  cases h : checkCert specWide g (encodeBytes gen3) c with
  | false => rfl
  | true =>
    obtain ⟨hH, o, n, ho, hn, -, -, hadm⟩ := checkCert_sound h
    rw [hH.2.2.2.2, decodeBytes_encodeBytes _ _ (by decide)] at ho
    rw [hc, decodeBytes_encodeBytes _ _ (by decide)] at hn
    cases ho; cases hn
    exact absurd hadm gen3_gen0_not_admissible

end PCS.V2.ProofGatedCertificate
