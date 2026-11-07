# Independent numerical implementation review

This is an internal review by a separate implementation agent, using authored examples and the development Hahn1 source only. It is not external expert validation. No held-out source, reference label or final prediction was consulted in reviewing the numerical checker.

The review found two defects before prospective evaluation. Both were repaired by the implementation owner and independently checked afterward:

1. Decimal constants in Python AST nodes had already passed through binary floating point before the exact rational and Decimal evaluators reconstructed them. For example, the source literal `0.12345678901234567890123456789` differs from the reconstructed `0.12345678901234568`. A point interval around the latter cannot enclose the former. The repair binds numeric constants to their original lexical source token and rejects exact-mode evaluation of unattached float AST constants. The authored regression now returns precisely the source fraction.
2. The parser evaluated each model at an invented `x=1` during validation. The valid authored model `b1/(x-1)` with observations at `x=2,3` was consequently rejected. Static validation now checks the entire AST without inventing a data-domain requirement. The authored case reproduces zero residual sum of squares.

Retained results are in `evidence/independent-numeric-review.json`. An exact-scalar falsification campaign tested 240 rational interval cases at 49,200 points with no enclosure violation. The independent oracle evaluates individual rational scalars; it does not duplicate the interval algorithm. These are finite tests, not a formal proof of the Python implementation. Six focused regression and security tests pass.

The development Hahn1 coefficients reproduce RSS `1.532438285360618` in float arithmetic and `1.5324382853606231100253714149137307869357440812417038683903140822734691162864110` at 80 Decimal digits. This is development evidence only. The conservative rational coefficient-rounding enclosure overlaps the reported RSS rounding interval under the stated nearest-rounding assumption.

Two scope cautions remain:

- Overlap with a conservative interval enclosure establishes that this enclosure does not refute the report. Dependency widening means it does not prove existence of one common parameter vector attaining the report, global optimality, or physical adequacy. The `COMPATIBLE` field must be read within that limited scope.
- Parameter standard deviations are source-reported table fields, not independently reconstructed uncertainties. The residual-statistics reproduction status cannot certify their values or infer confidence intervals, error distributions, independence or homoscedasticity. Negative parameter standard deviations should be treated as malformed scientific metadata if this field is admitted to a stronger checking contract.

The checker never executes uploaded model code. An authored formula attempting an import and file write returns `UNKNOWN` and leaves the sentinel absent. Exact transcendental interval bounds remain unsupported and explicitly abstain. Float/Decimal agreement is numerical cross-checking, not a rigorous transcendental error bound or empirical validation.
