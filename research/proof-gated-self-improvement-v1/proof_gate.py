"""Exact finite-domain reference; the Lean CLI, not Python, is the authority."""
from __future__ import annotations

from dataclasses import dataclass, asdict
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile

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

WIRE_MAGIC = "PGSI1"

def wire_bytes(model: Model) -> bytes:
    """Canonical single-string artifact, with no final newline or other fields."""
    activation = "R" if model.relu else "L"
    return f"{WIRE_MAGIC}|{activation}|{model.weight}|{model.bias}".encode("ascii")

def artifact_gate(old_path: Path, candidate_path: Path, formal_dir: Path) -> bool:
    """Pass original artifact paths directly to Lean. The Lean program reads and
    canonicalizes files itself. This is a research-only subprocess transport, NOT
    a secure deployment service or a check on future file contents.
    """
    try:
        result = subprocess.run(
            ["lake", "env", "lean", "--run", "PCS/V2/ProofGatedArtifacts.lean",
             str(old_path.resolve()), str(candidate_path.resolve())],
            cwd=formal_dir, capture_output=True, text=True, timeout=120, check=False)
    except (OSError, subprocess.TimeoutExpired, ValueError):
        return False
    return (result.returncode == 0 and result.stdout == "ACCEPT\\n"
            and result.stderr == "")

def check_with_lean(old: Model, candidate: Model, formal_dir: Path) -> bool:
    """Create exact candidate artifact bytes for independent Lean file checking."""
    with tempfile.TemporaryDirectory(prefix="pcs-pgsi-") as temp:
        original = Path(temp) / "incumbent.pgsi"
        proposed = Path(temp) / "candidate.pgsi"
        original.write_bytes(wire_bytes(old))
        proposed.write_bytes(wire_bytes(candidate))
        return artifact_gate(original, proposed, formal_dir)


def automatic_search(start: Model | None = None, *, max_steps: int = 8,
                     formal_dir: Path | None = None) -> dict:
    """Enumerate proposed weight and activation mutations.

    Python is only a search prefilter. When formal_dir is provided, the Lean
    process authorizes each individual proposed transition; failure stops
    the simulated update chain. This never deploys model artifacts.
    """
    incumbent = start or Model(True, 0, 0)
    trace = []
    for generation in range(max_steps):
        candidates = [Model(k, w, b) for k in (True, False)
                      for w in range(-3, 4) for b in range(-3, 4)]
        candidates.sort(key=lambda m: (
            abs(m.weight - incumbent.weight) + abs(m.bias - incumbent.bias)
            + (m.relu != incumbent.relu),
            m.relu != incumbent.relu,
            abs(m.weight) + abs(m.bias), m.weight, m.bias))
        selected = next(((candidate, d) for candidate in candidates
                         if (d := check(incumbent, candidate)).accepted), None)
        if selected is None:
            break
        candidate, decision = selected
        if formal_dir is not None and not check_with_lean(incumbent, candidate, formal_dir):
            raise RuntimeError("FAIL CLOSED: Lean rejected or was unavailable")
        trace.append({"generation": generation + 1, "old": asdict(incumbent),
                      "candidate": asdict(candidate), "verdict": asdict(decision)})
        incumbent = candidate
    return {"reference_only": formal_dir is None, "generation_count": len(trace),
            "final": asdict(incumbent), "trace": trace}

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
