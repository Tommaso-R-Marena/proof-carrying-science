# Warning: do not use the frozen v1 replayer alone to trust a bundle from someone else

Added 2026-11-17. This file is new; no frozen file was changed, and every digest in
`benchmark/FREEZE.json` still verifies.

`replay_independent.py` is part of the frozen v1 software (pinned by `benchmark/FREEZE.json`). It
re-derives each proof obligation from the receipt's claim and re-runs the Lean kernel. It does **not**
check that the claim is the one the sentence makes. A bundle that was edited and then resealed (every
digest recomputed) replays successfully, also with the real kernel, when its claim:

* names another number than the one printed in the sentence (for example the file's mean instead of
  the printed 111.2);
* checks another statistic than the claim's (a median for a claim about a mean); or
* drops one of the two standard-deviation conventions, so that a conditional result looks proved.

The kernel cannot catch this: the theorem that remains is true. It is about another statement.
(Finding of 2026-11-17 by the conformance work on the assurance research branch.)

**What to use instead**

* For a v1 bundle: `python research/claimcheck_v1_1/replay_v1_bundle_checked.py BUNDLE --checker-sha256 <digest>`.
  It runs this replayer unchanged and then requires that the claim's reported value is the printed
  literal, that the checked variants are exactly those the claim's statistic requires, and that every
  decided result is the status its variants establish. The six committed held-out bundles pass it
  (302 receipts, no problem).
* For a v1.1 bundle: `python research/claimcheck_v1_1/replay_independent_v1_1.py BUNDLE --checker-sha256 <digest>`,
  which applies the same checks.

The frozen replayer remains valid evidence of what the frozen run computed, and the frozen bundles
were not affected: they were written by the pipeline, not by hand. The warning concerns bundles whose
origin you cannot vouch for.
