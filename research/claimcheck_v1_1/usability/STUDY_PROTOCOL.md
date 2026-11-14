# ClaimCheck usability study: protocol and materials

**Status: prepared, not run. No participant has been recruited or tested, and no result exists.**
Nothing in this directory is evidence about users. A browser automation run is not a participant.

## Purpose

To find out whether a researcher who knows neither PCS nor Lean can complete a supported check and
understands what the result does and does not say. Misreading the scope of a verdict is treated as
a failure of the tool, not of the participant.

## Participants

At least five for a formative round (criterion C8 of the pilot criteria). Researchers who work with
tabular data and read quantitative papers; any field. Excluded: anyone who has contributed to PCS,
used Lean, or read the ClaimCheck reports. Recruited by the project owner. Participation is
voluntary and unpaid unless the owner decides otherwise; participants may stop at any time.

Before any session the owner must settle whether this needs ethics review at the owner's
institution. This protocol does not decide that.

## What is recorded

Task outcomes, answers to the questions below, time per task, and free comments. No audio or video
unless a participant agrees in writing. No personal data beyond field and career stage. Participants
use the example data provided; they are told not to upload unpublished data of their own.

## Session (about 40 minutes, one participant at a time)

The facilitator reads the introduction, then does not help. If a participant is stuck for three
minutes the facilitator notes it and gives the smallest hint that lets them continue; a hinted task
counts as not completed unaided.

**Introduction (read aloud):** "This is a research tool that checks whether a number printed in a
paper can be recomputed from a data file. We are testing the tool, not you. Please think aloud."

**Tasks** (materials: the example table and two sentences in `tasks.json`)

1. On the web page, open the example table and check the first sentence's mean.
2. Say in your own words what the page has and has not established.
3. Obtain a result checked by the Lean kernel for that claim, using the instructions on the page
   (download the proof file and the runner, run one command). Lean is pre-installed on the study
   machine; installation is tested separately in task 6.
4. Check the second sentence's mean (the file does not give the printed number).
5. Open the downloaded receipt or report and find: which file was checked, and which assumptions
   were made about rounding and missing values.
6. (Optional, timed separately) On a machine without Lean, follow the installation instructions.

**Questions** (after the tasks; `questions.json` holds the exact wording and the scoring key)

Critical scope questions, each scored correct or incorrect:

* S1 Does a confirmation show that the paper's conclusion is right?
* S2 Does a discrepancy flag show that the paper is wrong?
* S3 Who or what decided that the sentence means this statistic of this column?
* S4 The tool answered REQUIRE_HUMAN_REVIEW. What would you do next?

Further questions: what "the browser preview" is compared with the kernel result; what UNKNOWN
means; whether they could give the evidence to a colleague to re-check, and how.

## Measures and thresholds (fixed before any session)

* Task completion unaided: tasks 1, 3, 4 and 5 each completed by at least 80 % of participants.
* Each of S1 to S4 answered correctly by at least 80 % of participants.
* Any participant who concludes from a discrepancy flag that the paper is wrong, or from a
  confirmation that the science is right, is reported individually with what they saw on screen.
* Reported with counts, not percentages alone. With five participants "80 %" means four of five,
  and no confidence interval narrower than the data is claimed.

## Reporting

Every session is reported, including abandoned ones. Changes made to the tool between sessions are
listed with the session after which they were made; sessions before and after a change are not
pooled. If the thresholds are not met, the tool stays research-only for external users.
