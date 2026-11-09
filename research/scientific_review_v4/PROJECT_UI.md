# Complete-project browser walkthrough

The authored Firefox walkthrough opens the actual Fiedler2016 development review
package produced by the v4 end-to-end benchmark. It does not substitute synthetic
positive receipts or alter the review renderer. The package contains 103 source
artifacts, 54 proposed statements and 59 check records. The displayed evidence
classes contain one abstract formal receipt, four reproduced computations, 38
source checks, no contradiction records and 16 unresolved records. These are
scoped outputs, not certification of the principal paper conclusions.

The browser checks exact displayed counts and scope warnings, separate evidence
classes, the actual extracted assumptions and biological relation, keyboard
navigation, original-source download and digest equality, and layout at 390,
768 and 1440 pixels with every disclosure open. The downloaded paper has SHA-256
`015f56f263fb11782c139c71b74dd31f5215fcabdb82dbddc13ea6850ac73b02`.
No external browser request, page error, embedded script or external asset was
observed. Desktop and mobile screenshots were visually inspected: text wraps
inside the page at both sizes and the scope warning is visible near the top.

The first bounded run failed to reach the first statement's source disclosure
within 100 Tab presses from the questions skip target. Its JSON is preserved in
`evidence/project-ui-first-attempt.json`. A second measurement with a larger
navigation budget reached that disclosure after **117 Tab presses**, opened it
with Enter, and downloaded the exact captured paper bytes by keyboard. The
second run passes the functional checks while recording this navigation cost
as an outstanding usability issue. No renderer changes were made to force a
pass. A researcher can use the section navigation links to reach statements,
but the long question list needs a more direct keyboard path in future work.

The actual report also exposes technical identifiers such as `source_assumption`
and checker explanations such as `ValueError: not a supported model source`.
The layout is readable, but these messages need clearer researcher-facing
language. Neither visual inspection nor this automated walkthrough establishes
that a novice can understand the review or that a domain expert finds it useful.
No human usability study or expert scientific adjudication was conducted.

Reproduce with a completed benchmark packet (or another package with compatible
artifacts and supported evidence categories):

```sh
node research/scientific_review_v4/tests/project_browser_demo.cjs \
  /path/to/fiedler2016-v4 /path/to/browser-evidence
```

The script defaults to the retained managed-workspace Playwright and Firefox
installations. Override `PCS_PLAYWRIGHT_MODULE` and `PCS_FIREFOX` elsewhere.
`project-ui-results.json` binds the exact report, renderer, packet manifest and
harness by SHA-256. The walkthrough reads development data only. It performs no
scientific checking and makes no claim of human usability validation.
