import PCS.V2.ProofGatedReceipt

/-!
# V7 Priority 5: an explicit refinement contract for an external runtime

An external (Python or compiled) implementation is modelled **abstractly** as a record of
functions (`Runtime`): a policy loader, a checker, an artifact parser, an arithmetic
evaluator, the rule that decides which bytes are served after a commit, and the
generation update. Its state (`RState`) holds the configuration bytes it actually uses,
its generation, its active bytes and the bytes it actually serves.

The **refinement contract** (`Contract P X R`) lists every obligation as a separate
hypothesis:

| clause        | obligation                                                         |
|---------------|--------------------------------------------------------------------|
| `policyId`    | loading the pinned policy bytes yields exactly the pinned policy   |
| `checkerId`   | the runtime checker equals the verified checker table `runChecker` |
| `parseExact`  | byte-for-byte canonical parsing with exact parameters and bounds   |
| `arith`       | integer evaluation equals `predict` on valid networks, `|x| ≤ X`   |
| `execId`      | after a commit the runtime serves exactly the committed bytes      |
| `genNext`     | a commit advances the generation by exactly one                    |

plus the **state assumptions** of `Initial` (configuration = pinned bytes, served =
active, active decodes) and the **monotonic-state assumption** that the runtime state
evolves only through `rtStep` (no rollback / restore of an old snapshot).

`runtime_end_to_end` proves, under exactly these hypotheses, that after any adversarial
request sequence the runtime state *is* the abstract authority state, and that every
prediction it serves for `|x| ≤ X` equals `predict m x` for the committed network `m`,
which keeps every correct integer of the initial model and its interval error bounds.
`int64_runtime_end_to_end` discharges `arith` for a wrapping fixed-width evaluator by the
`NoOverflow` condition of `ProofGatedInterpreter`.

Each clause is necessary (kernel-checked counterexamples):
* no policy authority: `ProofGatedPolicy.naive_target_attack` and the other attacks;
* `execId` dropped (`stale_cache_runtime`): the runtime keeps serving the old model after a
  commit and answers differently from the committed network;
* monotonic state dropped (`rollback_breaks_no_forgetting`, `rollback_enables_replay`):
  restoring an old snapshot forgets inputs the current model gets right, and old
  certificates become acceptable again;
* `arith` dropped (`overflow_runtime`): the `int64` runtime returns `0` instead of `2^64`
  inside the certified interval;
* `parseExact` dropped (`truncating_parser_runtime`): a parser that drops the last hidden
  unit serves a different function.

**Not claimed**: nothing here verifies an actual Python interpreter, operating-system
permissions, signatures, disk durability or atomicity. Those are exactly the hypotheses.
-/

namespace PCS.V2.ProofGatedRuntimeContract

open PCS.V2.ProofGatedGeneric
open PCS.V2.ProofGatedWide
open PCS.V2.ProofGatedRobust
open PCS.V2.ProofGatedStrongGate
open PCS.V2.ProofGatedBytes
open PCS.V2.ProofGatedCertificate
open PCS.V2.ProofGatedCertCodec
open PCS.V2.ProofGatedPolicy
open PCS.V2.ProofGatedBoundary
open PCS.V2.ProofGatedInterpreter

/-- An abstract external runtime. -/
structure Runtime where
  loadPolicy : Bytes → Option Policy
  check : Policy → Nat → Bytes → Bytes → Option Bytes
  parse : Arch → Bytes → Option WideNet
  eval : WideNet → Int → Int
  servedAfterCommit : Bytes → Bytes → Bytes
  nextGen : Nat → Nat

/-- Runtime state. -/
structure RState where
  config : Bytes
  generation : Nat
  active : Bytes
  served : Bytes
  deriving Repr, DecidableEq

def rtStep (R : Runtime) (st : RState) (r : Request) : RState :=
  match R.loadPolicy st.config with
  | none => st
  | some p =>
    match R.check p st.generation st.active r.certificate with
    | some cand => ⟨st.config, R.nextGen st.generation, cand, R.servedAfterCommit st.served cand⟩
    | none => st

def rtRun (R : Runtime) : RState → List Request → RState
  | st, [] => st
  | st, r :: rs => rtRun R (rtStep R st r) rs

/-- What the runtime serves. -/
def rtPredict (R : Runtime) (st : RState) (x : Int) : Option Int :=
  match R.loadPolicy st.config with
  | none => none
  | some p => (R.parse p.arch st.served).map fun m => R.eval m x

/-- **The refinement contract.** Every external trust assumption is a field. -/
structure Contract (P : Policy) (X : Nat) (R : Runtime) : Prop where
  policyId : R.loadPolicy (encodePolicy P) = some P
  checkerId : ∀ p g a cb, R.check p g a cb = runChecker p g a cb
  parseExact : ∀ A bs, R.parse A bs = decodeBytes A bs
  arith : ∀ m x, valid P.arch m = true → x.natAbs ≤ X → R.eval m x = predict m x
  execId : ∀ old new, R.servedAfterCommit old new = new
  genNext : ∀ g, R.nextGen g = g + 1

/-- Initial-state assumptions. -/
structure Initial (P : Policy) (st : RState) (m₀ : WideNet) : Prop where
  config : st.config = encodePolicy P
  served : st.served = st.active
  decodes : decodeBytes P.arch st.active = some m₀

/-- The abstraction map. -/
def abs (P : Policy) (st : RState) : AState := ⟨P, st.generation, st.active⟩

theorem rtStep_refines {P : Policy} {X : Nat} {R : Runtime} (hC : Contract P X R) (st : RState)
    (hcfg : st.config = encodePolicy P) (r : Request) :
    abs P (rtStep R st r) = (propose (abs P st) r).1 ∧ (rtStep R st r).config = encodePolicy P ∧
      ((rtStep R st r).served = (rtStep R st r).active ∨ (rtStep R st r).served = st.served ∧
        (rtStep R st r).active = st.active) := by
  unfold rtStep
  rw [hcfg, hC.policyId]
  simp only [hC.checkerId]
  rcases propose_cases (abs P st) r with ⟨hd, hs, -⟩ | ⟨cand, hd, hs, -⟩
  · have hd' : runChecker P st.generation st.active r.certificate = none := hd
    rw [hd', hs]
    exact ⟨rfl, hcfg, Or.inr ⟨rfl, rfl⟩⟩
  · have hd' : runChecker P st.generation st.active r.certificate = some cand := hd
    rw [hd', hs]
    simp [abs, hC.genNext, hC.execId]

theorem rtRun_refines {P : Policy} {X : Nat} {R : Runtime} (hC : Contract P X R) :
    ∀ (rs : List Request) (st : RState), st.config = encodePolicy P → st.served = st.active →
      abs P (rtRun R st rs) = (runAdv (abs P st) rs).1 ∧ (rtRun R st rs).config = encodePolicy P ∧
        (rtRun R st rs).served = (rtRun R st rs).active := by
  intro rs
  induction rs with
  | nil => intro st h1 h2; exact ⟨rfl, h1, h2⟩
  | cons r rs ih =>
    intro st h1 h2
    obtain ⟨e1, e2, e3⟩ := rtStep_refines hC st h1 r
    have h3 : (rtStep R st r).served = (rtStep R st r).active := by
      rcases e3 with e | ⟨e, e'⟩
      · exact e
      · rw [e, e', h2]
    obtain ⟨f1, f2, f3⟩ := ih (rtStep R st r) e2 h3
    refine ⟨?_, f2, f3⟩
    simp only [rtRun, runAdv]
    rw [f1, e1]

/-- **Conditional end-to-end security of an external runtime.** Under the refinement
contract, the initial-state assumptions and the monotonic-state assumption (the runtime
state evolves only by `rtStep`), after **any** adversarial request sequence:
the runtime state is the abstract authority state, and every served prediction for
`|x| ≤ X` is `predict m x` for the committed network `m`, which keeps every integer the
initial model got right and stays within its interval error bounds. -/
theorem runtime_end_to_end (P : Policy) (X : Nat) (R : Runtime) (hC : Contract P X R)
    (st : RState) (m₀ : WideNet) (hI : Initial P st m₀) (rs : List Request) :
    abs P (rtRun R st rs) = (runAdv (abs P st) rs).1 ∧
    ∃ m, encodeBytes m = (rtRun R st rs).active ∧ valid P.arch m = true ∧
      (∀ x, x.natAbs ≤ X → rtPredict R (rtRun R st rs) x = some (predict m x)) ∧
      (∀ x, predict m₀ x = predict P.target x → predict m x = predict P.target x) ∧
      (∀ B, ErrBound m₀ P.target P.lo P.hi B → ErrBound m P.target P.lo P.hi B) ∧
      acceptedCount (runAdv (abs P st) rs).2 + loss P.spec.corpusSpec m ≤ loss P.spec.corpusSpec m₀ := by
  obtain ⟨h1, h2, h3⟩ := rtRun_refines hC rs st hI.config hI.served
  refine ⟨h1, ?_⟩
  obtain ⟨m, ⟨-, hd, hnf, hrob⟩, -, hl⟩ := runAdv_invariant (abs P st) rs m₀ hI.decodes
  rw [← h1] at hd
  have hd' : decodeBytes P.arch (rtRun R st rs).active = some m := hd
  have hv := decodeBytes_valid hd'
  refine ⟨m, decodeBytes_canonical hd', hv, fun x hx => ?_, hnf, hrob, hl⟩
  simp only [rtPredict, h2, hC.policyId, h3, hC.parseExact, hd', Option.map_some,
    hC.arith m x hv hx]

/-! ## Discharging `arith` for a fixed-width runtime -/

/-- A reference runtime with a wrapping fixed-width evaluator (registers of `2·h` values). -/
def refRuntime (h : Nat) : Runtime :=
  ⟨decodePolicy, runChecker, decodeBytes, predictK h, fun _ new => new, (· + 1)⟩

theorem refRuntime_contract (P : Policy) (X h : Nat) (hno : NoOverflow P.arch X h) :
    Contract P X (refRuntime h) :=
  ⟨decodePolicy_encodePolicy P, fun _ _ _ _ => rfl, fun _ _ => rfl,
    fun m x hv hx => predictK_eq_predict P.arch X h hno m hv x hx, fun _ _ => rfl, fun _ => rfl⟩

/-- **Fixed-width instance**: under `NoOverflow`, the wrapping runtime serves exactly the
committed network on `|x| ≤ X` after any adversarial request sequence. -/
theorem int64_runtime_end_to_end (P : Policy) (X h : Nat) (hno : NoOverflow P.arch X h)
    (st : RState) (m₀ : WideNet) (hI : Initial P st m₀) (rs : List Request) :
    ∃ m, encodeBytes m = (rtRun (refRuntime h) st rs).active ∧
      ∀ x, x.natAbs ≤ X → rtPredict (refRuntime h) (rtRun (refRuntime h) st rs) x = some (predict m x) := by
  obtain ⟨-, m, he, -, hp, -⟩ :=
    runtime_end_to_end P X (refRuntime h) (refRuntime_contract P X h hno) st m₀ hI rs
  exact ⟨m, he, hp⟩

/-! ## Necessity of each clause -/

/-- The initial runtime state of the fixtures: pinned policy, generation 0, `gen0`. -/
def st0 : RState := ⟨encodePolicy pinned0, 0, encodeBytes gen0, encodeBytes gen0⟩

/-- A runtime that keeps serving its cached model after a commit (no execution identity). -/
def staleCacheRuntime : Runtime :=
  { refRuntime 0 with eval := predict, servedAfterCommit := fun old _ => old }

/-- The authorised prediction (what the committed network computes). -/
def authorized (st : RState) (x : Int) : Option Int := inferBytes pinned0.arch st.active x

/-- **Execution identity is necessary**: after the genuine commit `gen0 ↦ r1`, the cached
runtime answers `predict gen0 (-1)`, while the committed network answers `predict r1 (-1)`. -/
theorem stale_cache_runtime :
    (rtRun staleCacheRuntime st0 (genuineReqs.take 1)).active = encodeBytes r1 ∧
    rtPredict staleCacheRuntime (rtRun staleCacheRuntime st0 (genuineReqs.take 1)) (-1) =
      some (predict gen0 (-1)) ∧
    authorized (rtRun staleCacheRuntime st0 (genuineReqs.take 1)) (-1) = some (predict r1 (-1)) ∧
    predict gen0 (-1) ≠ predict r1 (-1) := by
  decide +kernel

/-- Restore an old snapshot (what a non-monotonic store permits). -/
def rollbackTo (snapshot : RState) (_current : RState) : RState := snapshot

/-- **Monotonic state is necessary (forgetting)**: after the three genuine commits the
runtime serves `gen3`, which is correct at `x = 0`; restoring the generation-1 snapshot
serves `r1`, which is wrong at `x = 0`. -/
theorem rollback_breaks_no_forgetting :
    let R := refRuntime int64Half
    let st3 := rtRun R st0 genuineReqs
    let st1 := rtRun R st0 (genuineReqs.take 1)
    st3.active = encodeBytes gen3 ∧
    rtPredict R st3 0 = some (predict pinned0.target 0) ∧
    rtPredict R (rollbackTo st1 st3) 0 ≠ some (predict pinned0.target 0) := by
  decide +kernel

/-- **Monotonic state is necessary (replay)**: after restoring the generation-1 snapshot,
the already-used second genuine certificate is accepted *again*. -/
theorem rollback_enables_replay :
    let R := refRuntime int64Half
    let st3 := rtRun R st0 genuineReqs
    let st1 := rtRun R st0 (genuineReqs.take 1)
    rtRun R st3 ((genuineReqs.drop 1).take 1) = st3 ∧
    (rtRun R (rollbackTo st1 st3) ((genuineReqs.drop 1).take 1)).generation = 2 := by
  decide +kernel

/-- **The overflow contract is necessary**: under the verification configuration
`bigSpec`, the committed network is exact, yet the `int64` evaluator returns `0` instead of
`2^64` at `x = 2^62`, inside the certified interval. -/
theorem overflow_runtime :
    predict bigNet (2 ^ 62) = 2 ^ 64 ∧ predictK int64Half bigNet (2 ^ 62) = 0 ∧
    ¬ NoOverflow ⟨1, 4⟩ (2 ^ 62) int64Half := by
  refine ⟨int64_mismatch.2.2.1, int64_mismatch.2.2.2.1, ?_⟩
  intro h
  exact absurd h.1 (by decide)

/-- A parser that silently drops the last hidden unit. -/
def truncatingParse (A : Arch) (bs : Bytes) : Option WideNet :=
  (decodeBytes A bs).map fun m => ⟨m.hidden.dropLast, m.outBias⟩

def truncatingRuntime : Runtime := { refRuntime int64Half with parse := truncatingParse }

/-- **Exact parsing is necessary**: with the truncating parser, after the three genuine
commits the runtime serves `gen2` instead of the committed `gen3`, which differs at `x = 3`. -/
theorem truncating_parser_runtime :
    (rtRun truncatingRuntime st0 genuineReqs).active = encodeBytes gen3 ∧
    rtPredict truncatingRuntime (rtRun truncatingRuntime st0 genuineReqs) 3 = some (predict gen2 3) ∧
    predict gen2 3 ≠ predict gen3 3 := by
  decide +kernel

/-- The reference runtime satisfies the full contract for the pinned fixture policy on
`|x| ≤ 32768` (by `NoOverflow`, since `arch3` has width 8 and bound 32). -/
theorem pinned0_contract : Contract pinned0 32768 (refRuntime int64Half) := by
  apply refRuntime_contract
  unfold NoOverflow int64Half
  simp only [pinned0, arch3]
  omega

end PCS.V2.ProofGatedRuntimeContract
