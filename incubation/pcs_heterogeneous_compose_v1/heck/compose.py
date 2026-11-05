"""Heterogeneous evidence composition receiver (Python mirror of Lean HECK)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Mapping, Sequence

from .levels import Level, meet_list, parse_level

FORMAT = "heck-composite-claim-v1"
ATOM_FORMAT = "heck-evidence-atom-v1"
MAX_LEAVES = 64
MAX_ATOMS = 256


@dataclass(frozen=True)
class EvidenceAtom:
    id: str
    level: Level
    supported: bool
    claim_id: str
    evidence_sha256: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "format": ATOM_FORMAT,
            "id": self.id,
            "level": self.level.value,
            "supported": self.supported,
            "claim_id": self.claim_id,
            "evidence_sha256": self.evidence_sha256,
        }

    @classmethod
    def from_dict(cls, obj: Mapping[str, Any]) -> "EvidenceAtom":
        if not isinstance(obj, Mapping):
            raise ValueError("evidence atom must be an object")
        required = {"format", "id", "level", "supported", "claim_id", "evidence_sha256"}
        if set(obj) != required:
            raise ValueError(f"evidence atom fields must be exactly {sorted(required)}")
        if obj["format"] != ATOM_FORMAT:
            raise ValueError("unsupported evidence atom format")
        if not isinstance(obj["id"], str) or not obj["id"] or len(obj["id"]) > 128:
            raise ValueError("bounded non-empty atom id required")
        if not isinstance(obj["claim_id"], str) or not obj["claim_id"] or len(obj["claim_id"]) > 128:
            raise ValueError("bounded non-empty claim id required")
        if not isinstance(obj["supported"], bool):
            raise ValueError("supported must be a JSON boolean")
        digest = obj["evidence_sha256"]
        if not isinstance(digest, str) or len(digest) != 64 or any(
            c not in "0123456789abcdef" for c in digest
        ):
            raise ValueError("evidence_sha256 must be lowercase hex SHA-256")
        return cls(
            id=obj["id"],
            level=parse_level(obj["level"]),
            supported=obj["supported"],
            claim_id=obj["claim_id"],
            evidence_sha256=digest,
        )


@dataclass(frozen=True)
class CompositeClaim:
    id: str
    required_level: Level
    leaf_ids: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "format": FORMAT,
            "id": self.id,
            "required_level": self.required_level.value,
            "leaf_ids": list(self.leaf_ids),
        }

    @classmethod
    def from_dict(cls, obj: Mapping[str, Any]) -> "CompositeClaim":
        if not isinstance(obj, Mapping):
            raise ValueError("composite claim must be an object")
        required = {"format", "id", "required_level", "leaf_ids"}
        if set(obj) != required:
            raise ValueError(f"composite claim fields must be exactly {sorted(required)}")
        if obj["format"] != FORMAT:
            raise ValueError("unsupported composite claim format")
        if not isinstance(obj["id"], str) or not obj["id"] or len(obj["id"]) > 128:
            raise ValueError("bounded non-empty composite id required")
        leaves = obj["leaf_ids"]
        if not isinstance(leaves, list) or len(leaves) > MAX_LEAVES:
            raise ValueError("bounded leaf_ids list required")
        if any(not isinstance(x, str) or not x or len(x) > 128 for x in leaves):
            raise ValueError("leaf ids must be bounded non-empty strings")
        if len(set(leaves)) != len(leaves):
            raise ValueError("duplicate leaf ids are rejected")
        return cls(
            id=obj["id"],
            required_level=parse_level(obj["required_level"]),
            leaf_ids=tuple(leaves),
        )


def _index_atoms(atoms: Sequence[EvidenceAtom]) -> dict[str, EvidenceAtom]:
    if len(atoms) > MAX_ATOMS:
        raise ValueError("too many evidence atoms")
    index: dict[str, EvidenceAtom] = {}
    for atom in atoms:
        if atom.id in index:
            raise ValueError(f"duplicate atom id: {atom.id}")
        index[atom.id] = atom
    return index


def leaves_ok(atoms: Sequence[EvidenceAtom], claim: CompositeClaim) -> bool:
    index = _index_atoms(atoms)
    for leaf_id in claim.leaf_ids:
        atom = index.get(leaf_id)
        if atom is None:
            return False
        if not atom.supported:
            return False
        if not claim.required_level.le(atom.level):
            return False
    return True


def achieved_level(atoms: Sequence[EvidenceAtom], claim: CompositeClaim) -> Level:
    if not claim.leaf_ids:
        return Level.OPEN
    index = _index_atoms(atoms)
    levels: list[Level] = []
    for leaf_id in claim.leaf_ids:
        atom = index.get(leaf_id)
        levels.append(atom.level if atom is not None else Level.OPEN)
    return meet_list(levels)


def accept(atoms: Sequence[EvidenceAtom], claim: CompositeClaim) -> bool:
    if not claim.leaf_ids:
        return False
    if not leaves_ok(atoms, claim):
        return False
    return claim.required_level.le(achieved_level(atoms, claim))


def compose_receipt(
    atoms: Iterable[EvidenceAtom],
    claim: CompositeClaim,
    *,
    predictive_statuses: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    """Independently evaluate a composite and emit a deterministic receipt."""
    atom_list = list(atoms)
    ok = accept(atom_list, claim)
    level = achieved_level(atom_list, claim)
    reasons: list[str] = []
    if not claim.leaf_ids:
        reasons.append("empty_leaves")
    elif not leaves_ok(atom_list, claim):
        index = {a.id: a for a in atom_list}
        for leaf_id in claim.leaf_ids:
            atom = index.get(leaf_id)
            if atom is None:
                reasons.append(f"missing_leaf:{leaf_id}")
            elif not atom.supported:
                reasons.append(f"unsupported_leaf:{leaf_id}")
            elif not claim.required_level.le(atom.level):
                reasons.append(
                    f"underleveled_leaf:{leaf_id}:{atom.level.value}<{claim.required_level.value}"
                )
    elif not claim.required_level.le(level):
        reasons.append(
            f"achieved_below_required:{level.value}<{claim.required_level.value}"
        )
    if ok and level.at_most_empirical() and claim.required_level == Level.FORMAL:
        # Defensive: accept() already rejects this; surface the law explicitly.
        reasons.append("no_empirical_promotion")
        ok = False
    receipt: dict[str, Any] = {
        "format": "heck-compose-receipt-v1",
        "accepted": ok,
        "achieved_level": level.value,
        "required_level": claim.required_level.value,
        "claim": claim.to_dict(),
        "atoms": [a.to_dict() for a in atom_list],
        "rejection_reasons": reasons,
        "law": {
            "composite_is_meet": True,
            "no_empirical_promotion_to_formal": True,
            "empty_rejects": True,
        },
    }
    if predictive_statuses is not None:
        receipt["predictive_statuses"] = dict(predictive_statuses)
    return receipt
