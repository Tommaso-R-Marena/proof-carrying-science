/-
Do-calculus Rule 2 instance on the confounder fragment.

Rule 2 (informal): P(y | do(x), z) = P(y | x, z) when
  (Y ⊥ X | Z) in G_{\underline{X}} (delete arrows into X).

On Z→X, Z→Y, X→Y, after deleting Z→X, we have Z→Y and X→Y.
X and Y are NOT d-separated given Z in G_underline{X} because X→Y remains.
So Rule 2 does *not* apply for inserting/deleting do(X) given Z alone on Y —
the classical backdoor uses a different sequential argument.

We instead record the valid Rule-2-style fact for the *backdoor functional*:
after conditioning on Z, the remaining association X—Y in the mutilated graph
is exactly the causal edge, which is what the adjustment formula isolates.

Concrete proved facts:
  1. In G_underline{X}, Z→X is gone.
  2. In G_underline{X}, X→Y and Z→Y remain.
  3. Backdoor adjustment set {Z} has no proper descendants of X (imported).
-/
import PcsPccr.ConfounderInd
import PcsPccr.Mutilate

namespace PcsPccr.DoCalc
open PcsPccr.ConfounderInd
open PcsPccr.Mutilate

theorem rule2_context_Z_to_X_removed : ¬ ParentAfterDoX .Z .X :=
  doX_removes_Z_to_X

theorem rule2_context_causal_edge_remains : ParentAfterDoX .X .Y :=
  doX_keeps_X_to_Y

theorem rule2_context_confounder_to_Y_remains : ParentAfterDoX .Z .Y :=
  doX_keeps_Z_to_Y

/-- The backdoor set {Z} is valid on the original graph (imported). -/
theorem backdoor_Z_valid : SatisfiesBackdoor [.Z] :=
  Z_satisfies_backdoor

/-- Empty adjustment fails (imported). -/
theorem empty_backdoor_invalid : ¬ SatisfiesBackdoor [] :=
  empty_fails_backdoor

/-- Packaging: Rule-2 context + backdoor certificate for {Z}. -/
structure BackdoorDoCalcPack where
  zx_removed : ¬ ParentAfterDoX .Z .X
  xy_remains : ParentAfterDoX .X .Y
  zy_remains : ParentAfterDoX .Z .Y
  backdoor_ok : SatisfiesBackdoor [.Z]

def confounder_pack : BackdoorDoCalcPack where
  zx_removed := rule2_context_Z_to_X_removed
  xy_remains := rule2_context_causal_edge_remains
  zy_remains := rule2_context_confounder_to_Y_remains
  backdoor_ok := backdoor_Z_valid

theorem confounder_pack_zx : ¬ ParentAfterDoX .Z .X := confounder_pack.zx_removed
theorem confounder_pack_backdoor : SatisfiesBackdoor [.Z] := confounder_pack.backdoor_ok

end PcsPccr.DoCalc
