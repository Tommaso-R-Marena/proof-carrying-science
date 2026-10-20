"""Operator bootstrap from an externally reviewed scientific qualification.

Absolute paths are deliberately part of the historical checker identity. This
does not authorize remapping an old history to a different unchecked profile.
"""
from pathlib import Path
import argparse
from dataclasses import asdict
import json

from research.scientific_receiver_v1.full_profile import digest
from research.scientific_receiver_v1.host import OperatorConfig, Pin

ROOT = Path(__file__).resolve().parents[2]


def qualified_config(qualification: Path, expected_sha256: str) -> OperatorConfig:
    qualification = Path(qualification)
    if digest(qualification / "qualification.json") != expected_sha256:
        raise ValueError("Qualification does not match operator-reviewed SHA256")
    q = json.loads((qualification / "qualification.json").read_bytes())
    if (digest(qualification / "module-artifacts.json") != q["module_artifacts_sha256"]
            or digest(qualification / "environment.json") != q["environment_sha256"]):
        raise ValueError("Qualified module/environment inventory changed")
    command = tuple(q["command"])
    if len(command) != 3 or command[1] != "--run":
        raise ValueError("Exact reviewed Lean --run entry point required")
    source_root = Path(command[2]).parents[3]
    sources = {}
    for relative, expected in q["source_sha256"].items():
        actual = source_root / relative
        if digest(actual) != expected or digest(ROOT / relative) != expected:
            raise ValueError("Qualified and selected source bytes differ: " + relative)
        sources[str(actual)] = expected
    if str(Path(command[2])) not in sources:
        raise ValueError("Qualified entry point absent from source inventory")
    # Pin the Python authority paths actually imported in this checkout too.
    for namespace in ("scientific_receiver_v1", "scientific_history_v1",
                      "authorization_history_v1", "scientific_history_v2",
                      "scientific_witness_v1", "scientific_authority_v2"):
        for path in (ROOT / "research" / namespace).glob("*.py"):
            sources[str(path.resolve())] = digest(path)
    manifest = json.loads((qualification / "module-artifacts.json").read_bytes())
    dependencies = {e["path"]: e["sha256"] for e in manifest["artifacts"]}
    if sources.keys() & dependencies.keys():
        raise ValueError("Ambiguous source/dependency inventory")
    pins = tuple(Pin(kind, path, sha) for kind, inventory in
                 (("source", sources), ("dependency", dependencies))
                 for path, sha in sorted(inventory.items()))
    environment = json.loads((qualification / "environment.json").read_bytes())
    return OperatorConfig(command, q["lean_sha256"], pins, q["cwd"],
                          tuple(sorted(environment.items())), q["lean_version"],
                          timeout_seconds=60)


def write_config(config, path):
    item = asdict(config)
    item["environment"] = dict(config.environment)
    with Path(path).open("x") as stream:
        json.dump(item, stream, sort_keys=True, indent=2)
        stream.write("\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--qualification", type=Path, required=True)
    parser.add_argument("--qualification-sha256", required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    write_config(qualified_config(args.qualification, args.qualification_sha256), args.out)


if __name__ == "__main__":
    main()
