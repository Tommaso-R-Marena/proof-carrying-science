import PcsPccr.Basic

namespace PcsPccr

theorem collider_no_edge_X_to_Y :
    colliderGraph.hasEdge "X" "Y" = false := by
  native_decide

theorem collider_C_is_child_of_X :
    (colliderGraph.children "X").contains "C" = true := by
  native_decide

theorem collider_C_is_child_of_Y :
    (colliderGraph.children "Y").contains "C" = true := by
  native_decide

/-- C is not a descendant of X along a causal path to Y; C is a child, not Y. -/
theorem collider_Y_not_descendant_of_X :
    colliderGraph.isDescendant "X" "Y" = false := by
  native_decide

theorem collider_adjust_empty_ok :
    noDescendantsOfTreatment colliderGraph "X" [] = true := by
  native_decide

/-- Adjusting for collider C is not forbidden by the descendant rule (C is a
child of X, hence a descendant) — and that is exactly why it is the wrong
adjustment for total-effect queries when C lies downstream. -/
theorem collider_C_is_descendant_of_X :
    colliderGraph.isDescendant "X" "C" = true := by
  native_decide

theorem collider_adjust_C_forbidden_as_descendant :
    noDescendantsOfTreatment colliderGraph "X" ["C"] = false := by
  native_decide

end PcsPccr
