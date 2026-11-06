# Scientific routing and retained model card

No new scientific-intake model has been trained or promoted. Imported projects, uploaded Aristotle archives and evaluation cases are not training inputs.

The scientific planner is deterministic and budgeted. It chooses supported, source-bound checks before costly Lean checks; it cannot change checker semantics. Unknown meanings and unsupported formats go to review. The requested learned mode explicitly falls back and records its reason.

Native-domain diagnostics retain the actual trained Proof-JEPA `proof_guided-17` and Safety-JEPA `jepa_rl-17` checkpoints, graph representations, EMA target encoders, action-conditioned predictors and policy heads. Their exact checkpoint/training hashes appear in `routing.py` and retained diagnostic evidence. No pickle loader is used, model tensors are unchanged before/after diagnostics, and neural proposal origin is not independently attested.

Prior experiments did not outperform their strongest deterministic baselines. Proof-JEPA held-out deterministic search solved 5/10 tasks; neural seed results varied and provided no consistent advantage. Safety-JEPA's selected combined model completed 48/48 bounded tasks with two denials and 262 steps, versus the strong deterministic planner's 48/48, zero denials and 260 steps. Ordinary RL, transfer and proof-guided variants were unstable; the small real-Qwen pilot completed 0/6 tasks. These frozen results are not changed by this package.

Diagnostics here test model compatibility/loading and retained-domain behavior, not improved scientific reasoning, alignment, deception detection, universal safety or state-of-the-art open-model capability. The intake system does not infer from scientific embedding similarity. Its effective scientific route is deterministic, so there is no independent model-selection, calibration or neural OOD improvement claim.

A useful next experiment requires expert-annotated scientific tasks with compatible representations, meaningful sequential choices and independently checked outcomes. The default should remain deterministic until held-out measurements establish an incremental learned benefit.
