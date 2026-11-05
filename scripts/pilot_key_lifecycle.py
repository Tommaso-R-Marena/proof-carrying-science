from __future__ import annotations

import argparse
import json
import sys

from pcs.key_lifecycle import (
    CUSTODY_MODES,
    RECOVERY_CONTROLS,
    REVOCATION_SCOPES,
    KeyLifecycleError,
    assess_signer_file,
    register_active_key,
    revoke_key,
    rotate_key,
    write_new_registry,
)


def _print(value: object) -> None:
    print(json.dumps(value, indent=2, sort_keys=True))


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Manage the public lifecycle record for PCS pilot signing keys. "
            "Private key material is never stored in the registry."
        )
    )
    sub = parser.add_subparsers(dest="command", required=True)

    init = sub.add_parser("init")
    init.add_argument("--registry", required=True)
    init.add_argument("--registry-id", required=True)

    register = sub.add_parser("register")
    register.add_argument("--registry", required=True)
    register.add_argument("--public-key", required=True)
    register.add_argument("--key-id", required=True)
    register.add_argument("--custody-mode", choices=sorted(CUSTODY_MODES), required=True)
    register.add_argument(
        "--recovery-control",
        choices=sorted(RECOVERY_CONTROLS),
        required=True,
    )
    register.add_argument("--activated-at")
    register.add_argument("--notes", default="")

    rotate = sub.add_parser("rotate")
    rotate.add_argument("--registry", required=True)
    rotate.add_argument("--old-fingerprint", required=True)
    rotate.add_argument("--new-public-key", required=True)
    rotate.add_argument("--new-key-id", required=True)
    rotate.add_argument("--custody-mode", choices=sorted(CUSTODY_MODES), required=True)
    rotate.add_argument(
        "--recovery-control",
        choices=sorted(RECOVERY_CONTROLS),
        required=True,
    )
    rotate.add_argument("--effective-at")
    rotate.add_argument("--notes", default="")

    revoke = sub.add_parser("revoke")
    revoke.add_argument("--registry", required=True)
    revoke.add_argument("--fingerprint", required=True)
    revoke.add_argument("--reason", required=True)
    revoke.add_argument(
        "--scope",
        choices=sorted(REVOCATION_SCOPES),
        default="all_signatures",
    )
    revoke.add_argument("--effective-at")

    status = sub.add_parser("status")
    status.add_argument("--registry", required=True)
    status.add_argument("--fingerprint", required=True)
    status.add_argument("--signed-at", required=True)

    args = parser.parse_args()
    try:
        if args.command == "init":
            result = write_new_registry(args.registry, args.registry_id)
        elif args.command == "register":
            result = register_active_key(
                args.registry,
                args.public_key,
                key_id=args.key_id,
                custody_mode=args.custody_mode,
                recovery_control=args.recovery_control,
                activated_at=args.activated_at,
                notes=args.notes,
            )
        elif args.command == "rotate":
            result = rotate_key(
                args.registry,
                old_fingerprint=args.old_fingerprint,
                new_public_key_path=args.new_public_key,
                new_key_id=args.new_key_id,
                custody_mode=args.custody_mode,
                recovery_control=args.recovery_control,
                effective_at=args.effective_at,
                notes=args.notes,
            )
        elif args.command == "revoke":
            result = revoke_key(
                args.registry,
                fingerprint=args.fingerprint,
                reason=args.reason,
                scope=args.scope,
                effective_at=args.effective_at,
            )
        else:
            result = assess_signer_file(
                args.registry,
                args.fingerprint,
                signed_at=args.signed_at,
            )
    except (OSError, KeyLifecycleError) as exc:
        print(f"ERROR: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2

    _print(result)
    return 0 if result.get("valid", True) else 1


if __name__ == "__main__":
    raise SystemExit(main())
