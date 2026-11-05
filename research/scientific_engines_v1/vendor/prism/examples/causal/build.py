"""Demonstration B: partial identification and experiment design in a finite causal model.

Structural causal model (binary treatment X, binary outcome Y, arbitrary latent
confounding):  U = (U_X, U_Y),  X := U_X,  Y := g_{U_Y}(X), with U_Y one of the four
response types  never (g ≡ 0), always (g ≡ 1), helped (g(x) = x), hurt (g(x) = 1-x)
(canonical response-function representation; Balke & Pearl).  A *model* is a joint
distribution of (U_X, U_Y) on the rational grid with denominator N (all of the
latent confounding structure is allowed).

Experiments (idealized, infinite-sample, exact distributions):
  survey            observational distribution P(X, Y)                 cost 1
  rct_treat         P(Y = 1 | do(X = 1))  (one-arm trial)               cost 2
  rct_control       P(Y = 1 | do(X = 0))                               cost 2
  rct_treat_coarse  whether P(Y = 1 | do(X = 1)) >= 1/2                cost 1
Query: average treatment effect ATE = P(Y=1|do(X=1)) - P(Y=1|do(X=0)).

The interventional distributions are computed by *simulating the mutilated SCM*
(`interventional`), and independently cross-checked against the closed-form
response-type expressions and against the analytic natural (Manski) bounds.
"""
import json
import os
import sys
from fractions import Fraction as F
from itertools import product

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "python"))

from prism.core import Problem, bits  # noqa: E402
from prism.engine import Engine, render  # noqa: E402
from prism.lean_export import export  # noqa: E402
from prism.serialize import canonical_bytes, parse_problem, problem_to_json  # noqa: E402

TYPES = ["never", "always", "helped", "hurt"]
G = {"never": lambda x: 0, "always": lambda x: 1, "helped": lambda x: x, "hurt": lambda x: 1 - x}
CELLS = [(ux, ut) for ux in (0, 1) for ut in TYPES]


def compositions(total, parts):
    if parts == 1:
        yield (total,)
        return
    for i in range(total + 1):
        for rest in compositions(total - i, parts - 1):
            yield (i,) + rest


def observational(dist):
    """P(X=x, Y=y) by forward simulation of the SCM."""
    p = {(x, y): F(0) for x in (0, 1) for y in (0, 1)}
    for (ux, ut), w in dist.items():
        x = ux
        y = G[ut](x)
        p[(x, y)] += w
    return p


def interventional(dist, x_do):
    """P(Y=1 | do(X=x_do)) by simulating the mutilated model (X's equation replaced)."""
    return sum((w for (ux, ut), w in dist.items() if G[ut](x_do) == 1), F(0))


def fmt(x):
    return str(x)


def build(N=6, obs_target=None):
    obs_target = obs_target or {(1, 1): F(2, 6), (1, 0): F(1, 6), (0, 1): F(1, 6), (0, 0): F(2, 6)}
    exps = ["survey", "rct_treat", "rct_control", "rct_treat_coarse"]
    costs = [F(1), F(2), F(2), F(1)]
    models, rows, q, dists = [], [], [], []
    outs = [set() for _ in exps]
    raw_obs = []
    for comp in compositions(N, len(CELLS)):
        dist = {c: F(k, N) for c, k in zip(CELLS, comp)}
        po = observational(dist)
        y1, y0 = interventional(dist, 1), interventional(dist, 0)
        # independent closed-form cross-check
        pt = {t: sum(dist[(ux, t)] for ux in (0, 1)) for t in TYPES}
        assert y1 == pt["always"] + pt["helped"] and y0 == pt["always"] + pt["hurt"]
        ate = y1 - y0
        assert ate == pt["helped"] - pt["hurt"]
        o = ["|".join(fmt(po[(x, y)]) for x in (1, 0) for y in (1, 0)), fmt(y1), fmt(y0),
             "high" if y1 >= F(1, 2) else "low"]
        for i, v in enumerate(o):
            outs[i].add(v)
        raw_obs.append(o)
        models.append("u" + "".join(map(str, comp)))
        q.append(ate)
        dists.append(dist)
    outs = [sorted(s) for s in outs]
    rows = [[outs[i].index(v) for i, v in enumerate(o)] for o in raw_obs]
    P = Problem(models, exps, outs, rows, q, costs)
    target = "|".join(fmt(obs_target[(x, y)]) for x in (1, 0) for y in (1, 0))
    data = [(0, outs[0].index(target))]
    raw = problem_to_json(P, "binary_treatment_scm", "ATE", "average treatment effect",
                          data=data, eps=F(0),
                          description="Response-type SCM on a rational grid; model id lists the "
                                      "masses (×1/N) of cells (U_X, U_Y) in order "
                                      + ", ".join(f"({ux},{t})" for ux, t in CELLS))
    spec = parse_problem(json.loads(canonical_bytes(raw)))
    return spec, raw, dists, obs_target


def natural_bounds(p):
    """Analytic natural (Manski) bounds on the ATE for binary X, Y."""
    px1 = p[(1, 1)] + p[(1, 0)]
    px0 = 1 - px1
    lo = p[(1, 1)] - (p[(0, 1)] + px1)
    hi = (p[(1, 1)] + px0) - p[(0, 1)]
    return lo, hi


def main(write_lean=True):
    spec, raw, dists, target = build()
    P = spec.P
    with open(os.path.join(HERE, "problem.json"), "wb") as f:
        f.write(canonical_bytes(raw))
    out = [f"grid models: {P.n} (N = 6); experiments: {P.experiments}"]
    eng = Engine(spec)
    rep = eng.analyze()
    out.append(render(rep, "After the observational survey"))
    K = eng.version_space()
    lo, hi, _, _ = P.bounds(K)
    nlo, nhi = natural_bounds(target)
    out.append(f"analytic natural (Manski) bounds: [{nlo}, {nhi}]; finite-grid sharp bounds: [{lo}, {hi}]; "
               f"equal: {(lo, hi) == (nlo, nhi)}")
    assert (lo, hi) == (nlo, nhi)
    # observational equivalence witnesses
    eng_obs = Engine(spec, allowed_experiments=[0])
    rep_obs = eng_obs.analyze()
    out.append(render(rep_obs, "Only observational experiments permitted"))
    # tolerance variants
    for eps in [F(0), F(1, 3), F(1, 2)]:
        spec.eps = eps
        r = Engine(spec).analyze()
        out.append(render(r, f"All experiments, tolerance {eps}"))
        if eps == 0:
            rep0 = r
    spec.eps = F(0)
    # simulated discovery under a hidden true SCM
    truth = next(m for m in bits(K) if P.q[m] == F(1, 6))
    out.append(f"\n-- simulated discovery (hidden true model {P.models[truth]}, ATE {P.q[truth]}) --")
    step = 0
    while True:
        r = eng.analyze()
        kinds = [k for k, _ in r["verdicts"]]
        if "EXPERIMENT" not in kinds:
            out.append(render(r, f"step {step}: final"))
            break
        e = r["experiment_map"][r["optimal"]["policy"]["e"]]
        o = P.obs[truth][e]
        out.append(render(r, f"step {step}"))
        out.append(f"   -> running {P.experiments[e]}: observed {P.outcomes[e][o]}")
        eng.observe(e, o)
        step += 1
    text = "\n".join(out)
    with open(os.path.join(ROOT, "results", "demo_causal.txt"), "w") as f:
        f.write(text + "\n")
    if write_lean:
        opt = rep0["optimal"]
        lo, hi, mlo, mhi = P.bounds(K)
        opt_l = {"policy": opt["policy"], "bound": opt["value"], "core": opt["core"],
                 "adversary": sorted(opt["adversary"].items(), key=lambda t: (bin(t[0]).count("1"), t[0]))}
        # restrict the exported problem to the version space after the survey (see TRUST_BOUNDARIES)
        idx = list(bits(K))
        Pk = Problem([P.models[m] for m in idx], P.experiments, P.outcomes,
                     [P.obs[m] for m in idx], [P.q[m] for m in idx], P.cost)
        remap = {m: i for i, m in enumerate(idx)}

        def rm(mask):
            return sum(1 << remap[m] for m in bits(mask))
        opt_k = {"policy": opt_l["policy"], "bound": opt_l["bound"], "core": rm(opt_l["core"]),
                 "adversary": [(rm(S), b) for S, b in opt_l["adversary"]]}
        pair = rep_obs["impossible"]
        Pobs = Problem(Pk.models, ["survey"], [P.outcomes[0]], [[r[0]] for r in Pk.obs], Pk.q, [P.cost[0]])
        src = export(Pk, "Causal", K_mask=Pk.full, eps=F(0), problem_hash=spec.hash, optimal=opt_k,
                     bounds=(lo, hi, remap[mlo], remap[mhi]),
                     doc=("Demonstration B (binary-treatment SCM, response types, grid N=6). The exported "
                          "model space is the version space after the observational survey (36 of 1716 grid "
                          "models); the survey filter itself is re-checked by the Python checker."))
        with open(os.path.join(ROOT, "PRISM", "Examples", "Generated", "Causal.lean"), "w") as f:
            f.write(src)
        src2 = export(Pobs, "CausalObservationalOnly", K_mask=Pobs.full, eps=F(0), problem_hash=spec.hash,
                      impossible=(remap[pair[0]], remap[pair[1]]),
                      doc="Demonstration B restricted to the observational survey: the ATE is not identifiable.")
        with open(os.path.join(ROOT, "PRISM", "Examples", "Generated", "CausalObservationalOnly.lean"), "w") as f:
            f.write(src2)
    print(text)


if __name__ == "__main__":
    main()
