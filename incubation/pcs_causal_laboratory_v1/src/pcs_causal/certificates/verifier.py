"""Independent certificate verifier — fail closed; never trust producer_pass."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, List, Tuple

from pcs_causal.certificates.format import CausalCertificate, CertificateKind
from pcs_causal.graphs.dag import CausalDAG, GraphError
from pcs_causal.graphs.d_separation import d_separated
from pcs_causal.hypothesis.states import ScientificStatus
from pcs_causal.identification.backdoor import verify_backdoor_set
from pcs_causal.identification.frontdoor import check_frontdoor


@dataclass(frozen=True, slots=True)
class VerificationReport:
    accepted: bool
    status: ScientificStatus
    kind: str
    conclusion: str
    assumptions: Tuple[str, ...]
    unexplained_scientific_obligations: Tuple[str, ...]
    details: Tuple[str, ...]

    def to_dict(self) -> dict:
        return {
            "accepted": self.accepted,
            "status": self.status.value,
            "kind": self.kind,
            "conclusion": self.conclusion,
            "assumptions": list(self.assumptions),
            "unexplained_scientific_obligations": list(
                self.unexplained_scientific_obligations
            ),
            "details": list(self.details),
        }


def verify_certificate(cert: CausalCertificate) -> VerificationReport:
    if cert.version not in {"pcs-causal-cert-v1"}:
        return _reject(cert, f"unsupported certificate version: {cert.version}")

    try:
        if cert.kind == CertificateKind.BACKDOOR_IDENTIFICATION:
            return _verify_backdoor(cert)
        if cert.kind == CertificateKind.FRONTDOOR_IDENTIFICATION:
            return _verify_frontdoor(cert)
        if cert.kind == CertificateKind.D_SEPARATION:
            return _verify_dsep(cert)
        if cert.kind == CertificateKind.NONIDENTIFIABILITY_WITNESS:
            return _verify_nonident(cert)
        if cert.kind == CertificateKind.EXPERIMENT_DISTINGUISHABILITY:
            return _verify_experiment(cert)
        if cert.kind == CertificateKind.INTERVENTION_SEMANTICS:
            return _verify_intervention_semantics(cert)
        return _reject(cert, f"unsupported kind: {cert.kind}")
    except (GraphError, KeyError, ValueError, TypeError) as e:
        return _reject(cert, f"malformed certificate: {e}")


def _reject(cert: CausalCertificate, reason: str) -> VerificationReport:
    return VerificationReport(
        accepted=False,
        status=ScientificStatus.UNSUPPORTED,
        kind=cert.kind.value if isinstance(cert.kind, CertificateKind) else str(cert.kind),
        conclusion="rejected",
        assumptions=tuple(cert.assumptions),
        unexplained_scientific_obligations=tuple(cert.assumptions),
        details=(reason, "fail_closed"),
    )


def _graph(cert: CausalCertificate) -> CausalDAG:
    return CausalDAG.from_dict(cert.graph)


def _verify_backdoor(cert: CausalCertificate) -> VerificationReport:
    g = _graph(cert)
    q = cert.query
    z = cert.payload.get("adjustment_set", [])
    res = verify_backdoor_set(g, q["treatment"], q["outcome"], z)
    # Ignore producer_pass entirely
    if not res.valid:
        return VerificationReport(
            accepted=False,
            status=ScientificStatus.NOT_IDENTIFIABLE,
            kind=cert.kind.value,
            conclusion="backdoor identification rejected",
            assumptions=res.assumptions,
            unexplained_scientific_obligations=res.assumptions,
            details=res.reasons,
        )
    return VerificationReport(
        accepted=True,
        status=ScientificStatus.IDENTIFIED_UNDER_ASSUMPTIONS,
        kind=cert.kind.value,
        conclusion=res.formula or "backdoor identification accepted",
        assumptions=res.assumptions,
        unexplained_scientific_obligations=res.assumptions
        + (
            "Assumptions are not empirically validated by this certificate.",
        ),
        details=res.reasons,
    )


def _verify_frontdoor(cert: CausalCertificate) -> VerificationReport:
    g = _graph(cert)
    q = cert.query
    m = cert.payload.get("mediators", [])
    res = check_frontdoor(g, q["treatment"], q["outcome"], m)
    if not res.valid:
        return VerificationReport(
            accepted=False,
            status=ScientificStatus.NOT_IDENTIFIABLE,
            kind=cert.kind.value,
            conclusion="frontdoor identification rejected",
            assumptions=res.assumptions,
            unexplained_scientific_obligations=res.assumptions,
            details=res.reasons,
        )
    return VerificationReport(
        accepted=True,
        status=ScientificStatus.IDENTIFIED_UNDER_ASSUMPTIONS,
        kind=cert.kind.value,
        conclusion=res.formula or "frontdoor identification accepted",
        assumptions=res.assumptions,
        unexplained_scientific_obligations=res.assumptions
        + ("Assumptions are not empirically validated by this certificate.",),
        details=res.reasons,
    )


def _verify_dsep(cert: CausalCertificate) -> VerificationReport:
    g = _graph(cert)
    q = cert.query
    claim_sep = bool(cert.payload.get("separated", True))
    actual = d_separated(g, q["x"], q["y"], q.get("z", []))
    if actual != claim_sep:
        return _reject(
            cert,
            f"d-separation mismatch: claimed separated={claim_sep}, recomputed={actual}",
        )
    return VerificationReport(
        accepted=True,
        status=ScientificStatus.IDENTIFIED_UNDER_ASSUMPTIONS,
        kind=cert.kind.value,
        conclusion=f"d-separation claim verified: separated={actual}",
        assumptions=tuple(cert.assumptions)
        or ("graphical_markov_condition_for_independence_interpretation",),
        unexplained_scientific_obligations=(
            "Graphical d-separation equals CI only under Markov; faithfulness not assumed.",
        ),
        details=(f"recomputed_separated={actual}",),
    )


def _verify_nonident(cert: CausalCertificate) -> VerificationReport:
    """Payload must embed two serializable observational/interventional exact dists."""
    from fractions import Fraction
    from pcs_causal.probability.rational_pmf import FiniteDistribution

    payload = cert.payload
    try:
        obs_a = FiniteDistribution.from_dict(payload["observational_a"])
        obs_b = FiniteDistribution.from_dict(payload["observational_b"])
        int_a = FiniteDistribution.from_dict(payload["interventional_a"])
        int_b = FiniteDistribution.from_dict(payload["interventional_b"])
    except Exception as e:
        return _reject(cert, f"witness distributions malformed: {e}")

    obs_tv = obs_a.total_variation(obs_b)
    int_tv = int_a.total_variation(int_b)
    if obs_tv != 0:
        return _reject(cert, f"observational TV != 0 ({obs_tv})")
    if int_tv == 0:
        return _reject(cert, "interventional distributions agree; not a witness")
    return VerificationReport(
        accepted=True,
        status=ScientificStatus.NOT_IDENTIFIABLE,
        kind=cert.kind.value,
        conclusion=(
            "Non-identifiability witness accepted within the finite distribution "
            "model class encoded in the certificate payload."
        ),
        assumptions=tuple(cert.assumptions),
        unexplained_scientific_obligations=tuple(cert.assumptions)
        + (
            "Witness is scoped to the encoded finite models, not all causal formalisms.",
        ),
        details=(f"obs_tv={obs_tv}", f"interv_tv={int_tv}"),
    )


def _verify_experiment(cert: CausalCertificate) -> VerificationReport:
    from pcs_causal.probability.rational_pmf import FiniteDistribution

    pred_a = FiniteDistribution.from_dict(cert.payload["prediction_a"])
    pred_b = FiniteDistribution.from_dict(cert.payload["prediction_b"])
    tv = pred_a.total_variation(pred_b)
    min_tv = Fraction_from(cert.payload.get("min_tv", [0, 1]))
    if tv <= min_tv:
        return _reject(cert, f"predictions not distinguished: TV={tv} <= {min_tv}")
    return VerificationReport(
        accepted=True,
        status=ScientificStatus.EXPERIMENT_PROPOSED,
        kind=cert.kind.value,
        conclusion=(
            f"Simulated intervention distinguishes models (TV={tv}). "
            "No real-world experiment was performed."
        ),
        assumptions=tuple(cert.assumptions),
        unexplained_scientific_obligations=tuple(cert.assumptions),
        details=(f"tv={tv}", "simulated_only=true"),
    )


def _verify_intervention_semantics(cert: CausalCertificate) -> VerificationReport:
    from pcs_causal.probability.rational_pmf import FiniteDistribution

    cond = FiniteDistribution.from_dict(cert.payload["conditional_outcome"])
    interv = FiniteDistribution.from_dict(cert.payload["interventional_outcome"])
    differ = not cond.equals_exact(interv)
    claim_differ = bool(cert.payload.get("claim_differ", True))
    if differ != claim_differ:
        return _reject(cert, "conditioning vs intervention difference claim failed")
    return VerificationReport(
        accepted=True,
        status=ScientificStatus.IDENTIFIED_UNDER_ASSUMPTIONS,
        kind=cert.kind.value,
        conclusion=(
            "Verified that in the encoded finite model, conditioning and intervention "
            f"on the stated variables {'differ' if differ else 'agree'}."
        ),
        assumptions=tuple(cert.assumptions),
        unexplained_scientific_obligations=tuple(cert.assumptions),
        details=(f"distributions_differ={differ}",),
    )


def Fraction_from(pair) -> "Fraction":
    from fractions import Fraction

    if isinstance(pair, Fraction):
        return pair
    return Fraction(pair[0], pair[1])
