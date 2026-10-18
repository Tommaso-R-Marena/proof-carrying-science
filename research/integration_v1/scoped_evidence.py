"""Receiving replay with explicit scope; no production or promotion authority.

The host interpreter, imported libraries and source storage remain trusted.
These receipts record computation, not Python-to-Lean refinement or science.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import importlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
COMPONENTS = {
    "certnum": "incubation/pcs_certified_numerics_v1/python",
    "pcca": "incubation/pcs_conservation_algebra_v1/python",
    "pcs_causal": "incubation/pcs_causal_laboratory_v1/src",
    "pcs_next_v1": "incubation/pcs_next_v1",
    "heck": "incubation/pcs_heterogeneous_compose_v1",
}


class ComponentUnavailable(RuntimeError):
    pass


def component(name: str, *, root: Path = ROOT):
    """Load only the selected checkout's namespace, rejecting cached collisions."""
    if name not in COMPONENTS:
        raise ComponentUnavailable(f"unknown component: {name}")
    directory = (root / COMPONENTS[name]).resolve()
    package = directory / name
    if not (package / "__init__.py").is_file():
        raise ComponentUnavailable(f"ABSENT: {name}")
    cached = sys.modules.get(name)
    if cached is not None and Path(cached.__file__).resolve().parent != package:
        raise ComponentUnavailable(f"conflicting imported component: {name}")
    if str(directory) not in sys.path:
        sys.path.insert(0, str(directory))
    result = importlib.import_module(name)
    if Path(result.__file__).resolve().parent != package:
        raise ComponentUnavailable(f"component resolved outside selected checkout: {name}")
    return result


def digest(value) -> str:
    """Version-local JSON identity, not an RFC8785/PCS certificate codec."""
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                     ensure_ascii=True, allow_nan=False).encode()).hexdigest()


@dataclass(frozen=True)
class ScopedObservation:
    id: str
    subject_sha256: str
    category: str
    scope: str
    outcome: str
    assumptions: tuple[str, ...]
    open_obligations: tuple[str, ...]

    def to_dict(self):
        return {"format": "pcs-scoped-research-evidence-v1", **asdict(self),
                "pcs_authority": False, "scientific_acceptance": False,
                "promotion_authority": False}

    def supports(self, *, category: str, scope: str) -> bool:
        # This adapter grants only exact-scoped computational observations.
        # Neither an original calculus's declared rank nor a PASS flag upgrades it.
        return (self.category == category == "computationally_reproduced"
                and self.scope == scope and self.outcome == "REPLAYED")


def replay_interval(certificate: dict) -> ScopedObservation:
    component("certnum")
    from certnum.certificate.checker import check_certificate
    if certificate.get("format") != "certnum-cert-v1" or certificate.get("kind") != "interval_enclosure":
        raise ValueError("only interval_enclosure is supported by this adapter")
    result = check_certificate(certificate)
    if not result.accepted:
        raise ValueError(f"interval rejected: {result.reasons}")
    key = digest(certificate)
    return ScopedObservation("certnum:" + key, key, "computationally_reproduced",
                             "certnum.interval_enclosure:" + digest(certificate["claim"]),
                             "REPLAYED", ("Exact rational expression and declared box.",),
                             ("Python-to-Lean correspondence OPEN.", "Empirical validity OPEN."))


def replay_conservation(contract: dict):
    component("pcca")
    from pcca.receiver.replay import receive_contract
    from pcca.certificate.checker import check_certificate
    # The original parser calls int(); refuse lossy coercion before replay.
    for reaction in contract["reactions"]:
        for side in ("reactants", "products"):
            for term in reaction[side]:
                value = term["coefficient"]
                if type(value) is not int or value < 0:
                    raise ValueError("stoichiometric coefficients must be exact nonnegative integers")
    report = receive_contract(contract)
    if not report.accepted or not report.certificates:
        raise ValueError(f"conservation rejected: {report.reasons}")
    if not all(check_certificate(c).accepted for c in report.certificates):
        raise ValueError("receiving certificate replay failed")
    key = digest(contract)
    observations = [ScopedObservation("pcca:" + digest(c), key,
                     "computationally_reproduced", "pcca." + c["kind"] + ":" + digest(c["claim"]),
                     "REPLAYED", tuple(contract.get("assumptions", ())),
                     ("Python-to-Lean correspondence OPEN.", "Continuum accuracy OPEN.",
                      "Empirical chemistry OPEN.")) for c in report.certificates]
    return observations, report.to_json()


def replay_nonidentifiability():
    component("pcs_causal")
    from pcs_causal.nonident.witness_search import classic_confounding_witness
    from pcs_causal.nonident.witness_verifier import verify_witness
    result = verify_witness(classic_confounding_witness())
    if not result.accepted or result.status.value != "NOT_IDENTIFIABLE":
        raise ValueError("finite SCM counterexample did not replay")
    return {"format": "pcs-scoped-causal-negative-v1", "result": result.to_dict(),
            "causal_effect_supported": False, "pcs_authority": False,
            "scientific_acceptance": False}


def falsify_dependency():
    """Actual HECK sticky falsification reopens the actual PCSNext reverse cone."""
    component("heck")
    component("pcs_next_v1")
    from heck.predictive import PredictiveObligation, Observation, discharge_sticky, PredStatus
    from pcs_next_v1.translation.pog import ProofObligationGraph, ObligationNode, assert_well_formed
    from pcs_next_v1.core.statuses import AssuranceStatus
    prediction = PredictiveObligation.from_prediction(id="prediction:closed", theory_id="synthetic",
                                                     prediction={"closed_compartment": True})
    falsified = discharge_sticky(prediction, Observation.contradict(prediction.prediction_key))
    graph = ProofObligationGraph()
    graph.add(ObligationNode("pcca:assumption", "closed compartment", artifact_ids=[prediction.prediction_key],
                            status=AssuranceStatus.COMPUTATIONALLY_TESTED))
    graph.add(ObligationNode("certnum:dependent", "conditional scientific support",
                            depends_on=["pcca:assumption"], status=AssuranceStatus.COMPUTATIONALLY_TESTED))
    assert_well_formed(graph)
    changed = graph.invalidate_from(prediction.prediction_key) if falsified.status is PredStatus.FALSIFIED else []
    retained = discharge_sticky(falsified, Observation.match(prediction.prediction_key))
    return {"falsifier_status": retained.status.value, "reopened": changed,
            "graph": graph.to_dict(), "mathematical_theorems_invalidated": False,
            "explanation": "Conditional empirical support reopens; mathematical implications remain true."}
