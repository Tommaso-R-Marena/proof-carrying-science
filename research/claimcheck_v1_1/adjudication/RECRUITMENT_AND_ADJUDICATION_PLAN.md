# Independent adjudication: recruitment and procedure (owner decision A4)

**Status: prepared. No adjudicator has been appointed, contacted or asked.** Nobody is named here
because nobody has agreed to take part. Labels produced by a language model, by AI-assisted review,
by a second automated implementation, or by the people who built ClaimCheck are not independent
adjudication and are never reported as such.

## 1. Roles

| Role | Number | Does |
| --- | --- | --- |
| adjudicator | 2 per scientific context (6 for three contexts; 2 in total is the minimum if each covers all contexts) | classifies every number on the sheets, alone |
| resolver | 1 (may cover all contexts) | decides disagreements after both adjudicators have sealed their forms |
| package keeper | 1, not an adjudicator | builds and sends packages, holds the key, seals and opens forms; may be the owner |

## 2. Qualifications

* Graduate training (master's or doctorate) or equivalent professional experience in a quantitative
  empirical science, and practice in computing descriptive statistics from a data table with any
  tool (R, Python, a spreadsheet).
* Regular reading of primary research articles. At least one adjudicator per context works in or
  near that context (ecology and organismal biology; biomedical and health research; psychology,
  behavioural and social science), because what a sentence refers to often depends on field
  conventions.
* Resolver: an experienced researcher or a statistician, comfortable with sample versus population
  conventions, standard errors, exclusions and rounding.

## 3. Independence and conflicts of interest

Each person confirms in writing before receiving anything:

* no contribution of any kind to Proof-Carrying Science or ClaimCheck, and no access to its reports,
  receipts or outputs about the papers;
* not supervising, supervised by, employed by or co-authoring with the project owner;
* no authorship, shared laboratory or close collaboration with the authors of any paper in their
  package. Packages are checked against this per paper and a conflicted paper is given to another
  adjudicator;
* no payment or benefit that depends on the results. An honorarium for time is compatible with
  independence; the owner decides whether to offer one;
* they will work alone and not discuss items with the other adjudicator before resolution.

## 4. Workload

Per paper, the protocol (section 8) asks for every number that received a decided verdict from any
arm, every number with a provisional label, and ten further sampled numbers: about 25 numbers.

| | Per paper | 60 papers | 120 papers |
| --- | --- | --- | --- |
| reading methods, opening the data | 10 to 20 min | | |
| classifying (most numbers are quick; T and F need a computation) | 1 to 1.5 min per number | | |
| **per adjudicator** | 35 to 57 min | **35 to 55 h** | 70 to 110 h |
| resolver (assuming 15 to 25 % disagreement, about 3 min each) | | 11 to 19 h | 22 to 38 h |

These figures are assumptions, not measurements: nobody has yet adjudicated a package and no timing
exists. The preliminary round (section 9) measures them before the owner commits to a sample size.

## 5. Blinding

* Packages are built by `build_package.py`: the article text, the deposited data file, a data
  dictionary with the file's own SHA-256, and a sheet with each number marked «like this» in its
  sentence. Numbers of interest are mixed with control numbers in random order. The key stays with
  the package keeper (`KEY_DO_NOT_SEND/`).
* `check_blinding.py` must pass on every package before it is sent. It fails on verdict words,
  digests other than the data file's own, any column that could carry an answer, extra files, or
  any mention of the project outside the instructions. It passes on the prepared package
  `v1_discrepancies/package/`, and catches a deliberately leaky copy.
* Adjudicators are not told which numbers received verdicts, how many did, or which arm proposed
  what. Provisional labels are never shown.

## 6. What adjudicators verify

For every T or F number, in their own words and then as statistic, column and rows:

1. **source to column:** which column of the deposited table the sentence refers to, using names,
   units and the data dictionary; whether a like-named column is in fact another variable;
2. **statistic and convention:** mean, median, standard deviation with n − 1 or n, standard error,
   share, count of what (rows, individuals, sites, sequences);
3. **rows:** all rows, a group, exclusions stated in the methods (outliers, missing values,
   failed samples), and whether a printed sample size matches the rows used;
4. **units and scale:** units printed after the number against units of the column; percentages
   against fractions; transformed values (log, standardised);
5. **the deposited data set:** whether it is plausibly the analysed data (version, number of rows
   against the reported n, dates); any sign that it is not is written in the note;
6. **the value:** computed by them, with the printed rounding;
7. **for F:** whether exclusions, a file version or a definition could explain the difference. The
   note decides whether the case is a *discrepancy for review*; nobody records that a paper is wrong.

`INSTRUCTIONS_FOR_ADJUDICATORS.md` already asks for 1 to 3, 6 and 7 in plain words; items 4 and 5
are to be added to it before the first prospective package (a one-paragraph change; not made here
because the preliminary round should test the current text first).

## 7. Disagreements and ambiguity

1. Both forms are returned and sealed: the package keeper records the SHA-256 of each form and the
   time before anyone compares them.
2. Raw agreement and Cohen's κ on the class are computed before resolution and reported.
3. The resolver sees both forms and the package, never system outputs, and decides the class, or
   **A** where the case is genuinely ambiguous. An unresolved disagreement stays **A**; it is not
   decided by majority or by the system.
4. Disagreement about the reading with the same class (for example both T, different rows) is
   resolved the same way.
5. All original forms are kept unchanged with the resolution.
6. Results of the system are opened only after every form is sealed (protocol 11, no interim looks).

## 8. Records and data handling

Forms, timestamps, time spent and confidence ratings are kept. Articles and data are openly licensed.
An adjudicator's name, field and degree are reported only with their written consent; otherwise
they are described by field and career stage.

## 9. A preliminary round on the four apparent v1 discrepancies

`v1_discrepancies/package/` (3 papers, 30 numbers: the 4 apparent discrepancies of v1 and 2 related
numbers among 24 controls) is ready to send. Proposal for the owner:

* send it to the first two people who agree, as a **pilot of the procedure**: it tests the
  instructions, the form, the timing estimates and the agreement computation at small cost (about 2
  to 3 hours each);
* it also gives the first human judgement of whether those four numbers are real discrepancies,
  which matters for the authors and for the v1.1 policy, which currently sends all four to review;
* it is **not prospective evidence**: these papers were used to build and tune v1.1. Their results
  are reported as development-set adjudication, separately, and they enter no criterion.

## 10. Recruitment

The owner recruits; nothing has been sent to anyone. Suggested sources: colleagues in other
departments, statistics or research-software consulting units, reproducibility networks and open
science groups. Each person receives the information in sections 1 to 8, the instructions, and the
independence confirmation of section 3, and is asked to reply in writing.
