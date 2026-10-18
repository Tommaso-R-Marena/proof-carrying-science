"""Receiving-side regressions for false global bounds and missing witnesses."""
from certnum.certificate.checker import check_certificate
from certnum.certificate.schema import make_certificate
from certnum.expr.ast import expr_to_json
from certnum.expr.parse import parse_expr
from certnum.interval.interval import Interval


def certificate(*, coverage, incumbent={"x": "2"}, lower="0", upper="2"):
    claim = {"expr": expr_to_json(parse_expr("x")),
             "domain": {"x": Interval.mk(0, 2).to_json()},
             "lower_bound": lower, "upper_bound": upper}
    if incumbent is not None:
        claim["incumbent"] = incumbent
    return make_certificate("global_optimization", claim=claim,
                            witness={"coverage": [{"x": Interval.mk(*b).to_json()}
                                                  for b in coverage]})


def test_partial_cover_cannot_certify_false_global_lower_bound():
    # f(0)=0 refutes the old accepted lower bound 1.
    assert not check_certificate(certificate(coverage=[(1, 2)], lower="1")).accepted


def test_full_partition_retains_valid_bounds():
    assert check_certificate(certificate(coverage=[(0, 1), (1, 2)])).accepted


def test_missing_incumbent_cannot_certify_false_upper_bound():
    assert not check_certificate(certificate(coverage=[(0, 2)], incumbent=None,
                                             lower="-2", upper="-1")).accepted


def test_empty_incumbent_cannot_bypass_domain_membership():
    assert not check_certificate(certificate(coverage=[(0, 2)], incumbent={})).accepted
