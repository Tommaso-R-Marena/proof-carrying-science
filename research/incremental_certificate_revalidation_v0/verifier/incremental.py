"""
Incremental certificate revalidation engine.

Load DAG → full initial verify → record eligible evidence → apply changes →
affected closure (reverse dep BFS) → revalidate affected → reuse
eligible+authoritative entries → replayable report → compare to fresh.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Set

from cache.store import Cache, CacheEntry, ValidState, reuse_permitted
from model.graph import (
    Certificate,
    ChangeSet,
    Graph,
    Node,
    ObligationKey,
    Value,
    WellFormedError,
    CycleError,
    obligation_of,
    reject_duplicate_keys,
)
from model.ops import OpRegistry, default_registry
from reference.fresh import FreshReport, fresh_verify


@dataclass
class TraceEvent:
    kind: str
    node_id: Optional[int] = None
    detail: Dict[str, Any] = field(default_factory=dict)

    def to_json(self) -> dict:
        return {"kind": self.kind, "node_id": self.node_id, "detail": self.detail}


@dataclass
class IncrementalReport:
    accepted: bool
    outputs: Dict[int, Value] = field(default_factory=dict)
    certs: Dict[int, Certificate] = field(default_factory=dict)
    reused: List[int] = field(default_factory=list)
    rechecked: List[int] = field(default_factory=list)
    rejected: List[int] = field(default_factory=list)
    affected: List[int] = field(default_factory=list)
    unaffected: List[int] = field(default_factory=list)
    changes: List[int] = field(default_factory=list)
    trace: List[TraceEvent] = field(default_factory=list)
    agrees_with_fresh: Optional[bool] = None
    fresh_accepted: Optional[bool] = None
    error: Optional[str] = None

    def to_json(self) -> dict:
        from model.graph import encode_value

        return {
            "accepted": self.accepted,
            "outputs": {str(k): encode_value(v) for k, v in self.outputs.items()},
            "reused": list(self.reused),
            "rechecked": list(self.rechecked),
            "rejected": list(self.rejected),
            "affected": list(self.affected),
            "unaffected": list(self.unaffected),
            "changes": list(self.changes),
            "agrees_with_fresh": self.agrees_with_fresh,
            "fresh_accepted": self.fresh_accepted,
            "error": self.error,
            "trace": [t.to_json() for t in self.trace],
        }


class IncrementalVerifier:
    """Executable incremental verifier with local prior-state cache."""

    def __init__(self, registry: Optional[OpRegistry] = None):
        self.registry = registry or default_registry()
        self.cache = Cache()
        self.valid_state: Optional[ValidState] = None
        self.graph: Optional[Graph] = None

    # ------------------------------------------------------------------ load
    def load_graph(self, graph: Graph) -> Graph:
        graph.check_well_formed()
        graph.topological_rank()  # reject cycles
        self.graph = graph
        return graph

    def load_json(self, path: str | Path) -> Graph:
        text = Path(path).read_text(encoding="utf-8")
        data = json.loads(text, object_pairs_hook=reject_duplicate_keys)
        g = Graph.from_json(data)
        return self.load_graph(g)

    # ----------------------------------------------------------- initial verify
    def initial_verify(self, graph: Optional[Graph] = None) -> IncrementalReport:
        """Full initial verify; populate authoritative cache; record ValidState."""
        g = graph or self.graph
        if g is None:
            raise ValueError("no graph loaded")
        self.load_graph(g)

        fresh = fresh_verify(g, self.registry)
        report = IncrementalReport(accepted=fresh.accepted, changes=[])
        if not fresh.accepted:
            report.rejected = list(fresh.rejected)
            report.error = fresh.error
            report.rechecked = list(fresh.checked)
            return report

        self.cache.clear()
        for nid, key in fresh.obligations.items():
            cert = fresh.certs[nid]
            self.cache.put_authoritative(key, cert)
            report.rechecked.append(nid)
            report.trace.append(
                TraceEvent("recheck", nid, {"ok": True, "initial": True})
            )

        self.valid_state = ValidState(
            graph=g.copy(),
            outputs=dict(fresh.outputs),
            cache=self.cache.copy(),
            well_formed=True,
            acyclic=True,
            certs=dict(fresh.certs),
        )
        self.graph = g
        report.outputs = dict(fresh.outputs)
        report.certs = dict(fresh.certs)
        report.accepted = True
        report.agrees_with_fresh = True
        report.fresh_accepted = True
        return report

    # --------------------------------------------------------------- revalidate
    def revalidate(
        self,
        new_graph: Graph,
        changes: ChangeSet,
        provided_certs: Optional[Mapping[int, Certificate]] = None,
        compare_fresh: bool = True,
    ) -> IncrementalReport:
        """
        Apply changes relative to prior ValidState.
        Affected nodes are rechecked; unaffected may reuse eligible+authoritative
        cache entries. Never grants authority from lookup alone.
        """
        if self.valid_state is None:
            raise ValueError("no prior ValidState; call initial_verify first")

        report = IncrementalReport(accepted=False, changes=list(changes))
        try:
            new_graph.check_well_formed()
            new_graph.topological_rank()
        except (WellFormedError, CycleError) as exc:
            report.error = str(exc)
            report.rejected = list(new_graph.ids())
            return report

        # Affected closure uses dependency topology of the *new* graph
        # (Lean Affected is topology-based; changes are roots).
        affected = new_graph.affected_closure(changes)
        all_ids = set(new_graph.ids())
        unaffected = all_ids - affected
        report.affected = sorted(affected)
        report.unaffected = sorted(unaffected)

        outputs: Dict[int, Value] = {}
        certs: Dict[int, Certificate] = {}
        new_cache = Cache()

        try:
            order = new_graph.topo_order()
        except CycleError as exc:
            report.error = str(exc)
            return report

        for node in order:
            dep_vals = [outputs[d] for d in node.deps]
            current_key = obligation_of(node, dep_vals)

            if node.id in unaffected:
                # May attempt reuse — only if reuse_permitted
                hit = self.cache.lookup(current_key)
                report.trace.append(
                    TraceEvent(
                        "lookup",
                        node.id,
                        {"hit": hit is not None, "key_id": current_key.id},
                    )
                )
                if hit is not None and reuse_permitted(hit, current_key):
                    # Defense in depth: re-run local check even for authoritative reuse.
                    ok = self.registry.local_check_node(
                        node.op,
                        node.version,
                        node.policy,
                        node.evidence,
                        dep_vals,
                        hit.cert.payload,
                        hit.cert.output,
                    )
                    if not ok:
                        report.rejected.append(node.id)
                        report.error = f"reused cert failed local check at {node.id}"
                        report.outputs = outputs
                        report.trace.append(TraceEvent("reuse_check_failed", node.id, {}))
                        return report
                    outputs[node.id] = hit.cert.output
                    certs[node.id] = hit.cert
                    new_cache.put_authoritative(current_key, hit.cert)
                    report.reused.append(node.id)
                    report.trace.append(
                        TraceEvent("reuse", node.id, {"key": list(current_key.as_tuple()[:5])})
                    )
                    continue
                # Fallback: must recheck even if unaffected if no authoritative reuse
                # (e.g. dep outputs somehow differ — shouldn't happen if unaffected,
                # but fail-closed).
                report.trace.append(
                    TraceEvent(
                        "reuse_denied",
                        node.id,
                        {
                            "reason": (
                                "no_authority"
                                if hit is not None and not hit.prior_accepted
                                else "miss_or_ineligible"
                            )
                        },
                    )
                )

            # Recheck path (affected OR reuse denied)
            if provided_certs is not None and node.id in provided_certs:
                cert = provided_certs[node.id]
            else:
                try:
                    cert = self.registry.make_cert(node.op, dep_vals, node.evidence)
                except (TypeError, ValueError) as exc:
                    report.rejected.append(node.id)
                    report.error = f"node {node.id}: {exc}"
                    report.outputs = outputs
                    return report

            ok = self.registry.local_check_node(
                node.op,
                node.version,
                node.policy,
                node.evidence,
                dep_vals,
                cert.payload,
                cert.output,
            )
            report.trace.append(TraceEvent("recheck", node.id, {"ok": ok}))
            if not ok:
                report.rejected.append(node.id)
                report.error = f"local check failed for node {node.id}"
                report.outputs = outputs
                return report

            outputs[node.id] = cert.output
            certs[node.id] = cert
            new_cache.put_authoritative(current_key, cert)
            report.rechecked.append(node.id)

        report.accepted = True
        report.outputs = outputs
        report.certs = certs

        # Update prior state for further incremental steps
        self.cache = new_cache
        self.graph = new_graph
        self.valid_state = ValidState(
            graph=new_graph.copy(),
            outputs=dict(outputs),
            cache=self.cache.copy(),
            well_formed=True,
            acyclic=True,
            certs=dict(certs),
        )

        if compare_fresh:
            fresh = fresh_verify(new_graph, self.registry, provided_certs=certs)
            report.fresh_accepted = fresh.accepted
            report.agrees_with_fresh = (
                fresh.accepted == report.accepted
                and _outputs_equal(fresh.outputs, report.outputs)
            )
            if not report.agrees_with_fresh:
                report.error = (
                    (report.error or "")
                    + f"; incremental/fresh disagreement: fresh={fresh.accepted}"
                )

        return report

    def apply_node_changes(
        self,
        replacements: Sequence[Node],
        compare_fresh: bool = True,
    ) -> IncrementalReport:
        """Replace nodes by id and revalidate with changes = replacement ids."""
        if self.graph is None:
            raise ValueError("no graph loaded")
        new_graph = self.graph.replace_nodes(replacements)
        changes = [n.id for n in replacements]
        return self.revalidate(new_graph, changes, compare_fresh=compare_fresh)


def _outputs_equal(a: Mapping[int, Value], b: Mapping[int, Value]) -> bool:
    from model.graph import canonicalize_value

    if set(a.keys()) != set(b.keys()):
        return False
    for k in a:
        if canonicalize_value(a[k]) != canonicalize_value(b[k]):
            return False
    return True
