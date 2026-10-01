from __future__ import annotations

import argparse
import json
import sys

from .local_verify_v06 import V06LocalVerifyError, verify_local_bundle_v06


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="pcs-verifier-v06",
        description="Independent one-command verifier for delivered PCS v0.6 bundles.",
    )
    parser.add_argument("bundle")
    parser.add_argument("--trust", required=True, help="pcs-verifier-trust-v1 JSON")
    parser.add_argument("--receipt", help="write deterministic verification receipt JSON")
    parser.add_argument("--force-receipt", action="store_true")
    args = parser.parse_args()
    try:
        result = verify_local_bundle_v06(
            args.bundle,
            args.trust,
            receipt=args.receipt,
            overwrite_receipt=args.force_receipt,
        )
    except Exception as exc:
        print(f"ERROR: {type(exc).__name__}: {exc}", file=sys.stderr)
        raise SystemExit(2)
    print(json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False))
    raise SystemExit(0 if result.get("accepted", result.get("valid", False)) else 1)


if __name__ == "__main__":
    main()
