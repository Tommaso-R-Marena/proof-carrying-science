"""Independent receiving process for mass-action conservation certificates.

The receiver rebuilds stoichiometry from the contract, discovers/checks
conservation laws, optionally replays an Euler trajectory as stoichiometric
fires, and emits independently checkable certificates. Producer Lean source is
never executed.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from pcca.certificate.checker import (
    build_conservation_certificate,
    check_certificate,
)
from pcca.stoich.matrix import (
    discover_conservation_laws,
    elemental_laws,
    from_mass_action_contract,
    orders_from_contract,
    pool,
    simulate_euler_mass_action,
    fire,
    _rat_text,
)


@dataclass
class ReceiveReport:
    accepted: bool
    reasons: List[str]
    certificates: List[dict] = field(default_factory=list)
    laws: List[dict] = field(default_factory=list)
    trajectory_pools: Dict[str, Any] = field(default_factory=dict)
    pcs_authority: bool = False
    scientific_acceptance: bool = False

    def to_json(self) -> dict:
        return {
            "accepted": self.accepted,
            "reasons": self.reasons,
            "laws": self.laws,
            "trajectory_pools": self.trajectory_pools,
            "certificates": self.certificates,
            "pcs_authority": False,
            "scientific_acceptance": False,
        }


def receive_contract(
    contract: dict,
    *,
    replay_trajectory: bool = True,
    require_elemental: bool = True,
) -> ReceiveReport:
    try:
        network = from_mass_action_contract(contract)
    except (KeyError, ValueError, TypeError) as exc:
        return ReceiveReport(False, [f"contract rejected: {exc}"])

    elemental = elemental_laws(network)
    discovered = discover_conservation_laws(network)
    # Prefer elemental names; drop discovered duplicates that are scalar multiples.
    laws = list(elemental)
    for law in discovered:
        if not any(_parallel(law.weights, e.weights) for e in laws):
            laws.append(law)

    if require_elemental and network.formulas and any(network.formulas) and not elemental:
        return ReceiveReport(
            False,
            ["formulas present but no elemental conservation law verified"],
            laws=[law.as_dict(network.species) for law in laws],
        )

    certificates: List[dict] = []
    reasons: List[str] = []
    for law in laws:
        cert = build_conservation_certificate(
            network, law.name, law.weights, kind="conservation_law"
        )
        result = check_certificate(cert)
        if not result.accepted:
            return ReceiveReport(
                False,
                [f"self-check failed for {law.name}: {result.reasons}"],
                laws=[law.as_dict(network.species) for law in laws],
            )
        certificates.append(cert)
        reasons.append(f"verified conservation law {law.name} ({law.kind})")

    trajectory_pools: Dict[str, str] = {}
    if replay_trajectory and "rate_constant" in contract["reactions"][0]:
        rates, orders, initial, dt, steps = orders_from_contract(contract, network)
        traj = simulate_euler_mass_action(network, rates, orders, initial, dt, steps)
        # Reconstruct firing vectors used by Euler (receiver-owned).
        xis = []
        for k in range(steps):
            state = traj[k]
            xi = []
            for r in range(network.n_reactions):
                rate = rates[r]
                for s_idx, coeff in orders[r]:
                    rate *= state[s_idx] ** coeff
                xi.append(dt * rate)
            xis.append(tuple(xi))
            # Sanity: fire matches next state
            if fire(network, xis[-1], state) != traj[k + 1]:
                return ReceiveReport(
                    False,
                    [f"internal Euler/fire mismatch at step {k}"],
                    laws=[law.as_dict(network.species) for law in laws],
                    certificates=certificates,
                )
        for law in laws:
            pools = [pool(law.weights, st) for st in traj]
            if any(p != pools[0] for p in pools):
                # Emit refutation certificate for the broken claim.
                ref = build_conservation_certificate(
                    network, law.name, law.weights, kind="conservation_refutation"
                )
                certificates.append(ref)
                return ReceiveReport(
                    False,
                    [f"trajectory broke conservation law {law.name}"],
                    laws=[law.as_dict(network.species) for law in laws],
                    certificates=certificates,
                    trajectory_pools={law.name: [_rat_text(p) for p in pools]},
                )
            trajectory_pools[law.name] = _rat_text(pools[0])
            tcert = build_conservation_certificate(
                network,
                law.name,
                law.weights,
                kind="trajectory_conservation",
                states=traj,
                xis=xis,
                expected_pool=pools[0],
            )
            tresult = check_certificate(tcert)
            if not tresult.accepted:
                return ReceiveReport(
                    False,
                    [f"trajectory certificate rejected for {law.name}: {tresult.reasons}"],
                    laws=[law.as_dict(network.species) for law in laws],
                    certificates=certificates,
                )
            certificates.append(tcert)
            reasons.append(
                f"verified trajectory conservation for {law.name} over {steps} steps"
            )

    if not laws:
        return ReceiveReport(
            False,
            ["no conservation laws discovered or verified"],
            certificates=certificates,
        )

    return ReceiveReport(
        True,
        reasons,
        certificates=certificates,
        laws=[law.as_dict(network.species) for law in laws],
        trajectory_pools=trajectory_pools,
    )


def _parallel(a, b) -> bool:
    """True if a and b are scalar multiples (including zeros)."""
    scale = None
    for x, y in zip(a, b):
        if x == 0 and y == 0:
            continue
        if x == 0 or y == 0:
            return False
        s = x / y
        if scale is None:
            scale = s
        elif s != scale:
            return False
    return True


def receive_path(contract_path: Path, output_dir: Optional[Path] = None) -> ReceiveReport:
    contract = json.loads(Path(contract_path).read_text(encoding="utf-8"))
    report = receive_contract(contract)
    if output_dir is not None:
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / "receive-report.json").write_text(
            json.dumps(report.to_json(), indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        for i, cert in enumerate(report.certificates):
            name = cert.get("claim", {}).get("name", f"cert{i}")
            kind = cert.get("kind", "unknown")
            (output_dir / f"{kind}-{name}.json").write_text(
                json.dumps(cert, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
    return report
