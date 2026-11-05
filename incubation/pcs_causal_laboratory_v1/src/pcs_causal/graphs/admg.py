"""Acyclic directed mixed graphs for explicit latent confounding.

Bidirected edges A ↔ B represent an unmeasured common cause of A and B
(or an equivalent latent confounding relation in the model class). Ordinary
DAGs do not encode arbitrary unmeasured confounding.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import FrozenSet, Iterable, Mapping

from pcs_causal.graphs.dag import CausalDAG, GraphError


@dataclass(frozen=True, slots=True)
class ADMG:
    """Acyclic directed mixed graph: directed edges plus bidirected edges."""

    directed: CausalDAG
    bidirected: FrozenSet[frozenset[str]]

    def __post_init__(self) -> None:
        for e in self.bidirected:
            if len(e) != 2:
                raise GraphError("bidirected edge must connect exactly two distinct nodes")
            if not e <= self.directed.nodes:
                raise GraphError("bidirected edge references unknown node")

    @classmethod
    def from_edges(
        cls,
        nodes: Iterable[str],
        directed_edges: Iterable[tuple[str, str]],
        bidirected_edges: Iterable[tuple[str, str]] = (),
    ) -> "ADMG":
        dag = CausalDAG.from_edges(nodes, directed_edges)
        bi = frozenset(frozenset((a, b)) for a, b in bidirected_edges)
        return cls(directed=dag, bidirected=bi)

    @property
    def nodes(self) -> FrozenSet[str]:
        return self.directed.nodes

    def has_latent_confounding(self, a: str, b: str) -> bool:
        return frozenset((a, b)) in self.bidirected

    def to_dag_projection_warning(self) -> str:
        if self.bidirected:
            return (
                "ADMG contains bidirected edges; projecting to a DAG loses "
                "explicit latent confounding structure."
            )
        return "No bidirected edges; DAG projection is exact for this ADMG."

    def to_dict(self) -> dict:
        return {
            "nodes": sorted(self.nodes),
            "directed_edges": sorted([list(e) for e in self.directed.edges]),
            "bidirected_edges": sorted(
                [sorted(list(e)) for e in self.bidirected]
            ),
        }

    @classmethod
    def from_dict(cls, data: Mapping) -> "ADMG":
        return cls.from_edges(
            data["nodes"],
            [tuple(e) for e in data["directed_edges"]],
            [tuple(e) for e in data.get("bidirected_edges", [])],
        )
