from pcs_next_v1.adapters.chemistry import atom_balance

def test_balance():
    ok = {
        "reactants": [{"formula_atoms": {"C": 1, "O": 2}, "coeff": 1}],
        "products": [{"formula_atoms": {"C": 1, "O": 2}, "coeff": 1}],
    }
    assert atom_balance(ok)["status"] == "COMPUTATIONALLY_TESTED"
    bad = {
        "reactants": [{"formula_atoms": {"C": 1, "O": 2}, "coeff": 1}],
        "products": [{"formula_atoms": {"C": 1, "O": 1}, "coeff": 1}],
    }
    assert atom_balance(bad)["status"] == "REFUTED"
