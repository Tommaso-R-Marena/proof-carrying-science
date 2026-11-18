/-
Instrumental-variable graph: Z → X → Y with U → X, U → Y (no Z→Y).

Graphical IV side-conditions for this concrete instance.
-/
namespace PcsPccr.InstrumentInd

inductive Node where
  | U | Z | X | Y
  deriving DecidableEq, Repr, Inhabited

def Parent : Node → Node → Prop
  | .Z, .X => True
  | .X, .Y => True
  | .U, .X => True
  | .U, .Y => True
  | _, _ => False

instance (a b : Node) : Decidable (Parent a b) :=
  match a, b with
  | .Z, .X | .X, .Y | .U, .X | .U, .Y => isTrue trivial
  | .U, .U | .U, .Z | .Z, .Z | .Z, .U | .Z, .Y | .X, .X | .X, .U | .X, .Z
  | .Y, .Y | .Y, .U | .Y, .Z | .Y, .X =>
      isFalse (by intro h; exact False.elim h)

theorem parent_Z_X : Parent .Z .X := trivial
theorem parent_X_Y : Parent .X .Y := trivial
theorem parent_U_X : Parent .U .X := trivial
theorem parent_U_Y : Parent .U .Y := trivial

/-- Exclusion: no direct Z→Y. -/
theorem exclusion_no_Z_Y : ¬ Parent .Z .Y := by
  intro h; exact False.elim h

/-- Relevance: Z parents X. -/
theorem relevance_Z_to_X : Parent .Z .X := parent_Z_X

/-- After do(X): drop edges into X. -/
def ParentAfterDoX : Node → Node → Prop
  | .X, .Y => True
  | .U, .Y => True
  | _, _ => False

theorem doX_drops_Z_to_X : ¬ ParentAfterDoX .Z .X := by
  intro h; exact False.elim h

theorem doX_drops_U_to_X : ¬ ParentAfterDoX .U .X := by
  intro h; exact False.elim h

theorem doX_keeps_X_to_Y : ParentAfterDoX .X .Y := trivial

/-- In G_underline{X}, Z has no outgoing edges (Z only parented X). -/
theorem Z_childless_after_doX {b : Node} (h : ParentAfterDoX .Z b) : False := by
  cases b <;> exact False.elim h

/-- Exogeneity lite: Z shares no edge with Y after mutilation. -/
theorem Z_not_parent_Y_after_doX : ¬ ParentAfterDoX .Z .Y := by
  intro h; exact False.elim h

structure InstrumentCert where
  relevance : Parent .Z .X
  exclusion : ¬ Parent .Z .Y
  z_childless_after_doX : ∀ b, ¬ ParentAfterDoX .Z b

def z_instrument_cert : InstrumentCert where
  relevance := relevance_Z_to_X
  exclusion := exclusion_no_Z_Y
  z_childless_after_doX := by
    intro b h
    exact Z_childless_after_doX h

theorem z_instrument_relevance : Parent .Z .X := z_instrument_cert.relevance
theorem z_instrument_exclusion : ¬ Parent .Z .Y := z_instrument_cert.exclusion

/-- U fails exclusion (direct U→Y), so U is not an instrument for X→Y. -/
theorem u_not_instrument_exclusion : Parent .U .Y := parent_U_Y

theorem u_has_edge_to_Y_after_doX : ParentAfterDoX .U .Y := trivial

end PcsPccr.InstrumentInd
