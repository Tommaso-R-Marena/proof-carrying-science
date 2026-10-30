"""Demonstration A′: the enzyme-regulation problem with noisy assays.

Each assay reports the mechanism's predicted outcome with probability 1 - δ and a
uniformly random other outcome otherwise (δ = 1/10).  The adaptive procedure picks
the next assay greedily from the current mixture posterior (any data-dependent
rule is allowed by the theorem) and stops as soon as the claim is certified or
after T assays.  Claim: "retained flux ≥ 2/3".

Reported numbers are EXACT probabilities computed by exhaustive enumeration of
the procedure's decision tree with rational arithmetic (not simulations).
Lean theorem: PRISM.NoisyProblem.false_certification_le — for the mixture rule,
P_{m*}(certify a claim that m* violates) ≤ α for every m*, every adaptive design and
stopping rule.  The post-hoc rule has no such guarantee
(PRISM.posthoc_alternative_invalid) and the numbers below show it exceeding α.
"""
import os
import sys
from fractions import Fraction as F

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "python"))
sys.path.insert(0, HERE)

from build import build_problem  # noqa: E402
from prism.core import bits  # noqa: E402
from prism.noisy import hist_prob, evaluate, noisy_from_deterministic  # noqa: E402


def main():
    spec, _ = build_problem()
    P = spec.P
    K = spec.version_space()
    # keep one representative per (mechanism without the irrelevant activator)
    models = [m for m in bits(K) if "_act0_" in P.models[m]]
    delta = F(1, 10)
    S = noisy_from_deterministic(P, models, delta)
    names = [P.models[m] for m in models]
    pi = [F(1, len(models))] * len(models)
    claim = lambda i: S.q[i] >= F(2, 3)  # noqa: E731
    useful = [P.experiments.index(x) for x in ("product_spike", "lysate_flux", "LB_pattern", "isoform_knockdown")]

    def chooser(h, ever):
        # data-dependent choice: most-probable surviving model's most discriminating assay
        post = [pi[i] * hist_prob(S, i, h) for i in range(S.n)]
        alive = [i for i in range(S.n) if i not in ever]
        if not alive:
            return None
        best = max(alive, key=lambda i: post[i])
        used = [e for e, _ in h]
        for e in useful:
            if used.count(e) < 2:
                return e if (len(h) + best) % 2 == 0 else useful[(useful.index(e) + 1) % len(useful)]
        return None

    out = [f"models ({len(models)}): " + ", ".join(f"{n} (q={S.q[i]})" for i, n in enumerate(names)),
           f"noise δ = {delta}; claim: q ≥ 2/3; horizon T = 5"]
    for alpha in [F(1, 20), F(1, 5)]:
        for rule in ["mixture", "posthoc"]:
            r = evaluate(S, chooser, alpha, pi, rule, claim, max_depth=5)
            worst = max((r["certify_prob"][i], names[i]) for i in range(S.n) if not claim(i))
            power = min((r["certify_prob"][i], names[i]) for i in range(S.n) if claim(i))
            out.append(f"α = {alpha}, rule = {rule:8s}: max P(false certification) = {worst[0]} "
                       f"(≈{float(worst[0]):.4f}, at {worst[1]}); min P(correct certification) = "
                       f"{float(power[0]):.4f}; leaves = {r['leaves']}; "
                       f"{'≤ α ✓' if worst[0] <= alpha else 'EXCEEDS α'}")
    text = "\n".join(out)
    os.makedirs(os.path.join(ROOT, "results"), exist_ok=True)
    with open(os.path.join(ROOT, "results", "demo_noisy.txt"), "w") as f:
        f.write(text + "\n")
    print(text)


if __name__ == "__main__":
    main()
