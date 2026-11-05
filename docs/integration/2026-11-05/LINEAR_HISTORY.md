# Protected integration with linear Git history

Both `main` rulesets require pull requests, current required CI, resolved review threads, no deletion/force pushes and linear history. Repository merge methods include merge commits, but the protected linear-history rule rejects them. The initial merge attempt was refused before any protected source changed. No repository rule, required check or bypass setting is changed by this repair.

The integration uses squash merges. Original PR commits remain in exact retained source histories:

| Repository | Qualified source commit | Annotated retention tag |
| --- | --- | --- |
| Core | `0b521f39af99f5856b69dfcc25bc274ec9dc804a` | `pcs-source-intake/core-open-prs-v1-20261105` |
| Website | `d35e2b5e6b29e0a27dc0cb117986895fd58c1456` | `pcs-source-intake/site-open-prs-v1-20261105` |

The checker requires each tag to resolve to its exact compiled-in commit ID and every original PR head to be an ancestor of that retained commit. Protected baseline ancestry remains required in both the retained intake and current history. Every non-control source path, Git blob and file mode must match the qualified intake. This includes all scientific/model implementations, proof artifacts, experiments, fixtures, dependencies and history evidence. Added, missing, substituted or mode-changed source fails. The working tree must be clean.

Only a fixed list of integration controls may differ: this checker and its tests, source-review configuration, the relevant read-only CI entry point and integration documentation. Each must be a tracked regular file. These are reviewed trusted configuration, not caller-supplied profiles. Core V22 additionally binds the complete current file census and exact source identities, preserving the fully qualified V21 and older V20 manifests unchanged. Actual production acceptance, all Lean theorem files and the website public tree keep the earlier protected identities; the already-qualified transport helper remains the sole exact research receiver exception.

Twelve real Git fixture tests construct two divergent original source histories, retain their merge snapshot, then construct a one-parent squash on the protected baseline. They prove the source gate accepts that history shape only with exact retained sources. They also reject changed/added/missing source, changed modes, retargeted or missing tags, unrelated original heads, dirty or missing controls, untracked files and history unrelated to the protected baseline. No Lean verdict is mocked. A thirteenth test constructs a real one-parent squash of the entire current repository in an isolated Git/index view and runs the actual source checker there; core also requires the complete committed V22 census to pass. It never changes a protected ref or working file. Both CI entry points run all 13 tests, and website main pushes rerun the reconciliation gate.

Squashed main history is not original-commit ancestry. The original ancestry is preserved in the retained source snapshots and checked there. Tags, hashes and Git are not an independently administered immutable root; host/Git/CI configuration remains trusted. The record establishes source provenance and integration policy compliance, not semantic equivalence, universal runtime correctness, mathematical authority or scientific validity. Actual merge state and current CI are recorded on core PR198 and website PR148.
