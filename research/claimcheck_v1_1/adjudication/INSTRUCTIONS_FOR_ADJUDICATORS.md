# Instructions for adjudicators

Thank you for helping. You are asked to read parts of a published paper and say, for each marked
number, what it is. Nobody will tell you what a computer program concluded, and please do not look
for that: your judgement is useful only if it is independent.

## Before you start

Please confirm in your reply:

* your name, field and highest degree (these are reported with your consent);
* that you took no part in building Proof-Carrying Science or ClaimCheck;
* that you have not read the ClaimCheck reports about these papers;
* that you worked alone and did not discuss items with the other adjudicator.

## What you receive, per paper

* `article.txt`: the paper's text (open access).
* a data file (CSV): the table the authors deposited.
* `data_dictionary.json`: what the deposit says about the table.
* `sheet.csv`: the numbers to classify. In each sentence the number is marked «like this».

## What to do for each row of `sheet.csv`

1. Read the sentence, and as much of the paper as you need.
2. Decide the **class**:
   * **T**: the number is a descriptive statistic of this table (a count, a share, a sum, a mean, a
     median, a minimum or maximum, a standard deviation, a standard error, a variance, a correlation,
     or a regression slope or intercept), and when you compute it from the file you get the printed
     number (rounded as printed).
   * **F**: it is such a statistic, but the file gives a different number.
   * **N**: it is not a statistic of this table: a test statistic, a model estimate, a date, an
     identifier, a number about other data, or something this table cannot give.
   * **A**: you cannot tell.
3. For T and F, write what the number is in your own words, then the statistic, the column, and
   which rows (all rows, or which group). If you computed it, write your value.
4. Say how sure you are (1 = a guess, 5 = certain) and add any note. If you think the authors used
   other rows, another version of the data, or a different definition, say so. That is exactly the
   kind of note we need.

Use any software you like to compute. There is no time limit. If something is unclear, say so in
the notes instead of guessing.

## What your answers will be used for

To measure how often an automatic tool reads such sentences correctly. They will not be used to
judge the paper or its authors. A number classed F means only that this file does not give that
number under your reading.
