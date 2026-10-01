from __future__ import annotations

import argparse
import json
from pathlib import Path

from pcs.lean_authority_v06 import V06LeanAuthorityError
from pcs.verifier_zip_v06 import verify_package_zip_end_to_end_v06


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--source", required=True)
    p.add_argument(
        "--expect",
        choices=["accept", "semantic-reject", "process-exit", "timeout", "other-runtime"],
        required=True,
    )
    args = p.parse_args()

    source = Path(args.source).resolve()
    meta = json.loads((source / "campaign.json").read_text(encoding="utf-8"))
    try:
        result = verify_package_zip_end_to_end_v06(
            source / "study.pcs.zip",
            source / "producer-public.pem",
            expected_fingerprint=meta["producer_public_key_fingerprint"],
        )
    except V06LeanAuthorityError as exc:
        msg = str(exc)
        print(msg)
        if args.expect == "timeout":
            return 0 if ("TimeoutExpired" in msg or "timed out" in msg.lower()) else 1
        if args.expect == "process-exit":
            return 0 if "failed with exit code" in msg else 1
        if args.expect == "other-runtime":
            return 0 if (
                "invocation failed" in msg
                and "TimeoutExpired" not in msg
                and "timed out" not in msg.lower()
            ) else 1
        return 1

    print(json.dumps(result, indent=2, sort_keys=True))
    if args.expect == "accept":
        return 0 if result.get("valid") is True else 1
    if args.expect == "semantic-reject":
        return 0 if (
            result.get("valid") is False
            and result.get("failed_stage") == "lean_authority"
        ) else 1
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
