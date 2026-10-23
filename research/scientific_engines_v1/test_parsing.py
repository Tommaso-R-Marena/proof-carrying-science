import json
from pathlib import Path
import pytest
from . import parsing, emission
from .verifier import prepare_prism, prepare_aion, prepare_risk_demo, RISK_DESCRIPTOR

HERE = Path(__file__).parent


@pytest.fixture
def cert():
    return json.loads(
        (HERE / "vendor/aion/certificates/A_birth_death_N10.json").read_text()
    )


@pytest.fixture
def problem():
    return json.loads(
        (HERE / "vendor/prism/examples/biochemical/problem.json").read_text()
    )


def test_all_fourteen_supplied_aion_artifacts_pass_strict_boundary():
    files = list((HERE / "vendor/aion/certificates").glob("*.json"))
    assert len(files) == 14
    for p in files:
        parsing.aion(p.read_bytes())


def test_all_original_prism_problem_fixtures_pass_strict_boundary():
    for p in (HERE / "vendor/prism/examples").glob("*/problem.json"):
        parsing.prism(p.read_bytes())


@pytest.mark.parametrize(
    "mutate",
    [
        lambda c: c["target"].update(level=True),
        lambda c: c["target"].update(level=10.0),
        lambda c: c["x0"].__setitem__(0, True),
        lambda c: c["taboo_zero"].__setitem__(0, "false"),
        lambda c: c["model"]["reactions"][0]["inp"].__setitem__(0, True),
        lambda c: c["upper"]["box"].__setitem__(0, 10.5),
        lambda c: c["upper"]["table"].__setitem__("01", "0"),
        lambda c: c["upper"]["table"].__setitem__("1", "0.5"),
        lambda c: c["upper"]["table"].__setitem__("1", "-0"),
        lambda c: c["upper"]["table"].__setitem__("1", "1/3"),
        lambda c: c["model"]["reactions"][0].update(k="-1"),
        lambda c: c.update(verified=True),
        lambda c: c["target"].update(extra=True),
        lambda c: c.update(format="unknown"),
        lambda c: c["claim"].update(upper="2"),
    ],
)
def test_aion_coercion_ambiguity_and_unknown_fields_refuse(cert, mutate):
    mutate(cert)
    with pytest.raises((ValueError, TypeError)):
        parsing.aion(parsing.encode(cert))


@pytest.mark.parametrize(
    "raw", [b'{"x":1,"x":2}', b'{"x":NaN}', b'{"x":Infinity}', b"\xff", b'{"x":1.5}']
)
def test_strict_json_refuses_ambiguous_inputs(raw):
    with pytest.raises((ValueError, UnicodeError)):
        parsing.load(raw)


def test_prism_unsafe_metadata_never_enters_lean(problem):
    problem["description"] = '-/\n#eval IO.println "injected"\n/-'
    problem["models"][0]["id"] = "-/"
    for a in problem["assumptions"]:
        a["holds"] = [
            "-/" if m.startswith("comp_fb0_act0_iso0") else m for m in a["holds"]
        ]
    spec = parsing.prism(parsing.encode(problem))
    src = emission.prism(spec)
    assert "injected" not in src and "#eval" not in src and "* `0` ↦ `m0`" in src


def test_aion_unsafe_metadata_never_enters_lean(cert):
    cert["model"]["species"] = ['-/\n#eval IO.println "injected"\n/-']
    cert["model"]["reactions"][0]["name"] = '-/\n#eval IO.println "injected"\n/-'
    src = emission.aion(parsing.aion(parsing.encode(cert)))
    assert "injected" not in src and "#eval" not in src and "native_decide" not in src


def test_inconsistent_prism_is_never_vacuous_certification(problem):
    problem["assumptions"].append(
        dict(id="no_models", description="negative control", holds=[])
    )
    claim, source, names, cert = prepare_prism(parsing.encode(problem))
    assert (
        claim["status"] == "INCONSISTENT"
        and cert is None
        and "inconsistent_ok" in source
    )


def test_zero_experiments_supported_without_emitter_crash():
    p = dict(
        schema="prism-problem/1",
        name="empty_experiments",
        models=[dict(id="m0", q="0", obs={}), dict(id="m1", q="1", obs={})],
        experiments=[],
        query=dict(id="q"),
    )
    claim, src, names, _ = prepare_prism(parsing.encode(p))
    assert claim["status"] == "UNIDENTIFIABLE" and "Fin 0" in src


def test_aion_unsupported_robust_and_time_claims_never_accepted(cert):
    cert["finite_horizon"] = 10
    with pytest.raises(ValueError):
        prepare_aion(parsing.encode(cert))


def test_prism_nested_unknown_fields_not_silently_ignored(problem):
    problem["experiments"][0]["trusted_verdict"] = True
    with pytest.raises(ValueError):
        parsing.prism(parsing.encode(problem))


def test_envelope_hex_budget_does_not_relax_model_metadata_budget():
    raw = parsing.encode(dict(input_hex="ab" * 10000))
    with pytest.raises(ValueError, match="String budget"):
        parsing.load(raw)
    assert len(parsing.load(raw, evidence=True)["input_hex"]) == 20000
    with pytest.raises(ValueError, match="String budget"):
        parsing.load(parsing.encode(dict(description="a" * 10000)), evidence=True)


@pytest.mark.parametrize("value", ["-0", "00", "1/01", "2/2", "0\n", "0.0", "+1"])
def test_prism_tolerance_uses_exact_canonical_rational(problem, value):
    problem["tolerance"] = value
    with pytest.raises(ValueError):
        parsing.prism(parsing.encode(problem))


def test_joint_risk_values_against_independent_exact_gambler_ruin_oracle():
    from fractions import Fraction as Q

    claim, _, names, _ = prepare_risk_demo(parsing.encode(RISK_DESCRIPTOR))
    for mu, reported in zip([Q(2), Q(3, 2)], claim["risks"]):
        # Independent geometric-series expression, rather than the emitted formula.
        exact = 1 / sum(mu**j for j in range(20))
        assert exact == Q(reported)
    assert Q(claim["risks"][0]) < Q(claim["threshold"]) < Q(claim["risks"][1])
    assert len(names) == 8 and claim["empirical_validation"] is False


def test_joint_example_cannot_be_relabelled_as_real_observations():
    d = dict(RISK_DESCRIPTOR, empirical_validation=True)
    with pytest.raises(ValueError):
        prepare_risk_demo(parsing.encode(d))
