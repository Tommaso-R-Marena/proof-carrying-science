# Complete namespace in fresh replay

Protected run 38641886634 at source c8f88d650c16a06ec23e82c0cd14244fc4c1f558
again compiled all 68 conditional-runtime modules successfully. Subsequent fresh
replay failed before compiling its first certificate: Lean selected the temporary
PCSConditionalRuntime directory and could not find PyFront.olean there. Lean
selects a namespace directory before resolving its member files; a partial overlay
does not fall back to the second namespace directory for missing siblings.

The corrected receiver copies the complete, previously built conditional module
namespace and its root umbrella into its private directory. It deletes every
`.olean*` artifact for all six fresh targets before recompiling them sequentially.
Unchanged supporting imports retain byte inventories outside stable_contract;
they are not counted as newly compiled replay targets. Complete preceding build,
all six new elaborations, both false-source controls, all 673 axiom entries and
the source identity checks remain mandatory. Audit and negative-control processes
also receive the explicit configured memory cap.

A real-kernel regression reproduces the sparse-namespace missing-sibling failure.
The production helper then retains a qualified sibling and root umbrella, removes
all selected artifacts, and admits a newly compiled True definition where the
cached selected definition is False. This checks both sibling availability and
fresh-module precedence. It does not replace the protected complete-library run.

The external proof-carrying verification/AI-safety research is deferred at the
user's request. Its absence does not block Aristotle source qualification or merge.
