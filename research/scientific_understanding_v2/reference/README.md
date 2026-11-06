# Independent internal scientific reference annotations

These references are prepared by a separate internal reviewer reading upstream
publication text, model declarations, and author code documentation. The reviewer
does not import, run, or read the new PCS interpretation or check components, and
does not use PCS segment extraction as ground truth. This is independent internal
review, not external domain-expert review.

Each record states its scientific claim, typed expectation, status, conditions,
units, assumptions, exact source quote, source SHA-256, source locator, and label
provenance. Provenance distinguishes publication findings, curated model metadata,
author code/documentation output, manually derived consequences, and adversarial
counterclaims. Counterclaims are reviewer-authored and are never represented as
published findings. Equations copied from model declarations support the model's
declared behavior; they are not evidence that nature follows that model.

`development.json` is available during component development. `final.json` must be
loaded explicitly with `load_reference("final", allow_final=True)` only after the
evaluated components are frozen. This is a documented protocol, not access control.
Source identities are fixed before component evaluation. Hash and exact-quote
checks verify evidence integrity without recomputing scientific labels.

The prepared corpus contains 53 explicit annotations: 28 development annotations
over two projects and 25 final annotations over two other projects. A second
internal reader independently prepared the development cell-cycle model labels,
which the reference preparer reviewed. The final labels were prepared by the
reference preparer and were withheld from component developers. The annotation
file hashes are fixed in `annotation_freeze.json`; the loader rejects label-file
changes against that manifest. The manifest records a protocol, not protection
against a party able to edit both the labels and manifest.

The biochemical papers' full text is not bundled because a redistribution license
was not established. Attributed publication abstract quotations, curated model
declarations, and code generated upstream from those models carry distinct
provenance. Generated model-conversion code is not an independent author
simulation result. The SciPy numerical outputs are author-documentation examples,
not newly executed experiments or release-independent guarantees. No scientific
claim is promoted to an externally reviewed or formally proved theorem by its
inclusion here.

Numerical tolerances in a typed expectation are interpretation tolerances chosen
by the reviewer, unless the record explicitly identifies an upstream tolerance.
Ambiguous or unreported outcomes receive `insufficient_evidence`, rather than an
invented result. A contradicted counterclaim has direct incompatible evidence;
mere absence from a paper is not contradiction.
