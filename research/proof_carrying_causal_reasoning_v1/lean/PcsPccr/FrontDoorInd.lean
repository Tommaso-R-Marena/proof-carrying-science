/-
Inductive front-door graph: X → M → Y with unobserved confounder U→X, U→Y.

Front-door mediator {M}:
  (i)   M intercepts the only directed path X→M→Y
  (ii)  no backdoor into M from X that starts with an arrow into X along X←U…
        (X has parents, but paths X←U→Y do not go through M as a backdoor to M;
         we prove the graphical side-conditions used by the specialized checker)
  (iii) X blocks backdoors from M to Y

This is a concrete finite instance, not a general front-door soundness theorem.
-/
namespace PcsPccr.FrontDoorInd

inductive Node where
  | U | X | M | Y
  deriving DecidableEq, Repr, Inhabited

def Parent : Node → Node → Prop
  | .U, .X => True
  | .U, .Y => True
  | .X, .M => True
  | .M, .Y => True
  | _, _ => False

instance (a b : Node) : Decidable (Parent a b) :=
  match a, b with
  | .U, .X | .U, .Y | .X, .M | .M, .Y => isTrue trivial
  | .U, .U | .U, .M | .X, .X | .X, .U | .X, .Y | .M, .M | .M, .U | .M, .X
  | .Y, .Y | .Y, .U | .Y, .X | .Y, .M =>
      isFalse (by intro h; exact False.elim h)

inductive Descendant : Node → Node → Prop where
  | refl : ∀ a, Descendant a a
  | step : ∀ {a b c}, Descendant a b → Parent b c → Descendant a c

theorem parent_X_M : Parent .X .M := trivial
theorem parent_M_Y : Parent .M .Y := trivial
theorem parent_U_X : Parent .U .X := trivial
theorem parent_U_Y : Parent .U .Y := trivial

theorem descendant_X_M : Descendant .X .M :=
  Descendant.step (Descendant.refl .X) parent_X_M

theorem descendant_X_Y : Descendant .X .Y :=
  Descendant.step descendant_X_M parent_M_Y

/-- (i) The unique length-2 directed path X→M→Y is intercepted by M. -/
theorem directed_path_X_M_Y : Parent .X .M ∧ Parent .M .Y :=
  ⟨parent_X_M, parent_M_Y⟩

/-- No direct edge X→Y (so the only directed route is through M). -/
theorem no_direct_X_Y : ¬ Parent .X .Y := by
  intro h; exact False.elim h

/-- M is not a parent of X (no arrow M→X). -/
theorem no_parent_M_X : ¬ Parent .M .X := by
  intro h; exact False.elim h

/-- (ii)-lite: there is no edge into M from U (U does not parent M). -/
theorem U_not_parent_of_M : ¬ Parent .U .M := by
  intro h; exact False.elim h

/-- (iii)-lite: the only parent of Y among {M,U} that is on the causal route
from M is M itself; X blocks the backdoor M←X←U→Y by conditioning on X
in the classical criterion — here we record that X is a parent of M and U
is a common cause of X and Y. -/
theorem X_parents_M : Parent .X .M := parent_X_M

theorem U_confounds_X_Y : Parent .U .X ∧ Parent .U .Y :=
  ⟨parent_U_X, parent_U_Y⟩

/-- Specialized front-door certificate payload for mediator {M}. -/
structure FrontDoorCert where
  intercepts : Parent .X .M ∧ Parent .M .Y
  no_direct : ¬ Parent .X .Y
  mediator_not_confounded_by_U_edge : ¬ Parent .U .M

def m_frontdoor_cert : FrontDoorCert where
  intercepts := directed_path_X_M_Y
  no_direct := no_direct_X_Y
  mediator_not_confounded_by_U_edge := U_not_parent_of_M

theorem m_frontdoor_intercepts : Parent .X .M ∧ Parent .M .Y :=
  m_frontdoor_cert.intercepts

theorem m_frontdoor_no_direct : ¬ Parent .X .Y :=
  m_frontdoor_cert.no_direct

theorem m_frontdoor_U_not_to_M : ¬ Parent .U .M :=
  m_frontdoor_cert.mediator_not_confounded_by_U_edge

end PcsPccr.FrontDoorInd
