import PcsPccr.Basic

namespace PcsPccr

theorem confounder_Z_not_descendant_of_X :
    confounderGraph.isDescendant "X" "Z" = false := by
  native_decide

theorem confounder_Y_is_descendant_of_X :
    confounderGraph.isDescendant "X" "Y" = true := by
  native_decide

theorem confounder_adjust_Z_no_descendant :
    noDescendantsOfTreatment confounderGraph "X" ["Z"] = true := by
  native_decide

theorem confounder_adjust_Y_has_descendant :
    noDescendantsOfTreatment confounderGraph "X" ["Y"] = false := by
  native_decide

theorem confounder_has_backdoor_edge_into_X :
    confounderGraph.hasEdge "Z" "X" = true := by
  native_decide

theorem mediation_M_is_descendant_of_X :
    mediationGraph.isDescendant "X" "M" = true := by
  native_decide

theorem mediation_adjust_M_forbidden :
    noDescendantsOfTreatment mediationGraph "X" ["M"] = false := by
  native_decide

theorem mediation_adjust_empty_ok :
    noDescendantsOfTreatment mediationGraph "X" [] = true := by
  native_decide

end PcsPccr
