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

`builtinCheckers` registers the six verified built-ins:
`reaction_balance` (`PCS.V2.Chemistry`), `unit_compatible` (`PCS.V2.Units`),
`csv_disjoint` (`PCS.V2.Csv`), `pkpd_contract`, `pkpd_reference_match`, and
`pkpd_peak_concentration_threshold` (`PCS.V2.PKPDCheck`).
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

/-- **Compositional soundness**: the dispatcheSECB1ם}��Z�