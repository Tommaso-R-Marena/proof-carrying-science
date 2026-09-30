from __future__ import annotations

import argparse
import json
import tempfile
from pathlib import Path

from cross_machine_oci_campaign import aggregate


GROUPS = {
    "core": [
        "at_least_two_independent_machines",
        "amd64_and_arm64_observed",
        "baseline_valid_on_every_machine",
        "baseline_cross_machine_byte_identical",
        "baseline_realized_environment_differs_across_architecture",
    ],
    "locks": [
        "range_lock_valid_on_every_machine",
        "range_lock_output_byte_identical",
        "impossible_exact_lock_rejected_on_every_machine",
    ],
    "variants": [
        "container_os_variant_valid_on_every_machine",
        "container_os_variant_output_byte_identical",
        "container_os_variant_changes_image_identity",
        "provenance_variant_valid_on_every_machine",
        "provenance_variant_output_byte_identical",
        "provenance_variant_changes_image_identity",
    ],
    "attacks": [
        "reviewer_supplied_image_substitution_rejected",
        "missing_signed_base_refuses_registry_pull",
    ],
}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--group", choices=sorted(GROUPS), required=True)
    args = parser.parse_args()

    with tempfile.TemporaryDirectory(prefix="pcs-cross-machine-check-") as tmp:
        summary_path = Path(tmp) / "summary.json"
        value = aggregate(Path(args.input).resolve(), summary_path)

    selected = {
        key: value.get("assertions", {}).get(key)
        for key in GROUPS[args.group]
    }
    print(json.dumps({
        "group": args.group,
        "machine_count": value.get("machine_count"),
        "architectures": value.get("architectures"),
        "assertions": selected,
    }, indent=2, sort_keys=True))
    return 0 if all(selected.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
