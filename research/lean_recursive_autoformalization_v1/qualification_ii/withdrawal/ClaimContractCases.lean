import ClaimContract

namespace PCSResearch.ClaimContract.Cases

def causal : Scope := ⟨⟨"toy-risk-study", .causal "two-binary-SCMs" "randomized" "risk1>risk0"⟩, 1⟩
def policy : Scope := ⟨⟨"toy-action", .policy "approval-required" "write-record" "approved"⟩, 1⟩
def mathRef : Scope := ⟨⟨"toy-math", .mathReference "p" "not-not-p"⟩, 1⟩

def matrix (q : Scope) (agrees : Bool → Bool → Bool) (holds : Bool → Bool) : Evidence Bool Bool :=
  ⟨q, [false, true], [false, true], agrees, holds⟩

def run (e : Evidence Bool Bool) : Receipt := receive e.scope (.reviewed e.scope.subject) (some e)

/-- Hypothesis w chooses treatment risk 3/4 or 1/4 against control risk 2/4.
Both groups in this synthetic table favor the higher-risk hypothesis. -/
def risk := matrix causal (fun w _ => w) (fun w => decide (2 < if w then 3 else 1))
def approved := matrix policy (fun w _ => w) id
def denied := matrix policy (fun w _ => !w) id
def doubleNeg := matrix mathRef (fun _ _ => true) (fun w => !(!w) == w)

example : (run risk).display = (causal, "SUPPORTED_UNDER_CAUSAL_MODEL") := by decide
example : (run approved).display = (policy, "SATISFIES_SUPPLIED_POLICY") := by decide
example : (run denied).display = (policy, "VIOLATES_SUPPLIED_POLICY") := by decide
example : (run doubleNeg).display = (mathRef, "AGREES_WITH_FORMAL_REFERENCE") := by decide

-- A single counterinterpretation can defeat support without establishing refutation.
example : (run (matrix policy (fun w g => w || g) id)).decision = .insufficient := by decide
example : (run (matrix policy (fun _ _ => false) id)).decision = .inconsistent := by decide
example : (run { risk with groups := [true, true] }).decision = .invalidEvidence := by decide
example : (run { risk with scope.withdrawalBudget := 3 }).decision = .invalidEvidence := by decide
example : (receive causal .unparsed (some risk)).decision = .unparsed := by decide
example : (receive causal .ambiguous (some risk)).decision = .ambiguous := by decide
example : (receive causal (.reviewed causal.subject) (none : Option (Evidence Bool Bool))).decision =
    .insufficient := by decide
example : (receive causal (.reviewed policy.subject) (some risk)).decision = .bindingMismatch := by decide
example : (receive policy (.reviewed policy.subject) (some risk)).decision = .bindingMismatch := by decide
example : (receive mathRef (.reviewed mathRef.subject)
    (some { doubleNeg with scope.subject.source := "other-text" })).decision = .bindingMismatch := by decide
example : (receive causal (.reviewed causal.subject)
    (some { risk with scope.withdrawalBudget := 0 })).decision = .bindingMismatch := by decide

/-- Independent two-world/two-group oracle. Enumerate the four masks directly
and pool the surviving polarities. Never call the library's cost or check. -/
def byMasks (e : Evidence Bool Bool) : Decision := Id.run do
  let bits := [false, true]
  let base := bits.any fun w => e.agrees w false && e.agrees w true
  if !base then return .inconsistent
  let live := bits.filter fun w => bits.any fun a => bits.any fun b =>
    decide (a.toNat + b.toNat ≤ e.scope.withdrawalBudget) &&
    (a || e.agrees w false) && (b || e.agrees w true)
  if live.all e.holds then return .decided true
  if live.all (fun w => !(e.holds w)) then return .decided false
  return .insufficient

def bit (x : Nat) (i : Nat) : Bool := (x / (2^i)) % 2 == 1

def agreesOnAll : Bool := (List.range 64).all fun code => (List.range 3).all fun k =>
  let q := { mathRef with withdrawalBudget := k }
  let e := matrix q (fun w g => bit code (2 * w.toNat + g.toNat)) (fun w => bit code (4 + w.toNat))
  (run e).decision == byMasks e

set_option maxRecDepth 10000 in
set_option maxHeartbeats 2000000 in
example : agreesOnAll = true := by decide

#eval [run risk, run approved, run denied, run doubleNeg].map Receipt.display

end PCSResearch.ClaimContract.Cases
