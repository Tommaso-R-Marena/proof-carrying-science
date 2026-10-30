"""Posthoc mathematical counterexample family, separate from the frozen lattice."""

from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import sys

KERNEL = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KERNEL))
from replay import Kernel, audit, digest, canonical
from guard import guard_expression, replay_guards, TARGET
from affine_certificates import certificate
from pinned_authority import PinnedAuthority
from proof_gate import Model, check, wire_bytes, target
from universal_relu import single_neuron


def run(output, bundle):
    k = Kernel(output)
    authority = PinnedAuthority(bundle)
    cases, observations = [], []
    for parameter in range(18, 32):
        old = Model(True, parameter, 4)
        new = Model(True, parameter + 1, 2 - parameter)
        a, b = [single_neuron(m.relu, m.weight, m.bias) for m in (old, new)]
        preservation = certificate("preserves", (a, b, TARGET))
        oc, nc = [certificate("max_error", (n, TARGET), (-20, 20)) for n in (a, b)]
        cases.append(guard_expression(old, new, preservation, oc, nc, -20, 20, -1))
        native = authority.authorize(wire_bytes(old), wire_bytes(new))
        reference = check(old, new)
        first_worse = parameter + 3
        assert (
            reference.accepted
            and reference.old_loss == 6 * parameter
            and reference.new_loss == 3 * parameter - 2
        )
        assert oc["result"]["max_error"] == 20 * parameter - 37
        assert nc["result"]["max_error"] == 19 * (parameter - 1)
        observations.append(
            {
                "parameter": parameter,
                "old_artifact_hex": wire_bytes(old).hex(),
                "candidate_artifact_hex": wire_bytes(new).hex(),
                "native_finite_authorization": native,
                "old_loss": reference.old_loss,
                "new_loss": reference.new_loss,
                "old_maximum": oc["result"],
                "new_maximum": nc["result"],
                "tail_start_inclusive": first_worse,
                "old_error_at_tail_start": abs(
                    old.predict(first_worse) - target(first_worse)
                ),
                "new_error_at_tail_start": abs(
                    new.predict(first_worse) - target(first_worse)
                ),
            }
        )
    record = replay_guards(k, cases, "FamilyGuards")
    source = KERNEL / "results/supported-family-v1/FamilyTail.lean"
    proof_sha = digest(source)
    log = k.run(source)
    if digest(source) != proof_sha:
        raise RuntimeError("Family proof changed during checking")
    axioms = audit(
        log, {"PCS.Research.SupportedCounterexampleFamily.every_tail_input_worsens"}
    )
    (k.output / "TAIL_AXIOMS.log").write_text(log)
    (k.output / "FamilyTail.lean").write_bytes(source.read_bytes())
    result = {
        "format": "pgsi-supported-guard-counterexample-family-v1",
        "selection": "Posthoc constructed family; not part of prespecified 128-model frequencies",
        "parameters": list(range(18, 32)),
        "cases": observations,
        "kernel_guard_proof": record,
        "tail_theorem_for_every_integer_k_ge_18_and_x_ge_k_plus_3": True,
        "tail_axioms": axioms,
        "tail_source_sha256": proof_sha,
        "sources": k.sources,
        "runner_sha256": digest(__file__),
        "native_finite_authorizations": 14,
        "kernel_checked_guard_cases": 14,
        "promotion_performed": False,
        "native_execution_refinement_proved": False,
        "external_scientific_validation": False,
    }
    (k.output / "RESULT.json").write_bytes(canonical(result) + b"\n")
    index = {
        p.name: hashlib.sha256(p.read_bytes()).hexdigest()
        for p in k.output.iterdir()
        if p.is_file() and p.suffix in {".lean", ".json", ".log"}
    }
    (k.output / "SHA256.json").write_bytes(canonical(index) + b"\n")
    print(
        json.dumps(
            {
                "native_authorizations": 14,
                "kernel_guard_cases": 14,
                "universal_tail_theorem": True,
                "promoted": False,
                "proof_sha256": proof_sha,
            }
        ),
        flush=True,
    )
    return result


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output", required=True, type=Path)
    p.add_argument("--bundle", required=True, type=Path)
    a = p.parse_args()
    run(a.output, a.bundle)
