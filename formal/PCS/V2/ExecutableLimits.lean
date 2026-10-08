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

* `uncertifiedTag_passes_unsafe` â€” for an evidence item whose `check_spec.type` is not a
  registered tag (`trace_invariant_v2`), the executor returns whatever the transcript reports:
  with a transcript reporting `PASS` it returns `PASS` on an unsafe trace.  The meaning of such
  a `PASS` is only "the transcript said so" (`authorityValid_unhandled`), so no theorem about
  the executable can conclude `TraceSafe` from it without trusting the transcript.
* `certifiedTag_fails_unsafe` â€” the certified tag on the same unsafe trace yields `FAIL` for
  **every** transcript (the transcript cannot override a certified checker).  Consequently a
  certificate that honestly *records* `FAIL` passes the replay stage: acceptance certifies
  that recorded outcomes are reproduced, not that they are positive, so `ACCEPT` alone$ÑPÐ€L@ùëo…ªì