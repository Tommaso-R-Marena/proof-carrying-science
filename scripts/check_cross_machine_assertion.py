from __future__ import annotations

import argparse
import json
import tempfile
from pathlib import Path

from cross_machine_oci_campaign import aggregate


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--assertion", required=True)
    args = parser.parse_args()

    with tempfile.TemporaryDirectory(prefix="pcs-cross-machine-assertion-") as tmp:
        value = aggregate(
            Path(args.input).resolve(),
            Path(tmp) / "summary.json",
        )

    assertions = value.get("assertions", {})
    if args.assertion not in assertions:
        raise SystemExit(f"unknown assertion: {args.assertion}")
    observed = assertions[args.assertion]
    print(json.dumps({
        "assertion": args.assertion,
        "observed": observed,
        "machine_count": value.get("machine_count"),
        "architectures": value.get("architectures"),
    }, indent=2, sort_keys=True))
    return 0 if observed is True else 1


if __name__ == "__main__":
    raise SystemExit(main())
