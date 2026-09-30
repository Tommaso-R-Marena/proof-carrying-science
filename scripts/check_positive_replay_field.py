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


def load_rows(root: Path):
    rows = []
    for machine_dir in sorted(root.iterdir()):
        if not machine_dir.is_dir():
            continue
        for variant in POSITIVE_VARIANTS:
            path = machine_dir / variant / "summary.json"
            if not path.is_file():
                raise RuntimeError(f"missing summary: {path}")
            rows.append((machine_dir.name, variant, json.loads(path.read_text())))
    return rows


def check(row: dict, mode: str) -> bool:
    verdict = row.get("verdict") or {}
    comparison = row.get("environment_comparison") or {}
    result = row.get("execution_result") or {}

    if mode == "environment-contract":
        return result.get("environment_contract_match") is True
    if mode == "determinism":
        return result.get("determinism_confirmed") is True
    if mode == "nodes":
        return verdict.get("all_nodes_exited_zero") is True
    if mode == "outputs":
        return verdict.get("all_signed_outputs_reproduced_exactly") is True
    if mode == "non-output-integrity":
        return verdict.get("signed_non_outputs_unchanged") is True
    if mode == "namespace":
        return verdict.get("exact_output_namespace_satisfied") is True
    if mode == "symlinks":
        return verdict.get("filesystem_contains_no_symlinks") is True
    if mode == "container-binding":
        return (comparison.get("container") or {}).get("status") in {
            "derived_from_signed_contract",
            "image_digest_matches_signed_reference",
        }
    if mode == "interpreter":
        rows = comparison.get("interpreter_constraints") or []
        return all(x.get("status") == "match" for x in rows)
    if mode == "exact-packages":
        rows = comparison.get("signed_exact_packages") or []
        return all(x.get("status") == "match" for x in rows)
    if mode == "loose-packages":
        rows = comparison.get("signed_non_exact_dependencies") or []
        bad = {"missing", "constraint_mismatch"}
        return all(x.get("status") not in bad for x in rows)
    if mode == "dependency-projection":
        value = comparison.get("signed_dependency_projection_fingerprint") or {}
        return value.get("match") in {True, None}
    raise ValueError(mode)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument(
        "--mode",
        required=True,
        choices=[
            "environment-contract",
            "determinism",
            "nodes",
            "outputs",
            "non-output-integrity",
            "namespace",
            "symlinks",
            "container-binding",
            "interpreter",
            "exact-packages",
            "loose-packages",
            "dependency-projection",
        ],
    )
    args = parser.parse_args()

    rows = load_rows(Path(args.input))
    evidence = []
    ok = True
    for machine, variant, row in rows:
        passed = check(row, args.mode)
        ok = ok and passed
        evidence.append({
            "machine": machine,
            "variant": variant,
            "passed": passed,
            "valid": row.get("valid"),
            "environment_contract_match": (row.get("execution_result") or {}).get(
                "environment_contract_match"
            ),
            "determinism_confirmed": (row.get("execution_result") or {}).get(
                "determinism_confirmed"
            ),
            "verdict": row.get("verdict"),
            "environment_comparison": row.get("environment_comparison"),
        })
    print(json.dumps({"mode": args.mode, "ok": ok, "rows": evidence}, indent=2, sort_keys=True))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
