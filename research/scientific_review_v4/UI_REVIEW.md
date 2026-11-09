# Scientific review interface

`review.render(interpretation, checks, inventory_or_artifacts, summary)` returns
standalone, script-free HTML. It accepts the v3 interpretation shape, a check
list, and either a portable artifact inventory or a `dict[path, bytes]`. The
summary may supply `study_overview`, `missing_assets`, `next_checks`, and the
relative `source_download_prefix` (default `parent/intake/objects/`).

Contradictions and open questions appear first. Statements expose their sources,
units, scope, assumptions, conditions and mathematical domain through native
keyboard-accessible disclosures. Download links use captured original digests.
When original bytes are supplied, a matching UTF-8 excerpt is identified only
after checking its digest and byte range. PDF/DOCX derived text is labeled as
derived, with adapter/page/provenance shown from `source.transformation`; its
offsets are not presented as quotes in original binary bytes. XML normalization
provenance can coexist with an original byte excerpt.

Five evidence classes remain separate: formal proof, reproduced computation,
checked source statement, contradiction, and unresolved meaning/result. Exact
kernel status names require receipt fields. An incomplete receipt, unknown
verdict (including `VERIFIED_SUPPORTED`), authority claim or certified-meaning
claim is displayed as unresolved. Receipt shape validation does not authenticate
a caller's record: package replay owns that check. The page explicitly states
that no scientific conclusions are certified.

The restored interface was tested in a fresh actual Firefox 157.0 process on
2026-11-07. The authored walkthrough uses actual v3 interpretation/check APIs on
the development NIST Hahn1 file and a small SBML example. An altered Hahn1 copy
produces an actual contradiction. The positive formal result comes from a fresh
`scientific_semantics_v3.assurance.verify()` Lean 4.28.0 replay; no kernel success
record is fabricated. Final/held-out data are not read by this demonstration.

Automated checks cover Tab/Enter navigation, opening source disclosures,
downloading the original file by keyboard and matching its SHA-256, all five
classes, inert source injection, zero external network requests, and no
horizontal overflow at 390, 768 and 1440 pixels with all disclosures open.
Python tests also cover invalid prefixes, unsupported verdicts, incomplete
receipts, authority claims, missing assets, original byte binding and derived
PDF provenance. This is browser automation and an authored walkthrough; it does
not establish human usability.

Run from the repository root with an available pytest Python and Playwright:

```sh
/workspace/proof-carrying-science/.venv/bin/python -m pytest -q research/scientific_review_v4/tests/test_review_ui.py
/workspace/proof-carrying-science/.venv/bin/python -m research.scientific_review_v4.tests.ui_demo_fixture /tmp/pcs-ui-fresh-demo
node research/scientific_review_v4/tests/ui_browser_demo.cjs /tmp/pcs-ui-fresh-demo research/scientific_review_v4/evidence
```

The fixture output directory must be new. The harness defaults to retained
Playwright and Firefox installations under `/workspace/.onboarding`; override
them with `PCS_PLAYWRIGHT_MODULE` and `PCS_FIREFOX`. The fixture uses the pinned
Lean installation there when present. It refuses a formal demonstration if the
fresh actual Lean replay does not succeed.

Retained evidence: `evidence/ui-browser-results.json`, desktop/mobile/evidence
screenshots, and `evidence/ui-lean-receipt.json`. The browser result binds the
rendered page, renderer, generator and harness with SHA-256. Screenshots were
visually inspected for readable wrapping and layout. Earlier lost browser
results are not reused.
