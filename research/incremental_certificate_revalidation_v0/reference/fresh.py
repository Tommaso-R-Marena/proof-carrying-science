"""
Independent full-recomputation reference verifier.

NO incremental cache. Must not import incremental acceptance decisions.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Mapping, Optional

from model.graph import Certificate, Graph, ObligationKey, Value, obligation_of
from model.ops import OpRegistry, default_registry


@dataclass
class FreshReport:
    accepted: bool
    outputs: Dict[int, Value] = field(default_factory=dict)
    certs: Dict[int, Certificate] = field(default_factory=dict)
    obligations: Dict[int, ObligationKey] = field(default_factory=dict)
    rejected: List[int] = field(default_factory=list)
    checked: List[int] = field(default_factory=list)
    error: Optional[str] = None

    def to_json(self) -> dict:
        return {
            "accepted": self.accepted,
            "outputs": {str(k): _enc(v) for k, v in self.outputs.items()},
            "rejected": list(self.rejected),
            "checked": list(self.checked),
            "error": self.error,
        }


def _enc(v: Value):
    from model.graph import encode_value

    return encode_value(v)


def fresh_verify(
    graph: Graph,
    registry: Optional[OpRegistry] = None,
    provided_certs: Optional[Mapping[int, Certificate]] = None,
) -> FreshReport:
    """
    Full recomputation: every node must pass local_check_node.
    If provided_certs is given, validate those; otherwise compute certificates.
    """
    reg = registry or default_registry()
    report = FreshReport(accepted=False)
    try:
        order = graph.topo_order()
    except Exception as exc:
        report.error = str(exc)
        return report

    outputs: Dict[int, Value] = {}
    certs: Dict[int, Certificate] = {}
    obligations: Dict[int, ObligationKey] = {}

    for node in order:
        dep_vals = [outputs[d] for d in node.deps]
        if provided_certs is not None and node.id in provided_certs:
            cert = provided_certs[node.id]
        else:
            try:
                cert = reg.make_cert(node.op, dep_vals, node.evidence)
            except (TypeError, ValueError) as exc:
                report.rejected.append(node.id)
                report.error = f"node {node.id}: {exc}"
                report.outputs = outputs
                report.certs = certs
                return report

        ok = reg.local_check_node(
            node.op,
            node.version,
            node.policy,
            node.evidence,
            dep_vals,
            cert.payload,
            cert.output,
        )
        report.checked.append(node.id)
        if not ok:
            report.rejected.append(node.id)
            report.outputs = outputs
            report.certs = certs
            report.error = f"local check failed for node {node.id}"
            return report

        # assignment must match certificate output
        outputs[node.id] = cert.output
        certs[node.id] = cert
        obligations[node.id] = obligation_of(node, dep_vals)

    report.accepted = True
    report.outputs = outputs
    report.certs = certs
    report.obligations = obligations
    return report
