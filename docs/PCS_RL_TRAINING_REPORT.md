# PCS sequential RL v1

Actor–critic uses actual multi-step Lean transitions and checker-derived terminal rewards. Three seeds each run twelve episodes in two generations, for 72 real episodes. Policies, values and all rewards/failed attempts are retained. Both generations update weights. No final solve-rate gain over supervised policies was measured; all BC checkpoints and stronger symbolic search remain available. This is sequential RL, not a one-step bandit, and it is not a demonstrated long-horizon scientific intelligence.

See [the consolidated execution report](PCS_OMEGA_FULL_INSTANTIATION_REPORT.md) and [exact artifacts](../research/lean-learning-v1/SHA256.json) for commands, measured results and boundaries.
