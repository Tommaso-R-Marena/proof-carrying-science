# Measured costs and supported resource domain

These are finite observations, not asymptotic or speedup claims. The benchmark
manifest was frozen before execution. Cold means no mathematical-verdict cache;
it does not mean flushing the operating system's file cache.

| Retained events | Actual scientific checks including genesis | Observed cold replay |
| --- | --- | --- |
|0|1|3.414s|
|1|2|6.107s|
|8|9|28.396s|
|32|33|86.468s|

The partial research fixture profile was used for these measurements. Maximum
observed single-child peak RSS was2,924,608KiB; this is not total multi-process
memory. Authentication-only replay of32events took0.0281s; that measurement
includes signatures, canonical decoding and chain checks rather than isolated
signature throughput. Reusing unsigned/untrusted cached verdicts is unsupported.
Progress can be streamed but interruption resumes by rechecking genesis.

The full-inventory separate-process demo additionally pinned19,878 dependency
paths and the selected scientific/auditor/witness/coordinator Python sources.
It admitted two artifacts, performed complete history audit, rejected false
science and reconstructed two witnessed records after producer rollback. Its
recorded per-admission durations include actual witness checking, local commit,
finalization, full local science replay and fresh checkpoint checks; they are
not isolated network latency. Exact values are in
`research/scientific_authority_v2/reports/full-profile-demo/demo.json`.
Per-call file hashing makes this profile materially slower. Profiles must not be
silently exchanged when comparing timing or replaying a historical root.

The complete17-test coordinator/process-crash suite took385.10s. Per-case matrix
durations exclude fixture setup; the suite duration includes it. The17-test
historical audit suite took28.738s. The witness25unique cases were qualified as
24serial70.816s plus one race8.347s; its later full-checkpoint evidence delta has
a separate7.792s actual-server check. These overlap conceptually and must not be
summed as independent statistical samples. No aggregate throughput, networked
multi-host scalability, isolated SQLite fsync latency or power-failure metric is
claimed.

## Enforced limits

The history auditor supports at most32events,8,192bytes per artifact,
262,144aggregate scientific bytes and1,048,576aggregate envelope bytes.
Envelope size is capped at40,000bytes; event/genesis IDs at256bytes. Canonical
scientifically accepted wire length is further bounded by the predecessor Lean
codec theorem. Unsupported roots/policies/checkers/rotations reject.

The witness caps its SQLite database at16MiB, signed responses at4MiB, nested JSON
depth at32, and event count at32. It checks staged page/event/aggregate/export
budgets before COMMIT, so a returned record is not knowingly unexportable under
those limits. The serial server has five-second absolute header/body acquisition
and TLS-handshake deadlines. This bounds the measured acquisition stall, not
general availability under authenticated expensive work, disk stalls or load.

Whole-audit elapsed limits are acceptance deadlines checked around real verifier
calls. File-pin IO and OS scheduling are outside the child process deadline;
there is no hard preemptive total wall-clock guarantee. V1 SQLite snapshot loading
first applies its coarser1,024-event/64MiB envelope budget, then V2's stricter
domain before scientific launches. No claim is made that every maximum-size
history completes within the default budget on every machine/full pin profile.
