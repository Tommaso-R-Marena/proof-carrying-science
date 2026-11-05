"""Replayable Python certificates; NOT a Lean-certified universal authority.

The receiver checks coverage and each branch's sign on the whole cell using
endpoint inequalities. It never calls the producer's cut/sweep/affine routines.
Future Lean integration can check this finite witness rather than trust search.
"""

from __future__ import annotations
import hashlib
from universal_relu import (
    Net,
    piecewise_cells,
    all_integer_equal,
    universal_correctness_preserved,
    exact_interval_max_error,
)
from promotion_v2 import canonical

FORMAT = "pgsi-integer-affine-certificate-v1"


def model_data(n):
    return {
        "bias": n.bias,
        "terms": [[t.coefficient, t.weight, t.bias] for t in n.terms],
    }


def model_hash(n):
    return hashlib.sha256(
        b"PGSI-AFFINE-MODEL-v1\0" + canonical(model_data(n))
    ).hexdigest()


def certificate(property_name, nets, interval=None):
    nets = tuple(nets)
    if property_name == "equal" and len(nets) == 2:
        d = all_integer_equal(*nets)
        result = {"passes": d.passes, "counterexample": d.counterexample}
    elif property_name == "preserves" and len(nets) == 3:
        d = universal_correctness_preserved(*nets)
        result = {"passes": d.passes, "counterexample": d.counterexample}
    elif (
        property_name == "max_error"
        and len(nets) == 2
        and type(interval) is tuple
        and len(interval) == 2
    ):
        error, x = exact_interval_max_error(*nets, *interval)
        result = {"max_error": error, "argmax": x}
    else:
        raise ValueError("Unapproved property/arity/interval")
    if property_name != "max_error" and interval is not None:
        raise ValueError("Unexpected interval")
    _, rows = piecewise_cells(*nets)
    return {
        "format": FORMAT,
        "property": property_name,
        "model_sha256": [model_hash(n) for n in nets],
        "interval": list(interval) if interval is not None else None,
        "cells": [
            {"low": c.low, "high": c.high, "affine": [list(p) for p in pairs]}
            for c, pairs in rows
        ],
        "result": result,
        "kernel_proved": False,
    }


def _integer(x):
    if type(x) is not int or x.bit_length() > 16384:
        raise ValueError("Invalid/budget-exceeding exact integer")
    return x


def _eval(n, x):
    # Independent algebraic evaluation, no Net.predict call.
    return n.bias + sum(c * max(0, w * x + b) for c, w, b in model_data(n)["terms"])


def verify(cert, expected_nets, property_name, interval=None):
    """Receiver-owned inputs/property/interval are mandatory binding arguments."""
    nets = tuple(expected_nets)
    fields = {
        "format",
        "property",
        "model_sha256",
        "interval",
        "cells",
        "result",
        "kernel_proved",
    }
    if (
        type(cert) is not dict
        or set(cert) != fields
        or cert["format"] != FORMAT
        or cert["kernel_proved"] is not False
        or cert["property"] != property_name
        or cert["model_sha256"] != [model_hash(n) for n in nets]
        or cert["interval"] != (list(interval) if interval is not None else None)
    ):
        raise ValueError("Certificate scope/model binding mismatch")
    if property_name not in {"equal", "preserves", "max_error"} or len(nets) != (
        3 if property_name == "preserves" else 2
    ):
        raise ValueError("Bad receiver property")
    if any(type(n) is not Net for n in nets) or sum(len(n.terms) for n in nets) > 4096:
        raise ValueError("Unsupported model budget")
    cells = cert["cells"]
    if type(cells) is not list or not 1 <= len(cells) <= 8193:
        raise ValueError("Cell count budget")
    prior = None
    valid = True
    maximum = None
    old_correct_witness = None
    if property_name == "max_error":
        if type(interval) is not tuple or len(interval) != 2:
            raise ValueError("Bad interval")
        low, high = map(_integer, interval)
        if low > high:
            raise ValueError("Reversed interval")
    elif interval is not None:
        raise ValueError("Unexpected interval")
    for i, cell in enumerate(cells):
        if type(cell) is not dict or set(cell) != {"low", "high", "affine"}:
            raise ValueError("Malformed cell")
        lo, hi = cell["low"], cell["high"]
        if lo is not None:
            _integer(lo)
        if hi is not None:
            _integer(hi)
        if (
            (i == 0) != (lo is None)
            or (i == len(cells) - 1) != (hi is None)
            or (i > 0 and lo != prior + 1)
            or (lo is not None and hi is not None and lo > hi)
        ):
            raise ValueError(
                "Incomplete, overlapping or reversed integer-line coverage"
            )
        prior = hi
        affines = cell["affine"]
        if type(affines) is not list or len(affines) != len(nets):
            raise ValueError("Missing affine model")
        for net, pair in zip(nets, affines):
            if type(pair) is not list or len(pair) != 2:
                raise ValueError("Invalid affine coefficients")
            a, b = map(_integer, pair)
            slope, offset = 0, net.bias
            for c, w, bias in model_data(net)["terms"]:
                if c == 0:
                    continue
                if w == 0:
                    offset += c * max(0, bias)
                    continue
                active = (w > 0 and lo is not None and w * lo + bias > 0) or (
                    w < 0 and hi is not None and w * hi + bias > 0
                )
                inactive = (w > 0 and hi is not None and w * hi + bias <= 0) or (
                    w < 0 and lo is not None and w * lo + bias <= 0
                )
                if not active and not inactive:
                    raise ValueError("Cell crosses an unverified activation boundary")
                if active:
                    slope += c * w
                    offset += c * bias
            if (a, b) != (slope, offset):
                raise ValueError("Affine branch certificate is false")

        def contained(x):
            return (lo is None or lo <= x) and (hi is None or x <= hi)

        if property_name == "max_error":
            left = low if lo is None else max(low, lo)
            right = high if hi is None else min(high, hi)
            if left <= right:
                a, b = affines[0]
                c, d = affines[1]
                score = max(abs((a - c) * left + b - d), abs((a - c) * right + b - d))
                maximum = score if maximum is None else max(maximum, score)
        else:
            if property_name == "equal":
                a, b = affines[0]
                c, d = affines[1]
                a, b = a - c, b - d
            else:
                a, b = affines[0]
                c, d = affines[2]
                a, b = a - c, b - d
            if property_name == "equal":
                valid &= (
                    a * lo + b == 0
                    if lo is not None and lo == hi
                    else a == 0 and b == 0
                )
            else:
                na, nb = affines[1]
                ta, tb = affines[2]
                na, nb = na - ta, nb - tb
                if a == 0 and b == 0:
                    if old_correct_witness is None:
                        old_correct_witness = (
                            lo if lo is not None else hi if hi is not None else 0
                        )
                    valid &= (
                        na * lo + nb == 0
                        if lo is not None and lo == hi
                        else na == 0 and nb == 0
                    )
                elif a != 0 and (-b) % a == 0 and contained((-b) // a):
                    if old_correct_witness is None:
                        old_correct_witness = (-b) // a
                    valid &= na * ((-b) // a) + nb == 0
    result = cert["result"]
    if type(result) is not dict:
        raise ValueError("Missing result")
    if property_name == "max_error":
        if set(result) != {"max_error", "argmax"}:
            raise ValueError("Malformed maximum")
        score = _integer(result["max_error"])
        x = _integer(result["argmax"])
        if (
            score != maximum
            or not low <= x <= high
            or abs(_eval(nets[0], x) - _eval(nets[1], x)) != score
        ):
            raise ValueError("False exact maximum")
    else:
        if (
            set(result) != {"passes", "counterexample"}
            or type(result["passes"]) is not bool
            or result["passes"] != valid
        ):
            raise ValueError("False universal decision")
        x = result["counterexample"]
        if valid:
            if x is not None:
                raise ValueError("Positive certificate contains counterexample")
        else:
            x = _integer(x)
            witness = (
                _eval(nets[0], x) != _eval(nets[1], x)
                if property_name == "equal"
                else _eval(nets[0], x) == _eval(nets[2], x)
                and _eval(nets[1], x) != _eval(nets[2], x)
            )
            if not witness:
                raise ValueError("False counterexample witness")
    return {
        "checked": True,
        "kernel_proved": False,
        "property": property_name,
        "cells_checked": len(cells),
        "previously_correct_witness": old_correct_witness
        if property_name == "preserves"
        else None,
    }
