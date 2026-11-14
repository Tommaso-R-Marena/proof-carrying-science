# ClaimCheck v1: does this number in the paper come from this data?

ClaimCheck checks one narrow kind of scientific statement end to end: a number printed in a paper
that is claimed to be a descriptive statistic of an accompanying data table. It answers three
questions separately and never lets one stand in for another.

| Question | Who decides | Possible answers |
| --- | --- | --- |
| 1. Is the arithmetic right? | The Lean 4 kernel, on the exact bytes of the data file | PROVED, REFUTED, UNKNOWN |
| 2. Is the statement linked to the paper and the data? | Deterministic checks you can inspect | GROUNDED or NOT_GROUNDED; the semantic reading is always UNREVIEWED |
| 3. Does the evidence support the scientific interpretation? | Nobody in this tool | NOT_ASSESSED, with the open obligations listed |

This is a research sidecar. It has **no PCS v0.6 production authority**, changes no production
path, and is not a general paper reviewer. Read [REPORT.md](REPORT.md) for what was measured
(including where it fails) and [TRUST_BOUNDARY.md](TRUST_BOUNDARY.md) for exactly what a result
does and does not establish.

## What the held-out evaluation found, in brief

Six open-access articles with deposited data, frozen before the run ([REPORT.md](REPORT.md)):

* **A PROVED from a proposer that had not seen the data was reliable.** 71 PROVED results from two
  language models; 64 matched a gold reading, 6 were faithful readings the gold set had missed, 1 is
  defensible, none was found unfaithful.
* **A REFUTED is only as good as the reading.** One model issued 131 wrong refutations (mostly
  "number of rows" for a count of something else); the other issued 2 wrong and 11 right, including
  two real discrepancies between a paper and its deposited data. Read REFUTED as "this reading does
  not hold for this file".
* **A proposer that can see the data can fit readings to it.** A deliberate coincidence search got
  3 false PROVEDs through the source checks. The tool cannot verify that a submitter was blind.
* **Coverage is modest** (at best 40 of 86 true statements), and about half of the screened
  articles print no descriptive statistic of their table in prose at all.
* Model agreement and model critics added no reliability. Neither is used as authority anywhere.

## What a result means

A receipt's `result` is PROVED or REFUTED only if **both** hold:

* the Lean kernel accepted a theorem `run pcs_src pcs_c<i> = <outcome>`, where `run` is the fixed
  checker in [`formal/ClaimCheck.lean`](formal/ClaimCheck.lean), `pcs_src` is the data file as one
  numeral (its hexadecimal dump) and the claim is the typed reading; and
* every deterministic source check passed: the quoted words are in the paper, the number is printed
  there as a whole token, the unit printed after it agrees, the columns and groups of the reading
  are named in the same sentence, the statistic is named in the sentence (not required for counts
  and shares), and the sentence uses no wording the dataset manifest marks as outside the table.

Every result carries its scope in words, for example:

> PROVED, for the data file soil_nut_xwalked.csv (SHA-256 …) only: "The arithmetic mean of pH over
> all rows equals 6.07 when rounded to the printed precision." Not established: that this reading is
> what the authors meant, that this is the data they analysed, or that the number supports any
> conclusion.

REFUTED means the file does not give the printed number under the stated reading. It does not mean
the paper is wrong: the reading may be mistaken, or the authors may have analysed other rows or
another file version. A conditional result (for example a standard deviation that matches with
denominator n − 1 but not n, when the paper does not say which) is reported as UNKNOWN with both
branches shown; it is never promoted.

## Use it

Requirements: Python 3.11+ (standard library only) and Lean 4.28.0 on `PATH`
(`source scripts/activate_lean_428.sh` from the repository root installs the pinned toolchain).

```bash
# 1. Propose typed readings (untrusted; pick any proposer)
python -m research.claimcheck_v1 propose --source paper.txt --data data.csv --manifest manifest.json \
    --proposer search --out proposals.json            # deterministic, no network
#   --proposer gemini|openrouter --allow-network      # language model; see "Model providers" below

# 2. Verify them: gates, exact oracle, Lean kernel; writes a self-contained evidence bundle
python -m research.claimcheck_v1 check --source paper.txt --data data.csv --manifest manifest.json \
    --proposals proposals.json --out bundle/

# 3. Replay the bundle with a program that shares no code with step 2
python research/claimcheck_v1/replay_independent.py bundle/ \
    --checker-sha256 "$(cut -d' ' -f1 research/claimcheck_v1/formal/ClaimCheck.lean.sha256)"
```

`bundle/report.html` is a script-free readable report; `bundle/receipts.json` holds the receipts;
`bundle/obligations/*.lean` are the exact files the kernel checked (each is the fixed checker plus
one data numeral, the claims and the expected outcomes, so `lean file.lean` re-checks it with no
other software). You can also write `proposals.json` by hand; a proposal is

```json
{"quote": "Soils … had a somewhat acidic average pH of 6.07 ± 0.05 SE (range = 5.01–8.03).",
 "spec": {"stat": "mean", "column": "pH", "reported": "6.07"}}
```

### The dataset manifest

The manifest is written by the person submitting the data, not by a model. It pins the file and
supplies the vocabulary that the source checks use:

```json
{"sha256": "<digest of the CSV>", "na_tokens": ["", "NA"],
 "columns": {"body_mass_g": {"unit": "g", "aliases": ["body mass", "weigh"]}},
 "values": {"sex": {"male": ["male", "males"]}},
 "out_of_scope_terms": ["juvenile"], "sd_convention": "n-1"}
```

Only `na_tokens` affects arithmetic. A proposer cannot set missing-value tokens, unit factors,
rounding tolerance or the standard-deviation convention: units are converted by a fixed table, the
tolerance is half a unit of the last digit actually printed in the paper, and both SD conventions
are checked unless the submitter declares one (which is then listed as an assumption).

### Supported statements

Counts, shares/percentages, sums, means, medians, minima, maxima, standard deviations, standard
errors of the mean, sample variances, Pearson correlations and two-variable least-squares
slope/intercept, over one strict comma-separated table of at most 64 KB, with optional row
conditions (text equals / differs, numeric comparisons). Anything else ends as UNKNOWN with the
reason stated: test statistics, model estimates, quantiles, distinct counts, weighted or
transformed values, tables printed inside the paper, several data files.

## Model providers (optional, untrusted)

`propose --proposer gemini|openrouter --allow-network` asks a language model for candidate
readings. The model sees only the sentences of the paper that print a number, plus the data
dictionary (column names, units, aliases, group labels). **It never sees data rows**, so it cannot
fit a reading to the numbers. Its output is parsed as data; unexpected fields are rejected; nothing
it says can produce or strengthen a verdict. A second model can be asked to criticise readings; its
opinion can only remove a proposal before verification.

* Credentials are read from `GEMINI_API_KEY` / `OPENROUTER_API_KEY` at call time, sent only as a
  header to that provider's fixed host, and never written to prompts, URLs, logs, caches, receipts
  or exceptions. Redirects are refused. Nothing in the public website calls a provider.
* Free provider tiers may retain inputs. Send only text you are entitled to disclose. The benchmark
  sends openly licensed article sentences and column vocabulary only.
* Calls are bounded and counted (`providers.Ledger`), and responses are cached so results replay
  without a provider.

## Verify the software itself

```bash
python -m unittest discover -s research/claimcheck_v1/tests     # offline: gates, oracle, rendering, replay tamper tests
python -m research.claimcheck_v1.check_live --fuzz 300          # needs Lean: positive/negative kernel controls + differential fuzz
(cd research/claimcheck_v1/formal && lake build ClaimCheck ClaimCheckReal)   # checker + Mathlib meaning theorems
python -m research.claimcheck_v1.benchmark.freeze check         # software and held-out inputs match their frozen digests
```

`check_live` never skips: it fails if Lean 4.28.0 is unavailable. Its negative controls submit
forged outcomes (wrong verdict, wrong exact value, wrong row counts, altered data) and require the
kernel to reject each one. Its fuzz compares the Python oracle with the Lean checker on random CSV
dialects and claims; any disagreement fails.

## Layout

| Path | Role |
| --- | --- |
| `formal/ClaimCheck.lean` | the fixed checker (Lean core only; no `sorry`, axioms, `partial`, `unsafe`, `native_decide`) |
| `formal/real/ClaimCheckReal.lean` | Mathlib proofs of what the rational tests mean over the reals |
| `spec.py` | typed claim representation and strict validation |
| `grounding.py` | deterministic source checks (question 2) |
| `oracle.py` | untrusted exact-arithmetic prediction of the checker's outcome |
| `lean.py` | renders obligations and runs the real compiler; fails closed |
| `pipeline.py` | gates → oracle → kernel → three-question receipt |
| `replay_independent.py` | stand-alone replayer (imports nothing from this package) |
| `baseline.py`, `propose.py`, `providers.py` | untrusted proposers: rules, search, language models |
| `benchmark/` | frozen protocol, development and held-out documents, runners, results |
| `tools/` | reporting tools written after the freeze: post-run analysis, bundle cross-check, website export (they change no result) |
