"""Typed scientific claims with ordinary Lean evidence and independent replay."""

import json, os, tempfile
from pathlib import Path
from . import parsing, emission
from .authority import Authority, digest, RISK_NAMES
from .vendor.prism.python.prism import serialize as ps
from .vendor.prism.python.prism.reference import checker as pc
from .vendor.prism.python.prism.search.sandwich import sandwich_certify
from .vendor.aion.python.aion import checker as ac

FORMAT = "pcs-scientific-engines-evidence-v1"
CORRESPONDENCE = "trusted_host_emission; differential_tested_not_proved"
RISK_DESCRIPTOR = {
    "schema": "pcs-risk-experiment/1",
    "example": "birth-death-two-model-v1",
}


def prepare_risk_demo(raw):
    """Fixed synthetic cross-engine theorem, never an arbitrary scientific model."""
    if parsing.load(raw) != RISK_DESCRIPTOR:
        raise ValueError("Exact supported risk example required")
    names = ["PCSScientific.RiskDemo." + n for n in RISK_NAMES]
    source = "import PCSScientific.RiskDemo\n"
    claim = dict(
        kind="optimal_rare_event_classification_experiment",
        status="MODEL_CONDITIONAL_OPTIMAL",
        risks=["1/1048575", "524288/3485735825"],
        threshold="1/100000",
        event="hit population 20 before extinction from population 1",
        models=[dict(birth="1", death="2"), dict(birth="1", death="3/2")],
        optimal_worst_case_cost="1",
        alternative_assay_cost="7",
        no_informative_assay="unidentifiable for every adaptive policy",
        scientific_assumptions=[
            "actual model belongs to the declared pair",
            "assay outcomes exactly identify the model as stipulated",
            "linear birth-death jump-chain dynamics",
        ],
        time_semantics="eventual embedded jump chain",
        empirical_validation=False,
        finite_horizon_bound=False,
    )
    return claim, source, names, None


def prepare_prism(raw, certificate=None):
    spec = parsing.prism(raw)
    p = spec.P
    k = spec.version_space()
    names = ["PRISM.Generated.PCSReplay.K_eq"]
    claim = dict(
        kind="finite_model_identification",
        admissible_models=k.bit_count(),
        scientific_assumptions=spec.raw.get("assumptions", []),
        observations=spec.raw.get("data", []),
        tolerance=str(spec.eps),
        truth_membership_proved=False,
    )
    kwargs = {}
    cert_json = None
    extra = ""
    if not k:
        claim["status"] = "INCONSISTENT"
        if certificate is not None:
            raise ValueError("Cannot certify an optimal policy on inconsistent data")
        extra = "namespace PRISM.Generated.PCSReplay\nopen PRISM PRISM.Problem\ntheorem inconsistent_ok : checkInconsistent K = true := by decide +kernel\ntheorem inconsistent : K = ∅ := checkInconsistent_sound inconsistent_ok\nend PRISM.Generated.PCSReplay\n"
        names += [
            "PRISM.Generated.PCSReplay.inconsistent_ok",
            "PRISM.Generated.PCSReplay.inconsistent",
        ]
    else:
        lo, hi, mlo, mhi = p.bounds(k)
        kwargs["bounds"] = (lo, hi, mlo, mhi)
        claim.update(lower=str(lo), upper=str(hi))
        names += [
            "PRISM.Generated.PCSReplay.bounds_ok",
            "PRISM.Generated.PCSReplay.sharp_bounds",
        ]
        if certificate is not None:
            cert_json = parsing.prism_certificate(certificate)
            cert = ps.parse_optimal_cert(spec, cert_json)
            pc.check_optimal(p, k, spec.eps, cert)
            res = dict(
                status="optimal",
                value=cert["bound"],
                **{n: cert[n] for n in ["core", "policy", "adversary"]},
            )
        else:
            res = sandwich_certify(p, k, spec.eps, budget_states=10000, time_limit=10)
        if res["status"] == "optimal":
            if certificate is None:
                cert_json = ps.optimal_cert_to_json(spec, res)
            cert = ps.parse_optimal_cert(spec, cert_json)
            pc.check_optimal(p, k, spec.eps, cert)
            kwargs["optimal"] = cert
            claim.update(
                status="OPTIMAL_EXPERIMENT",
                optimal_worst_case_cost=str(cert["bound"]),
                policy=cert_json["policy"],
            )
            names += [
                "PRISM.Generated.PCSReplay." + n
                for n in [
                    "cert_ok",
                    "policy_sound",
                    "policy_cost",
                    "policy_optimal",
                    "value_eq",
                ]
            ]
        elif res["status"] == "impossible":
            pair = res["pair"]
            pc.check_impossible(p, k, spec.eps, *pair)
            kwargs["impossible"] = pair
            claim.update(
                status="UNIDENTIFIABLE", countermodels=[p.models[i] for i in pair]
            )
            names += [
                "PRISM.Generated.PCSReplay.impossible_ok",
                "PRISM.Generated.PCSReplay.impossible",
            ]
        else:
            claim.update(status="BOUNDED_PLANNING_UNRESOLVED")
    source = emission.prism(spec, **kwargs) + extra
    return claim, source, names, cert_json


def prepare_aion(raw):
    cert = parsing.aion(raw)
    report = ac.check_certificate(cert)
    if not report["ok"]:
        raise ValueError("Independent exact checker rejected: " + json.dumps(report))
    source = emission.aion(cert)
    names = [
        "AION.Examples.PCSReplay." + n
        for n in ["upper_ok", "lower_ok", "upper_val", "lower_val", "sandwich"]
    ]
    claim = dict(
        kind="jump_chain_rare_event_interval",
        status="BOUNDED_EVENTUAL_HITTING_PROBABILITY",
        model=cert["model"],
        target=cert["target"],
        taboo_zero=cert["taboo_zero"],
        initial_state=cert["x0"],
        lower=cert["claim"]["lower"],
        upper=cert["claim"]["upper"],
        time_semantics="eventual embedded jump chain",
        continuous_time_measure_constructed=False,
        finite_horizon_bound=False,
        empirical_validation="none; declared mechanistic model only",
    )
    return claim, source, names, None


def _derive(kind, raw, authority, *, certificate=None):
    if type(authority) is not Authority:
        raise ValueError("Fixed real Lean authority required")
    if kind not in {"prism", "aion", "risk-demo"}:
        raise ValueError("Known typed scientific engine required")
    if kind != "prism" and certificate is not None:
        raise ValueError("Separate certificate only supported by PRISM")
    authority.check()
    claim, source, names, generated = (
        prepare_prism(raw, certificate)
        if kind == "prism"
        else prepare_aion(raw)
        if kind == "aion"
        else prepare_risk_demo(raw)
    )
    # Include any generated policy certificate as exact replay input; replay does
    # not trust or rerun search to choose a different certificate.
    if generated is not None:
        certificate = parsing.encode(generated)
    prefix = kind.replace("-", "_")
    label = (
        prefix
        + "_"
        + digest(raw + (certificate or b""))[:20]
        + "_"
        + str(sum(1 for _ in authority.out.glob(prefix + "_*.lean")))
    )
    proof = authority._prove(source, names, label)
    authority.check()
    d = dict(
        format=FORMAT,
        engine=kind,
        input_hex=raw.hex(),
        certificate_hex=None if certificate is None else certificate.hex(),
        input_sha256=digest(raw),
        certificate_sha256=None if certificate is None else digest(certificate),
        source_sha256=authority.frozen,
        lean_sha256=authority.tool_sha,
        dependency_revisions=authority.dependencies,
        claim=claim,
        proof=proof,
        implementation_correspondence=CORRESPONDENCE,
        authenticated_origin=False,
        production_authority=False,
    )
    d["receipt_sha256"] = digest(parsing.encode(d))
    return d


def _publish(out, data):
    """Atomic no-clobber publication on the supported POSIX host filesystem.

    This protects against accidental concurrent writes, not a hostile host.
    The temporary file is synced before linking its complete bytes into place.
    """
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=".pcs-scientific-", dir=out.parent)
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(parsing.encode(data))
            f.flush()
            os.fsync(f.fileno())
        try:
            os.link(name, out)
        except FileExistsError as e:
            raise ValueError("Refusing historical evidence overwrite") from e
        directory = os.open(out.parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        os.unlink(name)
    return data


def verify(kind, raw, authority, *, certificate=None, out):
    if Path(out).exists():
        raise ValueError("Refusing historical evidence overwrite")
    return _publish(out, _derive(kind, raw, authority, certificate=certificate))


def replay(raw, authority, *, out):
    d = parsing.load(raw, evidence=True)
    required = {
        "format",
        "engine",
        "input_hex",
        "certificate_hex",
        "input_sha256",
        "certificate_sha256",
        "source_sha256",
        "lean_sha256",
        "dependency_revisions",
        "claim",
        "proof",
        "implementation_correspondence",
        "authenticated_origin",
        "production_authority",
        "receipt_sha256",
    }
    parsing.exact(d, required)
    if (
        d["format"] != FORMAT
        or d["production_authority"] is not False
        or d["authenticated_origin"] is not False
    ):
        raise ValueError("Unknown authority/format")
    if (
        d["implementation_correspondence"] != CORRESPONDENCE
        or d["proof"].get("kernel_checked") is not True
    ):
        raise ValueError("Unsupported verification contract")
    body = {k: v for k, v in d.items() if k != "receipt_sha256"}
    if digest(parsing.encode(body)) != d["receipt_sha256"]:
        raise ValueError("Receipt changed")
    if (
        d["source_sha256"] != authority.frozen
        or d["lean_sha256"] != authority.tool_sha
        or d["dependency_revisions"] != authority.dependencies
    ):
        raise ValueError("Source/tool/dependency binding differs")
    original = bytes.fromhex(d["input_hex"])
    cert = None if d["certificate_hex"] is None else bytes.fromhex(d["certificate_hex"])
    if (
        digest(original) != d["input_sha256"]
        or (None if cert is None else digest(cert)) != d["certificate_sha256"]
    ):
        raise ValueError("Input binding differs")
    fresh = _derive(d["engine"], original, authority, certificate=cert)
    if (
        fresh["claim"] != d["claim"]
        or fresh["proof"]["proof_sha256"] != d["proof"]["proof_sha256"]
        or fresh["proof"]["axiom_closures"] != d["proof"]["axiom_closures"]
    ):
        raise ValueError("Independent replay differs")
    return _publish(out, fresh)
