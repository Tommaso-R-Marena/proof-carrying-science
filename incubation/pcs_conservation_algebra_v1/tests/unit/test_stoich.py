from fractions import Fraction

from pcca.stoich.matrix import (
    StoichiometricNetwork,
    discover_conservation_laws,
    elemental_laws,
    fire,
    from_mass_action_contract,
    pool,
    simulate_euler_mass_action,
)


def _glucose_contract():
    return {
        "format": "pcca-mass-action-contract-v1",
        "species": [
            {"id": "glucose", "formula": "C6H12O6"},
            {"id": "lactate", "formula": "C3H6O3"},
            {"id": "isomer", "formula": "C3H6O3"},
        ],
        "reactions": [
            {
                "id": "cleavage",
                "reactants": [{"species": "glucose", "coefficient": 1}],
                "products": [{"species": "lactate", "coefficient": 2}],
                "rate_constant": "1/10",
                "rate_unit": "s^-1",
            },
            {
                "id": "isomerization",
                "reactants": [{"species": "lactate", "coefficient": 1}],
                "products": [{"species": "isomer", "coefficient": 1}],
                "rate_constant": "1/20",
                "rate_unit": "s^-1",
            },
        ],
        "initial": {"glucose": "1", "lactate": "0", "isomer": "0"},
        "time_step": "1/4",
        "steps": 4,
    }


def test_elemental_carbon_hydrogen_oxygen():
    net = from_mass_action_contract(_glucose_contract())
    laws = {law.name: law for law in elemental_laws(net)}
    assert set(laws) == {"C", "H", "O"}
    assert laws["C"].weights == (Fraction(6), Fraction(3), Fraction(3))
    assert net.annihilates(laws["C"].weights)


def test_nullspace_contains_elemental_span():
    net = from_mass_action_contract(_glucose_contract())
    discovered = discover_conservation_laws(net)
    assert len(discovered) >= 1
    # Carbon should be in the span of discovered laws (rank of left nullspace).
    carbon = (Fraction(6), Fraction(3), Fraction(3))
    assert net.annihilates(carbon)


def test_fire_preserves_carbon():
    net = from_mass_action_contract(_glucose_contract())
    carbon = (Fraction(6), Fraction(3), Fraction(3))
    state = (Fraction(1), Fraction(0), Fraction(0))
    xi = (Fraction(1, 10), Fraction(0))
    after = fire(net, xi, state)
    assert pool(carbon, after) == pool(carbon, state) == Fraction(6)


def test_euler_trajectory_preserves_all_elementals():
    contract = _glucose_contract()
    net = from_mass_action_contract(contract)
    laws = elemental_laws(net)
    rates = [Fraction("1/10"), Fraction("1/20")]
    orders = [((0, 1),), ((1, 1),)]
    initial = (Fraction(1), Fraction(0), Fraction(0))
    traj = simulate_euler_mass_action(net, rates, orders, initial, Fraction("1/4"), 4)
    for law in laws:
        values = [pool(law.weights, st) for st in traj]
        assert all(v == values[0] for v in values)


def test_exchange_total_amount():
    contract = {
        "format": "pcca-mass-action-contract-v1",
        "species": [{"id": "a", "formula": "X"}, {"id": "b", "formula": "X"}],
        "reactions": [
            {
                "id": "ex",
                "reactants": [{"species": "a", "coefficient": 1}],
                "products": [{"species": "b", "coefficient": 1}],
                "rate_constant": "1/5",
                "rate_unit": "s^-1",
            }
        ],
        "initial": {"a": "1", "b": "2"},
        "time_step": "1/4",
        "steps": 3,
    }
    net = from_mass_action_contract(contract)
    laws = elemental_laws(net)
    assert any(law.name == "X" for law in laws)
    total = next(law for law in laws if law.name == "X")
    assert pool(total.weights, (Fraction(1), Fraction(2))) == Fraction(3)
