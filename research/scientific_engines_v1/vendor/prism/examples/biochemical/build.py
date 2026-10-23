"""Demonstration A: hidden enzyme-regulation mechanism (synthetic, deterministic).

Enzyme E1 converts S -> P.  A drug D is being developed against E1.  Competing
discrete mechanisms (4 × 2 × 2 × 2 = 32 models):
  mode ∈ {competitive, uncompetitive, noncompetitive, none}   (drug action on E1)
  fb   ∈ {0, 1}   product feedback inhibition of E1
  act  ∈ {0, 1}   allosteric activator A acts on E1 (irrelevant to the query)
  iso  ∈ {0, 1}   a drug-insensitive isoform E2 carries half of the flux

Query: fraction of pathway flux retained in vivo under a saturating dose of D
(high substrate, product accumulating), an exact rational computed from an
idealized steady-state rule:
  f(mode) = 3/4, 1/4, 1/2, 1   (comp., uncomp., noncomp., none at high [S])
  q0 = f            if iso = 0,  (f + 1)/2 if iso = 1
  q  = q0           if fb = 0,   (2 q0 + 1)/3 if fb = 1  (feedback relief)

These are SYNTHETIC mechanistic calculations, not laboratory data.
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
from prism.serialize import (canonical_bytes, optimal_cert_to_json, parse_problem,  # noqa: E402
                             problem_to_json)

MODES = ["comp", "uncomp", "noncomp", "none"]
F_MODE = {"comp": F(3, 4), "uncomp": F(1, 4), "noncomp": F(1, 2), "none": F(1)}
LB = {"comp": "Km_up", "uncomp": "both_down", "noncomp": "Vmax_down", "none": "no_change"}

EXPERIMENTS = [
    # id, cost, outcomes
    ("LB_pattern", F(3), ["Km_up", "both_down", "Vmax_down", "no_change"]),
    ("rescue", F(1), ["no", "yes"]),
    ("product_spike", F(1), ["none", "decrease"]),
    ("activator_titration", F(1), ["none", "increase"]),
    ("isoform_knockdown", F(2), ["abolished", "residual"]),
    ("lysate_flux", F(2), ["1/4", "1/2", "5/8", "3/4", "7/8", "1"]),
]


def q_of(mode, fb, act, iso):
    q0 = F_MODE[mode] if not iso else (F_MODE[mode] + 1) / 2
    return q0 if not fb else (2 * q0 + 1) / 3


def obs_of(mode, fb, act, iso):
    q0 = F_MODE[mode] if not iso else (F_MODE[mode] + 1) / 2
    return {
        "LB_pattern": LB[mode],
        "rescue": "yes" if mode in ("comp", "none") else "no",
        "product_spike": "decrease" if fb else "none",
        "activator_titration": "increase" if act else "none",
        "isoform_knockdown": "residual" if iso else "abolished",
        "lysate_flux": str(q0) if q0.denominator != 1 else "1",
    }


def build_problem():
    models, obs, q = [], [], []
    exp_ids = [e[0] for e in EXPERIMENTS]
    outs = [e[2] for e in EXPERIMENTS]
    for mode, fb, act, iso in product(MODES, [0, 1], [0, 1], [0, 1]):
        mid = f"{mode}_fb{fb}_act{act}_iso{iso}"
        models.append(mid)
        o = obs_of(mode, fb, act, iso)
        obs.append([outs[i].index(o[e]) for i, e in enumerate(exp_ids)])
        q.append(q_of(mode, fb, act, iso))
    P = Problem(models, exp_ids, outs, obs, q, [e[1] for e in EXPERIMENTS])
    a1 = {"id": "A1_drug_acts_on_E1",
          "description": "the drug affects E1 (mode != none); justified by prior binding data",
          "mask": P.mask_of(i for i, m in enumerate(models) if not m.startswith("none"))}
    data = [(exp_ids.index("rescue"), 0)]  # initial observation: no substrate rescue
    raw = problem_to_json(P, "enzyme_regulation", "flux_retained",
                          "fraction of pathway flux retained in vivo under saturating drug",
                          assumptions=[a1], data=data, eps=F(0),
                          description="Synthetic enzyme-regulation mechanism discrimination")
    return parse_problem(json.loads(canonical_bytes(raw))), raw


def main(write_lean=True):
    spec, raw = build_problem()
    P = spec.P
    out = []
    os.makedirs(os.path.join(ROOT, "results"), exist_ok=True)
    with open(os.path.join(HERE, "problem.json"), "wb") as f:
        f.write(canonical_bytes(raw))
    claims = {"C1_retains_at_least_quarter": P.mask_of(m for m in range(P.n) if P.q[m] >= F(1, 4)),
              "C2_at_most_half_retained": P.mask_of(m for m in range(P.n) if P.q[m] <= F(1, 2))}
    eng = Engine(spec, claims=claims)
    rep = eng.analyze()
    out.append(render(rep, "Initial analysis (data: rescue = no)"))
    K0 = eng.version_space()
    # two mechanistically distinct explanations of the same data
    a = P.models.index("uncomp_fb1_act0_iso0")
    b = P.models.index("noncomp_fb0_act0_iso0")
    out.append(f"Two distinct mechanisms reproducing all data: {P.models[a]} (q={P.q[a]}) and "
               f"{P.models[b]} (q={P.q[b]}): different mechanisms with the same query value; experiments "
               f"that separate them: {[P.experiments[e] for e in range(P.k) if P.obs[a][e] != P.obs[b][e]]}")
    c = P.models.index("noncomp_fb1_act0_iso1")
    out.append(f"Mechanisms with different intervention predictions: {P.models[a]} (q={P.q[a]}) vs "
               f"{P.models[c]} (q={P.q[c]})")
    opt = rep["optimal"]
    cert_json = optimal_cert_to_json(spec, opt)
    with open(os.path.join(HERE, "certificate_initial.json"), "wb") as f:
        f.write(canonical_bytes(cert_json))
    # enumerate outcomes of the recommended first experiment
    pol = opt["policy"]
    e0 = pol["e"]
    for o, sub in sorted(P.split(K0, e0).items()):
        out.append(f"  if {P.experiments[e0]} = {P.outcomes[e0][o]}: {bin(sub).count('1')} models remain, "
                   f"query range [{P.bounds(sub)[0]}, {P.bounds(sub)[1]}]")
    # simulated discovery loop with a hidden truth
    truth = P.models.index("noncomp_fb1_act0_iso0")
    out.append(f"\n-- simulated discovery (hidden true mechanism: {P.models[truth]}) --")
    step = 0
    while True:
        rep = eng.analyze()
        kinds = [k for k, _ in rep["verdicts"]]
        if "EXPERIMENT" not in kinds:
            out.append(render(rep, f"step {step}: final"))
            break
        e = rep["experiment_map"][rep["optimal"]["policy"]["e"]]
        o = P.obs[truth][e]
        out.append(render(rep, f"step {step}"))
        out.append(f"   -> running {P.experiments[e]}: observed {P.outcomes[e][o]}")
        eng.observe(e, o)
        step += 1
    # restricted experiment set: impossibility
    eng2 = Engine(spec, allowed_experiments=[0, 1, 2, 3])
    rep2 = eng2.analyze()
    out.append(render(rep2, "Restricted experiment set {LB_pattern, rescue, product_spike, activator_titration}"))
    # tolerance variant
    spec.eps = F(1, 6)
    rep3 = Engine(spec).analyze()
    out.append(render(rep3, "Tolerance 1/6 variant"))
    spec.eps = F(0)
    text = "\n".join(out)
    with open(os.path.join(ROOT, "results", "demo_biochemical.txt"), "w") as f:
        f.write(text + "\n")
    if write_lean:
        lo, hi, mlo, mhi = P.bounds(K0)
        amask = spec.assumptions[0]["mask"]
        opt_l = {"policy": opt["policy"], "bound": opt["value"], "core": opt["core"],
                 "adversary": sorted(opt["adversary"].items(), key=lambda t: (bin(t[0]).count("1"), t[0]))}
        cm = next(iter(bits(K0 & ~claims["C2_at_most_half_retained"])))
        src = export(P, "Biochem", K_mask=K0, eps=F(0), assumption_mask=amask, data=spec.data,
                     problem_hash=spec.hash, optimal=opt_l, bounds=(lo, hi, mlo, mhi),
                     countermodel=(cm, "P.q m ≤ 1/2", "the claim 'at most half the flux is retained' "
                                   "fails in an admissible mechanism"),
                     doc="Demonstration A (synthetic enzyme-regulation mechanisms).")
        with open(os.path.join(ROOT, "PRISM", "Examples", "Generated", "Biochem.lean"), "w") as f:
            f.write(src)
        # impossibility for restricted experiments: export restricted problem
        Pr, ex = eng2.restricted_problem()
        src2 = export(Pr, "BiochemRestricted", K_mask=K0, eps=F(0), assumption_mask=amask,
                      data=[(ex.index(e), o) for e, o in spec.data], problem_hash=spec.hash,
                      impossible=rep2["impossible"],
                      doc="Demonstration A with experiments restricted to the first four assays.")
        with open(os.path.join(ROOT, "PRISM", "Examples", "Generated", "BiochemRestricted.lean"), "w") as f:
            f.write(src2)
    print(text)
    return text


if __name__ == "__main__":
    main()
