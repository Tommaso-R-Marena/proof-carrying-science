from __future__ import annotations

import argparse
import json
import sys

from pcs.pilot_closeout import (
    PilotCloseoutError,
    apply_closeout_plan,
    build_closeout_plan,
    load_closeout_plan,
    write_closeout_plan,
    write_closeout_receipt,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Plan and apply an exact, hash-bound PCS pilot retention/deletion closeout."
        )
    )
    sub = parser.add_subparsers(dest="command", required=True)

    plan = sub.add_parser("plan")
    plan.add_argument("--workspace", required=True)
    plan.add_argument("--pilot-id", required=True)
    plan.add_argument("--retain", action="append", default=[])
    plan.add_argument("--delete", action="append", default=[])
    plan.add_argument("-o", "--output", required=True)
    plan.add_argument("--force", action="store_true")

    apply = sub.add_parser("apply")
    apply.add_argument("--workspace", required=True)
    apply.add_argument("--plan", required=True)
    apply.add_argument("--confirm-plan-sha256", required=True)
    apply.add_argument("-o", "--receipt", required=True)
    apply.add_argument("--applied-at")
    apply.add_argument("--force", action="store_true")

    args = parser.parse_args()
    try:
        if args.command == "plan":
            value = build_closeout_plan(
                args.workspace,
                pilot_id=args.pilot_id,
                retain_paths=args.retain,
                delete_paths=args.delete,
            )
            written = write_closeout_plan(
                args.output,
                value,
                overwrite=args.force,
            )
            result = {
                "plan": str(written),
                "pilot_id": value["pilot_id"],
                "plan_sha256": value["plan_sha256"],
                "retain_count": sum(
                    entry["action"] == "RETAIN" for entry in value["entries"]
                ),
                "delete_count": sum(
                    entry["action"] == "DELETE" for entry in value["entries"]
                ),
                "next": (
                    "Review the exact path/hash inventory, then run apply with "
                    "--confirm-plan-sha256 equal to this plan_sha256."
                ),
            }
        else:
            plan_value = load_closeout_plan(args.plan)
            receipt = apply_closeout_plan(
                args.workspace,
                plan_value,
                confirm_plan_sha256=args.confirm_plan_sha256,
                applied_at=args.applied_at,
            )
            written = write_closeout_receipt(
                args.receipt,
                receipt,
                overwrite=args.force,
            )
            result = {
                "receipt": str(written),
                "pilot_id": receipt["pilot_id"],
                "plan_sha256": receipt["plan_sha256"],
                "receipt_sha256": receipt["receipt_sha256"],
                "deleted_count": len(receipt["deleted"]),
                "retained_count": len(receipt["retained"]),
            }
    except (OSError, PilotCloseoutError) as exc:
        print(f"ERROR: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2

    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
