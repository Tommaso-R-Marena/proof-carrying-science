"""Exact-scoped research composition using the existing HECK and PCSNext engines.

A synthetic observation never becomes empirical validation. This adapter is not
an inter-calculus equivalence proof, production authority, or immutable root.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
from pathlib import Path
import re
from typing import Any

from research.integration_v1.scoped_evidence import component, digest
from . import reference
from .differential import executable_identity, query_lean, response_issues

HERE = Path(__file__).resolve().parent
_ID = re.compile(r"[A-Za-z][A-Za-z0-9_.:-]{0,95}\Z", re.ASCII)
_SHA = re.compile(r"[0-9a-f]{64}\Z", re.ASCII)
THEOREM = "PCSScientificReceiver.verifiedWireSound"


class AssuranceError(ValueError):
    pass


def _identity(value: Any, label: str) -> None:
    if type(value) is not str or not _ID.fullmatch(value):
        raise AssuranceError(f"invalid {label}")


def _sha(value: Any) -> None:
    if type(value) is not str or not _SHA.fullmatch(value):
        raise AssuranceError("expected an exact lowercase SHA-256 identity")


@dataclass(frozen=True)
class ScientificAssumption:
    """Receiver-declared applicability premise, not an established scientific fact."""
    id: str
    subject_sha256: str
    statement: str
    predicate: str
    expected: bool

    def __post_init__(self) -> None:
        _identity(self.id, "assumption id")
        _sha(self.subject_sha256)
        if type(self.statement) is not str or not 1 <= len(self.statement) <= 2048:
            raise AssuranceError("assumption statement must be bounded nonempty text")
        _identity(self.predicate, "prediction predicate")
        if type(self.expected) is not bool:
            raise AssuranceError("prediction must be an exact boolean")

    @classmethod
    def from_dict(cls, value: Any) -> ScientificAssumption:
        if type(value) is not dict or set(value) != {"id", "subject_sha256", "statement", "predicate", "expected"}:
            raise AssuranceError("assumption fields must match the exact declared schema")
        return cls(**value)


@dataclass(frozen=True)
class SyntheticObservation:
    """Explicit synthetic control data bound to one artifact and exact prediction."""
    subject_sha256: str
    assumption_id: str
    prediction_key: str
    value: bool
    synthetic: bool = True

    def __post_init__(self) -> None:
        _sha(self.subject_sha256)
        _identity(self.assumption_id, "observation assumption id")
        _sha(self.prediction_key)
        if type(self.value) is not bool or self.synthetic is not True:
            raise AssuranceError("only exact boolean, explicitly synthetic controls are supported")

    @classmethod
    def from_dict(cls, value: Any) -> SyntheticObservation:
        if type(value) is not dict or set(value) != {"subject_sha256", "assumption_id", "prediction_key", "value", "synthetic"}:
            raise AssuranceError("observation fields must match the exact declared schema")
        return cls(**value)


def _obligation(assumption: ScientificAssumption):
    component("heck")
    from heck.predictive import PredictiveObligation
    return PredictiveObligation.from_prediction(
        id="prediction:" + assumption.id, theory_id="raw:" + assumption.subject_sha256,
        prediction={"assumption_id": assumption.id, "statement": assumption.statement,
                    "predicate": assumption.predicate, "value": assumption.expected},
    )


def prediction_key(assumption: ScientificAssumption) -> str:
    if type(assumption) is not ScientificAssumption:
        raise AssuranceError("typed ScientificAssumption required")
    return _obligation(assumption).prediction_key


def compose(raw: bytes, *, expected_raw_sha256: str,
            assumptions: tuple[ScientificAssumption, ...],
            observations: tuple[SyntheticObservation, ...] = (),
            checker: Path | None = None, checker_args: tuple[str, ...] = (),
            checker_cwd: Path | None = None) -> dict[str, Any]:
    """Recompute evidence; no supplied PASS, receipt, rank or verifier callback.

    ``checker`` is an operator-controlled differential-harness command, not an
    input protocol field or a production authority interface. Its executable,
    arguments, imported code and host remain trusted; a supplied verdict is
    never used. Compiler/IO/source correspondence requires separate qualification.
    """
    if type(raw) is not bytes:
        raise AssuranceError("immutable raw bytes required")
    _sha(expected_raw_sha256)
    subject = hashlib.sha256(raw).hexdigest()
    if subject != expected_raw_sha256:
        raise AssuranceError("raw artifact does not match receiver-owned identity")
    decision = reference.assess(raw)
    if not decision.accepted:
        raise AssuranceError("independent exact replay rejected: " + decision.reason)
    if type(assumptions) is not tuple or not 1 <= len(assumptions) <= 16:
        raise AssuranceError("one to sixteen typed assumptions are required")
    if type(observations) is not tuple or len(observations) > 64:
        raise AssuranceError("at most 64 typed observations are supported")
    if any(type(a) is not ScientificAssumption or a.subject_sha256 != subject for a in assumptions):
        raise AssuranceError("assumption type or raw artifact scope mismatch")
    if len({a.id for a in assumptions}) != len(assumptions):
        raise AssuranceError("duplicate assumption identifiers")
    by_id = {a.id: a for a in assumptions}
    obligations = {a.id: _obligation(a) for a in assumptions}
    for observation in observations:
        if (type(observation) is not SyntheticObservation or observation.subject_sha256 != subject
                or observation.assumption_id not in by_id
                or observation.prediction_key != obligations[observation.assumption_id].prediction_key):
            raise AssuranceError("observation has unrelated artifact, assumption, or prediction scope")

    lean: dict[str, Any] = {"status": "NOT_RUN", "acceptance": None}
    if checker is not None:
        before = executable_identity(checker, checker_args, checker_cwd)
        response = query_lean(checker, [raw], checker_args=checker_args, checker_cwd=checker_cwd)[0]
        after = executable_identity(checker, checker_args, checker_cwd)
        if before != after:
            raise AssuranceError("checker executable or argument file changed during replay")
        issues = response_issues(raw, response, decision)
        if response.get("accepted") is not True or issues:
            raise AssuranceError(f"actual Lean response disagrees with exact scoped replay: {issues}")
        lean = {"status": "ACTUAL_COMPILED_RECEIVER_REPLAYED", "acceptance": True,
                "checker_identity": before, "response": response,
                "scope": "Research executable observation, not protected execution attestation."}
    elif checker_args or checker_cwd is not None:
        raise AssuranceError("checker arguments require an actual checker command")

    component("pcs_next_v1")
    from heck.predictive import PredStatus, discharge_sticky, observe_against_prediction
    import heck.predictive as heck_engine
    import pcs_next_v1.translation.pog as graph_engine
    from pcs_next_v1.core.statuses import AssuranceStatus
    from pcs_next_v1.translation.pog import ProofObligationGraph, ObligationNode, assert_well_formed
    graph = ProofObligationGraph()
    computational_id = "computation:" + subject
    graph.add(ObligationNode(computational_id, "Exact rational replay of these model bytes",
                            artifact_ids=[subject], status=AssuranceStatus.COMPUTATIONALLY_TESTED))
    for a in assumptions:
        node = "assumption:" + a.id
        graph.add(ObligationNode(node, a.statement,
                                artifact_ids=[obligations[a.id].prediction_key], status=AssuranceStatus.OPEN))
        graph.add(ObligationNode("prediction:" + a.id, "Synthetic compatibility under declared premise",
                                depends_on=[node], status=AssuranceStatus.CONDITIONAL))
    graph.add(ObligationNode("scientific:applicability", "Applicability to the declared scientific case",
                            depends_on=["prediction:" + a.id for a in assumptions],
                            status=AssuranceStatus.CONDITIONAL))
    assert_well_formed(graph)
    events = []
    reopened: set[str] = set()
    for index, observation in enumerate(observations):
        a = by_id[observation.assumption_id]
        old = obligations[a.id]
        observed = {**dict(old.prediction), "value": observation.value}
        actual_observation = observe_against_prediction(old, observed)
        updated = discharge_sticky(old, actual_observation)
        obligations[a.id] = updated
        affected = graph.invalidate_from(old.prediction_key) if updated.status is PredStatus.FALSIFIED else []
        reopened.update(affected)
        events.append({"index": index, "observation": asdict(observation),
                       "heck_observation_kind": actual_observation.kind.value,
                       "heck_internal_status": updated.status.value, "reopened": affected,
                       "empirical_validation_granted": False})
    falsified = sorted(key for key, obligation in obligations.items() if obligation.status is PredStatus.FALSIFIED)
    theorem_file = HERE / "formal/PCSScientificReceiver/Receiver.lean"
    theorem_sources = {name: hashlib.sha256((HERE / "formal/PCSScientificReceiver" / name).read_bytes()).hexdigest()
                       for name in ("Types.lean", "Codec.lean", "Semantics.lean", "Receiver.lean")}
    report = {
        "format": "pcs-scientific-assurance-composition-v1", "subject_sha256": subject,
        "model_scope": "PCS-SCI-BOUND-V1 exact finite rational A→B schedule and final enclosures",
        "assumptions": [asdict(a) for a in assumptions],
        "composition_engines": {name: {"source_file": str(Path(module.__file__).resolve().relative_to(HERE.parents[1])),
                                       "sha256": hashlib.sha256(Path(module.__file__).read_bytes()).hexdigest()}
                                for name, module in (("heck_predictive", heck_engine), ("pcsnext_pog", graph_engine))},
        "dimensions": {
            "formal_mathematics": {"status": "CONDITIONAL_THEOREM_SOURCE_IDENTIFIED", "theorem": THEOREM,
                "source_sha256": hashlib.sha256(theorem_file.read_bytes()).hexdigest(),
                "local_theorem_source_modules": theorem_sources,
                "selected_checker_source_binding": "OPEN; separate executable/import qualification required",
                "conditional_on": "Pure receive(raw)=some(result), under the declared supported semantics.",
                "fresh_kernel_audit_in_this_composition": False, "invalidated_by_observation": False},
            "executable_correspondence": {"status": "OPEN", "actual_replay": lean,
                "limitation": "Compiler, IR/import objects, source-to-executable, IO and OS remain trusted."},
            "artifact_integrity": {"status": "RAW_SHA256_MATCHED", "raw_sha256": subject},
            "cryptographic_authentication": {"status": "NOT_ESTABLISHED"},
            "computational_reproducibility": {"status": "EXACT_REFERENCE_REPLAYED", "result": decision.result,
                                             "invalidated_by_observation": False},
            "numerical_uncertainty": {"status": "EXACT_DECLARED_RATIONAL_ENCLOSURE", "scope": "Declared discrete model only; no measurement or continuum uncertainty theorem."},
            "causal_identification": {"status": "NOT_CLAIMED"},
            "empirical_validation": {"status": "NOT_ESTABLISHED", "synthetic_only": True},
            "data_provenance": {"status": "RAW_IDENTITY_ONLY_NO_EXTERNAL_PROVENANCE"},
            "authenticated_history": {"status": "NOT_ESTABLISHED"},
            "known_refutations": {"status": "SYNTHETIC_COUNTEREXAMPLES_REPLAYED" if falsified else "NONE_OBSERVED",
                                  "prediction_ids": falsified, "empirical_refutation_established": False},
            "scientific_applicability": {"status": "REOPENED_BY_SYNTHETIC_FALSIFIER" if falsified else "CONDITIONAL_UNVALIDATED",
                                          "falsified_predictions": falsified},
        },
        "observations": events, "reopened": sorted(reopened), "obligation_graph": graph.to_dict(),
        "open_obligations": ["External empirical adequacy and measurement validity",
                             "Independent protected execution and authenticated history",
                             "Compiler/IO/OS and transitive runtime correspondence",
                             "Dependency completeness and cross-calculus refinement"],
        "scientific_acceptance": False, "production_authority": False, "promotion_authority": False,
    }
    report["report_sha256"] = digest(report)
    return report
