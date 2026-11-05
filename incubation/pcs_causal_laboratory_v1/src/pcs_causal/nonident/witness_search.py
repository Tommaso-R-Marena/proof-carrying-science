"""Exact finite witness search for classic confounding non-identifiability.

Searches small binary SCM spaces for pairs that agree observationally on (X,Y)
but disagree on P(Y|do(X)). SAT/SMT candidates would be treated as untrusted;
this module uses exact enumeration with Fraction arithmetic.
"""

from __future__ import annotations

from fractions import Fraction
from itertools import product
from typing import Iterator, List, Optional, Tuple

from pcs_causal.graphs.dag import CausalDAG
from pcs_causal.nonident.witness_verifier import NonIdentWitness, verify_witness
from pcs_causal.probability.rational_pmf import FiniteDistribution
from pcs_causal.scm.finite_scm import FiniteSCM


def _binary_confounded_scm(
    p_u: Fraction,
    # P(X=1|U=u)
    px: Tuple[Fraction, Fraction],
    # P(Y=1|X=x,U=u) indexed [x][u]
    py: Tuple[Tuple[Fraction, Fraction], Tuple[Fraction, Fraction]],
) -> FiniteSCM:
    """SCM: U → X, U → Y, X → Y with binary variables."""
    dag = CausalDAG.from_edges(["U", "X", "Y"], [("U", "X"), ("U", "Y"), ("X", "Y")])
    # Represent U as endogenous with exogenous noise; simpler: make U exogenous
    # Re-spec as endogenous {X,Y} with exogenous {U, UX, UY} — use U as exo and
    # fold into mechanisms via tables with noise.
    #
    # Construction: exogenous U ~ Bern(p_u); X = f(U, UX); Y = f(X,U,UY)
    # For exact Bernoulli mechanisms use stochastic tables via expanded noise.

    # Expand using independent unit noises with 2-point distributions encoding CPTs.
    # U ∈ {0,1}, NX ∈ {0,1}, NY ∈ {0,1}
    # P(U=1)=p_u; given U, P(X=1)=px[u] realized by NX; etc.

    # Simpler exact approach: enumerate joint over (U,X,Y) consistent with factorization
    # and build mechanisms that are deterministic given fine-grained noise.

    # Use noise taking values in a rich enough domain: for each parent config, noise picks Y.
    # Domain of NU: {0,1}, NX: {0,1}, NY: {0,1,2,3} mapping...

    # Clean construction with CapCPTs via independent coin flips stored as exo masses.
    domains_exo = {
        "U": (0, 1),
        "RX": (0, 1),  # unit random for X
        "RY": (0, 1),  # unit random for Y
    }

    # Build P(U,RX,RY) = P(U)P(RX)P(RY) with RX,RY Uniform — then threshold.
    # Actually: set RX ~ Bern(1/2) won't encode arbitrary px. Instead let RX have
    # domain {0,1} with mechanism X = 1 iff RX == 0 with mass px[u] on RX=0...
    # Standard trick: RX ∈ {0,1} with P(RX=0|U) baked into joint by defining
    # exo joint directly over (U,X,Y) is wrong for SCM.
    #
    # Mechanism: X = 1 if RX < thresh — use RX in {0,...,D-1}.
    # For rational p=a/b use RX domain size b.

    def bernoulli_noise_domain(p: Fraction) -> Tuple[Tuple[object, ...], MechanismSpec]:
        raise NotImplementedError

    # Direct: exogenous joint over U and independent uniforms encoded as Fractions
    # via product of Bernoullis with exact parameters using 2-atom vars:
    # Let EX_u be the exogenous bit used when U=u for X — two bits EX0, EX1.
    exo_domains = {
        "U": (0, 1),
        "EX0": (0, 1),
        "EX1": (0, 1),
        "EY00": (0, 1),
        "EY01": (0, 1),
        "EY10": (0, 1),
        "EY11": (0, 1),
    }

    def bern_atoms(p: Fraction):
        # returns P(bit=1)=p as masses for bit in {0,1}
        return {0: 1 - p, 1: p}

    # Product distribution
    factors = {
        "U": bern_atoms(p_u),
        "EX0": bern_atoms(px[0]),
        "EX1": bern_atoms(px[1]),
        "EY00": bern_atoms(py[0][0]),
        "EY01": bern_atoms(py[0][1]),
        "EY10": bern_atoms(py[1][0]),
        "EY11": bern_atoms(py[1][1]),
    }
    names = sorted(exo_domains)
    mass = {}
    for vals in product(*[exo_domains[k] for k in names]):
        assign = dict(zip(names, vals))
        p = Fraction(1)
        for k, v in assign.items():
            p *= factors[k][v]
        if p:
            mass[tuple(sorted(assign.items()))] = p
    exo = FiniteDistribution(variables=tuple(names), domains=exo_domains, mass=mass)

    dag_xy = CausalDAG.from_edges(["X", "Y"], [("X", "Y")])

    def mech_x(a):
        return a["EX1"] if a["U"] == 1 else a["EX0"]

    def mech_y(a):
        key = f"EY{a['X']}{a['U']}"
        return a[key]

    domains = {
        "X": (0, 1),
        "Y": (0, 1),
        **exo_domains,
    }
    return FiniteSCM(
        endogenous=("X", "Y"),
        exogenous=tuple(names),
        domains=domains,
        dag=dag_xy,
        mechanisms={"X": mech_x, "Y": mech_y},
        exogenous_dist=exo,
        noise_of={"X": "EX0", "Y": "EY00"},  # representative
    )


# Fix forward ref
from typing import Any  # noqa: E402

MechanismSpec = Any


def _candidate_fractions(max_den: int = 4) -> List[Fraction]:
    out = []
    for d in range(1, max_den + 1):
        for n in range(0, d + 1):
            out.append(Fraction(n, d))
    # unique preserve order
    seen = set()
    uniq = []
    for f in out:
        if f not in seen:
            seen.add(f)
            uniq.append(f)
    return uniq


def search_binary_confounding_witness(
    max_den: int = 3,
    max_pairs: int = 50_000,
) -> Optional[NonIdentWitness]:
    """Exhaustive search for confounding non-identifiability on binary X,Y with latent U.

    Returns a verified witness or None if none found in the bound.
    """
    fracs = _candidate_fractions(max_den)
    # Precompute observational map: serialize obs dist -> list of params
    from collections import defaultdict

    buckets: dict[tuple, list] = defaultdict(list)
    checked = 0

    def obs_key(scm: FiniteSCM):
        d = scm.observational_distribution()
        # key by all masses in canonical order
        items = []
        for a, p in sorted(d.mass.items()):
            items.append((a, p.numerator, p.denominator))
        return tuple(items)

    def interv_key(scm: FiniteSCM):
        d = scm.interventional_distribution({"X": 1}).marginal(["Y"])
        items = []
        for a, p in sorted(d.mass.items()):
            items.append((a, p.numerator, p.denominator))
        return tuple(items)

    for p_u in fracs:
        if p_u == 0 or p_u == 1:
            continue
        for px0 in fracs:
            for px1 in fracs:
                for py00 in fracs:
                    for py01 in fracs:
                        for py10 in fracs:
                            for py11 in fracs:
                                params = (
                                    p_u,
                                    (px0, px1),
                                    ((py00, py01), (py10, py11)),
                                )
                                scm = _binary_confounded_scm(*params)
                                ok = obs_key(scm)
                                ik = interv_key(scm)
                                buckets[ok].append((ik, params, scm))
                                checked += 1
                                # Try match within bucket
                                group = buckets[ok]
                                if len(group) >= 2:
                                    base_ik, _, base_scm = group[0]
                                    for ik2, _, scm2 in group[1:]:
                                        if ik2 != base_ik:
                                            wit = NonIdentWitness(
                                                model_a=base_scm,
                                                model_b=scm2,
                                                treatment="X",
                                                outcome="Y",
                                                treatment_value=1,
                                                observed_vars=("X", "Y"),
                                                label="binary_latent_confounding",
                                            )
                                            verd = verify_witness(wit)
                                            if verd.accepted:
                                                return wit
                                if checked >= max_pairs:
                                    return None
    # Second pass: compare all pairs in buckets
    for group in buckets.values():
        for i in range(len(group)):
            for j in range(i + 1, len(group)):
                if group[i][0] != group[j][0]:
                    wit = NonIdentWitness(
                        model_a=group[i][2],
                        model_b=group[j][2],
                        treatment="X",
                        outcome="Y",
                        treatment_value=1,
                        observed_vars=("X", "Y"),
                        label="binary_latent_confounding",
                    )
                    if verify_witness(wit).accepted:
                        return wit
    return None


def classic_confounding_witness() -> NonIdentWitness:
    """Exact finite confounding witness (cached pair + search fallback)."""
    scm_a = _binary_confounded_scm(
        Fraction(1, 2),
        (Fraction(0, 1), Fraction(0, 1)),
        ((Fraction(0, 1), Fraction(0, 1)), (Fraction(0, 1), Fraction(0, 1))),
    )
    scm_b = _binary_confounded_scm(
        Fraction(1, 2),
        (Fraction(0, 1), Fraction(0, 1)),
        ((Fraction(0, 1), Fraction(0, 1)), (Fraction(0, 1), Fraction(1, 1))),
    )
    wit = NonIdentWitness(
        model_a=scm_a,
        model_b=scm_b,
        treatment="X",
        outcome="Y",
        treatment_value=1,
        observed_vars=("X", "Y"),
        label="classic_confounding_witness",
    )
    if verify_witness(wit).accepted:
        return wit
    found = search_binary_confounding_witness(max_den=2, max_pairs=200_000)
    if found is None:
        raise RuntimeError("failed to construct classic confounding witness")
    return found
