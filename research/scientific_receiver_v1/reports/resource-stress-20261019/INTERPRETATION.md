# Bounded operands and large intermediate rationals

This targeted resource falsification attempt observed 11 actual accepts and two expected rejects in 13 fresh, sequential Lean `--run` processes. The measured phase took 33.060453931 seconds within a 120-second global deadline. No timeout, result disagreement, byte-echo disagreement or unexpected exit occurred.

The positive cases use n=0,8,16,32,64 and both physical/algebraic modes. For m=n/2, the initial state is (m,0). The first m firings are 1/d_i; the remaining m firings are (d_i−1)/d_i. The deterministic denominators descend from 10^18 and are selected by pairwise gcd=1, without a primality assumption. All wire operands satisfy the unchanged bound. Every positive final state is exactly (0,m), so the environment, total and singleton final-A enclosure are bounded and consistent.

The independently replayed maximum intermediate denominator lengths were 1,72,144,288,576 decimal digits. The largest valid input was only 1,973 bytes. The 64-step physical case was actually accepted with the 576-digit intermediate denominator; its fresh-process observation took 2.701773180 seconds. The corresponding algebraic observation took 2.570507156 seconds.

The n=0 observations took 2.462697388 and 2.333227538 seconds. Every timing includes startup, Main elaboration, IO, receiving and harness response parsing. OS filesystem/page caches were not cleared, cases ran in fixed order, and each case was observed once. The differences therefore do not isolate receiver CPU cost, establish a scaling law, or provide a statistical performance estimate. This experiment did not falsify successful handling of these particular bounded inputs; it does not establish a hard resource bound over all accepted submissions or deployment environments.

The wrong-environment control still submitted bounded env=1 and an internally matching singleton enclosure [1,1], while the actual final A remained0; actual receiving rejected it. A schedule with intermediate A=−1 and eventual A=0 accepted under algebraic scope and rejected under physical scope, as independently expected.

`plan.json` and `inputs.json` were written before the first actual process. `stress.json` preserves every exact response and independent result; `process-outputs.jsonl` preserves exact stdout/stderr bytes, exit codes and elapsed times, including failures or partial output if any had occurred. `progress.json` retains the final checkpoint. The actual pinned Lean executable used the unchanged Main source and the coordinating process's qualified-v3 environment, with its fresh receiving modules first in `LEAN_PATH`. The plan records the executable, Main, environment-file and experiment-source hashes. No fake checker, source generation or training was used. Earlier campaign/pilot artifacts were left unchanged.

Optional reproduction from the repository root:

```bash
python -m research.scientific_receiver_v1.stress \
  --checker /absolute/pinned/lean \
  --checker-arg=--run \
  --checker-arg=/absolute/receiver/formal/Main.lean \
  --checker-cwd /absolute/receiver/formal \
  --environment-json /absolute/qualified/environment.json \
  --out /fresh/output/directory --budget-seconds 120
```

This is a finite computational resource observation using compiled IR through the Lean interpreter. It grants no standalone-native benchmark, compiler/IO/OS correspondence, independently protected execution root, empirical chemistry/physiology, clinical safety, broad scientific acceptance or production authority.
