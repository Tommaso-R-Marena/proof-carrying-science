"""Exhaustive independent replay over original 128-model/16,384-transition lattice.

Run from the research directory: python relu_replay_campaign.py

This is a reproducible synthetic *Python reference* cross-check against the
previous falsification campaign; it is NOT Lean kernel verification.
"""
from __future__ import annotations

import hashlib
import itertools
import json

from proof_gate import Model, check
from universal_relu import Net, Term, single_neuron
from relu_certificate_export import build_certificate
from relu_certificate_replay import replay

EXPECTED = (4081,76,441,12,3576)
TARGET = Net((Term(1,2,1),))
DOMAIN = (-20,20)


def run() -> dict:
    models = [Model(relu,w,b) for relu,w,b in itertools.product(
        (False,True),range(-3,5),range(-3,5))]
    nets = {m: single_neuron(m.relu,m.weight,m.bias) for m in models}
    counts = [0,0,0,0,0]
    digest = b"\x00"*32
    checked = 0
    for old in models:
        for candidate in models:
            checked += 1
            if not check(old,candidate).accepted:
                continue
            certificate = build_certificate(
                nets[old],nets[candidate],TARGET,low=DOMAIN[0],high=DOMAIN[1])
            result = replay(certificate)
            counts[0] += 1
            lost = not result.no_forgetting
            worsened = not result.no_worse_in_window
            if lost: counts[1] += 1
            if worsened: counts[2] += 1
            if lost and worsened: counts[3] += 1
            if not lost and not worsened: counts[4] += 1
            digest = hashlib.sha256(
                b"PCS-INDEPENDENT-REPLAY-CAMPAIGN-v1\x00"+
                digest+bytes.fromhex(result.digest)).digest()
    if checked != 16384 or tuple(counts) != EXPECTED:
        raise AssertionError(
            f"independent replay differs from frozen study: {checked}, {counts}")
    return {
        "models":len(models),
        "ordered_transitions":checked,
        "baseline_accepted":counts[0],
        "lost_correct_integer":counts[1],
        "worsened_bounded_window_maximum":counts[2],
        "failed_both":counts[3],
        "passed_both":counts[4],
        "certificate_transcript_sha256":digest.hex(),
        "authority":"independent_python_reference_only",
    }


if __name__ == "__main__":
    print(json.dumps(run(), sort_keys=True, indent=2))
