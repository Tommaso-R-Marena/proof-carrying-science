from __future__ import annotations

import argparse
import json
from pathlib import Path


def _rows(root: Path, subdir: str) -> list[dict]:
    base = root / subdir
    return [
        json.loads(path.read_text(encoding="utf-8"))
        for path in sorted(base.rglob("summary.json"))
    ]


def check_python(root: Path, assertion: str) -> bool:
    rows = _rows(root, "python-results")
    if assertion == "rows_present":
        return len(rows) >= 2
    if len(rows) < 2:
        return False
    if assertion == "valid":
        return all(row.get("valid") is True for row in rows)
    if assertion == "contract":
        return all(row.get("environment_contract_match") is True for row in rows)
    if assertion == "determinism":
        return all(
            row.get("determinism_confirmed") is True
            and row.get("determinism_runs_completed") == 3
            for row in rows
        )
    if assertion == "version":
        return all(
            row.get("realized_package_version") == row.get("expected_package_version")
            for row in rows
        )
    if assertion == "native":
        return all(len(row.get("native_extension_hashes", [])) >= 1 for row in rows)
    if assertion == "output":
        return all(row.get("output_matches_producer") is True for row in rows)
    raise ValueError(assertion)


def check_r(root: Path, assertion: str) -> bool:
    rows = _rows(root, "r-results")
    if assertion == "rows_present":
        return len(rows) >= 2
    if len(rows) < 2:
        return False
    if assertion == "valid":
        return all(row.get("valid") is True for row in rows)
    if assertion == "contract":
        return all(row.get("environment_contract_match") is True for row in rows)
    if assertion == "determinism":
        return all(
            row.get("determinism_confirmed") is True
            and row.get("determinism_runs_completed") == 3
            for row in rows
        )
    if assertion == "version":
        return all(
            row.get("realized_digest_version") == row.get("expected_digest_version")
            for row in rows
        )
    if assertion == "artifacts":
        return all(
            isinstance(row.get("restoration_artifacts_signed"), int)
            and row["restoration_artifacts_signed"] >= 3
            for row in rows
        )
    if assertion == "rversion":
        return all(
            row.get("realized_r_version") == row.get("expected_r_version")
            for row in rows
        )
    if assertion == "output":
        return all(row.get("output_matches_producer") is True for row in rows)
    raise ValueError(assertion)



def check_determinism_component(root: Path, campaign: str, component: str) -> bool:
    rows = _rows(root, "python-results" if campaign == "python" else "r-results")
    if len(rows) < 2:
        return False
    for row in rows:
        det = row.get("determinism")
        if not isinstance(det, dict):
            return False
        runs = det.get("runs")
        if not isinstance(runs, list) or len(runs) != 3:
            return False
        if component == "child_valid":
            if not all(run.get("valid") is True for run in runs):
                return False
        elif component == "container_digest":
            values = [run.get("container_image_digest") for run in runs]
            if len(set(values)) != 1:
                return False
        elif component == "dependency_tree":
            values = [run.get("dependency_tree_sha256") for run in runs]
            if len(set(values)) != 1:
                return False
        elif component == "realized_environment":
            values = [run.get("realized_environment_semantic_sha256") for run in runs]
            if len(set(values)) != 1:
                return False
        elif component == "projection":
            values = [run.get("projection_sha256") for run in runs]
            if len(set(values)) != 1:
                return False
        else:
            raise ValueError(component)
    return True

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", required=True)
    parser.add_argument("--campaign", choices=["python", "r"], required=True)
    parser.add_argument("--assertion", required=True)
    parser.add_argument("--determinism-component", choices=["child_valid","container_digest","dependency_tree","realized_environment","projection"])
    args = parser.parse_args()
    root = Path(args.root)
    rows = _rows(root, "python-results" if args.campaign == "python" else "r-results")
    if args.determinism_component:
        ok = check_determinism_component(root, args.campaign, args.determinism_component)
    else:
        ok = (
            check_python(root, args.assertion)
            if args.campaign == "python"
            else check_r(root, args.assertion)
        )
    print(json.dumps({
        "campaign": args.campaign,
        "assertion": args.assertion,
        "determinism_component": args.determinism_component,
        "ok": ok,
        "rows": rows,
    }, indent=2, sort_keys=True))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
