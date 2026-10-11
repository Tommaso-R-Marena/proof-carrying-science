# PCS sequential RL v1

Actor–critic uses actual multi-step Lean transitions and checker-derived terminal rewards. Three seeds each run twelve episodes in two generations, for 72 real episodes. Policies, values and all rewards/failed attempts are retained. Both generations update weights. No final solve-rate gain over supervised policies was measured; all BC checkpoints and stronger symbolic search remain available. This is sequential RL, not a one-step bandit, and it is not a demonstrated long-horizon scientific intelligence.

See [the consolidated execution report](PCS_OMEGA_FULL_INSTANTIATION_REPORT.md) and [exact artifacts](../research/lean-learning-v1/SHA256.json) for commands, measured results and boundaries.

## Expanded implementation v2

V2 ran 72 sequential episodes across the expanded twelve training tasks, three seeds and two generations. Actual RL parameter updates persist; final solve counts remain 4/6, 5/6, 5/6 before and after RL. The trained symbolic/bag baselines remain available. No long-horizon discovery or RL superiority is established.

See [v2 reproducible artifacts](../research/lean-learning-v2/SHA256.json).

## Checked mathematical reuse and verified feedback

Checked-reuse V1 adds 36 actual sequential actor-critic episodes (129 environment steps), across three seeds and two generations. All six runs changed weights; one seed improved solve count, one regressed, one stayed unchanged. No robust RL superiority is claimed. [Complete reports](PCS_CHECKED_REUSE_REPORT.md).

## October 11 induction and grounded abstraction update

See the [consolidated executable results and limitations](PCS_OMEGA_FULL_INSTANTIATION_REPORT.md#induction-grounded-abstraction-and-bridge-builder--october-11-2026) and [complete prospective experiment](../research/induction-abstraction-v2/REPORT.md). This supersedes earlier absence of implemented list/Nat induction, trainable binding graphs, independently checked state-derived lemma admission and sequential induction RL. It does not supersede the documented limits on unrestricted English, autonomous discovery or runtime refinement.

V2 executes 32 sequential actor–critic episodes across two seeds/two generations, up to ten actions, including 24 verified training proofs. Rewards derive from checker transitions and terminal immutable-goal verification. All generations solve 4/8 final tasks: real weight updates, no measured solve-rate improvement.
