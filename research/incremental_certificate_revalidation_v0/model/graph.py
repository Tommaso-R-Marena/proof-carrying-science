"""Computation DAG model aligned with PCSIncremental Lean concepts.

Exact equality for obligation keys. Digests are never treated as proofs.
"""
from __future__ import annotations

from dataclasses import dataclass, field, replace
from fractions import Fraction
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple, Union

Value = Union[int, Fraction]
# Canonical JSON-safe encoding used in obligation keys and certificate payloads.
CanonValue = Any  # nested tuples/lists/ints/strs
NodeId = int
ChangeSet = List[NodeId]


class WellFormedError(ValueError):
    pass


class CycleError(ValueError):
    pass


def canonicalize_value(v: Value) -> CanonValue:
    if isinstance(v, bool):
        raise TypeError("bool is not a Value")
    if isinstance(v, int):
        return ("int", v)
    if isinstance(v, Fraction):
        return ("rat", v.numerator, v.denominator)
    raise TypeError(f"unsupported value type: {type(v)!r}")


def decode_value(c: CanonValue) -> Value:
    if isinstance(c, tuple):
        if len(c) == 2 and c[0] == "int":
            return int(c[1])
        if len(c) == 3 and c[0] == "rat":
            return Fraction(int(c[1]), int(c[2]))
    raise ValueError(f"bad canon value: {c!r}")


def encode_value(v: Value) -> CanonValue:
    return canonicalize_value(v)


def reject_duplicate_keys(pairs: List[Tuple[str, Any]]) -> dict:
    out: dict = {}
    for k, v in pairs:
        if k in out:
            raise ValueError(f"duplicate JSON key: {k}")
        out[k] = v
    return out


@dataclass(frozen=True)
class ObligationKey:
    id: NodeId
    op: int
    policy: int
    version: int
    evidence: int
    dep_outputs: Tuple[CanonValue, ...]

    def as_tuple(self) -> Tuple:
        return (self.id, self.op, self.policy, self.version, self.evidence, self.dep_outputs)

    def to_json(self) -> dict:
        return {
            "id": self.id,
            "op": self.op,
            "policy": self.policy,
            "version": self.version,
            "evidence": self.evidence,
            "dep_outputs": [list(x) if isinstance(x, tuple) else x for x in self.dep_outputs],
        }

    @staticmethod
    def from_json(d: dict) -> "ObligationKey":
        deps = []
        for x in d["dep_outputs"]:
            deps.append(tuple(x) if isinstance(x, list) else x)
        return ObligationKey(
            id=int(d["id"]),
            op=int(d["op"]),
            policy=int(d["policy"]),
            version=int(d["version"]),
            evidence=int(d["evidence"]),
            dep_outputs=tuple(deps),
        )


def eligible(cached: ObligationKey, current: ObligationKey) -> bool:
    return cached == current


def _payload_to_json(payload: CanonValue) -> Any:
    if isinstance(payload, tuple):
        return [_payload_to_json(x) for x in payload]
    return payload


def _payload_from_json(obj: Any) -> CanonValue:
    if isinstance(obj, list):
        return tuple(_payload_from_json(x) for x in obj)
    return obj


@dataclass(frozen=True)
class Certificate:
    payload: CanonValue
    output: Value

    def to_json(self) -> dict:
        return {"payload": _payload_to_json(self.payload), "output": encode_value(self.output)}

    @staticmethod
    def from_json(d: dict) -> "Certificate":
        return Certificate(payload=_payload_from_json(d["payload"]), output=decode_value(tuple(d["output"]) if isinstance(d["output"], list) else d["output"]))


@dataclass(frozen=True)
class Node:
    id: NodeId
    op: int
    deps: Tuple[NodeId, ...]
    policy: int
    version: int
    evidence: int

    def to_json(self) -> dict:
        return {
            "id": self.id,
            "op": self.op,
            "deps": list(self.deps),
            "policy": self.policy,
            "version": self.version,
            "evidence": self.evidence,
        }

    @staticmethod
    def from_json(d: dict) -> "Node":
        return Node(
            id=int(d["id"]),
            op=int(d["op"]),
            deps=tuple(int(x) for x in d["deps"]),
            policy=int(d["policy"]),
            version=int(d["version"]),
            evidence=int(d["evidence"]),
        )


@dataclass
class Graph:
    nodes: List[Node] = field(default_factory=list)

    def by_id(self) -> Dict[NodeId, Node]:
        return {n.id: n for n in self.nodes}

    def ids(self) -> List[NodeId]:
        return [n.id for n in self.nodes]

    def copy(self) -> "Graph":
        return Graph(nodes=list(self.nodes))

    def check_well_formed(self) -> None:
        seen: Set[NodeId] = set()
        for n in self.nodes:
            if n.id in seen:
                raise WellFormedError(f"duplicate node id {n.id}")
            seen.add(n.id)
        index = self.by_id()
        for n in self.nodes:
            for d in n.deps:
                if d not in index:
                    raise WellFormedError(f"node {n.id} missing dependency {d}")

    def topological_rank(self) -> Dict[NodeId, int]:
        order = self.topo_order()
        return {n.id: i for i, n in enumerate(order)}

    def topo_order(self) -> List[Node]:
        index = self.by_id()
        indeg = {n.id: 0 for n in self.nodes}
        children: Dict[NodeId, List[NodeId]] = {n.id: [] for n in self.nodes}
        for n in self.nodes:
            for d in n.deps:
                if d not in index:
                    raise WellFormedError(f"missing dependency {d}")
                indeg[n.id] += 1
                children[d].append(n.id)
        queue = [i for i, deg in indeg.items() if deg == 0]
        order: List[Node] = []
        while queue:
            i = queue.pop(0)
            order.append(index[i])
            for c in children[i]:
                indeg[c] -= 1
                if indeg[c] == 0:
                    queue.append(c)
        if len(order) != len(self.nodes):
            raise CycleError("dependency cycle detected")
        return order

    def reverse_adj(self) -> Dict[NodeId, List[NodeId]]:
        adj: Dict[NodeId, List[NodeId]] = {n.id: [] for n in self.nodes}
        for n in self.nodes:
            for d in n.deps:
                adj[d].append(n.id)
        return adj

    def affected_closure(self, changes: Sequence[NodeId]) -> Set[NodeId]:
        index = self.by_id()
        for c in changes:
            if c not in index:
                raise WellFormedError(f"change references unknown id {c}")
        adj = self.reverse_adj()
        affected: Set[NodeId] = set()
        stack = list(changes)
        while stack:
            u = stack.pop()
            if u in affected:
                continue
            affected.add(u)
            stack.extend(adj.get(u, []))
        return affected

    def replace_nodes(self, replacements: Sequence[Node]) -> "Graph":
        by = self.by_id()
        for n in replacements:
            if n.id not in by:
                raise WellFormedError(f"replace unknown id {n.id}")
            by[n.id] = n
        # preserve original order
        return Graph(nodes=[by[n.id] for n in self.nodes])

    def to_json(self) -> dict:
        return {"nodes": [n.to_json() for n in self.nodes]}

    @staticmethod
    def from_json(d: dict) -> "Graph":
        return Graph(nodes=[Node.from_json(n) for n in d["nodes"]])


def obligation_of(n: Node, dep_outputs: Sequence[Value]) -> ObligationKey:
    return ObligationKey(
        id=n.id,
        op=n.op,
        policy=n.policy,
        version=n.version,
        evidence=n.evidence,
        dep_outputs=tuple(canonicalize_value(v) for v in dep_outputs),
    )
