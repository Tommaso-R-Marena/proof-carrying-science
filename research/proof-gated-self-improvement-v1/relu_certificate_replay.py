"""Standalone all-integer ReLU replay; imports NO generator or universal_relu code.

This is an independent Python reference checker, NOT a kernel proof, signed
attestation, or immutable deployment authority. Reconstructs every integer
cell, both local affine models, the forgotten-input condition, and exact
bounded-window maxima. Rehashing a forged certificate cannot bypass replay.
"""
from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
import hashlib
import json
import re

PREFIX = b"PCS-RELU-REPLAY-v1\x00"
VERSION = "PCS-RELU-REPLAY-v1"
MAX_BYTES = 4 * 1024 * 1024
MAX_UNITS = 512
_INT = re.compile(r"(?:0|-?[1-9][0-9]*)\Z", re.ASCII)
_HASH = re.compile(r"[0-9a-f]{64}\Z", re.ASCII)


class ReplayError(ValueError):
    pass


@dataclass(frozen=True)
class ReplayVerdict:
    no_forgetting: bool
    counterexample: int | None
    old_max_error: int
    new_max_error: int
    no_worse_in_window: bool
    cell_count: int
    sample_count: int
    digest: str


def canonical(obj: object) -> bytes:
    try:
        return json.dumps(obj, sort_keys=True, separators=(",", ":"),
                          ensure_ascii=True, allow_nan=False).encode("ascii")
    except (TypeError, ValueError) as exc:
        raise ReplayError("invalid JSON") from exc


def _duplicate_reject(pairs):
    result = {}
    for key, val in pairs:
        if key in result:
            raise ReplayError("duplicate JSON key")
        result[key] = val
    return result


def _number_reject(_):
    raise ReplayError("JSON numbers forbidden: use canonical decimal strings")


def _fields(obj, wanted):
    if not isinstance(obj, dict) or set(obj) != wanted:
        raise ReplayError("invalid schema")
    return obj


def _decimal(value):
    if type(value) is not str or len(value) > 121 or not _INT.fullmatch(value) or value == "-0":
        raise ReplayError("noncanonical decimal")
    return int(value)


def _read(raw: bytes):
    if type(raw) is not bytes or not raw or len(raw) > MAX_BYTES:
        raise ReplayError("invalid certificate length/type")
    try:
        obj = json.loads(raw.decode("ascii"), object_pairs_hook=_duplicate_reject,
                         parse_int=_number_reject, parse_float=_number_reject,
                         parse_constant=_number_reject)
    except (UnicodeError, ValueError, RecursionError) as exc:
        raise ReplayError("invalid certificate JSON") from exc
    if type(obj) is not dict or canonical(obj) != raw:
        raise ReplayError("noncanonical JSON encoding")
    return obj


def _network(obj):
    data = _fields(obj, {"bias", "terms"})
    rows = data["terms"]
    if type(rows) is not list or len(rows) > MAX_UNITS:
        raise ReplayError("invalid hidden-unit count")
    terms = []
    for row in rows:
        if type(row) is not list or len(row) != 3:
            raise ReplayError("malformed hidden unit")
        terms.append(tuple(_decimal(x) for x in row))
    return tuple(terms), _decimal(data["bias"])


def _evaluate(net, x):
    terms, bias = net
    for coeff, weight, offset in terms:
        z = weight*x + offset
        if z > 0:
            bias += coeff*z
    return bias


def _affine(net, x):
    slope, intercept = 0, net[1]
    for coeff, weight, offset in net[0]:
        if weight*x + offset > 0:
            slope += coeff*weight
            intercept += coeff*offset
    return slope, intercept


def _difference(a,b,x):
    s,t = _affine(a,x)
    u,v = _affine(b,x)
    return s-u, t-v


def _cut(w,b):
    if w == 0:
        return None
    rational = Fraction(-b, w)
    if w > 0:
        return rational.numerator // rational.denominator
    return -((-rational.numerator)//rational.denominator)-1


def _partition(nets):
    cuts = sorted({c for terms,_ in nets for _,w,b in terms
                   if (c := _cut(w,b)) is not None})
    cells, lower = [], None
    for c in cuts:
        cells.append((lower,c))
        lower = c+1
    cells.append((lower,None))
    return cuts, cells


def _inside(x,cell):
    a,b = cell
    return (a is None or a<=x) and (b is None or x<=b)


def _rep(cell):
    a,b = cell
    return a if a is not None else (b if b is not None else 0)


def _zero_everywhere(slope, offset, cell):
    a,b = cell
    if a is not None and b == a:
        return slope*a + offset == 0
    return slope == 0 and offset == 0


def _different_at(slope,offset,cell):
    a,b = cell
    if a is not None and b == a:
        samples = (a,)
    elif a is not None:
        samples = (a,a+1)
    elif b is not None:
        samples = (b-1,b)
    else:
        samples = (0,1)
    for x in samples:
        if slope*x+offset != 0:
            return x
    raise ReplayError("invalid nonzero-affine witness")


def _forgotten(old_s,old_b,new_s,new_b,cell):
    if _zero_everywhere(old_s,old_b,cell):
        return None if _zero_everywhere(new_s,new_b,cell) else _different_at(new_s,new_b,cell)
    if old_s == 0 or (-old_b)%old_s:
        return None
    x = (-old_b)//old_s
    if _inside(x,cell) and new_s*x+new_b != 0:
        return x
    return None


def _endpoints(cells,low,high):
    points = {low,high}
    for a,b in cells:
        lo = low if a is None else max(low,a)
        hi = high if b is None else min(high,b)
        if lo <= hi:
            points.update((lo,hi))
    return sorted(points)


def replay(raw: bytes) -> ReplayVerdict:
    outer = _fields(_read(raw), {"body", "sha256"})
    digest = outer["sha256"]
    if type(digest) is not str or not _HASH.fullmatch(digest):
        raise ReplayError("invalid certificate digest")
    body = _fields(outer["body"], {
        "version", "old", "candidate", "target", "window",
        "cuts", "cells", "window_points", "claim",
    })
    if body["version"] != VERSION:
        raise ReplayError("unexpected protocol version")
    if hashlib.sha256(PREFIX+canonical(body)).hexdigest() != digest:
        raise ReplayError("certificate digest mismatch")
    nets = tuple(_network(body[key]) for key in ("old","candidate","target"))
    if type(body["window"]) is not list or len(body["window"]) != 2:
        raise ReplayError("invalid interval")
    low,high = (_decimal(x) for x in body["window"])
    if low > high:
        raise ReplayError("empty interval")
    cuts,cells = _partition(nets)
    rows = body["cells"]
    if type(body["cuts"]) is not list or [_decimal(x) for x in body["cuts"]] != cuts:
        raise ReplayError("altered/missing breakpoints")
    if type(rows) is not list or len(rows) != len(cells):
        raise ReplayError("altered/missing cells")
    actual_forgotten = None
    for cell,row in zip(cells,rows):
        if type(row) is not list or len(row) != 4:
            raise ReplayError("malformed affine row")
        a,b = cell
        if row[:2] != [None if a is None else str(a),None if b is None else str(b)]:
            raise ReplayError("altered cell bounds")
        x = _rep(cell)
        old_s,old_b = _difference(nets[0],nets[2],x)
        new_s,new_b = _difference(nets[1],nets[2],x)
        if row[2:] != [[str(old_s),str(old_b)],[str(new_s),str(new_b)]]:
            raise ReplayError("forged affine coefficients")
        w = _forgotten(old_s,old_b,new_s,new_b,cell)
        if actual_forgotten is None and w is not None:
            if _evaluate(nets[0],w) != _evaluate(nets[2],w) or (
                _evaluate(nets[1],w) == _evaluate(nets[2],w)):
                raise ReplayError("invalid proof witness")
            actual_forgotten = w
    points = _endpoints(cells,low,high)
    if type(body["window_points"]) is not list or [
        _decimal(x) for x in body["window_points"]] != points:
        raise ReplayError("incomplete/altered bounded interval coverage")
    old_max = max(abs(_evaluate(nets[0],x)-_evaluate(nets[2],x)) for x in points)
    new_max = max(abs(_evaluate(nets[1],x)-_evaluate(nets[2],x)) for x in points)
    claim = _fields(body["claim"], {
        "no_forgetting", "counterexample", "old_max_error",
        "new_max_error", "no_worse_in_window",
    })
    if type(claim["no_forgetting"]) is not bool or type(claim["no_worse_in_window"]) is not bool:
        raise ReplayError("non-Boolean claim")
    supplied = claim["counterexample"]
    if actual_forgotten is None and supplied is not None:
        raise ReplayError("spurious counterexample")
    if actual_forgotten is not None:
        if supplied is None:
            raise ReplayError("missing counterexample")
        supplied_x = _decimal(supplied)
        if _evaluate(nets[0],supplied_x) != _evaluate(nets[2],supplied_x) or (
            _evaluate(nets[1],supplied_x) == _evaluate(nets[2],supplied_x)):
            raise ReplayError("invalid claimed counterexample")
    actual = {
        "no_forgetting":actual_forgotten is None,
        "counterexample":supplied,
        "old_max_error":str(old_max),
        "new_max_error":str(new_max),
        "no_worse_in_window":new_max<=old_max,
    }
    if actual != claim:
        raise ReplayError("false replay claims")
    return ReplayVerdict(actual_forgotten is None,
                         None if supplied is None else _decimal(supplied),
                         old_max,new_max,new_max<=old_max,len(cells),len(points),digest)


def main(argv: list[str] | None = None) -> int:
    """Standalone offline research replay. Exit 0 means *consistency* only.

    It does NOT mean that a model was authorized, promoted, or globally safe.
    For checking endorsement, consumers must inspect the explicit Boolean
    findings in the JSON output and separately obtain a Lean authority verdict.
    """
    from pathlib import Path
    import sys
    if argv is None:
        argv = sys.argv[1:]
    if len(argv) != 1:
        print("REJECT:expected_one_certificate_file", file=sys.stderr)
        return 2
    try:
        path = Path(argv[0])
        with path.open("rb") as handle:
            raw = handle.read(MAX_BYTES+1)
        verdict = replay(raw)
    except (OSError, ReplayError) as exc:
        print(f"REJECT:invalid_reference_certificate:{exc}", file=sys.stderr)
        return 2
    print(canonical({
        "replay_consistent": True,
        "lean_kernel_verdict": False,
        "production_authorized": False,
        "no_forgetting": verdict.no_forgetting,
        "no_worse_in_window": verdict.no_worse_in_window,
        "counterexample": None if verdict.counterexample is None
                         else str(verdict.counterexample),
        "old_max_error": str(verdict.old_max_error),
        "new_max_error": str(verdict.new_max_error),
        "cell_count": str(verdict.cell_count),
        "sample_count": str(verdict.sample_count),
        "sha256": verdict.digest,
    }).decode("ascii"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
