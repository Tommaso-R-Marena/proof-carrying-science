"""Exact equality, single-process timings and Python allocation peaks on fixed DAGs."""
from fractions import Fraction
from itertools import product
import json
import time
import tracemalloc

from ..kernel.dag import CausalDAG
from ..kernel.scm import BinarySCM


def graph(n, fanin):
    order = [f"x{i:02d}" for i in range(n)]
    parents = {node: order[max(0, i-fanin):i] for i, node in enumerate(order)}
    return BinarySCM(CausalDAG.from_parents(parents), {
        node: lambda values, i=i: Fraction(1 + ((sum(values.values()) + i) % 4), 5)
        for i, node in enumerate(order)
    }), order


def measure(fn):
    # Record wall time separately from peak tracing overhead.
    start = time.perf_counter()
    answer = fn()
    elapsed = time.perf_counter() - start
    tracemalloc.start()
    try:
        assert fn() == answer
        peak = tracemalloc.get_traced_memory()[1]
    finally:
        tracemalloc.stop()
    return answer, {"milliseconds": round(1000*elapsed, 3), "python_peak_bytes": peak}


def study():
    rows = []
    for n, fanin, intervened in product((5, 8, 10), (1, 3), (False, True)):
        model, names = graph(n, fanin)
        if intervened:
            model = model.intervene({names[n//2]: 1})
        target = names[-1]
        idx = model.graph.topological_order().index(target)
        ref, old = measure(lambda: sum(m for state, m in model.observational_table().items() if state[idx]))
        val, new = measure(lambda: model.p_obs({target: 1}))
        if val != ref:
            raise ValueError("exact answers disagree")
        rows.append(dict(nodes=n, max_parents=fanin, intervened=intervened,
                         probability=str(val), enumeration=old, frontier=new))
    return rows


if __name__ == "__main__":
    print(json.dumps(study(), indent=2))
