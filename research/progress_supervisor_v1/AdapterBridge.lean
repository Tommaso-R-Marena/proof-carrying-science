import Adapter
import Data
set_option autoImplicit false
/-! Concrete bridge to the exact generated workflow model, not a generic adapter
    registration or an assertion about arbitrary tools. -/
namespace PCSProgressAdapterBridge
open PCSProgressAdapter

theorem edges_declared {s a t : Nat} (h : Edge s a t) :
    (⟨s,a,t⟩ : PCSActionShield.Edge) ∈ PCSProgressData.spec.base.edges ∧
    (s,a) ∈ PCSProgressData.spec.base.allowed := by
  simp only [Edge, List.mem_cons, List.not_mem_nil, or_false, Prod.mk.injEq] at h
  rcases h with ⟨rfl,rfl,rfl⟩ | ⟨rfl,rfl,rfl⟩ |
    ⟨rfl,rfl,rfl⟩ | ⟨rfl,rfl,rfl⟩ | ⟨rfl,rfl,rfl⟩ <;> decide

theorem step_declared {s a t : Nat} {r out : Rows}
    (hv : Valid s r) (hs : step s a r = some (t,out)) :
    (⟨s,a,t⟩ : PCSActionShield.Edge) ∈ PCSProgressData.spec.base.edges ∧
    (s,a) ∈ PCSProgressData.spec.base.allowed ∧ Valid t out := by
  have h := step_refines hv hs
  have e := edges_declared h.2.1
  exact ⟨e.1,e.2,h.1⟩

/-- Every abstract adapter execution is an existing PCS certified path. -/
theorem execution_path {s t n : Nat} {r out : Rows}
    (hv : Valid s r) (he : Execution s r n t out) :
    PCSProgress.Path PCSProgressData.spec n s t := by
  induction he with
  | nil s r => exact .nil s
  | cons a head tail ih =>
    have h := step_declared hv head
    exact .cons ⟨_,a,_⟩ rfl h.1 h.2.1 (ih h.2.2)
end PCSProgressAdapterBridge
