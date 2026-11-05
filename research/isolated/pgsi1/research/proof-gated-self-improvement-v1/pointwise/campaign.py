"""Prespecified exhaustive dominance replay and bounded search-graph experiment."""

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
import time

from dominance import certificate
from receive import Kernel, canonical, digest, expression
from proof_gate import Model, check
from universal_relu import Net, Term, single_neuron

SEED = 202610170201
TARGET = Net((Term(1, 2, 1),))


def write(path, data):
    with path.open("xb") as f:
        f.write(canonical(data) + b"\n")


def search_graph(models, accepted):
    """Exact graph, not a claim that a learned proposer improves itself.

    A local proposal toggles activation or changes ONE parameter by ONE.
    Reachability explores all accepted local paths, independently of greedy order.
    """
    neighbors = {
        i: [
            j
            for j, b in enumerate(models)
            if (int(a.relu != b.relu) + abs(a.weight - b.weight) + abs(a.bias - b.bias))
            == 1
        ]
        for i, a in enumerate(models)
    }
    target = models.index(Model(True, 2, 1))
    result = {}
    for name, edges in accepted.items():
        graph = {
            i: [j for j in neighbors[i] if (i, j) in edges] for i in range(len(models))
        }
        reachable = {target}
        while True:
            more = {i for i in graph if any(j in reachable for j in graph[i])}
            if more <= reachable:
                break
            reachable |= more
        stuck = [i for i in graph if i != target and not graph[i]]
        # A strict one-step target jump is a coordinated-change control.
        escapes = [i for i in stuck if (i, target) in edges]
        result[name] = {
            "local_edges": sum(map(len, graph.values())),
            "starts_reaching_target_including_target": len(reachable),
            "local_dead_ends_excluding_target": len(stuck),
            "dead_ends_escaped_by_direct_target_proposal": len(escapes),
            "dead_end_models": [asdict(models[i]) for i in stuck],
            "adaptive_proposer_learning_tested": False,
        }
    return result


def run(output):
    k = Kernel(output)
    protocol = {
        "format": "pgsi-pointwise-protocol-v1",
        "seed": SEED,
        "lattice": {"activation": [False, True], "weight": [-3, 4], "bias": [-3, 4]},
        "oracle_interval": [-64, 64],
        "ordered_two_unit_parameters": [-1, 0, 1],
        "random_cases": 128,
        "scaling_widths": [4, 8, 16, 32, 63],
        "batch": 128,
        "source_sha256": k.sources,
        "kernel_decide_only": True,
        "production_authority": False,
        "empirical_external_validation": False,
        "policy": "finite benchmark gate AND universal pointwise absolute-error dominance",
        "search_graph": "one activation toggle or unit weight/bias step; exact reachability",
    }
    write(k.output / "PROTOCOL.json", protocol)
    outcomes = Counter()
    records, pending, decisions = [], [], []
    edges = {"finite_gate": set(), "finite_and_pointwise": set()}

    def flush():
        if pending:
            records.append(k.replay(pending, "Batch" + str(len(records)).zfill(3)))
            pending.clear()
            print(
                json.dumps({"proof_modules": len(records), "claims": k.count}),
                flush=True,
            )

    def add(ns):
        c = certificate(*ns)
        pending.append(expression(c, ns))
        if len(pending) == 128:
            flush()
        return c

    models = [
        Model(r, w, b)
        for r, w, b in itertools.product((False, True), range(-3, 5), range(-3, 5))
    ]
    nets = [single_neuron(m.relu, m.weight, m.bias) for m in models]
    for i, a in enumerate(models):
        for j, b in enumerate(models):
            ns = (nets[i], nets[j], TARGET)
            c = add(ns)
            passed = c["result"]["passes"]
            brute = all(
                abs(nets[j].predict(x) - TARGET.predict(x))
                <= abs(nets[i].predict(x) - TARGET.predict(x))
                for x in range(-64, 65)
            )
            if passed != brute:
                raise AssertionError("Small-lattice bounded oracle differs")
            outcomes["pointwise_positive" if passed else "pointwise_negative"] += 1
            finite = check(a, b).accepted
            if finite:
                edges["finite_gate"].add((i, j))
                outcomes["finite_accepted"] += 1
                if passed:
                    edges["finite_and_pointwise"].add((i, j))
                    outcomes["finite_and_pointwise_accepted"] += 1
                else:
                    outcomes["finite_rejected_by_pointwise"] += 1
            decisions.append(
                {
                    "old": i,
                    "new": j,
                    "finite": finite,
                    "pointwise": passed,
                    "counterexample": c["result"]["counterexample"],
                }
            )
    # Exhaust all 27^2 ordered two-unit representations; permutation and target
    # controls stress sign refinement, cancellation, negative weights and zeros.
    terms = [Term(*v) for v in itertools.product((-1, 0, 1), repeat=3)]
    for a, b in itertools.product(terms, repeat=2):
        n = Net((a, b))
        assert add((n, Net((b, a)), TARGET))["result"]["passes"]
        assert add((n, TARGET, TARGET))["result"]["passes"]
        outcomes["two_unit_configurations"] += 1
    rng = random.Random(SEED)
    for _ in range(128):
        ns = tuple(
            Net(
                tuple(
                    Term(*(rng.randint(-7, 7) for _ in range(3)))
                    for _ in range(rng.randint(0, 8))
                ),
                rng.randint(-7, 7),
            )
            for _ in range(3)
        )
        c = add(ns)
        if c["result"]["passes"]:
            assert all(
                abs(ns[1].predict(x) - ns[2].predict(x))
                <= abs(ns[0].predict(x) - ns[2].predict(x))
                for x in range(-256, 257)
            )
        else:
            x = c["result"]["counterexample"]
            assert abs(ns[1].predict(x) - ns[2].predict(x)) > abs(
                ns[0].predict(x) - ns[2].predict(x)
            )
        outcomes["random_multiunit_cases"] += 1
    for parameter in range(18, 32):
        ns = (
            single_neuron(True, parameter, 4),
            single_neuron(True, parameter + 1, 2 - parameter),
            TARGET,
        )
        assert not add(ns)["result"]["passes"]
        outcomes["supported_tail_cases_rejected"] += 1
    # Mathematical, successful repeated changes; no training/acceleration claim.
    zero, middle = Net(()), Net((Term(1, 1, 1),))
    for ns in ((zero, middle, TARGET), (middle, TARGET, TARGET)):
        assert add(ns)["result"]["passes"]
        outcomes["useful_composed_transitions"] += 1
    far = Net((Term(1, 2, 1), Term(10, 1, -21)))
    assert not add((zero, far, TARGET))["result"]["passes"]
    outcomes["multiunit_worsening_tail_rejected"] += 1
    flush()
    scaling = []
    for width in (4, 8, 16, 32, 63):
        n = Net(
            tuple(
                Term(1 if i % 2 else -1, (-1) ** i * (i + 1), i - 20)
                for i in range(width)
            )
        )
        ns = (n, Net(tuple(reversed(n.terms))), TARGET)
        start = time.perf_counter()
        c = certificate(*ns)
        elapsed = time.perf_counter() - start
        assert c["result"]["passes"]
        proof = k.replay([expression(c, ns)], "Width" + str(width))
        records.append(proof)
        scaling.append(
            {
                "width": width,
                "cells": len(c["cells"]),
                "producer_seconds": elapsed,
                "kernel_seconds": proof["elapsed_seconds"],
            }
        )
    graph = search_graph(models, edges)
    write(
        k.output / "DECISIONS.json",
        {"models": [asdict(m) for m in models], "transitions": decisions},
    )
    write(k.output / "SEARCH_GRAPH.json", graph)
    semantic = {
        "outcomes": dict(outcomes),
        "kernel_claims": k.count,
        "universal_transitions": 16384,
        "pointwise_theorems": len(k.axioms),
        "search_graph": graph,
    }
    result = {
        "format": "pgsi-pointwise-campaign-v1",
        **semantic,
        "semantic_results_sha256": hashlib.sha256(canonical(semantic)).hexdigest(),
        "protocol_sha256": digest(k.output / "PROTOCOL.json"),
        "source_sha256": k.sources,
        "proofs": records,
        "scaling": scaling,
        "kernel_checked_encoded_mathematical_claims": True,
        "native_execution_refinement_proved": False,
        "production_authority": False,
        "external_empirical_validation": False,
    }
    write(k.output / "RESULTS.json", result)
    # Every archived byte is numeric-template proof data; never auto-execute it.
    with (k.output / "PROOFS.tar.gz").open("xb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as gz:
            with tarfile.open(mode="w", fileobj=gz) as tar:
                for record in records:
                    p = k.output / record["file"]
                    info = tar.gettarinfo(str(p), arcname=p.name)
                    info.uid = info.gid = info.mtime = 0
                    info.uname = info.gname = ""
                    info.mode = 0o600
                    with p.open("rb") as f:
                        tar.addfile(info, f)
    inventory = {
        p.name: digest(p)
        for p in sorted(k.output.iterdir())
        if p.is_file() and p.suffix in {".json", ".log", ".gz"}
    }
    write(k.output / "SHA256.json", inventory)
    print(
        json.dumps(
            {
                "kernel_claims": k.count,
                "outcomes": dict(outcomes),
                "search_graph": graph,
                "semantic_results_sha256": result["semantic_results_sha256"],
            }
        ),
        flush=True,
    )
    return result


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output", type=Path, required=True)
    run(p.parse_args().output)
