"""Reviewer CLI: root/config/checkpoint are independent operator trust inputs."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import stat

from research.authorization_history_v1 import history
from research.scientific_receiver_v1.host import OperatorConfig
from .audit import AuditRejected, audit_history, audit_material, canonical


def bounded_file(path: Path, limit: int) -> bytes:
    descriptor = os.open(path, os.O_RDONLY | os.O_NONBLOCK | os.O_NOFOLLOW)
    with os.fdopen(descriptor, "rb") as stream:
        info = os.fstat(stream.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_size > limit:
            raise AuditRejected("Expected bounded regular input file")
        raw = stream.read(limit + 1)
    if len(raw) > limit:
        raise AuditRejected("Input grew beyond byte budget")
    return raw


def _object(raw: bytes, fields: set[str]) -> dict:
    try:
        value = json.loads(raw)
        if type(value) is not dict or set(value) != fields or canonical(value) != raw:
            raise AuditRejected("Noncanonical/unknown input shape")
        return value
    except (ValueError, TypeError, RecursionError, UnicodeError) as exc:
        raise AuditRejected("Invalid bounded canonical input") from exc


def load_root(raw: bytes) -> history.Root:
    fields = {"format", "authority", "witness", "policy", "checker", "genesis_id",
              "genesis_incumbent", "genesis_generation"}
    value = _object(raw, fields)
    if value.pop("format") != "pcs-authorization-root-v1":
        raise AuditRejected("Unsupported root domain")
    try:
        result = history.Root(**{name: bytes.fromhex(v) if name != "genesis_generation" else v
                                 for name, v in value.items()})
    except (TypeError, ValueError) as exc:
        raise AuditRejected("Invalid fixed root") from exc
    if result.encode() != raw:
        raise AuditRejected("Noncanonical root")
    return result


def load_anchor(raw: bytes) -> history.Anchor:
    value = _object(raw, {"generation", "incumbent_hex", "tip_hex", "chain_digest_hex"})
    try:
        anchor = history.Anchor(value["generation"], bytes.fromhex(value["incumbent_hex"]),
                                bytes.fromhex(value["tip_hex"]), bytes.fromhex(value["chain_digest_hex"]))
    except (ValueError, TypeError) as exc:
        raise AuditRejected("Invalid checkpoint") from exc
    if canonical({"generation": anchor.generation, "incumbent_hex": anchor.incumbent.hex(),
                  "tip_hex": anchor.tip.hex(), "chain_digest_hex": anchor.chain_digest.hex()}) != raw:
        raise AuditRejected("Noncanonical checkpoint")
    return anchor


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    inputs = parser.add_mutually_exclusive_group(required=True)
    inputs.add_argument("--history", type=Path)
    inputs.add_argument("--material", type=Path, help="canonical object with exact envelope_hex list")
    parser.add_argument("--root", type=Path, required=True, help="independently retained trusted root")
    parser.add_argument("--anchor", type=Path, required=True, help="independently retained trusted checkpoint")
    parser.add_argument("--operator-config", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True, help="new output path; never overwrite evidence")
    args = parser.parse_args()
    root = load_root(bounded_file(args.root, 32768))
    anchor = load_anchor(bounded_file(args.anchor, 32768))
    config = OperatorConfig.load(args.operator_config)
    if args.history is not None:
        report = audit_history(args.history, root, anchor, config)
    else:
        material = _object(bounded_file(args.material, 2097152), {"envelope_hex"})["envelope_hex"]
        if type(material) is not list or len(material) > 32 or any(type(x) is not str for x in material):
            raise AuditRejected("Bounded envelope list required")
        try:
            wires = tuple(bytes.fromhex(x) for x in material)
        except ValueError as exc:
            raise AuditRejected("Invalid envelope hex") from exc
        if [x.hex() for x in wires] != material:
            raise AuditRejected("Noncanonical envelope hex")
        report = audit_material(root, anchor, wires, config)
    with args.report.open("x", encoding="utf-8") as stream:
        json.dump(report.as_dict(), stream, indent=2, sort_keys=True)
        stream.write("\n")
    print(json.dumps({"retrospective_mathematical_validity": report.retrospective_mathematical_validity,
                      "artifacts_checked": len(report.artifacts),
                      "historically_authenticated_verification": "UNVERIFIED",
                      "scientific_acceptance": False, "production_authority": False}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
