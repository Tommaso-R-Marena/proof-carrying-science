"""Portable reference-only scalar-ReLU certificate producer.

The replay consumer is independent of the original universal_relu algorithm.
A SHA-256 digest binds the certificate body but does NOT authenticate its author
or turn the Python calculations into a Lean kernel proof.
"""
from __future__ import annotations

import hashlib
import json

from universal_relu import (
    Net, integer_cells, universal_correctness_preserved,
    exact_interval_max_error,
)

PREFIX = b"PCS-RELU-REPLAY-v1\x00"
VERSION = "PCS-RELU-REPLAY-v1"


def canonical(obj: object) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=True, allow_nan=False).encode("ascii")


def model_json(net: Net) -> dict:
    return {"bias": str(net.bias),
            "terms": [[str(t.coefficient), str(t.weight), str(t.bias)]
                      for t in net.terms]}


def build_certificate(old: Net, candidate: Net, target: Net, *,
                      low: int = -20, high: int = 20) -> bytes:
    if type(low) is not int or type(high) is not int or low > high:
        raise ValueError("invalid integer verification interval")
    cuts, cells = integer_cells(old, candidate, target)
    rows = []
    points = {low, high}
    for cell in cells:
        x = cell.point()
        old_slope, old_bias = old.affine(x)
        candidate_slope, candidate_bias = candidate.affine(x)
        target_slope, target_bias = target.affine(x)
        rows.append([
            None if cell.low is None else str(cell.low),
            None if cell.high is None else str(cell.high),
            [str(old_slope-target_slope), str(old_bias-target_bias)],
            [str(candidate_slope-target_slope), str(candidate_bias-target_bias)],
        ])
        a = low if cell.low is None else max(low, cell.low)
        b = high if cell.high is None else min(high, cell.high)
        if a <= b:
            points.update((a, b))
    noforget = universal_correctness_preserved(old, candidate, target)
    oldmax, _ = exact_interval_max_error(old, target, low, high)
    newmax, _ = exact_interval_max_error(candidate, target, low, high)
    body = {
        "version": VERSION, "old": model_json(old),
        "candidate": model_json(candidate), "target": model_json(target),
        "window": [str(low), str(high)],
        "cuts": [str(c) for c in cuts],
        "cells": rows, "window_points": [str(p) for p in sorted(points)],
        "claim": {
            "no_forgetting": noforget.passes,
            "counterexample": None if noforget.passes else str(noforget.counterexample),
            "old_max_error": str(oldmax), "new_max_error": str(newmax),
            "no_worse_in_window": newmax <= oldmax,
        },
    }
    return canonical({
        "body": body,
        "sha256": hashlib.sha256(PREFIX + canonical(body)).hexdigest(),
    })
