from __future__ import annotations

import argparse
import json
from pathlib import Path


POSITIVE_VARIANTS = (
    "baseline_locked_bookworm",
    "lock_range_bookworm",
    "os_bullseye_locked",
    "provenance_full_bookworm",
)


def summaries(root: Path):
    for machine in sorted(root.iterdir()):
        if not machine.is_dir():
            continue
        for variant in POSITIVE_VARIANTS:
            p = machine / variant / "summary.json"
            if not p.is_file():
                raise RuntimeError(f"missing {p}")
            yield machine.name, variant, json.loads(p.read_text())


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument(
        "--mode",
        required=True,
        choices=[
            "exact-packages",
            "non-exact-dependencies",
            "interpreter-constraints",
            "container-binding",
            "dependency-projection",
            "enforceable-contract",
        ],
    )
    args = parser.parse_args()

    evidence = []
    overall = True
    for machine, variant, row in summaries(Path(args.input)):
        cmp = row.get("environment_comparison") or {}
        if args.mode == "exact-packages":
            rows = cmp.get("signed_exact_packages") or []
            passed = all(x.get("status") == "match" for x in rows)
            detail = rows
        elif args.mode == "non-exact-dependencies":
            rows = cmp.get("signed_non_exact_dependencies") or []
            bad = {"missing", "constraint_mismatch"}
            passed = all(x.get("status") not in bad for x in rows)
            detail = rows
        elif args.mode == "interpreter-constraints":
            rows = cmp.get("interpreter_constraints") or []
            passed = all(x.get("status") == "match" for x in rows)
            detail = rows
        elif args.mode == "container-binding":
            detail = cmp.get("container") or {}
            passed = detail.get("status") in {
                "derived_from_signed_contract",
                "image_digest_matches_signed_reference",
            }
        elif args.mode == "dependency-projection":
            detail = cmp.get("signed_dependency_projection_fingerprint") or {}
            passed = (
                detail.get("match") is True
                if detail.get("enforced") is True
                else True
            )
        else:
            detail = {
                "enforceable_contract_match": cmp.get("enforceable_contract_match"),
                "semantic_sha256": cmp.get("semantic_sha256"),
            }
            passed = cmp.get("enforceable_contract_match") is True
        overall = overall and passed
        evidence.append({
            "machine": machine,
            "variant": variant,
            "passed": passed,
            "detail": detail,
        })

    print(json.dumps({
        "mode": args.mode,
        "ok": overall,
        "evidence": evidence,
    }, indent=2, sort_keys=True))
    return 0 if overall else 1


if __name__ == "__main__":
    raise SystemExit(main())
