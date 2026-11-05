"""Exact-rational stoichiometric matrices and conservation discovery."""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from math import gcd
from typing import List, Mapping, Sequence, Tuple

from pcca.formula import parse_formula

MAX_SPECIES = 32
MAX_REACTIONS = 64
MAX_STEPS = 256
MAX_BITS = 4096


def _as_fraction(value, label: str) -> Fraction:
    if isinstance(value, bool):
        raise ValueError(f"{label}: booleans are not rationals")
    if isinstance(value, Fraction):
        q = value
    elif isinstance(value, int):
        q = Fraction(value)
    elif isinstance(value, str):
        q = Fraction(value)
    else:
        raise ValueError(f"{label}: unsupported rational literal {type(value).__name__}")
    if q.numerator.bit_length() > MAX_BITS or q.denominator.bit_length() > MAX_BITS:
        raise ValueError(f"{label}: rational exceeds bit budget")
    return q


def _rat_text(q: Fraction) -> str:
    return f"{q.numerator}/{q.denominator}" if q.denominator != 1 else str(q.numerator)


def _lcm(a: int, b: int) -> int:
    return abs(a * b) // gcd(a, b) if a and b else abs(a or b)


@dataclass(frozen=True)
class ConservationLaw:
    name: str
    weights: Tuple[Fraction, ...]  # aligned to species order
    kind: str  # "elemental" | "discovered" | "declared"

    def as_dict(self, species: Sequence[str]) -> dict:
        return {
            "name": self.name,
            "kind": self.kind,
            "weights": {species[i]: _rat_text(self.weights[i]) for i in range(len(species))},
        }


@dataclass(frozen=True)
class StoichiometricNetwork:
    species: Tuple[str, ...]
    reactions: Tuple[str, ...]
    # S[s][r] = net stoichiometric coefficient of species s in reaction r
    matrix: Tuple[Tuple[Fraction, ...], ...]
    formulas: Tuple[str | None, ...] = ()

    @property
    def n_species(self) -> int:
        return len(self.species)

    @property
    def n_reactions(self) -> int:
        return len(self.reactions)

    def annihilates(self, weights: Sequence[Fraction]) -> bool:
        if len(weights) != self.n_species:
            raise ValueError("weight dimension mismatch")
        for r in range(self.n_reactions):
            total = sum(weights[s] * self.matrix[s][r] for s in range(self.n_species))
            if total != 0:
                return False
        return True

    def to_json(self) -> dict:
        rows = []
        for s, name in enumerate(self.species):
            rows.append(
                {
                    "species": name,
                    "formula": self.formulas[s] if self.formulas else None,
                    "coeffs": [_rat_text(self.matrix[s][r]) for r in range(self.n_reactions)],
                }
            )
        return {
            "species": list(self.species),
            "reactions": list(self.reactions),
            "rows": rows,
        }


def pool(weights: Sequence[Fraction], state: Sequence[Fraction]) -> Fraction:
    if len(weights) != len(state):
        raise ValueError("pool dimension mismatch")
    return sum((w * x for w, x in zip(weights, state)), Fraction(0))


def fire(
    network: StoichiometricNetwork,
    xi: Sequence[Fraction],
    state: Sequence[Fraction],
) -> Tuple[Fraction, ...]:
    if len(xi) != network.n_reactions or len(state) != network.n_species:
        raise ValueError("fire dimension mismatch")
    out = []
    for s in range(network.n_species):
        delta = sum(network.matrix[s][r] * xi[r] for r in range(network.n_reactions))
        out.append(state[s] + delta)
    return tuple(out)


def from_mass_action_contract(contract: Mapping) -> StoichiometricNetwork:
    """Build S from a pcs-mass-action-contract-v1-like object (local copy)."""
    if contract.get("format") not in {
        "pcs-mass-action-contract-v1",
        "pcca-mass-action-contract-v1",
    }:
        raise ValueError("unsupported contract format")
    species_entries = contract["species"]
    reactions = contract["reactions"]
    if not (1 <= len(species_entries) <= MAX_SPECIES):
        raise ValueError("species count out of bounds")
    if not (1 <= len(reactions) <= MAX_REACTIONS):
        raise ValueError("reaction count out of bounds")
    species = tuple(entry["id"] for entry in species_entries)
    if len(set(species)) != len(species):
        raise ValueError("duplicate species")
    formulas = tuple(entry.get("formula") for entry in species_entries)
    index = {name: i for i, name in enumerate(species)}
    rxn_ids: List[str] = []
    matrix = [[Fraction(0) for _ in reactions] for _ in species]
    for r, reaction in enumerate(reactions):
        rid = reaction["id"]
        if rid in rxn_ids:
            raise ValueError("duplicate reaction")
        rxn_ids.append(rid)
        for item in reaction["reactants"]:
            s = index[item["species"]]
            coeff = int(item["coefficient"])
            if not 1 <= coeff <= 8:
                raise ValueError("coefficient out of range")
            matrix[s][r] -= coeff
        for item in reaction["products"]:
            s = index[item["species"]]
            coeff = int(item["coefficient"])
            if not 1 <= coeff <= 8:
                raise ValueError("coefficient out of range")
            matrix[s][r] += coeff
    return StoichiometricNetwork(
        species=species,
        reactions=tuple(rxn_ids),
        matrix=tuple(tuple(row) for row in matrix),
        formulas=formulas,
    )


def elemental_laws(network: StoichiometricNetwork) -> List[ConservationLaw]:
    """Derive elemental conservation laws from formulas when every reaction balances."""
    if not network.formulas or any(f is None for f in network.formulas):
        return []
    parsed = [parse_formula(f) for f in network.formulas]  # type: ignore[arg-type]
    elements = sorted({el for counts in parsed for el in counts})
    laws: List[ConservationLaw] = []
    for el in elements:
        weights = tuple(Fraction(counts.get(el, 0)) for counts in parsed)
        if all(w == 0 for w in weights):
            continue
        if network.annihilates(weights):
            laws.append(ConservationLaw(name=el, weights=weights, kind="elemental"))
    return laws


def discover_conservation_laws(network: StoichiometricNetwork) -> List[ConservationLaw]:
    """Exact rational basis for the left nullspace {γ | γᵀ S = 0}.

    Solves Sᵀ γ = 0 by row-reducing Sᵀ and reading free-variable basis vectors.
    """
    m, n = network.n_species, network.n_reactions
    # A = Sᵀ has shape n × m
    mat = [[network.matrix[s][r] for s in range(m)] for r in range(n)]
    rows, cols = n, m
    pivot_cols: List[int] = []
    r = 0
    for c in range(cols):
        pivot = None
        for i in range(r, rows):
            if mat[i][c] != 0:
                pivot = i
                break
        if pivot is None:
            continue
        mat[r], mat[pivot] = mat[pivot], mat[r]
        piv = mat[r][c]
        mat[r] = [v / piv for v in mat[r]]
        for i in range(rows):
            if i == r:
                continue
            factor = mat[i][c]
            if factor != 0:
                mat[i] = [mat[i][j] - factor * mat[r][j] for j in range(cols)]
        pivot_cols.append(c)
        r += 1
        if r == rows:
            break
    pivot_set = set(pivot_cols)
    free = [c for c in range(cols) if c not in pivot_set]
    laws: List[ConservationLaw] = []
    for idx, free_col in enumerate(free):
        weights = [Fraction(0)] * m
        weights[free_col] = Fraction(1)
        for row_i, piv_c in enumerate(pivot_cols):
            weights[piv_c] = -mat[row_i][free_col]
        dens = [w.denominator for w in weights if w != 0]
        scale = 1
        for d in dens:
            scale = _lcm(scale, d)
        weights_t = tuple(w * scale for w in weights)
        for w in weights_t:
            if w != 0:
                if w < 0:
                    weights_t = tuple(-ww for ww in weights_t)
                break
        if network.annihilates(weights_t):
            laws.append(
                ConservationLaw(
                    name=f"nullspace_{idx}",
                    weights=weights_t,
                    kind="discovered",
                )
            )
    return laws


def simulate_euler_mass_action(
    network: StoichiometricNetwork,
    rates: Sequence[Fraction],
    orders: Sequence[Tuple[Tuple[int, int], ...]],
    initial: Sequence[Fraction],
    dt: Fraction,
    steps: int,
) -> Tuple[Tuple[Fraction, ...], ...]:
    """Explicit Euler with mass-action rates; each step is a stoichiometric fire."""
    if not 1 <= steps <= MAX_STEPS:
        raise ValueError("steps out of bounds")
    if len(rates) != network.n_reactions or len(orders) != network.n_reactions:
        raise ValueError("rate/order dimension mismatch")
    if len(initial) != network.n_species:
        raise ValueError("initial dimension mismatch")
    dt = _as_fraction(dt, "dt")
    state = tuple(_as_fraction(x, f"x[{i}]") for i, x in enumerate(initial))
    traj = [state]
    for _ in range(steps):
        xi = []
        for r in range(network.n_reactions):
            rate = _as_fraction(rates[r], f"rate[{r}]")
            for s_idx, coeff in orders[r]:
                rate *= state[s_idx] ** coeff
            xi.append(dt * rate)
        state = fire(network, xi, state)
        traj.append(state)
    return tuple(traj)


def orders_from_contract(contract: Mapping, network: StoichiometricNetwork):
    index = {name: i for i, name in enumerate(network.species)}
    rates = []
    orders = []
    for reaction in contract["reactions"]:
        rates.append(_as_fraction(reaction["rate_constant"], "rate"))
        orders.append(
            tuple(
                (index[item["species"]], int(item["coefficient"]))
                for item in reaction["reactants"]
            )
        )
    initial = tuple(
        _as_fraction(contract["initial"][name], name) for name in network.species
    )
    dt = _as_fraction(contract["time_step"], "time_step")
    steps = int(contract["steps"])
    return rates, orders, initial, dt, steps
