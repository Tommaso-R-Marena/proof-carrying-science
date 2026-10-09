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
      TraceSafe tr c.budget c.forbidden }

inductive TraceIR where
  | all (c : TraceClaim)
  | safe (trace : String) (budget forbidden : Nat)
  deriving DecidableEq

def traceSem (w : List (String × ByteArray)) : TraceIR → Prop
  | .all c => ∀ a ∈ c.traces, ∃ tr, artBytes w a = some tr ∧ TraceSafe tr c.budget c.forbidden
  | .safe a b f => ∃ tr, artBytes w a = some tr ∧ TraceSafe tr b f

/-! ## Proof-carrying checker -/

theorem stateAfter_take_le (tr : List UInt8) (k : Nat) : stateAfter (tr.take k) ≤ stateAfter tr := by
  have h := congrArg (fun l => (l.map risk).sum) (List.take_append_drop k tr)
  simp only [List.map_append, List.sum_append_nat] at h
  unfold stateAfter
  omega

def traceTestB (tr : List UInt8) (budget forbidden : Nat) : Bool :=
  tr.all (fun a => a.toNat != forbidden) && decide (stateAfter tr ≤ budget)

theorem traceTestB_sound {tr : List UInt8} {b f : Nat} (h : traceTestB tr b f = true) :
    TraceSafe tr b f := by
  simp only [traceTestB, Bool.and_eq_true, List.all_eq_true, bne_iff_ne, ne_eq,
    decide_eq_true_eq] at h
  exact ⟨h.1, fun k _ => Nat.le_trans (stateAfter_take_le tr k) h.2⟩

def parseTrace (ev : JVal) : Option (String × Nat × Nat) :=
  match specStr ev "trace_artifact", specNat ev "budget", specNat ev "forbidden" with
  | some a, some b, some f => some (a, b, f)
  | _, _, _ => none

def traceTest (x : String × Nat × Nat) (w : List (String × ByteArray)) : Bool :=
  match artBytes w x.1 with
  | some tr => traceTestB tr x.2.1 x.2.2
  | none => false

theorem traceTest_sound (x : String × Nat × Nat) (w : List (String × ByteArray))
    (h : traceTest x w = true) : traceSem w (.safe x.1 x.2.1 x.2.2) := by
  unfold traceTest at h
  split at h
  · rename_i tr htr; exact ⟨tr, htr, traceTestB_sound h⟩
  · cases h

def traceChecker : DomainChecker :=
  specChecker "trace_invariant" parseTrace traceTest
    (fun x w => traceSem w (.safe x.1 x.2.1 x.2.2)) traceTest_sound

/-! ## Adapter -/

def traceNodeOf (ev : JVal) : Option TraceIR :=
  if isCheckType "trace_invariant" ev then (parseTrace ev).map (fun x => .safe x.1 x.2.1 x.2.2)
  else none

def traceRule (r : String) (p : TraceIR) (cs : List TraceIR) : Bool :=
  r == "ai.episodes" &&
    match p with
    | .all c => decide (cs = c.traces.map (fun a => .safe a c.budget c.forbidden))
    | _ => false

/-- Claim predicate: `{"kind": "ai.trace_invariant", "budget": b, "forbidden": f,
    "trace_artifact": a}` (single-trace form; multi-trace claims arise from IR). -/
def aiAdapter : DomainAdapter aiDomain :=
  { IR := TraceIR,
    decode := fun v => match predStr v "kind",
        predStr v "trace_artifact",
        predNat v "budget",
        predNat v "forbidden" with
      | some "ai.trace_invariant", some a, some b, some f => some ⟨[a], b, f⟩
      | _, _, _, _ => none,
    compile := fun c => if c.traces.isEmpty then none else some (.all c),
    world := id,
    sem := traceSem,
    leafCheck := fun ev n => decide (traceNodeOf ev = some n),
    ruleCheck := traceRule }

theorem aiAdapter_sound {ks : List DomainChecker} (hreg : Registered ks)
    (hk : traceChecker ∈ ks) (ExtHolds : ReplayRequest → Prop) :
    AdapterSound aiAdapter (AuthorityValid (registry ks) ExtHolds) where
  compile_sound := by
    intro w c ir hc hsem
    simp only [aiAdapter] at hc
    split at hc
    · cases hc
    · cases hc; exact hsem
  rule_sound := by
    intro w r p cs h hcs
    simp only [aiAdapter, traceRule, Bool.and_eq_true] at h
    obtain ⟨_, h⟩ := h
    cases p with
    | all c =>
      simp only [decide_eq_true_eq] at h
      subst h
      intro a ha
      exact hcs _ (List.mem_map_of_mem ha)
    | safe _ _ _ => cases h
  leaf_sound := by
    intro req n hl hv
    simp only [aiAdapter, decide_eq_true_eq] at hl
    unfold traceNodeOf at hl
    split at hl
    · rename_i ht
      obtain ⟨x, hx, rfl⟩ := Option.map_eq_some_iff.mp hl
      obtain ⟨x', hx', hsem⟩ := registry_valid hreg hk ht hv
      rw [hx] at hx'; cases hx'
      exact hsem
    · cases hl

/-- **AI-safety trace assurance from a raw signed archive** (instance of the generic
    flagship; sole hypothesis `NoForgery` plus registration). -/
theorem ai_archive_sound {ks : List DomainChecker} (hreg : Registered ks)
    (hk : traceChecker ∈ ks)
    {t : PCS.V2.Authority.AuthorityTranscript} {T : PCS.V2.EndToEnd.TrustAnchor}
    {signed : List UInt8 → Prop}
    (hB : PCS.V2.Signature.NoForgery PCS.V2.Ed25519.verify T.pk signed)
    {raw : ByteArray} {inp : PCS.V2.Package.PackageInput} {r : PCS.V2.EndToEnd.AcceptedResult}
    (h : acceptArchiveWithCheckers (registry ks) t T raw = some (inp, r))
    {cid : String} {g : Graph String TraceIR} {c : TraceClaim}
    (hd : domainAccepts aiAdapter r cid g = some c) :
    ∀ a ∈ c.traces, ∃ tr, artBytes r.table a = some tr ∧ TraceSafe tr c.budget c.forbidden :=
  ((pcs_generic_domain_archive_acceptance_sound_certified (registry ks) hB h aiAdapter
    (aiAdapter_sound hreg hk _) hd).2).holds

end PCS.V2.Witnesses.AISafety
