# PCS v0.6 adaptive replay scheduler

Status: **implemented experimental optimization layer; outside scientific verdict semantics**.

## Purpose

PCS must execute every mandatory replay check before a valid scientific assurance
result can be accepted. The adaptive scheduler changes only the order in which
ready checks execute.

Its optimization target is:

```text
minimize expected time to first detected failure
```

It is not permitted to optimize, predict, replace, or modify the scientific
PASS/FAIL decision itself.

## Trust invariant

For every supported scheduler strategy:

```text
same mandatory evidence set
        ↓
same deterministic check functions
        ↓
same replayed evidence outcomes
        ↓
same claim assessments
        ↓
same normalized scientific decisions
```

Only the execution order may differ.

The replay implementation reconstructs the evidence result list in the original
certificate order before claim assessment and normalized-wire derivation.

## Strategies

PCS v0.6 implements:

- `manifest` — certificate evidence order;
- `cheapest-first` — lowest historically estimated duration first;
- `failure-rate-first` — highest smoothed historical failure frequency first;
- `failure-per-second` — highest estimated failure probability per millisecond;
- `bandit` — contextual LinUCB ranking using failure observations plus input-size
  and artifact-count context.

All strategies execute all checks.

## Contextual bandit

The bandit is a disjoint LinUCB-style scheduler per check type.

Current context vector:

```text
1
log1p(input_bytes) / 20
min(artifact_count, 8) / 8
```

Historical reward:

```text
1 when the check outcome was FAIL
0 otherwise
```

The ranking score is an upper-confidence failure estimate divided by expected
duration. This biases the order toward checks that are both informative about
failure and inexpensive.

No random policy action is used in the acceptance path.

## Cold-start guard

Requested `bandit` scheduling does not become the effective execution strategy
until the history contains:

- at least 20 eligible check observations overall; and
- at least 3 observations for every check type present in the current package.

Before that threshold, PCS records the requested strategy but falls back to
`failure-per-second`.

The receipt-visible scheduler record includes the requested strategy, effective
strategy, readiness statistics, and fallback reason.

## Shadow mode

Recommended deployment begins with:

```bash
pcs verify-v06-bundle study.pcs.zip \
  --public-key trusted-public.pem \
  --scheduler manifest \
  --shadow-bandit \
  --scheduler-history scheduler-history.jsonl \
  --scheduler-telemetry-append scheduler-history.jsonl
```

PCS continues to execute manifest order while recording the order the contextual
bandit would have selected.

After enough history is collected:

```bash
pcs scheduler-report-v06 scheduler-history.jsonl \
  -o scheduler-report.json
```

The report compares manifest, cheapest-first, failure-rate-first,
failure-per-second, and bandit scheduling chronologically. Each historical run is
planned using only telemetry from earlier lines.

Reported time-to-first-failure comparisons reuse observed per-check durations as
counterfactual estimates. They are evidence for prioritization behavior, not proof
of future wall-clock speedup.

## Active adaptive ordering

After the cold-start readiness threshold and external benchmark review:

```bash
pcs verify-v06-bundle study.pcs.zip \
  --public-key trusted-public.pem \
  --scheduler bandit \
  --scheduler-history scheduler-history.jsonl \
  --scheduler-telemetry-append scheduler-history.jsonl
```

Even in active mode, all mandatory checks execute.

## Telemetry

Telemetry format:

```text
pcs-replay-telemetry-v1
```

Per check it records:

- check type;
- original and execution index;
- artifact count;
- aggregate input bytes;
- replay outcome;
- failure class;
- wall-clock duration;
- CPU duration.

It does not record artifact contents.

Evidence identifiers are SHA-256-derived in persisted telemetry rather than stored
as human-readable IDs.

Telemetry is observational and remains external to:

- claim assessment;
- normalized decision generation;
- reviewer policy;
- signed-review quorum;
- formal assurance semantics.

Append-only JSONL history uses a single append write per run.

## Scheduler report

```bash
pcs scheduler-report-v06 scheduler-history.jsonl
```

The report summarizes check-type failure rates/durations and chronological
counterfactual time-to-first-failure for every implemented strategy.

The report is not a scientific certificate and must never be interpreted as one.

## Promotion requirements

A learned ordering policy should remain shadow-only until all of the following
hold:

1. full v0.6 repository gate executes successfully on a real runner;
2. scheduler semantic-invariance tests pass;
3. telemetry is collected from workflows not authored solely for scheduler tests;
4. chronological evaluation beats deterministic baselines on the target workload;
5. no check type required by the target workflow is below the cold-start threshold;
6. operational review confirms the telemetry does not expose prohibited data.

If these conditions stop holding, deployment should return to a deterministic
baseline.

## Direct runtime check

A standalone runtime exercise on 2026-09-29 used 20 synthetic historical
observations:

- 10 `unit_compatible` PASS observations at about 10.45 ms mean duration;
- 10 `reaction_balance` FAIL observations at about 1.045 ms mean duration.

The bandit became ready and changed the three-check order from:

```text
E1 unit → E2 reaction → E3 unit
```

to:

```text
E2 reaction → E1 unit → E3 unit
```

All mandatory checks remained present.

Using those measured synthetic durations, the counterfactual time to first detected
failure changed from 11.495 ms to 1.045 ms (11×). This is a scheduler-algorithm
runtime check, not a scientific-accuracy result and not a substitute for the full
repository gate.
