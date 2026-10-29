# Combined isolated validation

This new validation branch locally combines exact #156 `eec5c65`, #154
`ba07e16` and #157 `044f9c6`. No GitHub pull request, main, PR153 head or
original contributor branch was merged or rewritten. The tested merge is
`b1abffbb74a962a3f396e69b65f7b5bf9c70a99b`; the following evidence-only commit preserves its results.

All **316 tests and 47 additional subtests passed**, with zero failures/errors/
skips. The single warning is the existing intentional duplicate-ZIP fixture.
New receiver modules were freshly checked (190 namespace theorem declarations,
54 authored), as was the separate 28-theorem history library. All axiom closures
use only the permitted standard three. Cached import trust remains explicit.
The source gate passes all 1,992 original identities plus the one receipt pin
and 38 V7 modules. Production formal source is unchanged relative to b916.

Evidence is under `research/post_integration_validation_20261019/`; hashes and
exact inputs are in `COMBINED_VALIDATION.json`. The real production authority
was supplied through the receiver environment from the source-identical baseline;
new scientific receiver modules were freshly compiled in this checkout.

This establishes bounded coexistence and regression evidence. It does not connect
the signed history to scientific checking/serving, prove Python/compiler/IO/OS
refinement, protect a root/checkpoint, validate empirical science, or approve any
PR. Individual small drafts remain the review units.
