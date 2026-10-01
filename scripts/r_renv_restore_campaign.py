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

FORMAT = "pcs-r-renv-offline-restore-v1"
BASE_TAG = "docker.io/library/r-base:latest"

ANALYSIS = r'''d <- read.csv("renv_input.csv")
payload <- paste(as.character(d$value), collapse = ",")
hash <- digest::digest(payload, algo = "sha256", serialize = FALSE)
out <- data.frame(metric = "sha256", value = hash)
write.csv(out, "renv_output.csv", row.names = FALSE, quote = FALSE)
'''


def run(argv: list[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
    p = subprocess.run(argv, text=True, capture_output=True)
    if check and p.returncode:
        raise RuntimeError(
            f"command failed ({p.returncode}): {argv!r}\n"
            f"stdout={p.stdout[-10000:]}\nstderr={p.stderr[-10000:]}"
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


def archive_version(path: Path, package: str) -> str:
    m = re.match(rf"^{re.escape(package)}_([^/]+)\.tar\.gz$", path.name)
    if not m:
        raise RuntimeError(f"unexpected {package} archive name: {path.name}")
    return m.group(1)


def produce(output: Path) -> dict[str, Any]:
    output.mkdir(parents=True, exist_ok=False)
    run(["docker", "pull", BASE_TAG])
    base_digest = image_index_digest(BASE_TAG)
    image_ref = f"docker.io/library/r-base@{base_digest}"
    run(["docker", "pull", image_ref])
    rver = run(
        [
            "docker",
            "run",
            "--rm",
            "--network=none",
            image_ref,
            "Rscript",
            "--vanilla",
            "-e",
            "cat(as.character(getRversion()))",
        ]
    ).stdout.strip()

    base_has_digest = run(
        [
            "docker",
            "run",
            "--rm",
            "--network=none",
            image_ref,
            "Rscript",
            "--vanilla",
            "-e",
            'quit(status=if(requireNamespace("digest", quietly=TRUE)) 17 else 0)',
        ],
        check=False,
    )
    if base_has_digest.returncode != 0:
        raise RuntimeError(
            "selected R base unexpectedly already contains digest; "
            "campaign would not prove restoration"
        )

    project = Path(tempfile.mkdtemp(prefix="pcs-renv-producer-"))
    private = project.parent / "renv-private.pem"
    try:
        init_project(project, template="pkpd", subject="renv-offline-restoration")
        (project / "analysis_renv.R").write_text(ANALYSIS, encoding="utf-8")
        (project / "renv_input.csv").write_text(
            "value\n2\n3\n5\n7\n11\n13\n",
            encoding="utf-8",
        )

        downloads = project / "_downloads"
        downloads.mkdir()
        run(
            [
                "docker",
                "run",
                "--rm",
                "-v",
                f"{downloads}:/downloads",
                image_ref,
                "Rscript",
                "--vanilla",
                "-e",
                (
                    'options(repos=c(CRAN="https://cloud.r-project.org"));'
                    'download.packages(c("renv","digest"),destdir="/downloads",'
                    'type="source",repos=getOption("repos"))'
                ),
            ]
        )
        renv_archives = sorted(downloads.glob("renv_*.tar.gz"))
        digest_archives = sorted(downloads.glob("digest_*.tar.gz"))
        if len(renv_archives) != 1 or len(digest_archives) != 1:
            raise RuntimeError(
                f"unexpected source downloads: renv={renv_archives}, digest={digest_archives}"
            )
        renv_version = archive_version(renv_archives[0], "renv")
        digest_version = archive_version(digest_archives[0], "digest")

        bootstrap = project / "r-packages" / "bootstrap"
        contrib = project / "r-packages" / "repo" / "src" / "contrib"
        bootstrap.mkdir(parents=True)
        contrib.mkdir(parents=True)
        renv_target = bootstrap / renv_archives[0].name
        digest_target = contrib / digest_archives[0].name
        shutil.move(str(renv_archives[0]), renv_target)
        shutil.move(str(digest_archives[0]), digest_target)
        shutil.rmtree(downloads)

        run(
            [
                "docker",
                "run",
                "--rm",
                "-v",
                f"{project / 'r-packages' / 'repo'}:/repo",
                image_ref,
                "Rscript",
                "--vanilla",
                "-e",
                'tools::write_PACKAGES("/repo/src/contrib", type="source")',
            ]
        )

        lock = {
            "R": {
                "Version": rver,
                "Repositories": [
                    {"Name": "CRAN", "URL": "file:///r-packages/repo"}
                ],
            },
            "Packages": {
                "digest": {
                    "Package": "digest",
                    "Version": digest_version,
                    "Source": "Repository",
                    "Repository": "CRAN",
                }
            },
        }
        (project / "renv.lock").write_text(
            json.dumps(lock, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        (project / "DESCRIPTION").write_text(
            "Package: pcsRenvBoundary\n"
            "Version: 0.0.1\n"
            f"Depends: R (== {rver})\n"
            f"Imports: digest (== {digest_version})\n",
            encoding="utf-8",
        )
        (project / "Dockerfile").write_text(
            f"FROM {image_ref}\n"
            "ENV RENV_CONFIG_AUTOLOADER_ENABLED=FALSE "
            "RENV_CONFIG_SANDBOX_ENABLED=FALSE\n"
            "COPY r-packages /r-packages\n"
            "COPY renv.lock /renv.lock\n"
            f"RUN R CMD INSTALL /r-packages/bootstrap/{renv_target.name}\n"
            "RUN Rscript --vanilla -e "
            "\"options(repos=c(CRAN='file:///r-packages/repo'));"
            "renv::restore(lockfile='/renv.lock',library=.libPaths()[1],prompt=FALSE)\"\n",
            encoding="utf-8",
        )

        producer_tag = "pcs-renv-producer"
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
        restored = run(
            [
                "docker",
                "run",
                "--rm",
                "--network=none",
                producer_tag,
                "Rscript",
                "--vanilla",
                "-e",
                'cat(as.character(packageVersion("digest")))',
            ]
        ).stdout.strip()
        if restored != digest_version:
            raise RuntimeError(
                f"renv restore produced digest {restored}, expected {digest_version}"
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
                "Rscript",
                "--vanilla",
                "analysis_renv.R",
            ]
        )

        report = discover_project_v06(
            project,
            minimum_workflow_confidence=0.85,
        )
        restoration = report["environment_capture"].get("restoration_artifacts", [])
        r_sources = [
            row for row in restoration
            if row.get("kind") == "r_distribution_artifact"
        ]
        required_vendor_paths = {
            f"r-packages/bootstrap/{renv_target.name}",
            f"r-packages/repo/src/contrib/{digest_target.name}",
            "r-packages/repo/src/contrib/PACKAGES",
        }
        observed_vendor_paths = {row.get("path") for row in r_sources}
        if not required_vendor_paths.issubset(observed_vendor_paths):
            raise RuntimeError(
                "R restoration payloads were not fully bound into the signed environment: "
                f"missing={sorted(required_vendor_paths - observed_vendor_paths)}"
            )

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
            "r_version": rver,
            "renv_version": renv_version,
            "digest_version": digest_version,
            "base_image_digest_package_absent": True,
            "renv_archive": {
                "name": renv_target.name,
                "sha256": sha256_file(renv_target),
            },
            "digest_archive": {
                "name": digest_target.name,
                "sha256": sha256_file(digest_target),
            },
            "producer_public_key_fingerprint": fingerprint,
            "bundle_sha256": sha256_file(bundle),
            "expected_output_sha256": sha256_file(project / "renv_output.csv"),
            "restoration_artifacts_signed": len(r_sources),
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
        timeout_seconds=900,
    )
    receipt = json.loads(
        (replay_dir / "pcs-replay-execution.json").read_text(encoding="utf-8")
    )
    realized = json.loads(
        (replay_dir / "pcs-realized-environment.json").read_text(encoding="utf-8")
    )
    out = replay_dir / "outputs" / "renv_output.csv"
    digest_pkg = next(
        (
            row
            for row in realized.get("r", {}).get("packages", [])
            if str(row.get("name", "")).lower() == "digest"
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
        "expected_r_version": meta["r_version"],
        "base_image_digest_package_absent": meta.get("base_image_digest_package_absent"),
        "restoration_artifacts_signed": meta.get("restoration_artifacts_signed"),
        "realized_r_version": realized.get("r", {}).get("version"),
        "expected_digest_version": meta["digest_version"],
        "realized_digest_version": digest_pkg.get("version") if digest_pkg else None,
        "r_interpreter_sha256": realized.get("r", {}).get("executable_sha256"),
        "r_package_count": len(realized.get("r", {}).get("packages", [])),
        "dependency_tree_sha256": realized.get("dependency_tree_sha256"),
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
        "base_image_did_not_supply_digest": len(rows) >= 2 and all(
            row.get("base_image_digest_package_absent") is True for row in rows
        ),
        "signed_local_r_repository_payloads_present": len(rows) >= 2 and all(
            isinstance(row.get("restoration_artifacts_signed"), int)
            and row.get("restoration_artifacts_signed") >= 3
            for row in rows
        ),
        "r_version_matches_signed_lock": len(rows) >= 2 and all(
            row.get("realized_r_version") == row.get("expected_r_version")
            for row in rows
        ),
        "renv_restored_digest_version_matches_lock": len(rows) >= 2 and all(
            row.get("realized_digest_version") == row.get("expected_digest_version")
            for row in rows
        ),
        "r_interpreter_hash_captured_everywhere": len(rows) >= 2 and all(
            isinstance(row.get("r_interpreter_sha256"), str)
            and len(row["r_interpreter_sha256"]) == 64
            for row in rows
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
