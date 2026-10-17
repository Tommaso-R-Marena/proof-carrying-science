"""Offline kernel-checked PGSI1 strengthening; does not promote any model."""

from __future__ import annotations
import argparse
import hashlib
from dataclasses import asdict
import json
from pathlib import Path
from replay import (
    Kernel,
    rows,
    z,
    integer,
    audit,
    canonical,
    strict_json,
    _read_regular,
    digest,
)
from affine_certificates import certificate, verify
from proof_gate import parse_model, check, wire_bytes
from universal_relu import Net, Term, single_neuron
from pinned_authority import PinnedAuthority

TARGET = Net((Term(1, 2, 1),))


def neuron(m):
    return (
        "⟨"
        + ("true" if m.relu else "false")
        + ","
        + z(m.weight)
        + ","
        + z(m.bias)
        + "⟩"
    )


def guard_expression(old, new, preservation, old_cert, new_cert, low, high, witness):
    # All three data-to-Lean certificates are structurally checked first; the
    # composed Lean checker, not these Python validators, decides mathematical truth.
    from replay import expression

    a = single_neuron(old.relu, old.weight, old.bias)
    b = single_neuron(new.relu, new.weight, new.bias)
    expression(preservation, (a, b, TARGET), "preserves", witness=witness)
    expression(old_cert, (a, TARGET), "max_error", (low, high))
    expression(new_cert, (b, TARGET), "max_error", (low, high))
    om, nm = old_cert["result"], new_cert["result"]
    return (
        "(⟨"
        + ",".join(
            (
                neuron(old),
                neuron(new),
                rows(preservation, 3),
                rows(old_cert, 2),
                rows(new_cert, 2),
                z(low),
                z(high),
                str(integer(om["max_error"])),
                str(integer(nm["max_error"])),
                z(om["argmax"]),
                z(nm["argmax"]),
                z(witness),
            )
        )
        + "⟩ : GuardCase)"
    )


def guard_module(expressions):
    if not 1 <= len(expressions) <= 256:
        raise ValueError("Guard batch budget exceeded")
    return (
        "import PGSI1Bridge\nset_option maxRecDepth 10000\nset_option maxHeartbeats 20000000\n"
        "open PCS.Research.IntegerAffine PCS.Research.PGSI1Bridge\n"
        "namespace PCS.Research.GuardReplay\ndef cases : List GuardCase := [\n"
        + ",\n".join(expressions)
        + "]\n"
        "theorem checked : cases.all checkGuardCase = true := by decide\n"
        "theorem cases_sound : ∀ c ∈ cases, GuardMeaning c := checkGuardBatch_sound cases checked\n"
        "#print axioms cases_sound\nend PCS.Research.GuardReplay\n"
    )


def replay_guards(kernel, expressions, name):
    import re, time

    if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]*", name):
        raise ValueError("Invalid guard output name")
    p = kernel.output / (name + ".lean")
    raw = guard_module(expressions)
    with p.open("x") as f:
        f.write(raw)
    expected_sha = hashlib.sha256(raw.encode()).hexdigest()
    if digest(p) != expected_sha:
        raise RuntimeError("Generated guard proof changed before replay")
    start = time.perf_counter()
    log = kernel.run(p)
    if digest(p) != expected_sha:
        raise RuntimeError("Generated guard proof changed during replay")
    ax = audit(log, {"PCS.Research.GuardReplay.cases_sound"})
    kernel.count += len(expressions)
    return {
        "file": p.name,
        "sha256": expected_sha,
        "claims": len(expressions),
        "elapsed_seconds": time.perf_counter() - start,
        "axioms": ax,
    }


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--request", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument(
        "--bundle",
        type=Path,
        help="Optional owner-built finite-gate native verifier; no promotion",
    )
    a = p.parse_args()
    request_raw = _read_regular(a.request, 65536)
    r = strict_json(request_raw)
    if type(r) is not dict or set(r) != {"old", "candidate", "interval"}:
        raise ValueError("Expected exact receiver guard request")
    old, new = parse_model(r["old"]), parse_model(r["candidate"])
    if type(r["interval"]) is not list or len(r["interval"]) != 2:
        raise ValueError("Expected interval pair")
    lo, hi = map(integer, r["interval"])
    if lo > hi or not check(old, new).accepted:
        raise ValueError("No finite improvement or invalid interval")
    an, bn = [single_neuron(m.relu, m.weight, m.bias) for m in (old, new)]
    pc = certificate("preserves", (an, bn, TARGET))
    w = verify(pc, (an, bn, TARGET), "preserves")["previously_correct_witness"]
    if not pc["result"]["passes"] or w is None:
        raise ValueError("No nonvacuous universal preservation certificate")
    oc, nc = [certificate("max_error", (n, TARGET), (lo, hi)) for n in (an, bn)]
    expr = guard_expression(old, new, pc, oc, nc, lo, hi, w)
    k = Kernel(a.output)
    proof = replay_guards(k, [expr], "Guard")
    native = None
    if a.bundle is not None:
        native = PinnedAuthority(a.bundle).authorize(wire_bytes(old), wire_bytes(new))
    record = {
        "format": "pgsi-offline-kernel-guard-v1",
        "sources": k.sources,
        "lean_version": k.version,
        "request_sha256": hashlib.sha256(request_raw).hexdigest(),
        "proof": proof,
        "old": asdict(old),
        "candidate": asdict(new),
        "old_canonical_artifact_hex": wire_bytes(old).hex(),
        "candidate_canonical_artifact_hex": wire_bytes(new).hex(),
        "nonvacuity_witness": w,
        "interval": [lo, hi],
        "old_exact_maximum": oc["result"],
        "new_exact_maximum": nc["result"],
        "native_finite_authorization": native,
        "kernel_checked_mathematical_guard": True,
        "promotion_performed": False,
        "production_authority": False,
        "serialized_host_refinement_proved": False,
        "external_scientific_validation": False,
    }
    (k.output / "GUARD_RECEIPT.json").write_bytes(canonical(record) + b"\n")
    print(json.dumps(record, sort_keys=True))


if __name__ == "__main__":
    main()
