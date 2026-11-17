# Record of the runner forgery (kept as evidence, not for use)

| File | What it is |
| --- | --- |
| `claimcheck_kernel_runner_v1.withdrawn` | the stand-alone kernel runner as distributed until 2026-11-16 (`research/claimcheck_v1_1/claimcheck_kernel_runner.py` at commit `a09d9ab9` and earlier; served by the site draft), byte for byte, SHA-256 `8d9e07b4ac4b0abed13c9e750cbca113f1db26d82f3709579a7aafa7401f713f`. **Withdrawn. It is not a verification path:** it accepts proof files whose generated part was written by hand. The file extension is removed on purpose; `../../runner/test_strict_tail.py` runs it only from a temporary copy, only on the forged file, to show the defect |
| `forged_tail.lean.txt` | the forged generated part: its own `Decoy` type and its own `run`, proved by `rfl`. Appended to the reviewed checker after the marker, the Lean kernel accepts it |
| `forgery_reproduction.json` | output of `../../runner/test_strict_tail.py --out` with the real Lean 4.28.0 kernel: plain Lean accepts the forged file, the withdrawn runner reports a match for it, the installed runner refuses it before asking Lean anything and accepts a genuine file |
| `forgery_reproduction_runner_831bbaba.json` | the same test, 2026-11-17, against the runner hardened after the independent security review (SHA-256 `831bbaba…`): the forgery is still refused before Lean is asked anything, the genuine file is accepted, 84 committed proof files parse, 1,551 of 1,569 single-character edits are refused. The record above, for the runner of 2026-11-16, is kept unchanged |

The correction is the installed runner (receipt schema v2), core commits `d5a36975` and `2de4f872`
on `tommaso-r-marena/festive-galileo-4a5m5k`. See `../RUNNER_TAIL_FORGERY.md`.
