# Pre-training Mathlib v4 environment clarification

This separately sealed overlay preserves the original22-task corpus, its protocol and its seal byte-for-byte. It adds Mathlib.Tactic to the common evaluation imports required by the already declared strong baseline and strengthens training/validation duplicate rejection before fitting. No benchmark result informed these changes. The original helper source is compressed for exact reproduction of the first source manifest.

The original source-only corpus remains under ../mathlib-v4. The approved source-level signatures were extracted under six imports; all search and baseline policies execute under the same seven-import environment in evaluation-environment.json. The extra import does not establish unseen mathematics or forbid transitive use of target Mathlib facts. Each experiment still needs actual exact receiver/policy/checkpoint/source/resource receipts and independent Lean proof replay.
