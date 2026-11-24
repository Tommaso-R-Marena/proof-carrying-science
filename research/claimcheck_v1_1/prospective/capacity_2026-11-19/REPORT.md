# Kernel resource feasibility study (feasibility study part C): consolidated report

Generated from the logs in this directory by `capacity_run.py --report`; every number below is computed from them, none typed. Development and synthetic data only: no prospective paper, no model call. A development-set finding: it enters no criterion, and protocol draft 3 stays unapproved.

Machine: 4 CPUs, 15.7 GiB physical memory; Lean (version 4.28.0, x86_64-unknown-linux-gnu, commit 7e01a1bf5c70fc6167d49c345d3bf80596e9a79b, Release). Every process started from this session's shell shares one memory cgroup limit of 13.35 GiB (14,338,756,608 bytes); the machine has no swap in that domain.

Outcomes. Every run has exactly one label, taken from its own kernel record: *accepted*; *memory guard stop* (the guard stopped Lean at its limit); *system kill* (the operating system killed Lean: the memory domain was exhausted, a property of the configuration and machine, not of the claim); *time limit* (900 s); *rejected (depth)* (Lean stopped at its maximum recursion depth, a limit of the checker); *rejected (other)*. Only *accepted* establishes anything; every other label leaves the claim UNKNOWN. Memory stops, system kills and time limits are the resource-related UNKNOWNs.

Record validation: **valid** (1284 documented runs; 19 development documents, each completed once; every synthetic case once; every run has its guard record; every further configuration ran each of its targets once, each rebuilt to the same obligation). Checks: no_malformed_run_record True, every_synthetic_case_once True, every_development_document_done_once True, every_run_has_a_guard_record True, further_configurations_complete True, valid True.

## A. Documented configuration (2 workers, 7 GiB per Lean process, 900 s, one claim per file)

### Synthetic tables

90 runs: accepted 66; memory guard stop 11; killed by the operating system 1; kernel rejection: Lean recursion-depth limit 12. Completed share 0.7333; resource-related UNKNOWN 12.

Seconds per claim over all runs, failures included: median 17.1, 95th percentile 51.824, maximum 64.073; kernel time 0.589 h. Largest peak: 7.01 GiB.

| Statistic | Runs | Accepted | Memory stop | System kill | Time limit | Rejected (depth) | Rejected (other) | Median s | 95th pct s | Max s | Max peak GiB |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| count | 15 | 15 | 0 | 0 | 0 | 0 | 0 | 9.82 | 42.961 | 42.961 | 4.88 |
| mean | 15 | 13 | 0 | 0 | 0 | 2 | 0 | 13.94 | 59.427 | 59.427 | 6.67 |
| median | 15 | 6 | 8 | 1 | 0 | 0 | 0 | 47.96 | 57.621 | 57.621 | 7.01 |
| min | 15 | 7 | 0 | 0 | 0 | 8 | 0 | 15.48 | 59.079 | 59.079 | 6.59 |
| pearson | 15 | 12 | 3 | 0 | 0 | 0 | 0 | 23.51 | 51.824 | 51.824 | 7.01 |
| sd_sample | 15 | 13 | 0 | 0 | 0 | 2 | 0 | 16.47 | 64.073 | 64.073 | 6.7 |

Every run that did not complete (24):

| Statistic | Table bytes | Rows / document | Outcome | Seconds | Peak GiB |
| --- | ---: | --- | --- | ---: | ---: |
| mean | 51209 | 2400 | kernel rejection: Lean recursion-depth limit | 48.513 | 5.78 |
| mean | 59952 | 2800 | kernel rejection: Lean recursion-depth limit | 59.427 | 6.67 |
| median | 12377 | 600 | memory guard stop | 47.96 | 7.0 |
| median | 14451 | 700 | memory guard stop | 49.354 | 7.01 |
| median | 16523 | 800 | memory guard stop | 49.323 | 7.0 |
| median | 20689 | 1000 | memory guard stop | 48.926 | 7.0 |
| median | 25048 | 1200 | memory guard stop | 47.334 | 7.0 |
| median | 33760 | 1600 | memory guard stop | 47.333 | 7.0 |
| median | 42487 | 2000 | memory guard stop | 48.882 | 7.0 |
| median | 51209 | 2400 | memory guard stop | 50.153 | 7.01 |
| median | 59952 | 2800 | killed by the operating system | 57.621 | 6.95 |
| min | 14451 | 700 | kernel rejection: Lean recursion-depth limit | 15.481 | 2.05 |
| min | 16523 | 800 | kernel rejection: Lean recursion-depth limit | 16.51 | 2.26 |
| min | 20689 | 1000 | kernel rejection: Lean recursion-depth limit | 20.569 | 2.68 |
| min | 25048 | 1200 | kernel rejection: Lean recursion-depth limit | 23.503 | 3.12 |
| min | 33760 | 1600 | kernel rejection: Lean recursion-depth limit | 31.188 | 4.02 |
| min | 42487 | 2000 | kernel rejection: Lean recursion-depth limit | 40.344 | 4.9 |
| min | 51209 | 2400 | kernel rejection: Lean recursion-depth limit | 49.045 | 5.77 |
| min | 59952 | 2800 | kernel rejection: Lean recursion-depth limit | 59.079 | 6.59 |
| pearson | 42487 | 2000 | memory guard stop | 47.796 | 7.0 |
| pearson | 51209 | 2400 | memory guard stop | 50.416 | 7.01 |
| pearson | 59952 | 2800 | memory guard stop | 51.824 | 7.0 |
| sd_sample | 51209 | 2400 | kernel rejection: Lean recursion-depth limit | 48.445 | 5.78 |
| sd_sample | 59952 | 2800 | kernel rejection: Lean recursion-depth limit | 64.073 | 6.7 |

### Development claims

1194 runs: accepted 1147; memory guard stop 17; killed by the operating system 3; kernel rejection: Lean recursion-depth limit 27. Completed share 0.9606; resource-related UNKNOWN 20.

Seconds per claim over all runs, failures included: median 17.62, 95th percentile 25.397, maximum 178.221; kernel time 5.336 h. Largest peak: 7.01 GiB.

| Statistic | Runs | Accepted | Memory stop | System kill | Time limit | Rejected (depth) | Rejected (other) | Median s | 95th pct s | Max s | Max peak GiB |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| count | 326 | 326 | 0 | 0 | 0 | 0 | 0 | 15.4 | 22.27 | 24.038 | 2.92 |
| max | 76 | 61 | 0 | 0 | 0 | 15 | 0 | 17.64 | 25.442 | 26.087 | 3.14 |
| mean | 123 | 123 | 0 | 0 | 0 | 0 | 0 | 18.0 | 23.876 | 25.132 | 3.06 |
| median | 54 | 34 | 17 | 3 | 0 | 0 | 0 | 26.67 | 99.715 | 178.221 | 7.01 |
| min | 80 | 68 | 0 | 0 | 0 | 12 | 0 | 18.0 | 24.121 | 25.334 | 3.03 |
| ols_intercept | 2 | 2 | 0 | 0 | 0 | 0 | 0 | 19.37 | 19.658 | 19.658 | 2.53 |
| ols_slope | 2 | 2 | 0 | 0 | 0 | 0 | 0 | 19.67 | 20.004 | 20.004 | 2.53 |
| pearson | 4 | 4 | 0 | 0 | 0 | 0 | 0 | 22.47 | 25.474 | 25.474 | 3.19 |
| sd_pop | 195 | 195 | 0 | 0 | 0 | 0 | 0 | 17.82 | 25.397 | 26.596 | 3.15 |
| sd_sample | 195 | 195 | 0 | 0 | 0 | 0 | 0 | 17.84 | 25.473 | 27.047 | 3.15 |
| sem | 92 | 92 | 0 | 0 | 0 | 0 | 0 | 17.51 | 24.58 | 25.654 | 3.11 |
| share | 20 | 20 | 0 | 0 | 0 | 0 | 0 | 7.35 | 7.645 | 7.715 | 1.2 |
| sum | 25 | 25 | 0 | 0 | 0 | 0 | 0 | 6.39 | 18.018 | 18.164 | 2.48 |

Every run that did not complete (47):

| Statistic | Table bytes | Rows / document | Outcome | Seconds | Peak GiB |
| --- | ---: | --- | --- | ---: | ---: |
| max | 26444 | 10_pmc5817150:mutated | kernel rejection: Lean recursion-depth limit | 20.627 | 2.67 |
| max | 26444 | 10_pmc5817150:mutated | kernel rejection: Lean recursion-depth limit | 20.391 | 2.67 |
| max | 26444 | 10_pmc5817150:mutated | kernel rejection: Lean recursion-depth limit | 19.479 | 2.57 |
| max | 26444 | 10_pmc5817150:mutated | kernel rejection: Lean recursion-depth limit | 19.89 | 2.56 |
| max | 26444 | 10_pmc5817150:mutated | kernel rejection: Lean recursion-depth limit | 19.682 | 2.57 |
| max | 26444 | 10_pmc5817150:mutated | kernel rejection: Lean recursion-depth limit | 19.621 | 2.57 |
| max | 26444 | 10_pmc5817150:mutated | kernel rejection: Lean recursion-depth limit | 19.99 | 2.6 |
| max | 26444 | 10_pmc5817150:original | kernel rejection: Lean recursion-depth limit | 20.958 | 2.67 |
| max | 26444 | 10_pmc5817150:original | kernel rejection: Lean recursion-depth limit | 20.202 | 2.67 |
| max | 26444 | 10_pmc5817150:original | kernel rejection: Lean recursion-depth limit | 20.348 | 2.57 |
| max | 26444 | 10_pmc5817150:original | kernel rejection: Lean recursion-depth limit | 20.243 | 2.56 |
| max | 26444 | 10_pmc5817150:original | kernel rejection: Lean recursion-depth limit | 20.657 | 2.56 |
| max | 26444 | 10_pmc5817150:original | kernel rejection: Lean recursion-depth limit | 19.849 | 2.57 |
| max | 26444 | 10_pmc5817150:original | kernel rejection: Lean recursion-depth limit | 20.206 | 2.57 |
| max | 26444 | 10_pmc5817150:original | kernel rejection: Lean recursion-depth limit | 20.294 | 2.6 |
| median | 26444 | 10_pmc5817150:mutated | killed by the operating system | 178.221 | 6.97 |
| median | 26444 | 10_pmc5817150:mutated | killed by the operating system | 175.691 | 6.68 |
| median | 26444 | 10_pmc5817150:mutated | memory guard stop | 48.653 | 7.01 |
| median | 26444 | 10_pmc5817150:mutated | memory guard stop | 49.46 | 7.01 |
| median | 26444 | 10_pmc5817150:mutated | memory guard stop | 49.776 | 7.0 |
| median | 26444 | 10_pmc5817150:mutated | memory guard stop | 47.786 | 7.01 |
| median | 26444 | 10_pmc5817150:mutated | memory guard stop | 48.602 | 7.0 |
| median | 26444 | 10_pmc5817150:mutated | memory guard stop | 48.375 | 7.01 |
| median | 26444 | 10_pmc5817150:mutated | memory guard stop | 48.994 | 7.01 |
| median | 26444 | 10_pmc5817150:mutated | memory guard stop | 48.616 | 7.01 |
| median | 26444 | 10_pmc5817150:original | killed by the operating system | 97.865 | 6.97 |
| median | 26444 | 10_pmc5817150:original | memory guard stop | 99.715 | 7.0 |
| median | 26444 | 10_pmc5817150:original | memory guard stop | 50.809 | 7.01 |
| median | 26444 | 10_pmc5817150:original | memory guard stop | 50.238 | 7.01 |
| median | 26444 | 10_pmc5817150:original | memory guard stop | 51.172 | 7.0 |
| median | 26444 | 10_pmc5817150:original | memory guard stop | 49.904 | 7.01 |
| median | 26444 | 10_pmc5817150:original | memory guard stop | 49.736 | 7.0 |
| median | 26444 | 10_pmc5817150:original | memory guard stop | 50.121 | 7.01 |
| median | 26444 | 10_pmc5817150:original | memory guard stop | 50.723 | 7.01 |
| median | 26444 | 10_pmc5817150:original | memory guard stop | 51.268 | 7.01 |
| min | 26444 | 10_pmc5817150:mutated | kernel rejection: Lean recursion-depth limit | 21.407 | 2.73 |
| min | 26444 | 10_pmc5817150:mutated | kernel rejection: Lean recursion-depth limit | 20.122 | 2.62 |
| min | 26444 | 10_pmc5817150:mutated | kernel rejection: Lean recursion-depth limit | 19.883 | 2.62 |
| min | 26444 | 10_pmc5817150:mutated | kernel rejection: Lean recursion-depth limit | 19.47 | 2.62 |
| min | 26444 | 10_pmc5817150:mutated | kernel rejection: Lean recursion-depth limit | 19.721 | 2.62 |
| min | 26444 | 10_pmc5817150:mutated | kernel rejection: Lean recursion-depth limit | 20.08 | 2.65 |
| min | 26444 | 10_pmc5817150:original | kernel rejection: Lean recursion-depth limit | 21.522 | 2.73 |
| min | 26444 | 10_pmc5817150:original | kernel rejection: Lean recursion-depth limit | 20.187 | 2.62 |
| min | 26444 | 10_pmc5817150:original | kernel rejection: Lean recursion-depth limit | 20.446 | 2.62 |
| min | 26444 | 10_pmc5817150:original | kernel rejection: Lean recursion-depth limit | 20.274 | 2.62 |
| min | 26444 | 10_pmc5817150:original | kernel rejection: Lean recursion-depth limit | 21.53 | 2.62 |
| min | 26444 | 10_pmc5817150:original | kernel rejection: Lean recursion-depth limit | 21.146 | 2.65 |

### Development claims by paper (original and planted copy together)

| Paper | Table rows | Runs | Accepted | Memory stop | System kill | Time limit | Rejected (depth) | Rejected (other) | Median s | Max s | Max peak GiB |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 01_pmc6972591 | 246 | 290 | 290 | 0 | 0 | 0 | 0 | 0 | 17.63 | 28.223 | 3.3 |
| 03_pmc5551083 | 100 | 108 | 108 | 0 | 0 | 0 | 0 | 0 | 18.98 | 21.076 | 2.53 |
| 06_pmc5980576 | 351 | 188 | 188 | 0 | 0 | 0 | 0 | 0 | 23.72 | 27.047 | 3.15 |
| 08_pmc6238128 | 96 | 98 | 98 | 0 | 0 | 0 | 0 | 0 | 3.77 | 4.633 | 0.83 |
| 09_pmc6476783 | 193 | 164 | 164 | 0 | 0 | 0 | 0 | 0 | 5.8 | 8.512 | 1.32 |
| 10_pmc5817150 | 617 | 122 | 75 | 17 | 3 | 0 | 27 | 0 | 20.37 | 178.221 | 7.01 |
| 12_pmc4417136 | 168 | 131 | 131 | 0 | 0 | 0 | 0 | 0 | 8.11 | 8.868 | 1.32 |
| 17_pmc9309151 | 332 | 93 | 93 | 0 | 0 | 0 | 0 | 0 | 17.56 | 23.758 | 3.08 |

### Interrupted by the infrastructure (not a kernel result)

The session's 2-hour background limit stopped the first development invocation. The document in progress was re-run from the start; the driver records above are the complete re-run. The interrupted attempt's guard records are kept: 33 finished runs with no driver record and 2 run(s) started and never finished. They are excluded from the tables above because the same claims were re-run to completion, and listed here so that nothing is dropped silently.

### C7 on the development claims (documented configuration)

* Within the candidate supported size: 991 runs, completed share 1.0, median 17.38 s, 95th percentile 24.482 s, largest peak 3.19 GiB, memory stops 0, system kills 0, depth rejections 0; C7's limits hold: True.
* Outside it: 203 runs, completed share 0.7685, median 20.19 s, 95th percentile 49.904 s, largest peak 7.01 GiB, memory stops 17, system kills 3, depth rejections 27; C7's limits hold: False.
* All development runs: 1194 runs, completed share 0.9606, median 17.62 s, 95th percentile 25.397 s, largest peak 7.01 GiB, memory stops 17, system kills 3, depth rejections 27; C7's limits hold: True.

## B. Isolated reruns (1 worker, 7 GiB): every obligation the operating system killed

| Statistic | Table bytes | Documented runs (outcome) | Same obligation | Rerun outcome | Seconds | Peak GiB |
| --- | ---: | --- | --- | --- | ---: | ---: |
| median | 26444 | 10_pmc5817150:original: killed by the operating system; 10_pmc5817150:mutated: killed by the operating system | True | memory guard stop | 62.397 | 7.0 |
| median | 26444 | 10_pmc5817150:mutated: killed by the operating system | True | memory guard stop | 45.505 | 7.0 |
| median | 59952 | synthetic: killed by the operating system | True | memory guard stop | 47.42 | 7.01 |

## C. Safer configuration (2 workers, 6 GiB per Lean process)

The proposed safer configuration: two workers at 6 GiB, on every obligation whose documented peak exceeded 5 GiB. Evaluated separately, with its own guard log; the documented results are unchanged.

30 obligations: accepted 3; memory guard stop 24; kernel rejection: Lean recursion-depth limit 3. Median 38.89 s, maximum 48.127 s, largest peak 6.04 GiB.

| Statistic | Table bytes | Rows / document | Documented outcome(s) | Documented s | Documented peak GiB | Outcome here | Seconds | Peak GiB |
| --- | ---: | --- | --- | ---: | ---: | --- | ---: | ---: |
| median | 26444 | 10_pmc5817150:mutated; 10_pmc5817150:original | memory guard stop | 50.238 | 7.01 | memory guard stop | 38.632 | 6.01 |
| median | 26444 | 10_pmc5817150:mutated; 10_pmc5817150:original | memory guard stop | 51.268 | 7.01 | memory guard stop | 38.886 | 6.0 |
| median | 26444 | 10_pmc5817150:mutated; 10_pmc5817150:original | killed by the operating system | 178.221 | 6.97 | memory guard stop | 38.558 | 6.01 |
| median | 26444 | 10_pmc5817150:mutated; 10_pmc5817150:original | memory guard stop | 51.172 | 7.0 | memory guard stop | 39.012 | 6.01 |
| median | 26444 | 10_pmc5817150:mutated; 10_pmc5817150:original | memory guard stop | 50.809 | 7.01 | memory guard stop | 38.222 | 6.0 |
| median | 26444 | 10_pmc5817150:mutated; 10_pmc5817150:original | memory guard stop | 49.904 | 7.01 | memory guard stop | 38.686 | 6.0 |
| median | 26444 | 10_pmc5817150:mutated; 10_pmc5817150:original | memory guard stop | 49.736 | 7.0 | memory guard stop | 38.847 | 6.01 |
| median | 26444 | 10_pmc5817150:mutated; 10_pmc5817150:original | killed by the operating system, memory guard stop | 175.691 | 7.0 | memory guard stop | 39.126 | 6.0 |
| mean | 42487 | 2000 | accepted | 40.554 | 5.06 | accepted | 40.155 | 5.05 |
| mean | 51209 | 2400 | kernel rejection: Lean recursion-depth limit | 48.513 | 5.78 | kernel rejection: Lean recursion-depth limit | 48.127 | 5.78 |
| mean | 59952 | 2800 | kernel rejection: Lean recursion-depth limit | 59.427 | 6.67 | memory guard stop | 39.935 | 6.02 |
| median | 10299 | 500 | accepted | 48.903 | 5.8 | accepted | 46.298 | 5.81 |
| median | 12377 | 600 | memory guard stop | 47.96 | 7.0 | memory guard stop | 37.734 | 6.0 |
| median | 14451 | 700 | memory guard stop | 49.354 | 7.01 | memory guard stop | 38.268 | 6.0 |
| median | 16523 | 800 | memory guard stop | 49.323 | 7.0 | memory guard stop | 37.528 | 6.01 |
| median | 20689 | 1000 | memory guard stop | 48.926 | 7.0 | memory guard stop | 38.233 | 6.01 |
| median | 25048 | 1200 | memory guard stop | 47.334 | 7.0 | memory guard stop | 38.394 | 6.01 |
| median | 33760 | 1600 | memory guard stop | 47.333 | 7.0 | memory guard stop | 38.691 | 6.0 |
| median | 42487 | 2000 | memory guard stop | 48.882 | 7.0 | memory guard stop | 38.888 | 6.0 |
| median | 51209 | 2400 | memory guard stop | 50.153 | 7.01 | memory guard stop | 40.444 | 6.01 |
| median | 59952 | 2800 | killed by the operating system | 57.621 | 6.95 | memory guard stop | 39.943 | 6.04 |
| min | 51209 | 2400 | kernel rejection: Lean recursion-depth limit | 49.045 | 5.77 | kernel rejection: Lean recursion-depth limit | 46.456 | 5.77 |
| min | 59952 | 2800 | kernel rejection: Lean recursion-depth limit | 59.079 | 6.59 | memory guard stop | 39.366 | 6.04 |
| pearson | 33760 | 1600 | accepted | 50.968 | 6.19 | memory guard stop | 37.955 | 6.01 |
| pearson | 42487 | 2000 | memory guard stop | 47.796 | 7.0 | memory guard stop | 38.41 | 6.0 |
| pearson | 51209 | 2400 | memory guard stop | 50.416 | 7.01 | memory guard stop | 38.781 | 6.0 |
| pearson | 59952 | 2800 | memory guard stop | 51.824 | 7.0 | memory guard stop | 40.157 | 6.04 |
| sd_sample | 42487 | 2000 | accepted | 43.965 | 5.42 | accepted | 42.41 | 5.42 |
| sd_sample | 51209 | 2400 | kernel rejection: Lean recursion-depth limit | 48.445 | 5.78 | kernel rejection: Lean recursion-depth limit | 47.433 | 5.78 |
| sd_sample | 59952 | 2800 | kernel rejection: Lean recursion-depth limit | 64.073 | 6.7 | memory guard stop | 39.614 | 6.03 |

Memory domain (rule fixed before these runs: analytic worst case and sampled working set both at least 1.0 GiB below the limit, and no system kill): worst case 12.204 GiB (workers x (limit + largest guard overshoot 40.6 MB) + 128 MB for the driver and guards) against a limit of 13.354 GiB; sampled working set at most 11.784 GiB (usage including reclaimable cache 11.871 GiB); system kills 0; OOM-kill counter change 0. Safe on this machine: **True**.

## D. Reduced concurrency (1 worker, 7 GiB per Lean process)

Reduced concurrency: one worker at the documented 7 GiB, on the same obligations. Evaluated separately, with its own guard log; the documented results are unchanged.

30 obligations: accepted 4; memory guard stop 20; kernel rejection: Lean recursion-depth limit 6. Median 45.09 s, maximum 55.212 s, largest peak 7.01 GiB.

| Statistic | Table bytes | Rows / document | Documented outcome(s) | Documented s | Documented peak GiB | Outcome here | Seconds | Peak GiB |
| --- | ---: | --- | --- | ---: | ---: | --- | ---: | ---: |
| median | 26444 | 10_pmc5817150:mutated; 10_pmc5817150:original | memory guard stop | 50.238 | 7.01 | memory guard stop | 44.835 | 7.0 |
| median | 26444 | 10_pmc5817150:mutated; 10_pmc5817150:original | memory guard stop | 51.268 | 7.01 | memory guard stop | 46.143 | 7.0 |
| median | 26444 | 10_pmc5817150:mutated; 10_pmc5817150:original | killed by the operating system | 178.221 | 6.97 | memory guard stop | 45.057 | 7.01 |
| median | 26444 | 10_pmc5817150:mutated; 10_pmc5817150:original | memory guard stop | 51.172 | 7.0 | memory guard stop | 44.397 | 7.0 |
| median | 26444 | 10_pmc5817150:mutated; 10_pmc5817150:original | memory guard stop | 50.809 | 7.01 | memory guard stop | 43.466 | 7.01 |
| median | 26444 | 10_pmc5817150:mutated; 10_pmc5817150:original | memory guard stop | 49.904 | 7.01 | memory guard stop | 43.791 | 7.0 |
| median | 26444 | 10_pmc5817150:mutated; 10_pmc5817150:original | memory guard stop | 49.736 | 7.0 | memory guard stop | 44.761 | 7.01 |
| median | 26444 | 10_pmc5817150:mutated; 10_pmc5817150:original | killed by the operating system, memory guard stop | 175.691 | 7.0 | memory guard stop | 44.507 | 7.0 |
| mean | 42487 | 2000 | accepted | 40.554 | 5.06 | accepted | 38.435 | 5.05 |
| mean | 51209 | 2400 | kernel rejection: Lean recursion-depth limit | 48.513 | 5.78 | kernel rejection: Lean recursion-depth limit | 45.886 | 5.78 |
| mean | 59952 | 2800 | kernel rejection: Lean recursion-depth limit | 59.427 | 6.67 | kernel rejection: Lean recursion-depth limit | 55.212 | 6.71 |
| median | 10299 | 500 | accepted | 48.903 | 5.8 | accepted | 46.691 | 5.8 |
| median | 12377 | 600 | memory guard stop | 47.96 | 7.0 | memory guard stop | 43.537 | 7.0 |
| median | 14451 | 700 | memory guard stop | 49.354 | 7.01 | memory guard stop | 44.78 | 7.01 |
| median | 16523 | 800 | memory guard stop | 49.323 | 7.0 | memory guard stop | 46.224 | 7.0 |
| median | 20689 | 1000 | memory guard stop | 48.926 | 7.0 | memory guard stop | 45.78 | 7.0 |
| median | 25048 | 1200 | memory guard stop | 47.334 | 7.0 | memory guard stop | 44.449 | 7.0 |
| median | 33760 | 1600 | memory guard stop | 47.333 | 7.0 | memory guard stop | 44.637 | 7.01 |
| median | 42487 | 2000 | memory guard stop | 48.882 | 7.0 | memory guard stop | 44.596 | 7.0 |
| median | 51209 | 2400 | memory guard stop | 50.153 | 7.01 | memory guard stop | 45.5 | 7.0 |
| median | 59952 | 2800 | killed by the operating system | 57.621 | 6.95 | memory guard stop | 45.975 | 7.0 |
| min | 51209 | 2400 | kernel rejection: Lean recursion-depth limit | 49.045 | 5.77 | kernel rejection: Lean recursion-depth limit | 46.685 | 5.77 |
| min | 59952 | 2800 | kernel rejection: Lean recursion-depth limit | 59.079 | 6.59 | kernel rejection: Lean recursion-depth limit | 54.283 | 6.7 |
| pearson | 33760 | 1600 | accepted | 50.968 | 6.19 | accepted | 48.25 | 6.19 |
| pearson | 42487 | 2000 | memory guard stop | 47.796 | 7.0 | memory guard stop | 45.021 | 7.01 |
| pearson | 51209 | 2400 | memory guard stop | 50.416 | 7.01 | memory guard stop | 45.116 | 7.01 |
| pearson | 59952 | 2800 | memory guard stop | 51.824 | 7.0 | memory guard stop | 46.148 | 7.0 |
| sd_sample | 42487 | 2000 | accepted | 43.965 | 5.42 | accepted | 41.438 | 5.42 |
| sd_sample | 51209 | 2400 | kernel rejection: Lean recursion-depth limit | 48.445 | 5.78 | kernel rejection: Lean recursion-depth limit | 45.22 | 5.78 |
| sd_sample | 59952 | 2800 | kernel rejection: Lean recursion-depth limit | 64.073 | 6.7 | kernel rejection: Lean recursion-depth limit | 53.666 | 6.71 |

Memory domain (rule fixed before these runs: analytic worst case and sampled working set both at least 1.0 GiB below the limit, and no system kill): worst case 7.133 GiB (workers x (limit + largest guard overshoot 7.8 MB) + 128 MB for the driver and guards) against a limit of 13.354 GiB; sampled working set at most 7.216 GiB (usage including reclaimable cache 7.395 GiB); system kills 0; OOM-kill counter change 0. Safe on this machine: **True**.

## Candidate supported size by statistic

Largest synthetic table accepted with every smaller size accepted, within C7's per-run limits. Measured sizes only: no size beyond the largest table tested (2,800 rows) is claimed. Under C and D, the cases those phases re-ran take their result there; the others (documented peak at most 5 GiB) keep their documented result.

| Statistic | A: 2 x 7 GiB (bytes) | C: 2 x 6 GiB (bytes) | D: 1 x 7 GiB (bytes) | Provisional in draft 3 (bytes) |
| --- | ---: | ---: | ---: | ---: |
| count | 59952 | 59952 | 59952 | 51209 |
| mean | 42487 | 42487 | 42487 | 33760 |
| min | 12377 | 12377 | 12377 | 8219 |
| sd_sample | 42487 | 42487 | 42487 | 33760 |
| median | 10299 | 10299 | 10299 | 8219 |
| pearson | 33760 | 25048 | 33760 | 33760 |

## Repeatability

* Same obligation run twice in A (an original and its planted copy), both completed: 315 pairs; peak memory differs by median 1.6 MB, at most 9.1 MB; time differs by median 2.0%, at most 10.5%.
* Same obligation in A and in D, both completed: 4 pairs; peak memory differs by median 0.8 MB, at most 1.3 MB; time differs by median 5.3%, at most 5.7%.

## Kernel time for 60 and 120 papers

Observed on 8 development papers (original and planted copy, every distinct claim of the four v1 arms, one claim per file, documented configuration): kernel time per paper mean 0.586 h, median 0.421 h, maximum 1.449 h; kernel runs per paper mean 132.6, maximum 290.

Projected wall time (a projection, not a measurement: perfect packing, papers like the development papers):

| Design | Workers | At the observed mean (h) | If every paper were the slowest observed (h) |
| --- | ---: | ---: | ---: |
| 60 papers | 1 | 35.2 | 86.9 |
| 60 papers | 2 | 17.6 | 43.5 |
| 120 papers | 1 | 70.4 | 173.9 |
| 120 papers | 2 | 35.2 | 86.9 |

