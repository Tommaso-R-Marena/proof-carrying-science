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

FORMAT = "pcs-oci-engine-boundary-v1"
BASE_TAG = "docker.io/library/python:3.12-slim-bookworm"

ANALYSIS = """from decimal import Decimal, getcontext
from pathlib import Path

getcontext().prec = 40
rows = [
    (Decimal("0"), Decimal("100")),
    (Decimal("1"), Decimal("81.8730753078")),
    (Decimal("2"), Decimal("67.0320046036")),
]
out = ["time,prediction"]
for t, y in rows:
    adjusted = y * (Decimal("1") + t / Decimal("1000"))
    out.append(f"{t},{adjusted.quantize(Decimal('0.0000000001'))}")
Path("predictions.csv").write_text("\n".join(out) + "\n", encoding="utf-8")
"""


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
    image_ref = f"docker.io/library/python@{digest}"
    run(["docker", "pull", image_ref])
    pyver = run([
        "docker", "run", "--rm", "--network=none", image_ref,
        "python", "-c", "import platform; print(platform.python_version())",
    ]).stdout.strip()
    pip_text = run([
        "docker", "run", "--rm", "--network=none", image_ref,
        "python", "-m", "pip", "--version",
    ]).stdout.strip()
    pipver = re.match(r"pip\s+([^\s]+)", pip_text).group(1)

    project = Path(tempfile.mkdtemp(prefix="pcs-oci-engine-producer-"))
    try:
        init_project(project, template="pkpd", subject="oci-engine-boundary")
        (project / "analysis.py").write_text(ANALYSIS, encoding="utf-8")
        (project / "requirements.txt").write_text(f"pip=={pipver}\n", encoding="utf-8")
        (project / ".python-version").write_text(pyver + "\n", encoding="utf-8")
        (project / "Dockerfile").write_text(f"FROM {image_ref}\n", encoding="utf-8")
        run([
            "docker", "run", "--rm", "--network=none",
            "-v", f"{project}:/workspace", "-w", "/workspace",
            image_ref, "python", "analysis.py",
        ])

        report = discover_project_v06(project)
        draft = project / "pcs-manifest.draft.json"
        write_discovery_outputs_v06(
            report,
            manifest_output=draft,
            report_output=project / "pcs-discovery.json",
            overwrite=True,
        )
        manifest = project / "confirmed-manifest.json"
        confirm_manifest_draft_v06(draft, manifest, project_root=project, overwrite=True)

        private = project.parent / "oci-engine-private.pem"
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
            "python_version": pyver,
            "pip_version": pipver,
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


def replay(source: Path, output: Path, runtime: str, machine_id: str) -> dict[str, Any]:
    if runtime not in {"docker", "podman"}:
        raise ValueError("runtime must be docker or podman")
    if shutil.which(runtime) is None:
        raise RuntimeError(f"{runtime} is unavailable")

    meta = json.loads((source / "campaign.json").read_text(encoding="utf-8"))
    output.mkdir(parents=True, exist_ok=False)
    run([runtime, "pull", meta["image_ref"]])

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
        runtime=runtime,
        determinism_runs=3,
    )
    receipt = json.loads((replay_dir / "pcs-replay-execution.json").read_text(encoding="utf-8"))
    realized = json.loads((replay_dir / "pcs-realized-environment.json").read_text(encoding="utf-8"))
    predictions = replay_dir / "outputs" / "predictions.csv"

    summary = {
        "format": FORMAT,
        "phase": "consumer",
        "runtime": runtime,
        "runtime_version": run([runtime, "--version"]).stdout.strip(),
        "machine_id": machine_id,
        "host_platform": platform.platform(),
        "host_machine": platform.machine(),
        "prepared_valid": prepared.get("valid"),
        "valid": result.get("valid"),
        "environment_contract_match": result.get("environment_contract_match"),
        "determinism_confirmed": result.get("determinism_confirmed"),
        "determinism_runs_completed": result.get("determinism_runs_completed"),
        "expected_predictions_sha256": meta["expected_predictions_sha256"],
        "realized_predictions_sha256": sha256_file(predictions) if predictions.is_file() else None,
        "output_matches_producer": (
            predictions.is_file()
            and sha256_file(predictions) == meta["expected_predictions_sha256"]
        ),
        "container_image_digest": realized.get("container_image_digest"),
        "container_image_digest_kind": realized.get("container_image_digest_kind"),
        "dependency_tree_sha256": realized.get("dependency_tree_sha256"),
        "realized_environment_semantic_sha256": realized.get("semantic_sha256"),
        "python_executable_sha256": realized.get("python", {}).get("executable_sha256"),
        "verdict": receipt.get("verdict"),
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
    by_runtime = {row["runtime"]: row for row in rows}
    docker = by_runtime.get("docker")
    podman = by_runtime.get("podman")
    assertions = {
        "docker_observed": docker is not None,
        "podman_observed": podman is not None,
        "both_replays_valid": bool(docker and podman and docker.get("valid") is True and podman.get("valid") is True),
        "both_environment_contracts_match": bool(
            docker and podman
            and docker.get("environment_contract_match") is True
            and podman.get("environment_contract_match") is True
        ),
        "both_three_run_deterministic": bool(
            docker and podman
            and docker.get("determinism_confirmed") is True
            and podman.get("determinism_confirmed") is True
            and docker.get("determinism_runs_completed") == 3
            and podman.get("determinism_runs_completed") == 3
        ),
        "scientific_output_identical_across_engines": bool(
            docker and podman
            and docker.get("realized_predictions_sha256")
            and docker.get("realized_predictions_sha256") == podman.get("realized_predictions_sha256")
        ),
        "both_outputs_match_signed_producer": bool(
            docker and podman
            and docker.get("output_matches_producer") is True
            and podman.get("output_matches_producer") is True
        ),
    }
    value = {
        "format": FORMAT,
        "phase": "aggregate",
        "rows": rows,
        "assertions": assertions,
        "unsigned_cross_engine_observations": {
            "container_image_digest_equal": (
                docker.get("container_image_digest") == podman.get("container_image_digest")
                if docker and podman else None
            ),
            "dependency_tree_sha256_equal": (
                docker.get("dependency_tree_sha256") == podman.get("dependency_tree_sha256")
                if docker and podman else None
            ),
            "realized_environment_semantic_sha256_equal": (
                docker.get("realized_environment_semantic_sha256")
                == podman.get("realized_environment_semantic_sha256")
                if docker and podman else None
            ),
        },
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
    r.add_argument("--runtime", choices=["docker", "podman"], required=True)
    r.add_argument("--machine-id", required=True)
    a = sub.add_parser("aggregate")
    a.add_argument("--input", required=True)
    a.add_argument("--output", required=True)
    args = parser.parse_args()

    if args.command == "produce":
        value = produce(Path(args.output).resolve())
    elif args.command == "replay":
        value = replay(Path(args.input).resolve(), Path(args.output).resolve(), args.runtime, args.machine_id)
    else:
        value = aggregate(Path(args.input).resolve(), Path(args.output).resolve())
    print(json.dumps(value, indent=2, sort_keys=True))
    return 0 if args.command != "aggregate" or value.get("success") is True else 1


if __name__ == "__main__":
    raise SystemExit(main())
