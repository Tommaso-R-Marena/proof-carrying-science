import PCS.V2.ExecutableGeneral
import PCS.V2.Witnesses.AISafetyCampaign
import PCS.V2.KernelRfl

/-!
# Why the executable bridge is conditional: proved obstructions

`PCS.V2.ExecutableGeneral` proves that `ACCEPT` implies the bounded trace invariant for every
`PASS`-recorded, **certified-tag** (`trace_invariant`) evidence item.  Each qualifier is
necessary.  The facts below are kernel-checked statements about the *executable's own replay
executor* (`authorityOraclesWith certifiedRegistry t`, the executor inside the decision
function of `pcs-lean-authority`) on the unsafe trace `[0, 1, 2, 4, 1, 7]`:

* `uncertifiedTag_passes_unsafe` — for an evidence item whose `check_spec.type` is not a
  registered tag (`trace_invariant_v2`), the executor returns whatever the transcript reports:
  with a transcript reporting `PASS` it returns `PASS` on an unsafe trace.  The meaning of such
  a `PASS` is only "the transcript said so" (`authorityValid_unhandled`), so no theorem about
  the executable can conclude `TraceSafe` from it without trusting the transcript.
* `certifiedTag_fails_unsafe` — the certified tag on the same unsafe trace yields `FAIL` for
  **every** transcript (the transcript cannot override a certified checker).  Consequently a
  certificate that honestly *records* `FAIL` passes the replay stage: acceptance certifies
  that recorded outcomes are reproduced, not that they are positive, so `ACCEPT` alone does
  not imply that any trace is safe.
* `TraceSafe` concerns committed bytes only; transfer to a deployed run requires
  `FaithfulLog` (`PCS.V2.Witnesses.AISafetyDeployment.committed_safe_deployed_unsafe`).

The end-to-end consequence of the first point (a whole archive using the uncertified tag over
an unsafe trace is accepted by the executable when the transcript reports `PASS`) is checked
below by compiled evaluation (`#guard`), which is a test, not a proof.
-/

set_option autoImplicit false

namespace PCS.V2.ExecutableLimits

open PCS PCS.V2.Json PCS.V2.EndToEnd PCS.V2.Authority PCS.V2.Replay PCS.V2.DomainAuthority
open PCS.V2.Witnesses PCS.V2.Witnesses.AISafety PCS.V2.Witnesses.AISafetyGolden
open PCS.V2.Witnesses.AISafetyCampaign

/-- The unsafe trace: forbidden action `7` occurs. -/
def unsafeTrace : ByteArray := ⟨#[0, 1, 2, 4, 1, 7]⟩

theorem unsafeTrace_unsafe : ¬ TraceSafe unsafeTrace.data.toList 4 7 := by
  intro h
  exact h.1 7 (by decide) rfl

/-- Fixture variant: unsafe trace, evidence tagged with the unregistered `trace_invariant_v2`. -/
def v2Spec : FixtureSpec := { trace := unsafeTrace, checkTag := "trace_invariant_v2" }

/-- Fixture variant: unsafe trace with the certified tag `trace_invariant`.  Its evidence
    object is the replay request run in `certifiedTag_fails_unsafe` (the recorded outcome in
    the object is irrelevant there: the executor recomputes it). -/
def v1Spec : FixtureSpec := { trace := unsafeTrace }

def v2Req : ReplayRequest := ⟨[], checkerVersion, v2Spec.evidenceJ, [(traceId, unsafeTrace)]⟩
def v1Req : ReplayRequest := ⟨[], checkerVersion, v1Spec.evidenceJ, [(traceId, unsafeTrace)]⟩

/-- An uncertified tag is decided by the transcript: `PASS` on an unsafe trace. -/
theorem uncertifiedTag_passes_unsafe :
    ((authorityOraclesWith certifiedRegistry v2Spec.transcript).exec v2Req).outcome = .pass ∧
    ¬ TraceSafe unsafeTrace.data.toList 4 7 :=
  ⟨by kernel_rfl, unsafeTrace_unsafe⟩

/-- The certified tag on the same unsafe trace is `FAIL` whatever the transcript says. -/
theorem certifiedTag_fails_unsafe :
    ∀ t : AuthorityTranscript,
      ((authorityOraclesWith certifiedRegistry t).exec v1Req).outcome = .fail := by
  kernel_rfl

/-! Compiled evaluation (tests, not proofs). -/

-- The whole uncertified-tag archive over the unsafe trace, re-signed: the legacy
-- transcript-fallback authority accepted it when the transcript reported `PASS` for `E1`; the
-- strict executable rejects it before replay (kernel-checked in general by
-- `PCS.V2.ExecutableFailClosed.executableAuthority_rejects_unregistered_type`).
#guard productionVerdict v2Spec.transcript v2Spec.build == "ACCEPT"
#guard verdict v2Spec.transcript v2Spec.build == "unsupported_check_type"

end PCS.V2.ExecutableLimits
