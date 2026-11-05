"""Independent HECK receiving verifier for package directories."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .canonical import canonicalize, digest_obj, sha256_hex
from .compose import CompositeClaim, EvidenceAtom, compose_receipt
from .predictive import PredStatus, PredictiveObligation, discharge_sticky, observe_against_prediction
from .theory_ir import TheoryObject, evaluate_theory

MAX_FILE_BYTES = 1_048_576


def _read_json(path: Path) -> Any:
    raw = path.read_bytes()
    if len(raw) > MAX_FILE_BYTES:
        raise ValueError(f"file too large: {path}")
    return json.loads(raw.decode("utf-8"))


def verify_package(package_dir: Path) -> dict[str, Any]:
    """Verify a HECK package directory.

    Expected layout:
      atoms.json          — list of evidence atoms
      claim.json          — composite claim
      optional theory.json
      optional observations.json  — {obligation_id: observed_payload}
    """
    package_dir = Path(package_dir)
    atoms_raw = _read_json(package_dir / "atoms.json")
    claim_raw = _read_json(package_dir / "claim.json")
    if not isinstance(atoms_raw, list):
        raise ValueError("atoms.json must be a list")
    atoms = [EvidenceAtom.from_dict(a) for a in atoms_raw]
    claim = CompositeClaim.from_dict(claim_raw)
    receipt = compose_receipt(atoms, claim)

    theory_path = package_dir / "theory.json"
    theory_eval = None
    if theory_path.exists():
        theory = TheoryObject.from_dict(_read_json(theory_path))
        obs_path = package_dir / "observations.json"
        if obs_path.exists():
            observations = _read_json(obs_path)
            if not isinstance(observations, dict):
                raise ValueError("observations.json must be an object")
            for obl_id, payload in observations.items():
                if not isinstance(payload, dict):
                    raise ValueError("each observation payload must be an object")
                theory.apply_observation(obl_id, payload)
        theory_eval = evaluate_theory(theory, atoms)

    result = {
        "format": "heck-package-verification-v1",
        "package_dir": str(package_dir),
        "compose_receipt": receipt,
        "theory_evaluation": theory_eval,
        "accepted": receipt["accepted"]
        if theory_eval is None
        else bool(theory_eval.get("scientific_closure")),
        "input_digests": {
            "atoms": digest_obj(atoms_raw),
            "claim": digest_obj(claim_raw),
        },
    }
    result["receipt_sha256"] = sha256_hex(canonicalize(result))
    return result


def verify_predictive_only(
    obligation: PredictiveObligation, observed: dict[str, Any]
) -> dict[str, Any]:
    obs = observe_against_prediction(obligation, observed)
    updated = discharge_sticky(obligation, obs)
    return {
        "format": "heck-predictive-verification-v1",
        "obligation_id": obligation.id,
        "before": obligation.status.value,
        "after": updated.status.value,
        "observation": obs.kind.value,
        "is_support": updated.status is PredStatus.EMPIRICALLY_SUPPORTED,
        "to_level": updated.status.to_level().value,
        "non_claims": ["empirical_support_is_not_formal_proof"],
    }
