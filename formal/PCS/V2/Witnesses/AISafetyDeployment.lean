import PCS.V2.ExternalWorld
import PCS.V2.Witnesses.AISafety

/-!
# AI-safety external-world bridge: committed trace ⟶ deployed execution

PCS proves the bounded trace invariant about the **committed** trace bytes.  To say
anything about the **deployed / evaluated execution**, an explicit premise is required: the
committed episode logs faithfully record the deployed episodes (`FaithfulLog`).  Only then
may the property be transported (`aiBridge.transport`).

`committed_safe_deployed_unsafe` shows that the premise cannot be dropped: the committed
world satisfies the golden claim while a deployed run that actually took the forbidden
action violates it; PCS acceptance, a function of the committed bytes only, cannot tell the
two apart.
-/

set_option autoImplicit false

namespace PCS.V2.Witnesses.AISafety

open PCS PCS.V2.Json PCS.V2.DomainAdapter PCS.V2.Witnesses

/-- The deployed / evaluated execution: the action sequence the deployed agent actually
    executed in each episode. -/
structure DeployedRun where
  episode : String → Option (List UInt8)

/-- Data-adequacy premise: every committed episode log is the exact action sequence of
    the corresponding deployed episode. -/
def FaithfulLog (w : List (String × ByteArray)) (ew : DeployedRun) : Prop :=
  ∀ a tr, artBytes w a = some tr → ew.episode a = some tr

/-- The external reading of a trace claim: the deployed episodes are safe. -/
def DeployedSafe (ew : DeployedRun) (c : TraceClaim) : Prop :=
  ∀ a ∈ c.traces, ∃ tr, ew.episode a = some tr ∧ TraceSafe tr c.budget c.forbidden

/-- The AI-safety bridge. -/
def aiBridge : ExternalWorldBridge aiDomain :=
  { ExternalWorld := DeployedRun, ExternalHolds := DeployedSafe, Corresponds := FaithfulLog,
    transport := by
      intro w ew c hcorr hw a ha
      obtain ⟨tr, htr, hs⟩ := hw a ha
      exact ⟨tr, hcorr a tr htr, hs⟩ }

/-- The committed world of the golden fixture (artifact id `trace`). -/
def goldenWorld : List (String × ByteArray) := [("trace", ⟨#[0, 1, 2, 4, 1, 8]⟩)]

def goldenClaim : TraceClaim := ⟨["trace"], 4, 7⟩

/-- A deployed run whose episode `trace` actually took the forbidden action 7. -/
def unsafeRun : DeployedRun := { episode := fun _ => some [0, 7] }

/-- **The correspondence premise is necessary.**  The committed world satisfies the claim,
    the unfaithfully logged deployed run violates it, and that run does not correspond to the
    committed world. -/
theorem committed_safe_deployed_unsafe :
    aiDomain.Holds goldenWorld goldenClaim ∧ ¬ DeployedSafe unsafeRun goldenClaim ∧
      ¬ FaithfulLog goldenWorld unsafeRun := by
  refine ⟨?_, ?_, ?_⟩
  · intro a ha
    simp only [goldenClaim, List.mem_singleton] at ha
    subst ha
    exact ⟨[0, 1, 2, 4, 1, 8], by decide, by decide, by decide⟩
  · intro h
    obtain ⟨tr, htr, hs⟩ := h "trace" (by simp [goldenClaim])
    simp only [unsafeRun, Option.some.injEq] at htr
    subst htr
    exact hs.1 7 (by decide) rfl
  · intro h
    have := h "trace" [0, 1, 2, 4, 1, 8] (by decide)
    simp [unsafeRun] at this

end PCS.V2.Witnesses.AISafety
