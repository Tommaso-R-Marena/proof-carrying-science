"""Exact finite-domain reference; the Lean CLI, not Python, is the authority."""
from __future__ import annotations

from dataclasses import dataclass, asdict
import hashlib
import json
from pathlib import Path
import subprocess

DOMAIN = tuple(range(-3, 4))
BOUND = 32
POLICY_VERSION = "pcs-pgsi-v1/finite-7/relu-target-v1"

def target(x: int) -> int:
    return max(0, 2*x + 1)

def canonical(data: object) -> bytes:
    return json.dumps(data, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("ascii")

def digest(data: object) -> str:
    return hashlib.sha256(b"PCS-PGSI-v1\0" + canonical(data)).hexdigest()

POLICY = {"version": POLICY_VERSION, "domain": DOMAIN,
          "targets": [target(x) for x in DOMAIN], "bound": BOUND,
          "requirements": ["no_correctness_regression", "new_correct_case", "strict_loss_decrease"]}
POLICY_HASH = digest(POLICY)

@dataclass(frozen=True)
class Model:
    relu: bool
    weight: int
    bias: int

    def __post_init__(self) -> None:
        if type(self.relu) is not bool:
            raise TypeError("relu must be bool")
        for field in ("weight", "bias"):
            value = getattr(self, field)
            if type(value) is not int or not -BOUND <= value <= BOUND:
                raise ValueError(f"{field} out of bounds or invalid")

    def predict(self, x: int) -> int:
        z = self.weight*x + self.bias
        return max(0, z) if self.relu else z

def loss(model: Model) -> int:
    return sum(abs(model.predict(x) - target(x)) for x in DOMAIN)

def solved(model: Model) -> frozenset[int]:
    return frozenset(x for x in DOMAIN if model.predict(x) == target(x))

@dataclass(frozen=True)
class Decision:
    accepted: bool
    reason: str
    old_loss: int
    new_loss: int
    old_solved: tuple[int, ...]
    new_solved: tuple[int, ...]
    gained: tuple[int, ...]

def check(old: Model, candidate: Model) -> Decision:
    a, b = solved(old), solved(candidate)
    old_loss, new_loss = loss(old), loss(candidate)
    if not a <= b:
        reason = "REJECT:certified_capability_regression"
    elif not b - a:
        reason = "REJECT:no_new_certified_capability"
    elif not new_loss < old_loss:
        reason = "REJECT:loss_not_strictly_lower"
    else:
        reason = "ACCEPT:reference_only"
    return Decision(reason.startswith("ACCEPT"), reason, old_loss, new_loss,
                    tuple(sorted(a)), tuple(sorted(b)), tuple(sorted(b-a)))

def parse_model(value: object) -> Model:
    if not isinstance(value, dict) or set(value) != {"relu", "weight", "bias"}:
        raise ValueError("model must contain exactly relu, weight, bias")
    return Model(**value)

def request(old: Model, candidate: Model) -> dict:
    return {"policy_hash": POLICY_HASH, "old": asdict(old), "candidate": asdict(candidate)}

def check_request(value: object, active: Model) -> Decision:
    if not isinstance(value, dict) or set(value) != {"policy_hash", "old", "candidate"}:
        raise ValueError("noncanonical request fields")
    if value["policy_hash"] != POLICY_HASH:
        raise ValueError("policy hash mismatch")
    old = parse_model(value["old"])
    if old != active:
        raise ValueError("stale or substituted incumbent")
    return check(old, parse_model(value["candidate"]))

def check_with_lean(old: Model, candidate: Model, formal_dir: Path) -> bool:
    """Fail-closed invocation; host/Lean source integrity must be enforced separately."""
    def fields(model: Model) -> list[str]:
        return ["relu" if model.relu else "linear", str(model.weight), str(model.bias)]
    try:
        result = subprocess.run(
            ["lake", "env", "lean", "--run", "PCS/V2/ProofGatedSelfImprovement.lean",
             *fields(old), *fields(candidate)],
            cwd=formal_dir, capture_output=True, text=True, timeout=120, check=False)
    except (OSError, subprocess.TimeoutExpired):
        return False
    return result.returncode == 0 and result.stdout.strip() == "ACCEPT"

def demonstration() -> dict:
    incumbent = Model(True, 0, 0)
    start = incumbent
    events = []
    for candidate in (Model(True, 0, 0), Model(True, 1, 2),
                      Model(True, 1, 1), Model(True, 2, 1)):
        verdict = check(incumbent, candidate)
        events.append({"old": asdict(incumbent), "candidate": asdict(candidate),
                       "verdict": asdict(verdict),
                       "request_hash": digest(request(incumbent, candidate))})
        if verdict.accepted:
            incumbent = candidate
    return {"scope": "reference-only: no deployed neural model and no kernel verdict",
            "policy_hash": POLICY_HASH, "start": asdict(start),
            "final": asdict(incumbent), "events": events}

if __name__ == "__main__":
    print(json.dumps(demonstration(), indent=2, sort_keys=True))
