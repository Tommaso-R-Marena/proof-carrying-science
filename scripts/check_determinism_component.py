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


def all_equal(values):
    return len(values) > 0 and len(set(values)) == 1


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument(
        "--mode",
        required=True,
        choices=[
            "runs-completed",
            "runs-valid",
            "projection-match",
            "container-digest-stable",
            "dependency-tree-stable",
            "realized-environment-stable",
        ],
    )
    args = parser.parse_args()

    evidence = []
    overall = True
    for machine, variant, row in summaries(Path(args.input)):
        det = row.get("determinism") or {}
        runs = det.get("runs") or []
        if args.mode == "runs-completed":
            passed = det.get("runs_completed") == det.get("runs_requested") == 3
        elif args.mode == "runs-valid":
            passed = len(runs) == 3 and all(x.get("valid") is True for x in runs)
        elif args.mode == "projection-match":
            passed = (
                len(runs) == 3
                and all(x.get("matches_primary_projection") is True for x in runs[1:])
            )
        elif args.mode == "container-digest-stable":
            vals = [x.get("container_image_digest") for x in runs]
            passed = len(runs) == 3 and all_equal(vals)
        elif args.mode == "dependency-tree-stable":
            vals = [x.get("dependency_tree_sha256") for x in runs]
            passed = len(runs) == 3 and all_equal(vals)
        else:
            vals = [x.get("realized_environment_semantic_sha256") for x in runs]
            passed = len(runs) == 3 and all_equal(vals)
        overall = overall and passed
        evidence.append({
            "machine": machine,
            "variant": variant,
            "passed": passed,
            "determinism_status": det.get("status"),
            "runs": runs,
        })

    print(json.dumps({"mode": args.mode, "ok": overall, "evidence": evidence}, indent=2, sort_keys=True))
    return 0 if overall else 1


if __name__ == "__main__":
    raise SystemExit(main())
