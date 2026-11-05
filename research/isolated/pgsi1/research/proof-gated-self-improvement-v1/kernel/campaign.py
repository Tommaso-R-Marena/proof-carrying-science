"""Prespecified exhaustive kernel replay; synthetic mathematics, not empirical AI safety."""

from __future__ import annotations
import argparse
from collections import Counter
from dataclasses import asdict
import gzip
import hashlib
import itertools
import json
from pathlib import Path
import random
import tarfile
from replay import Kernel, expression, lean_net, rows, z, canonical, digest
from guard import guard_expression, replay_guards, TARGET
from affine_certificates import certificate, verify
from proof_gate import Model, check
from universal_relu import Net, Term, single_neuron

SEED = 202610170130
BATCH = 128


def write(path, data):
    with path.open("xb") as f:
        f.write(canonical(data) + b"\n")


def run(output):
    k = Kernel(output)
    protocol = {
        "format": "pgsi-affine-kernel-protocol-v1",
        "seed": SEED,
        "model_lattice": {
            "activations": [False, True],
            "weights": [-3, 4],
            "biases": [-3, 4],
        },
        "two_unit_ordered_parameters": [-1, 0, 1],
        "window": [-20, 20],
        "brute_force_domain": [-64, 64],
        "batch": BATCH,
        "kernel_decide_only": True,
        "optimized_producer_trusted": False,
        "external_empirical_validation": False,
        "production_promotion": False,
        "scope": "finite flat scalar-input exact integer ReLU sums; not deep nets/floats/GPU",
        "source_sha256": k.sources,
    }
    write(
        k.output / "PROTOCOL.json", protocol
    )  # Before selecting/evaluating campaign cases.
    records, expressions, guard_exprs, classifications = [], [], [], []
    outcomes = Counter()

    def add(expr):
        expressions.append(expr)
        if len(expressions) == BATCH:
            flush()

    def flush():
        if expressions:
            r = k.replay(expressions, "Batch" + str(len(records)).zfill(3))
            records.append(r)
            expressions.clear()
            print(
                json.dumps({"batches": len(records), "kernel_claims": k.count}),
                flush=True,
            )

    # Classify each starting model: explicit correct witness, or a universal
    # kernel proof that no correct integer exists (via target shifted by one).
    models = [
        Model(r, w, b)
        for r, w, b in itertools.product((False, True), range(-3, 5), range(-3, 5))
    ]
    nets = {m: single_neuron(m.relu, m.weight, m.bias) for m in models}
    maxima, witnesses = {}, {}
    for m in models:
        n = nets[m]
        pc = certificate("preserves", (n, TARGET, TARGET))
        witness = verify(pc, (n, TARGET, TARGET), "preserves")[
            "previously_correct_witness"
        ]
        witnesses[m] = witness
        if witness is None:
            shifted = Net(TARGET.terms, TARGET.bias + 1)
            nc = certificate("preserves", (n, shifted, TARGET))
            assert nc["result"]["passes"]
            add(f"(.noCorrect {lean_net(n)} {lean_net(TARGET)} {rows(nc, 3)} : Claim)")
            outcomes["models_with_no_correct_integer"] += 1
        else:
            add(f"(.hasCorrect {lean_net(n)} {lean_net(TARGET)} {z(witness)} : Claim)")
            outcomes["models_with_correct_witness"] += 1
        classifications.append({"model": asdict(m), "correct_witness": witness})
        mc = certificate("max_error", (n, TARGET), (-20, 20))
        maxima[m] = mc
        assert mc["result"]["max_error"] == max(
            abs(n.predict(x) - TARGET.predict(x)) for x in range(-20, 21)
        )
        add(expression(mc, (n, TARGET), "max_error", (-20, 20)))
        add(expression(certificate("equal", (n, TARGET)), (n, TARGET), "equal"))
    # Every ordered transition, including negative universal decisions.
    for a in models:
        for b in models:
            an, bn = nets[a], nets[b]
            pc = certificate("preserves", (an, bn, TARGET))
            actual = pc["result"]["passes"]
            brute = all(
                an.predict(x) != TARGET.predict(x) or bn.predict(x) == TARGET.predict(x)
                for x in range(-64, 65)
            )
            assert actual == brute
            add(expression(pc, (an, bn, TARGET), "preserves"))
            outcomes[
                "universal_preserves_positive"
                if actual
                else "universal_preserves_negative"
            ] += 1
            if check(a, b).accepted:
                outcomes["finite_accepted"] += 1
                bad = not actual
                worse = (
                    maxima[b]["result"]["max_error"] > maxima[a]["result"]["max_error"]
                )
                outcomes["finite_lost_correct"] += bad
                outcomes["finite_max_error_regression"] += worse
                outcomes["finite_both_regressions"] += bad and worse
                if not bad and not worse:
                    outcomes["both_stronger_filters"] += 1
                    if witnesses[a] is not None:
                        outcomes["nonvacuous_guard_acceptances"] += 1
                        guard_exprs.append(
                            guard_expression(
                                a, b, pc, maxima[a], maxima[b], -20, 20, witnesses[a]
                            )
                        )
                    else:
                        outcomes["vacuous_stronger_filter_acceptances"] += 1
    # Exhaustive ordered two-unit cases, including zero/negative weights,
    # redundant terms, sign changes and singleton activation cells.
    terms = [Term(*p) for p in itertools.product((-1, 0, 1), repeat=3)]
    for a, b in itertools.product(terms, repeat=2):
        n = Net((a, b))
        perm = Net((b, a))
        add(expression(certificate("equal", (n, perm)), (n, perm), "equal"))
        mc = certificate("max_error", (n, TARGET), (-8, 8))
        assert mc["result"]["max_error"] == max(
            abs(n.predict(x) - TARGET.predict(x)) for x in range(-8, 9)
        )
        add(expression(mc, (n, TARGET), "max_error", (-8, 8)))
        outcomes["two_unit_configurations"] += 1
    rng = random.Random(SEED)
    for _ in range(64):
        n = Net(
            tuple(
                Term(rng.randint(-5, 5), rng.randint(-5, 5), rng.randint(-9, 9))
                for _ in range(6)
            ),
            rng.randint(-10, 10),
        )
        b = Net(
            n.terms
            + (Term(rng.randint(-5, 5), rng.randint(-5, 5), rng.randint(-9, 9)),),
            n.bias,
        )
        for prop, ns, bounds in (
            ("equal", (n, Net(tuple(reversed(n.terms)), n.bias)), None),
            ("preserves", (n, b, TARGET), None),
            ("max_error", (n, TARGET), (-23, 19)),
        ):
            c = certificate(prop, ns, bounds)
            if prop == "max_error":
                assert c["result"]["max_error"] == max(
                    abs(n.predict(x) - TARGET.predict(x)) for x in range(-23, 20)
                )
            add(expression(c, ns, prop, bounds))
        outcomes["random_multiunit_cases"] += 1
    flush()
    guard_records = []
    for start in range(0, len(guard_exprs), BATCH):
        guard_records.append(
            replay_guards(
                k,
                guard_exprs[start : start + BATCH],
                "GuardBatch" + str(start // BATCH).zfill(3),
            )
        )
        print(
            json.dumps({"guard_batches": len(guard_records), "kernel_claims": k.count}),
            flush=True,
        )
    scaling = []
    for width in (4, 8, 16, 32, 64):
        n = Net(
            tuple(
                Term(((-1) ** i) * (i % 3 + 1), i % 7 - 3, 3 * i - 100)
                for i in range(width)
            ),
            7,
        )
        perm = Net(tuple(reversed(n.terms)), 7)
        es = [
            expression(certificate("equal", (n, perm)), (n, perm), "equal"),
            expression(
                certificate("max_error", (n, TARGET), (-1000, 1000)),
                (n, TARGET),
                "max_error",
                (-1000, 1000),
            ),
        ]
        r = k.replay(es, "Width" + str(width))
        scaling.append({"width": width, **r})
    expected = {
        "finite_accepted": 4081,
        "finite_lost_correct": 76,
        "finite_max_error_regression": 441,
        "finite_both_regressions": 12,
        "both_stronger_filters": 3576,
        "nonvacuous_guard_acceptances": 741,
        "vacuous_stronger_filter_acceptances": 2835,
        "two_unit_configurations": 729,
        "random_multiunit_cases": 64,
    }
    for name, value in expected.items():
        assert outcomes[name] == value, (name, outcomes[name], value)
    write(k.output / "MODEL_CLASSIFICATION.json", classifications)
    result = {
        "format": "pgsi-affine-kernel-campaign-v1",
        "protocol_sha256": digest(k.output / "PROTOCOL.json"),
        "outcomes": dict(outcomes),
        "universal_transitions": 16384,
        "kernel_claims": k.count,
        "axioms_audited": len(k.axioms),
        "batches": records,
        "guard_batches": guard_records,
        "scaling": scaling,
        "source_sha256": k.sources,
        "kernel_checked_encoded_mathematical_claims": True,
        "serialized_host_refinement_proved": False,
        "production_authority": False,
        "external_empirical_validation": False,
    }
    semantic = {
        key: result[key]
        for key in (
            "outcomes",
            "universal_transitions",
            "kernel_claims",
            "axioms_audited",
        )
    }
    result["semantic_results_sha256"] = hashlib.sha256(canonical(semantic)).hexdigest()
    write(k.output / "RESULTS.json", result)
    # Keep exact generated proofs for receiver replay, with reproducible archive metadata.
    archive = k.output / "PROOFS.tar.gz"
    with archive.open("xb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as compressed:
            with tarfile.open(mode="w", fileobj=compressed) as tar:
                for p in sorted(k.output.glob("*.lean")):
                    info = tar.gettarinfo(str(p), arcname=p.name)
                    info.uid = info.gid = 0
                    info.uname = info.gname = ""
                    info.mtime = 0
                    info.mode = 0o600
                    with p.open("rb") as stream:
                        tar.addfile(info, stream)
    inventory = {
        p.name: digest(p)
        for p in sorted(k.output.iterdir())
        if p.is_file() and p.suffix in {".json", ".gz", ".log"}
    }
    write(k.output / "SHA256.json", inventory)
    print(
        json.dumps(
            {
                "kernel_claims": k.count,
                "semantic_results_sha256": result["semantic_results_sha256"],
                "outcomes": dict(outcomes),
            }
        ),
        flush=True,
    )
    return result


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    run(args.output)
