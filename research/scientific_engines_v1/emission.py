"""Numeric-only proof generation. Descriptive strings never enter Lean source."""

import copy, tempfile
from pathlib import Path
from .vendor.prism.python.prism.core import Problem
from .vendor.prism.python.prism.lean_export import export
from .vendor.aion.python.aion.emit_lean import emit


def prism(spec, **claims):
    p = spec.P
    # Labels are metadata, not mathematical indices. Safe deterministic labels
    # eliminate comment/namespace injection without changing any mathematical data.
    safe = Problem(
        [f"m{i}" for i in range(p.n)],
        [f"e{i}" for i in range(p.k)],
        [[f"o{j}" for j in range(len(o))] for o in p.outcomes],
        p.obs,
        p.q,
        p.cost,
    )
    mask = p.full
    for a in spec.assumptions:
        mask &= a["mask"]
    return export(
        safe,
        "PCSReplay",
        K_mask=spec.version_space(),
        eps=spec.eps,
        assumption_mask=mask,
        data=spec.data,
        problem_hash=spec.hash,
        **claims,
    )


def aion(cert):
    safe = copy.deepcopy(cert)
    safe["model"]["species"] = [f"s{i}" for i in range(len(safe["model"]["species"]))]
    for i, r in enumerate(safe["model"]["reactions"]):
        r["name"] = f"r{i}"
    with tempfile.TemporaryDirectory(prefix="pcs-safe-emission-", dir="/tmp") as d:
        p = Path(d) / "Replay.lean"
        emit(safe, "PCSReplay", str(p))
        source = p.read_text()
    if "native_decide" in source:
        raise ValueError("Compiler-trusted certificate forbidden")
    return source
