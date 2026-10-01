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
from pcs.discover_v06 import (
    confirm_manifest_draft_v06,
    discover_project_v06,
    write_discovery_outputs_v06,
)
from pcs.environment_execute_v06 import execute_prepared_replay_workspace_v06
from pcs.environment_workspace_v06 import prepare_verified_environment_workspace_v06
from pcs.scaffold import init_project
from pcs.signing import generate_keypair

FORMAT = "pcs-python-hash-wheel-abi-v1"
BASE_TAG = "docker.io/library/python:3.12-slim-bookworm"
PACKAGE_SPEC = "numpy>=2.1,<3"

ANALYSIS = r'''import json
from pathlib import Path
import numpy as np

payload = json.loads(Path("native_input.json").read_text(encoding="utf-8"))
values = np.asarray(payload["values"], dtype=np.float64)
result = {
    "count": int(values.size),
    "sum": f"{float(values.sum()):.12f}",
    "dot": f"{float(np.dot(values, values)):.12f}",
    "mean": f"{float(values.mean()):.12f}",
}
Path("native_output.json").write_text(
    json.dumps(result, sort_keys=True, separators=(",", ":")) + "\n",
    encoding="utf-8",
)
'''


def run(argv: list[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
    p = subprocess.run(argv, text=True, capture_output=True)
    if check and p.returncode:
        raise RuntimeError(
            f"command failed ({p.returncode}): {argv!r}\n"
            f"stdout={p.stdout[-8000:]}\nstderr={p.stderr[-8000:]}"
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


def download_wheel(wheelhouse: Path, platform_tag: str, spec: str) -> None:
    run(
        [
            "python",
            "-m",
            "pip",
            "download",
            "--disable-pip-version-check",
            "--only-binary=:all:",
            "--no-deps",
            "--dest",
            str(wheelhouse),
            "--platform",
            platform_tag,
            "--implementation",
            "cp",
            "--python-version",
            "312",
            "--abi",
            "cp312",
            spec,
        ]
    )


def wheel_version(path: Path) -> str:
    m = re.match(r"(?i)^numpy-([0-9][^-]*)-", path.name)
    if not m:
        raise RuntimeError(f"unexpected numpy wheel filename: {path.name}")
    return m.group(1)


def produce(output: Path) -> dict[str, Any]:
    output.mkdir(parents=True, exist_ok=False)
    run(["docker", "pull", BASE_TAG])
    base_digest = image_index_digest(BASE_TAG)
    image_ref = f"docker.io/library/python@{base_digest}"
    run(["docker", "pull", image_ref])
    pyver = run(
        [
            "docker",
            "run",
            "--rm",
            "--network=none",
            image_ref,
            "python",
            "-c",
            "import platform; print(platform.python_version())",
        ]
    ).stdout.strip()

    project = Path(tempfile.mkdtemp(prefix="pcs-python-wheel-producer-"))
    private = project.parent / "python-wheel-private.pem"
    try:
        init_project(project, template="pkpd", subject="python-hash-wheel-abi")
        (project / "analysis_native.py").write_text(ANALYSIS, encoding="utf-8")
        (project / "native_input.json").write_text(
            '{"values":[1,2,3,5,8,13,21]}\n',
            encoding="utf-8",
        )

        wheelhouse = project / "wheelhouse"
        wheelhouse.mkdir()
        download_wheel(wheelhouse, "manylinux2014_x86_64", PACKAGE_SPEC)
        x86_wheels = sorted(wheelhouse.glob("numpy-*-x86_64*.whl"))
        if len(x86_wheels) != 1:
            raise RuntimeError(f"expected one x86_64 wheel, got {x86_wheels}")
        version = wheel_version(x86_wheels[0])

        download_wheel(
            wheelhouse,
            "manylinux2014_aarch64",
            f"numpy=={version}",
        )
        wheels = sorted(wheelhouse.glob("numpy-*.whl"))
        if len(wheels) != 2:
            raise RuntimeError(f"expected two architecture wheels, got {[x.name for x in wheels]}")
        if {wheel_version(x) for x in wheels} != {version}:
            raise RuntimeError("architecture wheels resolved different versions")

        hashes = [sha256_file(w) for w in wheels]
        lock_lines = [f"numpy=={version} \\"]
        for index, digest in enumerate(hashes):
            suffix = " \\" if index < len(hashes) - 1 else ""
            lock_lines.append(f"    --hash=sha256:{digest}{suffix}")
        (project / "requirements.lock").write_text(
            "\n".join(lock_lines) + "\n",
            encoding="utf-8",
        )
        (project / ".python-version").write_text(pyver + "\n", encoding="utf-8")
        (project / "Dockerfile").write_text(
            f"FROM {image_ref}\n"
            "ENV PYTHONDONTWRITEBYTECODE=1 PIP_DISABLE_PIP_VERSION_CHECK=1\n"
            "COPY wheelhouse /wheelhouse\n"
            "COPY requirements.lock /requirements.lock\n"
            "RUN python -m pip install --no-compile --no-index "
            "--find-links=/wheelhouse --require-hashes -r /requirements.lock\n",
            encoding="utf-8",
        )

        producer_tag = "pcs-python-wheel-producer"
        run(
            [
                "docker",
                "build",
                "--network=none",
                "--no-cache",
                "--pull=false",
                "--provenance=false",
                "--sbom=false",
                "-t",
                producer_tag,
                "-f",
                str(project / "Dockerfile"),
                str(project),
            ]
        )
        run(
            [
                "docker",
                "run",
                "--rm",
                "--network=none",
                "-v",
                f"{project}:/workspace",
                "-w",
                "/workspace",
                producer_tag,
                "python",
                "-B",
                "analysis_native.py",
            ]
        )

        report = discover_project_v06(project)
        restoration = report["environment_capture"].get("restoration_artifacts", [])
        wheel_sources = [
            row for row in restoration
            if row.get("kind") == "python_distribution_artifact"
        ]
        if len(wheel_sources) != 2:
            raise RuntimeError(
                f"expected two signed Python distribution artifacts, got {wheel_sources}"
            )
        if report["environment_capture"].get("hermeticity") != "strongly_pinned":
            raise RuntimeError("hash-locked vendored wheel environment was not strongly pinned")

        draft = project / "pcs-manifest.draft.json"
        write_discovery_outputs_v06(
            report,
            manifest_output=draft,
            report_output=project / "pcs-discovery.json",
            overwrite=True,
        )
        manifest = project / "confirmed-manifest.json"
        confirm_manifest_draft_v06(
            draft,
            manifest,
            project_root=project,
            overwrite=True,
        )

        public = output / "producer-public.pem"
        fingerprint = generate_keypair(private, public)["fingerprint"]
        bundle = output / "study.pcs.zip"
        attested = attest_v06(
            manifest,
            bundle,
            private,
            public,
            expected_fingerprint=fingerprint,
        )
        if attested.get("valid") is not True:
            raise RuntimeError(f"attestation failed: {attested}")

        value = {
            "format": FORMAT,
            "phase": "producer",
            "base_image_ref": image_ref,
            "base_image_index_digest": base_digest,
            "python_version": pyver,
            "package": "numpy",
            "package_version": version,
            "wheel_files": [
                {
                    "name": w.name,
                    "sha256": sha256_file(w),
                    "size": w.stat().st_size,
                }
                for w in wheels
            ],
            "producer_public_key_fingerprint": fingerprint,
            "bundle_sha256": sha256_file(bundle),
            "expected_output_sha256": sha256_file(project / "native_output.json"),
            "restoration_artifacts_signed": len(wheel_sources),
        }
        write_json(output / "campaign.json", value)
        return value
    finally:
        shutil.rmtree(project, ignore_errors=True)
        private.unlink(missing_ok=True)


def replay(source: Path, output: Path, machine_id: str) -> dict[str, Any]:
    meta = json.loads((source / "campaign.json").read_text(encoding="utf-8"))
    output.mkdir(parents=True, exist_ok=False)
    run(["docker", "pull", meta["base_image_ref"]])

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
    receipt = json.loads(
        (replay_dir / "pcs-replay-execution.json").read_text(encoding="utf-8")
    )
    realized = json.loads(
        (replay_dir / "pcs-realized-environment.json").read_text(encoding="utf-8")
    )
    out = replay_dir / "outputs" / "native_output.json"
    native = [
        row
        for row in realized.get("python", {}).get("native_extensions", [])
        if str(row.get("package", "")).lower() == "numpy"
    ]
    package = next(
        (
            row
            for row in realized.get("python", {}).get("packages", [])
            if str(row.get("name", "")).lower() == "numpy"
        ),
        None,
    )
    summary = {
        "format": FORMAT,
        "phase": "consumer",
        "machine_id": machine_id,
        "host_machine": platform.machine(),
        "host_platform": platform.platform(),
        "prepared_valid": prepared.get("valid"),
        "valid": result.get("valid"),
        "environment_contract_match": result.get("environment_contract_match"),
        "determinism_confirmed": result.get("determinism_confirmed"),
        "determinism_runs_completed": result.get("determinism_runs_completed"),
        "expected_package_version": meta["package_version"],
        "realized_package_version": package.get("version") if package else None,
        "native_extensions": native,
        "native_extension_hashes": sorted(
            {row["sha256"] for row in native if isinstance(row.get("sha256"), str)}
        ),
        "dependency_tree_sha256": realized.get("dependency_tree_sha256"),
        "realized_environment_semantic_sha256": realized.get("semantic_sha256"),
        "container_image_digest": realized.get("container_image_digest"),
        "expected_output_sha256": meta["expected_output_sha256"],
        "realized_output_sha256": sha256_file(out) if out.is_file() else None,
        "output_matches_producer": (
            out.is_file()
            and sha256_file(out) == meta["expected_output_sha256"]
        ),
        "environment_comparison": receipt.get("environment_comparison"),
    }
    write_json(output / "summary.json", summary)
    return summary


def aggregate(input_root: Path, output: Path) -> dict[str, Any]:
    rows = []
    for p in sorted(input_root.rglob("summary.json")):
        value = json.loads(p.read_text(encoding="utf-8"))
        if value.get("format") == FORMAT and value.get("phase") == "consumer":
            rows.append(value)

    architectures = {str(row.get("host_machine") or "").lower() for row in rows}
    outputs = {row.get("realized_output_sha256") for row in rows if row.get("realized_output_sha256")}
    native_sets = {
        row["machine_id"]: tuple(row.get("native_extension_hashes", []))
        for row in rows
    }
    assertions = {
        "amd64_and_arm64_observed": (
            any(x in {"x86_64", "amd64"} or "x86" in x for x in architectures)
            and any(x in {"aarch64", "arm64"} or "arm" in x for x in architectures)
        ),
        "all_replays_valid": len(rows) >= 2 and all(row.get("valid") is True for row in rows),
        "all_environment_contracts_match": len(rows) >= 2 and all(
            row.get("environment_contract_match") is True for row in rows
        ),
        "all_three_run_deterministic": len(rows) >= 2 and all(
            row.get("determinism_confirmed") is True
            and row.get("determinism_runs_completed") == 3
            for row in rows
        ),
        "restored_package_version_matches_lock": len(rows) >= 2 and all(
            row.get("realized_package_version") == row.get("expected_package_version")
            for row in rows
        ),
        "native_extension_hash_captured_on_every_host": len(rows) >= 2 and all(
            len(row.get("native_extension_hashes", [])) >= 1 for row in rows
        ),
        "native_extension_binary_differs_across_architecture": (
            len({digest for values in native_sets.values() for digest in values}) >= 2
        ),
        "scientific_output_byte_identical_across_architecture": len(outputs) == 1 and bool(outputs),
        "all_outputs_match_signed_producer": len(rows) >= 2 and all(
            row.get("output_matches_producer") is True for row in rows
        ),
    }
    value = {
        "format": FORMAT,
        "phase": "aggregate",
        "rows": rows,
        "architectures": sorted(architectures),
        "native_extension_hashes_by_machine": native_sets,
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
        value = replay(
            Path(args.input).resolve(),
            Path(args.output).resolve(),
            args.machine_id,
        )
    else:
        value = aggregate(Path(args.input).resolve(), Path(args.output).resolve())

    print(json.dumps(value, indent=2, sort_keys=True))
    return 0 if args.command != "aggregate" or value.get("success") is True else 1


if __name__ == "__main__":
    raise SystemExit(main())
