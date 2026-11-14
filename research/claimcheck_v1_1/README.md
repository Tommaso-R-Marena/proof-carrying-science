# ClaimCheck v1.1: a proved mismatch is not an accusation, a proved match is not a reading

Research sidecar. **No PCS v0.6 production authority.** Not validated prospectively: every number
in this directory comes from documents that were used to design v1.1 ([REPORT.md](REPORT.md)).

ClaimCheck v1 lets the Lean kernel decide whether a typed statement ("the mean of column pH over
all rows rounds to 6.07") is true of the exact bytes of a data file. Its held-out evaluation showed
what that is worth on its own: one proposer's readings were refuted wrongly 131 times, and a
proposer that had seen the data got coincidental matches through.

v1.1 adds one layer and changes nothing underneath it. The Lean checker, the kernel path and every
frozen v1 file are untouched. The new layer can only withhold.

## Three statements, kept apart

| | What it says | Who decides | Values |
| --- | --- | --- | --- |
| 1. Mathematical | the typed statement is true or false of these bytes | the Lean kernel | `MATCH_PROVED`, `MISMATCH_PROVED`, `CONDITIONAL_ON_CONVENTION`, `UNDEFINED_PROVED`, `NOT_ESTABLISHED` |
| 2. Reading of the sentence | whether there is enough support to say the sentence makes that statement | fixed mechanical rules; never a person, never a model | `SUPPORTED_BY_AUTOMATIC_CHECKS`, `REQUIRE_HUMAN_REVIEW`, `NOT_ATTACHED` |
| 3. Scientific | whether anything follows | nobody here | `NOT_ASSESSED` |

One **outward verdict** per reading, never stronger than the weaker of 1 and 2:

* `CONFIRMATION`: the printed number is reproduced, under a reading the rules below support.
* `DISCREPANCY_FOR_REVIEW`: the number is not reproduced under a reading that another number in the
  same sentence independently supports. For a person to look at. It never says a paper is wrong.
* `REQUIRE_HUMAN_REVIEW`: a mathematical result exists and is kept, but the reading is not
  supported well enough. Most kernel results end here, by design.
* `UNKNOWN`: no mathematical result, or nothing in the source to attach it to.

A statement by a named person that the reading is right can be recorded. PCS cannot verify who
wrote it, so it is shown beside the automatic verdict and never changes it.

## The rules (policy `pcs-claimcheck-semantic-policy-v1.1`)

The policy assumes that whoever chose the reading had looked at the data, whatever they say.

Needed for any outward verdict:

1. **Plain number.** Not part of a date ("22 July 2015") or an identifier ("NC-006").
2. **Eligible reading.** At most two row conditions, each "column = group label" with the label
   named in the sentence. No numeric thresholds, no "is not", no selecting rows by a value of a
   numeric column (that reproduces any number that occurs in the column).
3. **Wording attached to the number.** "mean … 6.07" with no other number between, "± 0.05",
   "5.01–8.03", "n = 124", "96 species" where the manifest says a row is a species. The word "mean"
   somewhere else in the sentence is not enough.
4. **Compatible unit.** A unit printed after the number must fit the column's declared unit. If the
   manifest declares none, the two cannot be compared and the verdict is withheld.

For a match to be a `CONFIRMATION`:

5. No other statistic or column that the sentence's wording attaches to this number reproduces it.
6. **Low chance of coincidence.** Among comparable numbers (same decimals, same number of digits,
   the printed one included), at most 2 % are reproduced by some eligible reading. A one-digit number
   has nine comparable numbers, so it is never confirmed. Or: a confirmed number in the same sentence
   fixes the column and rows, and the 2 % limit holds within what that leaves.

For a mismatch to be a `DISCREPANCY_FOR_REVIEW`, all of:

7. not a count (what a count counts is the least constrained reading of all);
8. no eligible reading of the sentence reproduces the number (otherwise the reading is probably wrong);
9. the difference exceeds one unit in the last printed digit (truncation and double rounding are
   not discrepancies);
10. a "±" value is named as a standard deviation or a standard error;
11. the sentence has no wording for statistics the tool does not compute (adjusted, interquartile,
    confidence interval, transformed, …);
12. a sample size printed in the sentence equals the rows the reading uses;
13. another number in the sentence is a `CONFIRMATION` from the same column and the same rows.

Every record lists each rule with pass or fail and a sentence saying why.

## Use it

Python 3.11+ (standard library) and Lean 4.28.0 (`source scripts/activate_lean_428.sh`).

```bash
# one number, with a fresh kernel run (about half a minute for a small table)
python -m research.claimcheck_v1_1 verify --data soil.csv --manifest manifest.json \
  --sentence "Soils … had a somewhat acidic average pH of 6.07 ± 0.05 SE (range = 5.01–8.03)." \
  --number 6.07 --stat mean --column pH --out bundle/

# replay the bundle with a program that shares no code with the one that made it
python research/claimcheck_v1_1/replay_independent_v1_1.py bundle/ \
  --checker-sha256 "$(cut -d' ' -f1 research/claimcheck_v1/formal/ClaimCheck.lean.sha256)"
```

`bundle/report.html` shows the three statements side by side. `bundle/records.json` holds the
v1.1 records; `bundle/v1/` is an ordinary v1 bundle with every Lean file the kernel checked.
The command also looks for other numbers in the same sentence that the same column and rows
reproduce, and puts those to the kernel too; they are the only thing that can support a discrepancy.

For a proof file downloaded from the web page there is a single-file runner with no dependency on
this repository:

```bash
python claimcheck_kernel_runner.py claimcheck-proof.lean --out kernel-run.json
```

It checks that the file starts with the reviewed checker, runs Lean, and reports what was proved.

A manifest may now say what one row is (`"row_unit": ["individual"]`); without it no count in prose
can be confirmed. Units should be declared for every column that has one.

## What is in here

| Path | Role |
| --- | --- |
| `policy.py`, `space.py`, `binding.py` | the rules; the reading space a sentence admits; wording attached to a number |
| `verify.py`, `__main__.py` | v1 pipeline → policy → three-layer records, bundle, report; command line |
| `replay_independent_v1_1.py` | stand-alone replay (imports nothing from the packages) |
| `claimcheck_kernel_runner.py` | stand-alone kernel runner for one proof file |
| `check_live_v11.py`, `tests/` | live checks with the real kernel; offline tests |
| `dev/` | development evaluation and free-choice adversary on the v1 documents |
| `perf/` | kernel cost by table size |
| `prospective/` | **draft** protocol, criteria, statistics, contamination checks for the evaluation that has not been run |
| `adjudication/`, `usability/` | materials prepared for people who have not yet been asked |

## Licences and data handling

* v1.1 adds no third-party material. The eight v1 documents it re-uses are CC BY articles with
  CC0 data deposits; licence, source and digest are recorded with each
  (`../claimcheck_v1/benchmark/*/*/document.json`, `acquisition.json`). The adjudication package
  quotes sentences from those CC BY articles with their citations.
* Code here is under the repository's Apache-2.0 licence. It needs Python's standard library and
  Lean 4.28.0 (Apache-2.0); the meaning theorems of v1 use Mathlib (Apache-2.0).
* v1.1 made no call to any language model. `verify`, the replayer and the kernel runner make no
  network request: a researcher's data and text stay on the machine that runs them. The prospective
  protocol sends models only sentences of openly licensed articles and column names, as v1 did.
* Unpublished or uploaded researcher material is to be treated as confidential: do not put it in a
  proposer prompt, a bug report or a committed bundle without the researcher's explicit permission.
  A bundle embeds the complete data file.
* Not done: a legal review of the model providers' terms for redistributing recorded model
  proposals (the v1 receipts contain them as short typed readings). Listed for the owner.

## Limits

* The rules are lexical and numerical. They cannot know that "nestling age at sampling" is not the
  column `chick_age`; they can only refuse to flag a mismatch that nothing else in the sentence
  supports.
* Coverage is low on purpose: on development data about a quarter of true statements are confirmed
  and one false statement in sixteen is flagged.
* Tables up to about 400 rows for every statistic; up to about 1,600 for counts, means, standard
  deviations and correlations; medians, minima and maxima fail above that ([perf](perf/results.json)).
  A failed kernel run is `UNKNOWN`.
* Whether the deposited file is the analysed file is outside the tool.
