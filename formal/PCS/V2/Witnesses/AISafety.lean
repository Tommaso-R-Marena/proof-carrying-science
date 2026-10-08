import PCS.V2.Witnesses.Registry

/-!
# Witness domain 2: AI safety — bounded execution-trace invariants

Domain claim `TraceClaim`: for each of a non-empty list of committed execution-trace
artifacts (one action code per byte), with the declared risk budget `budget` and the
declared forbidden action code `forbidden`,

* no forbidden action occurs, and
* every transition preserves the safety invariant "cumulative risk ≤ budget", i.e. the
  state after every prefix of the trace satisfies the invariant (`TraceSafe`).

The risk of an action `a` is `a mod 4` (a toy, declared cost model).

Decomposition: root `.all c` is split by rule `"ai.episodes"` into one `.safe` leaf per
trace (an n-ary, data-dependent decomposition); each leaf is discharged by the
proof-carrying checker `trace_invariant`.  The checker tests only the *total* risk;
`traceTest_sound` proves this implies the invariant at *every* prefix (risks are
non-negative), so the checker's PASS really means the per-transition property.

**Scope.** This proves the stated invariant of the committed traces.  It says nothing about
traces that were not committed, about the policy's behaviour elsewhere, or about global AI
safety.
-/

set_option autoImplicit false

namespace PCS.V2.Witnesses.AISafety

open PCS PCS.V2.Json PCS.V2.Replay PCS.V2.Checkers PCS.V2.PKPDCheck PCS.V2.DomainAuthority
open PCS.V2.DomainAdapter PCS.V2.ClaimGraph PCS.V2.Witnesses

/-! ## Domain semantics -/

def risk (a : UInt8) : Nat := a.toNat % 4

/-- State (cumulative risk) after executing a trace prefix. -/
def stateAfter (tr : List UInt8) : Nat := (tr.map risk).sum

/-- Every transition keeps the invariant and no forbidden action occurs. -/
def TraceSafe (tr : List UInt8) (budget forbidden : Nat) : Prop :=
  (∀ a ∈ tr, a.toNat ≠ forbidden) ∧ ∀ k ≤ tr.length, stateAfter (tr.take k) ≤ budget

structure TraceClaim where
  traces : List String
  budget : Nat
  forbidden : Nat
  deriving DecidableEq

def aiDomain : Domain :=
  { World := List (String × ByteArray), Claim := TraceClaim,
    Holds := fun w c => ∀ a ∈ c.traces, ∃ tr, artBytes w a = some tr ∧
      TM��{��Z�