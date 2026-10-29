"""PCCA command-line interface."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from pcca import __version__
from pcca.certificate.checker import check_certificate
from pcca.receiver.replay import receive_path
from pcca.stoich.matrix import (
    discover_conservation_laws,
    elemental_laws,
    from_mass_action_contract,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="pcca",
        description="Proof-Carrying Conservation Algebra — independent stoichiometric certificates",
    )
    parser.add_argument("--version", action="version", version=f"pcca {__version__}")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_disc = sub.add_parser("discover", help="Discover conservation laws from a contract")
    p_disc.add_argument("contract", type=Path)

    p_recv = sub.add_parser("receive", help="Independently receive and certify a contract")
    p_recv.add_argument("contract", type=Path)
    p_recv.add_argument("-o", "--output", type=Path, default=None)

    p_ver = sub.add_parser("verify", help="Verify a PCCA certificate")
    p_ver.add_argument("certificate", type=Path)

    p_exp = sub.add_parser("explain", help="Human-readable explanation of a certificate")
    p_exp.add_argument("certificate", type=Path)

    args = parser.parse_args(argv)

    if args.cmd == "discover":
        contract = json.loads(args.contract.read_text(encoding="utf-8"))
        network = from_mass_action_contract(contract)
        elemental = [law.as_dict(network.species) for law in elemental_laws(network)]
        discovered = [law.as_dict(network.species) for law in discover_conservation_laws(network)]
        print(json.dumps({"elemental": elemental, "discovered": discovered}, indent=2))
        return 0

    if args.cmd == "receive":
        report = receive_path(args.contract, args.output)
        print(json.dumps(report.to_json(), indent=2, sort_keys=True))
        return 0 if report.accepted else 1

    if args.cmd == "verify":
        cert = json.loads(args.certificate.read_text(encoding="utf-8"))
        result = check_certificate(cert)
        print(json.dumps(result.to_json(), indent=2, sort_keys=True))
        return 0 if result.accepted else 1

    if args.cmd == "explain":
        cert = json.loads(args.certificate.read_text(encoding="utf-8"))
        result = check_certificate(cert)
        print(f"format: {cert.get('format')}")
        print(f"kind:   {cert.get('kind')}")
        print(f"name:   {cert.get('claim', {}).get('name')}")
        print(f"check:  {'ACCEPT' if result.accepted else 'REJECT'}")
        for reason in result.reasons:
            print(f"  - {reason}")
        for lim in cert.get("limitations", []):
            print(f"limit:  {lim}")
        print("authority: pcs_authority=false scientific_acceptance=false")
        return 0 if result.accepted else 1

    return 2


if __name__ == "__main__":
    sys.exit(main())
