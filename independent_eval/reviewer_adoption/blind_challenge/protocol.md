# Blind reviewer challenge protocol

## Purpose

Measure whether reviewers can distinguish:

1. **valid** — computationally sound *and* scientifically scoped claims;
2. **invalid** — integrity/check failures that should not be accepted;
3. **computationally_valid_scientifically_unsupported** — checks pass, but the
   scientific claim exceeds declared assumptions / limitations.

## Blinding rules

1. Case packets shown to reviewers omit `ground_truth_label`, answer keys, and
   any field named `expected_*`.
2. Case IDs presented to reviewers use opaque tokens (`CASE-01`, …), not labels.
3. Ordering is shuffled with a recorded seed for reproducibility of the packet,
   not of human performance.
4. Human scores are recorded only when a real reviewer response sheet is
   supplied. This repository ships **no invented human results**.

## Allowed reviewer judgments

For each case the reviewer selects exactly one of:

- `accept_as_valid`
- `reject_as_invalid`
- `accept_computational_only`
- `abstain`

Optional free-text notes are allowed but not scored automatically.

## Scoring (automated)

| Ground truth | Correct responses |
| --- | --- |
| `valid` | `accept_as_valid` |
| `invalid` | `reject_as_invalid` |
| `computationally_valid_scientifically_unsupported` | `accept_computational_only` |

`abstain` is never counted as correct. Unknown response labels fail closed.

Machine scoring emits per-case correctness and aggregate accuracy. It does
**not** claim statistical significance, inter-rater reliability, or external
validation of PCS.

## Separation of duties

- Packet generation: `blind.py`
- Scoring against sealed ground truth: `score.py`
- Ground truth file remains under `keys/` and must not be bundled into reviewer
  packets.
