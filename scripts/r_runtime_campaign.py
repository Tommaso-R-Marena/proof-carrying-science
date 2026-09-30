from __future__ import annotations

import argparse
import hashlib
import json
import platform
import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from pcs.attest_v06 import attest_v06
from pcs.discover_v06 import confirm_manifest_draft_v06, discover_project_v06, write_discovery_outputs_v06
from pcs.environment_execute_v06 import execute_prepared_replay_workspace_v06
from pcs.environment_workspace_v06 import prepare_verified_environment_workspace_v06
from pcs.scaffold import init_project
from pcs.signing import generate_keypair

FORMAT = "pcs-r-runtime-boundary-v1"
BASE_TAG = "docker.io/library/r-base:latest"

R_CODE = r'''d <- read.csv("input.csv")
x <- as.numeric(d$x)
y <- as.numeric(d$y)
mx <- mean(x)
my <- mean(y)
slope <- sum((x - mx) * (y - my)) / sum((x - mx)^2)
intercept <- my - slope * mx
pred <- intercept + slope * x
out <- data.frame(
  x = x,
  prediction = sprintf("%.10f", pred),
  residual = sprintf("%.10f", y - pred)
)
write.csv(out, "predictions.csv", row.names=FALSE, quote=FALSE)
'''


def run(argv: list[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
    p = subprocess.run(argv, text=True, capture_output=True)
    if check and p.returncode:
        raise RuntimeError(
            f"command failed ({p.returncode}): {argv!r}\n"
            f"stdout={p.stdout[-6000:]}\nstderr={p.stderr[-6000:]}"
        )
    return p


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def image_index_digest(tag: str) -> str:
    p = run(["docker", "buildx", "imagetools", "inspect", tag])
    m = re.search(r"(?m)^Digest:\s+(sha256:[0-9a-f]{64})\s*$", p.stdout)
    if not m:
        raise RuntimeError(f"could not determine multi-arch digest for {tag}")
    return m.group(1)


def produce(output: Path) -> dict[str, Any]:
    output.mkdir(parents=True, exist_ok=False)
    run(["docker", "pull", BASE_TAG])
    digest = image_index_digest(BASE_TAG)
    image_ref = f"docker.io/library/r-base@{digest}"
    run(["docker", "pull", image_ref])
    rver = run([
        "docker", "run", "--rm", "--network=none", image_ref,
        "Rscript", "--vanilla", "-e", "cat(as.character(getRversion()))",
    ]).stdout.strip()

    project = Path(tempfile.mkdtemp(prefix="pcs-r-runtime-producer-"))
    try:
        init_project(project, template="pkpd", subject="r-runtime-boundary")
        (project / "analysis.R").write_text(R_CODE, encoding="utf-8")
        (project / "input.csv").write_text(
            "x,y\n1,3\n2,5\n3,7\n4,9\n5,11\n",
            encoding="utf-8",
        )
        (project / "DESCRIPTION").write_text(
            "Package: pcsRBoundary\n"
            "Version: 0.0.1\n"
            f"Depends: R (== {rver})\n",
            encoding="utf-8",
        )
        (project / "Dockerfile").write_text(f"FROM {image_ref}\n", encoding="utf-8")

        run([
            "docker", "run", "--rm", "--network=none",
            "-v", f"{project}:/workspace", "-w", "/workspace",
            image_ref, "Rscript", "--vanilla", "analysis.R",
        ])

        report = discover_project_v06(project, minimum_workflow_confidence=0.85)
        draft = project / "pcs-manifest.draft.json"
        write_discovery_outputs_v06(
            report,
            manifest_output=draft,
            report_output=project / "pcs-discovery.json",
            overwrite=True,
        )
        selected = report.get("selected_workflow_inferences", [])
        r_sources = [
            s for s in report.get("workflow_map", {}).get("sources", [])
            if s.get("source_kind") == "r"
        ]
        if not r_sources or not any(s.get("id") in selected for s in r_sources):
            raise RuntimeError("R static workflow inference was not selected")

        manifest = project / "confirmed-manifest.json"
        confirm_manifest_draft_v06(draft, manifest, project_root=project, overwrite=True)
        private = project.parent / "r-runtime-private.pem"
        public = output / "producer-public.pem"
        fingerprint = generate_keypair(private, public)["fingerprint"]
        bundle = output / "study.pcs.zip"
        attested = attest_v06(
            manifest, bundle, private, public, expected_fingerprint=fingerprint
        )
        if attested.get("valid") is not True:
            raise RuntimeError(f"attestation failed: {attested}")

        meta = {
            "format": FORMAT,
            "phase": "producer",
            "image_tag": BASE_TAG,
            "image_ref": image_ref,
            "image_index_digest": digest,
            "r_version": rver,
            "workflow_discovery_threshold": 0.85,
            "r_inference_confidence": r_sources[0].get("confidence"),
            "producer_public_key_fingerprint": fingerprint,
            "bundle_sha256": sha256_file(bundle),
            "expected_predictions_sha256": sha256_file(project / "predictions.csv"),
        }
        write_json(output / "campaign.json", meta)
        return meta
    finally:
        shutil.rmtree(project, ignore_errors=True)
        try:
            private.unlink()
        except Exception:
            pass


def replay(source: Path, output: Path, machine_id: str) -> dict[str, Any]:
    meta = json.loads((source / "campaign.json").read_text(encoding="utf-8"))
    output.mkdir(parents=True, exist_ok=False)
    run(["docker", "pull", meta["image_ref"]])

    workspace = output / "workspace"
    prepared = prepare_verified_environment_workspace_v06(
        source / "study.pcs.zip",
        workspace,
        source / "producer-public.pem",
        expected_fingerprint=meta["producer_public_key_fingerprint"],
    )
    replay_dir = output / "replay"
    result = execute_prepared_replay_workspace_v06(
        workspace,
        replay_dir,
        source / "producer-public.pem",
        expected_fingerprint=meta["producer_public_key_fingerprint"],
        runtime="docker",
        determinism_runs=3,
    )
    receipt = json.loads((replay_dir / "pcs-replay-execution.json").read_text(encoding="utf-8"))
    realized = json.loads((replay_dir / "pcs-realized-environment.json").read_text(encoding="utf-8"))
    predictions = replay_dir / "outputs" / "predictions.csv"
    rinfo = realized.get("r", {})

    summary = {
        "format": FORMAT,
        "phase": "consumer",
        "machine_id": machine_id,
        "host_platform": platform.platform(),
        "host_machine": platform.machine(),
        "prepared_valid": prepared.get("valid"),
        "valid": result.get("valid"),
        "environment_contract_match": result.get("environment_contract_match"),
        "determinism_confirmed": result.get("determinism_confirmed"),
        "determinism_runs_completed": result.get("determinism_runs_completed"),
        "expected_r_version": meta["r_version"],
        "realized_r_version": rinfo.get("version"),
        "r_interpreter_sha256": rinfo.get("executable_sha256"),
        "r_package_count": len(rinfo.get("packages", [])),
        "dependency_tree_sha256": realized.get("dependency_tree_sha256"),
        "realized_environment_semantic_sha256": realized.get("semantic_sha256"),
        "container_image_digest": realized.get("container_image_digest"),
        "expected_predictions_sha256": meta["expected_predictions_sha256"],
        "realized_predictions_sha256": sha256_file(predictions) if predictions.is_file() else None,
        "output_matches_producer": (
            predictions.is_file()
            and sha256_file(predictions) == meta["expected_predictions_sha256"]
        ),
        "verdict": receipt.get("verdict"),
        "environment_comparison": receipt.get("environment_comparison"),
        "determinism": receipt.get("determinism"),
    }
    write_json(output / "summary.json", summary)
    return summary


def aggregate(input_root: Path, output: Path) -> dict[str, Any]:
    rows = []
    for p in sorted(input_root.rglob("summary.json")):
        value = json.loads(p.read_text(encoding="utf-8"))
        if value.get("format") == FORMAT and value.get("phase") == "consumer":
            rows.append(value)
    hashes = {x.get("realized_predictions_sha256") for x in rows if x.get("realized_predictions_sha256")}
    architectures = {str(x.get("host_machine") or "").lower() for x in rows}
    assertions = {
        "at_least_two_r_replay_hosts": len(rows) >= 2,
        "amd64_and_arm64_r_replay_observed": (
            any("x86" in x or x == "amd64" for x in architectures)
            and any("arm" in x or "aarch64" in x for x in architectures)
        ),
        "all_r_replays_valid": bool(rows) and all(x.get("valid") is True for x in rows),
        "all_r_environment_contracts_match": bool(rows) and all(
            x.get("environment_contract_match") is True for x in rows
        ),
        "all_r_replays_three_run_deterministic": bool(rows) and all(
            x.get("determinism_confirmed") is True
            and x.get("determinism_runs_completed") == 3
            for x in rows
        ),
        "realized_r_version_matches_signed_version": bool(rows) and all(
            x.get("realized_r_version") == x.get("expected_r_version") for x in rows
        ),
        "r_interpreter_hash_captured_everywhere": bool(rows) and all(
            isinstance(x.get("r_interpreter_sha256"), str)
            and len(x["r_interpreter_sha256"]) == 64
            for x in rows
        ),
        "r_package_inventory_captured_everywhere": bool(rows) and all(
            isinstance(x.get("r_package_count"), int) and x["r_package_count"] > 0
            for x in rows
        ),
        "scientific_output_byte_identical_across_r_hosts": len(hashes) == 1 and bool(hashes),
        "all_r_outputs_match_signed_producer": bool(rows) and all(
            x.get("output_matches_producer") is True for x in rows
        ),
    }
    value = {
        "format": FORMAT,
        "phase": "aggregate",
        "rows": rows,
        "architectures": sorted(architectures),
        "assertions": assertions,
        "success": all(assertions.values()),
    }
    write_json(output, value)
    return value


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("produce")
    p.add_argument("--output", required=True)
    r = sub.add_parser("replay")
    r.add_argument("--input", required=True)
    r.add_argument("--output", required=True)
    r.add_argument("--machine-id", required=True)
    a = sub.add_parser("aggregate")
    a.add_argument("--input", required=True)
    a.add_argument("--output", required=True)
    args = parser.parse_args()

    if args.command == "produce":
        value = produce(Path(args.output).resolve())
    elif args.command == "replay":
        value = replay(Path(args.input).resolve(), Path(args.output).resolve(), args.machine_id)
    else:
        value = aggregate(Path(args.input).resolve(), Path(args.output).resolve())
    print(json.dumps(value, indent=2, sort_keys=True))
    return 0 if args.command != "aggregate" or value.get("success") is True else 1


if __name__ == "__main__":
    raise SystemExit(main())
